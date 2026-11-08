# Assumptions

The brief says to assume rather than ask. Each assumption below states what I assumed, why, and what breaks if I'm wrong.

## About the problem

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A1 | A promo is a **cut list**, not a rendered video: `(episode, start, end)` segments an editor hands to an assembler. No editing, music or overlays. | Brief p.2: "Your job is only to find these promos: the right moments, and the right start and end points." | Nothing — this is explicit. |
| A2 | Promo length is a **hard** constraint: 20.0s ≤ total ≤ 60.0s, enforced in code, no exceptions. | Brief p.2 states 20–60s. | If 15s or 90s promos are acceptable, it's one config value. |
| A3 | "Opens on a hook in the first 3 seconds" means the **hook beat must begin within 3.0s of promo start**. | Brief p.2. | Looser reading (hook merely present early) would admit more candidates. |
| A4 | Timestamps are **relative to each episode's start**. | Verified: all 50 episodes have a first beat at `00:00.00`; no absolute series clock exists anywhere in the pack. | Would need a show-level offset table, which the pack doesn't provide. |
| A5 | Most promos should be a **single continuous stretch**; multi-segment is the exception. | Brief p.2: "usually one continuous stretch". | Ratio is a config value. |
| A6 | The editor is the decision-maker. The tool ranks and explains; it never publishes. | Brief p.2 describes an editor doing this by hand today. | — |
| A7 | Episodes are consumed in order, so a promo may spoil a *later* episode but a viewer-facing promo must not require having seen an *earlier* one. | Implied by "makes sense on its own to someone who has never seen the show". | — |

## About the input data

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A8 | The screenplay format is stable enough to parse with rules, not an LLM: `**LABEL:**` → `Start: (MM:SS.ss) \| End: (MM:SS.ss)` → text. | Holds across all 50 files, 3,727 beats. | Parser emits a reconciliation report and fails loudly rather than producing partial output. |
| A9 | Parenthetical tone tags on dialogue labels are a usable **emotion signal**. | 1,478 of 1,487 dialogue beats (99.4%) carry at least one; 620 distinct values. | Coverage is measured per run; below 60% the pipeline falls back to a keyword lexicon over ACTION/SOUND FX text and says so in the report. |
| A10 | `(V.O.)`, `(O.S.)`, `(Off-screen)`, `(Continuing)`, `(CONT'D)` are **stage directions, not emotions**, and are stripped before scoring. | They appear mixed into the same parentheses as real tone words. | Minor scoring noise. |
| A11 | Speaker labels differing only by an honorific or an epithet are the **same character**: `LADY JULIANA`≡`JULIANA`, `LADY CATHERINE`≡`CATHERINE`, `THE FORMER GROOM`≡`GERALD`, `LADY IN GOLD GOWN`≡`CLARISSA`, `THE BEARDED STRANGER`≡`MYSTERIOUS BEARDED MAN`. | 64 distinct labels for ~31 characters; ep 1's logline names "Gerald" while his lines are labelled `THE FORMER GROOM`. | Alias map is a visible table in the repo, not buried logic. Honorific stripping is automatic; the epithet pairs above are my judgment and are listed explicitly so they can be corrected. |
| A12 | Generic labels (`LORD`, `MAID`, `NOBLEWOMAN`, `OFF-SCREEN VOICE`) are **roles, not identities**, and are not merged with each other. | Same label is used for different people in different episodes. | Could under-merge; safer than over-merging. |
| A13 | CAMERA beats are excluded from LLM prompts (kept in the data) because ACTION beats already carry the physical events, and CAMERA is 47% of all beats. | Token budget: Groq free tier is 8,000 tokens/minute. | Some visual hooks exist only in CAMERA lines; measured as a known limitation. |
| A14 | Episode runtime is `max(beat end)`. 8 of 50 episodes exceed 150s (max 200.8s) despite the "1–2 minute" framing — I treat the data as truth. | Measured. | — |
| A15 | The 8 non-monotonic beat starts and 10 overlapping dialogue beats are **data noise, not meaning**. Beats are sorted by start time; overlaps are kept (characters do talk over each other). | Deltas are 0.1–0.5s, consistent with rounding. | Negligible. |

## About quality and evaluation

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A16 | There is **no ground truth** for "good promo", so scoring weights are hand-set and documented, never presented as learned. | No labelled data exists and none can be created in the time available. | Honest by construction. The editor ✓/✕ log in the UI is the dataset that would eventually allow real tuning. |
| A17 | A **blind comprehension test** is a defensible proxy for "makes sense on its own": a model given only the promo text, with no logline, episode number or surrounding beats, must answer who/stakes/open-question/would-watch. | Operationalises the brief's third criterion instead of asserting it. | It's a proxy, not a viewer. Transcripts are shipped so the reader can judge the judge. |
| A18 | A second model from a different family is enough for a stability check. | Groq free tier offers `openai/gpt-oss-120b` and `qwen/qwen3.8-27b` — different families, not two sizes of one. | — |
| A19 | Shot-level visual quality, performance, music and pacing are **invisible to this solution**. | Input is text. | Stated as the first limitation in the doc, and the first thing I'd fix with frame-level input. |

## About infrastructure

| # | Assumption | Basis | If wrong |
|---|---|---|---|
| A20 | Free tier only. Groq: **1,000 requests/day, 8,000 tokens/minute** (measured from live response headers). | `x-ratelimit-limit-requests: 1000`, `x-ratelimit-limit-tokens: 8000`. | The token-per-minute ceiling, not cost, is the binding constraint. A full 50-episode run is therefore pace-limited to roughly 25–35 minutes of wall clock. Mitigations: CAMERA beats excluded from prompts (A13), disk cache keyed on `(provider, model, prompt hash)` so re-runs are free and instant, and a token-aware pacer with 429 + `Retry-After` handling. |
| A21 | Structured-output support is **not** guaranteed across models. | `openai/gpt-oss-20b` returns HTTP 400 `json_validate_failed` on the same request the other two models answer fine. | Model layer tries JSON mode, falls back to text + brace extraction, then drops the candidate with a log entry. |
| A22 | `--no-llm` must produce a complete ranked promo list using code-only scoring and templated copy. | Live-demo insurance; also makes the pipeline testable without burning quota. | — |
| A23 | The input pack may be committed to a public repo. | **Explicitly decided by Ayush Raj**, who states the Kuku team has agreed. I flagged the confidentiality clause on PDF p.5 and the risk that deleting a public repo does not undo cloning or indexing; he confirmed. `data/` is the input path, so excluding it later is a one-line `.gitignore` change. | Recorded as his decision, not an inference of mine. |
| A24 | The API key lives in `.env` (gitignored) and in Streamlit secrets when deployed, never in code or committed files. | — | The key pasted into this chat should be rotated at [console.groq.com](https://console.groq.com) after submission, since it will also appear in any screen recording of the terminal. |
