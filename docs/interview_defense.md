# Interview defense sheet

Every number here traces to a file in `outputs/`. If a question isn't covered, the honest answer is "I don't know, here's how I'd find out" — that beats improvising.

---

### 1. "Everyone picked Problem 1. Why should we read yours?"

I didn't differentiate on topic, I differentiated on three things the default build won't have. First, timestamps that can't be hallucinated — the model answers in beat IDs and code writes the time, proven 51/51 every run. Second, the score is built from the tone tags already in your screenplays, 1,472 of 1,487 dialogue beats, which is a signal specific to your data. Third, I measure standalone comprehension with a blind test instead of asserting it, and five promos failed it, transcripts included. The scoring matrix in `docs/02_decision.md` has the default approach — one prompt, whole screenplay — at 48.6 against this at 95.

### 2. "How do you know these are actually good promos? You have no media background."

I don't claim taste. I claim a measurable proxy and I report where it disagrees with me. Before writing any code I hand-picked six promos from the beat sheets; the tool overlaps five of six at mean IoU 0.46. The structural rules come straight from the brief — hook in 3s, cut unresolved, standalone — and each is a hard validator, not a vibe. What I genuinely can't measure is whether a clip converts, and I'd want your post-performance data as the real label.

### 3. "What would the model have got wrong if you'd trusted it?"

Two concrete things, one toy and one from a real run.

The toy: `qwen3.8-27b`, asked to pick a promo from three beats, returned `start_beat: b_03, end_beat: b_01` — a clip that plays backwards. Valid JSON, right schema, reproducible at every token budget I tried.

The real one, same model, episode 8 of the full run: it chose a promo spanning `00:25.00 → 00:49.60` and named as its hook a beat that starts **8.7 seconds before the promo begins**. The hook text it wrote — Juliana offering to trim Alexander's beard, him refusing with "Not yet" — is a genuine moment from that episode, fluently described. It just isn't in the clip. An editor would cut those 24 seconds and find no beard conversation in them. That one cannot be caught by reading the output, because the output is coherent and the moment is real; only checking the beat table catches it. Two validators did.

My own code made the same class of error: the first flagship assembly invented `01:52.50` by adding 4 seconds to a beat end, and `timestamps_exist` failed it on the first run.

### 4. "Your deterministic scorer scores 0.44 and the full pipeline 0.46. Why use an LLM at all?"

That's the most useful thing I found, and I put it in the doc rather than hiding it. Three selectors against the same gold set: code only 0.44, `gpt-oss-120b` 0.46, `qwen3.8-27b` 0.37. The deterministic baseline beats the weaker model outright. So the model isn't earning its keep on moment selection — the lexicon does that. It earns it on three jobs code can't do: writing hook and cliffhanger copy an editor can read at a glance, labelling hook type so you can diversify a posting schedule, and running the blind comprehension test that rejected five promos. If you told me to cut the API entirely, `--no-llm` ships a complete ranked list and I'd lose the copy and the gate, not the picks.

The uncomfortable corollary I'd rather say than have you find: a *worse* model made the product worse than no model. "Add an LLM" is a thing to measure, not a free win, and I only know which side of the line I'm on because the deterministic baseline exists to compare against.

### 4b. "How stable is this across models?"

Not very, and the number is in the report. Same 50 episodes, `gpt-oss-120b` vs `qwen3.8-27b`: mean IoU 0.54, identical picks on 18 of 50, substantial overlap on 27, and **no overlap at all on 9**. Hook-type agreement is 0.54 — barely better than a coin flip on a four-way label. A real part of this ranking is model taste rather than signal, which is an argument for keeping the editor in the loop and for using model disagreement as a confidence flag. With a paid key I'd run both and surface the promos both models choose.

### 5. "The tone tags won't exist on another show. Then what?"

Then coverage drops and the tool says so — it's printed every run and surfaced in the UI. Below 60% it falls back to a keyword lexicon over ACTION and SOUND FX text. I'd rather demo that degradation than hide it. The structural machinery — window enumeration on real beat boundaries, the hook/cliffhanger/standalone checks, the blind gate — doesn't depend on tone tags at all. If your pipeline generates these tags consistently, that's an argument for keeping them: they're free supervision.

### 6. "Walk me through the cost at our real volume."

Measured, not projected: 102 calls and 158,989 tokens for one 50-episode show. At a new show weekly that's ~5,300 calls and ~8.3M tokens a year. Free tier covers it outright. At Gemini Flash-Lite rates it's about $1.75 a year. Tokens are not the scaling cost and I'd say so in a planning meeting. The binding constraint on free tier is 8,000 tokens per minute, which paces a full show to roughly 20 minutes of wall clock; a paid key removes that. The real cost is editor attention, which is why duplicate suppression and the gate exist — to keep the review list short enough to trust.

