# Promo Finder

Reads microdrama screenplays and returns ranked, timestamped **promo cut-lists** an editor can act on: which seconds of which episodes to post as a 20–60s clip on Instagram, TikTok or YouTube.

Kuku AI Generalist assignment, Problem 1. Ayush Raj, IIT Guwahati.

**The design decision everything follows from: code owns time, the model owns judgment.** The model is shown beats with timestamps *stripped from the prompt* and answers in beat IDs (`e012_b0043`); code looks each ID up in the parsed beat table and writes the timestamp. A hallucinated timestamp is not something this system can produce. The `timestamps_exist` validator proves it on every run — 92/92 on the full pack.

It caught a real one: on episode 8, `qwen3.8-27b` named as its hook a beat starting **8.7 seconds before its own promo begins**. The hook text was fluent and that moment genuinely exists in the episode — it just isn't in the clip. No reader could catch that by eye.

---

## Results on the supplied 50-episode pack

| | |
|---|---|
| Episodes parsed | 50 → **3,727 timed beats** (1,754 camera · 1,487 dialogue · 372 action · 114 sfx) |
| Promos shipped | **47** from 91 candidates (50 continuous stretches, 41 two-piece splices) |
| Validators | **92/92 on all 6 checks**, zero invented timestamps |
| Blind cold-viewer gate | 54 tested, **7 failed**, 87.0% pass, 0 untested |
| Continuous vs spliced promos | pass the blind test at **0.886 vs 0.800** — splicing measurably costs comprehension |
| Near-duplicates suppressed | 37, of which 10 are genuine cross-episode repeats (including episodes 31 and 32, which both end on a branding iron inches from the heroine's eye) |
| Gold set — 6 promos hand-picked before the tool existed | all 6 overlap a tool pick. Mean IoU: code-only **0.354** · `gpt-oss-120b` **0.465** · `qwen3.8-27b` **0.359** |
| Determinism | two runs → identical decision fingerprint `c7b809ad92b976e7` |
| Cost for one full show | 127 API calls, 199,803 tokens, **$0.00 on free tier** |

Full numbers: [`outputs/eval_report.md`](outputs/eval_report.md). Honest failures: [`outputs/rejected_promos.json`](outputs/rejected_promos.json).

---

## Run it

```bash
pip install -r requirements.txt

# 1. Code-only. No API key, no network, works immediately.
python run.py --input data --no-llm

# 2. Full pipeline. Needs a key in .env (see below).
python run.py --input data

# 3. Web interface
streamlit run app.py

# 4. Evaluation report
python evaluate.py
```

### API key

Copy `.env.example` to `.env` and add one key. Any of these providers work; no SDKs are installed, the client speaks HTTP directly.

```
GROQ_API_KEY=...            # free tier: 1,000 requests/day — what this was built on
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
```

Swap the model with a flag, no code change:

```bash
python run.py --input data --model qwen/qwen3.8-27b
python run.py --input data --provider gemini --model gemini-2.5-flash-lite
python run.py --input data --provider openai --model gpt-4o-mini
```

### Useful flags

| Flag | Effect |
|---|---|
| `--no-llm` | Deterministic scoring + templated copy. No network. Live-demo insurance. |
| `--episodes 1,24,31` | Develop on a few episodes instead of 50. |
| `--max-calls N` | Hard cap, default 400. Raises rather than overspending. |
| `--no-cache` | Ignore the response cache. |
| `--no-gate` / `--no-flagship` | Skip the blind gate / the cross-episode promo. |
| `--top-k N` | Candidate windows per episode shown to the model (default 4). |

---

## How it works

```
50 .txt screenplays
   │
   ├─ parse.py      rule-based parser → 3,727 timed beats; reconciles labels vs
   │                timestamps vs beats and ABORTS if they disagree; reports 22
   │                source-data hazards; merges 64 speaker labels → 58 characters
   │
   ├─ score.py      tone tags → intensity curve → every legal 20–60s window on real
   │                beat boundaries (18,141) → 4 sub-scores → shortlist 171
   │                also proposes two-piece splices within an episode, rejected
   │                unless the pair has an arc (speaker changes or intensity rises)
   │                           ⬑ NO MODEL INVOLVED. Runs in 0.8s offline.
   │
   ├─ stages.py     selector: 1 call/episode, sees beat IDs and text, no timestamps
   │
   ├─ validate.py   6 hard checks + visual near-duplicate suppression
   │
   ├─ stages.py     blind cold-viewer gate: 1 call/promo, fresh context, clip text only
   │
   └─ pipeline.py   rank, build the flagship cross-episode promo, write outputs
```

**The signal that makes this cheap:** the screenplays label the delivery of nearly every line of dialogue — `(Cold, Commanding)`, `(Screaming, Desperate)`, `(Whispering, Tearful)`. 1,472 of 1,487 dialogue beats carry one, across 617 distinct values. So the tool does not need a model to guess where the drama is; the script already says. A hand-written lexicon (`lexicon.py`, 90% hit rate) turns those tags into an intensity curve, and a promo is a shape on that curve: a spike inside the first 3 seconds, a rising edge, and a cut while still high.

**The check that makes it honest:** every candidate is handed to a second model instance with the logline, episode number and surrounding beats removed, and asked who this is, what's at stake, what question it leaves, and whether they'd keep watching. Promos that can't be followed are rejected with the transcript attached. Five were. One of my own hand-picked promos was flagged this way at audit time for exactly the reason the gate later measured.

## Outputs

| File | What it is |
|---|---|
| `outputs/promos.md` | the editor's view: one ranked table |
| `outputs/promos.json` | machine-readable, full scores and beat provenance |
| `outputs/rejected_promos.json` | everything thrown out, with the reason and the gate transcript |
| `outputs/parse_report.json` | hazards, tone coverage, alias map, per-episode stats |
| `outputs/eval_report.md` | gold-set agreement, validator counts, gate rates, model stability |
| `outputs/raw/` | unedited request/response pairs for every API call |
| `outputs/tension_curves.json` | per-second intensity, per episode |

## Repo layout

```
run.py            CLI
app.py            Streamlit UI — a view over pipeline.run(), not a second implementation
evaluate.py       evaluation harness
promo/
  parse.py        screenplay → beats
  lexicon.py      tone-tag → intensity table (hand-written, in the open)
  score.py        windows + the four sub-scores
  llm.py          provider-agnostic client: cache, token pacer, retries, call cap
  stages.py       the three prompts
  validate.py     hard validators + duplicate suppression
  pipeline.py     orchestration; the only place a timestamp is written
data/             the 50-episode input pack
samples/          a synthetic episode I wrote, for testing on unseen input
docs/             audit, exploration, decision memo, spec, assumptions, AI mistakes log
outputs/          results from the full run
```

## What this does not do

Shot-level visual quality, performance and music are invisible to it — the input is text, so it is reading sheet music and guessing at the performance. It builds exactly one cross-episode promo rather than many, because stitching arbitrary moments across 50 episodes needs reliable character identity and this corpus has 64 speaker labels for 58 characters. The scoring weights are my judgment, hand-set and written down in one table; there is no labelled data for "good promo", so anything described as learned would be invented.

Known limitations, measured rather than guessed: [`outputs/eval_report.md`](outputs/eval_report.md) §3 and the limitations section of the solution doc.

## Input pack

`data/` holds Kuku's 50-episode screenplay pack, included at the explicit direction of the repo owner, who states the Kuku team agreed to this. It is Kuku's own unreleased content. `data/` is the single input path, so excluding it is a one-line `.gitignore` change.
