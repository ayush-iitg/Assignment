"""
Promo Finder - web interface.

A view over promo.pipeline.run(), the same function run.py calls. No pipeline
logic lives here; presentation lives in promo/ui_style.py.

    streamlit run app.py
"""
import os
import json
import glob
import shutil
import tempfile

import altair as alt
import pandas as pd
import streamlit as st

from promo.pipeline import run
from promo.llm import PROVIDERS, load_dotenv
from promo import ui_style as ui

st.set_page_config(page_title="Promo Finder", page_icon="◆", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)
load_dotenv()

MODELS = [
    ("groq", "openai/gpt-oss-120b"),
    ("groq", "qwen/qwen3.8-27b"),
    ("gemini", "gemini-3.5-flash-lite"),
    ("gemini", "gemini-3.5-flash"),
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


def segments_text(promo: dict) -> str:
    return "   +   ".join(
        (f'ep{s["episode"]}  ' if len(promo["episodes"]) > 1 else "")
        + f'{s["start"]} → {s["end"]}'
        for s in promo["segments"]
    )


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<div class="sec" style="margin-top:0">Run</div>',
                unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Screenplay files", type=["txt"], accept_multiple_files=True,
        label_visibility="collapsed",
        help="Leave empty to use the bundled 50-episode pack.",
    )
    st.caption("Drop .txt screenplays, or leave empty for the bundled pack.")

    choice = st.selectbox(
        "Model", range(len(MODELS)),
        format_func=lambda i: f"{MODELS[i][1]}",
    )
    provider, model = MODELS[choice]
    st.caption(f"via {provider}")
    has_key = bool(key_for(provider))

    go = st.button("Find promos", type="primary", width="stretch")

    if has_key:
        st.caption("Responses are cached, so a repeat run is instant.")
    else:
        st.caption(
            f"No {PROVIDERS[provider]['key_env']} set. The bundled pack still "
            f"runs from cached responses, which is how this reproduces without "
            f"credentials. A new screenplay would need a key."
        )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(ui.masthead(
    "Promo Finder",
    "Reads microdrama screenplays and returns ranked, timestamped promo "
    "cut&nbsp;lists. <b>Code owns time, the model owns judgment</b>: the model "
    "picks moments by beat ID and never sees or writes a timestamp, so every "
    "time below is looked up from the parsed screenplay.",
), unsafe_allow_html=True)

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
        with st.spinner("Parsing, scoring, then asking the model to choose…"):
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
                f"{PROVIDERS[provider]['key_env']} is set. The bundled pack "
                f"runs without one because its responses are cached; a "
                f"screenplay the cache has never seen cannot."
            )
        else:
            st.error(message)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

result = st.session_state.get("result")
if not result:
    st.info("Press **Find promos** to run on the bundled pack.")
    st.stop()


# ---------------------------------------------------------------------------
# Stat strip
# ---------------------------------------------------------------------------

counts, stats, meta = result["counts"], result["llm"], result["run"]
promos = result["promos"]
report = result["parse_report"]
tested = counts["shipped"] + counts["gate_failed"]

st.markdown(ui.stat_row([
    ui.stat("Promos", counts["shipped"],
            f'from {len(meta["episodes"])} episodes, {report["n_beats"]} beats'),
    ui.stat("Passed blind test",
            f'{counts["shipped"]}/{tested}' if tested else "—",
            f'{counts["gate_failed"]} rejected with transcripts'),
    ui.stat("Invented timestamps", "0",
            f'{len(promos)}/{len(promos)} validators pass', good=True),
    ui.stat("Cost", f'{stats["calls"]} calls',
            f'{stats["cache_hits"]} cached · {meta["elapsed_s"]}s · '
            f'{stats["model"].split("/")[-1]}'),
]), unsafe_allow_html=True)


tab_promos, tab_rejected, tab_run = st.tabs([
    f"Ranked  ·  {len(promos)}",
    f"Rejected  ·  {len(result['rejected'])}",
    "How it ran",
])


# ---------------------------------------------------------------------------
# Ranked
# ---------------------------------------------------------------------------

