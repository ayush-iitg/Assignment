"""
Deterministic promo scoring.

Takes parsed beats and produces candidate promo windows with four sub-scores.
No LLM is involved here at all, which means:

  * it runs offline, instantly, for free, and gives the same answer every time
  * the shortlist handed to the model is already length-legal and
    boundary-legal, so the model only has to make a judgment call
  * every number can be explained in one sentence

Weights are hand-set (see docs/assumptions.md A16). There is no labelled
training data for "good promo", so anything learned would be invented.
"""
from __future__ import annotations

import re
from .lexicon import (
    tone_intensity, action_intensity, UNRESOLVED_MARKERS, THREAT_WORDS,
)

# Promo rules from the brief (p.2).
MIN_LEN = 20.0
MAX_LEN = 60.0
HOOK_WINDOW = 3.0          # "something in the first 3 seconds"

# A window whose first 3 seconds contain nothing arresting is not a promo,
# whatever else it scores. The brief makes the hook a requirement, not a
# preference, so this is a filter rather than a weight. Rejections are
# counted and reported.
MIN_HOOK = 0.45

# Beats that the LLM never sees. CAMERA is 47% of all beats and describes
# framing, which an editor can see for themselves; ACTION already carries the
# physical events. Excluding it keeps prompts inside the 8,000 tokens/minute
# free-tier ceiling (docs/assumptions.md A13, A20).
PROMPT_KINDS = ("DIALOGUE", "ACTION", "SFX")

COMPOSITE_WEIGHTS = {
    "hook": 0.30,
    "tension": 0.20,
    "cliffhanger": 0.30,
    "standalone": 0.20,
}

RE_THIRD_PERSON = re.compile(r"\b(he|she|him|her|his|hers|they|them|their|it)\b", re.I)


# ---------------------------------------------------------------------------
# Per-beat intensity
# ---------------------------------------------------------------------------

def annotate_intensity(beats: list[dict]) -> dict:
    """Attach `intensity` to every beat. Returns coverage stats."""
    unknown_tags: dict[str, int] = {}
    n_dialogue = n_scored = 0

    for beat in beats:
        if beat["kind"] == "DIALOGUE":
            n_dialogue += 1
            score, unknown = tone_intensity(beat.get("tone", []))
            for tag in unknown:
                unknown_tags[tag] = unknown_tags.get(tag, 0) + 1
            if score == 0.0:
                # No usable tone tag: fall back to the words themselves, so a
                # shout written as plain text still registers.
                score = max(action_intensity(beat["text"]), 0.25)
            else:
                n_scored += 1
            # An exclamation or a question is delivery information too.
            if beat["text"].endswith("!"):
                score = min(1.0, score + 0.06)
            beat["intensity"] = round(score, 4)
        elif beat["kind"] in ("ACTION", "SFX"):
            beat["intensity"] = round(action_intensity(beat["text"]), 4)
        else:
            beat["intensity"] = 0.0

    return {
        "dialogue_beats": n_dialogue,
        "scored_from_tone_lexicon": n_scored,
        "lexicon_hit_rate": round(n_scored / n_dialogue, 4) if n_dialogue else 0.0,
        "n_unknown_tags": len(unknown_tags),
        "top_unknown_tags": sorted(unknown_tags.items(), key=lambda kv: -kv[1])[:40],
    }


# ---------------------------------------------------------------------------
# Window enumeration
# ---------------------------------------------------------------------------

def episode_beats(beats: list[dict], episode: int) -> list[dict]:
    return [b for b in beats if b["episode"] == episode]


def anchor_beats(ep_beats: list[dict]) -> list[dict]:
    """
    Beats a promo is allowed to start or end on.

    A promo must not begin or end on a camera direction: starting there would
    mean opening on an empty frame description, and the editor needs a real
    event at both edges.
    """
    return [b for b in ep_beats if b["kind"] in PROMPT_KINDS]


def enumerate_windows(ep_beats: list[dict]) -> list[dict]:
    """
    Every (start_beat, end_beat) pair whose span is a legal promo length.

    Boundaries are real beat edges, so a window can never point at a
    timestamp that doesn't exist in the screenplay.
    """
    anchors = anchor_beats(ep_beats)
    windows = []
    for i, start in enumerate(anchors):
        for end in anchors[i:]:
            length = end["end"] - start["start"]
            if length < MIN_LEN:
                continue
            if length > MAX_LEN:
                break          # anchors are sorted, so every later end is longer
            windows.append({
                "episode": start["episode"],
                "start_beat_id": start["id"],
                "end_beat_id": end["id"],
                "start": round(start["start"], 2),
                "end": round(end["end"], 2),
                "duration_s": round(length, 2),
            })
    return windows


