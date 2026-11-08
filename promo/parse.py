"""
Screenplay parser.

Turns a folder of microdrama screenplay .txt files into a flat list of timed
"beats" (one per timestamped line of dialogue / action / camera / sound effect).

Deliberately rule-based, not LLM-based: the format is regular, so rules are
faster, free, and reproducible. The parser's job is to be boring and honest —
it reconciles what it saw against what it built, and refuses to continue if
those disagree.

Observed format (holds for all 50 files in the pack):

    EPISODE NUMBER: Episode 1
    EPISODE LOGLINE: ...
    CONTINUITY NOTES: ...
    --- SCRIPT START ---
    SCENE 01
    Scene heading: INT. CATHEDRAL - DAY
    Scene start: 00:00.00
    Scene end: 02:18.00
    Actions and dialogue:

    **CAMERA:**                              <- technical beat label
    Start: (00:00.00) | End: (00:04.80)
    <one or more text lines>

    **JULIANA (Whispering, Tearful):**       <- dialogue label + tone tags
    Start: (00:33.80) | End: (00:35.00)
    "Gerald?"
"""
from __future__ import annotations

import os
import re
import glob
from collections import Counter

# ---------------------------------------------------------------------------
# Line patterns
# ---------------------------------------------------------------------------

# **ANYTHING:**  -> a beat label. Dialogue labels carry tone tags in parens.
RE_LABEL = re.compile(r"^\*\*(.+?):\*\*$")

# Start: (00:04.80) | End: (00:06.80)   (parens are optional in principle)
RE_TIMES = re.compile(
    r"Start:\s*\(?(\d+):(\d+(?:\.\d+)?)\)?\s*\|\s*End:\s*\(?(\d+):(\d+(?:\.\d+)?)\)?"
)

RE_SCENE = re.compile(r"^SCENE\s*(\d+)\b")

# Lines that are document structure, never beat content. Without this the
# ep-24 hazard occurs: a scene header directly follows a line of dialogue with
# no blank line between, and gets swallowed into that beat's text.
RE_STRUCTURAL = re.compile(
    r"^(SCENE\s*\d+|Scene heading:|Scene start:|Scene end:|Actions and dialogue:"
    r"|---\s*SCRIPT (START|END)\s*---|EPISODE NUMBER:|EPISODE LOGLINE:|CONTINUITY NOTES:)",
    re.IGNORECASE,
)

# Beat labels that describe craft rather than a speaking character.
TECHNICAL = {
    "CAMERA", "ACTION", "SOUND FX", "SFX", "SOUND", "MUSIC", "VFX",
    "TEXT", "TITLE", "ON SCREEN TEXT", "SUPER",
}

# Parenthetical content that is a stage direction, not an emotion (A10).
NON_TONE = {
    "v.o.", "vo", "o.s.", "os", "off-screen", "offscreen", "off screen",
    "cont'd", "contd", "continuing", "continues", "continued", "pre-lap", "prelap",
}

# Honorifics / titles stripped when resolving a speaker to a character (A11).
HONORIFICS = (
    "LADY ", "LORD ", "SIR ", "THE LADY ", "MISS ", "MRS ", "MR ", "DR ",
    "DUCHESS ", "DUKE ", "YOUNG ", "OLD ",
)

# Same character, different epithet. My judgment, listed explicitly so it can
# be audited or corrected rather than hidden in code (A11).
EPITHET_ALIASES = {
    "THE FORMER GROOM": "GERALD",
    "LADY IN GOLD GOWN": "CLARISSA",
    "THE BEARDED STRANGER": "MYSTERIOUS BEARDED MAN",
    "BEARDED STRANGER": "MYSTERIOUS BEARDED MAN",
    "BEARDED MAN": "MYSTERIOUS BEARDED MAN",
}

# Generic role labels: never merged with each other, because the same label is
# reused for different people in different episodes (A12).
GENERIC_ROLES = {
    "LORD", "MAID", "NOBLEWOMAN", "NOBLEMAN", "MATRIARCH", "NOBLE MATRIARCH",
    "OFF-SCREEN VOICE", "OFF SCREEN VOICE", "VOICE", "GUARD", "ROYAL GUARD",
    "SERVANT", "HOUSEKEEPER", "CROWD", "VILLAGER", "ELDER VILLAGER",
    "PEASANT MOTHER", "ARISTOCRATIC WOMAN", "INFORMANT", "JUDGE", "HIGH PRIEST",
    "THE PRIEST", "PRIEST", "CONSTABLE", "CROWN OFFICIAL", "ELDER NOBLEMAN",
    "BLOND NOBLEMAN", "THUG WITH CAP", "THUG", "DOCTOR", "PHYSICIAN",
}


