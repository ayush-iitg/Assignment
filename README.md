# Promo Finder

Reads microdrama screenplays and returns ranked, timestamped **promo cut-lists** an editor can act on: which seconds of which episodes to post as a 20–60s clip.

Kuku AI Generalist assignment, **Problem 1**. Ayush Raj, IIT Guwahati.

Solution doc: [`solution_doc.pdf`](solution_doc.pdf) · Results: [`outputs/promos.md`](outputs/promos.md) · Evaluation: [`outputs/eval_report.md`](outputs/eval_report.md) · Honest failures: [`outputs/rejected_promos.json`](outputs/rejected_promos.json)

---

## Run it — no API key needed

```bash
pip install -r requirements.txt
python run.py --input data          # 47 promos from 50 episodes, ~1 second
streamlit run app.py                # the web interface
```

**Every model response from the full run is committed in `.cache/`**, keyed by `(provider, model, prompt hash)`. So a reviewer with no API key reproduces the exact shipped output in under a second. Delete `.cache/` to force live calls.

For live calls, copy `.env.example` → `.env` and add one key. Swapping models is a flag, not a code change:

```bash
python run.py --input data --model qwen/qwen3.8-27b
python run.py --input data --provider gemini --model gemini-3.5-flash-lite
python run.py --input data --no-llm          # code only, zero network
python run.py --input samples                # an episode the tool has never seen
python evaluate.py                           # regenerate the evaluation report
python ab_test.py                            # blind A/B against random windows
```

Groq, OpenAI, Gemini, Anthropic and OpenRouter are wired. No vendor SDKs — the client speaks HTTP, so there is nothing to install.

---

## The one design decision

> **Code owns time. The model owns judgment.**

The model never sees a timestamp and never writes one. It reads beats as `[b07] JULIANA (desperate): "..."` and answers in beat IDs; code looks each ID up in the parsed table and emits the time. A hallucinated timestamp is not an output this system can produce — `timestamps_exist` is **92/92** on every run.

That isn't theoretical. On episode 8, `qwen3.8-27b` named as its hook a beat starting **8.7 seconds before its own promo begins**. The description was fluent and the moment genuinely exists in that episode — it just isn't in the clip. No reviewer catches that by reading; two validators did.

## What went to AI, what stayed as code

| Stage | Who | Why |
|---|---|---|
| Parse 50 files → 3,727 timed beats | **code** | the format is regular, so rules are faster, free and reproducible. Reconciles labels vs timestamps vs beats and aborts on mismatch |
| Emotion → intensity curve | **code** | the scripts already label delivery — `(Cold, Commanding)`, `(Screaming, Desperate)` — on **1,472 of 1,487** dialogue beats across 617 values. A hand-written lexicon (90% hit rate) reads them. No guessing needed |
| Enumerate 18,141 legal windows, score, shortlist 171 | **code** | 0.8s, offline, free. Every candidate is already length-legal and boundary-legal before a model sees it |
| Choose among candidates, write the copy | **AI**, 1 call/episode | judgement is the one thing code can't do |
| Splice two moments within an episode | **code** | rejected unless the pair has an arc: the speaker changes or intensity rises |
| 6 hard validators + duplicate suppression | **code** | pass/fail, not advisory |
| Blind comprehension gate | **AI**, 1 call/promo | a fresh instance sees only the clip — no logline, episode number or surrounding beats |
| Final selection | **human** | the tool ranks and explains; it never posts |

**Cost at real volume:** one 50-episode show needs **107 model calls and about 175,000 tokens**, which is **$0.00** on the free tier. Building the thing cost 127 calls, because probes and retries aren't free either, but 107 is the number that scales. At a show a week that's roughly 5,600 calls and 9M tokens a year, about $2 at Gemini Flash-Lite rates. Tokens are not the scaling cost — the free tier's 8,000 tokens/minute is, and it vanishes on a paid key. The real cost is editor attention, which is why the gate and duplicate suppression exist.

## How a promo is chosen, step by step

Nine stages take 50 screenplays to 47 ranked promos. Six are pure code, two are model calls, and the last one is both. Every count below comes from the committed run and is visible in the app's **How it ran** tab.

### Step 1 · Parse the scripts into beats — *code*

50 files become **3,727 beats**. A beat is one unit of the screenplay — a line of dialogue, an action, a camera note, a sound effect — and each one carries a start and an end time.

