"""
Orchestration. One function, `run()`, called identically by run.py (CLI) and
app.py (web UI), so the interface can never drift from the tool.

This module is also the ONLY place a timestamp is ever written into output:
beat IDs come back from the model, and `_segment()` looks up the real times.
"""
from __future__ import annotations

import os
import json
import time

from .parse import parse_folder, mmss
from .score import (
    annotate_intensity, shortlist_episode, tension_curve, beats_in_span,
    episode_beats, multi_segment_candidates, MIN_LEN, MAX_LEN,
    COMPOSITE_WEIGHTS,
)
from .validate import validate_promo, suppress_duplicates
from . import stages
from .llm import LLM


def _segment(order: int, episode: int, start: float, end: float) -> dict:
    return {
        "order": order,
        "episode": episode,
        "start": mmss(start),
        "end": mmss(end),
        "start_s": round(start, 2),
        "end_s": round(end, 2),
        "duration_s": round(end - start, 2),
    }


def _clamp_to_legal(start: float, end: float, anchors: list[dict]) -> tuple[float, float]:
    """
    Keep a model-chosen span inside 20-60s without inventing a boundary.

    If the span is too long we pull the end back to the latest real beat edge
    that fits; if too short we push it out to the earliest edge that reaches
    20s. Every resulting value is still a beat edge from the screenplay.
    """
    edges = sorted({round(b["end"], 2) for b in anchors})
    length = end - start
    if length > MAX_LEN:
        fits = [e for e in edges if e - start <= MAX_LEN and e > start]
        if fits:
            end = max(fits)
    elif length < MIN_LEN:
        fits = [e for e in edges if e - start >= MIN_LEN]
        if fits:
            end = min(fits)
    return start, end


def _templated_copy(span: list[dict], start: float, end: float) -> dict:
    """
    Hook/cliffhanger text without a model, for --no-llm runs.

    Picks the most intense beat near each edge and quotes it. Blunt on
    purpose: it should be obviously mechanical, so nobody mistakes the
    offline mode for the real thing.

    The windows must be measured from the promo's own start, not from the
    first beat in the span: `beats_in_span` includes beats that *overlap* the
    span, so a beat can begin before the promo does. Using the span's first
    beat put the hook outside the promo for 8 of 50 code-only promos, which
    the hook_within_3s validator correctly rejected.
    """
    if not span:
        return {"hook": "", "cliffhanger": "", "hook_type": "", "why_it_works": ""}
    opening = [b for b in span if start - 1e-6 <= b["start"] <= start + 3.0]
    tail = [b for b in span if b["start"] <= end + 1e-6 and b["end"] >= end - 5.0]
    opening = opening or [min(span, key=lambda b: abs(b["start"] - start))]
    tail = tail or [max(span, key=lambda b: b["end"])]
    hook_beat = max(opening, key=lambda b: b["intensity"])
    cliff_beat = max(tail, key=lambda b: b["intensity"])

    def describe(beat: dict) -> str:
        if beat["kind"] == "DIALOGUE":
            tone = f" ({', '.join(beat['tone'])})" if beat["tone"] else ""
            return f'{beat["speaker"]}{tone}: "{beat["text"]}"'
        return beat["text"]

    return {
        "hook": describe(hook_beat),
        "cliffhanger": describe(cliff_beat),
        "hook_type": "",
        "why_it_works": "[--no-llm mode] highest-intensity opening and an unresolved final beat.",
        "hook_beat_id": hook_beat["id"],
        "cliffhanger_beat_id": cliff_beat["id"],
    }


