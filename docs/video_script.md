# Walkthrough script — 2:24

**Before recording**

- **Rotate the Groq key.** It's in `.env` and it will be on screen.
- App already running (`python3 -m streamlit run app.py`), terminal already in the repo, large font. Nothing waits on the network: every model response is cached, so the full run finishes in under a second.
- Narration is 326 words: 2:10 at a normal 150 words a minute, 2:20 even at a slow 140. That leaves room for the run to finish and for a pause on each click, and still lands under 2:30 at any pace.
- Say the numbers as written. Each one is checked against a file; the table at the bottom says which.

---

## Shot 1 · 0:00–0:24 · The problem, and the thing I noticed

*A screenplay file open, scrolled to a few tagged dialogue lines.*

> "Kuku ships fifty episodes a week, and an editor watches all fifty by hand to find the clips worth posting. Mine reads the screenplays and returns a ranked shortlist.
>
> What makes that tractable is already in Kuku's files: every line of dialogue is labelled with how it's delivered — *cold, commanding; screaming, desperate.* So I never guess where the drama is."

---

## Shot 2 · 0:24–0:54 · It runs, and it runs with no key

```bash
python3 run.py --input data
```

*Let it finish on camera. About a second.*

> "One command, fifty episodes, under a second — and no API key set. Every model response is committed, so you can clone this and reproduce all forty-seven promos without signing up."

*Point at `timestamps_exist: 92/92`.*

> "That line is the whole design. The model never sees a timestamp and never writes one; it answers in beat IDs and code looks up the time. A hallucinated timestamp isn't unlikely. It's impossible."

---

## Shot 3 · 0:54–1:16 · What an editor actually gets

*Browser, **Ranked** tab. The table is the first thing on the page. The detail panel below it is already on rank 1.*

> "Forty-seven promos, ranked. Number one: episode forty-four, fourteen seconds to one-oh-two. It opens on a guard forcing a man to the ground and cuts on a confession nobody answers."

*Point at the intensity curve.*

> "The curve is the mechanism: intensity from those tone tags. Spike early, cut while it's high."

---

## Shot 4 · 1:16–1:52 · How I know it isn't just plausible

*Click **Rejected · 44**, open one gate failure so a transcript is on screen.*

> "Every candidate also goes to a second model with no logline and nothing either side. Seven failed and don't ship; their transcripts do.
>
> But the number I'd defend: every pick runs against a random legal window from the same episode. The judge preferred whichever clip it read second, so I ran both orders and counted pairs, not judgements. Seventy-seven percent, p nought-nought-three. Against a window that already passes the hook filter, seventy-three — and that drop is the honest part."

---

## Shot 5 · 1:52–2:24 · The limit, and what I didn't ship

*Back to the ranked list.*

> "It reads text, so it can't see whether a shot is any good. And it embellishes: that top hook says 'blood and dust'; the screenplay says 'stone dust'.
>
> I also built three scoring improvements and didn't ship them: they changed eight of forty-three picks and I couldn't re-run the blind test in time. Shipping better promos beside a number describing the old ones would've been the one dishonest thing here. It's in the git history."

---

### If they ask for a live run

Sidebar uploader, then **Find promos**. One unseen episode is about three calls and six seconds. Say the call count out loud before you press it, so the cost is on the record.

### Every number said out loud, and where to check it

| Said | Source |
|---|---|
| 50 episodes · 47 promos | `outputs/promos.json` → `counts.shipped` |
| 92 of 92 validators | `outputs/eval_report.md` §1 — 47 shipped + 44 rejected + 1 flagship |
| 7 gate failures · 44 rejected | `outputs/eval_report.md` §3 |
| ep 44, `00:14.00` → `01:02.40` | `outputs/promos.json` → rank 1, blind test 4/4 |
| 77.4%, p = 0.003 · 73.3% | `outputs/ab_test_balanced.json` → `win_rate_decisive_pairs` |
| 8 of 43 picks changed | git history, the reverted improvement |

On screen but not narrated, if anyone pauses the video: 3,727 beats, 22 source defects reported rather than repaired, 18,141 legal windows, 3,376 rejected for having no hook in the first three seconds, 1,472 of 1,487 dialogue beats tone-tagged.

### If you're running fast, add this back

After shot 3's first paragraph, the one line worth 7 seconds:

> "Each carries a hook type, so an editor can spread them instead of posting four slaps in a row."

It's cut by default only because it's the least essential thing in the script, not because it's weak — it's the one line showing the taxonomy came from reading what ReelShort and DramaBox actually do. Never cut the stone-dust example or the unshipped improvements instead: the brief asks where AI got it wrong and what you'd do differently, and those two carry it.
