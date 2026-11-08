# Phase 0 — Audit (evidence only)

Source: `I Married a Broken Soldier. He was a Duke/` (50 files) + `Kuku — AI Generalist Assignment.pdf` (6 pages).
Every figure below is reproduced by `python run.py --input data --no-llm`, which prints the same counts and writes `outputs/parse_report.json`. This document is what I established about the data *before* designing anything, and it is why the solution is shaped the way it is.

## 1. Corpus shape

| Metric | Value |
|---|---|
| Episodes | 50 (`Episode 1`..`Episode 50`), one show, English, US audience (PDF p.2) |
| File size | 5.6–15.8 KB, median 10.6 KB; 529 KB / 75,120 words total |
| Episode runtime (max beat end) | min 70.5s, median 118.9s, max 200.8s |
| Episodes > 150s | **12** (ep 36 = 200.8s, 18 = 192.0s, 34 = 190.0s, 33 = 174.0s, …) — brief says "1 to 2-minute", data says otherwise. *(Corrected: an earlier draft of this table said 8. The parser counts 12; `promo/parse.py` is authoritative.)* |
| Scenes per episode | min 1, median 2, max 5. 28/50 episodes are a single scene |
| Timed beats | 3,727 total (median 71/episode) |
| Beat types | CAMERA 1,754 · DIALOGUE 1,487 · ACTION 372 · SOUND FX 114 |
| Dialogue share of runtime | 27%–82%, median 61% |

## 2. Format (consistent enough to parse deterministically)

Every file: `EPISODE NUMBER:` / `EPISODE LOGLINE:` / `CONTINUITY NOTES:` (all 50 present, no exceptions), then `--- SCRIPT START ---`, then `SCENE nn` + `Scene heading:` + `Scene start:` + `Scene end:`, then repeating beats:

```
**CAMERA:**                                  <- or **ACTION:**, **SOUND FX:**, or **SPEAKER (tone, tone):**
Start: (00:04.80) | End: (00:06.80)
<one or more content lines>
```

- Timestamps are `MM:SS.ss`, **relative to episode start**, and every episode's first beat starts at `00:00.00`. No absolute series clock.
- 1,406 distinct bold labels; shape census: `**W:**` 2,126 (technical) · `**W (W, W):**` 677 · `**W W (W, W):**` 251 · `**W (W):**` 193. Dialogue speakers carry parenthetical **tone tags**: **1,472 of 1,487 dialogue beats (98.99%)** have at least one real emotion tag, **617 distinct values** (top: cold 62, resolute 55, desperate 46, whispering 40, defiant 39, mocking 31, screaming 23). Figures are the parser's, after stripping stage directions that share the same parentheses (`V.O.`, `O.S.`, `Continuing`, `Pre-lap`); a first hand-count before that filter existed gave 1,478 / 620.
- Beats overlap by design (CAMERA + ACTION + SOUND FX cover the same seconds), so time ranges are layers, not a sequence.

## 3. Parsing hazards (found, with locations)

| Hazard | Count | Evidence |
|---|---|---|
| Scene header swallowed into previous beat's text (no blank-line separator) | ≥1 | ep 24: `"Good. Perhaps we can teach you your place." SCENE 02 Scene heading: INT. MANOR HEARTH ROOM` lands in one beat |
| `Scene heading/start/end` missing | ep 6 | audit2: 2 scenes with no heading, scene duration sum 0.0 |
| Non-monotonic beat starts (next beat starts before previous) | 8 | ep 4 L450 147.5→147.0 · ep 12 L98 31.0→30.0 · ep 21 L58, L98 · ep 32 L118 33.5→33.2 · ep 46 L218 |
| Overlapping *dialogue* beats (two speakers talking over each other) | 10 | ep 3 L26 · ep 5 L158 · ep 6 L257 · ep 18 L192 · ep 20 L113 |
| Tone tag mixes delivery with stage direction | many | `(V.O.)`, `(O.S. / Continues)`, `(Off-screen, Dismissive)`, `(Reverent toward Clarissa)` — must be stripped before treating tone as emotion |
| No end-before-start, no missing timestamps | 0 | clean |

