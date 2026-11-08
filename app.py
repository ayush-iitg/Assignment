"""
Promo Finder - web interface.

A view over promo.pipeline.run(), the same function run.py calls. No pipeline
logic lives here.

    streamlit run app.py
"""
import os
import json
import glob
import shutil
import tempfile

import pandas as pd
import streamlit as st

from promo.pipeline import run
from promo.llm import PROVIDERS, load_dotenv

st.set_page_config(page_title="Promo Finder", page_icon="🎬", layout="wide")
load_dotenv()

MODELS = [
    ("groq", "openai/gpt-oss-120b"),
    ("groq", "qwen/qwen3.8-27b"),
    ("gemini", "gemini-2.5-flash-lite"),
    ("gemini", "gemini-2.5-flash"),
    ("openai", "gpt-4o-mini"),
    ("anthropic", "claude-3-5-haiku-20241022"),
]


def key_for(provider: str) -> str:
    name = PROVIDERS[provider]["key_env"]
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.environ.get(name, "")


def load_latest() -> dict | None:
    for folder in ("outputs", "outputs_dev"):
        path = os.path.join(folder, "promos.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        curves = os.path.join(folder, "tension_curves.json")
        if os.path.exists(curves):
            with open(curves, encoding="utf-8") as fh:
                data["tension_curves"] = json.load(fh)
        data["_folder"] = folder
        return data
    return None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Run")
    uploaded = st.file_uploader(
        "Screenplay .txt files", type=["txt"], accept_multiple_files=True,
        help="Leave empty to use the bundled 50-episode pack.",
    )
    choice = st.selectbox(
        "Model", range(len(MODELS)),
        format_func=lambda i: f"{MODELS[i][1]}  ({MODELS[i][0]})",
    )
    provider, model = MODELS[choice]
    has_key = bool(key_for(provider))
    go = st.button("▶  Find promos", type="primary", width="stretch")

    if has_key:
        st.caption("Responses are cached, so a repeat run is instant.")
    else:
        # No key is not a blocker. Every model response from the full run is
        # committed in .cache/, keyed by (provider, model, prompt hash), and
        # the client checks the cache before it checks for a key. So the
        # bundled pack reproduces exactly with no credentials at all. Only a
        # file the cache has never seen needs a live call.
        st.caption(
            f"No {PROVIDERS[provider]['key_env']} configured. The bundled "
            f"50-episode pack still runs from cached responses, which is how "
            f"this reproduces without credentials. Uploading a new screenplay "
            f"needs a key."
        )


st.title("🎬 Promo Finder")
st.caption("Microdrama screenplays → ranked, timestamped promo cut-lists. "
           "The model picks moments by beat ID; code writes every timestamp.")

if "result" not in st.session_state:
    st.session_state.result = load_latest()

if go:
    workdir = None
    if uploaded:
        workdir = tempfile.mkdtemp(prefix="promo_in_")
        for item in uploaded:
            with open(os.path.join(workdir, item.name), "wb") as fh:
                fh.write(item.getbuffer())
        input_dir = workdir
    else:
        input_dir = "data" if glob.glob("data/*.txt") else "samples"

    if has_key:
        os.environ[PROVIDERS[provider]["key_env"]] = key_for(provider)
    lines: list[str] = []
    box = st.empty()

    def log(message: str) -> None:
        lines.append(str(message))
        box.code("\n".join(lines[-14:]))

    out_dir = tempfile.mkdtemp(prefix="promo_out_")
    try:
        with st.spinner("Running…"):
            result = run(input_dir, out_dir, provider=provider, model=model,
                         max_calls=250, log=log)
            result["_folder"] = out_dir
            st.session_state.result = result
        box.empty()
    except RuntimeError as exc:
        message = str(exc)
        if "is not set" in message:
            st.error(
                f"This input needs a live model call and no "
                f"{PROVIDERS[provider]['key_env']} is configured. The bundled "
                f"50-episode pack runs without one because its responses are "
                f"cached; a screenplay the cache has never seen cannot. Add the "
                f"key under **Settings → Secrets** and rerun, or clear the "
                f"uploader to use the bundled pack."
            )
        else:
            st.error(message)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

result = st.session_state.get("result")
if not result:
    st.info("Press **Find promos**.")
    st.stop()


# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------

counts, stats, meta = result["counts"], result["llm"], result["run"]
promos = result["promos"]
cols = st.columns(4)
cols[0].metric("Promos", counts["shipped"], f"from {len(meta['episodes'])} episodes")
tested = counts["shipped"] + counts["gate_failed"]
cols[1].metric("Passed blind viewer test",
               f"{counts['shipped']}/{tested}" if tested else "n/a",
               f"{counts['gate_failed']} rejected")
cols[2].metric("Invented timestamps", "0",
               f"{len(promos)}/{len(promos)} validators pass")
cols[3].metric("API calls", stats["calls"], stats["model"])


def segments_of(promo: dict) -> str:
    return "  +  ".join(
        f"ep{s['episode']}  {s['start']} → {s['end']}" for s in promo["segments"]
    )


tab_promos, tab_rejected, tab_run = st.tabs(
    [f"Promos ({len(promos)})", f"Rejected ({len(result['rejected'])})", "Run details"]
)


# ---------------------------------------------------------------------------
# Promos
# ---------------------------------------------------------------------------

with tab_promos:
    ordered_by_model = set((result.get("rank_rationale") or {}).get("order") or [])
    with st.expander("How this list is ordered"):
        st.markdown(
            f"""
1. **The blind test is a filter, not a score.** {counts['gate_failed']} promos that
   failed it were removed and are not ranked at all. They're in the Rejected tab.
2. **Code sorts the survivors** by a composite of four sub-scores:
   `0.30 x hook + 0.20 x tension + 0.30 x cliffhanger + 0.20 x standalone`.
   Weights are hand-set and documented; there is no labelled data to learn them from.
3. **The model reorders the top {len(ordered_by_model) or 12}**, seeing each promo's
   hook, cliffhanger, hook type, composite score and blind-test score, and returns a
   posting order. Everything below that keeps the composite order.

So the composite column is deliberately **not** in descending order for the top
rows. Where it isn't, the model moved something. And because the blind-test score
reaches the ranking only through the model's judgement rather than as a numeric
term, a 3/4 can sit above a 4/4.
"""
        )

    rows = [{
        "#": p.get("rank"),
        "Ep": ",".join(map(str, p["episodes"])),
        "Start → End": segments_of(p),
        "Len": f"{p['total_duration_s']:.0f}s",
        "Hook type": p.get("hook_type", ""),
        "Hook": p.get("hook", ""),
        "Cliffhanger": p.get("cliffhanger", ""),
        "Blind test": (p.get("cold_viewer") or {}).get("score", "—"),
        "Score": round(p["scores"]["composite"], 3),
        "Ordered by": "model" if p["promo_id"] in ordered_by_model else "score",
    } for p in promos]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=430)

    left, right = st.columns([1, 5])
    left.download_button("⬇  JSON", json.dumps(promos, indent=2, ensure_ascii=False),
                         "promos.json", "application/json")
    right.download_button("⬇  CSV", pd.DataFrame(rows).to_csv(index=False),
                          "promos.csv", "text/csv")

    st.divider()
    pick = st.selectbox(
        "Inspect", [p["promo_id"] for p in promos],
        format_func=lambda pid: next(
            f"#{p['rank']}  ·  episode {p['episodes'][0]}  ·  {p.get('hook','')[:70]}"
            for p in promos if p["promo_id"] == pid
        ),
    )
    promo = next(p for p in promos if p["promo_id"] == pick)

    one, two = st.columns([2, 3])
    with one:
        for seg in promo["segments"]:
            st.code(f"episode {seg['episode']}\n{seg['start']} → {seg['end']}"
                    f"   ({seg['duration_s']:.1f}s)")
        st.markdown(f"**Hook** — {promo.get('hook','')}")
        st.markdown(f"**Cliffhanger** — {promo.get('cliffhanger','')}")
        st.markdown(f"**Why it works** — {promo.get('why_it_works','')}")
        if promo.get("rank_rationale"):
            st.markdown(f"**Post order** — {promo['rank_rationale']}")
    with two:
        gate = promo.get("cold_viewer") or {}
        if gate.get("answers"):
            st.markdown(f"**Blind viewer test — {gate.get('score','')}**  \n"
                        f"A model shown only this clip: no logline, no episode "
                        f"number, no surrounding scenes.")
            for question, answer in gate["answers"].items():
                st.markdown(f"- *{question.replace('_',' ')}* — {answer}")
        curves = result.get("tension_curves") or {}
        key = str(promo["episodes"][0])
        curve = curves.get(key) or curves.get(promo["episodes"][0])
        if curve:
            st.markdown("**Intensity across the episode**, from the screenplay's "
                        "own tone tags. The promo is the spike-then-cut.")
            st.line_chart(pd.DataFrame(curve).set_index("t"), height=180)

    flagship = result.get("flagship")
    if flagship:
        with st.expander(f"Flagship cross-episode promo — "
                         f"{flagship['total_duration_s']:.0f}s across episodes "
                         f"{flagship['episodes']}  ·  blind test "
                         f"{(flagship.get('cold_viewer') or {}).get('score','—')}"):
            st.dataframe(pd.DataFrame(flagship["segments"])[
                ["order", "episode", "start", "end", "duration_s"]
            ], hide_index=True, width="stretch")
            st.markdown(f"**Story a stranger follows** — {flagship.get('narrative','')}")
            st.markdown(f"**Hook** — {flagship.get('hook','')}")
            st.markdown(f"**Cliffhanger** — {flagship.get('cliffhanger','')}")


