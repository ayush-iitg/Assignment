# Phase 2 — Decision memo

## 1. Weighted scoring matrix

Weights (sum 100) = the five published lenses plus the five things that decide whether I actually land this in 7 hours.
`frame` problem choice & framing 15 · `scale` approach/scale/cost 15 · `qual` quality checking 15 · `proto` prototype runs on real inputs 20 · `comms` explainability 5 · `feas` feasibility in 150 build-min 10 · `meas` measurability of quality 5 · `demo` demo-ability on an unseen input 5 · `dist` distinctiveness vs many similar candidates 7 · `safe` low overpromise risk 3. Scores 1–5, normalised to 100.

| Approach | frame | scale | qual | proto | comms | feas | meas | demo | dist | safe | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1B+1C+1D composite** | 5 | 5 | 5 | 5 | 4 | 3 | 5 | 5 | 5 | 5 | **95.0** |
| 1D cold-viewer gate + pairwise | 4 | 4 | 5 | 4 | 4 | 4 | 5 | 5 | 5 | 5 | 87.0 |
| 1B windows + beat-ID LLM | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 5 | 4 | 4 | 85.0 |
| 3.1 character-label drift | 3 | 4 | 4 | 5 | 4 | 5 | 5 | 4 | 4 | 4 | 84.0 |
| 3.4 timeline validator | 3 | 4 | 4 | 5 | 4 | 5 | 5 | 4 | 3 | 5 | 83.2 |
| 1C tone-curve, code ranks | 4 | 5 | 4 | 4 | 5 | 3 | 4 | 3 | 5 | 4 | 82.4 |
| 2C evidence triage | 4 | 4 | 3 | 4 | 4 | 4 | 3 | 4 | 4 | 4 | 76.0 |
| 2B rules + templates | 4 | 4 | 3 | 4 | 5 | 4 | 3 | 3 | 3 | 5 | 75.2 |
| 2A RAG + citation verifier | 4 | 4 | 4 | 4 | 4 | 2 | 4 | 5 | 3 | 3 | 75.0 |
| 3.3 runtime drift check | 2 | 3 | 3 | 5 | 5 | 5 | 5 | 4 | 2 | 5 | 73.8 |
| 2D opponent sim + refusal | 3 | 3 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 5 | 70.6 |
| 1A whole-episode LLM (the median submission) | 2 | 2 | 1 | 3 | 4 | 5 | 1 | 4 | 1 | 2 | 48.6 |

## 2. Sensitivity: which weights flip the winner?

| Re-weighting | Winner | Runner-up |
|---|---|---|
| Base | 1B+1C+1D (95.0) | 1D (87.0) |
| Ship-at-all-costs (feas 30, proto 30) | 1B+1C+1D (90.0) | 3.1 label drift (87.7) |
| Distinctiveness ×3.5 (25) | 1B+1C+1D (95.8) | 1D (89.0) |
| Problem-choice ×2.3 (35) | 1B+1C+1D (95.8) | 1D (85.8) |
| Quality-checking ×2 (30) | 1B+1C+1D (95.7) | 1D (88.7) |
| **Feasibility 40 (panic mode)** | **3.1 character-label drift (87.7)** | 3.4 timeline validator (87.1) |

Only one reweighting flips it: if I decide I can't ship a working P1 pipeline, the right move is P3 character-label drift, because it's measurable and buildable in ~1.5 h. **That is my fallback, and the trigger is explicit: if the end-to-end ugly version isn't running on 2 episodes by build-minute 70, I switch.**

## 3. Red team on my own pick

| Attack | Honest answer |
|---|---|
| **"Everyone picks P1."** It has the input pack. The brief itself warns that similar submissions from one campus get reviewed closely. | True, and it's the main risk. I'm not betting on problem choice for distinctiveness; I'm betting on three things the median P1 build won't have: timestamps that *cannot* be hallucinated (the model selects beat IDs, code emits times), a promo score built from the tone tags already in Kuku's own screenplays, and a blind cold-viewer test that can fail my own promos. |
| **"You have no media background. Why is your taste in promos worth anything?"** | It isn't, and I won't claim it. I claim a measurable proxy instead: hook in the first 3s, rising tension, a cut at an unresolved beat, and a comprehension test a context-free reader must pass. Where the tool disagrees with my hand-picks I report the disagreement rather than tuning until it agrees. |
| **"No ground truth, so 'how do you know it's good' is hand-waving."** | Weakest point. Mitigation: a 5–6 promo gold set I built before any LLM ran (3 already in `00_audit.md`), rank stability across two runs and two models, and a validator suite with hard pass/fail. I will report overlap numbers even if they're bad. |
| **"Tone tags are a crutch that won't exist on the next show."** | Fair. The parser reports tone-tag coverage; below a threshold it falls back to a lexicon over ACTION/SOUND FX text. I'll demo that path rather than hide it. |
| **"A promo is visual; a screenplay isn't video."** | Agreed. The brief scopes this to finding moments and timestamps, no editing. I'll say plainly that shot-level visual impact is invisible to me and is the first thing I'd add with frame-level input. |
| **"Problem 2 would stand out more."** | It would differentiate on topic but I'd be building legal content with zero legal background and no input pack, in 7 hours, under a rule that forbids inventing sections. Higher overpromise risk, lower chance of a prototype that survives being re-run live. |

