# Why Problem 1, and how I scoped it

Written before any code existed. I sketched four genuinely different approaches to each of the three problems, scored them, then attacked my own winner.

## 1. Scoring

Weights sum to 100: the five published lenses, plus four practical constraints that decide whether a thing actually ships — `feas` can I build it, `meas` can I measure whether it's good, `demo` does it survive being re-run on an unseen input, `safe` how easily it overpromises.

`frame` 15 · `scale` 15 · `qual` 15 · `proto` 20 · `comms` 5 · `feas` 10 · `meas` 5 · `demo` 5 · `dist` 7 · `safe` 3. Scores 1–5, normalised.

| Approach | Total |
|---|---|
| **P1 — deterministic windows + LLM picks by beat ID + blind comprehension gate** | **95.0** |
| P1 — blind comprehension gate with pairwise ranking, candidates from anywhere | 87.0 |
| P1 — enumerate legal windows, LLM selects by beat ID | 85.0 |
| P3 — character-label drift detector (64 labels for ~58 characters) | 84.0 |
| P3 — screenplay timeline validator (out-of-order beats, overlapping dialogue) | 83.2 |
| P1 — tone-tag tension curve, ranking fully in code, LLM writes only the copy | 82.4 |
| P2 — evidence triage: messy story → case file + missing-proof checklist | 76.0 |
| P2 — rule-based intake flows with reviewed templates, LLM out of the legal path | 75.2 |
| P2 — RAG over bare act text with a citation verifier | 75.0 |
| P3 — episode runtime drift check (12 of 50 episodes exceed the format) | 73.8 |
| P2 — opponent role-play simulator + refusal/escalation classifier | 70.6 |
| **P1 — paste the whole screenplay into one prompt (the default submission)** | **48.6** |

The gap that mattered: 95.0 against **48.6** for the obvious build. Same problem, same input, same brief — the difference is entirely in where the work is placed.

## 2. Sensitivity — which weights flip the winner?

| Re-weighting | Winner |
|---|---|
| Base | **the chosen approach (95.0)** |
| Ship-at-all-costs (feasibility 30, prototype 30) | the chosen approach (90.0) |
| Distinctiveness ×3.5 | the chosen approach (95.8) |
| Problem-choice ×2.3 | the chosen approach (95.8) |
| Quality-checking ×2 | the chosen approach (95.7) |
| **Feasibility 40 (panic mode)** | **P3 character-label drift (87.7)** |

One reweighting flips it. If I couldn't ship a working promo pipeline, the right move was the label-drift detector — measurable, buildable in ~90 minutes, and already evidenced in `docs/00_audit.md`. I wrote that trigger down in advance rather than deciding under pressure.

## 3. Red team on my own choice

| Attack | Answer |
|---|---|
| **Everyone picks Problem 1.** It has the input pack, and the brief warns that similar submissions from one campus get reviewed closely. | True, and it is the main risk. I'm not betting on the problem for distinctiveness — I'm betting on three things the default build won't have: timestamps that *cannot* be hallucinated because the model only ever emits beat IDs; a promo score built from tone tags already sitting in Kuku's own screenplays; and a blind comprehension test that can and does overrule me. |
| **You have no media background. Why is your taste worth anything?** | It isn't, and I don't claim it. I claim a measurable proxy — hook inside 3 seconds, rising tension, a cut at an unresolved beat — each enforced as a hard validator, and a blind A/B against a random legal window to show the scoring beats chance. Where the tool disagrees with me, I report the disagreement rather than tuning until it agrees. |
| **A promo is visual; a screenplay isn't video.** | Agreed, and it's limitation #1 in the solution doc. The brief scopes this to finding moments and timestamps, with no editing. Shot quality and performance are invisible to me, and that's the first thing I'd fix with frame-level input. |
| **Problem 2 would stand out more.** | It would differentiate on topic, but I'd be writing legal content with no legal background, no input pack, and a rule against inventing sections. Higher chance of overpromising, lower chance of a prototype that survives being re-run live. |
| **Problem 3 lets you pick something you can win at.** | I found four real, evidenced candidates in the data — label drift, repeated cliffhanger framing, runtime drift, timeline defects. None of them clears the brief's own bar of mattering *more* than Problems 1 and 2. The brief states promo-picking is a manual bottleneck against a weekly cadence; that's a stronger claim than anything I could establish about label hygiene. Saying so is more honest than dressing up a QA chore as a business problem. |

## 4. The decision

**Problem 1.** A deterministic parser and scorer do the finding; the model makes only the judgment call and never touches arithmetic; a blind comprehension test gates the output; a human editor makes the final call and never sees an unranked list.

Declared in advance and still true: if the API or quota died, `--no-llm` had to produce a complete ranked list from code alone. It does, in 0.8 seconds, and that fallback turned into one of the more useful measurements in the project.