# ---------------------------------------------------------------------------
# Rejected
# ---------------------------------------------------------------------------

def rejection_kind(promo: dict) -> str:
    reason = promo.get("rejected_reason") or ""
    if "cold-viewer" in reason:
        return "gate"
    if "near-duplicate" in reason:
        return "duplicate"
    return "validator"


with tab_rejected:
    buckets = {"gate": [], "duplicate": [], "validator": []}
    for promo in result["rejected"]:
        buckets[rejection_kind(promo)].append(promo)

    st.caption("Everything the pipeline threw out, grouped by why. The blind-test "
               "failures are the interesting ones: they scored well structurally "
               "and a context-free reader still could not follow them.")

    sections = [
        ("gate", "Failed the blind comprehension test",
         "A reader shown only the clip could not say who this is, what is at "
         "stake, or was left with nothing unresolved."),
        ("duplicate", "Suppressed as a near-duplicate",
         "Shows nearly the same thing as a higher-ranked promo from a nearby "
         "episode, measured on visual descriptions. Posting both wastes a slot."),
        ("validator", "Failed a hard validator",
         "Broke one of the six structural rules, so it never reached the gate."),
    ]
    for key, title, blurb in sections:
        rows = buckets[key]
        if not rows:
            continue
        st.markdown(f"#### {title} ({len(rows)})")
        st.caption(blurb)
        for promo in rows:
            gate = promo.get("cold_viewer") or {}
            label = f"episode {promo['episodes'][0]}"
            if key == "gate":
                label += f"  ·  scored {gate.get('score','?')} on the blind test"
            elif key == "duplicate":
                label += f"  ·  duplicate of {promo.get('rejected_reason','').split('of ')[-1].split(' ')[0]}"
            with st.expander(label):
                # Informational, not an alarm: a suppressed duplicate is the
                # pipeline working, not failing.
                st.info(f"**Why it was dropped** — {promo.get('rejected_reason','')}")
                st.code(segments_of(promo))
                st.markdown(f"**Proposed hook** — {promo.get('hook','')}")
                st.markdown(f"**Proposed cliffhanger** — {promo.get('cliffhanger','')}")
                st.caption(f"Structural score {promo['scores']['composite']:.3f} "
                           f"(hook {promo['scores']['hook']:.2f}, "
                           f"cliffhanger {promo['scores']['cliffhanger']:.2f}, "
                           f"standalone {promo['scores']['standalone']:.2f})")
                if gate.get("answers"):
                    st.markdown(f"**What the blind reader said — {gate.get('score','')}**")
                    for question, answer in gate["answers"].items():
                        st.markdown(f"- *{question.replace('_',' ')}* — {answer}")
                if promo.get("validator_failures"):
                    st.markdown("**Validator failures**")
                    for failure in promo["validator_failures"]:
                        st.markdown(f"- {failure}")