def run(
    input_dir: str,
    out_dir: str = "outputs",
    *,
    provider: str | None = None,
    model: str | None = None,
    use_llm: bool = True,
    use_cache: bool = True,
    episodes: list[int] | None = None,
    max_calls: int = 400,
    top_k: int = 6,
    promos_per_episode: int = 1,
    multi_per_episode: int = 1,
    run_gate: bool = True,
    run_flagship: bool = True,
    log=print,
) -> dict:
    """Parse -> score -> select -> validate -> gate -> rank -> emit."""
    t0 = time.time()
    os.makedirs(out_dir, exist_ok=True)
    raw_dir = os.path.join(out_dir, "raw")

    # ---- 1. parse --------------------------------------------------------
    beats, parse_report = parse_folder(input_dir, episodes=episodes)
    coverage = annotate_intensity(beats)
    parse_report["intensity_coverage"] = coverage
    beats_by_id = {b["id"]: b for b in beats}
    durations = {e["episode"]: e["duration"] for e in parse_report["episodes"]}
    ep_list = sorted(durations)

    log(f"[parse]  {parse_report['n_files']} files -> {parse_report['n_beats']} beats "
        f"{parse_report['kinds']}")
    log(f"[parse]  tone-tag coverage {parse_report['tone_tag_coverage']:.3f}, "
        f"lexicon hit rate {coverage['lexicon_hit_rate']:.3f}")
    log(f"[parse]  {parse_report['speaker_labels_raw']} raw speaker labels -> "
        f"{parse_report['characters_canonical']} characters "
        f"({len(parse_report['alias_map'])} merges)")
    log(f"[parse]  {parse_report['n_hazards']} hazards found and reported")

    # ---- 2. shortlist (code only) ---------------------------------------
    shortlists, window_stats = {}, []
    for ep in ep_list:
        sl, stats = shortlist_episode(beats, ep, durations[ep], top_k=top_k)
        shortlists[ep] = sl
        window_stats.append(stats)
    total_windows = sum(s["windows_enumerated"] for s in window_stats)
    total_shortlisted = sum(s["shortlisted"] for s in window_stats)
    total_nohook = sum(s["rejected_no_hook"] for s in window_stats)
    log(f"[score]  {total_windows} windows enumerated, {total_nohook} rejected for no hook, "
        f"{total_shortlisted} shortlisted")

    # ---- 3. select -------------------------------------------------------
    llm = None
    if use_llm:
        llm = LLM(provider=provider, model=model, max_calls=max_calls,
                  use_cache=use_cache, raw_dir=raw_dir)
        log(f"[llm  ]  provider={llm.provider} model={llm.model} "
            f"cache={'on' if use_cache else 'off'} cap={max_calls}")

    candidates: list[dict] = []
    for ep in ep_list:
        shortlist = shortlists[ep]
        if not shortlist:
            continue
        ep_beats = episode_beats(beats, ep)
        picks = []

        if llm:
            chosen = stages.select_promo(llm, beats, ep, shortlist)
            if chosen:
                picks.append(chosen)
            else:
                log(f"[llm  ]  episode {ep}: selector returned nothing, using code pick")
        if not picks:
            picks.append({"window": shortlist[0], "start_beat_id": None,
                          "end_beat_id": None, "no_llm": True})

        # Optionally keep a second, non-overlapping code pick per episode.
        for extra in shortlist[1:promos_per_episode]:
            picks.append({"window": extra, "start_beat_id": None,
                          "end_beat_id": None, "no_llm": True})

        for n, pick in enumerate(picks):
            promo = _build_promo(pick, ep, ep_beats, beats_by_id, n)
            if promo:
                candidates.append(promo)

        # Two-piece promos from this episode, if any pair joins cleanly.
        if multi_per_episode:
            pairs = multi_segment_candidates(beats, ep, durations[ep], shortlist)
            for n, window in enumerate(pairs[:multi_per_episode], 1):
                promo = _build_multi_promo(window, ep, ep_beats, beats_by_id, n)
                if promo:
                    candidates.append(promo)

    n_multi = sum(1 for c in candidates if c["shape"] == "multi_segment")
    log(f"[build]  {len(candidates)} candidate promos "
        f"({len(candidates) - n_multi} single stretch, {n_multi} two-piece)")

    # ---- 4. validate -----------------------------------------------------
    valid, invalid = [], []
    for promo in candidates:
        validate_promo(promo, beats_by_id)
        (valid if promo["valid"] else invalid).append(promo)
    checks = ("timestamps_exist", "length_ok", "order_ok", "hook_within_3s",
              "hook_inside_promo", "cliffhanger_inside_promo")
    for check in checks:
        passed = sum(1 for p in candidates if p["validators"].get(check))
        log(f"[valid]  {check}: {passed}/{len(candidates)}")
    for promo in invalid:
        promo["rejected_reason"] = "validator: " + "; ".join(promo["validator_failures"])

    # ---- 5. de-duplicate -------------------------------------------------
    valid, duplicates = suppress_duplicates(valid, beats_by_id)
    log(f"[valid]  near-duplicates dropped: {len(duplicates)}")

    # ---- 6. cold-viewer gate --------------------------------------------
    gated, gate_failed = [], []
    gate_errors = 0
    if llm and run_gate:
        for promo in valid:
            result = stages.cold_viewer_gate(llm, promo, beats_by_id)
            promo["cold_viewer"] = result
            if result is None:
                # The gate could not be run (network, quota, unparseable
                # answer). That is NOT a pass. Shipping it as one would mean
                # the quality claim quietly covers promos that were never
                # tested - which happened on the first full run, where 5
                # network failures sailed through as passes.
                gate_errors += 1
                promo["cold_viewer"] = {
                    "verdict": "not_tested",
                    "score": "n/a",
                    "score_n": None,
                    "answers": {},
                    "error": "gate call failed after retries",
                }
                gated.append(promo)
            elif result["verdict"] == "fail":
                promo["rejected_reason"] = (
                    f"cold-viewer gate {result['score']}: "
                    + (result["answers"].get("what_is_at_stake") or "")
                )
                gate_failed.append(promo)
            else:
                gated.append(promo)
        tested = len(gated) + len(gate_failed) - gate_errors
        log(f"[gate ]  cold-viewer: {len(gated) - gate_errors} pass / "
            f"{len(gate_failed)} fail / {gate_errors} NOT TESTED "
            f"(of {tested + gate_errors} candidates)")
    else:
        gated = valid
        for promo in gated:
            promo["cold_viewer"] = None

    # ---- 7. rank ---------------------------------------------------------
    gated.sort(key=lambda p: -p["scores"]["composite"])
    rationale = None
    if llm and gated:
        rationale = stages.rank_rationale(llm, gated[:12])
        if rationale:
            order = [pid for pid in (rationale.get("order") or [])]
            by_id = {p["promo_id"]: p for p in gated}
            if order and all(pid in by_id for pid in order[:len(gated)]):
                reordered = [by_id[pid] for pid in order if pid in by_id]
                reordered += [p for p in gated if p["promo_id"] not in set(order)]
                gated = reordered
            for promo in gated:
                promo["rank_rationale"] = (rationale.get("rationale") or {}).get(
                    promo["promo_id"], ""
                )
    for n, promo in enumerate(gated, 1):
        promo["rank"] = n

    # ---- 8. flagship -----------------------------------------------------
    flagship = None
    if llm and run_flagship and len(gated) >= 3:
        best = [{"episode": p["episodes"][0], "source_beat_ids": p["source_beat_ids"]}
                for p in gated[:10]]
        raw = stages.flagship_promo(llm, beats, best)
        if raw:
            flagship = _build_flagship(raw, beats, beats_by_id)
            if flagship:
                validate_promo(flagship, beats_by_id)
                if run_gate:
                    flagship["cold_viewer"] = stages.cold_viewer_gate(
                        llm, flagship, beats_by_id
                    )
                log(f"[flag ]  cross-episode flagship: "
                    f"{len(flagship['segments'])} segments, "
                    f"{flagship['total_duration_s']:.1f}s, valid={flagship['valid']}")

    # ---- 9. emit ---------------------------------------------------------
    rejected = invalid + duplicates + gate_failed
    curves = {ep: tension_curve(beats, ep) for ep in ep_list}
    stats = llm.stats() if llm else {"provider": "none", "model": "none (--no-llm)",
                                     "calls": 0, "cache_hits": 0, "tokens_in": 0,
                                     "tokens_out": 0, "failures": 0}
    result = {
        "run": {
            "input_dir": input_dir,
            "episodes": ep_list,
            "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_s": round(time.time() - t0, 1),
            "use_llm": bool(llm),
            "composite_weights": COMPOSITE_WEIGHTS,
            "promo_length_bounds": [MIN_LEN, MAX_LEN],
        },
        "llm": stats,
        "counts": {
            "windows_enumerated": total_windows,
            "rejected_no_hook": total_nohook,
            "shortlisted": total_shortlisted,
            "candidates": len(candidates),
            "candidates_single_stretch": len(candidates) - n_multi,
            "candidates_two_piece": n_multi,
            "validator_failed": len(invalid),
            "near_duplicates": len(duplicates),
            "gate_failed": len(gate_failed),
            "gate_not_tested": gate_errors,
            "shipped": len(gated),
        },
        "promos": gated,
        "flagship": flagship,
        "rejected": rejected,
        "rank_rationale": rationale,
        "parse_report": parse_report,
        "window_stats": window_stats,
        "tension_curves": curves,
    }

    _write_outputs(result, out_dir)
    log(f"[out  ]  {len(gated)} promos -> {out_dir}/promos.json, {out_dir}/promos.md")
    log(f"[done ]  {result['run']['elapsed_s']}s | calls {stats['calls']} "
        f"| cache hits {stats['cache_hits']} "
        f"| tokens {stats['tokens_in']}/{stats['tokens_out']}")
    return result


