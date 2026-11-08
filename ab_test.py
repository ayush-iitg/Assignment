#!/usr/bin/env python3
"""
Blind A/B test: does the tool's pick beat a random legal promo?

This replaces hand-picked gold sets as the headline quality measure, because a
gold set asks the wrong question. "Did the tool match one human's pick?" is not
the job. The job is "is this shortlist better than picking at random?", and that
question scales: it runs unattended on every new show, forever, with no editor
time at all.

Two comparisons per episode, because they isolate different things:

  1. tool pick  vs  RANDOM LEGAL window
     Any 20-60s span on real beat boundaries. Tests the whole selection system -
     hook filter plus tension scoring plus the model's choice.

  2. tool pick  vs  RANDOM HOOKED window
     A span that already passes the hook filter. Tests whether the tension
     scoring and the model add anything *beyond* simply requiring a strong
     opening. If the tool only wins comparison 1, the hook filter is doing all
     the work and the rest of the scoring is decoration.

Controls:
  * the judge sees two clips as plain text, never a score, never which is which
  * presentation order is randomised per pair, and position bias is measured
    rather than assumed - if "shown first" wins far more than half the time,
    the whole result is suspect and the report says so
  * the judge prompt is written for an ad-picking role, deliberately different
    from the cold-viewer comprehension gate, so the two checks stay independent
  * seeded RNG, and every response cached, so the run is reproducible

    python ab_test.py
    python ab_test.py --model qwen/qwen3.8-27b --episodes 1,2,3
"""
import os
import json
import random
import argparse
import collections

from promo.parse import parse_folder, mmss
from promo.score import (
    annotate_intensity, enumerate_windows, episode_beats, beats_in_span,
    score_window, PROMPT_KINDS, MIN_HOOK,
)
from promo.llm import LLM

SEED = 20261108

JUDGE_SYSTEM = """You choose which clips get posted as ads for a vertical drama app.

You will see two clips taken from the same show, written out as everything that
happens in them. You have never seen the show. Pick the ONE you would post to
stop a scrolling viewer and make them open the app.

Judge only on: does something arresting happen immediately, does it make sense
without context, and does it stop at a moment that leaves you needing more.
Ignore length. Ignore which one you were shown first.

You must choose. Reply with JSON only:
{
  "choice": 1 or 2,
  "reason": "<one sentence>",
  "confidence": "high" | "low"
}"""


def clip_text(beats: list[dict]) -> str:
    lines = []
    for beat in beats:
        if beat["kind"] not in PROMPT_KINDS:
            continue
        if beat["kind"] == "DIALOGUE":
            lines.append(f'{beat["speaker"]}: "{beat["text"]}"')
        else:
            lines.append(f'[{beat["kind"].lower()}] {beat["text"]}')
    return "\n".join(lines)


def overlap_fraction(a: dict, b: dict) -> float:
    lo = max(a["start"], b["start"])
    hi = min(a["end"], b["end"])
    if hi <= lo:
        return 0.0
    return (hi - lo) / min(a["end"] - a["start"], b["end"] - b["start"])


