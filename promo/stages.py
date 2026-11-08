"""
The stages that use a model, and their prompts.

Design rule, enforced here: **the model never sees a timestamp and never
writes one.** It is shown beats as `[b07] JULIANA (desperate): "..."` and
answers with beat IDs. `pipeline.py` converts IDs to times by lookup. A
hallucinated timestamp is therefore not a thing this system can produce -
see docs/ai_mistakes_log.md #1 for the output that proved why this matters.

Three stages:
  select_promo      - pick the best window per episode, write the copy
  cold_viewer_gate  - blind comprehension test, the quality check
  flagship_promo    - one cross-episode launch promo for the whole show
"""
from __future__ import annotations

from .score import PROMPT_KINDS, beats_in_span, episode_beats

# The hook taxonomy is DramaBox's, from a published analysis of how
# short-drama openings work: fire an emotional trigger before giving context.
# Using their vocabulary gives an editor a diversity lever (don't post four
# "moral outrage" clips in a row) instead of an opaque score.
# https://www.dramaboxdb.com/content/critique/6163_dramabox-from-short-attention-to-strong-emotion
HOOK_TYPES = ("moral outrage", "romantic tension", "empathy shock", "power reversal")


# ---------------------------------------------------------------------------
# Rendering beats for a prompt (no timestamps, ever)
# ---------------------------------------------------------------------------

def render_beats(beats: list[dict], label_map: dict[str, str]) -> str:
    """
    One line per beat: `[b07] JULIANA (desperate, pleading): "Gerald... Look at me."`

    CAMERA beats are excluded (47% of all beats, pure framing) to stay inside
    the free-tier token ceiling. Short local labels b00..bNN keep the prompt
    compact and make the model's answer easy to validate.
    """
    lines = []
    for beat in beats:
        if beat["kind"] not in PROMPT_KINDS:
            continue
        tag = label_map[beat["id"]]
        if beat["kind"] == "DIALOGUE":
            tone = f" ({', '.join(beat['tone'])})" if beat["tone"] else ""
            lines.append(f'[{tag}] {beat["speaker"]}{tone}: "{beat["text"]}"')
        else:
            lines.append(f'[{tag}] {beat["kind"]}: {beat["text"]}')
    return "\n".join(lines)