## 4. Continuity / naming inconsistencies (matters for "makes sense standalone")

Same character, multiple labels across the corpus. Precisely: **64 raw speaker labels resolve to 58 canonical names through 5 merge groups** (`promo/parse.py` alias map). Honorifics are only stripped when the bare name is independently attested elsewhere in the corpus — `JULIANA` appears alone 352 times, so `LADY JULIANA` is the same woman; `ASHCROFT` never appears alone, so `LORD ASHCROFT` and `LADY ASHCROFT` stay two people. Generic roles (`MAID`, `NOBLEWOMAN`, `JUDGE`) are deliberately not merged, because the same label is reused for different people in different episodes. The 5 merges:

| Canonical | Labels merged (counts) | Basis |
|---|---|---|
| `JULIANA` | `JULIANA` 352, `LADY JULIANA` 110 | honorific |
| `CATHERINE` | `CATHERINE` 187, `LADY CATHERINE` 9 | honorific |
| `CLARISSA` | `CLARISSA` 17, `LADY IN GOLD GOWN` 17, `LADY CLARISSA` 11 | honorific + epithet |
| `GERALD` | `GERALD` 32, `THE FORMER GROOM` 16 | epithet |
| `MYSTERIOUS BEARDED MAN` | `MYSTERIOUS BEARDED MAN` 28, `THE BEARDED STRANGER` 15 | epithet |

Rejected merges, caught by the attestation rule: `LORD ASHCROFT` + `LADY ASHCROFT` and `LORD HARRINGTON` + `LADY HARRINGTON` are kept separate (husband and wife, not one character). My first hand-written alias table merged them; see `docs/ai_mistakes_log.md` #5.

Not merged, deliberately: `ALEXANDER'S MOTHER` 39 / `DOWAGER DUCHESS` 26 / `MATRIARCH` 8 / `NOBLE MATRIARCH` 11 are plausibly one woman, but "matriarch" is also used generically, so merging needs scene-level evidence I haven't established. Generic role labels (`LORD` 36, `MAID` 20, `NOBLEWOMAN` 14, `OFF-SCREEN VOICE`) stay separate by design.

Also: ep 1 names the fiancé "Gerald" in the logline but labels his lines `THE FORMER GROOM`; ep 2 labels the father `BLOND NOBLEMAN`. Ep 31 and ep 32 both end on a near-identical image (branding iron stopping inches from Juliana's eye, ep31 151.5–160.0 vs ep32 151.2–154.4) — adjacent episodes reuse cliffhanger framing, so a naive picker will surface near-duplicate promos.

No cross-episode dialogue duplication: for every episode pair, shared verbatim quote lines < 12% of the smaller episode. 1,487 unique quoted lines total.

## 5. Manual promo picks (my eval seed, hand-made before any LLM ran)

| # | Episode | Segment(s) | Len | Hook (first 3s) | Cliffhanger (last beat) | Why it works |
|---|---|---|---|---|---|---|
| A | 1 | 00:39.10 → 01:18.50 | 39.4s | 00:39.1 Clarissa, gloating: "Because he is marrying me." | 01:15.0–01:18.5 "Long enough to know he was never going to marry you." | Whole premise lands with zero prior context: bride at the altar discovers her sister is the one marrying her fiancé, and the family knew. |
| B | 24 | 00:32.50 → 01:21.00 | 48.5s | 00:32.5 whip crack — the noblewoman strikes Juliana across the torso with a riding crop (visual, no dialogue needed) | 01:18.6 Juliana, cold: "Let her think I am only a maid." | Physical violence stops the scroll, then a secret-identity tease replaces resolution: the viewer now needs to know who she really is. |
| C | 31 | 02:11.00 → 02:40.00 | 29.0s | 02:11.0 Catherine's enraged scream "Enough!" over a branding iron hitting her mother's book | 02:31.5–02:40.0 iron stops inches from Juliana's eyes, macro close-up of the ember in her eye | Pure peril, no setup required, and it cuts mid-threat — the question is literally "does she get burned?" |

Caveat on C: it needs one line of who-is-who; A and B are self-explanatory. That asymmetry is the thing a standalone-comprehension check has to catch.