# ---------------------------------------------------------------------------
# Promo construction
# ---------------------------------------------------------------------------

def _build_multi_promo(window: dict, episode: int, ep_beats: list[dict],
                       beats_by_id: dict, n: int) -> dict | None:
    """
    Build a two-piece promo from one episode.

    Code-only by design: the pieces come from windows the model already
    endorsed individually, and the join rule is deterministic. Asking the
    model to approve the splice as well would double the call count for a
    judgment the hook and cliffhanger scores already encode.
    """
    pieces = window["pieces"]
    segments, source_ids, span = [], [], []
    for order, piece in enumerate(pieces, 1):
        segments.append(_segment(order, episode, piece["start"], piece["end"]))
        chunk = beats_in_span(ep_beats, piece["start"], piece["end"])
        span.extend(chunk)
        source_ids.extend(b["id"] for b in chunk)
    if not span:
        return None

    copy = _templated_copy(
        beats_in_span(ep_beats, pieces[0]["start"], pieces[0]["end"]),
        pieces[0]["start"], pieces[0]["end"],
    )
    tail = _templated_copy(
        beats_in_span(ep_beats, pieces[1]["start"], pieces[1]["end"]),
        pieces[1]["start"], pieces[1]["end"],
    )
    total = sum(s["duration_s"] for s in segments)
    return {
        "promo_id": f"p_{episode:03d}_m{n}",
        "shape": "multi_segment",
        "episodes": [episode],
        "segments": segments,
        "total_duration_s": round(total, 2),
        "gap_removed_s": window["gap_removed_s"],
        "hook_is_cold_open": False,
        "hook": copy["hook"],
        "hook_type": "",
        "cliffhanger": tail["cliffhanger"],
        "why_it_works": (
            f"Two moments from episode {episode} joined, with "
            f"{window['gap_removed_s']:.0f}s of setup cut out: opens on the "
            f"strongest beat and lands on an unresolved one."
        ),
        "standalone_risk": "The viewer must bridge one cut unaided.",
        "hook_beat_id": window["hook_beat_id"],
        "cliffhanger_beat_id": window["cliffhanger_beat_id"],
        "source_beat_ids": source_ids,
        "scores": window["scores"],
        "standalone_detail": window.get("standalone_detail"),
        "selected_by": "code",
    }


