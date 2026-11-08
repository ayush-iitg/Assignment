# Submission checklist — do these in order

## 1. Rotate the API key (2 min, do this first)

The key you pasted into chat is in `.env` and will appear in any terminal screen recording. Go to [console.groq.com/keys](https://console.groq.com/keys), delete it, create a new one, and update `.env`. `.env` is gitignored, so it never reaches GitHub either way.

## 2. Your details

Fill the placeholders in `docs/solution_doc.md`:
- roll number and branch in the header
- the three `<link>` placeholders once you have them

## 3. Review the gold set — the one thing only you can do

`docs/gold_set.json` holds 6 hand-picked promos that the whole evaluation leans on. I drafted them from the beat sheets during the audit. **In the interview you will be asked why these are good promos, so they need to be yours.**

```bash
open docs/_beatsheets.txt      # all 50 episodes, readable, timestamped
```

Keep, change or delete any entry, then:

```bash
python evaluate.py             # regenerates outputs/eval_report.md with your picks
```

Then update the gold-set numbers in `docs/solution_doc.md` §"How I know it's good" if they move.

## 4. Push to GitHub

```bash
cd /Users/apple/Desktop/KUKU
git init
git add .
git commit -m "Promo Finder: Kuku AI Generalist assignment, Problem 1"
git branch -M main
git remote add origin https://github.com/<you>/kuku-promo-finder.git
git push -u origin main
```

Check before pushing: `git status` must NOT list `.env`. If it does, stop and fix `.gitignore`.

## 5. Deploy the UI (5 min)

1. [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Pick the repo, branch `main`, main file `app.py`
3. **Advanced settings → Secrets** → paste the contents of `.streamlit/secrets.toml.example` with your real key
4. Deploy. First build takes ~2 minutes.
5. Open the link in a private window to confirm it loads for anyone.

If the deploy fights you, the brief explicitly accepts a repo with clear run steps — `README.md` has them. Don't burn an hour on hosting.

## 6. Solution doc → PDF (2 pages max)

```bash
# easiest: open in a markdown editor and export, or
pandoc docs/solution_doc.md -o solution_doc.pdf --pdf-engine=xelatex -V geometry:margin=0.6in -V fontsize=9pt
```

Check it is **2 pages**. If it spills, cut in this order: the assumptions table (link to the repo instead), then the scale table's third row, then trim "Where it fails" from 7 items to 5. Do **not** cut the AI-mistakes section or the 0.44-vs-0.46 finding — those are the strongest parts.

## 7. Raw outputs link

Zip and upload to Drive, share "anyone with the link":

```bash
zip -r kuku_raw_outputs.zip outputs/ outputs_qwen/ outputs_nollm/ outputs_unseen/ -x "*.DS_Store"
```

Contains: `promos.json`, `promos.md`, `rejected_promos.json`, `parse_report.json`, `eval_report.md`, `tension_curves.json`, and `raw/` with every unedited request/response pair.

## 8. Video (optional, recommended)

Script with timings: `docs/video_script.md`. Record with a full run already cached so nothing waits on the network. 2:55 of content.

## 9. Form

- Problem chosen: **Problem 1 — Find the Promos**
- Prototype link: Streamlit URL (or repo URL)
- Raw outputs: Drive link from step 7
- Solution doc: the PDF from step 6

---

## Before the interview

Read `docs/interview_defense.md`. Memorise the numbers table at the bottom. Be ready to volunteer the four things in "Things I should volunteer rather than wait to be asked" — especially that code-only scores 0.44 against your hand-picks and the full pipeline 0.46.

Dry-run the live re-run once:

```bash
streamlit run app.py
# upload samples/sample_episode.txt, press Find promos
```

Know where the no-LLM checkbox is. If their network or the API misbehaves on the day, tick it and keep talking.
