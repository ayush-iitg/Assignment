# Spec — Promo Finder

Problem 1. Reads microdrama screenplays, returns ranked promo cut-lists an editor can act on.
Provider: Groq (verified). Default model `openai/gpt-oss-120b`; second model for stability `qwen/qwen3.8-27b`.
Assumptions: `docs/assumptions.md`. AI failures so far: `docs/ai_mistakes_log.md`.

## 1. Data model

**Beat** — one timed line in a screenplay, the atomic unit. The LLM is never shown `start`/`end`.
```python
{ "id": "e001_b0042", "episode": 1, "scene": 1, "start": 39.10, "end": 41.20,
  "kind": "DIALOGUE|ACTION|CAMERA|SFX", "speaker": "CLARISSA", "speaker_raw": "LADY IN GOLD GOWN",
  "tone": ["gloating","smug"], "text": "Because he is marrying me.", "intensity": 0.86, "src_line": 118 }
```

**Promo** — the output unit. `segments` is a list, so single-stretch is just length 1.
```python
{ "promo_id": "p_001_a", "shape": "single_stretch|multi_segment|cross_episode",
  "episodes": [1], "segments": [ {"order":1,"episode":1,"start":"00:39.10","end":"01:18.50","duration_s":39.4} ],
  "total_duration_s": 39.4, "hook_is_cold_open": false,
  "hook": {"at":"00:39.10","type":"power reversal|moral outrage|romantic tension|empathy shock","text":"..."},
  "cliffhanger": {"at":"01:18.50","text":"..."},
  "why_it_works": "one line",
  "scores": {"hook":0.93,"tension":0.88,"cliffhanger":0.95,"standalone":0.86,"composite":0.91},
  "cold_viewer": {"verdict":"pass|fail","score":"4/4","answers":{...}},
  "rank": 1, "rank_rationale": "...", "source_beat_ids": ["e001_b0042","e001_b0071"],
  "validators": {"timestamps_exist":true,"length_ok":true,"hook_within_3s":true,"order_ok":true} }
```

## 2. Pipeline

| Stage | Module | Who | In → Out |
|---|---|---|---|
| 1 Parse | `parse.py` | code | 50 `.txt` → beats + `parse_report` (labels vs timestamps vs beats must reconcile, else abort) |
| 2 Alias | `parse.py` | code | 64 raw speaker labels → 56 canonical names via 7 merge groups (honorific strip + explicit epithet map, A11) |
| 3 Intensity | `score.py` | code + hand lexicon | tone tags → `intensity` 0–1 per beat; report tag coverage + unknown tags |
| 4 Windows | `score.py` | code | every 20–60s span with real beat boundaries; greedy non-overlap → top 8/episode |
| 5 Score | `score.py` | code | `hook`, `tension`, `cliffhanger`, `standalone` → `composite` |
| 6 Select | `stages.py` | **LLM** 1 call/ep | shortlist (beat IDs + text, **no timestamps**) → `{start_beat_id, end_beat_id, hook, hook_type, cliffhanger, why_it_works}` |
| 7 Resolve | `pipeline.py` | code | beat IDs → timestamps. The only place a timestamp is ever written. |
| 8 Multi-seg | `stages.py` | code proposes, **LLM** confirms | two windows in one episode, gap ≤ 45s, combined 20–60s |
| 9 Flagship | `stages.py` | **LLM** 1 call/show | best cross-episode launch promo, 3–6 segments |
| 10 Validate | `validate.py` | code | 4 hard checks + near-duplicate suppression (cosine on beat text, threshold 0.75) |
| 11 Gate | `stages.py` | **LLM** 1 call/candidate, fresh context | promo text only → 4 answers + verdict; `<3/4` = rejected, transcript kept |
| 12 Rank | `rank.py` | code + **LLM** | composite sort, then Swiss pairwise over top 12 (3 rounds), LLM writes `rank_rationale` |
| 13 Emit | `pipeline.py` | code | `promos.json`, `promos.md`, `rejected_promos.json`, `parse_report.json`, `raw/`, `run_manifest.json` |