def _build_promo(pick: dict, episode: int, ep_beats: list[dict],
                 beats_by_id: dict, n: int) -> dict | None:
    """Turn a selector answer (beat IDs) into a promo (timestamps)."""
    window = pick["window"]
    start_beat = beats_by_id.get(pick.get("start_beat_id") or "")
    end_beat = beats_by_id.get(pick.get("end_beat_id") or "")
    start = start_beat["start"] if start_beat else window["start"]
    end = end_beat["end"] if end_beat else window["end"]
    if end <= start:
        # The model handed back a reversed span (observed on qwen3.8-27b, see
        # ai_mistakes_log #1). Fall back to the code window rather than
        # silently swapping, and let the validator record what happened.
        start, end = window["start"], window["end"]

    anchors = [b for b in ep_beats if b["kind"] in stages.PROMPT_KINDS]
    start, end = _clamp_to_legal(start, end, anchors)
    span = [b for b in beats_in_span(ep_beats, start, end)]
    if not span:
        return None

    source_ids = [b["id"] for b in span]
    hook_id = pick.get("hook_beat_id")
    cliff_id = pick.get("cliffhanger_beat_id")
    copy = {k: pick.get(k, "") for k in ("hook", "cliffhanger", "hook_type",
                                         "why_it_works", "standalone_risk")}
    if pick.get("no_llm") or not copy["hook"]:
        templated = _templated_copy(span, start, end)
        copy.update({k: v for k, v in templated.items() if k in copy})
        hook_id = hook_id or templated.get("hook_beat_id")
        cliff_id = cliff_id or templated.get("cliffhanger_beat_id")

    # Guard: a hook outside the first 3s is a validator failure, so prefer the
    # code's hook beat when the model named one too late.
    if hook_id and beats_by_id.get(hook_id):
        if beats_by_id[hook_id]["start"] - start > 3.0:
            hook_id = window.get("hook_beat_id") or hook_id
    hook_id = hook_id or window.get("hook_beat_id")
    cliff_id = cliff_id or window.get("cliffhanger_beat_id")

    return {
        "promo_id": f"p_{episode:03d}_{chr(ord('a') + n)}",
        "shape": "single_stretch",
        "episodes": [episode],
        "segments": [_segment(1, episode, start, end)],
        "total_duration_s": round(end - start, 2),
        "hook_is_cold_open": False,
        "hook": copy["hook"],
        "hook_type": copy["hook_type"],
        "cliffhanger": copy["cliffhanger"],
        "why_it_works": copy["why_it_works"],
        "standalone_risk": copy.get("standalone_risk", ""),
        "hook_beat_id": hook_id,
        "cliffhanger_beat_id": cliff_id,
        "source_beat_ids": source_ids,
        "scores": window["scores"],
        "standalone_detail": window.get("standalone_detail"),
        "selected_by": "code" if pick.get("no_llm") else "llm",
    }


