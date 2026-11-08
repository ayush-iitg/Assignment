# Evaluation report

Input `data` · 50 episodes · model `openai/gpt-oss-120b` · generated from `outputs/promos.json`.

## Funnel

| Stage | Count |
|---|---|
| Legal 20-60s windows enumerated | 18141 |
| Rejected: nothing arresting in first 3s | 3376 |
| Shortlisted by code for the model to judge | 171 |
| Candidate promos built | 91 |
| Failed a hard validator | 0 |
| Suppressed as near-duplicates | 37 |
| Failed the blind cold-viewer gate | 7 |
| Gate could not be run (counted separately, never as a pass) | 0 |
| **Shipped** | 47 |

## 1. Validator integrity

Evaluated 92 promos (shipped + rejected + flagship).

| Check | Pass | Fail | Failing |
|---|---|---|---|
| `timestamps_exist` | 92 | 0 | - |
| `length_ok` | 92 | 0 | - |
| `order_ok` | 92 | 0 | - |
| `hook_within_3s` | 92 | 0 | - |
| `hook_inside_promo` | 92 | 0 | - |
| `cliffhanger_inside_promo` | 92 | 0 | - |

No invented timestamps in shipped output: **True**


## 2. Blind A/B: does the tool beat picking at random?

Judge: `openai/gpt-oss-120b`, seed 20261108. Each pick compared against a random legal window from the same episode. Blind: the judge sees two clips as text, never a score, never which is which. Order randomised per pair, then as many pairs as the free-tier token budget allowed were re-judged in the opposite order.

> **Caveat.** The judge has a strong preference for whichever clip is shown second, so the uncorrected win rate is not trustworthy on its own. The position-corrected figure averages the two position-conditional rates; the counterbalanced subset removes position by construction. Report those, not the raw number.

| Compared against | Pairs | Uncorrected | Shown 1st / 2nd | **Position-corrected** | Counterbalanced subset |
|---|---|---|---|---|---|
| Any legal 20–60s window — the whole system | 38 | 76.3% (p=0.00166) | 66.7% / 85.0% | **75.8%** | 78.6% over 28 judgements |
| A window already passing the hook filter — what the tension scoring adds | 38 | 73.7% (p=0.0051) | 41.7% / 88.5% | **65.1%** | 64.3% over 28 judgements |

Chance is 50%. This replaces a hand-picked reference set as the headline quality measure: it runs unattended on any new show, needs no editor time, and n equals the episode count rather than 6.

*Any legal 20–60s window — the whole system* — on the 14 pairs judged in both orders, the tool was preferred both ways 10 times, the random window both ways 2 times, and 2 flipped with presentation order.

*A window already passing the hook filter — what the tension scoring adds* — on the 14 pairs judged in both orders, the tool was preferred both ways 8 times, the random window both ways 4 times, and 2 flipped with presentation order.


**Where the tool lost (Any legal 20–60s window — the whole system):**

- episode 28: tool picked `113.3-136.7`, judge preferred `52.8-91.0` — *The violent snatching of a family heirloom and the threat of poison create immediate tension and end on a hook.*
- episode 4: tool picked `113.0-134.5`, judge preferred `79.2-119.0` — *It builds tension with a secretive ceremony then ends on a shocking outburst, leaving a clear hook.*
- episode 9: tool picked `6.3-54.0`, judge preferred `86.6-111.2` — *The mysterious rumor about a war veteran who looks like the dead Duke ends on a tense, unanswered "Impossible" hook.*
- episode 18: tool picked `73.5-106.8`, judge preferred `38.0-68.0` — *The immediate danger of a collapsing ceiling and the urgent conflict over the ledger create a clear hook that compels viewers to want to see what happens next.*
- episode 7: tool picked `21.0-69.5`, judge preferred `65.6-93.8` — *The scarred man’s ominous arrival and Gerald’s sudden dread create an immediate hook that leaves viewers wanting to know what happens next.*
- episode 37: tool picked `104.0-148.0`, judge preferred `47.0-95.5` — *It reveals a shocking public execution tied to a wedding and ends on Juliana’s defiant gesture, creating immediate intrigue and a cliffhanger.*


**Where the tool lost (A window already passing the hook filter — what the tension scoring adds):**

- episode 28: tool picked `113.3-136.7`, judge preferred `54.0-103.7` — *The sudden violent grab of the locket and the reveal of a hidden identity create immediate tension and end on a mysterious hook.*
- episode 1: tool picked `46.8-70.4`, judge preferred `7.2-29.8` — *The sudden, visual revelation at the altar creates immediate tension and ends on a shocking hook, enticing viewers to learn more.*
- episode 47: tool picked `78.8-108.5`, judge preferred `43.0-78.5` — *The sudden command to throw Catherine out creates immediate tension and a cliffhanger that begs for resolution.*
- episode 4: tool picked `113.0-134.5`, judge preferred `79.2-116.8` — *The mysterious bearded man’s protective promise and the sudden outburst create immediate tension and a hook that begs for continuation.*
- episode 9: tool picked `6.3-54.0`, judge preferred `43.8-77.5` — *It ends on a mysterious warning that hints at larger conflict, leaving the viewer craving more.*
- episode 30: tool picked `120.0-143.5`, judge preferred `44.8-72.8` — *The creaking doors, urgent dialogue about a hidden prisoner, and a tense reveal of a legal trap end on a cliffhanger that hooks viewers*