*Why code:* the format is regular, so rules beat inference on speed, cost and repeatability. The parser also reconciles the file's own labels against its timestamps against its beat count, and aborts if they disagree. A silent partial parse would hand you promos built from half an episode.

### Step 2 · Turn delivery notes into an intensity curve — *code*

The scripts already say how each line is performed: `(Cold, Commanding)`, `(Screaming, Desperate)`. **1,472 of 1,487** dialogue beats carry one, across 617 distinct values. A hand-written lexicon (90% hit rate) maps those to a number, giving a per-second intensity curve for each episode.

*Why it matters:* this is the piece of luck the whole approach rests on. Nothing has to infer where the drama is, because the screenplay states it.

### Step 3 · Enumerate every legal clip — *code*

Every window between 20 and 60 seconds long, starting and ending on a real beat boundary: **18,141 candidates**.

*Why code:* the brief's length rule is not a preference, so it should not be a request to a model. Enumerating only legal windows makes an illegal promo impossible to produce rather than something to detect afterwards. Boundary-snapping means no promo ever starts mid-word.

### Step 4 · Score each clip four ways — *code*

| Score | What it measures | Weight |
|---|---|---|
| `hook` | strongest beat in the first 3 seconds, plus a bonus for a physical event or a raised voice landing there | **0.30** |
| `cliffhanger` | strongest beat in the final 5 seconds, plus markers of non-resolution: a question, a trailing-off, a threat, an episode-end cut | **0.30** |
| `tension` | shape of the intensity curve across the clip — rising is better than flat | **0.20** |
| `standalone` | a cheap proxy for comprehensibility: enough speech, not too many characters, no opening pronoun with no name anywhere in the clip | **0.20** |

*Why these four:* they are the brief's own words for what a promo is — opens on a hook, ends on a cliffhanger, makes sense alone. The weights are hand-set and written down in one table. There is no labelled data here, so nothing is learned, and I won't describe it as if it were.

`standalone` is deliberately weak. It exists only to avoid spending a model call on something obviously incomprehensible. The real comprehension test is step 8.

### Step 5 · Filter and shortlist — *code*

**3,376** clips are dropped for having nothing in the first three seconds. The rest are ranked by composite and the best few per episode are kept: **171 shortlisted**.

*Why:* a model asked to choose among 18,141 options does worse than one choosing among four, and costs 4,000× more. Code narrows the field; the model only makes the call that needs judgement.

### Step 6 · The model chooses, once per episode — *AI*

It sees the shortlisted clips as beats — `[b07] JULIANA (desperate): "..."` — picks one, and writes the hook line, the cliffhanger line, one sentence on why it works, and a hook type. Result: **91 candidate promos**.

*Why AI:* which of four strong moments is the most arresting is the one thing rules cannot do.

**It answers in beat IDs and never sees a timestamp.** Code looks each ID up and writes the time. That is why a fabricated timestamp is not an output this system can produce.

### Step 7 · Six hard checks, then remove near-duplicates — *code*

Every promo must pass all six, pass/fail, no advisory warnings:

1. `timestamps_exist` — every time matches a real parsed beat edge
2. `length_ok` — total duration inside 20–60s
3. `order_ok` — each segment runs forwards and segments don't overlap
4. `hook_within_3s` — the named hook beat starts within 3s of the promo's start
5. `hook_inside_promo` — the hook beat is actually inside the promo's own segments
6. `cliffhanger_inside_promo` — same for the cliffhanger

All **91 pass**. Checks 4 to 6 exist because of a real failure: `qwen3.8-27b` once named a hook beat starting 8.7 seconds *before* its own promo began — fluent, real, and not in the clip.

Then **37 promos** are dropped as near-duplicates. Adjacent episodes reuse framing: episodes 31 and 32 both end on a branding iron inches from the heroine's eye. Posting both wastes a slot.

*Why the duplicate rule looks the way it does:* I measured all 1,225 promo pairs before choosing it. Overlap on **dialogue** words peaks at 0.177, so my original threshold of 0.45 on dialogue could never have fired. Repetition in this show is visual, not verbal — the same image described in different words. Overlap on **visual** beats puts ep31/ep32 at 0.191, fourth highest of 1,225, and six of the top seven pairs are one or two episodes apart. Hence the rule: visual-word overlap above **0.17** between episodes no more than **2** apart.