**Scoring, explicitly (no learned weights — A16):**
- `intensity(beat)` = max over its tone tags of a hand-written lexicon (`screaming/agonized/furious` 1.0 … `gentle/quiet/soft` 0.2); ACTION/SFX get a keyword score; unknown tags → 0.0 and counted.
- `hook` = max intensity in the first 3.0s, +0.15 if an ACTION or SFX beat starts there, +0.10 if the first dialogue line is a question or exclamation.
- `tension` = mean intensity + slope of a least-squares fit across the window.
- `cliffhanger` = intensity of the final beat × (1 + unresolved marker bonus: ends on a question, a threat, or an interrupted action), +0.10 if the window ends within 10s of episode end.
- `standalone` = dialogue-second coverage ÷ window length, −0.08 per distinct character beyond 3, −0.15 if the first 10s contains a third-person pronoun with no named antecedent inside the window.
- `composite` = 0.30·hook + 0.20·tension + 0.30·cliffhanger + 0.20·standalone.

## 3. Model layer (`llm.py`) — one function, swappable

`complete(prompt, system, *, provider=env, model=env, json=True) -> dict`

| Requirement | Implementation |
|---|---|
| Provider-agnostic | `groq` and `openai` share the OpenAI chat schema; `gemini` and `anthropic` are separate request builders. All read `{PROVIDER}_API_KEY`. Config: `LLM_PROVIDER`, `LLM_MODEL` env or CLI flag or UI dropdown. |
| Cache | `.cache/{sha256(provider\|model\|system\|prompt)}.json`. Re-runs are free and byte-identical. |
| Rate limits | Token-aware pacer for the measured 8,000 TPM ceiling (A20): rolling 60s window, sleeps before it would breach. |
| Retries | 60s timeout, 2 retries, exponential backoff 2s/8s, honours `Retry-After` on 429. |
| Hard cap | `--max-calls` (default 400). Prints running count; raises at the cap. |
| JSON robustness | `response_format` first; on `json_validate_failed` or a non-JSON body, one plain-text retry + outermost-brace extraction; then drop + log (A21). |
| Audit trail | Every request/response pair written unedited to `outputs/raw/`. |

## 4. Interfaces

**CLI** — `python run.py --input data --out outputs [--provider groq] [--model openai/gpt-oss-120b] [--no-llm] [--episodes 1,2,24] [--max-calls 400] [--no-cache]`
**UI** — `streamlit run app.py`. Calls `pipeline.run(files, config)`, the same function `run.py` calls. Tabs: ranked promos · rejected + transcripts · tension curves · parse report · eval vs gold set · raw LLM I/O. Upload widget, provider/model dropdowns, no-LLM checkbox, JSON/CSV download, ✓/✕ editor log.

## 5. Task budget — Phase 4, 240 min

| Task | Min |
|---|---|
| M1 `parse.py` + reconciliation + alias map | 25 |
| M2 `score.py` lexicon, intensity, windows, 4 sub-scores | 30 |
| M3 `llm.py` cache, pacer, retries, cap, JSON fallback, raw dump | 30 |
| M4 `validate.py` 4 checks + near-duplicate suppression | 15 |
| M5 `run.py` + emitters (`promos.json`/`.md`) + `--no-llm` | 15 |
| M6 Selector stage + prompt | 25 |
| M7 Cold-viewer gate + transcripts | 25 |
| M8 Multi-segment generator | 20 |
| M9 Cross-episode flagship | 15 |
| M10 Ranking + pairwise + rationale | 20 |
| U1 Streamlit UI | 40 |
| **Total** | **260** |

Over by 20; M9 and the pairwise half of M10 are the two I drop if the first end-to-end slice isn't running by minute 100.

## 6. Done means

1. `python run.py --input data` runs on all 50 episodes and writes every artifact.
2. Zero validator violations in the shipped set; violations found during the run are reported, not hidden.
3. `--no-llm` produces a complete ranked list with no network access.
4. A different model via `--model` produces output without code changes.
5. The cold-viewer gate has rejected at least one promo **I picked by hand**, with the transcript shipped.
6. `streamlit run app.py` shows the ranked table, the rejects and the parse report.
7. Every number in the solution doc traces to a file in `outputs/`.
