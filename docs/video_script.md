# Walkthrough script — 2:27, prototype only

Everything happens inside the web app. No terminal, no editor, no files on screen.

**Before you record**

1. **Rotate the Groq key**, then move the env file aside: `mv .env .env.hold`. Put it back afterwards.
   This isn't only about key safety. With no key present, the sidebar prints *"No GROQ_API_KEY set. The bundled pack still runs from cached responses, which is how this reproduces without credentials."* So the biggest claim in your video becomes something the viewer can see, not something you just say. Verified: the button still works and you still get all 47 promos.
2. Start the app, open it in the browser, then hide the terminal for the whole recording.
3. Zoom so the stat strip and the first few table rows fit on screen together.
4. **Read it out loud once before recording.** If a sentence makes you stumble, change it. It's your voice, and a line you can't say naturally is worse than a line that's slightly less clever.

**On length.** 355 words as written, which is 2:22 at a normal speaking pace and lands the video at 2:27 with the pauses. One sentence in shot 4 is marked *(optional)*: if you read slowly, drop it and you are back to 2:21 even at a slow pace.

---

## Shot 1 · 0:00–0:25 · The problem, and the sidebar

*App freshly loaded. Sidebar visible with the no-key message.*

> Kuku ships fifty new episodes every week. And right now, an editor watches all fifty by hand to find the clips worth posting.
>
> This reads the screenplays instead, and gives back a ranked shortlist.
>
> Before I run it, look at the sidebar. There's no API key set. Every response is already cached, so anyone can clone this and get the same output.

---

## Shot 2 · 0:25–0:55 · Press it, then read the top line

*Press **Find promos**. Let the log lines and spinner play. Takes about a second.*

> Fifty episodes, about a second, and zero live calls. All hundred and seven came from cache.
>
> Forty-seven promos.

*Point at the **Invented timestamps** card.*

> And this is the card I care about. Zero invented timestamps.
>
> The model never sees a timestamp, and it never writes one. It picks moments by ID, and my code looks up the real time. So a made-up timestamp isn't unlikely here. It's impossible.

---

## Shot 3 · 0:55–1:21 · The output, and how it finds them

*Ranked tab. Table is already at the top. Scroll it once, then move down to the detail panel, already on rank 1.*

> All forty-seven, ranked.
>
> Number one is episode forty-four. Fourteen seconds, to one-oh-two. It opens on a guard slamming a man to the ground, and it cuts on a confession nobody answers.

*Point at the intensity curve.*

> This curve is how it finds them. The screenplays already tell you how every line is delivered. Cold and commanding. Screaming, desperate. So I never have to guess where the drama is.

---

## Shot 4 · 1:21–1:59 · How I know it isn't just plausible

*Rejected tab. Open one blind-test failure so the transcript and its four answers are on screen.*

> Every promo also has to get past a second model that only sees the clip. Seven of them failed, and they're all here with the transcripts.
>
> The number I'd really defend is in the evaluation report.
>
> I put every pick against a random clip from the same episode, and let a blind judge choose. Mine wins about seventy-seven percent of the time. And when I make the random clip start strong too, it still wins seventy-three.
>
> That gap is the honest part. *(optional)* A strong opening does most of the work, and my scoring adds the rest.

---

## Shot 5 · 1:59–2:27 · The limits, and what I didn't ship

*"How it ran" tab. Show the funnel, then open the raw requests expander and leave it open while you talk.*

> Now the limits. It embellishes. That top promo says "blood and dust", when the screenplay only says "stone dust".
>
> And one last thing. I built three improvements that work, and I didn't ship them. They changed eight of my forty-three picks, and I couldn't re-run the blind test in time. Shipping better promos next to a number that measured the old ones didn't feel honest. It's all in the git history.

---

# Read-through — just the words

No stage directions. Line breaks are where to breathe. Bold is where to lean in, not where to slow down.

Kuku ships fifty new episodes every week. And right now, an editor watches all fifty by hand to find the clips worth posting.

