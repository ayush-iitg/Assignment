# 3-minute walkthrough script

Record with the web UI already open and the repo already cloned. Nothing waits on the network — every model response is cached, so the full run completes in about a second. Terminal font large. **Rotate the Groq key before recording** — it's in `.env` and will appear on screen.

**Total 2:50. Five shots.**

---

## 0:00–0:22 · The problem, and the thing I noticed

*On screen: the Run details tab, source data panel.*

> "Kuku ships a new show every week, fifty episodes each, and today an editor watches all fifty by hand to pick the clips worth posting. I built a tool that reads the screenplays and hands them a ranked shortlist instead.
>
> The reason this is tractable is sitting in Kuku's own files. Every line of dialogue is already labelled with how it's delivered — *cold, commanding. screaming, desperate.* Fourteen hundred and seventy-two of fourteen eighty-seven dialogue beats have one. So I never need an AI to guess where the drama is. The script already says."

---

## 0:22–0:50 · It runs, with no API key

```bash
python run.py --input data
```

> "One command, all fifty episodes, one second. And note — I have no API key set here. Every model response from the full run is committed in the repo, so you can clone this and reproduce the exact output before you've signed up for anything.
>
> Thirty-seven hundred beats. Twenty-two defects in the source data, reported not swallowed. Eighteen thousand legal twenty-to-sixty-second windows, all snapped to real beat boundaries. Three thousand rejected because nothing happens in the first three seconds. Forty-seven promos ship."

*Point at `timestamps_exist: 92/92`.*

> "That line is the whole design. The model never sees a timestamp and never writes one — it answers in beat IDs, and my code looks up the time. A hallucinated timestamp isn't an output this thing can produce."

---

## 0:50–1:35 · The output an editor would use

*Promos tab. Click row 1, then the inspect dropdown.*

> "Forty-seven promos, ranked. Episode forty-four, fourteen seconds to one-oh-two. It opens on a guard forcing a man to the ground — no dialogue needed, that's the scroll-stopper — and it cuts on a confession nobody answers.
>
> Each one gets a hook type: moral outrage, power reversal, empathy shock, romantic tension. That's DramaBox's own taxonomy, and it's there so an editor can spread the types instead of posting four slaps in a row."

*Scroll to the intensity curve in the inspect panel.*

> "And here's the mechanism, visible. Intensity per second, built from those tone tags. A promo is a shape on this curve — a spike inside the first three seconds, a rising edge, and a cut while it's still high."

---

## 1:35–2:20 · How I know it's not just plausible

*Rejected tab. Open one of the 1-out-of-4 failures.*

> "The brief says a promo has to make sense to someone who's never seen the show. Everyone will claim that. I measured it. Every candidate goes to a second model with everything stripped out — no logline, no episode number, no surrounding scenes. Four questions. Seven promos failed and don't ship. The transcript ships instead.
>
> But the measure I'd actually defend is this one."

*Switch to `outputs/eval_report.md`, section 1b.*

> "I compare every pick against a **random legal window** from the same episode — same length rules, same real boundaries, just not selected. Blind judge, never sees a score. The tool wins seventy-six percent of the time.
>
> And here's the part I want you to see: the judge turned out to strongly prefer whichever clip came second — eighty-eight percent there versus forty-two percent shown first. So I re-ran the pairs in the opposite order. Two independent corrections agree. Against a window that *already* has a strong opening, the win rate drops to sixty-five percent — which tells me the hook rule is doing most of the work and my tension scoring adds a smaller real edge. That decomposition is more useful to me than the headline number."

---

## 2:20–2:50 · Re-runnable, and the honest limit

```bash
python run.py --input samples --model qwen/qwen3.8-27b
```

> "Different input, different model, no code change. Five providers wired.
>
> The honest limit: this reads text, so it can't see whether a shot is any good or whether the actor landed the line. And it embellishes — the top promo's hook says 'blood and dust flying' where the screenplay says 'stone dust'. The word blood appears nowhere in that episode. Timestamps are verified; descriptions are not, and a copy verifier is the next thing I'd build.
>
> Give me frames and the editor's accept-reject log, and those are the two weaknesses that close."

---

### If they ask for a live re-run instead

Upload their file in the UI sidebar and press **Find promos**. A single unseen episode is about three calls and ten seconds. Say the call count out loud before pressing it.