### Step 8 · The blind comprehension test — *AI*

This is the check that can overrule both the code score and the model's own pick, and it's the only one that tests the thing the brief actually asks for: *does this clip work for someone who has never seen the show?*

**How it works.** A fresh model instance is given the clip's dialogue and action, in order, and **nothing else**. No logline. No episode number. No character list. No surrounding beats. No title. It is told it is someone scrolling social media who has never heard of this show, to answer only from the clip, and not to be generous or fill gaps from genre convention.

It answers four questions:

| Question | Passes if |
|---|---|
| Who is the main character? | the clip actually names or identifies them |
| What is at stake? | the conflict is clear without assuming the situation |
| What question are you left with? | the clip does **not** resolve its own conflict |
| Would you keep watching? | yes or maybe, with a reason |

**Three of four is a pass.** **54 promos were tested, 7 failed, none went untested.** Failures are not quietly dropped — they ship in the **Rejected** tab with the full transcript of what the blind reader said, so you can disagree with the judgement.

Across all 54 tested: ends-unresolved **54/54**, character-identifiable **49/54**, stakes-clear **41/54**, would-keep-watching **35/54**. That last one is the honest number. Clips are followable far more often than they are compelling, and that gap is taste this tool can't measure. Among the 47 that survived, would-keep-watching rises to 34/47 — better, but it's the weakest criterion either way.

### Step 9 · Rank what survives

**47 promos** remain. Code sorts them on the weighted composite:

```
composite = 0.30 × hook + 0.20 × tension + 0.30 × cliffhanger + 0.20 × standalone
```

Then the model reorders the top 12, seeing each promo's hook, cliffhanger, hook type, composite and blind-test result. Everything below stays in score order.

*Why a model step at the end:* the composite says which promo is structurally strongest. It cannot say which one to post first. The shipped output shows the difference — the promo at **rank 1** scored **0.876** and was only **tenth** by score. The formula's favourite scored **0.941** and sits at **rank 9**, because it only got 3 of 4 on the blind test while rank 1 got 4 of 4.

So the Score column deliberately isn't descending at the top. Where it isn't, the model moved something, and the table's `Ordered by` column says which.

One consequence worth knowing: a 3/4 can outrank a 4/4, because the blind-test result reaches the ranking through the model's judgement rather than as a term in the formula.

### The funnel in one table

| Stage | Count |
|---|---|
| Legal 20–60s windows on real beat boundaries | 18,141 |
| Rejected — nothing in the first 3 seconds | −3,376 |
| Shortlisted for the model to judge | 171 |
| Candidate promos built | 91 |
| Failed a hard validator | −0 |
| Dropped as a near-duplicate | −37 |
| Failed the blind comprehension test | −7 |
| **Shipped** | **47** |

Full evidence, including the blind A/B against random windows: [`outputs/eval_report.md`](outputs/eval_report.md).

## What it can't do

It can't see: shot quality, performance and music are invisible in text. Its prose embellishes even though its timestamps can't — the top promo's hook says "blood and dust flying" where the screenplay says "stone dust", and the word *blood* appears nowhere in that episode. 8 of 50 episodes ship nothing, having lost their best candidate to the gate or a duplicate. Scoring weights are hand-set and written down in one table; there is no labelled data, so nothing here is learned.

Five things the AI got wrong, with before/after: [`docs/ai_mistakes_log.md`](docs/ai_mistakes_log.md).

## Layout

```
run.py / app.py                CLI · web UI
evaluate.py                    evaluation report
ab_test.py / salvage_ab.py     blind A/B, and the counterbalanced recount
promo/
  parse.py      screenplay → beats           score.py     windows + 4 sub-scores
  lexicon.py    tone tag → intensity         llm.py       provider-agnostic client
  stages.py     the three prompts            validate.py  hard checks + dedup
  ui_style.py   presentation for app.py
  pipeline.py   orchestration — the only place a timestamp is written
data/           the 50-episode input pack    samples/     a synthetic unseen episode
outputs/        the full run, 127 model calls, every request and response kept
outputs_qwen/   second model, 128 records    outputs_nollm/     code-only baseline
outputs_unseen/ unseen-input run             outputs/raw_ab/    158 A/B judgements
.cache/         every model response, which is why this repo runs with no API key
logs/           console transcript of the counterbalanced A/B run
docs/           framing, assumptions, audit, AI mistakes, video script
```