def _build_flagship(raw: dict, beats: list[dict], beats_by_id: dict) -> dict | None:
    """
    Assemble the cross-episode promo from the beat IDs the model chose.

    Each picked beat becomes a short segment: that beat plus whatever follows
    it, up to about 5 seconds. The end MUST land on a real beat edge. A first
    version used `beat["end"] + 4.0`, which produced times like `01:52.50`
    that exist nowhere in the screenplay - caught by the timestamps_exist
    validator on the first run, which is precisely the failure the validator
    exists to prevent. The model wasn't the one hallucinating a timestamp
    that time; my own assembly code was.
    """
    chosen = [beats_by_id[b] for b in raw["resolved_beat_ids"] if b in beats_by_id]
    if len(chosen) < 2:
        return None

    # Hook first (may come from anywhere); the rest in episode/time order.
    hook = chosen[0]
    rest = sorted(chosen[1:], key=lambda b: (b["episode"], b["start"]))
    ordered = [hook] + rest

    by_episode: dict[int, list[dict]] = {}
    for beat in beats:
        by_episode.setdefault(beat["episode"], []).append(beat)

    segments, total, source_ids = [], 0.0, []
    for i, beat in enumerate(ordered, 1):
        budget = max(0.0, MAX_LEN - total)
        if budget < 1.0:
            break
        reach = beat["start"] + min(beat["end"] - beat["start"] + 5.0, budget)
        # The latest real beat edge in this episode that fits the budget.
        edges = [
            b["end"] for b in by_episode.get(beat["episode"], [])
            if b["start"] >= beat["start"] - 1e-6 and b["end"] <= reach + 1e-6
        ]
        span_end = max(edges) if edges else beat["end"]
        if span_end - beat["start"] < 1.0 or total + (span_end - beat["start"]) > MAX_LEN:
            continue
        segments.append(_segment(i, beat["episode"], beat["start"], span_end))
        total += span_end - beat["start"]
        source_ids.append(beat["id"])

    # The model picks moments; code decides how much around each moment to
    # keep. If the chosen beats are short the promo lands under the 20s floor
    # (observed: 3 beats totalling 16.5s), so grow the segments outward to
    # the next real beat edges until it is legal. Always edges, never
    # arithmetic, so timestamps_exist still holds.
    guard = 0
    while total < MIN_LEN and guard < 40:
        guard += 1
        best_growth = None
        for seg in segments:
            later = sorted(
                b["end"] for b in by_episode.get(seg["episode"], [])
                if b["end"] > seg["end_s"] + 1e-6
            )
            if not later:
                continue
            gain = later[0] - seg["end_s"]
            if total + gain > MAX_LEN:
                continue
            if best_growth is None or gain < best_growth[1]:
                best_growth = (seg, gain, later[0])
        if best_growth is None:
            break
        seg, gain, new_end = best_growth
        seg["end_s"] = round(new_end, 2)
        seg["end"] = mmss(new_end)
        seg["duration_s"] = round(new_end - seg["start_s"], 2)
        total += gain

    if not segments or total < MIN_LEN:
        return None
    total = round(sum(s["duration_s"] for s in segments), 2)
    for n, seg in enumerate(segments, 1):
        seg["order"] = n

    return {
        "promo_id": "p_flagship",
        "shape": "cross_episode",
        "episodes": sorted({s["episode"] for s in segments}),
        "segments": segments,
        "total_duration_s": round(total, 2),
        "hook_is_cold_open": True,
        "hook": raw.get("hook", ""),
        "hook_type": (raw.get("hook_type") or "").lower(),
        "cliffhanger": raw.get("cliffhanger", ""),
        "why_it_works": raw.get("why_it_works", ""),
        "narrative": raw.get("narrative", ""),
        "hook_beat_id": source_ids[0],
        "cliffhanger_beat_id": source_ids[-1],
        "source_beat_ids": source_ids,
        "scores": {"hook": 0.0, "tension": 0.0, "cliffhanger": 0.0,
                   "standalone": 0.0, "composite": 0.0},
        "selected_by": "llm",
    }


