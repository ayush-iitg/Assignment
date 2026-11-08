"""
Combine the order-randomised A/B run with however many mirrored judgements
completed, and report both a position-corrected estimate and a strictly
counterbalanced subset.

The mirrored run was cut short by the free tier's 8,000 tokens/minute ceiling
(28 of 76 pairs judged in the second order). Rather than throw away a partial
counterbalanced design, this script reports:

  1. the position-corrected estimate over the FULL sample - the mean of the
     win rate when the tool was shown first and when it was shown second,
     which removes the effect of unequal allocation
  2. the strictly counterbalanced result over the SUBSET judged both ways,
     where position cancels by construction and order-flips are visible

Run: python salvage_ab.py
"""
import re
import json
import glob
import math
import collections

SEED_FILE = "outputs/ab_test.json"
RAW_GLOB = "outputs/raw_ab/*abmirror*.json"
OUT = "outputs/ab_test_balanced.json"


def two_sided_binomial(k: int, n: int, p: float = 0.5) -> float:
    probs = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in probs if x <= probs[k] * 1.0000001))


def main() -> int:
    original = json.load(open(SEED_FILE, encoding="utf-8"))
    trials = original["trials"]
    index = {(t["episode"], t["baseline"]): t for t in trials}

    # Recover mirrored judgements from the unedited raw records.
    mirrored = []
    for path in sorted(glob.glob(RAW_GLOB)):
        rec = json.load(open(path, encoding="utf-8"))
        m = re.match(r"abmirror_(?P<base>[a-z_]+)_ep(?P<ep>\d+)", rec["tag"])
        if not m:
            continue
        key = (int(m.group("ep")), m.group("base"))
        seed = index.get(key)
        if not seed:
            continue
        try:
            choice = str(json.loads(rec["response_text"])["choice"])
        except Exception:
            continue
        if choice not in ("1", "2"):
            continue
        tool_first = not seed["tool_shown_first"]      # mirror flips the order
        mirrored.append({
            **seed,
            "tool_shown_first": tool_first,
            "judge_chose_first": choice == "1",
            "tool_won": (choice == "1") == tool_first,
            "mirrored": True,
        })

    summary = {}
    for baseline in ("random_legal", "random_hooked"):
        rows = [t for t in trials if t["baseline"] == baseline]
        mrows = [t for t in mirrored if t["baseline"] == baseline]
        if not rows:
            continue

        first = [t for t in rows if t["tool_shown_first"]]
        second = [t for t in rows if not t["tool_shown_first"]]
        wf = sum(1 for t in first if t["tool_won"])
        ws = sum(1 for t in second if t["tool_won"])
        raw_wins = sum(1 for t in rows if t["tool_won"])

        rate_first = wf / len(first) if first else None
        rate_second = ws / len(second) if second else None
        corrected = (
            round((rate_first + rate_second) / 2, 3)
            if rate_first is not None and rate_second is not None else None
        )

        # Strictly counterbalanced subset: pairs judged in both orders.
        paired = {}
        for t in rows:
            paired.setdefault(t["episode"], {})["a"] = t
        for t in mrows:
            if t["episode"] in paired:
                paired[t["episode"]]["b"] = t
        both = {e: v for e, v in paired.items() if "b" in v}
        judgements = [x for v in both.values() for x in v.values()]
        cb_wins = sum(1 for x in judgements if x["tool_won"])
        tool_both = sum(1 for v in both.values()
                        if v["a"]["tool_won"] and v["b"]["tool_won"])
        rival_both = sum(1 for v in both.values()
                         if not v["a"]["tool_won"] and not v["b"]["tool_won"])
        flipped = len(both) - tool_both - rival_both

        summary[baseline] = {
            "n_pairs": len(rows),
            "uncorrected_win_rate": round(raw_wins / len(rows), 3),
            "uncorrected_p_value": round(two_sided_binomial(raw_wins, len(rows)), 5),
            "win_rate_when_tool_shown_first": round(rate_first, 3) if rate_first is not None else None,
            "win_rate_when_tool_shown_second": round(rate_second, 3) if rate_second is not None else None,
            "allocation_first_vs_second": [len(first), len(second)],
            "position_corrected_win_rate": corrected,
            "counterbalanced_subset": {
                "pairs_judged_both_orders": len(both),
                "judgements": len(judgements),
                "win_rate": round(cb_wins / len(judgements), 3) if judgements else None,
                "tool_preferred_both_orders": tool_both,
                "rival_preferred_both_orders": rival_both,
                "flipped_with_order": flipped,
            },
            "losses": [
                {"episode": t["episode"], "tool": t["tool_span"],
                 "rival": t["rival_span"], "reason": t["reason"]}
                for t in rows if not t["tool_won"]
            ],
        }

    out = {
        "judge": original["judge"],
        "design": (
            "Each pick compared against a random legal window from the same "
            "episode. Blind: the judge sees two clips as text, never a score, "
            "never which is which. Order randomised per pair, then as many "
            "pairs as the free-tier token budget allowed were re-judged in "
            "the opposite order."
        ),
        "caveat": (
            "The judge has a strong preference for whichever clip is shown "
            "second, so the uncorrected win rate is not trustworthy on its "
            "own. The position-corrected figure averages the two "
            "position-conditional rates; the counterbalanced subset removes "
            "position by construction. Report those, not the raw number."
        ),
        "summary": summary,
        "n_mirrored_recovered": len(mirrored),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    for baseline, row in summary.items():
        cb = row["counterbalanced_subset"]
        print(f"== {baseline}")
        print(f"   uncorrected            {row['uncorrected_win_rate']:.1%} "
              f"(n={row['n_pairs']}, p={row['uncorrected_p_value']})")
        print(f"   shown first / second   {row['win_rate_when_tool_shown_first']:.1%}"
              f" / {row['win_rate_when_tool_shown_second']:.1%}"
              f"   allocation {row['allocation_first_vs_second']}")
        print(f"   POSITION-CORRECTED     {row['position_corrected_win_rate']:.1%}")
        print(f"   counterbalanced subset {cb['win_rate']:.1%} over {cb['judgements']} "
              f"judgements / {cb['pairs_judged_both_orders']} pairs "
              f"(tool both ways {cb['tool_preferred_both_orders']}, "
              f"rival both ways {cb['rival_preferred_both_orders']}, "
              f"flipped {cb['flipped_with_order']})")
    print(f"\nrecovered {out['n_mirrored_recovered']} mirrored judgements -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
