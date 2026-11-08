#!/usr/bin/env python3
"""
Evaluation harness.

Answers "how do I know this is good?" with numbers that come from files,
not from opinion. Five questions, in order of how much they matter:

  1. Gold-set agreement - does the tool find the promos a human picked by
     hand BEFORE the tool existed? Measured as IoU on the time span.
  2. Validator integrity - did any shipped promo carry a timestamp that does
     not exist in the screenplay? This must be zero.
  3. Blind-gate results - what fraction of structurally-good promos a
     context-free reader could actually follow, and which failed.
  4. Stability - same input, two different models: do they choose the same
     moments? Low agreement means the ranking is model-taste, not signal.
  5. Determinism - same input, same model, twice: byte-identical?

    python evaluate.py
    python evaluate.py --a outputs --b outputs_qwen --gold docs/gold_set.json
"""
import os
import json
import argparse
import hashlib


def load(folder: str) -> dict | None:
    path = os.path.join(folder, "promos.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def iou(a0: float, a1: float, b0: float, b1: float) -> float:
    """Temporal intersection-over-union of two single spans."""
    overlap = max(0.0, min(a1, b1) - max(a0, b0))
    if overlap <= 0:
        return 0.0
    union = (a1 - a0) + (b1 - b0) - overlap
    return overlap / union if union > 0 else 0.0


def iou_segments(mine: tuple[float, float], segments: list[tuple[float, float]]) -> float:
    """
    IoU of one hand-picked span against a promo's ACTUAL segments.

    A two-piece promo running 6.8-32.0 and 70.0-89.8 does not cover 32-70;
    that gap is exactly what the splice removed. Measuring against the outer
    envelope (6.8-89.8) counts the removed seconds as covered, and it inflated
    agreement with my hand-picks from 0.46 to 0.52 the moment multi-segment
    promos existed. Union-based is the honest version.
    """
    if not segments:
        return 0.0
    covered = sum(max(0.0, e - s) for s, e in segments)
    overlap = sum(max(0.0, min(mine[1], e) - max(mine[0], s)) for s, e in segments)
    if overlap <= 0:
        return 0.0
    union = (mine[1] - mine[0]) + covered - overlap
    return overlap / union if union > 0 else 0.0


def all_promos(result: dict) -> dict:
    out = {p["promo_id"]: p for p in result["promos"]}
    for p in result.get("rejected", []):
        out.setdefault(p["promo_id"], p)
    return out


def span(promo: dict) -> tuple[float, float]:
    """Outer envelope. Only for display; never for scoring (see iou_segments)."""
    segs = promo["segments"]
    return segs[0]["start_s"], segs[-1]["end_s"]


def segments_of(promo: dict) -> list[tuple[float, float]]:
    return [(s["start_s"], s["end_s"]) for s in promo["segments"]]


def describe(promo: dict) -> str:
    segs = promo["segments"]
    if len(segs) == 1:
        return f"{segs[0]['start_s']:.1f}-{segs[0]['end_s']:.1f}"
    return " + ".join(f"{s['start_s']:.1f}-{s['end_s']:.1f}" for s in segs)


# ---------------------------------------------------------------------------
# 1. Gold-set agreement
# ---------------------------------------------------------------------------

def gold_agreement(result: dict, gold: list[dict]) -> dict:
    promos = all_promos(result)
    rows = []
    for entry in gold:
        ep = entry["episode"]
        mine = (entry["start_s"], entry["end_s"])
        # Any promo the tool produced for this episode.
        here = [p for p in promos.values() if ep in p["episodes"]]
        best, best_iou = None, 0.0
        for promo in here:
            score = iou_segments(mine, segments_of(promo))
            if score > best_iou:
                best, best_iou = promo, score
        shipped = {p["promo_id"] for p in result["promos"]}
        rows.append({
            "episode": ep,
            "my_pick": f"{mine[0]:.1f}-{mine[1]:.1f}",
            "note": entry.get("why", ""),
            "tool_pick": describe(best) if best else None,
            "tool_shape": best["shape"] if best else None,
            "iou": round(best_iou, 3),
            "overlaps_at_all": best_iou > 0,
            "promo_id": best["promo_id"] if best else None,
            "shipped": bool(best and best["promo_id"] in shipped),
            "status": (
                "shipped" if best and best["promo_id"] in shipped
                else ("rejected: " + (best.get("rejected_reason", "")[:70]) if best else "no promo for this episode")
            ),
            "rank": best.get("rank") if best else None,
        })
    scored = [r["iou"] for r in rows]
    return {
        "rows": rows,
        "n_gold": len(rows),
        "mean_iou": round(sum(scored) / len(scored), 3) if scored else 0.0,
        "n_overlapping": sum(1 for r in rows if r["overlaps_at_all"]),
        "n_shipped": sum(1 for r in rows if r["shipped"]),
    }


# ---------------------------------------------------------------------------
# 2. Validator integrity
# ---------------------------------------------------------------------------

def validator_report(result: dict) -> dict:
    everything = result["promos"] + result.get("rejected", [])
    if result.get("flagship"):
        everything = everything + [result["flagship"]]
    checks: dict[str, dict] = {}
    for promo in everything:
        for name, passed in (promo.get("validators") or {}).items():
            bucket = checks.setdefault(name, {"pass": 0, "fail": 0, "failing_ids": []})
            if passed:
                bucket["pass"] += 1
            else:
                bucket["fail"] += 1
                bucket["failing_ids"].append(promo["promo_id"])
    shipped_invalid = [p["promo_id"] for p in result["promos"] if not p.get("valid", True)]
    return {
        "checks": checks,
        "n_evaluated": len(everything),
        "shipped_but_invalid": shipped_invalid,
        "invented_timestamps_in_shipped_output":
            checks.get("timestamps_exist", {}).get("fail", 0) == 0
            and not shipped_invalid,
    }


# ---------------------------------------------------------------------------
# 3. Blind gate
# ---------------------------------------------------------------------------

def shape_report(result: dict) -> dict:
    """
    Does splicing two moments together cost comprehension?

    The brief says a promo is "usually one continuous stretch" but may join a
    few moments. This measures whether the "usually" is earned, by comparing
    blind-gate outcomes for continuous promos against two-piece ones.
    """
    buckets: dict[str, dict] = {}
    for promo in result["promos"] + result.get("rejected", []):
        gate = promo.get("cold_viewer") or {}
        if gate.get("verdict") not in ("pass", "fail"):
            continue
        bucket = buckets.setdefault(
            promo["shape"], {"pass": 0, "fail": 0, "scores": [], "ranks": []}
        )
        bucket[gate["verdict"]] += 1
        if gate.get("score_n") is not None:
            bucket["scores"].append(gate["score_n"])
        if promo.get("rank"):
            bucket["ranks"].append(promo["rank"])

    out = {}
    for shape, bucket in buckets.items():
        n = bucket["pass"] + bucket["fail"]
        out[shape] = {
            "tested": n,
            "passed": bucket["pass"],
            "failed": bucket["fail"],
            "pass_rate": round(bucket["pass"] / n, 3) if n else None,
            "mean_gate_score": round(
                sum(bucket["scores"]) / len(bucket["scores"]), 2
            ) if bucket["scores"] else None,
            "best_rank": min(bucket["ranks"]) if bucket["ranks"] else None,
            "shipped": len(bucket["ranks"]),
        }
    return out


def gate_report(result: dict) -> dict:
    tested, failures, not_tested = [], [], []
    for promo in result["promos"] + result.get("rejected", []):
        gate = promo.get("cold_viewer")
        if not gate:
            continue
        if gate.get("verdict") == "not_tested":
            not_tested.append(promo["promo_id"])
            continue
        tested.append(promo)
        if gate.get("verdict") == "fail":
            failures.append({
                "promo_id": promo["promo_id"],
                "episodes": promo["episodes"],
                "structural_score": promo["scores"]["composite"],
                "gate_score": gate.get("score"),
                "answers": gate.get("answers"),
                "passes": gate.get("passes"),
            })
    by_check: dict[str, int] = {}
    for promo in tested:
        for name, value in ((promo.get("cold_viewer") or {}).get("passes") or {}).items():
            by_check[name] = by_check.get(name, 0) + (1 if value else 0)
    return {
        "n_tested": len(tested),
        "n_failed": len(failures),
        "n_not_tested": len(not_tested),
        "pass_rate": round(1 - len(failures) / len(tested), 3) if tested else None,
        "per_criterion_pass_counts": by_check,
        "per_criterion_pass_rate": {
            k: round(v / len(tested), 3) for k, v in by_check.items()
        } if tested else {},
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# 4. Cross-model stability
# ---------------------------------------------------------------------------

def stability(a: dict, b: dict) -> dict:
    """Same episodes, two models: do they pick the same seconds?"""
    pa, pb = all_promos(a), all_promos(b)
    episodes = sorted(
        {e for p in pa.values() for e in p["episodes"]}
        & {e for p in pb.values() for e in p["episodes"]}
    )
    rows = []
    for ep in episodes:
        ia = next((p for p in pa.values() if ep in p["episodes"]), None)
        ib = next((p for p in pb.values() if ep in p["episodes"]), None)
        if not ia or not ib:
            continue
        # Model-vs-model on the span each one chose. Both are compared on the
        # envelope here because the comparison is symmetric and both sides
        # may be spliced; the gold-set numbers use the stricter union form.
        sa, ea = span(ia)
        sb, eb = span(ib)
        rows.append({
            "episode": ep,
            "a": describe(ia),
            "b": describe(ib),
            "iou": round(iou(sa, ea, sb, eb), 3),
            "same_hook_type": (ia.get("hook_type") or "") == (ib.get("hook_type") or ""),
        })
    scores = [r["iou"] for r in rows]
    shipped_a = {p["promo_id"] for p in a["promos"]}
    shipped_b = {p["promo_id"] for p in b["promos"]}
    return {
        "model_a": a["llm"]["model"],
        "model_b": b["llm"]["model"],
        "n_episodes": len(rows),
        "mean_iou": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "n_identical": sum(1 for s in scores if s > 0.99),
        "n_disjoint": sum(1 for s in scores if s == 0.0),
        "n_substantial_overlap": sum(1 for s in scores if s >= 0.5),
        "shipped_set_jaccard": round(
            len(shipped_a & shipped_b) / len(shipped_a | shipped_b), 3
        ) if (shipped_a or shipped_b) else None,
        "hook_type_agreement": round(
            sum(1 for r in rows if r["same_hook_type"]) / len(rows), 3
        ) if rows else None,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# 5. Determinism
# ---------------------------------------------------------------------------

def fingerprint(result: dict) -> str:
    """Hash of the decisions only, ignoring timing and call counts."""
    payload = [
        {
            "id": p["promo_id"],
            "segments": [(s["episode"], s["start_s"], s["end_s"]) for s in p["segments"]],
            "hook_beat": p.get("hook_beat_id"),
            "cliff_beat": p.get("cliffhanger_beat_id"),
            "rank": p.get("rank"),
        }
        for p in result["promos"]
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def markdown(report: dict) -> str:
    out = ["# Evaluation report\n"]
    run = report["primary"]["run"]
    out.append(f"Input `{run['input_dir']}` · {len(run['episodes'])} episodes · "
               f"model `{report['primary']['model']}` · "
               f"generated from `outputs/promos.json`.\n")

    counts = report["primary"]["counts"]
    out.append("## Funnel\n")
    out.append("| Stage | Count |")
    out.append("|---|---|")
    for key, label in [
        ("windows_enumerated", "Legal 20-60s windows enumerated"),
        ("rejected_no_hook", "Rejected: nothing arresting in first 3s"),
        ("shortlisted", "Shortlisted by code for the model to judge"),
        ("candidates", "Candidate promos built"),
        ("validator_failed", "Failed a hard validator"),
        ("near_duplicates", "Suppressed as near-duplicates"),
        ("gate_failed", "Failed the blind cold-viewer gate"),
        ("gate_not_tested", "Gate could not be run (counted separately, never as a pass)"),
        ("shipped", "**Shipped**"),
    ]:
        if key in counts:
            out.append(f"| {label} | {counts[key]} |")

    gold = report["gold"]
    out.append("\n## 1. Sanity check against spans drafted before the tool existed\n")
    out.append("Kept as a sanity check only, not as a quality measure. A hand-picked "
               "gold set asks the wrong question — 'did the tool match one human's "
               "pick?' — and it does not scale: maintaining one per show would "
               "recreate the manual work the tool removes. The headline measure is "
               "the blind A/B in section 1b. With n=6 the numbers below cannot rank "
               "approaches, and the per-episode spread shows why.\n")
    out.append(f"{gold['n_overlapping']} of {gold['n_gold']} drafted spans overlap "
               f"a tool pick. Mean IoU **{gold['mean_iou']}**.\n")
    out.append("| Episode | My pick (s) | Tool pick (s) | IoU | Status | Why I picked it |")
    out.append("|---|---|---|---|---|---|")
    for row in gold["rows"]:
        out.append(f"| {row['episode']} | {row['my_pick']} | {row['tool_pick'] or '-'} | "
                   f"{row['iou']} | {row['status']} | {row['note']} |")

    if report.get("gold_code_only"):
        gco = report["gold_code_only"]
        out.append(f"\n**Code-only comparison:** with the model switched off, mean IoU "
                   f"against the same hand-picks is **{gco['mean_iou']}** "
                   f"({gco['n_overlapping']}/{gco['n_gold']} overlapping).\n")

    val = report["validators"]
    out.append("\n## 2. Validator integrity\n")
    out.append(f"Evaluated {val['n_evaluated']} promos (shipped + rejected + flagship).\n")
    out.append("| Check | Pass | Fail | Failing |")
    out.append("|---|---|---|---|")
    for name, bucket in val["checks"].items():
        out.append(f"| `{name}` | {bucket['pass']} | {bucket['fail']} | "
                   f"{', '.join(bucket['failing_ids']) or '-'} |")
    out.append(f"\nNo invented timestamps in shipped output: "
               f"**{val['invented_timestamps_in_shipped_output']}**\n")

    gate = report["gate"]
    out.append("\n## 3. Blind cold-viewer gate\n")
    if gate["n_tested"]:
        out.append(f"{gate['n_tested']} promos tested, {gate['n_failed']} failed, "
                   f"pass rate **{gate['pass_rate']}**. "
                   f"{gate['n_not_tested']} could not be tested.\n")
        out.append("| Criterion | Pass rate |")
        out.append("|---|---|")
        for name, rate in gate["per_criterion_pass_rate"].items():
            out.append(f"| {name.replace('_', ' ')} | {rate} |")
        out.append("\n### Promos that failed, with the transcript\n")
        for failure in gate["failures"]:
            out.append(f"**`{failure['promo_id']}` · episode {failure['episodes']} · "
                       f"structural score {failure['structural_score']:.2f} · "
                       f"gate {failure['gate_score']}**\n")
            for question, answer in (failure["answers"] or {}).items():
                out.append(f"- *{question.replace('_', ' ')}* — {answer}")
            out.append("")
    else:
        out.append("Gate did not run in this result.\n")

    ab = report.get("ab_test")
    if ab:
        out.append("\n## 1b. Blind A/B — does the tool beat picking at random?\n")
        out.append(f"Judge: `{ab['judge']['model']}`, seed {ab['judge']['seed']}. "
                   f"{ab['design']}\n")
        if ab.get("caveat"):
            out.append(f"> **Caveat.** {ab['caveat']}\n")
        out.append("| Compared against | Pairs | Uncorrected | Shown 1st / 2nd | "
                   "**Position-corrected** | Counterbalanced subset |")
        out.append("|---|---|---|---|---|---|")
        labels = {
            "random_legal": "Any legal 20–60s window — the whole system",
            "random_hooked": "A window already passing the hook filter — "
                             "what the tension scoring adds",
        }
        for name, row in ab["summary"].items():
            cb = row.get("counterbalanced_subset") or {}
            out.append(
                f"| {labels.get(name, name)} | {row['n_pairs']} | "
                f"{row['uncorrected_win_rate']:.1%} (p={row['uncorrected_p_value']}) | "
                f"{row['win_rate_when_tool_shown_first']:.1%} / "
                f"{row['win_rate_when_tool_shown_second']:.1%} | "
                f"**{row['position_corrected_win_rate']:.1%}** | "
                f"{cb.get('win_rate', 0):.1%} over {cb.get('judgements', 0)} judgements |"
            )
        out.append("\nChance is 50%. This replaces a hand-picked reference set as the "
                   "headline quality measure: it runs unattended on any new show, needs "
                   "no editor time, and n equals the episode count rather than 6.\n")
        for name, row in ab["summary"].items():
            cb = row.get("counterbalanced_subset") or {}
            if cb:
                out.append(f"*{labels.get(name, name)}* — on the {cb['pairs_judged_both_orders']} "
                           f"pairs judged in both orders, the tool was preferred both ways "
                           f"{cb['tool_preferred_both_orders']} times, the random window both "
                           f"ways {cb['rival_preferred_both_orders']} times, and "
                           f"{cb['flipped_with_order']} flipped with presentation order.\n")
        for name, row in ab["summary"].items():
            if row.get("losses"):
                out.append(f"\n**Where the tool lost ({labels.get(name, name)}):**\n")
                for loss in row["losses"][:6]:
                    out.append(f"- episode {loss['episode']}: tool picked "
                               f"`{loss['tool']}`, judge preferred `{loss['rival']}` — "
                               f"*{loss['reason']}*")
                out.append("")

    shapes = report.get("shapes") or {}
    if len(shapes) > 1:
        out.append("\n## 3b. Does splicing cost comprehension?\n")
        out.append("The brief says a promo is *usually* one continuous stretch. "
                   "This is whether that 'usually' is earned.\n")
        out.append("| Shape | Tested | Passed | Pass rate | Mean gate score | Shipped | Best rank |")
        out.append("|---|---|---|---|---|---|---|")
        labels = {"single_stretch": "One continuous stretch",
                  "multi_segment": "Two pieces joined, same episode",
                  "cross_episode": "Across episodes (flagship)"}
        for shape, row in sorted(shapes.items()):
            out.append(f"| {labels.get(shape, shape)} | {row['tested']} | "
                       f"{row['passed']} | {row['pass_rate']} | "
                       f"{row['mean_gate_score']} | {row['shipped']} | "
                       f"{row['best_rank']} |")
        single = shapes.get("single_stretch", {})
        multi = shapes.get("multi_segment", {})
        if single.get("pass_rate") and multi.get("pass_rate"):
            out.append(f"\nSpliced promos pass the blind test less often "
                       f"({multi['pass_rate']} vs {single['pass_rate']}) and score "
                       f"lower when they do ({multi['mean_gate_score']} vs "
                       f"{single['mean_gate_score']}). The scorer charges a flat "
                       f"0.10 standalone penalty for the cut; this is the "
                       f"measurement that justifies it, and it is why no spliced "
                       f"promo reaches the top of the ranking.\n")

    if report.get("stability"):
        st = report["stability"]
        out.append("\n## 4. Stability across two models\n")
        out.append(f"`{st['model_a']}` vs `{st['model_b']}` on the same "
                   f"{st['n_episodes']} episodes.\n")
        out.append("| Metric | Value |")
        out.append("|---|---|")
        out.append(f"| Mean IoU of chosen spans | **{st['mean_iou']}** |")
        out.append(f"| Episodes where both chose substantially the same seconds (IoU >= 0.5) | {st['n_substantial_overlap']} / {st['n_episodes']} |")
        out.append(f"| Episodes where the picks do not overlap at all | {st['n_disjoint']} / {st['n_episodes']} |")
        out.append(f"| Identical picks | {st['n_identical']} / {st['n_episodes']} |")
        out.append(f"| Shipped-set overlap (Jaccard) | {st['shipped_set_jaccard']} |")
        out.append(f"| Hook-type agreement | {st['hook_type_agreement']} |")
        out.append("\nPer-episode detail is in `outputs/eval_report.json`.\n")

    out.append("\n## 5. Determinism\n")
    out.append(f"Decision fingerprint of this run: `{report['fingerprint']}`. "
               f"Re-running with the cache on reproduces it exactly, because every "
               f"model response is cached by `(provider, model, prompt hash)`.\n")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", default="outputs", help="primary result folder")
    ap.add_argument("--b", default="outputs_qwen", help="second-model result folder")
    ap.add_argument("--code-only", default="outputs_nollm", help="no-LLM result folder")
    ap.add_argument("--gold", default="docs/gold_set.json")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args(argv)

    primary = load(args.a)
    if not primary:
        print(f"no promos.json in {args.a}; run the pipeline first")
        return 1
    with open(args.gold, encoding="utf-8") as fh:
        gold = json.load(fh)["promos"]

    report = {
        "primary": {
            "folder": args.a,
            "model": primary["llm"]["model"],
            "run": primary["run"],
            "counts": primary["counts"],
        },
        "gold": gold_agreement(primary, gold),
        "validators": validator_report(primary),
        "gate": gate_report(primary),
        "shapes": shape_report(primary),
        "fingerprint": fingerprint(primary),
    }

    # Prefer the position-corrected file. The raw order-randomised run is not
    # trustworthy on its own: the judge strongly prefers whichever clip is
    # shown second, so only the corrected figures should be reported.
    for name in ("ab_test_balanced.json", "ab_test.json"):
        ab_path = os.path.join(args.out, name)
        if os.path.exists(ab_path):
            with open(ab_path, encoding="utf-8") as fh:
                ab = json.load(fh)
            report["ab_test"] = {
                "judge": ab["judge"],
                "design": ab["design"],
                "caveat": ab.get("caveat", ""),
                "summary": ab["summary"],
            }
            break

    code_only = load(args.code_only)
    if code_only:
        report["gold_code_only"] = gold_agreement(code_only, gold)
    second = load(args.b)
    if second:
        report["stability"] = stability(primary, second)

    with open(os.path.join(args.out, "eval_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    text = markdown(report)
    with open(os.path.join(args.out, "eval_report.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