def mirror(args) -> int:
    """
    Re-run every pair in the opposite order, so position bias cancels exactly.

    The first run randomised order and then measured the bias, which turned out
    to be severe: in the random_hooked comparison the tool won 88.5% when its
    clip was shown second and 41.7% when shown first. Random allocation was
    also unlucky (12 first vs 26 second), so the favourable position was
    over-represented and the headline number was inflated.

    Presenting every pair both ways removes the problem by construction rather
    than by correction: across 2N judgements each clip sits in each position
    exactly once, so any positional preference cancels.
    """
    with open(args.mirror_of, encoding="utf-8") as fh:
        original = json.load(fh)
    trials = original["trials"]
    if args.baseline:
        trials = [t for t in trials if t["baseline"] == args.baseline]

    beats, report = parse_folder(args.input)
    annotate_intensity(beats)
    llm = LLM(provider=args.provider, model=args.model,
              max_calls=args.max_calls, raw_dir="outputs/raw_ab")
    print(f"[ab   ] mirroring {len(trials)} pairs with judge {llm.model}")

    mirrored = []
    for trial in trials:
        ep = trial["episode"]
        ep_beats = episode_beats(beats, ep)
        ts, te = (float(x) for x in trial["tool_span"].split("-"))
        rs, re_ = (float(x) for x in trial["rival_span"].split("-"))
        tool_clip = clip_text(beats_in_span(ep_beats, ts, te))
        rival_clip = clip_text(beats_in_span(ep_beats, rs, re_))
        if not tool_clip.strip() or not rival_clip.strip():
            continue

        # Opposite of the original presentation.
        tool_first = not trial["tool_shown_first"]
        first, second = (tool_clip, rival_clip) if tool_first else (rival_clip, tool_clip)
        prompt = (f"CLIP 1:\n{first}\n\n-----\n\nCLIP 2:\n{second}\n\n"
                  f"Which would you post?")
        tag = f"abmirror_{trial['baseline']}_ep{ep:03d}"
        answer = llm.complete(JUDGE_SYSTEM, prompt, tag=tag, max_tokens=700)
        if not answer or str(answer.get("choice")) not in ("1", "2"):
            continue
        picked_first = str(answer["choice"]) == "1"
        won = picked_first == tool_first
        mirrored.append({**trial, "tool_shown_first": tool_first,
                         "judge_chose_first": picked_first, "tool_won": won,
                         "reason": answer.get("reason"),
                         "confidence": answer.get("confidence"), "mirrored": True})
        print(f"[ab   ] ep{ep:>3} {trial['baseline']:14s} "
              f"{'TOOL' if won else 'rival':5s} wins (mirrored)")

    combined = collections.defaultdict(list)
    for t in trials + mirrored:
        combined[t["baseline"]].append(t)

    summary = {}
    for baseline, rows in combined.items():
        # Only pairs judged in BOTH orders count toward the balanced figure.
        by_ep = collections.defaultdict(list)
        for t in rows:
            by_ep[t["episode"]].append(t)
        both = {e: v for e, v in by_ep.items() if len(v) == 2}
        judgements = [t for v in both.values() for t in v]
        wins = sum(1 for t in judgements if t["tool_won"])
        consistent = sum(
            1 for v in both.values() if v[0]["tool_won"] == v[1]["tool_won"]
        )
        tool_both = sum(1 for v in both.values() if all(t["tool_won"] for t in v))
        rival_both = sum(1 for v in both.values() if not any(t["tool_won"] for t in v))
        summary[baseline] = {
            "pairs_judged_both_orders": len(both),
            "judgements": len(judgements),
            "position_balanced_win_rate": round(wins / len(judgements), 3) if judgements else None,
            "order_consistent_pairs": consistent,
            "order_consistency_rate": round(consistent / len(both), 3) if both else None,
            "tool_preferred_in_both_orders": tool_both,
            "rival_preferred_in_both_orders": rival_both,
            "flipped_with_order": len(both) - consistent,
        }

    out = {
        "judge": {"provider": llm.provider, "model": llm.model, "seed": SEED},
        "design": "every pair judged in BOTH presentation orders; position bias "
                  "cancels by construction",
        "summary_position_balanced": summary,
        "original_summary": original.get("summary"),
        "llm": llm.stats(),
        "trials": trials + mirrored,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print("\n=== POSITION-BALANCED RESULT ===")
    for baseline, row in summary.items():
        print(f"{baseline:14s} {row['judgements']:3d} judgements over "
              f"{row['pairs_judged_both_orders']:3d} pairs  "
              f"win rate {row['position_balanced_win_rate']:.1%}  |  "
              f"tool preferred both ways {row['tool_preferred_in_both_orders']}, "
              f"rival both ways {row['rival_preferred_in_both_orders']}, "
              f"flipped with order {row['flipped_with_order']}")
    print(f"\ncalls {llm.stats()['calls']} -> {args.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data")
    ap.add_argument("--results", default="outputs/promos.json")
    ap.add_argument("--out", default="outputs/ab_test.json")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--episodes", default=None)
    ap.add_argument("--max-calls", type=int, default=250)
    ap.add_argument(
        "--mirror-of", default=None,
        help="path to an existing ab_test.json; re-runs every pair in the "
             "OPPOSITE presentation order so position bias cancels exactly",
    )
    ap.add_argument("--baseline", default=None,
                    help="restrict to one baseline, e.g. random_hooked")
    args = ap.parse_args(argv)

    if args.mirror_of:
        return mirror(args)

    with open(args.results, encoding="utf-8") as fh:
        shipped = json.load(fh)["promos"]
    only = None
    if args.episodes:
        only = {int(x) for x in args.episodes.replace(" ", "").split(",") if x}

    beats, report = parse_folder(args.input)
    annotate_intensity(beats)
    durations = {e["episode"]: e["duration"] for e in report["episodes"]}
    rng = random.Random(SEED)
    llm = LLM(provider=args.provider, model=args.model,
              max_calls=args.max_calls, raw_dir="outputs/raw_ab")

    print(f"[ab   ] judge = {llm.provider}/{llm.model}, seed {SEED}")
    trials = []

    # One pair of comparisons per episode that produced a single-stretch promo.
    # Spliced promos are excluded: a random baseline for them is not well
    # defined, and mixing shapes would confound the result.
    for promo in shipped:
        if promo["shape"] != "single_stretch":
            continue
        ep = promo["episodes"][0]
        if only and ep not in only:
            continue

        ep_beats = episode_beats(beats, ep)
        chosen = {"start": promo["segments"][0]["start_s"],
                  "end": promo["segments"][0]["end_s"]}
        windows = [
            score_window(w, ep_beats, durations[ep])
            for w in enumerate_windows(ep_beats)
        ]
        pools = {
            "random_legal": [w for w in windows if overlap_fraction(chosen, w) < 0.4],
            "random_hooked": [
                w for w in windows
                if overlap_fraction(chosen, w) < 0.4
                and w["scores"]["hook"] >= MIN_HOOK
            ],
        }

        tool_clip = clip_text(beats_in_span(ep_beats, chosen["start"], chosen["end"]))
        if not tool_clip.strip():
            continue

        for baseline_name, pool in pools.items():
            if not pool:
                continue
            rival = rng.choice(pool)
            rival_clip = clip_text(beats_in_span(ep_beats, rival["start"], rival["end"]))
            if not rival_clip.strip():
                continue

            tool_first = rng.random() < 0.5
            first, second = (
                (tool_clip, rival_clip) if tool_first else (rival_clip, tool_clip)
            )
            prompt = (
                f"CLIP 1:\n{first}\n\n"
                f"-----\n\n"
                f"CLIP 2:\n{second}\n\n"
                f"Which would you post?"
            )
            tag = f"ab_{baseline_name}_ep{ep:03d}"
            answer = llm.complete(JUDGE_SYSTEM, prompt, tag=tag, max_tokens=700)
            if not answer or answer.get("choice") not in (1, 2, "1", "2"):
                print(f"[ab   ] ep{ep} {baseline_name}: unusable answer, skipped")
                continue

            picked_first = str(answer["choice"]) == "1"
            tool_won = picked_first == tool_first
            trials.append({
                "episode": ep,
                "baseline": baseline_name,
                "tool_span": f"{chosen['start']:.1f}-{chosen['end']:.1f}",
                "rival_span": f"{rival['start']:.1f}-{rival['end']:.1f}",
                "tool_shown_first": tool_first,
                "judge_chose_first": picked_first,
                "tool_won": tool_won,
                "confidence": answer.get("confidence"),
                "reason": answer.get("reason"),
                "tool_composite": promo["scores"]["composite"],
                "rival_composite": rival["scores"]["composite"],
            })
            print(f"[ab   ] ep{ep:>3} {baseline_name:14s} "
                  f"{'TOOL' if tool_won else 'rival':5s} wins  ({answer.get('reason','')[:60]})")

    # ---- tally -----------------------------------------------------------
    summary = {}
    for baseline in ("random_legal", "random_hooked"):
        rows = [t for t in trials if t["baseline"] == baseline]
        if not rows:
            continue
        wins = sum(1 for t in rows if t["tool_won"])
        first_wins = sum(1 for t in rows if t["judge_chose_first"])
        summary[baseline] = {
            "n": len(rows),
            "tool_wins": wins,
            "tool_win_rate": round(wins / len(rows), 3),
            "position_bias_first_chosen_rate": round(first_wins / len(rows), 3),
            "high_confidence_n": sum(1 for t in rows if t.get("confidence") == "high"),
            "tool_win_rate_high_confidence": round(
                sum(1 for t in rows if t["tool_won"] and t.get("confidence") == "high")
                / max(1, sum(1 for t in rows if t.get("confidence") == "high")), 3
            ),
            "losses": [
                {"episode": t["episode"], "tool": t["tool_span"],
                 "rival": t["rival_span"], "reason": t["reason"]}
                for t in rows if not t["tool_won"]
            ],
        }

    out = {
        "judge": {"provider": llm.provider, "model": llm.model, "seed": SEED},
        "design": "tool pick vs a random legal window from the same episode; "
                  "blind, order randomised, judge never sees a score",
        "summary": summary,
        "llm": llm.stats(),
        "trials": trials,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    print("\n=== RESULT ===")
    for baseline, row in summary.items():
        print(f"{baseline:14s} n={row['n']:3d}  tool wins {row['tool_wins']:3d}  "
              f"= {row['tool_win_rate']:.1%}   "
              f"(position bias: first chosen {row['position_bias_first_chosen_rate']:.1%})")
    print(f"\ncalls {llm.stats()['calls']} | cached {llm.stats()['cache_hits']} "
          f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
