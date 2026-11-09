# Video script — about 2:00, read word for word

Every line is a complete sentence. Read it exactly as written. You do not need to add anything while you talk.

**Before you record**

1. **Rotate the Groq key**, then move the env file aside: `mv .env .env.hold`. Put it back afterwards. With no key there, the sidebar shows the "no API key" message, which is what makes paragraph 2 true on screen.
2. Start the app and open it in the browser. Hide the terminal.
3. Do one run before you record. Then the results are already on screen if the live press goes wrong.
4. Read the script out loud once. If a line feels awkward in your mouth, change that line.

**Length.** 292 words. That is 1:56 at a normal speaking speed, and about 2:05 with pauses. Even at a slow pace it only reaches 2:14, and the brief allows 3 minutes, so there is no need to hurry.

---

## The script

*Screen: the app is open, sidebar visible.*

**1.** Kuku puts out fifty new episodes every week, and right now a person watches all fifty by hand to find the clips worth posting. This tool reads the scripts and returns a ranked list instead.

*Screen: point at the sidebar, then press **Find promos**.*

**2.** I am running it now. There is no API key here, because every model answer is already saved. Anyone can download this and get the same result.

*Screen: the four cards along the top.*

**3.** It found forty-seven promos from fifty episodes, and it invented zero timestamps.

*Screen: open **How it ran** and move down the funnel table.*

**4.** Here is how it works. It breaks the scripts into three thousand seven hundred beats, each with a start and an end time. It cuts every possible clip between twenty and sixty seconds, which gives eighteen thousand clips. It scores each one on its opening, its tension, its ending, and whether it stands alone. Any clip with nothing in the first three seconds is deleted. Then the model picks one promo per episode. It only sees beat numbers and never sees times, so it cannot invent a timestamp.

*Screen: open **Rejected**.*

**5.** Every promo also has to pass a blind test, where a second model sees only the clip and has to say who is in it and what is at stake. Seven promos failed, so I dropped them.

*Screen: open **Ranked** and point at the Score column.*

**6.** The four scores are then combined into one. The top promo scored zero point eight seven six, but by score it was only tenth. The model moved it to first place, because a formula cannot judge which promo is best to post first.

*Screen: stay on **Ranked**.*

**7.** To check that this beats guessing, I put every promo against a random clip from the same episode. A blind judge preferred mine seventy-seven percent of the time.

*Screen: stay where you are.*

**8.** The tool only reads text, so it cannot tell whether a shot looks good. That is the first thing I would fix.

---

## The same script with nothing in between

Read straight down. Blank lines are where to breathe.

Kuku puts out fifty new episodes every week, and right now a person watches all fifty by hand to find the clips worth posting. This tool reads the scripts and returns a ranked list instead.

I am running it now. There is no API key here, because every model answer is already saved. Anyone can download this and get the same result.

It found forty-seven promos from fifty episodes, and it invented zero timestamps.

Here is how it works. It breaks the scripts into three thousand seven hundred beats, each with a start and an end time. It cuts every possible clip between twenty and sixty seconds, which gives eighteen thousand clips. It scores each one on its opening, its tension, its ending, and whether it stands alone. Any clip with nothing in the first three seconds is deleted. Then the model picks one promo per episode. It only sees beat numbers and never sees times, so it cannot invent a timestamp.

Every promo also has to pass a blind test, where a second model sees only the clip and has to say who is in it and what is at stake. Seven promos failed, so I dropped them.

The four scores are then combined into one. The top promo scored zero point eight seven six, but by score it was only tenth. The model moved it to first place, because a formula cannot judge which promo is best to post first.

To check that this beats guessing, I put every promo against a random clip from the same episode. A blind judge preferred mine seventy-seven percent of the time.

The tool only reads text, so it cannot tell whether a shot looks good. That is the first thing I would fix.

---

## Where to click, in order

| At paragraph | Do this |
|---|---|
| 1 | Nothing. The app is already open. |
| 2 | Point at the sidebar, then press **Find promos** |
| 3 | Point at the four cards along the top |
| 4 | Open **How it ran**, move down the funnel table |
| 5 | Open **Rejected** |
| 6 | Open **Ranked**, point at the Score column |
| 7 and 8 | Nothing. Stay on **Ranked**. |

## Every number is checked

| You say | Checked against |
|---|---|
| fifty episodes, three thousand seven hundred beats | `outputs/parse_report.json` |
| eighteen thousand clips | funnel row 1, 18,141 |
| forty-seven promos, zero invented timestamps | the **Promos** and **Invented timestamps** cards |
| seven promos failed | funnel row 7, and the **Rejected** tab |
| zero point eight seven six, only tenth | Ranked table row 1 |
| seventy-seven percent | `outputs/ab_test_balanced.json` |

Two of them are worth understanding, in case you are asked.

**"Only tenth" is true and it is the best part.** The top promo is genuinely not the highest scorer. It scored 0.876. The formula's favourite scored 0.941 and sits at rank 9, and that one only got 3 out of 4 on the blind test while the top one got 4 out of 4. You can see this on screen: the Score column is not in descending order at the top, and the "Ordered by" column says `model`.

**Seventy-seven percent is 77.4% rounded.** It counts the 31 pairs where the judge gave the same answer with the clips shown in both orders. The log file also shows 72.4%, which counts all 76 judgements including the ones that flipped when the order changed. Both are correct, and the solution doc uses the pair-level number.

## Two things not to say

Do not say "ninety-two of ninety-two". The written doc uses that number and it is correct there, but the screen shows ninety-one. Only say what is visible.

Do not read `1:02` as "one colon zero two". Say "one minute two".
