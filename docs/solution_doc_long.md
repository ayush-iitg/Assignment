# Find the Promos — Ayush Raj, IIT Guwahati

**Prototype:** `<streamlit link>` · **Repo:** `<github link>` · **Raw outputs:** `outputs/` · **Video:** `<link>`

## Why Problem 1

The brief states the bottleneck itself: an editor watches every episode and picks promo moments by hand, one show at a time, against a weekly release cadence. That is a stated, recurring cost with a checkable output, which is what makes it worth automating. I scored all three problems against the five lenses plus feasibility, measurability and distinctiveness (`docs/02_decision.md`): Problem 1 won, and the only re-weighting that flipped it was valuing raw feasibility above everything, which would have pointed to a smaller data-hygiene tool.

The risk I accepted: Problem 1 is the obvious pick, so many submissions will look alike. I chose not to differentiate on topic but on three things the default build won't have — timestamps that *cannot* be hallucinated, a promo score built from a signal already sitting in Kuku's own screenplays, and a blind comprehension test that can overrule me.

## Assumptions where the brief was silent

Full list with consequences in `docs/assumptions.md`. The ones that shaped the build:

| | Assumption |
|---|---|
| A promo is a **cut list**, not a rendered clip — `(episode, start, end)` segments, which is what "find the right start and end points" asks for | |
| 20.0s ≤ length ≤ 60.0s and "hook within 3 seconds" are **hard constraints enforced in code**, not preferences | |
| Timestamps are **relative to each episode's start** — verified: all 50 episodes begin at `00:00.00`, no series clock exists in the pack | |
| Most promos are one continuous stretch ("usually one continuous stretch"), so splicing is allowed within an episode but **exactly one** promo is built across episodes — stitching arbitrary moments across 50 episodes needs character identity this corpus can't support | |
| Episode runtimes contradict the "1–2 minute" framing — median 118.9s but **12 of 50 exceed 150s**, max 200.8s. I treated the data as truth | |
| There is **no ground truth** for "good promo", so scoring weights are hand-set and documented, never described as learned | |

## How it works

**The design decision: code owns time, the model owns judgment.** The model never sees a timestamp and never writes one. It is shown beats as `[b07] JULIANA (desperate): "..."` and answers in beat IDs; code looks each ID up in the parsed table and emits the timestamp. This is the difference between mitigating hallucinated timestamps and making them structurally impossible.

