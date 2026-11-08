# 3-minute walkthrough script

Record with the web UI already loaded and a full run cached, so nothing waits on the network. Terminal font large. Say the numbers out loud — they're the point.

**Total: 2:55. Four shots.**

---

## 0:00–0:22 · The problem, and the thing I noticed (talking over the parse report tab)

> "Kuku ships a new show every week, fifty episodes each, and today an editor watches all fifty to hand-pick the clips worth posting. I built a tool that reads the screenplays and hands them a ranked shortlist instead.
>
> The reason this is tractable is sitting in Kuku's own files. Look — every line of dialogue is labelled with how it's delivered. *Cold, commanding. Screaming, desperate.* Fourteen hundred and seventy-two of fourteen eighty-seven dialogue beats have one. So I don't need an AI to guess where the drama is. The script already says."

*Show: the parse report tab — tone-tag coverage 99%, 617 distinct tags, the alias map.*

---

## 0:22–0:50 · The run (terminal)

> "One command on all fifty episodes."

```bash
python run.py --input data
```

> "Thirty-seven hundred beats parsed. Twenty-two hazards in the source data, reported not swallowed — one episode has a scene header glued onto a line of dialogue. Eighteen thousand legal twenty-to-sixty-second windows, snapped to real beat boundaries. Three thousand rejected because nothing happens in the first three seconds. A hundred and seventy-two go to the model.
>
> A hundred and two API calls. Free tier. All six validators pass fifty-one out of fifty-one."

*Point at the `timestamps_exist: 51/51` line.*

> "That line is the whole design. The model never sees a timestamp and never writes one — it answers in beat IDs, and my code looks up the time. A hallucinated timestamp isn't something this thing can produce."

---

## 0:50–1:45 · The output an editor would use (ranked promos tab)

> "Thirty-nine promos, ranked. Episode twenty-four, one-oh-seven-point-five to one-twenty-nine-point-eight. It opens on a riding crop hitting someone across the face — no dialogue needed, that's the scroll-stopper — and it cuts on a threat nobody answers.
>
> Each one gets a hook type: moral outrage, power reversal, empathy shock, romantic tension. That's DramaBox's own taxonomy, and it's there so an editor can spread the types instead of posting four slaps in a row."

*Open the tension curves tab.*

> "And here's the mechanism, visible. This is intensity per second built from those tone tags. A promo is a shape on this curve — a spike inside the first three seconds, a rising edge, and a cut while it's still high. That's the whole thesis in one picture."

---

## 1:45–2:30 · The part I'd want to be asked about (rejected tab)

> "Now the bit I care about. The brief says a promo has to make sense to someone who's never seen the show. Everyone will claim that. I measured it.
>
> Every candidate goes to a second model with everything stripped out — no logline, no episode number, no surrounding scenes. Just the clip. Four questions: who is this, what's at stake, what are you left wondering, would you keep watching.
>
> Five promos failed. Here's one at one out of four — strong structural score, and the blind reader said 'unclear from the clip.' The transcript ships with it.
>
> And episode thirty-one was *my* favourite pick. I chose it by hand during the audit, before I wrote any of this. It shipped nothing — the tool picked a different window and then suppressed it as a near-duplicate of episode thirty-two, because both episodes end on the same image of a branding iron next to the heroine's eye. I predicted that repeat in my audit document and then built the check that caught it."

---

## 2:30–2:55 · Re-runnable, and the honest limit

> "Different model, no code change."

```bash
python run.py --input samples --model qwen/qwen3.8-27b
```

> "And if the API dies mid-demo, `--no-llm` still produces the full ranked list from the deterministic scorer.
>
> One number I'd put in front of you before you ask: with the model switched off entirely, agreement with my hand-picked promos is point four four. With the full pipeline it's point four six. The model is not finding better moments — the lexicon is doing that work. What the model earns its place for is writing the copy and running the blind test.
>
> The honest limit: this reads text, so it can't see whether a shot is any good or whether the actor landed the line. I'm reading sheet music and guessing at the performance. Give me frames and that's the first thing I'd fix."

---

### If a live re-run is requested instead of the recording

Upload their file in the UI, leave "use cached responses" on, keep the no-LLM checkbox visible as the fallback. A single unseen episode is ~3 calls and about ten seconds. Say the call count out loud before pressing run.