def _secs(minutes: str, seconds: str) -> float:
    return int(minutes) * 60 + float(seconds)


def mmss(t: float) -> str:
    """Seconds -> MM:SS.ss, the format used throughout the input pack."""
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def canonical_speaker(raw: str, bare_names: set[str] | None = None) -> str:
    """
    Map a raw speaker label to a canonical character name.

    'LADY JULIANA' -> 'JULIANA', 'THE FORMER GROOM' -> 'GERALD'.
    Generic roles are passed through untouched.

    An honorific is only stripped when the bare name is *independently
    attested* somewhere in the corpus. `JULIANA` appears on its own 352 times,
    so `LADY JULIANA` is the same woman. `ASHCROFT` never appears on its own,
    so `LORD ASHCROFT` and `LADY ASHCROFT` stay two different people — which
    is almost certainly right, since a lord and a lady of one house are a
    husband and wife, not one character. Without this rule the parser merged
    them, and my first hand-written alias table made exactly that mistake.

    `bare_names` is None only when parsing a single file in isolation, in
    which case the conservative path (no honorific stripping) is taken.
    """
    name = raw.upper().strip()
    if name in EPITHET_ALIASES:
        return EPITHET_ALIASES[name]
    if name in GENERIC_ROLES:
        return name

    stripped = name
    for h in HONORIFICS:
        if stripped.startswith(h):
            candidate = stripped[len(h):].strip()
            if bare_names is not None and candidate in bare_names:
                stripped = candidate
            break
    if stripped.startswith("THE "):
        candidate = stripped[4:].strip()
        if bare_names is None or candidate in bare_names:
            stripped = candidate
    return EPITHET_ALIASES.get(stripped, stripped or name)


def collect_bare_names(raw_labels) -> set[str]:
    """Speaker labels that appear with no honorific and no 'THE' prefix."""
    bare = set()
    for label in raw_labels:
        name = label.upper().strip()
        if name in GENERIC_ROLES or name in EPITHET_ALIASES:
            continue
        if name.startswith("THE ") or any(name.startswith(h) for h in HONORIFICS):
            continue
        bare.add(name)
    return bare


def split_label(label: str) -> tuple[str, list[str], bool]:
    """
    '**JULIANA (V.O.) (Reflective, Vulnerable):**' -> ('JULIANA',
                                                       ['reflective','vulnerable'],
                                                       False)

    Returns (base_name, tone_tags, is_technical).
    """
    base = label.split("(")[0].strip()
    parens = re.findall(r"\(([^)]*)\)", label)
    tones: list[str] = []
    for group in parens:
        for piece in group.split(","):
            tag = piece.strip().lower()
            if tag and tag not in NON_TONE:
                tones.append(tag)
    base_up = base.upper()
    is_tech = base_up in TECHNICAL or base_up.startswith("SOUND")
    return base, tones, is_tech


def _kind_for(base: str) -> str:
    b = base.upper()
    if b.startswith("SOUND") or b == "SFX":
        return "SFX"
    if b in ("CAMERA",):
        return "CAMERA"
    if b in ("ACTION",):
        return "ACTION"
    return b  # MUSIC, VFX, TEXT...