with tab_promos:
    rationale = result.get("rank_rationale") or {}
    ordered_by_model = set(rationale.get("order") or [])

    if rationale.get("post_first_reason"):
        st.markdown(ui.section(
            "Post this first",
            f'<b>{rationale.get("post_first","")}</b> &nbsp;·&nbsp; '
            f'{ui.esc(rationale["post_first_reason"])}',
        ), unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # The whole list, and the two files an editor would take away.
    # -----------------------------------------------------------------------
    rows = [{
        "#": p.get("rank"),
        "Episodes": ",".join(map(str, p["episodes"])),
        "Start → End": segments_text(p),
        "Len": round(p["total_duration_s"], 1),
        "Hook type": p.get("hook_type", ""),
        "Hook": p.get("hook", ""),
        "Cliffhanger": p.get("cliffhanger", ""),
        "Blind test": (p.get("cold_viewer") or {}).get("score") or "—",
        "Score": round(p["scores"]["composite"], 3),
        "Ordered by": "model" if p["promo_id"] in ordered_by_model else "score",
    } for p in promos]
    frame = pd.DataFrame(rows)

    st.markdown(ui.section(
        f"Every promo · {len(promos)}",
        "The cut list as an editor would receive it, in rank order. "
        "<b>Ordered by</b> says whether a position came from the composite "
        "score or from the model reordering the top of the list.",
    ), unsafe_allow_html=True)

    st.dataframe(
        frame, hide_index=True, width="stretch", height=340,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Len": st.column_config.NumberColumn(format="%.1f s", width="small"),
            "Score": st.column_config.ProgressColumn(
                min_value=0.0, max_value=1.0, format="%.3f"),
            "Hook": st.column_config.TextColumn(width="large"),
            "Cliffhanger": st.column_config.TextColumn(width="large"),
        },
    )

    get_json, get_csv, _ = st.columns([1, 1, 4])
    get_json.download_button(
        "Download JSON", json.dumps(promos, indent=2, ensure_ascii=False),
        "promos.json", "application/json", width="stretch")
    get_csv.download_button(
        "Download CSV", frame.to_csv(index=False),
        "promos.csv", "text/csv", width="stretch")

    with st.expander("How this list is ordered"):
        st.markdown(f"""
The blind comprehension test is a **filter, not a score**. The
{counts['gate_failed']} promos that failed it were removed and are not ranked
at all; they're in the Rejected tab with their transcripts.

Code then sorts the survivors on a weighted composite:
`0.30 × hook + 0.20 × tension + 0.30 × cliffhanger + 0.20 × standalone`.
Weights are hand-set and documented. There's no labelled data to learn them from.

The model reorders the top {len(ordered_by_model) or 12}, seeing each promo's
hook, cliffhanger, hook type, composite score and blind-test result. Everything
below that keeps the composite order. So the score column deliberately isn't
descending at the top: where it isn't, the model moved something.

One consequence worth knowing: a 3/4 can sit above a 4/4, because the
blind-test score reaches the ranking through the model's judgment rather than
as a term in the formula.
        """)

    # -----------------------------------------------------------------------
    # One promo, in full. Defaults to rank 1 so the page shows a worked
    # example without anyone having to click first.
    # -----------------------------------------------------------------------
    st.markdown(ui.section(
        "One promo in detail",
        "Exact segments, the four sub-scores behind its composite, what a "
        "blind reader made of it, and where it sits on the episode's "
        "intensity curve.",
    ), unsafe_allow_html=True)

    pick = st.selectbox(
        "Inspect", [p["promo_id"] for p in promos],
        format_func=lambda pid: next(
            f'#{p["rank"]}  ·  episode {p["episodes"][0]}  ·  {p.get("hook","")[:64]}'
            for p in promos if p["promo_id"] == pid
        ),
        label_visibility="collapsed",
    )
    chosen = next(p for p in promos if p["promo_id"] == pick)

    one, two = st.columns([2, 3])
    with one:
        for seg in chosen["segments"]:
            st.code(f'episode {seg["episode"]}\n{seg["start"]} → {seg["end"]}'
                    f'   ({seg["duration_s"]:.1f}s)')
        st.caption("Sub-scores")
        st.json(chosen["scores"], expanded=True)
    with two:
        gate = chosen.get("cold_viewer") or {}
        if gate.get("answers"):
            st.caption(f'Blind viewer test — {gate.get("score","")}. A model '
                       f'shown only this clip: no logline, no episode number, '
                       f'nothing either side of it.')
            for question, answer in gate["answers"].items():
                st.markdown(f'**{question.replace("_"," ")}** — {answer}')
        else:
            st.caption("This promo did not go through the blind viewer test.")

    curves = result.get("tension_curves") or {}
    curve = curves.get(str(chosen["episodes"][0])) or curves.get(chosen["episodes"][0])
    if curve:
        lead_ep = chosen["episodes"][0]
        here = [s for s in chosen["segments"] if s["episode"] == lead_ep]
        band = pd.DataFrame([{"start": s["start_s"], "end": s["end_s"]} for s in here])
        chart = (
            alt.layer(
                alt.Chart(band).mark_rect(
                    color=ui.ACCENT, opacity=0.15
                ).encode(x="start:Q", x2="end:Q"),
                alt.Chart(pd.DataFrame(curve)).mark_area(
                    line={"color": ui.ACCENT, "strokeWidth": 1.4},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[alt.GradientStop(color=ui.WASH, offset=0),
                               alt.GradientStop(color=ui.ACCENT, offset=1)],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                ).encode(
                    x=alt.X("t:Q", title="seconds into the episode",
                            axis=alt.Axis(grid=False, tickCount=8)),
                    y=alt.Y("intensity:Q", title=None,
                            scale=alt.Scale(domain=[0, 1]),
                            axis=alt.Axis(grid=True, tickCount=3)),
                ),
            )
            .properties(height=210)
            .configure_view(stroke=None)
            .configure_axis(labelColor=ui.FAINT, titleColor=ui.FAINT,
                            gridColor="#1E2430", domainColor="#1E2430",
                            labelFontSize=10, titleFontSize=10)
        )
        st.caption(f"Intensity across episode {lead_ep}, computed from the "
                   f"screenplay's own tone tags. The shaded band is this promo.")
        st.altair_chart(chart, width="stretch")

    # -----------------------------------------------------------------------
    # The same ranking as cards, for reading rather than scanning.
    # -----------------------------------------------------------------------
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(ui.section(
        "All of them, card by card",
        "The same ranking, read rather than scanned: what each promo opens "
        "on, what it cuts away on, and why it holds up alone.",
    ), unsafe_allow_html=True)

    for item in promos:
        st.markdown(
            ui.promo_card(item, segments_text(item), lead=item.get("rank") == 1),
            unsafe_allow_html=True,
        )


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

    sections = [
        ("gate", "Failed the blind comprehension test",
         "A reader shown only the clip couldn't say who this is or what's at "
         "stake, or found nothing left unresolved. Several of these scored well "
         "structurally, which is the point of testing comprehension separately."),
        ("duplicate", "Suppressed as a near-duplicate",
         "Shows nearly the same thing as a higher-ranked promo from a nearby "
         "episode, measured on visual descriptions rather than dialogue. Posting "
         "both would waste a slot."),
        ("validator", "Failed a hard validator",
         "Broke one of the six structural rules, so it never reached the gate."),
    ]
    for key, title, blurb in sections:
        rows = buckets[key]
        if not rows:
            continue
        st.markdown(ui.section(f"{title} · {len(rows)}", blurb), unsafe_allow_html=True)
        for promo in rows:
            gate = promo.get("cold_viewer") or {}
            label = f'episode {promo["episodes"][0]}'
            if key == "gate":
                label += f'  ·  blind test {gate.get("score","?")}'
            elif key == "duplicate":
                dup = (promo.get("rejected_reason") or "").split("of ")[-1].split(" ")[0]
                label += f'  ·  duplicate of {dup}'
            with st.expander(label):
                st.markdown(
                    f'<p class="note" style="margin-bottom:.6rem">'
                    f'<b>Dropped because</b> — {ui.esc(promo.get("rejected_reason",""))}'
                    f'</p>', unsafe_allow_html=True)
                st.markdown(f'<span class="ts">{ui.esc(segments_text(promo))}</span>',
                            unsafe_allow_html=True)
                st.markdown(f'\n**Proposed hook** — {promo.get("hook","")}')
                st.markdown(f'**Proposed cliffhanger** — {promo.get("cliffhanger","")}')
                s = promo["scores"]
                st.caption(f'Structural score {s["composite"]:.3f} '
                           f'(hook {s["hook"]:.2f}, cliffhanger {s["cliffhanger"]:.2f}, '
                           f'standalone {s["standalone"]:.2f})')
                if gate.get("answers"):
                    st.markdown("**What the blind reader said**")
                    for question, answer in gate["answers"].items():
                        st.markdown(f'- *{question.replace("_"," ")}* — {answer}')
                if promo.get("validator_failures"):
                    for failure in promo["validator_failures"]:
                        st.markdown(f"- {failure}")