def beats_in_span(ep_beats: list[dict], start: float, end: float) -> list[dict]:
    """Beats that overlap the span at all (beats are layered, not sequential)."""
    return [b for b in ep_beats if b["end"] > start + 1e-9 and b["start"] < end - 1e-9]


# ---------------------------------------------------------------------------
# The four sub-scores
# ---------------------------------------------------------------------------

def score_hook(span_beats: list[dict], start: float) -> tuple[float, dict | None]:
    """
    "Opens on a hook": something in the first 3 seconds that stops a scroll.

    Score = strongest beat starting inside the window, plus bonuses for a
    physical event or a raised voice landing there.
    """
    # Must begin at or after the promo starts: `beats_in_span` returns beats
    # that merely overlap the span, so without the lower bound a beat that
    # began before the promo can be named as its hook - a hook the viewer
    # never sees. This is the same mistake the templated-copy path made.
    opening = [
        b for b in span_beats
        if start - 1e-9 <= b["start"] < start + HOOK_WINDOW + 1e-9
    ]
    if not opening:
        return 0.0, None
    best = max(opening, key=lambda b: b["intensity"])
    score = best["intensity"]
    if any(b["kind"] in ("ACTION", "SFX") and b["intensity"] >= 0.6 for b in opening):
        score += 0.15                      # a slap or a crack, not just talk
    first_line = next((b for b in opening if b["kind"] == "DIALOGUE"), None)
    if first_line and (first_line["text"].endswith("?") or first_line["text"].endswith("!")):
        score += 0.10                      # opens mid-confrontation
    return round(min(score, 1.0), 4), best


def score_tension(span_beats: list[dict]) -> float:
    """
    Mean intensity, plus credit for rising rather than flat.

    Slope is a least-squares fit over (beat start, intensity); a promo that
    escalates beats one that stays loud throughout.
    """
    live = [b for b in span_beats if b["intensity"] > 0]
    if len(live) < 2:
        return 0.0
    mean = sum(b["intensity"] for b in live) / len(live)
    xs = [b["start"] for b in live]
    ys = [b["intensity"] for b in live]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom if denom else 0.0
    return round(min(1.0, max(0.0, mean + 8.0 * slope)), 4)


def score_cliffhanger(span_beats: list[dict], ep_duration: float, end: float) -> tuple[float, dict | None]:
    """
    "Ends on a cliffhanger": cuts at an unresolved moment.

    Takes the strongest beat in the final 5 seconds (not strictly the last
    beat, which is often a camera-adjacent action), then rewards markers of
    non-resolution: a question, a trailing off, a threat, an episode-end cut.
    """
    tail = [b for b in span_beats if b["end"] > end - 5.0]
    if not tail:
        return 0.0, None
    last = max(tail, key=lambda b: b["intensity"])
    score = last["intensity"]
    text = last["text"]
    if any(m in text[-3:] or text.endswith(m) for m in UNRESOLVED_MARKERS):
        score += 0.12
    if any(w in text.lower() for w in THREAT_WORDS):
        score += 0.08
    if end >= ep_duration - 10.0:
        score += 0.10        # episodes are themselves engineered to cliffhang
    return round(min(score, 1.0), 4), last


def score_standalone(span_beats: list[dict], start: float, end: float) -> tuple[float, dict]:
    """
    "Makes sense on its own": a deterministic proxy, not the real test.

    The real test is the blind cold-viewer gate in stages.py. This score only
    filters out the obviously incomprehensible before spending a model call:
    too little speech, too many characters, or an opening that refers to
    someone by pronoun with no name anywhere in the clip.
    """
    length = max(end - start, 1e-6)
    dialogue = [b for b in span_beats if b["kind"] == "DIALOGUE"]
    spoken = sum(min(b["end"], end) - max(b["start"], start) for b in dialogue)
    coverage = min(1.0, spoken / length)

    speakers = {b["speaker"] for b in dialogue if b["speaker"]}
    score = coverage
    if len(speakers) > 3:
        score -= 0.08 * (len(speakers) - 3)

    named = " ".join(b["text"] for b in dialogue).upper()
    names_spoken = {s for s in speakers if s.split()[0] in named}
    opening_text = " ".join(
        b["text"] for b in span_beats if b["start"] < start + 10.0
    )
    dangling = bool(RE_THIRD_PERSON.search(opening_text)) and not names_spoken
    if dangling:
        score -= 0.15

    return round(min(1.0, max(0.0, score)), 4), {
        "dialogue_coverage": round(coverage, 4),
        "n_speakers": len(speakers),
        "speakers": sorted(speakers),
        "names_spoken_aloud": sorted(names_spoken),
        "dangling_pronoun_opening": dangling,
    }


