# AI mistakes log

Every item here is something an AI model (or an AI coding assistant) actually got wrong during this build, with the before/after. Required by the brief ("tell us which tools you used and one place where they got it wrong"), but kept as a running log because the failures drove design decisions.

---

## 1. Groq `qwen/qwen3.8-27b` returned a promo that runs backwards
**When:** provider smoke test, before any pipeline code existed.
**Prompt (abridged):** three beats — `b_01` "Because he is marrying me." · `b_02` "No..." · `b_03` "You knew this before I walked through those doors!" — "pick the best promo start and end."

**Before (verbatim model output):**
```json
{"start_beat_id": "b_03", "end_beat_id": "b_01", "hook": "You knew this before I walked through those doors!"}
```
The promo starts at beat 3 and ends at beat 1. A clip that plays from 00:46 to 00:39. Confidently formatted, valid JSON, schema-correct, and physically impossible.

For comparison, `openai/gpt-oss-120b` on the identical prompt returned `b_01 → b_03`, which is correct.

**After (design change, not a prompt tweak):** `validate.py` rejects any promo where `start_beat.start >= end_beat.start`, and the ordering is re-checked after beat IDs are resolved to timestamps. The pipeline counts and reports these rejections rather than silently reordering them, so the eval report shows how often each model does this.

**Why it matters:** this is the exact failure my architecture was built to contain. If I had let the model write timestamps directly, this output would have produced a plausible-looking `00:46.80 → 00:39.10` in the final deliverable and nobody reading the PDF would have caught it.

---

## 2. A JSON-mode failure I initially diagnosed wrong — and the correction
**When:** provider smoke test, then re-tested deliberately.

**What I saw first:** `openai/gpt-oss-20b` with `response_format: {"type":"json_object"}` →
```
HTTP 400 {"error":{"message":"Failed to validate JSON. Please adjust your prompt.
See 'failed_generation' for more details.","code":"json_validate_failed","failed_generation":""}}
```
while `gpt-oss-120b` and `qwen3.8-27b` answered the identical request fine.

**What I wrote in this log:** "`gpt-oss-20b` cannot honour JSON mode." Tidy story, wrong conclusion.

**What a controlled re-test actually showed** — same prompt, same model, only `max_tokens` changed:

