# Walkthrough script — 2:27, prototype only

Everything happens inside the web app. No terminal, no editor, no files on screen.

**Before you record**

1. **Rotate the Groq key**, then move the env file aside: `mv .env .env.hold`. Put it back afterwards.
   This isn't only about key safety. With no key there, the sidebar prints *"No GROQ_API_KEY set. The bundled pack still runs from cached responses, which is how this reproduces without credentials."* So the biggest claim in your video is something people can see, not just something you say. Checked: the button still works and you still get all 47 promos.
2. Start the app, open it in the browser, then hide the terminal for the whole recording.
3. Zoom in so the four cards at the top and the first few table rows fit on screen together.
4. **Read it out loud once before you record.** If a line makes you stumble, change it. It's your voice, and a line you can't say easily is worse than a line that sounds clever.

**On length.** 356 words. That's 2:22 at a normal speaking speed, and the video lands at 2:27 with the pauses. One line in shot 4 is marked *(optional)*: drop it if you speak slowly, and you're still at 2:26.

---

## Shot 1 · 0:00–0:25 · The problem, and the sidebar

*App just loaded. Sidebar showing the no-key message.*

> Kuku puts out fifty new episodes every week. Right now, someone watches all fifty by hand to find the clips worth posting.
>
> This reads the scripts and gives back a short list, best first.
>
> Before I run it, look at the sidebar. There's no API key here. Every model answer is already saved, so anyone can run this and get the same result.

---

## Shot 2 · 0:25–0:55 · Press it, then read the top line

*Press **Find promos**. Let the log lines and the spinner play. Takes about a second.*

> Fifty episodes, about one second, and zero live calls. All hundred and seven came from the saved ones.
>
> Forty-seven promos.

*Point at the **Invented timestamps** card.*

> And this is the one I care about. Zero made-up timestamps.
>
> The model never sees a time, and it never writes one. It picks a moment by its ID, and my code looks up the real time. So it can't make up a time. Not unlikely. Impossible.

---

## Shot 3 · 0:55–1:21 · The list, and how it finds them

*Ranked tab. The table is already at the top. Scroll it once, then move down to the panel below, already showing number one.*

> All forty-seven, best first. Number one is episode forty-four. Fourteen seconds, to one-oh-two. It starts with a guard throwing a man to the ground, and it ends on a confession nobody answers.

*Point at the curve.*

> This curve is how it finds them. The scripts already say how every line should be said. Cold and commanding. Screaming, desperate. So I never have to guess where the drama is.

---

## Shot 4 · 1:21–1:59 · How I know it's actually good

*Rejected tab. Open one failed promo so its answers are on screen.*

> Each promo also faces a second model that only sees the clip. Seven failed. They're all here, with the reasons.
>
> But the real proof is in the evaluation report.
>
> I tested every pick against a random clip from the same episode. A blind judge picked the better one. Mine won seventy-seven percent of the time. Then I made the random clip start strong too. Mine still won seventy-three.
>
> That drop is the honest part. *(optional)* A strong start does a lot of the work, and my scoring adds the rest.

---

## Shot 5 · 1:59–2:27 · What it can't do, and what I left out

*"How it ran" tab. Show the funnel, then open the raw requests box and leave it open while you talk.*

> Now the limits. Sometimes it adds things that aren't there. That top promo says "blood and dust". The script only says "stone dust".
>
> One last thing. I built three improvements that work, and I left them out. They changed eight of my forty-three picks, and I couldn't run the blind test again in time. Showing better promos next to a score from the old ones felt wrong. It's in the git history.

---

# Read-through — just the words

No stage directions. Line breaks are where to breathe. Bold is where to lean in, not where to slow down.

Kuku puts out fifty new episodes every week. Right now, someone watches all fifty by hand to find the clips worth posting.

This reads the scripts and gives back a short list, best first.

Before I run it, look at the sidebar. There's **no API key here**. Every model answer is already saved, so anyone can run this and get the same result.

Fifty episodes, about one second, and **zero live calls**. All hundred and seven came from the saved ones.

Forty-seven promos.

And this is the one I care about. **Zero made-up timestamps.**

The model never sees a time, and it never writes one. It picks a moment by its ID, and my code looks up the real time. So it can't make up a time. Not unlikely. **Impossible.**

All forty-seven, best first. Number one is episode forty-four. Fourteen seconds, to one-oh-two. It starts with a guard throwing a man to the ground, and it ends on a confession nobody answers.

This curve is how it finds them. The scripts already say how every line should be said. Cold and commanding. Screaming, desperate. So I never have to guess where the drama is.

Each promo also faces a second model that only sees the clip. Seven failed. They're all here, with the reasons.

But the real proof is in the evaluation report.

I tested every pick against a random clip from the same episode. A blind judge picked the better one. Mine won **seventy-seven percent** of the time. Then I made the random clip start strong too. Mine still won seventy-three.

That drop is the honest part. A strong start does a lot of the work, and my scoring adds the rest.

Now the limits. Sometimes it adds things that aren't there. That top promo says "blood and dust". The script only says "stone dust".

One last thing. I built three improvements that work, and I left them out. They changed eight of my forty-three picks, and I couldn't run the blind test again in time. Showing better promos next to a score from the old ones **felt wrong**. It's in the git history.

---

### Reading notes

Four places people rush, and shouldn't:

- **"Impossible."** Stop fully before it. It's the strongest thing you say, so let it sit for a beat.
- **"Zero live calls."** Point at the Cost card as you say it. The number is right there, so let them read it while you talk.
- **"Seventy-seven percent... still won seventy-three."** Say both numbers slowly. The second one is lower on purpose, and the next line explains why. Rush it and it sounds like a mistake instead of a choice.
- **"felt wrong."** Don't soften it, and don't laugh after it. It's the best thing in the whole submission.

Two habits to avoid. Don't start a shot with "um, so" — just start. And say `1:02` as "one-oh-two", not "one colon zero two".

### Where each number is on screen

| You say | Where it is |
|---|---|
| fifty episodes | **Promos** card, small line underneath |
| forty-seven promos | **Promos** card, and the Ranked tab |
| zero live calls, hundred and seven saved | **Cost** card |
| zero made-up timestamps | **Invented timestamps** card |
| seven failed | **Passed blind test** card, 47/54, and the Rejected tab |
| episode forty-four, fourteen seconds to one-oh-two | First row of the table, and the panel below it |
| seventy-seven percent · seventy-three | **Not on screen.** That's exactly why you say "it's in the evaluation report". It comes from `outputs/ab_test_balanced.json`, written up in `outputs/eval_report.md` §2 |
| eight of forty-three picks | **Not on screen.** Git history |

### Two things not to say

Don't say "ninety-two of ninety-two". That number is right in the written doc, where it also counts the rejected promos and the flagship. But the card on screen says **47 / 47**, and saying a number that doesn't match what someone is looking at costs you more than the bigger number gains.

Don't say "p equals point zero zero three". It's in the doc for anyone who wants it. Out loud it sounds like you're reading off a stats table, and "seventy-seven percent" followed by "that drop is the honest part" already makes the point to anyone who'd care.

### If you have ten seconds spare

Add this to shot 5, just before "Sometimes it adds things that aren't there":

> It only reads text, so it can't tell you if a shot actually looks good.

That's the clearest way to say what the tool can't do, and it's left out only because it was the least important line in a tight edit. Never cut the stone-dust line or the part about leaving the improvements out — the brief asks where AI got things wrong and what you'd do differently, and those two are what answer it.
