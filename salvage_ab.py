"""
Combine the two A/B passes into a fully counterbalanced result.

Every pair was judged twice: once with the tool's clip shown first, once with
it shown second. That matters because the judge turned out to strongly prefer
whichever clip it read second (88.5% there against 41.7% shown first on one
baseline). Presenting both orders makes position cancel arithmetically instead
of needing a correction.

On the unit of analysis. 38 pairs x 2 orders = 76 judgements, but the two
judgements of a pair are not independent: they concern the same two clips. So
the headline figure is computed per PAIR, not per judgement:

  * tool preferred in BOTH orders        -> a clean win
  * rival preferred in BOTH orders       -> a clean loss
  * preference flips with order          -> no signal, the judge was swayed
                                            by position rather than content

The binomial test therefore runs on the decisive pairs only. The
judgement-level rate is reported too, but flagged, because treating correlated
judgements as independent would overstate significance.

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
    if n == 0:
        return 1.0
    probs = [math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(n + 1)]
    return min(1.0, sum(x for x in probs if x <= probs[k] * 1.0000001))


def main() -> int:
    original = json.load(open(SEED_FILE, encoding="utf-8"))
    trials = original["trials"]
    index = {(t["episode"], t["baseline"]): t for t in trials}

    mirrored = []
    for path in sorted(glob.glob(RAW_GLOB)):
        rec = json.load(open(path, encoding="utf-8"))
        m = re.match(r"abmirror_(?P<base>[a-z_]+)_ep(?P<ep>\d+)", rec["tag"])
        if not m:
            continue
        seed = index.get((int(m.group("ep")), m.group("base")))
        if not seed:
            continue
        try:
            choice = str(json.loads(rec["response_text"])["choice"])
        except Exception:
            continue
        if choice not in ("1", "2"):
            continue
        tool_first = not seed["tool_shown_first"]
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
        mrows = {t["episode"]: t for t in mirrored if t["baseline"] == baseline}
        if not rows:
            continue

        pairs = []
        for t in rows:
            other = mrows.get(t["episode"])
            if other:
                pairs.append((t, other))

        tool_both = sum(1 for a, b in pairs if a["tool_won"] and b["tool_won"])
        rival_both = sum(1 for a, b in pairs if not a["tool_won"] and not b["tool_won"])
        flipped = len(pairs) - tool_both - rival_both
        decisive = tool_both + rival_both

        judgements = [x for p in pairs for x in p]
        jwins = sum(1 for x in judgements if x["tool_won"])

        first = [x for x in judgements if x["tool_shown_first"]]
        second = [x for x in judgements if not x["tool_shown_first"]]

        summary[baseline] = {
            "pairs": len(pairs),
            "judgements": len(judgements),
            "counterbalanced": len(pairs) == len(rows),

            # headline, pair-level
            "tool_preferred_both_orders": tool_both,
            "rival_preferred_both_orders": rival_both,
            "flipped_with_order": flipped,
            "decisive_pairs": decisive,
            "win_rate_decisive_pairs": round(tool_both / decisive, 3) if decisive else None,
            "p_value_decisive_pairs": round(two_sided_binomial(tool_both, decisive), 5),
            "order_consistency": round(decisive / len(pairs), 3) if pairs else None,

            # secondary, judgement-level (correlated within pair)
            "win_rate_all_judgements": round(jwins / len(judgements), 3) if judgements else None,
            "win_rate_when_shown_first": round(
                sum(1 for x in first if x["tool_won"]) / len(first), 3) if first else None,
            "win_rate_when_shown_second": round(
                sum(1 for x in second if x["tool_won"]) / len(second), 3) if second else None,

            "losses_both_orders": [
                {"episode": a["episode"], "tool": a["tool_span"],
                 "rival": a["rival_span"], "reason": a["reason"]}
                for a, b in pairs if not a["tool_won"] and not b["tool_won"]
            ],
        }

    out = {
        "judge": original["judge"],
        "design": (
            "Each pick compared against a random legal window from the same "
            "episode: same length rules, same real beat boundaries, not "
            "selected. The judge sees two clips as plain text, never a score "
            "and never which is which. Every pair was judged twice, once in "
            "each presentation order, so position bias cancels by "
            "construction rather than by correction."
        ),
        "unit_of_analysis": (
            "The pair, not the judgement. The two judgements of a pair concern "
            "the same two clips and are not independent, so the binomial test "
            "runs on pairs that gave the same answer in both orders. Pairs "
            "that flipped with order carry no signal about content."
        ),
        "summary": summary,
        "n_mirrored_recovered": len(mirrored),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    for baseline, r in summary.items():
        print(f"== {baseline}   (fully counterbalanced: {r['counterbalanced']})")
        print(f"   {r['pairs']} pairs, {r['judgements']} judgements")
        print(f"   tool won both orders   {r['tool_preferred_both_orders']}")
        print(f"   rival won both orders  {r['rival_preferred_both_orders']}")
        print(f"   flipped with order     {r['flipped_with_order']}"
              f"   (order consistency {r['order_consistency']:.1%})")
        print(f"   HEADLINE: {r['win_rate_decisive_pairs']:.1%} of "
              f"{r['decisive_pairs']} decisive pairs, p={r['p_value_decisive_pairs']}")
        print(f"   judgement-level (correlated): {r['win_rate_all_judgements']:.1%}"
              f"   1st {r['win_rate_when_shown_first']:.1%} /"
              f" 2nd {r['win_rate_when_shown_second']:.1%}")
    print(f"\nrecovered {out['n_mirrored_recovered']} mirrored judgements -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
