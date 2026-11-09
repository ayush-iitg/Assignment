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

**Cost at real volume:** one 50-episode show = **127 calls, 199,803 tokens, $0.00** on free tier; ~$2.20/year at a show a week on Gemini Flash-Lite rates. Tokens are not the scaling cost — the free tier's 8,000 tokens/minute is, and it vanishes on a paid key. The real cost is editor attention, which is why the gate and duplicate suppression exist.

## How I know it's good

| | |
|---|---|
| **Beats a random legal window** (blind, 38 pairs, every pair judged in both orders) | **77.4%** of decisive pairs, p=0.003 |
| Beats a window that already passes the hook filter | **73.3%**, p=0.016 — the hook rule does a lot of the lift, the scoring adds a real edge on top |
| Validators across 92 promos | **92/92** on all six. Zero invented timestamps |
| Blind comprehension gate | 54 tested, **7 failed**, 0 untested |
| Continuous vs spliced promos | **0.886 vs 0.800** pass rate — splicing measurably costs comprehension |
| Determinism | two runs → identical fingerprint `c7b809ad92b976e7` |
| Cross-model stability | mean IoU **0.50**, no overlap at all on 8 of 50 episodes |

There is deliberately **no hand-picked gold set** as the headline. It asks the wrong question and wouldn't scale — see the solution doc.

## What it can't do

It can't see: shot quality, performance and music are invisible in text. Its prose embellishes even though its timestamps can't — the top promo's hook says "blood and dust flying" where the screenplay says "stone dust", and the word *blood* appears nowhere in that episode. 8 of 50 episodes ship nothing, having lost their best candidate to the gate or a duplicate. Scoring weights are hand-set and written down in one table; there is no labelled data, so nothing here is learned.

Five things the AI got wrong, with before/after: [`docs/ai_mistakes_log.md`](docs/ai_mistakes_log.md).

## Layout

```
run.py / app.py / evaluate.py / ab_test.py     CLI · web UI · evaluation · blind A/B
promo/
  parse.py      screenplay → beats           score.py     windows + 4 sub-scores
  lexicon.py    tone tag → intensity         llm.py       provider-agnostic client
  stages.py     the three prompts            validate.py  hard checks + dedup
  pipeline.py   orchestration — the only place a timestamp is written
data/           the 50-episode input pack    samples/     a synthetic unseen episode
outputs/        full run + 127 raw call records  outputs_qwen/  second model, 128 records
outputs_nollm/  code-only baseline           outputs_unseen/    unseen-input run
docs/           framing, assumptions, audit, AI mistakes, video script
```

`data/` holds Kuku's screenplay pack, included at the repo owner's direction. `data/` is the single input path, so excluding it is a one-line `.gitignore` change.
