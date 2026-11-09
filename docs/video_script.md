# Walkthrough script — features, then how ranking works

A tour of the app, then the six steps that turn 50 scripts into 47 ranked promos. Everything happens inside the web app. No terminal, no code on screen.

**Before you record**

1. **Rotate the Groq key**, then move the env file aside: `mv .env .env.hold`. Put it back afterwards.
   With no key there, the sidebar says *"No GROQ_API_KEY set. The bundled pack still runs from cached responses"*, so your reproducibility claim is visible rather than just spoken. Checked: the button still works and you still get all 47 promos.
2. Start the app, open it in the browser, then hide the terminal.
3. Open the **How it ran** tab once before you start. Steps 1 to 5 are all rows in its funnel table, so you can point at each row as you say it instead of hunting for numbers live.
4. **Read it out loud once first.** If a line makes you stumble, change it.

**On length.** 402 words, which is 2:40 at a normal speaking speed and 2:52 if you go slowly. The video lands at 2:48 with the pauses. The brief allows up to 3 minutes. Part 2 is the important half, so if you run long, trim Part 1 rather than the steps.

---

# Part 1 · What's in the app

## Shot 1 · 0:00–0:28 · The problem, and the sidebar

*App just loaded, sidebar visible.*

> Kuku puts out fifty new episodes every week. Right now, someone watches all fifty by hand to find the clips worth posting. This reads the scripts and gives back a ranked list instead.
>
> In the sidebar you can drop in your own scripts, pick a model, and press one button. And there's no API key here. Every model answer is already saved, so anyone can run this and get the same output.

## Shot 2 · 0:28–0:54 · The four numbers, and the three tabs

*Press **Find promos**. When it finishes, point at each card, then each tab.*

> Four numbers at the top. How many promos it found. How many passed a blind test. Zero made-up timestamps. And what the run cost.
>
> Then three tabs. Ranked is the list, with start and end times and a download button. Rejected shows what it threw away and why. And How it ran shows every step and every call it made.

---

# Part 2 · How a promo gets ranked

*Stay on **How it ran** for steps 1 to 5. Point at each funnel row as you say its number.*

## Step 1 · 0:54–1:07 · Read the scripts

> Step one. It reads all fifty scripts and breaks them into three thousand seven hundred beats. Every line, every action, every camera note, each with a start and end time.

## Step 2 · 1:07–1:24 · Cut every possible clip and score it

> Step two. It cuts every clip between twenty and sixty seconds long, always starting and ending on a real beat. That's eighteen thousand clips. Each gets four scores: the opening, the tension, the ending, and whether it stands alone.

## Step 3 · 1:24–1:39 · Throw away the weak ones

> Step three. If nothing happens in the first three seconds, it's gone. That removes three thousand clips. Then it keeps only the best few from each episode. Eighteen thousand becomes a hundred and seventy-one.

## Step 4 · 1:39–1:57 · Let the model choose

> Step four. Now the model gets involved, once per episode. It picks from that short list and writes the hook and the ending line. It only ever sees beat IDs, never times, so it can't make up a timestamp. That gives ninety-one promos.

## Step 5 · 1:57–2:15 · Check them and clean up

> Step five. Six hard rules check every promo, and all ninety-one pass. Then it removes near-copies: thirty-seven showed almost the same thing as a better one. And a second model sees only the clip and answers four questions. Seven failed. Forty-seven are left.

## Step 6 · 2:15–2:48 · Put them in order

*Switch to the **Ranked** tab. Point at the Score column, then the "Ordered by" column.*

> Step six. The four scores combine into one. Opening and ending count thirty percent each, tension and standalone twenty each.
>
> Number one here scored point eight seven six. But by score alone, it was only tenth. The model moved it to the top, because a formula can't tell which promo is best to post first. The highest score sits at number nine.
>
> One honest limit. It only reads text, so it can't tell you whether a shot actually looks good.

---

# Read-through — just the words

No stage directions. Line breaks are where to breathe.

Kuku puts out fifty new episodes every week. Right now, someone watches all fifty by hand to find the clips worth posting. This reads the scripts and gives back a ranked list instead.