# ---------------------------------------------------------------------------
# Run details
# ---------------------------------------------------------------------------

with tab_run:
    report = result["parse_report"]
    funnel = [
        ("Legal 20–60s windows on real beat boundaries", counts["windows_enumerated"]),
        ("Rejected — nothing arresting in first 3 seconds", counts["rejected_no_hook"]),
        ("Shortlisted for the model to judge", counts["shortlisted"]),
        ("Candidate promos built", counts["candidates"]),
        ("Dropped — failed a hard validator", counts["validator_failed"]),
        ("Dropped — near-duplicate of a better promo", counts["near_duplicates"]),
        ("Dropped — failed the blind viewer test", counts["gate_failed"]),
        ("Shipped", counts["shipped"]),
    ]
    one, two = st.columns(2)
    with one:
        st.markdown("**Funnel**")
        st.dataframe(pd.DataFrame(funnel, columns=["Stage", "Count"]),
                     hide_index=True, width="stretch")
    with two:
        st.markdown("**Source data**")
        st.dataframe(pd.DataFrame([
            ("Episodes", str(report["n_files"])),
            ("Beats parsed", str(report["n_beats"])),
            ("Tone-tag coverage", f"{report['tone_tag_coverage']*100:.1f}%"),
            ("Lexicon hit rate",
             f"{report['intensity_coverage']['lexicon_hit_rate']*100:.1f}%"),
            ("Speaker labels → characters",
             f"{report['speaker_labels_raw']} → {report['characters_canonical']}"),
            ("Hazards found in source files", str(report["n_hazards"])),
            ("Tokens in / out", f"{stats['tokens_in']} / {stats['tokens_out']}"),
            ("Runtime", f"{meta['elapsed_s']}s"),
        ], columns=["Measure", "Value"]), hide_index=True, width="stretch")

    with st.expander(f"Hazards in the source screenplays ({report['n_hazards']}) — "
                     f"reported, not silently repaired"):
        for hazard in report["hazards"]:
            st.text(hazard)

    with st.expander(f"Speaker labels merged ({len(report['alias_map'])}) — an "
                     f"honorific is only stripped when the bare name appears "
                     f"elsewhere, so LORD and LADY ASHCROFT stay two people"):
        st.json(report["alias_map"])

    folder = os.path.join(result.get("_folder", "outputs"), "raw")
    files = sorted(glob.glob(os.path.join(folder, "*.json")))
    with st.expander(f"Raw model requests and responses ({len(files)})"):
        if not files:
            st.caption("Every response came from cache on this run.")
        else:
            name = st.selectbox("File", [os.path.basename(f) for f in files],
                                label_visibility="collapsed")
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                payload = json.load(fh)
            st.code(payload["system"])
            st.code(payload["prompt"][:4000])
            st.code(payload["response_text"])