# ---------------------------------------------------------------------------
# Output files
# ---------------------------------------------------------------------------

def _write_outputs(result: dict, out_dir: str) -> None:
    def dump(name: str, obj) -> None:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, ensure_ascii=False)

    slim = {k: v for k, v in result.items() if k != "tension_curves"}
    dump("promos.json", slim)
    dump("rejected_promos.json", result["rejected"])
    dump("parse_report.json", result["parse_report"])
    dump("tension_curves.json", result["tension_curves"])
    dump("run_manifest.json", {"run": result["run"], "llm": result["llm"],
                               "counts": result["counts"]})

    with open(os.path.join(out_dir, "promos.md"), "w", encoding="utf-8") as fh:
        fh.write(_markdown(result))


def _markdown(result: dict) -> str:
    run, counts, stats = result["run"], result["counts"], result["llm"]
    out = ["# Promo candidates\n"]
    out.append(f"Input `{run['input_dir']}` · {len(run['episodes'])} episodes · "
               f"{stats['model']} · {run['elapsed_s']}s · "
               f"{stats['calls']} calls ({stats['cache_hits']} cached)\n")
    out.append(f"{counts['windows_enumerated']} windows enumerated → "
               f"{counts['shortlisted']} shortlisted → {counts['candidates']} candidates → "
               f"**{counts['shipped']} shipped** "
               f"({counts['validator_failed']} failed validators, "
               f"{counts['near_duplicates']} near-duplicates, "
               f"{counts['gate_failed']} failed the cold-viewer gate)\n")

    if result.get("rank_rationale", {}) and result["rank_rationale"].get("post_first_reason"):
        out.append(f"**Post first:** `{result['rank_rationale'].get('post_first','')}` — "
                   f"{result['rank_rationale']['post_first_reason']}\n")

    out.append("\n| # | Ep | Segments | Len | Hook type | Hook | Cliffhanger | "
               "Why it works | Blind viewer | Score |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for promo in result["promos"]:
        segs = "<br>".join(
            f"`{s['start']} → {s['end']}`" + (f" (ep {s['episode']})"
                                              if len(promo["episodes"]) > 1 else "")
            for s in promo["segments"]
        )
        gate = promo.get("cold_viewer") or {}
        out.append(
            f"| {promo['rank']} | {','.join(map(str, promo['episodes']))} | {segs} | "
            f"{promo['total_duration_s']:.1f}s | {promo.get('hook_type','')} | "
            f"{_clean(promo.get('hook'))} | {_clean(promo.get('cliffhanger'))} | "
            f"{_clean(promo.get('why_it_works'))} | {gate.get('score','n/a')} | "
            f"{promo['scores']['composite']:.2f} |"
        )

    flagship = result.get("flagship")
    if flagship:
        out.append("\n## Flagship cross-episode promo\n")
        out.append(f"**{flagship['total_duration_s']:.1f}s across episodes "
                   f"{flagship['episodes']}** — {_clean(flagship.get('narrative'))}\n")
        out.append("| # | Episode | Segment | Len |")
        out.append("|---|---|---|---|")
        for s in flagship["segments"]:
            out.append(f"| {s['order']} | {s['episode']} | "
                       f"`{s['start']} → {s['end']}` | {s['duration_s']:.1f}s |")
        out.append(f"\nHook: {_clean(flagship.get('hook'))}  ")
        out.append(f"Cliffhanger: {_clean(flagship.get('cliffhanger'))}")

    if result["rejected"]:
        out.append("\n## Rejected, with reasons\n")
        out.append("| Promo | Episodes | Score | Why it was dropped |")
        out.append("|---|---|---|---|")
        for promo in result["rejected"][:40]:
            out.append(
                f"| `{promo['promo_id']}` | {','.join(map(str, promo['episodes']))} | "
                f"{promo['scores']['composite']:.2f} | "
                f"{_clean(promo.get('rejected_reason'))} |"
            )
    return "\n".join(out) + "\n"


def _clean(text) -> str:
    return (text or "").replace("|", "/").replace("\n", " ").strip()