### 7. "What breaks first if we run this across every show we make?"

The alias map. It's partly my judgment, and judgment doesn't scale across shows. I caught myself merging `LORD ASHCROFT` with `LADY ASHCROFT` — a husband and wife collapsed into one character — and fixed it with a rule that only strips an honorific when the bare name appears independently. On a new show with different naming conventions that rule will mis-fire somewhere. Second thing to break: the hand-set composite weights, which have no data behind them. That's what the editor ✓/✕ log in the UI is for.

### 8. "You only build one cross-episode promo. Why so timid?"

Because the honest version of cross-episode stitching needs reliable character identity, and this corpus has 64 speaker labels for 58 characters, with `GERALD` also appearing as `THE FORMER GROOM`. Generating dozens of cross-episode promos on that foundation produces confident nonsense. One flagship has a clear editorial job — the launch ad for the show — and it goes through the same validators and the same blind gate as everything else. In this run it passes the validators and fails the gate at 2/4, which is in the output.

### 9. "Where does the tool pick badly?"

Four places, all in the eval report. Episode 24 it scored IoU 0.24 against my pick while the code-only version scored 0.77 — the model moved to a worse window. Episode 31, my favourite pick, shipped nothing. "Would keep watching" is the weakest gate criterion at 0.71, meaning clips are comprehensible but not always compelling, and that gap is exactly the taste I can't measure. And it has no idea whether any of this looks good on screen.

### 10. "Your duplicate check — did you verify it actually fires?"

It didn't, at first, and that's the most instructive bug in the build. My initial threshold was 0.45 Jaccard on dialogue text. I measured all 1,225 promo pairs: dialogue overlap *peaks* at 0.177, so the check could never fire and never did. Repetition in a microdrama is visual, not verbal — different words, same image. On visual text, episodes 31 and 32 score 0.191, fourth highest of 1,225, and six of the top seven pairs are episodes one or two apart. So the rule is visual overlap above 0.17 within two episodes. Measuring the distribution is what turned a dead check into a working one.

### 11. "We'll give you a stronger model and a paid key. What changes?"

Four things, in order of value. Raise `--top-k` from 4 to 10 so the model judges more candidates per episode. Gate every candidate rather than one per episode. Add the pairwise ranking tournament I cut — pairwise comparison is more reliable than absolute scoring and the only reason it isn't in is the token-per-minute ceiling. And run the selector across two models and keep only promos both choose, using disagreement as a confidence signal. None of that needs a code change beyond flags.

### 12. "What would you do with another week?"

Week one, two things. Get frames: run a vision model over the first 3 seconds of each candidate and score visual impact, because that's the dimension I'm completely blind to today. And close the loop — ship the editor ✓/✕ log into a real dataset so the composite weights stop being my opinion. Those two kill the biggest weaknesses in order.

Then, if the first promos are live, replace my proxy entirely: fit the weights against actual watch-through and install rate per posted clip. At that point "is this a good promo" stops being a question I answer with a lexicon and becomes a question answered with your own performance data, which is the only version of this that's really defensible.

---

## Things I should volunteer rather than wait to be asked

- The deterministic-vs-LLM number (0.44 vs 0.46). It's unflattering to the fashionable part of the design and it's the most interesting result.
- That episode 31, my own pick, shipped nothing.
- That I corrected a wrong diagnosis in my own AI mistakes log (`gpt-oss-20b` JSON mode was token starvation, not incapability) rather than leaving the cleaner-sounding story.
- That the machine slept mid-run during the build, which is why the first full run shows network failures — and that those failures exposed a real bug: gate calls that errored were being counted as passes. Now they're reported as `not_tested` and never as a pass.

## Numbers to have memorised

| | |
|---|---|
| 50 episodes → 3,727 beats (1,754 camera / 1,487 dialogue / 372 action / 114 sfx) | |
| Tone tags: 1,472 of 1,487 dialogue beats, 617 distinct, lexicon hit rate 90% | |
| 64 speaker labels → 58 characters via 5 evidence-based merges | |
| 22 source-data hazards reported | |
| 18,141 windows → 3,139 rejected (no hook) → 172 shortlisted → 50 candidates → 39 shipped | |
| Validators 51/51 × 6 checks | |
| Gate: 44 tested, 5 failed, 0.886 pass | |
| Gold set IoU: code-only **0.44** · gpt-oss-120b **0.46** · qwen3.8-27b **0.37** | |
| Cross-model stability: mean IoU 0.54, 18/50 identical, 9/50 no overlap, hook-type agreement 0.54 | |
| 102 calls, 158,989 tokens, $0 on free tier (~$1.75/yr at Flash-Lite rates) | |
