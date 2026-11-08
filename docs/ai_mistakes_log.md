# Where the AI got it wrong

The brief asks for one example. These are the five that changed the design — two from the models in the pipeline, three from me or my own code. Kept because each one taught a different lesson; the rest are in the git history.

Tools: **Claude** (code and drafting), **Groq-hosted `openai/gpt-oss-120b`** (pipeline model), **`qwen/qwen3.8-27b`** (comparison model).

---

## 1. A promo that cannot exist, written fluently — twice

**The toy case.** Before any pipeline code existed, I asked both models to pick a promo from three beats: `b_01` "Because he is marrying me." · `b_02` "No..." · `b_03` "You knew this before I walked through those doors!"

`qwen/qwen3.8-27b` returned:

```json
{"start_beat_id": "b_03", "end_beat_id": "b_01", "hook": "You knew this before..."}
```

A clip that starts at beat 3 and ends at beat 1 — it plays backwards. Valid JSON, correct schema, confident. It reproduces at every token budget I tried. `gpt-oss-120b` got the same prompt right.

**The real case**, same model, episode 8 of the full 50-episode run. It chose a promo spanning `00:25.00 → 00:49.60` and named as its hook a beat starting **8.7 seconds before the promo begins**:

```
failures: ['hook beat starts -8.70s into the promo, limit is 3.0s',
           "hook beat is not inside the promo's own segments"]
```

The hook it described — *"Juliana offers to trim Alexander's beard, but he refuses with a cryptic 'Not yet.'"* — is a real moment from that episode, written fluently. It simply is not in the clip. An editor following this promo would cut those 24 seconds and find no beard conversation in them.

**Why this one matters most.** No human reviewer catches this by reading, because the output is internally coherent and the moment genuinely exists. Only a check against the parsed beat table catches it, and two validators did. `gpt-oss-120b` produced zero validator failures across the same 50 episodes.

**What it changed:** it is the entire justification for the architecture. The model answers in beat IDs and never sees or writes a timestamp, so `00:46.80 → 00:39.10` is not an output this system can produce. 92/92 on `timestamps_exist` every run.

---

## 2. The model embellishes its prose, even though it cannot touch the timestamps

`p_044_a` is the top-ranked promo in the shipped run. Its hook, as written by `gpt-oss-120b`:

> "A royal guard slams Rupert to the ground, **blood and dust flying**."

The beat it points at actually reads:

> "A royal redcoat guard firmly forces Rupert down into the **stone dust**."

The word "blood" appears in **zero** of episode 44's beats — I checked every one. "Slams" is also an upgrade on "firmly forces".

**A competing explanation, tested and rejected.** `BLOND NOBLEMAN` speaks two beats below the hook, and *blond* is one character from *blood*. A token-level corruption of a character label into a physical substance would be a far more alarming failure than embellishment, and it fits the evidence at a glance. So I tested it: same prompt, same model, speaker renamed to `FAIR-HAIRED NOBLEMAN`, so the string `blond` appears nowhere.

```
A  original            (BLOND present) -> "...to the ground, blood and dust flying"
B  BLOND -> FAIR-HAIRED (blond absent)  -> "...to the ground, blood and dust flying"
```

B settles it. With `blond` gone the fabrication survives, so the model is not misreading the label. What it is doing is pattern-completion: "forced down into the stone dust" plus violence completes as the genre cliché "blood and dust flying". It keeps the real word, `dust`, and attaches a conventional companion the screenplay never mentions.

**Why the test mattered more than the result.** The corruption story was the better story, and I would have had no evidence for it. This is the second time here that the tidy explanation was wrong and one controlled variable caught it, the first being #5 below. The rule I'd take forward: when a failure has an explanation that is more interesting than the obvious one, that is the moment to run the control, not to start writing.

**Still not fixed, and scoped honestly.** The architecture guarantees the dangerous part: timestamps are verified. The prose is not. An editor reading "blood and dust flying" would cut to `00:14.00` and find no blood.

