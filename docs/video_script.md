# Walkthrough script — 2:26, prototype only

Everything happens inside the web app. No terminal, no editor, no files on screen.

**Before recording**

1. **Rotate the Groq key**, then move the env file aside: `mv .env .env.hold`. Restore it afterwards.
   This isn't only key hygiene. With no key present the sidebar prints *"No GROQ_API_KEY set. The bundled pack still runs from cached responses, which is how this reproduces without credentials"* — so the strongest claim in the video is visible on screen instead of asserted. Verified: the button still works and the run still returns all 47 promos.
2. Start the app, open it in the browser, then hide the terminal for the whole recording.
3. Zoom so the stat strip and the first rows of the table are visible together.
4. Narration is 347 words: 2:18 at a normal 150 words a minute, 2:28 even at a slow 140. Under 2:30 either way, with room to let the run finish.
5. Say the numbers as written. All of them are on screen except the A/B figures, which the script attributes out loud to the repo.

---

## Shot 1 · 0:00–0:22 · The problem, and the sidebar

*App freshly loaded. Sidebar visible, with the no-key caption.*

> "An editor at Kuku watches fifty episodes a week by hand to find the clips worth posting. This reads the screenplays instead and returns a ranked shortlist.
>
> Before I run it, look at the sidebar: no API key set. Every response from the full run is cached here, so anyone can clone this and reproduce it."

---

## Shot 2 · 0:22–0:52 · Press it, then read the top line

*Press **Find promos**. Let the log lines and spinner play. About a second.*

> "Fifty episodes, under a second, zero live calls — a hundred and seven served from cache.
>
> Forty-seven promos. Zero invented timestamps, forty-seven of forty-seven validators passing."

*Point at the **Invented timestamps** card.*

> "That card is the whole design. The model never sees a timestamp and never writes one; it answers in beat IDs and my code looks up the time. A hallucinated timestamp isn't unlikely here. It's impossible."

---

## Shot 3 · 0:52–1:20 · The output, and the mechanism

*Ranked tab. The table is already the first thing on the page. Scroll it once, then move to the detail panel below, already on rank 1.*

> "Forty-seven ranked, with JSON and CSV right here. Number one: episode forty-four, fourteen seconds to one-oh-two — opens on a guard forcing a man to the ground, cuts on a confession nobody answers."

*Point at the intensity curve.*

> "And the mechanism is visible. Intensity per second, built from tone tags the screenplays already carry — *cold, commanding; screaming, desperate.* So I never guess where the drama is. Spike early, cut while it's still high."

---

## Shot 4 · 1:20–1:55 · How I know it isn't just plausible

*Rejected tab. Open one blind-test failure so its transcript and four answers are on screen.*

> "Every candidate also faces a second model that sees only the clip. Seven failed, and they're all here with their transcripts.
>
> The number I'd defend isn't on this screen, it's in the evaluation report. Every pick ran against a random legal window from the same episode. The judge preferred whichever clip it read second, so I ran both orders and counted pairs. Seventy-seven percent, p nought-nought-three. Against a window that already passes the hook filter, seventy-three — and that drop is the honest part."

---

## Shot 5 · 1:55–2:26 · Receipts, and what I didn't ship

*"How it ran" tab. Show the funnel, then open the raw requests expander and leave it open while you talk — it makes the point without narration.*

> "Twenty-two defects in Kuku's files, reported rather than repaired. And it can't see, so shot quality is invisible to it.
>
> It also embellishes: that top hook says 'blood and dust'; the screenplay says 'stone dust'. I built three scoring improvements and didn't ship them, because they changed eight of forty-three picks and I couldn't re-run the blind test in time. Better promos beside a number describing the old ones would've been the one dishonest thing here."

---

### If they ask for a live run

That needs the key back: restore `.env`, restart, then upload a file in the sidebar and press **Find promos**. One unseen episode is about three calls and six seconds. Say the call count out loud before you press it.

### Where each number is on screen

| Said | Where it is in the app |
|---|---|
| 50 episodes · 3,727 beats | **Promos** card, sub-line |
| 47 promos | **Promos** card, and the Ranked tab label |
| 0 live calls · 107 cached · under a second | **Cost** card |
| 0 invented timestamps · 47 of 47 validators | **Invented timestamps** card |
| 7 blind-test failures | **Passed blind test** card, 47/54 · Rejected tab |
| ep 44, `00:14.00` → `01:02.40` | Ranked table row 1, and the detail panel |
| 22 source defects | How it ran → Source data, and the defects expander |
| 77.4%, p = 0.003 · 73.3% | **Not in the app.** `outputs/ab_test_balanced.json`, written up in `outputs/eval_report.md` §2. Say "it's in the evaluation report", as scripted |
| 8 of 43 picks changed | **Not in the app.** Git history |

### Two things not to do

Don't say "ninety-two of ninety-two". That counts shipped plus rejected plus the flagship and is right in the written doc, but the card on screen reads **47 / 47**. Saying a number that contradicts the screen someone is staring at is the fastest way to lose them.

Don't cut the stone-dust example or the unshipped improvements to save time. The brief asks where AI got it wrong and what you'd do differently, and those two lines carry both. If a take runs long, drop "Spike early, cut while it's still high" from shot 3 instead.