In the sidebar you can drop in your own scripts, pick a model, and press one button. And there's no API key here. Every model answer is already saved, so anyone can run this and get the same output.

Four numbers at the top. How many promos it found. How many passed a blind test. Zero made-up timestamps. And what the run cost.

Then three tabs. Ranked is the list, with start and end times and a download button. Rejected shows what it threw away and why. And How it ran shows every step and every call it made.

Step one. It reads all fifty scripts and breaks them into three thousand seven hundred beats. Every line, every action, every camera note, each with a start and end time.

Step two. It cuts every clip between twenty and sixty seconds long, always starting and ending on a real beat. That's eighteen thousand clips. Each gets four scores: the opening, the tension, the ending, and whether it stands alone.

Step three. If nothing happens in the first three seconds, it's gone. That removes three thousand clips. Then it keeps only the best few from each episode. Eighteen thousand becomes a hundred and seventy-one.

Step four. Now the model gets involved, once per episode. It picks from that short list and writes the hook and the ending line. It only ever sees beat IDs, never times, so it can't make up a timestamp. That gives ninety-one promos.

Step five. Six hard rules check every promo, and all ninety-one pass. Then it removes near-copies: thirty-seven showed almost the same thing as a better one. And a second model sees only the clip and answers four questions. Seven failed. Forty-seven are left.

Step six. The four scores combine into one. Opening and ending count thirty percent each, tension and standalone twenty each.

Number one here scored point eight seven six. But by score alone, it was only tenth. The model moved it to the top, because a formula can't tell which promo is best to post first. The highest score sits at number nine.

One honest limit. It only reads text, so it can't tell you whether a shot actually looks good.

---

### Every number, and where it's on screen

| You say | Where it is |
|---|---|
| fifty scripts · three thousand seven hundred beats | How it ran → Source data |
| eighteen thousand clips | Funnel row 1 (18,141) |
| removes three thousand | Funnel row 2 (3,376) |
| a hundred and seventy-one | Funnel row 3 |
| ninety-one promos | Funnel row 4 |
| six rules, all ninety-one pass | Funnel row 5 (0 failures) · **Invented timestamps** card |
| thirty-seven near-copies | Funnel row 6 · Rejected tab |
| seven failed the blind test | Funnel row 7 · **Passed blind test** card, 47/54 |
| forty-seven left | Funnel row 8 · **Promos** card |
| thirty / twenty / thirty / twenty percent | Ranked tab → "How this list is ordered" |
| point eight seven six | Ranked table row 1, Score column |
| only tenth · highest sits at number nine | Score column isn't descending at the top, and "Ordered by" says `model` |

### The two things worth getting right

**The maths reconciles, so you can say it with confidence.** 0.30 × 1.0, plus 0.20 × 0.751, plus 0.30 × 0.94, plus 0.20 × 0.719, equals 0.876 exactly. The sub-scores are in the detail panel if anyone wants to check.

**Number one is genuinely not the top scorer, and that's the point of step 6.** It scored 0.876 and ranked tenth on score alone. The formula's favourite, 0.941, is sitting at rank 9 — and it only got 3 out of 4 on the blind test, while number one got 4 out of 4. So don't say "the highest score"; say it was tenth and the model moved it. That one sentence explains why there's a model in the ranking at all, and a reviewer can verify it on screen in two seconds.

### Two things not to say

Don't say "ninety-two of ninety-two". That's right in the written doc, where it counts the flagship promo too, but the funnel on screen says ninety-one. Say what's on screen.

Don't read `1:02` as "one colon zero two". It's "one-oh-two".

### If you have twenty seconds spare

You're at 2:48 and the brief allows three minutes. If you want the strongest thing in the submission, add this at the very end:

> I also built three improvements that work, and I left them out. They changed eight of my forty-three picks, and I couldn't run the blind test again in time. Showing better promos next to a score from the old ones felt wrong. It's in the git history.

The brief asks where AI got things wrong and what you'd do differently. The solution doc answers that in writing, but saying it out loud is what people remember.