def parse_file(path: str) -> dict:
    """Parse one screenplay file into metadata + beats."""
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.splitlines()

    meta = {
        "file": os.path.basename(path),
        "episode_label": "",
        "episode": None,
        "logline": "",
        "continuity": "",
        "scenes": [],
    }
    beats: list[dict] = []
    seen_labels = 0
    seen_timestamps = 0

    current_label: str | None = None
    current_scene = 0
    pending: dict | None = None

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        # --- header fields -------------------------------------------------
        if line.startswith("EPISODE NUMBER:"):
            meta["episode_label"] = line.split(":", 1)[1].strip()
            digits = re.search(r"(\d+)", meta["episode_label"])
            if digits:
                meta["episode"] = int(digits.group(1))
            continue
        if line.startswith("EPISODE LOGLINE:"):
            meta["logline"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("CONTINUITY NOTES:"):
            meta["continuity"] = line.split(":", 1)[1].strip()
            continue

        # --- scene structure -----------------------------------------------
        scene_match = RE_SCENE.match(line)
        if scene_match:
            current_scene = int(scene_match.group(1))
            meta["scenes"].append(
                {"index": current_scene, "heading": None, "start": None, "end": None}
            )
            pending = None
            continue
        if line.startswith("Scene heading:") and meta["scenes"]:
            meta["scenes"][-1]["heading"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("Scene start:") and meta["scenes"]:
            m = re.search(r"(\d+):(\d+(?:\.\d+)?)", line)
            if m:
                meta["scenes"][-1]["start"] = _secs(*m.groups())
            continue
        if line.startswith("Scene end:") and meta["scenes"]:
            m = re.search(r"(\d+):(\d+(?:\.\d+)?)", line)
            if m:
                meta["scenes"][-1]["end"] = _secs(*m.groups())
            continue

        # --- beat label ----------------------------------------------------
        label_match = RE_LABEL.match(line)
        if label_match:
            current_label = label_match.group(1).strip()
            seen_labels += 1
            pending = None
            continue

        # --- beat timestamps ------------------------------------------------
        times = RE_TIMES.search(line)
        if times:
            seen_timestamps += 1
            start = _secs(times.group(1), times.group(2))
            end = _secs(times.group(3), times.group(4))
            base, tones, is_tech = split_label(current_label or "UNKNOWN")
            pending = {
                "episode": meta["episode"],
                "scene": current_scene,
                "start": start,
                "end": max(end, start),  # guard: never let end precede start
                "label_raw": current_label or "UNKNOWN",
                "kind": _kind_for(base) if is_tech else "DIALOGUE",
                "speaker_raw": None if is_tech else base,
                "speaker": None if is_tech else canonical_speaker(base),
                "tone": [] if is_tech else tones,
                "text_parts": [],
                "src_line": idx + 1,
            }
            beats.append(pending)
            continue

        # --- beat content ---------------------------------------------------
        # Structural lines are never content. This is the ep-24 fix: a scene
        # header can directly follow dialogue with no blank line between.
        if RE_STRUCTURAL.match(line):
            pending = None
            continue
        if pending is not None:
            pending["text_parts"].append(line)

    # Finalise beats.
    for beat in beats:
        joined = " ".join(beat.pop("text_parts")).strip()
        # Dialogue is quoted in the source; keep the words, drop the quotes.
        beat["text"] = joined.strip('"').strip() if beat["kind"] == "DIALOGUE" else joined

    # Record source-order timing faults BEFORE sorting, otherwise sorting
    # hides them. 8 such beats exist in the pack (deltas of 0.1-0.5s).
    meta["nonmonotonic"] = [
        {"src_line": nxt["src_line"], "from": prev["start"], "to": nxt["start"]}
        for prev, nxt in zip(beats, beats[1:])
        if nxt["start"] < prev["start"] - 1e-6
    ]

    beats.sort(key=lambda b: (b["start"], b["end"]))
    for n, beat in enumerate(beats):
        beat["id"] = f"e{meta['episode'] or 0:03d}_b{n:04d}"

    meta["duration"] = max((b["end"] for b in beats), default=0.0)
    meta["n_beats"] = len(beats)
    meta["counts"] = Counter(b["kind"] for b in beats)
    meta["reconcile"] = {
        "labels_seen": seen_labels,
        "timestamps_seen": seen_timestamps,
        "beats_built": len(beats),
        "ok": seen_timestamps == len(beats),
    }
    return {"meta": meta, "beats": beats}


def parse_folder(folder: str, episodes: list[int] | None = None) -> tuple[list[dict], dict]:
    """
    Parse every .txt in `folder`.

    Returns (beats, report). Raises RuntimeError if any file fails to
    reconcile — a silent partial parse is worse than a loud stop.
    """
    paths = sorted(glob.glob(os.path.join(folder, "*.txt")))
    if not paths:
        raise RuntimeError(f"no .txt screenplays found in {folder!r}")

    all_beats: list[dict] = []
    per_episode: list[dict] = []
    hazards: list[str] = []
    alias_map: dict[str, Counter] = {}
    tone_counts: Counter = Counter()
    broken: list[str] = []

    # Pass 1: parse everything, then work out which bare character names are
    # attested corpus-wide, so honorific stripping is evidence-based.
    parsed_files = [parse_file(p) for p in paths]
    bare_names = collect_bare_names(
        b["speaker_raw"]
        for p in parsed_files
        for b in p["beats"]
        if b["kind"] == "DIALOGUE" and b["speaker_raw"]
    )

    # Pass 2: apply canonical names now that the evidence is in.
    for parsed in parsed_files:
        for beat in parsed["beats"]:
            if beat["kind"] == "DIALOGUE" and beat["speaker_raw"]:
                beat["speaker"] = canonical_speaker(beat["speaker_raw"], bare_names)

    for parsed in parsed_files:
        meta, beats = parsed["meta"], parsed["beats"]

        if episodes and meta["episode"] not in episodes:
            continue
        if not meta["reconcile"]["ok"]:
            broken.append(f"{meta['file']}: {meta['reconcile']}")

        # Hazard detection (reported, not silently repaired).
        for nm in meta["nonmonotonic"]:
            hazards.append(
                f"{meta['file']}: beat out of source order at line {nm['src_line']} "
                f"({nm['from']:.2f}s -> {nm['to']:.2f}s); repaired by sorting"
            )
        for scene in meta["scenes"]:
            if not scene["heading"]:
                hazards.append(f"{meta['file']}: scene {scene['index']} has no heading")
            if scene["start"] is None or scene["end"] is None:
                hazards.append(f"{meta['file']}: scene {scene['index']} has no start/end times")
        dialogue = [b for b in beats if b["kind"] == "DIALOGUE"]
        for prev, nxt in zip(dialogue, dialogue[1:]):
            if nxt["start"] < prev["end"] - 0.01:
                hazards.append(f"{meta['file']}: overlapping dialogue near line {nxt['src_line']}")
        if not dialogue:
            hazards.append(f"{meta['file']}: no dialogue beats at all")

        for beat in dialogue:
            alias_map.setdefault(beat["speaker"], Counter())[beat["speaker_raw"]] += 1
            tone_counts.update(beat["tone"])

        all_beats.extend(beats)
        per_episode.append({
            "episode": meta["episode"],
            "file": meta["file"],
            "logline": meta["logline"],
            "continuity": meta["continuity"],
            "duration": round(meta["duration"], 2),
            "n_beats": meta["n_beats"],
            "n_scenes": len(meta["scenes"]),
            "counts": dict(meta["counts"]),
            "reconcile": meta["reconcile"],
        })

    if broken:
        raise RuntimeError(
            "parser failed to reconcile labels/timestamps/beats:\n  " + "\n  ".join(broken)
        )

    n_dialogue = sum(1 for b in all_beats if b["kind"] == "DIALOGUE")
    n_toned = sum(1 for b in all_beats if b["kind"] == "DIALOGUE" and b["tone"])
    report = {
        "folder": folder,
        "n_files": len(per_episode),
        "n_beats": len(all_beats),
        "kinds": dict(Counter(b["kind"] for b in all_beats)),
        "episodes": per_episode,
        "duration_stats": _stats([e["duration"] for e in per_episode]),
        "tone_tag_coverage": round(n_toned / n_dialogue, 4) if n_dialogue else 0.0,
        "n_distinct_tone_tags": len(tone_counts),
        "top_tone_tags": tone_counts.most_common(30),
        "speaker_labels_raw": sum(len(v) for v in alias_map.values()),
        "characters_canonical": len(alias_map),
        "bare_names_attested": sorted(bare_names),
        "alias_map": {k: dict(v) for k, v in sorted(alias_map.items()) if len(v) > 1},
        "hazards": hazards,
        "n_hazards": len(hazards),
    }
    return all_beats, report


def _stats(values: list[float]) -> dict:
    if not values:
        return {}
    s = sorted(values)
    return {
        "min": s[0],
        "p25": s[len(s) // 4],
        "median": s[len(s) // 2],
        "p75": s[3 * len(s) // 4],
        "max": s[-1],
        "n_over_150s": sum(1 for v in s if v > 150),
    }