def score_window(window: dict, ep_beats: list[dict], ep_duration: float) -> dict:
    """Attach all four sub-scores plus the composite to one window."""
    span = beats_in_span(ep_beats, window["start"], window["end"])
    hook, hook_beat = score_hook(span, window["start"])
    tension = score_tension(span)
    cliff, cliff_beat = score_cliffhanger(span, ep_duration, window["end"])
    standalone, standalone_detail = score_standalone(span, window["start"], window["end"])

    composite = (
        COMPOSITE_WEIGHTS["hook"] * hook
        + COMPOSITE_WEIGHTS["tension"] * tension
        + COMPOSITE_WEIGHTS["cliffhanger"] * cliff
        + COMPOSITE_WEIGHTS["standalone"] * standalone
    )
    window = dict(window)
    window["scores"] = {
        "hook": hook,
        "tension": tension,
        "cliffhanger": cliff,
        "standalone": standalone,
        "composite": round(composite, 4),
    }
    window["hook_beat_id"] = hook_beat["id"] if hook_beat else None
    window["cliffhanger_beat_id"] = cliff_beat["id"] if cliff_beat else None
    window["n_beats"] = len(span)
    window["standalone_detail"] = standalone_detail
    return window


# ---------------------------------------------------------------------------
# Shortlisting
# ---------------------------------------------------------------------------

def suppress_overlapping(windows: list[dict], max_overlap: float = 0.4) -> list[dict]:
    """
    Greedy non-maximum suppression over time.

    Without this, the top 8 windows for an episode are 8 nearly identical
    spans around the same spike.
    """
    kept: list[dict] = []
    for cand in sorted(windows, key=lambda w: -w["scores"]["composite"]):
        clash = False
        for k in kept:
            overlap = min(cand["end"], k["end"]) - max(cand["start"], k["start"])
            if overlap > 0:
                shorter = min(cand["duration_s"], k["duration_s"])
                if overlap / shorter > max_overlap:
                    clash = True
                    break
        if not clash:
            kept.append(cand)
    return kept


_STOP = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "is", "are", "was", "be", "you", "your", "i", "me", "my",
    "he", "she", "it", "they", "them", "this", "that", "not", "no", "do",
    "will", "have", "has", "what", "who", "why", "how", "so", "all", "can",
}


def _content_words(beats: list[dict]) -> set[str]:
    text = " ".join(b["text"] for b in beats if b["kind"] == "DIALOGUE").lower()
    return {w for w in re.findall(r"[a-z']+", text) if len(w) > 2 and w not in _STOP}


def _redundant(piece_one: list[dict], piece_two: list[dict], threshold: float = 0.30) -> bool:
    """True when the two halves of a spliced promo repeat each other."""
    one, two = _content_words(piece_one), _content_words(piece_two)
    if not one or not two:
        return False
    return len(one & two) / len(one | two) >= threshold


def _no_arc(hook_beat: dict, cliff_beat: dict) -> bool:
    """
    True when a spliced promo ends where it began.

    A two-piece promo has to earn the cut. If the same character is at both
    ends and the temperature has not risen, the viewer has watched one
    emotional beat twice and is owed nothing at the end. Caught a real case:
    hook "You still think you are better?!" closing on "You think you can
    lecture me?!" - same speaker, same fury, no question raised. Whole-piece
    word overlap was only 0.25 there, below any threshold I would defend,
    because the redundancy is in the first and last lines rather than spread
    across the clip.

    Either the speaker changes, or the intensity rises. One or the other.
    """
    same_speaker = (
        hook_beat.get("speaker")
        and hook_beat.get("speaker") == cliff_beat.get("speaker")
    )
    escalates = cliff_beat.get("intensity", 0.0) > hook_beat.get("intensity", 0.0) + 0.02
    return bool(same_speaker and not escalates)


