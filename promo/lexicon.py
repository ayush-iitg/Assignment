"""
Tone-tag intensity lexicon.

The screenplays label the delivery of almost every line of dialogue
("Cold, Commanding", "Screaming, Desperate"). 1,472 of 1,487 dialogue beats
carry at least one such tag across 617 distinct values. That is a free
emotion signal, so the promo scorer uses it instead of asking a model to
guess where the drama is.

These weights are MY judgment, not learned from data (there is no labelled
data). They are in one table, in the open, so they can be argued with. Three
bands, chosen so the numbers mean something:

  0.85 - 1.00  explosive: someone is screaming, striking, breaking
  0.55 - 0.80  charged: cruelty, threat, defiance, grief held in
  0.15 - 0.45  quiet: tenderness, calm, exposition

Unknown tags score 0.0 and are counted in the parse report, so coverage is
visible rather than assumed.
"""

TONE_INTENSITY: dict[str, float] = {
    # --- explosive -------------------------------------------------------
    "screaming": 1.00, "shrieking": 1.00, "roaring": 0.98, "enraged scream": 1.00,
    "maniacal": 0.97, "agonized": 0.96, "shouting": 0.94, "yelling": 0.94,
    "furious": 0.93, "enraged": 0.93, "hysterical": 0.93, "wailing": 0.92,
    "violent": 0.92, "frantic": 0.90, "panicked": 0.90, "terrified": 0.90,
    "horrified": 0.89, "murderous": 0.95, "savage": 0.92, "vicious": 0.88,
    "explosive": 0.95, "outraged": 0.88, "raging": 0.94, "berserk": 0.96,

    # --- charged ---------------------------------------------------------
    "desperate": 0.80, "pleading": 0.74, "begging": 0.76, "sobbing": 0.82,
    "weeping": 0.78, "crying": 0.76, "crying out": 0.84, "tearful": 0.70,
    "trembling": 0.68, "shaking": 0.68, "breathless": 0.66, "gasping": 0.72,
    "devastated": 0.80, "shattered": 0.80, "crushed": 0.76, "broken": 0.76,
    "heartbroken": 0.78, "anguished": 0.86, "betrayed": 0.76, "accusing": 0.74,
    "accusatory": 0.74, "defiant": 0.78, "fierce": 0.80, "unyielding": 0.72,
    "resolute": 0.68, "steely": 0.70, "determined": 0.66, "commanding": 0.72,
    "authoritative": 0.68, "stern": 0.62, "harsh": 0.70, "severely": 0.70,
    "cruel": 0.78, "callous": 0.74, "sadistic": 0.88, "malicious": 0.82,
    "hateful": 0.84, "spiteful": 0.76, "venomous": 0.82, "threatening": 0.82,
    "menacing": 0.82, "cold": 0.64, "icy": 0.66, "piercing": 0.72,
    "scathing": 0.76, "mocking": 0.70, "taunting": 0.72, "sneering": 0.70,
    "derisive": 0.70, "scornful": 0.72, "gloating": 0.74, "smug": 0.62,
    "triumphant": 0.70, "incredulous": 0.64, "disbelieving": 0.66,
    "shaken": 0.66, "urgent": 0.72, "bitter": 0.68, "disgusted": 0.70,
    "contemptuous": 0.72, "arrogant": 0.60, "conceited": 0.58, "haughty": 0.58,
    "condescending": 0.58, "dismissive": 0.56, "impatient": 0.56,
    "warning": 0.74, "ominous": 0.76, "grave": 0.60, "solemn": 0.50,
    "suspicious": 0.58, "guarded": 0.52, "evasive": 0.52, "scheming": 0.64,
    "sinister": 0.80, "chilling": 0.82, "unhinged": 0.90, "unapologetic": 0.58,
    "blunt": 0.58, "unforgiving": 0.66, "firm": 0.56, "emphatic": 0.60,
    "steadfast": 0.60, "proud": 0.54, "powerful": 0.70, "decisive": 0.64,
    "provocative": 0.70, "confrontational": 0.76, "insistent": 0.64,
    "vulnerable": 0.58, "raw": 0.70, "painful": 0.70, "grief-stricken": 0.84,
    "mournful": 0.62, "haunted": 0.66, "hollow": 0.58, "numb": 0.50,
    "confused": 0.48, "bewildered": 0.52, "unbelieving": 0.60,
    "dignified": 0.54, "controlled": 0.48, "subdued": 0.40, "restrained": 0.46,

    # --- quiet -----------------------------------------------------------
    "whispering": 0.44, "hushed": 0.42, "murmuring": 0.38, "quiet": 0.32,
    "soft": 0.28, "softly": 0.28, "gentle": 0.26, "tender": 0.28,
    "warm": 0.24, "kind": 0.24, "calm": 0.32, "measured": 0.34,
    "low": 0.36, "flat": 0.30, "matter-of-fact": 0.26, "neutral": 0.20,
    "sincere": 0.34, "earnest": 0.40, "reflective": 0.30, "wistful": 0.34,
    "nostalgic": 0.30, "curious": 0.34, "questioning": 0.40, "hopeful": 0.36,
    "relieved": 0.38, "grateful": 0.32, "amused": 0.34, "cheerful": 0.30,
    "playful": 0.32, "teasing": 0.44, "shy": 0.26, "hesitant": 0.40,
    "uncertain": 0.42, "weary": 0.42, "tired": 0.36, "resigned": 0.44,
    "formal": 0.24, "polite": 0.20, "respectful": 0.24, "reverent": 0.30,
    "observant": 0.26, "thoughtful": 0.30, "patient": 0.26, "reassuring": 0.34,
    "comforting": 0.32, "protective": 0.56, "intimate": 0.46, "longing": 0.48,
    "affectionate": 0.30, "loving": 0.32, "concerned": 0.48, "worried": 0.54,
    "anxious": 0.58, "nervous": 0.54, "cautious": 0.44, "apologetic": 0.36,
    "humble": 0.26, "obedient": 0.24, "submissive": 0.28,

    # --- second pass: the 40 most frequent tags the first draft missed ----
    # Found by running the scorer over all 50 episodes and printing unknown
    # tags by frequency. Raised lexicon hit rate from 81.4% to the figure in
    # outputs/parse_report.json. Keeping this block separate so the method is
    # visible: measure the gap, then close it, rather than guessing twice.
    "demanding": 0.74, "sharp": 0.72, "passionate": 0.72, "final": 0.70,
    "resonant": 0.60, "calculating": 0.64, "steady": 0.44, "alarmed": 0.76,
    "deep": 0.44, "inquiring": 0.40, "focused": 0.48, "stunned": 0.72,
    "grim": 0.64, "choked": 0.76, "choked with tears": 0.82, "gleeful": 0.66,
    "booming": 0.86, "direct": 0.50, "somber": 0.52, "dark": 0.66,
    "emotional": 0.70, "shocked": 0.76, "vindictive": 0.82, "pained": 0.72,
    "indignant": 0.74, "certain": 0.54, "unwavering": 0.66, "despairing": 0.84,
    "sorrowful": 0.70, "intense": 0.74, "ruthless": 0.84, "condemning": 0.78,
    "clear": 0.46, "thunderous": 0.92, "deadly": 0.86, "gruff": 0.58,
    "smooth": 0.42, "scoffing": 0.64, "disdainful": 0.62, "unflinching": 0.68,
}