## 3. Blind cold-viewer gate

54 promos tested, 7 failed, pass rate **0.87**. 0 could not be tested.

| Criterion | Pass rate |
|---|---|
| character identifiable | 0.907 |
| stakes clear | 0.759 |
| ends unresolved | 1.0 |
| would watch | 0.648 |

### Promos that failed, with the transcript

**`p_011_a` · episode [11] · structural score 0.87 · gate 2/4**

- *who is the main character* — Juliana (the clip focuses on her, though it never labels her as the main character)
- *what is at stake* — Juliana's remaining possessions and possibly her reputation/freedom are threatened by accusations of theft and the prospect of violence
- *what question are you left with* — Will the constable find incriminating evidence in the coat, and will anyone be harmed by the threatened "one blow"?
- *would you keep watching* — maybe, the dialogue hints at high tension but the situation is unclear

**`p_003_a` · episode [3] · structural score 0.84 · gate 2/4**

- *who is the main character* — the bearded stranger (MYSTERIOUS BEARDED MAN) – the clip never gives a proper name
- *what is at stake* — Juliana's safety/freedom as the bearded man defends her against the guard and family interference
- *what question are you left with* — Will the bearded man be allowed to protect Juliana despite the noble matriarch's objection?
- *would you keep watching* — maybe, because the action is intriguing but the context is unclear

**`p_034_a` · episode [34] · structural score 0.83 · gate 1/4**

- *who is the main character* — The clip does not name a main character; several characters appear (Judge, Lord, Townsman, Old Woman, Juliana)
- *what is at stake* — unclear from the clip
- *what question are you left with* — Is Juliana’s mixture a cure or a poison?
- *would you keep watching* — maybe, because the dispute hints at larger consequences

**`p_041_a` · episode [41] · structural score 0.73 · gate 1/4**

- *who is the main character* — The clip does not name a single main character; several characters (Juliana, Catherine, a blond nobleman, and a priest) speak.
- *what is at stake* — Unclear from the clip; there is mention of the Ashburgh title and a violent attack on a cathedral, but the exact stakes are not explained.
- *what question are you left with* — Will the Ashburgh title be claimed and who will survive the explosion?
- *would you keep watching* — maybe, the violent spectacle is intriguing but the context is vague

**`p_006_m1` · episode [6] · structural score 0.65 · gate 2/4**

- *who is the main character* — Juliana (named in the clip)
- *what is at stake* — unclear from the clip
- *what question are you left with* — Will Juliana continue onward despite her loss, or what will happen next?
- *would you keep watching* — maybe, the mood is intriguing but the stakes are vague

**`p_040_a` · episode [40] · structural score 0.61 · gate 2/4**

- *who is the main character* — The clip does not name a main character; several characters appear (Elder Nobleman, Lady Harrington, Blond Nobleman, Catherine, Rupert)
- *what is at stake* — unclear from the clip
- *what question are you left with* — What will happen to the witch and how will Catherine and Rupert’s scheme affect the new Duke and Duchess?
- *would you keep watching* — maybe, the political intrigue and conspiratorial smiles hint at larger drama

**`p_049_m1` · episode [49] · structural score 0.59 · gate 2/4**

- *who is the main character* — Catherine (named in the clip)
- *what is at stake* — The outcome of an unresolved hearing and the council's decision about a woman referred to as "her," with Catherine trying to delay the hearing and learn the council's knowledge
- *what question are you left with* — What is the hearing about, who is "her," and how will the council ultimately decide?
- *would you keep watching* — maybe, the dialogue hints at intrigue but lacks context


## 4. Does splicing cost comprehension?

The brief says a promo is *usually* one continuous stretch. This is whether that 'usually' is earned.

| Shape | Tested | Passed | Pass rate | Mean gate score | Shipped | Best rank |
|---|---|---|---|---|---|---|
| Two pieces joined, same episode | 10 | 8 | 0.8 | 3.1 | 8 | 23 |
| One continuous stretch | 44 | 39 | 0.886 | 3.36 | 39 | 1 |

Spliced promos pass the blind test less often (0.8 vs 0.886) and score lower when they do (3.1 vs 3.36). The scorer charges a flat 0.10 standalone penalty for the cut; this is the measurement that justifies it, and it is why no spliced promo reaches the top of the ranking.


## 5. Stability across two models

`openai/gpt-oss-120b` vs `qwen/qwen3.8-27b` on the same 50 episodes.

| Metric | Value |
|---|---|
| Mean IoU of chosen spans | **0.5** |
| Episodes where both chose substantially the same seconds (IoU >= 0.5) | 23 / 50 |
| Episodes where the picks do not overlap at all | 8 / 50 |
| Identical picks | 17 / 50 |
| Shipped-set overlap (Jaccard) | 0.548 |
| Hook-type agreement | 0.48 |

Per-episode detail is in `outputs/eval_report.json`.


## 6. Determinism

Decision fingerprint of this run: `c7b809ad92b976e7`. Re-running with the cache on reproduces it exactly, because every model response is cached by `(provider, model, prompt hash)`.