def multi_segment_candidates(
    beats: list[dict],
    episode: int,
    ep_duration: float,
    shortlist: list[dict],
    max_gap: float = 50.0,
) -> list[dict]:
    """
    Pairs of moments from ONE episode, joined with the boring middle removed.

    The brief allows a promo to "join a few moments, from one episode or across
    several". Within an episode this is cheap and safe: same scene vocabulary,
    same characters, no identity resolution needed. So the rule is deliberate
    and narrow:

      * take two shortlisted windows from the same episode
      * trim each to its strongest part so the pair fits 20-60s together
      * the FIRST piece must contain the hook, the SECOND must end unresolved
      * the gap between them must be real (they must not be adjacent, or we
        have just rebuilt a single stretch) and not so large that the two
        moments belong to unrelated parts of the episode

    Scored with the same four sub-scores as a single stretch, with the hook
    taken from piece one and the cliffhanger from piece two, because that is
    what the viewer actually experiences.
    """
    ep_beats = episode_beats(beats, episode)
    anchors = anchor_beats(ep_beats)
    if len(shortlist) < 2 or not anchors:
        return []

    starts = sorted({round(b["start"], 2) for b in anchors})
    ends = sorted({round(b["end"], 2) for b in anchors})
    out: list[dict] = []

    for i, first in enumerate(shortlist):
        for second in shortlist[i + 1:]:
            a, b = sorted((first, second), key=lambda w: w["start"])
            gap = b["start"] - a["end"]
            if gap < 2.0 or gap > max_gap:
                continue

            # Trim each piece to a real beat boundary, aiming for roughly
            # half the budget each, hook end first then cliffhanger start.
            target = 17.0
            a_ends = [e for e in ends if a["start"] + 6.0 <= e <= a["start"] + target]
            b_starts = [s for s in starts if b["end"] - target <= s <= b["end"] - 6.0]
            if not a_ends or not b_starts:
                continue
            a_end = max(a_ends)
            b_start = min(b_starts)
            if b_start <= a_end:
                continue

            total = (a_end - a["start"]) + (b["end"] - b_start)
            if not (MIN_LEN <= total <= MAX_LEN):
                continue

            piece_one = beats_in_span(ep_beats, a["start"], a_end)
            piece_two = beats_in_span(ep_beats, b_start, b["end"])
            if not piece_one or not piece_two:
                continue

            hook, hook_beat = score_hook(piece_one, a["start"])
            if hook < MIN_HOOK or hook_beat is None:
                continue
            cliff, cliff_beat = score_cliffhanger(piece_two, ep_duration, b["end"])
            if cliff_beat is None:
                continue

            # The two halves must say different things. Without this the
            # generator produced promos that open on "You still think you are
            # better?!" and close on "You think you can lecture me?!" - the
            # same beat emotionally, so the clip ends where it started and
            # there is nothing for the viewer to need.
            if _redundant(piece_one, piece_two) or _no_arc(hook_beat, cliff_beat):
                continue
            tension = score_tension(piece_one + piece_two)
            standalone, detail = score_standalone(
                piece_one + piece_two, a["start"], b["end"]
            )
            # A cut between two moments costs the viewer something: they have
            # to bridge the jump themselves. Charge it rather than pretend
            # a spliced promo is as easy to follow as a continuous one.
            standalone = round(max(0.0, standalone - 0.10), 4)

            composite = (
                COMPOSITE_WEIGHTS["hook"] * hook
                + COMPOSITE_WEIGHTS["tension"] * tension
                + COMPOSITE_WEIGHTS["cliffhanger"] * cliff
                + COMPOSITE_WEIGHTS["standalone"] * standalone
            )
            out.append({
                "episode": episode,
                "multi": True,
                "pieces": [
                    {"start": round(a["start"], 2), "end": round(a_end, 2)},
                    {"start": round(b_start, 2), "end": round(b["end"], 2)},
                ],
                "start": round(a["start"], 2),
                "end": round(b["end"], 2),
                "duration_s": round(total, 2),
                "gap_removed_s": round(b_start - a_end, 2),
                "scores": {
                    "hook": hook, "tension": tension, "cliffhanger": cliff,
                    "standalone": standalone, "composite": round(composite, 4),
                },
                "hook_beat_id": hook_beat["id"],
                "cliffhanger_beat_id": cliff_beat["id"],
                "n_beats": len(piece_one) + len(piece_two),
                "standalone_detail": detail,
            })

    out.sort(key=lambda w: -w["scores"]["composite"])
    return out


def shortlist_episode(
    beats: list[dict], episode: int, ep_duration: float, top_k: int = 8
) -> tuple[list[dict], dict]:
    """
    Candidate windows for one episode, best first, de-overlapped.

    Returns (shortlist, stats) so the pipeline can report how many windows
    existed and how many were thrown out for having no hook.
    """
    ep_beats = episode_beats(beats, episode)
    windows = enumerate_windows(ep_beats)
    scored = [score_window(w, ep_beats, ep_duration) for w in windows]
    with_hook = [w for w in scored if w["scores"]["hook"] >= MIN_HOOK]
    shortlist = suppress_overlapping(with_hook)[:top_k]
    stats = {
        "episode": episode,
        "windows_enumerated": len(windows),
        "windows_with_hook": len(with_hook),
        "rejected_no_hook": len(scored) - len(with_hook),
        "shortlisted": len(shortlist),
    }
    return shortlist, stats


def tension_curve(beats: list[dict], episode: int, step: float = 0.5) -> list[dict]:
    """
    Per-second intensity for plotting. Max intensity of any beat alive at
    time t, which is what makes the hook spike and the final cut visible.
    """
    ep_beats = episode_beats(beats, episode)
    if not ep_beats:
        return []
    duration = max(b["end"] for b in ep_beats)
    out, t = [], 0.0
    while t <= duration:
        live = [b["intensity"] for b in ep_beats if b["start"] <= t < b["end"]]
        out.append({"t": round(t, 2), "intensity": round(max(live) if live else 0.0, 4)})
        t += step
    return out