def build_label_map(beats: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    """beat_id -> short label, and the reverse."""
    forward, back = {}, {}
    n = 0
    for beat in beats:
        if beat["kind"] not in PROMPT_KINDS:
            continue
        tag = f"b{n:02d}"
        forward[beat["id"]] = tag
        back[tag] = beat["id"]
        n += 1
    return forward, back


# ---------------------------------------------------------------------------
# Stage 1: selection
# ---------------------------------------------------------------------------

SELECT_SYSTEM = """You are a promo editor for vertical microdramas (ReelShort/DramaBox style).
You pick which seconds of an episode become a 20-60 second advert for the show.

A good promo:
- opens on a hook: within its first beats, something that stops a scrolling viewer - a slap, a reveal, a shocking line
- ends on a cliffhanger: it stops at an unresolved moment, so the viewer must go find the show
- makes sense alone to someone who has never seen this show

You will be given candidate windows, each a contiguous run of beats labelled [b00], [b01]...
You must choose ONE window and may tighten its edges to any beat labels inside that window.

Reply with JSON only:
{
  "chosen_window": <integer index of the window you picked>,
  "start_beat": "<beat label>",
  "end_beat": "<beat label>",
  "hook_beat": "<beat label, must be at or within 2 beats of start_beat>",
  "cliffhanger_beat": "<beat label, must be at or near end_beat>",
  "hook": "<what grabs the viewer in the first seconds, one sentence>",
  "cliffhanger": "<the unresolved moment it cuts on, one sentence>",
  "hook_type": "<one of: moral outrage, romantic tension, empathy shock, power reversal>",
  "why_it_works": "<one sentence, concrete, no marketing language>",
  "standalone_risk": "<what a new viewer would NOT understand, or 'none'>"
}

Never invent dialogue. Never output a time or a duration - only beat labels."""


def select_promo(llm, beats: list[dict], episode: int, shortlist: list[dict]) -> dict | None:
    """Ask the model to choose among pre-validated windows for one episode."""
    if not shortlist:
        return None
    ep_beats = episode_beats(beats, episode)
    blocks = []
    label_maps = []

    for i, window in enumerate(shortlist):
        span = [
            b for b in beats_in_span(ep_beats, window["start"], window["end"])
            if b["kind"] in PROMPT_KINDS
        ]
        forward, back = build_label_map(span)
        label_maps.append(back)
        blocks.append(
            f"--- WINDOW {i} ({window['duration_s']:.0f} seconds, "
            f"code score {window['scores']['composite']:.2f}) ---\n"
            + render_beats(span, forward)
        )

    prompt = (
        f"Episode {episode}. {len(shortlist)} candidate windows, already checked "
        f"for legal length and real beat boundaries.\n\n"
        + "\n\n".join(blocks)
        + "\n\nPick the single best promo."
    )
    result = llm.complete(SELECT_SYSTEM, prompt, tag=f"select_ep{episode:03d}", max_tokens=1200)
    if not result:
        return None

    try:
        idx = int(result.get("chosen_window", 0))
    except (TypeError, ValueError):
        idx = 0
    if not 0 <= idx < len(shortlist):
        idx = 0
    back = label_maps[idx]

    def resolve(key: str) -> str | None:
        label = (result.get(key) or "").strip().strip("[]")
        return back.get(label)

    return {
        "window": shortlist[idx],
        "start_beat_id": resolve("start_beat"),
        "end_beat_id": resolve("end_beat"),
        "hook_beat_id": resolve("hook_beat"),
        "cliffhanger_beat_id": resolve("cliffhanger_beat"),
        "hook": result.get("hook", ""),
        "cliffhanger": result.get("cliffhanger", ""),
        "hook_type": (result.get("hook_type") or "").lower().strip(),
        "why_it_works": result.get("why_it_works", ""),
        "standalone_risk": result.get("standalone_risk", ""),
        "raw": result,
    }


# ---------------------------------------------------------------------------
# Stage 2: the blind cold-viewer gate
# ---------------------------------------------------------------------------

GATE_SYSTEM = """You are a person scrolling social media. You have never heard of this show.
You just watched a short clip. Below is everything that happens in it - all the
dialogue and action, in order. You have no other information.

Answer strictly from the clip. If the clip does not tell you something, say so
plainly; do not guess from genre convention and do not be generous.

Reply with JSON only:
{
  "who_is_the_main_character": "<name them if the clip names them; otherwise describe and say the clip never names them>",
  "what_is_at_stake": "<what the conflict is, or 'unclear from the clip'>",
  "what_question_are_you_left_with": "<the unresolved question, or 'none - it felt finished'>",
  "would_you_keep_watching": "<yes | maybe | no>, then one short reason",
  "passes": {
    "character_identifiable": true/false,
    "stakes_clear": true/false,
    "ends_unresolved": true/false,
    "would_watch": true/false
  }
}

Be strict. "character_identifiable" is false if the clip never says who they are.
"stakes_clear" is false if you had to assume the situation. "ends_unresolved" is
false if the clip resolved its own conflict."""


def cold_viewer_gate(llm, promo: dict, beats_by_id: dict) -> dict | None:
    """
    Hand the model ONLY the promo's own content and ask if it lands.

    Everything contextual is withheld: no logline, no continuity note, no
    episode number, no surrounding beats. This is the test the brief's third
    requirement implies, and it is the one check in the pipeline that can
    overrule both the code score and the selector.
    """
    lines = []
    for bid in promo["source_beat_ids"]:
        beat = beats_by_id.get(bid)
        if not beat or beat["kind"] not in PROMPT_KINDS:
            continue
        if beat["kind"] == "DIALOGUE":
            lines.append(f'{beat["speaker"]}: "{beat["text"]}"')
        else:
            lines.append(f'[{beat["kind"].lower()}] {beat["text"]}')
    if not lines:
        return None

    prompt = "THE CLIP:\n" + "\n".join(lines)
    result = llm.complete(
        GATE_SYSTEM, prompt, tag=f"gate_{promo['promo_id']}", max_tokens=900
    )
    if not result:
        return None

    passes = result.get("passes") or {}
    score = sum(1 for v in passes.values() if v is True)
    return {
        "verdict": "pass" if score >= 3 else "fail",
        "score": f"{score}/4",
        "score_n": score,
        "answers": {
            k: result.get(k)
            for k in (
                "who_is_the_main_character",
                "what_is_at_stake",
                "what_question_are_you_left_with",
                "would_you_keep_watching",
            )
        },
        "passes": passes,
    }


# ---------------------------------------------------------------------------
# Stage 3: the cross-episode flagship promo
# ---------------------------------------------------------------------------

FLAGSHIP_SYSTEM = """You are building ONE launch advert for a whole microdrama series,
assembled from moments across different episodes.

You will see the strongest moment from each of several episodes, as beats labelled
[e01_b04] style. Choose 3 to 6 of them that together tell a stranger why to watch:
a shocking hook, one or two escalations, and a final unresolved image.

Rules:
- the hook may come from any episode and goes first
- after the hook, keep the remaining segments in episode order
- do not pick two moments that say the same thing
- a stranger must understand who the main character is from the clips alone

Reply with JSON only:
{
  "segments": ["<beat label>", "<beat label>", ...],
  "hook": "<one sentence>",
  "cliffhanger": "<one sentence>",
  "hook_type": "<moral outrage | romantic tension | empathy shock | power reversal>",
  "why_it_works": "<one sentence>",
  "narrative": "<the story a stranger would follow, one sentence>"
}

Never invent dialogue. Never output a time or a duration - only beat labels."""


def flagship_promo(llm, beats: list[dict], best_per_episode: list[dict]) -> dict | None:
    """One cross-episode promo for the whole show."""
    beats_by_id = {b["id"]: b for b in beats}
    lines, allowed = [], set()
    for entry in best_per_episode:
        ep = entry["episode"]
        chunk = []
        for bid in entry["source_beat_ids"]:
            beat = beats_by_id.get(bid)
            if not beat or beat["kind"] not in PROMPT_KINDS:
                continue
            allowed.add(bid)
            if beat["kind"] == "DIALOGUE":
                tone = f" ({', '.join(beat['tone'])})" if beat["tone"] else ""
                chunk.append(f'[{bid}] {beat["speaker"]}{tone}: "{beat["text"]}"')
            else:
                chunk.append(f'[{bid}] {beat["kind"]}: {beat["text"]}')
        if chunk:
            lines.append(f"--- EPISODE {ep} ---\n" + "\n".join(chunk[:12]))

    if not lines:
        return None
    result = llm.complete(
        FLAGSHIP_SYSTEM, "\n\n".join(lines), tag="flagship", max_tokens=1200
    )
    if not result:
        return None
    chosen = [
        bid.strip().strip("[]") for bid in (result.get("segments") or [])
        if bid.strip().strip("[]") in allowed
    ]
    if len(chosen) < 2:
        return None
    result["resolved_beat_ids"] = chosen
    return result


# ---------------------------------------------------------------------------
# Stage 4: ranking rationale
# ---------------------------------------------------------------------------

RANK_SYSTEM = """You are the editor deciding posting order for promo clips from one show.
You will see each promo's hook, cliffhanger and a blind viewer's comprehension result.

Reply with JSON only, and keep it short:
{
  "order": ["<promo_id>", "<promo_id>", ...],
  "post_first": "<promo_id>",
  "post_first_reason": "<two sentences maximum>",
  "rationale": {"<promo_id>": "<one short clause>"}
}

Include every promo_id you were given in "order". Put a rationale for the top 5
only. Favour promos a stranger understood, that open on something physical or
shocking, and that leave a question. Spread hook types rather than posting four
of a kind."""


def rank_rationale(llm, promos: list[dict]) -> dict | None:
    """Ask for a posting order. Code still owns the score; this adds the why."""
    if not promos:
        return None
    lines = []
    for promo in promos:
        gate = promo.get("cold_viewer") or {}
        lines.append(
            f"{promo['promo_id']} | episodes {promo['episodes']} | "
            f"{promo['total_duration_s']:.0f}s | hook_type {promo.get('hook_type','?')} | "
            f"code score {promo['scores']['composite']:.2f} | "
            f"blind viewer {gate.get('score','n/a')}\n"
            f"  hook: {promo.get('hook','')}\n"
            f"  cliffhanger: {promo.get('cliffhanger','')}"
        )
    return llm.complete(
        RANK_SYSTEM, "\n\n".join(lines), tag="rank", max_tokens=3000
    )
