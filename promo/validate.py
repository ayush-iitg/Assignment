"""
Hard validators.

These are pass/fail, not advisory. A promo that fails any of them never
reaches the output file; it goes to rejected_promos.json with the reason, so
the failure rate is a reported number rather than a hidden one.

The first check is the one that matters most. The model is never shown a
timestamp and answers only in beat IDs, so a hallucinated timestamp should be
structurally impossible - this check proves that claim on every run instead
of asserting it in a document.
"""
from __future__ import annotations

import re
from .score import MIN_LEN, MAX_LEN, HOOK_WINDOW

RE_WORD = re.compile(r"[a-z']+")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "at",
    "for", "with", "is", "are", "was", "were", "be", "been", "am", "i", "you",
    "he", "she", "it", "we", "they", "me", "him", "her", "them", "us", "my",
    "your", "his", "its", "our", "their", "this", "that", "these", "those",
    "as", "so", "not", "no", "do", "does", "did", "have", "has", "had", "will",
    "would", "can", "could", "what", "who", "why", "how", "when", "where",
}


def validate_promo(promo: dict, beat_index: dict) -> dict:
    """
    Run every check against one promo.

    `beat_index` maps beat_id -> beat, which is the authority on what
    timestamps exist.
    """
    failures: list[str] = []
    checks: dict[str, bool] = {}

    # 1. Every timestamp must correspond to a real parsed beat edge.
    starts = {round(b["start"], 2) for b in beat_index.values()}
    ends = {round(b["end"], 2) for b in beat_index.values()}
    ok = True
    for seg in promo["segments"]:
        if round(seg["start_s"], 2) not in starts:
            ok = False
            failures.append(f"segment start {seg['start']} is not any beat's start time")
        if round(seg["end_s"], 2) not in ends:
            ok = False
            failures.append(f"segment end {seg['end']} is not any beat's end time")
    checks["timestamps_exist"] = ok

    # 2. Total length inside the brief's 20-60s band.
    total = promo["total_duration_s"]
    checks["length_ok"] = MIN_LEN - 1e-6 <= total <= MAX_LEN + 1e-6
    if not checks["length_ok"]:
        failures.append(f"total duration {total}s outside [{MIN_LEN}, {MAX_LEN}]")

    # 3. Each segment must run forwards, and segments must not overlap.
    ok = True
    for seg in promo["segments"]:
        if seg["end_s"] <= seg["start_s"]:
            ok = False
            failures.append(f"segment {seg['order']} ends at or before it starts")
    same_ep = {}
    for seg in promo["segments"]:
        same_ep.setdefault(seg["episode"], []).append(seg)
    for ep, segs in same_ep.items():
        for a, b in zip(segs, segs[1:]):
            if b["start_s"] < a["end_s"] - 1e-6:
                ok = False
                failures.append(f"segments overlap within episode {ep}")
    checks["order_ok"] = ok

    # 4. The hook must land within the first 3 seconds of the promo.
    hook_beat = beat_index.get(promo.get("hook_beat_id") or "")
    first = promo["segments"][0]
    if hook_beat is None:
        checks["hook_within_3s"] = False
        failures.append("hook beat id does not exist")
    else:
        offset = hook_beat["start"] - first["start_s"]
        checks["hook_within_3s"] = -1e-6 <= offset <= HOOK_WINDOW + 1e-6
        if not checks["hook_within_3s"]:
            failures.append(
                f"hook beat starts {offset:.2f}s into the promo, limit is {HOOK_WINDOW}s"
            )

    # 5. Hook and cliffhanger must be inside the promo's own segments.
    def inside(beat) -> bool:
        return any(
            beat["start"] >= s["start_s"] - 1e-6 and beat["start"] <= s["end_s"] + 1e-6
            and beat["episode"] == s["episode"]
            for s in promo["segments"]
        )

    cliff_beat = beat_index.get(promo.get("cliffhanger_beat_id") or "")
    checks["hook_inside_promo"] = bool(hook_beat) and inside(hook_beat)
    checks["cliffhanger_inside_promo"] = bool(cliff_beat) and inside(cliff_beat)
    if not checks["hook_inside_promo"]:
        failures.append("hook beat is not inside the promo's own segments")
    if not checks["cliffhanger_inside_promo"]:
        failures.append("cliffhanger beat is not inside the promo's own segments")

    promo["validators"] = checks
    promo["validator_failures"] = failures
    promo["valid"] = not failures
    return promo


# ---------------------------------------------------------------------------
# Near-duplicate suppression
# ---------------------------------------------------------------------------

def _bag(text: str) -> set[str]:
    return {w for w in RE_WORD.findall(text.lower()) if w not in STOPWORDS and len(w) > 2}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Beats that describe what the viewer SEES. Repetition in a microdrama is
# visual, not verbal - the same image gets reused with different words.
VISUAL_KINDS = ("CAMERA", "ACTION", "SFX")


def suppress_duplicates(
    promos: list[dict],
    beat_index: dict,
    threshold: float = 0.17,
    max_episode_gap: int = 2,
) -> tuple[list[dict], list[dict]]:
    """
    Drop promos that show nearly the same thing as a higher-ranked one.

    Needed because adjacent episodes reuse cliffhanger framing: episodes 31
    and 32 both end on a branding iron stopping inches from Juliana's eye. An
    editor who posts two near-identical clips has wasted a slot.

    Both the signal and the threshold were measured, not guessed. Over all
    1,225 promo pairs from a 50-episode run:

      * Jaccard on DIALOGUE text peaks at 0.177 and puts ep31/ep32 at 0.157,
        mid-pack - the lines are genuinely different, so a lexical check on
        speech cannot see the repeat. An earlier 0.45 threshold on dialogue
        text could never fire at all, and didn't.
      * Jaccard on VISUAL text puts ep31/ep32 at 0.191, 4th highest of 1,225,
        and 6 of the top 7 pairs are episodes 1-2 apart.

    Hence: visual-word overlap above 0.17 between episodes no more than 2
    apart. The adjacency condition matters - the highest cross-corpus pair
    (episodes 4 and 40, 0.174) is shared period vocabulary, not a reused
    image, and should not be suppressed.

    Jaccard rather than embeddings: no extra dependency, no API call, and the
    number can be recomputed by hand from the output files.
    """
    kept: list[dict] = []
    dropped: list[dict] = []
    for promo in sorted(promos, key=lambda p: -p["scores"]["composite"]):
        visual = " ".join(
            beat_index[bid]["text"] for bid in promo.get("source_beat_ids", [])
            if bid in beat_index and beat_index[bid]["kind"] in VISUAL_KINDS
        )
        promo["_bag"] = _bag(visual)
        clash = None
        for other in kept:
            gap = min(
                abs(a - b) for a in promo["episodes"] for b in other["episodes"]
            )
            if gap > max_episode_gap:
                continue
            score = jaccard(promo["_bag"], other["_bag"])
            if score >= threshold:
                clash = (other, score, gap)
                break
        if clash:
            other, score, gap = clash
            promo["rejected_reason"] = (
                f"near-duplicate of {other['promo_id']} (episodes "
                f"{other['episodes']}, {gap} apart, visual overlap {score:.2f} "
                f">= {threshold})"
            )
            dropped.append(promo)
        else:
            kept.append(promo)
    for promo in kept + dropped:
        promo.pop("_bag", None)
    return kept, dropped
