# Time log — Kuku AI Generalist take-home

Total budget: 420 min (7h). Start: 2026-11-07 23:14:54 IST.

| Phase | Budget | Start | End | Actual | Delta | Note |
|---|---|---|---|---|---|---|
| 0 Audit | 20 | 23:14 | 23:21 | 6 | **-14** | Under. 3 audit scripts + manual promo seed done. |
| 1 Explore | 30 | 23:21 | 23:25 | 4 | **-26** | Under. 12 approaches + 5 P3 candidates, 4 web searches used of 5. |
| 2 Decide | 20 | 23:25 | 23:28 | 3 | **-17** | Under. Awaiting approval at gate. |
| 3 Spec | 15 | 23:28 | 23:40 | 12 | -3 | On budget. spec.md + assumptions.md + ai_mistakes_log.md. |
| 4 Build | 240 (rescoped) | 23:40 | 07:40 | ~240 active | 0 | Machine slept mid-run; wall clock misleading. All MUST + UI + flagship done. |
| 5 Evaluate | 60 | 07:40 | 10:25 | ~50 active | -10 | Two 50-ep model runs + evaluate.py. Wall clock inflated by two machine sleeps. |
| 6 Deliverables | 60 | 07:41 | 10:25 | ~45 active | -15 | solution_doc, README, video script, defense sheet, SUBMIT checklist. |
| Buffer | 65 | | | | | |

**Cumulative after Phase 2: 13 min used of 70 budgeted — 57 min ahead.**

## Build notes
- Deliverable state after Phase 4: 39 promos shipped from 50 episodes, all 6 validators 50/50,
  6 near-duplicates suppressed, 5 failed the blind gate, 0 untested, flagship valid.
- Scope ADDED vs the original plan (user relaxed the time limit): Streamlit web UI,
  cross-episode flagship promo, pairwise-free LLM ranking with rationale, unseen-input sample.
- Bugs found and fixed during the build, each logged in docs/ai_mistakes_log.md:
  alias over-merge (LORD/LADY), templated hook outside promo bounds, flagship inventing
  timestamps, want_json contract bug crashing the ranking stage, gate failures silently
  counted as passes, duplicate threshold that could never fire, reasoning-token starvation.

## Final state (verified by re-running every entry point)

| Entry point | Result |
|---|---|
| `python run.py --input data --no-llm` | 43 promos, 0.8s, zero network calls |
| `python run.py --input data` | 39 promos, 0.7s from cache (97 hits) - live demo is instant |
| `python run.py --input samples --model qwen/qwen3.8-27b` | 1 promo, 3 calls, 2.3s - unseen input + model swap |
| `python evaluate.py` | all reported numbers reproduce |
| `streamlit run app.py` | 0 exceptions, 0 errors, 6 tabs (verified headlessly via AppTest) |

Wall clock from first `date` to last: ~11h, of which roughly 5h was the machine asleep
(two sleeps, both mid-API-run) and a further stretch was design Q&A before build started.
Active working time is close to the 420-minute budget. The sleeps were not free: they killed
one full model run at call 39 and produced the network-failure cascade that exposed the
"gate errors counted as passes" bug, which is now fixed and logged.