# ---------------------------------------------------------------------------
# How it ran
# ---------------------------------------------------------------------------

with tab_run:
    funnel = [
        ("Legal 20–60s windows on real beat boundaries", counts["windows_enumerated"]),
        ("Rejected — nothing arresting in the first 3 seconds", counts["rejected_no_hook"]),
        ("Shortlisted for the model to judge", counts["shortlisted"]),
        ("Candidate promos built", counts["candidates"]),
        ("Dropped — failed a hard validator", counts["validator_failed"]),
        ("Dropped — near-duplicate of a better promo", counts["near_duplicates"]),
        ("Dropped — failed the blind test", counts["gate_failed"]),
        ("Shipped", counts["shipped"]),
    ]
    source = [
        ("Episodes", str(report["n_files"])),
        ("Beats parsed", str(report["n_beats"])),
        ("Tone-tag coverage", f'{report["tone_tag_coverage"]*100:.1f}%'),
        ("Lexicon hit rate",
         f'{report["intensity_coverage"]["lexicon_hit_rate"]*100:.1f}%'),
        ("Speaker labels → characters",
         f'{report["speaker_labels_raw"]} → {report["characters_canonical"]}'),
        ("Defects found in source files", str(report["n_hazards"])),
        ("Tokens in / out", f'{stats["tokens_in"]} / {stats["tokens_out"]}'),
        ("Runtime", f'{meta["elapsed_s"]}s'),
    ]
    one, two = st.columns(2)
    with one:
        st.markdown(ui.section("Funnel"), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(funnel, columns=["Stage", "Count"]),
                     hide_index=True, width="stretch", height=322)
    with two:
        st.markdown(ui.section("Source data"), unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(source, columns=["Measure", "Value"]),
                     hide_index=True, width="stretch", height=322)

    with st.expander(f'Defects found in the screenplays · {report["n_hazards"]}'):
        st.caption("Reported, never silently repaired.")
        for hazard in report["hazards"]:
            st.text(hazard)

    with st.expander(f'Speaker labels merged · {len(report["alias_map"])}'):
        st.caption("An honorific is only stripped when the bare name appears "
                   "elsewhere in the corpus, so a title shared by two different "
                   "characters doesn't collapse them into one.")
        st.json(report["alias_map"])

    flagship = result.get("flagship")
    if flagship:
        gate = flagship.get("cold_viewer") or {}
        with st.expander(
            f'Cross-episode flagship promo · {flagship["total_duration_s"]:.0f}s '
            f'across episodes {flagship["episodes"]} · blind test '
            f'{gate.get("score","—")}'
        ):
            st.caption("The only promo that crosses episodes. Stitching freely "
                       "across 50 needs reliable character identity, and this "
                       "corpus has 64 speaker labels for 58 characters, so this "
                       "is deliberately one output held to the same checks as "
                       "everything else.")
            st.dataframe(pd.DataFrame(flagship["segments"])[
                ["order", "episode", "start", "end", "duration_s"]
            ], hide_index=True, width="stretch")
            st.markdown(f'**Story a stranger would follow** — {flagship.get("narrative","")}')
            if gate.get("answers"):
                for question, answer in gate["answers"].items():
                    st.markdown(f'- *{question.replace("_"," ")}* — {answer}')

    folder = os.path.join(result.get("_folder", "outputs"), "raw")
    files = sorted(glob.glob(os.path.join(folder, "*.json")))
    with st.expander(f"Raw model requests and responses · {len(files)}"):
        if not files:
            st.caption("Every response came from cache on this run.")
        else:
            name = st.selectbox("File", [os.path.basename(f) for f in files],
                                label_visibility="collapsed")
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                payload = json.load(fh)
            st.caption("System prompt")
            st.code(payload["system"])
            st.caption("User prompt")
            st.code(payload["prompt"][:4000])
            st.caption("Response")
            st.code(payload["response_text"])