I also measured how widespread it is before deciding what to build, and the obvious fix turned out to be useless. Matching the words of each description against the beats it covers flags **46 of 47** promos, because the top offenders are `declares`, `erupts`, `hanging` and `unresolved` - legitimate paraphrase and structural description, not invention. Narrowing to concrete physical things a viewer would expect to see, and counting speaker labels as present, leaves **2 of 47**, of which one is arguable. So the real rate is roughly one in fifty, and a word-presence verifier would fire on everything while catching nothing. Any useful version has to separate paraphrase from fabrication, which word presence cannot do.

---

## 3. My evaluation inflated its own headline number the moment a feature landed

When two-piece promos started shipping, agreement with my pre-written reference spans jumped from **0.46 to 0.519**. It looked like the new feature had improved the tool.

It hadn't. My IoU took a promo's outer envelope:

```python
return segs[0]["start_s"], segs[-1]["end_s"]     # 6.8 -> 89.8
```

For a two-piece promo running `6.8–32.0` **+** `70.0–89.8`, that counts `32–70` as covered — precisely the seconds the splice *removes*. The metric was crediting the tool for footage it had deliberately cut.

Fixed to compute overlap and union across the real segment list; agreement returned to **0.465**.

**Why it matters.** This is the most dangerous bug in the project, because it moved a number in the direction I wanted and handed me a story about why my new feature was good. Nothing errored, no test failed. I caught it only because a feature I expected to be marginal produced a 13% gain, which didn't smell right. **A metric that improves when you add code deserves more suspicion than one that doesn't.**

---

## 4. My hand-written character alias table merged two different people

First run of the parser, with the rule "strip the honorific, then merge":

```
ASHCROFT    <- {'LORD ASHCROFT': 8,   'LADY ASHCROFT': 6}
HARRINGTON  <- {'LADY HARRINGTON': 7, 'LORD HARRINGTON': 4}
```

A lord and a lady of the same house are a husband and wife. The parser had collapsed two characters into one, which would let a promo quote both as the same speaker and still pass every validator.

**Fixed with evidence instead of judgment:** an honorific is stripped only when the bare name is independently attested somewhere in the corpus. `JULIANA` appears alone 352 times, so `LADY JULIANA` is the same woman. `ASHCROFT` never appears alone, so the merge is refused. 64 raw labels → **58** canonical names through **5** merges, down from a wrong 56 / 7.

This was my mistake, not a model's: I eyeballed the top 40 speaker labels, saw `LADY JULIANA`/`JULIANA`, and generalised. The rule only became correct once it had to justify itself against the whole corpus.

---

## 5. A diagnosis I got wrong, and the correction

`openai/gpt-oss-20b` returned `HTTP 400 json_validate_failed` with an empty generation, while two other models answered the identical request fine. I logged it as "this model cannot honour JSON mode." Tidy story, wrong conclusion.

A controlled re-test, same prompt, only `max_tokens` changed:

| Model | max_tokens | Result |
|---|---|---|
| `gpt-oss-20b` | 300 | HTTP 400 `json_validate_failed` |
| `gpt-oss-20b` | 900 | HTTP 200, valid JSON |

It is a reasoning model: it spends output tokens thinking before emitting the object, and at 300 it was truncated mid-JSON. The API reports a truncated-and-invalid result as a *validation* failure, which reads like a capability gap but is a budget gap. The error code pointed at "fix your prompt"; the fix was "give it room to finish."

**Changed two defaults:** `max_tokens` is 900 rather than 300, and the client keeps a plain-text fallback with brace extraction as defence in depth. The wrong diagnosis would have changed neither.

A related variant cost me a whole run: the ranking call once returned HTTP 200 with **empty content** and `finish_reason: length` — 1,600 tokens spent entirely on reasoning, a success code carrying no answer. The client now detects that case and retries with double the budget.
