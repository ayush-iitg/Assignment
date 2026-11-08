# Evaluation report

Input `data` · 50 episodes · model `qwen/qwen3.8-27b` · generated from `outputs/promos.json`.

## Funnel

| Stage | Count |
|---|---|
| Legal 20-60s windows enumerated | 18141 |
| Rejected: nothing arresting in first 3s | 3139 |
| Shortlisted by code for the model to judge | 172 |
| Candidate promos built | 50 |
| Failed a hard validator | 1 |
| Suppressed as near-duplicates | 4 |
| Failed the blind cold-viewer gate | 8 |
| Gate could not be run (counted separately, never as a pass) | 0 |
| **Shipped** | 37 |

## 1. Agreement with promos I picked by hand before building the tool

6 of 6 hand-picked promos overlap a tool pick. Mean IoU **0.366**.

| Episode | My pick (s) | Tool pick (s) | IoU | Status | Why I picked it |
|---|---|---|---|---|---|
| 1 | 39.1-78.5 | 13.5-50.0 | 0.168 | rejected: near-duplicate of p_002_a (episodes [2], 1 apart, visual overlap 0.18  | Whole premise with zero prior context: a bride at the altar learns her sister is marrying her fiance, and the family knew. |
| 2 | 47.8-86.5 | 69.4-107.4 | 0.287 | shipped | Humiliation turned into defiance; works as a standalone clapback with no setup needed. |
| 13 | 54.0-112.0 | 80.5-112.0 | 0.543 | shipped | Wordless physical ordeal, then an object reveal that poses a question without answering it. |
| 15 | 47.4-78.0 | 16.4-62.0 | 0.237 | shipped | Violence opens it, and it cuts before the fight resolves - the viewer needs the outcome. |
| 24 | 32.5-81.0 | 66.0-89.8 | 0.262 | shipped | Physical violence stops the scroll, then a secret-identity tease replaces resolution. |
| 31 | 131.0-160.0 | 131.0-151.2 | 0.697 | shipped | Pure peril needing no setup, cut mid-threat. Flagged at audit time as the weakest of my picks for standalone comprehension - a stranger is never told her name. |

**Code-only comparison:** with the model switched off, mean IoU against the same hand-picks is **0.44** (5/6 overlapping).


## 2. Validator integrity

Evaluated 51 promos (shipped + rejected + flagship).

| Check | Pass | Fail | Failing |
|---|---|---|---|
| `timestamps_exist` | 51 | 0 | - |
| `length_ok` | 51 | 0 | - |
| `order_ok` | 51 | 0 | - |
| `hook_within_3s` | 50 | 1 | p_008_a |
| `hook_inside_promo` | 50 | 1 | p_008_a |
| `cliffhanger_inside_promo` | 51 | 0 | - |

No invented timestamps in shipped output: **True**


## 3. Blind cold-viewer gate

45 promos tested, 8 failed, pass rate **0.822**. 0 could not be tested.

| Criterion | Pass rate |
|---|---|
| character identifiable | 0.778 |
| stakes clear | 0.644 |
| ends unresolved | 1.0 |
| would watch | 0.911 |

### Promos that failed, with the transcript

**`p_047_a` · episode [47] · structural score 0.91 · gate 1/4**

- *who is the main character* — Juliana (the clip names her, but does not explain who she is or her role beyond being in charge of the house)
- *what is at stake* — Catherine's survival and status; she is being forced to work as a servant after being exposed as an impostor who tried to destroy Juliana
- *what question are you left with* — Who is this 'impostor' Catherine, what did she actually do to Juliana, and what is the nature of the house 'Ashbourne'?
- *would you keep watching* — maybe, the dialogue is dramatic but I have no context for who these people are or why this matters

**`p_023_a` · episode [23] · structural score 0.85 · gate 1/4**

- *who is the main character* — The clip features Prudence and Juliana, but never identifies a single main character or provides context for who they are.
- *what is at stake* — A character referred to as 'the Duchess' is dying from arsenic poisoning, and the characters are attempting to save her while someone is approaching the door.
- *what question are you left with* — Who is the Duchess, who is the person coming through the door, and what is the relationship between Prudence and Juliana?
- *would you keep watching* — no, the clip provides zero context on who these people are or why I should care about the Duchess.

**`p_020_a` · episode [20] · structural score 0.85 · gate 2/4**

- *who is the main character* — The clip features two distinct groups: Seamus and Juliana (who are never given last names or titles beyond 'viscount's daughter'), and Catherine and Rupert. No single main character is explicitly identified as the protagonist, though Juliana and Catherine are the primary speakers.
- *what is at stake* — There are two conflicting stakes: Juliana is fighting to remain a healer for her village despite her noble birth, while Catherine is plotting to take control of Ashbury estate after the death of the 'old Duchess'.
- *what question are you left with* — Who is the 'old Duchess' and how does Juliana's role as a healer connect to Catherine's plot to take over Ashbury?
- *would you keep watching* — maybe, because the connection between the two scenes is unclear and I need to know if Juliana is the target of Catherine's scheme

**`p_030_a` · episode [30] · structural score 0.83 · gate 1/4**

- *who is the main character* — The clip features Rupert, Catherine, and an Elder Nobleman, but never identifies a single main character or protagonist.
- *what is at stake* — Juliana is being reclassified from a prisoner to a witch to face execution by hanging, which the characters view as a solution to a town's problem.
- *what question are you left with* — Who is Juliana, why is she being accused of witchcraft, and what is the specific conflict that makes her execution a 'perfect solution'?
- *would you keep watching* — no, the clip is just a static conversation with no context, action, or visual interest to hook a new viewer.

**`p_007_a` · episode [7] · structural score 0.81 · gate 2/4**

- *who is the main character* — The clip features a man named Gerald and an unnamed Aristocratic Woman, but the central figure driving the action is the 'Scarred Bearded Man' who is never named.
- *what is at stake* — Unclear from the clip. It appears to be a social confrontation or threat, but the specific danger or relationship dynamics are not explained.
- *what question are you left with* — Who is the Scarred Bearded Man, why is he threatening Gerald, and what is the relationship between these characters?
- *would you keep watching* — maybe, because the sudden shift in power and the mysterious stranger create immediate tension, though the context is missing.

**`p_011_a` · episode [11] · structural score 0.70 · gate 2/4**

- *who is the main character* — The clip features Alexander, Juliana, Gerald, and a Constable. It does not identify a single main character, nor does it provide context for who they are to each other beyond their names.
- *what is at stake* — Unclear from the clip. There is a conflict involving a coat and a gold chain, and Alexander mentions a choice between ending something and destroying a life, but the specific nature of the threat or the relationship between the characters is not explained.
- *what question are you left with* — Who is 'her' that Alexander is protecting, and what is the significance of the gold chain in the coat that causes Juliana such terror?
- *would you keep watching* — maybe, because the sudden shift from philosophical dialogue to a physical search and a character's terrified reaction creates a jarring mystery that demands an explanation.

**`p_017_a` · episode [17] · structural score 0.64 · gate 2/4**

- *who is the main character* — Alexander (named in dialogue), described as having large, weathered palms; Juliana (named in dialogue), described as having trembling, bandaged hands
- *what is at stake* — Unclear from the clip. The dialogue implies a recent physical threat or attack by 'those men' and a promise of future protection, but the specific nature of the conflict or danger is not explained.
- *what question are you left with* — Who are 'those men' and what happened to cause Juliana's injuries?
- *would you keep watching* — maybe, because the romantic gesture is intense but I have no context for the plot or characters

**`p_050_a` · episode [50] · structural score 0.61 · gate 2/4**

- *who is the main character* — The clip features Catherine and Father Thomas, but never explicitly states which is the 'main' character; it also introduces Agnes. The clip does not provide a title or context to determine a single protagonist.
- *what is at stake* — The immediate conflict is the discovery of a forbidden sexual relationship between a priest and a woman by a third party (Agnes). The broader stakes (consequences of this discovery) are not explained.
- *what question are you left with* — What will Agnes do with this information, and what are the consequences for Catherine and Father Thomas?
- *would you keep watching* — maybe, because the cliffhanger of the discovery creates immediate tension, but I have no context for why this matters or who these people are.


## 4. Stability across two models

`qwen/qwen3.8-27b` vs `openai/gpt-oss-120b` on the same 50 episodes.

| Metric | Value |
|---|---|
| Mean IoU of chosen spans | **0.539** |
| Episodes where both chose substantially the same seconds (IoU >= 0.5) | 27 / 50 |
| Episodes where the picks do not overlap at all | 9 / 50 |
| Identical picks | 18 / 50 |
| Shipped-set overlap (Jaccard) | 0.617 |
| Hook-type agreement | 0.54 |

Per-episode detail is in `outputs/eval_report.json`.


## 5. Determinism

Decision fingerprint of this run: `35e12363edf2b4c8`. Re-running with the cache on reproduces it exactly, because every model response is cached by `(provider, model, prompt hash)`.