**What the median competitor ships:** one prompt containing a whole screenplay, a bullet list of 3 promos with plausible-looking timestamps, a one-paragraph "ranking" with no method, and a doc that asserts the promos make sense standalone without testing it.

## 4. Decision

- **Primary: Problem 1, built as 1B+1C with 1D as the quality gate.** Deterministic parser → enumerate 20–60s windows snapped to real beat boundaries → tone-tag tension score shortlists → LLM picks and explains by beat ID only → validators + blind cold-viewer comprehension test → ranked promo list with a "post this first" rationale.
- **Fallback (trigger at build-minute 70): P3.1 character-label drift detector.** Already evidenced in `00_audit.md`.
- **Degraded mode inside the primary (no API / quota dead): 1C alone** with templated hook/cliffhanger copy. The pipeline must still produce a complete ranked promo list with `--no-llm`.

## 5. MUST / SHOULD / CUT — revised after the "web interface" instruction

Phase 4 extended from 150 → **175 min**, funded by the 57 min earned in Phases 0–2 (not from buffer). Streamlit UI promoted from CUT to MUST; S3 demoted to CUT.

| | Task | Min |
|---|---|---|
| **MUST** | M1 Parser: beats, tone tags, speaker aliasing, hazard handling (ep-6, ep-24, non-monotonic), parse report | 25 |
| **MUST** | M2 Window enumeration + deterministic tension/hook/cliffhanger scoring from tone lexicon | 25 |
| **MUST** | M3 Provider-agnostic LLM layer (env var provider+model, disk cache, 60s timeout, 2 retries, 429 handling, hard call cap) + selector prompt returning beat IDs | 30 |
| **MUST** | M4 Validators: every timestamp exists in beat table, 20–60s, hook within first 3s, near-duplicate suppression | 10 |
| **MUST** | M5 `run.py` CLI → `outputs/promos.json` + Markdown, incl. `--no-llm` mode | 10 |
| **MUST** | M6 Blind cold-viewer comprehension gate (fresh context, strict rubric, transcript saved) — promoted, it is the distinctiveness | 25 |
| **MUST** | **U1 Streamlit web UI** over the same functions: upload .txt → run → ranked table, rejected-with-transcript tab, parse report, tension curve, download buttons, provider/model selectors | 35 |
| **SHOULD** | S2 Ranking rationale ("post this first because…"), composite score; pairwise tournament only if spare | 10 |
| **SHOULD** | U2 Deploy to Streamlit Community Cloud + README run steps | 15 (Phase 6) |
| **CUT** | S3 multi-segment promo, cross-episode thread stitching, visual/shot scoring, any training, auth |  |

MUST = 160 min, SHOULD-in-phase-4 = 10 min, total 170 of 175.

**UI architecture rule: the UI is a view, not a second implementation.** `pipeline.run(files, config) → dict` is called identically by `run.py` and `app.py`. If the UI breaks, the CLI still produces every deliverable.

**Confidentiality constraint on deployment** (PDF p.5: don't publish or share the input pack): the public repo and the deployed app ship **no Kuku episode files**. The deployed app defaults to upload mode. Precomputed results over the real pack go in the `outputs/` link on the submission form, not into a public GitHub repo.

---

## STOP — I need two answers before I write code

1. **Which API key do you have available?** Say the env var name and I'll wire it as the default (free tier is fine: Gemini 2.5 Flash-Lite is ~1,000 req/day). If you have none, I build `--no-llm` first and you add the key later — the pipeline will still run end-to-end, just with templated copy instead of LLM-written hooks.
2. **Approve the plan above, or switch?** Default if you just say "go": Problem 1 as specified.

⏱ **Checkpoint: 10 min used of 70 budgeted for Phases 0–2 (60 min ahead).** If I fall behind later, the first cut is S3 (multi-segment promo), then S2 drops from pairwise to a composite score.
