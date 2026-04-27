"""
retriever
=========

Pull a candidate set of songs out of the catalog before scoring.

The original Module 3 project scored every song every time. That works
for 18 rows but it isn't really how a real recommender pipeline is
shaped — usually there is a retrieval stage that narrows the field with
cheap filters first, then a ranker does the expensive math on what's
left.

This module mimics that two-stage shape and attaches "evidence" to each
candidate (mood match, genre match, energy delta, acoustic match) so
the rest of the pipeline can show its work and the evaluator can grade
the retrieval itself.

Two modes:
    * strict  — keep songs that match at least two of {genre, mood,
                acoustic} OR are within ENERGY_TOL of target energy.
    * relaxed — keep anything within RELAXED_ENERGY_TOL of target
                energy and also throw in genre/mood neighbors. Used by
                the agent's retry path when the strict pass returned
                too little.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from src.profile_parser import ParsedProfile


# Genre neighborhoods. Used by relaxed retrieval to keep e.g. "pop"
# from looking like a hard wall against indie pop, synthwave from a
# wall against electronic, etc.
GENRE_NEIGHBORS: Dict[str, List[str]] = {
    "pop": ["indie pop", "synthwave"],
    "indie pop": ["pop", "indie rock"],
    "rock": ["indie rock", "metal"],
    "indie rock": ["rock", "indie pop"],
    "metal": ["rock"],
    "lofi": ["ambient", "jazz"],
    "ambient": ["lofi", "classical"],
    "classical": ["ambient"],
    "jazz": ["lofi", "r&b"],
    "r&b": ["jazz", "pop"],
    "synthwave": ["electronic", "pop"],
    "electronic": ["synthwave", "hip hop"],
    "hip hop": ["electronic", "r&b"],
    "country": ["folk"],
    "folk": ["country", "lofi"],
}

# Mood neighborhoods. Same idea — "chill" and "relaxed" should help
# each other; "focused" sits between them; "intense" and "energetic"
# are close cousins.
MOOD_NEIGHBORS: Dict[str, List[str]] = {
    "happy": ["energetic"],
    "sad": ["melancholy", "moody"],
    "melancholy": ["sad", "moody"],
    "moody": ["melancholy", "nostalgic"],
    "chill": ["relaxed", "focused"],
    "relaxed": ["chill", "focused"],
    "focused": ["chill", "relaxed"],
    "intense": ["energetic"],
    "energetic": ["intense", "happy"],
    "nostalgic": ["moody", "romantic"],
    "romantic": ["nostalgic", "chill"],
}

ENERGY_TOL = 0.20
RELAXED_ENERGY_TOL = 0.40
ACOUSTIC_THRESHOLD = 0.6


@dataclass
class Candidate:
    """One retrieved song plus the reasons it survived retrieval."""
    song: Dict
    evidence: List[str] = field(default_factory=list)
    relaxed: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.song["id"],
            "title": self.song["title"],
            "artist": self.song["artist"],
            "genre": self.song["genre"],
            "mood": self.song["mood"],
            "energy": self.song["energy"],
            "acousticness": self.song["acousticness"],
            "evidence": list(self.evidence),
            "relaxed": self.relaxed,
        }


def _evidence_for(profile: ParsedProfile, song: Dict, relaxed: bool) -> List[str]:
    """Build the evidence list explaining why this song was kept."""
    ev: List[str] = []

    if song["genre"] == profile.genre:
        ev.append(f"genre match ({profile.genre})")
    elif relaxed and song["genre"] in GENRE_NEIGHBORS.get(profile.genre, []):
        ev.append(f"genre neighbor ({song['genre']} ~ {profile.genre})")

    if song["mood"] == profile.mood:
        ev.append(f"mood match ({profile.mood})")
    elif relaxed and song["mood"] in MOOD_NEIGHBORS.get(profile.mood, []):
        ev.append(f"mood neighbor ({song['mood']} ~ {profile.mood})")

    energy_diff = abs(song["energy"] - profile.energy)
    tol = RELAXED_ENERGY_TOL if relaxed else ENERGY_TOL
    if energy_diff <= tol:
        ev.append(f"energy close (Δ {energy_diff:.2f})")

    is_acoustic = song["acousticness"] >= ACOUSTIC_THRESHOLD
    if profile.likes_acoustic and is_acoustic:
        ev.append("acoustic match")
    elif not profile.likes_acoustic and not is_acoustic:
        ev.append("non-acoustic match")

    return ev


def retrieve(
    profile: ParsedProfile,
    songs: List[Dict],
    relaxed: bool = False,
    min_evidence: int = 2,
) -> List[Candidate]:
    """
    Return candidates whose evidence list reaches `min_evidence` items
    (or, in relaxed mode, at least one piece of evidence).

    The relaxed pass also accepts genre and mood neighbors so the
    retry path can find SOMETHING when a strict request was too narrow
    for the catalog.
    """
    candidates: List[Candidate] = []
    threshold = 1 if relaxed else min_evidence

    for song in songs:
        evidence = _evidence_for(profile, song, relaxed=relaxed)
        if len(evidence) >= threshold:
            candidates.append(
                Candidate(song=song, evidence=evidence, relaxed=relaxed)
            )

    # Stable order: most evidence first, then closest energy as a
    # tiebreaker. The ranker still does the real scoring later.
    candidates.sort(
        key=lambda c: (
            -len(c.evidence),
            abs(c.song["energy"] - profile.energy),
        )
    )
    return candidates