This reads the screenplays instead, and gives back a ranked shortlist.

Before I run it, look at the sidebar. There's **no API key set**. Every response is already cached, so anyone can clone this and get the same output.

Fifty episodes, about a second, and **zero live calls**. All hundred and seven came from cache.

Forty-seven promos.

And this is the card I care about. **Zero invented timestamps.**

The model never sees a timestamp, and it never writes one. It picks moments by ID, and my code looks up the real time. So a made-up timestamp isn't unlikely here. It's **impossible**.

All forty-seven, ranked.

Number one is episode forty-four. Fourteen seconds, to one-oh-two. It opens on a guard slamming a man to the ground, and it cuts on a confession nobody answers.

This curve is how it finds them. The screenplays already tell you how every line is delivered. Cold and commanding. Screaming, desperate. So I never have to guess where the drama is.

Every promo also has to get past a second model that only sees the clip. Seven of them failed, and they're all here with the transcripts.

The number I'd really defend is in the evaluation report.

I put every pick against a random clip from the same episode, and let a blind judge choose. Mine wins about **seventy-seven percent** of the time. And when I make the random clip start strong too, it still wins seventy-three.

That gap is the honest part. A strong opening does most of the work, and my scoring adds the rest.

Now the limits. It embellishes. That top promo says "blood and dust", when the screenplay only says "stone dust".

And one last thing. I built three improvements that work, and I didn't ship them. They changed eight of my forty-three picks, and I couldn't re-run the blind test in time. Shipping better promos next to a number that measured the old ones **didn't feel honest**. It's all in the git history.

---

### Reading notes

Four places people rush, and shouldn't:

- **"It's impossible."** Put a full stop before it. It's the strongest claim in the video and it's load-bearing, so let it sit for a beat.
- **"Zero live calls."** Point at the Cost card as you say it. The number is on screen, so let them read it while you talk.
- **"Seventy-seven percent... it still wins seventy-three."** Say both numbers slowly. The second is lower on purpose, and the next line explains why. If you rush it, it sounds like a mistake instead of a choice.
- **"didn't feel honest."** Don't hedge it and don't laugh after it. It's the best thing in the submission.

Two habits to avoid. Don't open a shot with "um, so" — just start. And read `1:02` as "one-oh-two", not "one colon zero two".

### Where each number is on screen

| You say | Where it is |
|---|---|
| fifty episodes | **Promos** card, sub-line |
| forty-seven promos | **Promos** card, and the Ranked tab |
| zero live calls, hundred and seven cached | **Cost** card |
| zero invented timestamps | **Invented timestamps** card |
| seven failed | **Passed blind test** card, 47/54, and the Rejected tab |
| episode forty-four, fourteen seconds to one-oh-two | Ranked table row 1, and the detail panel |
| seventy-seven percent · seventy-three | **Not on screen.** That's exactly why you say "it's in the evaluation report". Source: `outputs/ab_test_balanced.json`, written up in `outputs/eval_report.md` §2 |
| eight of forty-three picks | **Not on screen.** Git history |

### Two things not to say

Don't say "ninety-two of ninety-two validators". That number is correct in the written doc, where it counts rejected promos and the flagship as well. But the card on screen says **47 / 47**, and saying a number that doesn't match what someone is looking at costs you more than the bigger number gains.

Don't say "p equals point zero zero three". It's in the doc for anyone who wants it. Out loud it sounds like you're reading a stats table, and "about seventy-seven percent" followed by "that gap is the honest part" already lands the point with anyone who'd care.

### If you have ten seconds spare

Add this back into shot 5, before "It embellishes":

> It reads text, so it can't tell you whether a shot actually looks good.

It's the cleanest statement of the real limitation, and it's cut only because it was the least essential line in a tight edit. Never cut the stone-dust example or the unshipped improvements to make room — the brief specifically asks where AI got it wrong and what you'd do differently, and those two carry it.