| Model | max_tokens | Result |
|---|---|---|
| `openai/gpt-oss-20b` | 300 | HTTP 400 `json_validate_failed` |
| `openai/gpt-oss-20b` | 900 | HTTP 200 `{"start_beat_id":"b_02",...}` |
| `qwen/qwen3.8-27b` | 300 | HTTP 200 (but reversed — see #1) |
| `qwen/qwen3.8-27b` | 900 | HTTP 200 (reversed again, reproducible) |

**The real cause:** `gpt-oss-20b` spends output tokens on reasoning before it emits the object. At 300 tokens it gets truncated mid-JSON, and the API reports the truncated-and-invalid result as a validation failure with an empty `failed_generation` — which reads like a capability gap but is a budget gap. A 400 error code pointed me at "fix your prompt"; the fix was "give it room to finish".

**After:** two changes, both kept.
1. `max_tokens` defaults to 900, not 300, because the cheap models here are reasoning models.
2. The JSON fallback path stays anyway: on `json_validate_failed` the client retries in plain-text mode and extracts the outermost `{...}`. Defensible as defence-in-depth rather than as a fix for this specific bug.

**Why it matters:** I had a plausible, well-formatted explanation and no evidence for it. The honest version is less flattering to the model and more useful to anyone running it. It also changed a real default in the code, which the wrong diagnosis would not have.

---

## 3. Claude (this assistant) mis-parsed the screenplay format on the first attempt
**When:** Phase 0 audit, `scripts/audit2.py`.
**Before:** my first beat-type census reported only three kinds of beat — `CAMERA` 1,754, `ACTION` 372, `SOUND FX` 114, total 2,240 — while separately counting 3,727 timestamp lines. I had written the label regex as `^\*\*([A-Z /&_'-]+):?\*\*$`, which silently excluded every dialogue label because real labels carry parenthetical tone tags: `**JULIANA (Whispering, Tearful):**`. 1,487 dialogue beats, 40% of the corpus, were invisible, and the script reported no error.

**After:** `scripts/audit3.py` matches `^\*\*(.+?):\*\*$` and classifies by whether the base name is a technical keyword. That change is what surfaced the tone tags — 1,478 of 1,487 dialogue beats carry one, 620 distinct values — which became the central signal of the whole solution.

**Why it matters:** the mistake was mine, caught only because I cross-checked two counts that should have matched (2,240 labels vs 3,727 timestamps). The lesson went straight into the design: the parser emits a reconciliation report (labels seen vs timestamps seen vs beats built) and the pipeline refuses to run if they disagree.

---

## 4. Python/urllib SSL failure sent me toward the wrong fix
**When:** first API call attempt.
**Before:** `urllib.request` → `SSL: CERTIFICATE_VERIFY_FAILED`. The obvious-looking fix, and the one an assistant will often propose, is `ssl._create_unverified_context()` — i.e. turn off certificate verification to make the error go away.
**After:** used `requests`, which ships with `certifi`, and it worked first try. No verification disabled.
**Why it matters:** a small thing, but disabling TLS verification in a tool that carries an API key is exactly the kind of "fix" that gets copied into production.

---

## 5. My hand-written character alias table merged two different people
**When:** M1, first run of `promo/parse.py` on all 50 episodes.

**Before:** I wrote the alias rule as "strip the honorific, then merge". It produced 7 merge groups, including these two:
```
ASHCROFT    <- {'LORD ASHCROFT': 8,   'LADY ASHCROFT': 6}
HARRINGTON  <- {'LADY HARRINGTON': 7, 'LORD HARRINGTON': 4}
```
A lord and a lady of the same house are a husband and wife. The parser had just collapsed two characters into one, which would have let a promo quote both of them as the same speaker and still pass every validator.

**After:** the honorific is only stripped when the bare surname is *independently attested* somewhere in the corpus as a standalone label. `JULIANA` appears alone 352 times, so `LADY JULIANA` is the same woman. `ASHCROFT` never appears alone, so the merge is refused. Result: 64 raw labels → **58** canonical names through **5** evidence-based merges, down from a wrong 56 / 7.

```python
for h in HONORIFICS:
    if stripped.startswith(h):
        candidate = stripped[len(h):].strip()
        if bare_names is not None and candidate in bare_names:   # <- the fix
            stripped = candidate
        break
```

**Why it matters:** this is the failure mode of writing rules from a sample instead of from the data. I'd eyeballed the top 40 speaker labels, seen `LADY JULIANA`/`JULIANA`, and generalised. The rule only became correct once it had to justify itself against the whole corpus. It also cost me a wrong number in my own audit document ("roughly 30 characters"), which I've corrected in place rather than quietly overwritten.

---

## 6. The ordering failure from #1, caught again in a real 50-episode run
**When:** full run with `qwen/qwen3.8-27b` as the selector, episode 8.

Mistake #1 was a three-beat toy prompt. This is the same class of error on real work, and it is the clearest justification for the whole architecture.

**Before** — qwen chose a promo spanning `00:25.00 → 00:49.60`, then named as its *hook* a beat that begins **8.7 seconds before the promo starts**:

```
p_008_a  segments: 00:25.00 → 00:49.60  (24.6s)
failures: ['hook beat starts -8.70s into the promo, limit is 3.0s',
           "hook beat is not inside the promo's own segments"]
validators: {timestamps_exist: True, length_ok: True, order_ok: True,
             hook_within_3s: False, hook_inside_promo: False,
             cliffhanger_inside_promo: True}
```

The hook it described — *"Juliana offers to trim Alexander's beard, but he refuses with a cryptic 'Not yet.'"* — is a real moment from the episode, written fluently and plausibly. It simply is not in the clip. An editor following this promo would cut 25.0–49.6 and find no beard conversation anywhere in it.

**After:** rejected by two validators and reported in `outputs_qwen/rejected_promos.json`. `gpt-oss-120b` produced zero validator failures on the same 50 episodes.

**Why it matters:** this is the failure that a human reviewer cannot catch by reading the output, because the output is internally coherent and the quoted moment genuinely exists. Only a check against the parsed beat table catches it. Models are casual about positional constraints in a way that is invisible in prose and obvious in arithmetic.

**The broader result it produced.** Measuring the same gold set against three selectors:

| Selector | Mean IoU vs 6 hand-picked promos |
|---|---|
| Code only, no model at all | **0.44** |
| `openai/gpt-oss-120b` | **0.46** |
| `qwen/qwen3.8-27b` | **0.37** |

A weaker model is *worse than no model*. "Add an LLM" is not automatically an improvement, and without the deterministic baseline to compare against I would never have known which side of that line I was on. This is the main reason `--no-llm` is a supported mode rather than a fallback I was embarrassed about.

One honest counterpoint against my own framing: on episode 31 — my favourite hand-pick — qwen chose `131.0–151.2` against my `131.0–160.0`, an IoU of 0.70, while gpt-oss-120b chose a different part of the episode entirely and scored 0.00. The weaker model agreed with me on the pick I cared most about. With a gold set of six, per-episode agreement is noisy, and I should not over-read any single row of that table.

---

## 7. My evaluation inflated its own headline number the moment the feature landed
**When:** immediately after adding two-piece promos, re-running `evaluate.py`.

**Before:** gold-set agreement jumped from **0.46 to 0.519** and "overlapping" went from 5/6 to 6/6. It looked like the new feature had improved the tool. It hadn't. My IoU function took a promo's outer envelope:

```python
def span(promo):
    segs = promo["segments"]
    return segs[0]["start_s"], segs[-1]["end_s"]     # 6.8 -> 89.8
```

For a two-piece promo running `6.8–32.0` **+** `70.0–89.8`, that treats `32–70` as covered. Those are precisely the seconds the splice *removed*. The metric was crediting the tool for footage it had deliberately cut.

**After:** `iou_segments()` computes overlap and union across the real segment list. Agreement went back to **0.465**, and episode 31's match is now reported honestly as `10.5-23.5 + 118.4-132.8`, IoU 0.033, instead of a single flattering span.

**Why it matters:** this is the most dangerous kind of bug in this whole project, because it moved a number in the direction I wanted and gave me a story about why my new feature was good. Nothing failed, nothing errored. I only caught it because a 13% jump from a feature I expected to be marginal didn't smell right. Metrics that improve when you add code deserve more suspicion than metrics that don't.

---

## 8. The two-piece generator's first output ended where it began
**When:** first run of `multi_segment_candidates`, before the arc rule.

**Before:** `p_032_m1` opened on Catherine shouting *"You still think you are better?!"* and closed on Catherine shouting *"You think you can lecture me?!"* — same character, same fury, no question raised. A viewer watches one emotional beat twice and is owed nothing at the end. It passed all six validators: legal length, real timestamps, hook inside the first 3 seconds, cliffhanger inside the promo. Structurally perfect, narratively pointless.

My first fix was a word-overlap check across the two halves. It didn't fire: measured Jaccard was 0.25, and the redundancy lived in the first and last lines rather than spread through the clip, so no threshold I could defend would catch it.

**After:** a rule about arc instead of vocabulary — a spliced promo must either **change who is speaking** or **raise the intensity**. One or the other.

```python
def _no_arc(hook_beat, cliff_beat):
    same_speaker = hook_beat.get("speaker") == cliff_beat.get("speaker")
    escalates = cliff_beat["intensity"] > hook_beat["intensity"] + 0.02
    return bool(same_speaker and not escalates)
```

Episode 32's slot was then filled by its next-best pair — *"Say goodbye to your mother."* escalating to *"Silence! Silence!"* — same speaker, but the temperature rises, so it passes legitimately.

**Why it matters:** two attempts, and the second worked because I stopped measuring the surface (shared words) and measured the thing I actually cared about (does anything change between the start and the end). The first fix would have shipped as a plausible-looking threshold that never fired — the same failure as the duplicate check in #5's neighbourhood.