| Stage | Who | What |
|---|---|---|
| Parse | code | 50 files → **3,727 timed beats**. Reconciles labels vs timestamps vs beats and aborts if they disagree. Reports **22 hazards** in the source (8 beats out of order, 10 overlapping dialogue beats, ep 6 missing scene times, ep 24's scene header glued onto a line of dialogue). Merges **64 speaker labels → 58 characters**, stripping an honorific only when the bare name is attested elsewhere, so `LORD ASHCROFT` and `LADY ASHCROFT` stay two people. |
| Score | code | **The unfair advantage.** The screenplays label the delivery of nearly every line — `(Cold, Commanding)`, `(Screaming, Desperate)`. **1,472 of 1,487 dialogue beats** carry one, across 617 values. A hand-written lexicon (90% hit rate) turns these into an intensity curve, so the tool doesn't guess where the drama is — the script already says. It then enumerates **every legal 20–60s window on real beat boundaries (18,141)**, rejects **3,376** with nothing arresting in the first 3 seconds, and shortlists **171**. Runs in 0.8s, offline, free. |
| Select | model | 1 call per episode: choose among pre-validated windows, write the hook, cliffhanger, one-line why, and a hook type from DramaBox's published taxonomy (moral outrage / romantic tension / empathy shock / power reversal) so an editor can spread types instead of posting four of a kind. |
| Splice | code | The brief allows joining a few moments. Within one episode that's safe, so code proposes **two-piece promos** — two endorsed windows, the boring middle cut (23–77s removed), hook from the first piece and cliffhanger from the second. A pair is rejected unless it has an arc: either the speaker changes or the intensity rises. **41 of 91 candidates** were two-piece; 8 shipped. |
| Validate | code | 6 hard checks. Plus near-duplicate suppression on **visual** text between episodes ≤2 apart — dropped 37, of which 27 are a two-piece promo competing with its own continuous parent, and 10 are genuine cross-episode repeats including episodes 31 and 32, which both end on a branding iron inches from the heroine's eye. |
| Gate | model | Blind cold-viewer test: a fresh instance sees **only the clip's text** — no logline, no episode number, no surrounding beats — and must say who this is, what's at stake, what question it leaves, and whether it would keep watching. |
| Rank | code + model | Code scores so the order is reproducible; the model writes the "post this first" rationale. |

Human in the loop: the tool never posts. It converts "watch 50 episodes and scrub" into "review ~39 timestamped candidates, ranked". The ✓/✕ log in the UI is the dataset that would eventually let the weights be tuned honestly.

## Scale and cost

Measured, not projected: one 50-episode show = **127 API calls, 124,482 input + 75,321 output tokens**. At one new show per week (52 shows, 2,600 episodes/year): ~6,600 calls, ~10.4M tokens.

| | Per show | Per year at weekly cadence |
|---|---|---|
| Free tier (Groq, 1,000 req/day) | **$0.00** | **$0.00** — 127 calls/show leaves room for ~7 shows/day |
| At Gemini 2.5 Flash-Lite rates ($0.10/$0.40 per M) | ~$0.043 | ~**$2.20** |
| Deterministic stage (parse, score, splice, validate) | free, 0.8s | free |

**Tokens are not the scaling cost, and I won't pretend otherwise.** The binding constraint is the free tier's 8,000 tokens/minute, which paces a full show to ~20 minutes of wall clock; a paid tier removes that entirely. The real cost is editor attention, which is why the expensive parts of this design — the blind gate, duplicate suppression — exist to protect a short review list rather than to save tokens. With a paid key I'd raise `--top-k`, run a pairwise ranking tournament, and gate every candidate instead of one per episode.

## How I know it's good

| Check | Result |
|---|---|
| `timestamps_exist` across all 92 shipped + rejected + flagship promos | **92/92**, zero invented timestamps |
| Other 5 hard validators | **92/92** each |
| Blind cold-viewer gate | 54 tested, **7 failed**, pass rate **0.870**, 0 untested |
| Per-criterion gate pass rate | ends-unresolved **1.00** · character-identifiable **0.91** · stakes-clear **0.76** · would-keep-watching **0.65** |
| Episode coverage | 42 of 50 episodes yield at least one shipped promo; the other 8 lost theirs to the gate or to duplicate suppression |
| Determinism | two runs, same input → identical decision fingerprint `c7b809ad92b976e7` (measured, not asserted) |

**Does splicing cost comprehension?** The brief says a promo is *usually* one continuous stretch. The gate says why:

| Shape | Tested | Pass rate | Mean gate score | Best rank |
|---|---|---|---|---|
| One continuous stretch | 44 | **0.886** | 3.36 | 1 |
| Two pieces joined | 10 | **0.800** | 3.10 | 23 |

Spliced promos are measurably harder to follow. I had charged a flat 0.10 standalone penalty for the cut on instinct before building this; the measurement is what justifies it, and it is why no spliced promo reaches the top of the ranking.

**Agreement with 6 promos hand-picked before the tool existed** (`docs/gold_set.json`). All 6 overlap a tool pick; the per-episode spread is the real result:

| Episode | My pick | Code only, no model | With `gpt-oss-120b` |
|---|---|---|---|
| 1 | 39.1–78.5 | 0.599 | 0.599 |
| 2 | 47.8–86.5 | **0.000** (shipped nothing) | 0.505 |
| 13 | 54.0–112.0 | 0.350 | 0.543 |
| 15 | 47.4–78.0 | 0.221 | **0.874** |
| 24 | 32.5–81.0 | 0.258 | 0.236 |
| 31 | 131.0–160.0 | **0.697** | 0.033 |
| **mean** | | **0.354** | **0.465** |

**What I will not claim from this.** The mean favours the model, but one episode drives most of the gap: on episode 2 the code-only run shipped nothing at all, scoring a zero. Flip the one episode where code wins outright — episode 31, where the deterministic scorer picked my window almost exactly (0.697) and the model picked a different part of the episode (0.033) — and the ordering is far less clear. **With n=6, this instrument cannot rank these approaches**, and the honest conclusion is that I don't yet know how much the model is adding to moment *selection*. What I can say without hand-waving is that it earns its place on three jobs code cannot do: writing hook and cliffhanger copy an editor can scan, labelling hook type for scheduling, and running the gate that rejected 7 promos.

Expanding the gold set is therefore the first thing I would do with more time, ahead of any modelling work.

Adding the second model makes the same point from another angle. All three selectors, same gold set, same code:

| Selector | Mean IoU | Validator failures / 50 eps | Promos shipped |
|---|---|---|---|
| Code only, no model | 0.354 | 0 | 55 |
| `openai/gpt-oss-120b` | **0.465** | 0 | 47 |
| `qwen/qwen3.8-27b` | 0.359 | **1** | 49 |

The good model is ahead; the weaker one is indistinguishable from no model at all. So "add an LLM" buys something only if the model is good enough, and the deterministic baseline is what tells you which case you're in.

**Stability across the two model families** (50 episodes each): mean IoU **0.50**, identical picks on 17/50, **no overlap at all on 8/50**, shipped-set Jaccard 0.55, hook-type agreement **0.48** on a four-way label — a coin flip. A real part of this ranking is model taste rather than signal, which argues for keeping the editor in the loop and for treating cross-model disagreement as a confidence flag rather than noise.

## Where it fails

1. **It cannot see.** Shot quality, performance, pacing and music are invisible in text. I am reading sheet music and guessing at the performance. First thing I'd fix with frame-level input.
2. **The evaluation is too small to answer its own main question** — 6 hand-picked promos cannot tell me whether the model beats the lexicon at picking moments. See the table above; one episode swings the whole comparison.
3. **"Would keep watching" is the weakest gate criterion at 0.65** — clips are comprehensible but not always compelling. That gap is taste, and I have no ground truth for it.
4. **8 of 50 episodes ship no promo at all**, having lost their best candidate to the gate or to duplicate suppression. An editor wanting coverage of every episode would need the rejected list, which is why it ships.
5. **Episode 31 is the clearest single miss.** The deterministic scorer picked my window almost exactly (IoU 0.697); with the model in the loop it chose a different part of the episode (0.033) and then lost it to duplicate suppression against episode 32.
6. **The duplicate check nearly didn't work.** My first threshold (0.45 on dialogue text) could never fire: across 1,225 promo pairs, dialogue overlap peaks at 0.177. Repetition here is visual, not verbal. Switching to visual text put episodes 31/32 at 0.191, 4th of 1,225.
7. **The alias map is partly my judgment.** `ALEXANDER'S MOTHER` / `DOWAGER DUCHESS` / `MATRIARCH` are plausibly one woman and are left unmerged for want of evidence.
8. **The lexicon misses ~10% of tone tags** (369 distinct unknowns, long tail). Coverage is printed every run; below 60% the tool falls back and says so.

## AI tools used, and where they got it wrong

Claude (Anthropic) for code and drafting; Groq-hosted `openai/gpt-oss-120b` as the pipeline model, `qwen/qwen3.8-27b` as the comparison. Full log with before/after in `docs/ai_mistakes_log.md`.

**The one that matters.** Asked to pick a promo from three beats, `qwen3.8-27b` returned `{"start_beat_id": "b_03", "end_beat_id": "b_01"}` — a promo that plays backwards. Valid JSON, correct schema, confident, and physically impossible. It reproduces at every token budget I tried. `gpt-oss-120b` got the same prompt right. Had I let the model write timestamps, that output would have become `00:46.80 → 00:39.10` in a deliverable and nobody reading the PDF would have caught it. Instead the ordering validator rejects it and the pipeline falls back to the code window.

**One of mine.** My first flagship-promo assembly computed segment ends as `beat_end + 4.0` seconds. The `timestamps_exist` validator failed it immediately on times like `01:52.50` that exist nowhere in the screenplay. The model wasn't hallucinating a timestamp that time — my own code was. It now snaps to real beat edges and grows outward to reach the 20s floor.

**The one that nearly fooled me, in my own evaluation code.** When two-piece promos landed, gold-set agreement jumped from 0.46 to 0.519 and it looked like the feature had improved the tool. It hadn't: my IoU used a promo's outer envelope, so a two-piece promo running `6.8–32.0 + 70.0–89.8` was credited with covering `32–70` — exactly the seconds the splice removes. Fixed to measure against the real segment union; agreement returned to 0.465. Nothing errored and no test failed. I caught it only because a marginal feature produced a 13% gain, which didn't smell right. A metric that improves when you add code deserves more suspicion than one that doesn't.

**One diagnosis I got wrong and corrected.** I logged "`gpt-oss-20b` cannot honour JSON mode" after a clean HTTP 400. A controlled re-test showed token starvation: the model spends output tokens reasoning, and at 300 it truncated mid-object while at 900 it answered fine. The tidy story was wrong, and the real cause changed a default in the code.
