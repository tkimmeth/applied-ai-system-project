"""
profile_parser
==============

Turn a plain-English request like

    "I need calm music for coding, low energy, acoustic if possible"

into a structured profile the rest of the pipeline can use:

    {
        "genre": "lofi",
        "mood": "focused",
        "energy": 0.35,
        "likes_acoustic": True,
        "raw_request": "...",
        "warnings": [],
        "matched_terms": {...},
    }

This is a rule-based parser. No LLM, no API calls. It is intentionally
shallow because the assignment asks for something deterministic and
testable, and because catching contradictions is easier when the rules
are visible.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple


# --- Keyword tables ---------------------------------------------------------
#
# Each entry maps a trigger word -> the slot it touches. The parser walks
# these once and builds up evidence; conflicts are reported as warnings
# rather than silently overwritten.

_GENRE_HINTS: Dict[str, str] = {
    "lofi": "lofi", "lo-fi": "lofi", "study beats": "lofi",
    "pop": "pop", "top 40": "pop",
    "rock": "rock", "metal": "metal", "punk": "rock",
    "jazz": "jazz", "lounge": "jazz",
    "classical": "classical", "orchestra": "classical",
    "hip hop": "hip hop", "rap": "hip hop", "hip-hop": "hip hop",
    "country": "country", "folk": "folk",
    "synthwave": "synthwave", "retrowave": "synthwave",
    "electronic": "electronic", "edm": "electronic", "house": "electronic",
    "ambient": "ambient",
    "indie": "indie pop", "indie pop": "indie pop", "indie rock": "indie rock",
    "r&b": "r&b", "rnb": "r&b", "soul": "r&b",
}

_MOOD_HINTS: Dict[str, str] = {
    # focused / coding cluster
    "coding": "focused", "code": "focused", "study": "focused",
    "studying": "focused", "homework": "focused", "focus": "focused",
    "concentration": "focused", "deep work": "focused",
    # chill / calm cluster
    "chill": "chill", "calm": "chill", "mellow": "chill",
    "relax": "relaxed", "relaxed": "relaxed", "relaxing": "relaxed",
    # happy / upbeat
    "happy": "happy", "upbeat": "happy", "fun": "happy", "cheerful": "happy",
    "joyful": "happy",
    # sad
    "sad": "sad", "heartbreak": "sad", "lonely": "sad", "blue": "sad",
    "grief": "sad", "melancholy": "melancholy", "melancholic": "melancholy",
    # intense / energetic
    "intense": "intense", "aggressive": "intense", "angry": "intense",
    "energetic": "energetic", "hype": "energetic", "pumped": "energetic",
    # nostalgic / moody / romantic
    "nostalgic": "nostalgic", "throwback": "nostalgic",
    "moody": "moody", "brooding": "moody",
    "romantic": "romantic", "love song": "romantic",
}

# Activity hints push BOTH a mood and a genre when there is a strong
# common pairing (gym -> hip hop + energetic, coding -> lofi + focused).
_ACTIVITY_HINTS: Dict[str, Tuple[str, str, float]] = {
    "coding": ("lofi", "focused", 0.35),
    "code": ("lofi", "focused", 0.35),
    "study": ("lofi", "focused", 0.35),
    "studying": ("lofi", "focused", 0.35),
    "homework": ("lofi", "focused", 0.35),
    "gym": ("hip hop", "energetic", 0.90),
    "workout": ("hip hop", "energetic", 0.90),
    "running": ("electronic", "energetic", 0.85),
    "cardio": ("electronic", "energetic", 0.90),
    "party": ("pop", "happy", 0.85),
    "driving": ("synthwave", "moody", 0.65),
    "road trip": ("rock", "energetic", 0.75),
    "sleep": ("ambient", "chill", 0.20),
    "meditation": ("ambient", "chill", 0.20),
}

_ACOUSTIC_TRUE = ("acoustic", "guitar", "unplugged", "strings", "piano")
_ACOUSTIC_FALSE = ("electronic", "synth", "edm", "club", "techno", "bass drop")

# If the user said a mood but never named an energy level, fall back to a
# typical energy for that mood instead of the bland 0.55 default.
_MOOD_DEFAULT_ENERGY: Dict[str, float] = {
    "sad": 0.30,
    "melancholy": 0.25,
    "chill": 0.35,
    "relaxed": 0.35,
    "focused": 0.40,
    "happy": 0.75,
    "energetic": 0.85,
    "intense": 0.90,
    "moody": 0.55,
    "nostalgic": 0.45,
    "romantic": 0.45,
}

_ENERGY_PHRASES: Dict[str, float] = {
    "very low energy": 0.15,
    "low energy": 0.30,
    "calm": 0.30,
    "mellow": 0.35,
    "chill": 0.40,
    "medium energy": 0.55,
    "moderate energy": 0.55,
    "upbeat": 0.75,
    "high energy": 0.85,
    "very high energy": 0.95,
    "max energy": 0.95,
}


# --- Output shape -----------------------------------------------------------

@dataclass
class ParsedProfile:
    """Structured form of a natural-language request."""
    genre: str = "pop"
    mood: str = "happy"
    energy: float = 0.55
    likes_acoustic: bool = False
    raw_request: str = ""
    warnings: List[str] = field(default_factory=list)
    matched_terms: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_user_prefs(self) -> Dict:
        """Shape the existing recommender.score_song expects."""
        return {
            "genre": self.genre,
            "mood": self.mood,
            "energy": self.energy,
            "likes_acoustic": self.likes_acoustic,
        }


# --- Parser -----------------------------------------------------------------

def _scan(text: str, table: Dict[str, str]) -> List[Tuple[str, str]]:
    """Return [(trigger, value), ...] for every entry whose trigger appears in text."""
    hits: List[Tuple[str, str]] = []
    for trigger, value in table.items():
        if trigger in text:
            hits.append((trigger, value))
    return hits


def _vote(hits: List[Tuple[str, str]]) -> Tuple[str, List[str], List[str]]:
    """
    Pick the most common value among hits.
    Returns (winner_or_empty, all_distinct_values, all_triggers).
    """
    if not hits:
        return "", [], []
    counts: Dict[str, int] = {}
    triggers: List[str] = []
    for trig, val in hits:
        counts[val] = counts.get(val, 0) + 1
        triggers.append(trig)
    winner = max(counts.items(), key=lambda kv: kv[1])[0]
    return winner, list(counts.keys()), triggers


def parse_request(text: str) -> ParsedProfile:
    """
    Convert free-form English into a ParsedProfile.

    Approach:
        1. Lowercase, scan keyword tables.
        2. Activity hints push genre/mood/energy together.
        3. Explicit genre/mood words can override activity defaults.
        4. Energy phrases set energy directly when present.
        5. Acoustic flag pulled from a small whitelist/blacklist.
        6. Conflicts (multiple distinct genres, mood/energy mismatch,
           acoustic vs electronic) become warnings — they do not silently
           overwrite each other.
    """
    if not text or not text.strip():
        return ParsedProfile(
            raw_request=text or "",
            warnings=["empty request — using default profile"],
        )

    lowered = text.lower()
    profile = ParsedProfile(raw_request=text)
    matched: Dict[str, List[str]] = {}

    # --- Activity defaults (set first, so explicit hints can override) ----
    for trig, (g, m, e) in _ACTIVITY_HINTS.items():
        if trig in lowered:
            profile.genre = g
            profile.mood = m
            profile.energy = e
            matched.setdefault("activity", []).append(trig)
            break  # one activity is enough; first match wins

    # --- Genre ----------------------------------------------------------
    genre_hits = _scan(lowered, _GENRE_HINTS)
    genre_winner, genre_values, genre_triggers = _vote(genre_hits)
    if genre_winner:
        profile.genre = genre_winner
        matched["genre"] = genre_triggers
    if len(genre_values) > 1:
        profile.warnings.append(
            f"multiple genre hints found ({', '.join(genre_values)}); "
            f"picked '{genre_winner}'"
        )

    # --- Mood -----------------------------------------------------------
    mood_hits = _scan(lowered, _MOOD_HINTS)
    mood_winner, mood_values, mood_triggers = _vote(mood_hits)
    if mood_winner:
        profile.mood = mood_winner
        matched["mood"] = mood_triggers
    if len(mood_values) > 1:
        profile.warnings.append(
            f"multiple mood hints found ({', '.join(mood_values)}); "
            f"picked '{mood_winner}'"
        )

    # --- Energy --------------------------------------------------------
    # Priority: explicit phrase > mood default (only when no activity hint
    # already set the energy) > whatever the activity/default left in place.
    explicit_energy = None
    for phrase, value in _ENERGY_PHRASES.items():
        if phrase in lowered:
            explicit_energy = value
            matched.setdefault("energy", []).append(phrase)
    if explicit_energy is not None:
        profile.energy = explicit_energy
    elif "activity" not in matched and mood_winner in _MOOD_DEFAULT_ENERGY:
        profile.energy = _MOOD_DEFAULT_ENERGY[mood_winner]
        matched.setdefault("energy", []).append(f"mood-default:{mood_winner}")

    # --- Acoustic flag --------------------------------------------------
    wants_acoustic = any(t in lowered for t in _ACOUSTIC_TRUE)
    rejects_acoustic = any(t in lowered for t in _ACOUSTIC_FALSE)
    if wants_acoustic and rejects_acoustic:
        profile.warnings.append(
            "request mentions both acoustic and electronic cues"
        )
        # bias toward whichever appeared first in the text
        first_acoustic = min(
            (lowered.find(t) for t in _ACOUSTIC_TRUE if t in lowered),
            default=10**9,
        )
        first_electronic = min(
            (lowered.find(t) for t in _ACOUSTIC_FALSE if t in lowered),
            default=10**9,
        )
        profile.likes_acoustic = first_acoustic < first_electronic
    elif wants_acoustic:
        profile.likes_acoustic = True
        matched["acoustic"] = [t for t in _ACOUSTIC_TRUE if t in lowered]
    elif rejects_acoustic:
        profile.likes_acoustic = False
        matched["acoustic"] = [t for t in _ACOUSTIC_FALSE if t in lowered]

    # --- Cross-slot contradictions -------------------------------------
    # Sad + high energy is the textbook adversarial pattern.
    if profile.mood in ("sad", "melancholy") and profile.energy >= 0.7:
        profile.warnings.append(
            "request asks for a low-arousal mood with high energy — "
            "catalog rarely has both"
        )
    if profile.mood in ("focused", "chill", "relaxed") and profile.energy >= 0.8:
        profile.warnings.append(
            "request asks for a calm mood with very high energy"
        )
    if profile.mood == "happy" and profile.energy <= 0.25:
        profile.warnings.append(
            "request asks for a happy mood with very low energy"
        )

    # If we matched literally nothing, say so honestly.
    if not matched:
        profile.warnings.append(
            "no clear genre, mood, energy, or acoustic cue found — "
            "falling back to default pop/happy/0.55"
        )

    profile.matched_terms = matched
    return profile