# Physical events in ACTION / SOUND FX text. A promo can open on a slap with
# no dialogue at all, which is exactly what the brief describes, so these
# cannot be ignored just because they carry no tone tag.
ACTION_KEYWORDS: dict[str, float] = {
    "slap": 1.00, "slaps": 1.00, "strikes": 0.95, "strike": 0.92, "punch": 0.95,
    "whip": 0.92, "lash": 0.90, "stab": 1.00, "stabs": 1.00, "dagger": 0.88,
    "blade": 0.84, "knife": 0.86, "blood": 0.82, "bloody": 0.80,
    "bleeding": 0.80, "wound": 0.74, "shoves": 0.84, "shove": 0.84,
    "slams": 0.88, "slam": 0.88, "throws": 0.80, "hurls": 0.84, "drags": 0.82,
    "grabs": 0.74, "seizes": 0.76, "chokes": 0.95, "strangl": 0.96,
    "collapse": 0.84, "collapses": 0.84, "falls": 0.66, "crashes": 0.84,
    "screams": 0.95, "scream": 0.95, "gasps": 0.68, "gasp": 0.68,
    "convuls": 0.88, "poison": 0.88, "dies": 0.95, "dead": 0.88,
    "kill": 0.92, "corpse": 0.88, "gallows": 0.90, "noose": 0.92,
    "brand": 0.88, "branding": 0.90, "searing": 0.86, "burn": 0.84,
    "flames": 0.78, "fire": 0.70, "shatters": 0.82, "smashes": 0.86,
    "explodes": 0.90, "gunshot": 0.95, "chains": 0.70, "shackles": 0.72,
    "cell": 0.62, "dungeon": 0.68, "gavel": 0.74, "verdict": 0.72,
    "pregnant": 0.84, "pregnancy": 0.84, "wedding": 0.62, "altar": 0.62,
    "kiss": 0.68, "kisses": 0.68, "embrace": 0.52, "tears": 0.60,
    "slaps her": 1.00, "cut to black": 0.55,
}

# Markers that a line leaves the situation open. Used by the cliffhanger
# score: a promo should stop mid-problem, not after the problem is solved.
UNRESOLVED_MARKERS: tuple[str, ...] = (
    "?",            # a question nobody has answered yet
    "...",          # trailing off / interrupted
    "—",            # cut off mid-sentence
)

THREAT_WORDS: tuple[str, ...] = (
    "will", "unless", "if you", "i swear", "you will", "never", "tomorrow",
    "tonight", "before dawn", "or else", "i promise you", "watch", "wait",
)


def tone_intensity(tags: list[str]) -> tuple[float, list[str]]:
    """
    Intensity of a dialogue beat = the strongest emotion it carries.

    Returns (score, unknown_tags). Max rather than mean: "Cold, Commanding"
    is a cold line, and averaging in a mild second tag would dilute a strong
    first one.
    """
    scores, unknown = [], []
    for tag in tags:
        key = tag.strip().lower()
        if key in TONE_INTENSITY:
            scores.append(TONE_INTENSITY[key])
        else:
            # try the head word: "calm, cutting" -> "calm"
            head = key.split()[0] if key.split() else ""
            if head in TONE_INTENSITY:
                scores.append(TONE_INTENSITY[head])
            else:
                unknown.append(key)
    return (max(scores) if scores else 0.0), unknown


def action_intensity(text: str) -> float:
    """Intensity of an ACTION / SFX beat, from physical-event keywords."""
    low = text.lower()
    hits = [w for kw, w in ACTION_KEYWORDS.items() if kw in low]
    return max(hits) if hits else 0.0
