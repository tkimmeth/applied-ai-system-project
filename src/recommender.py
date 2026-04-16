"""
Music recommender logic.

Exposes a functional API used by src/main.py:
    load_songs, score_song, recommend_songs

And an OOP API used by tests/test_recommender.py:
    Song, UserProfile, Recommender
"""

import csv
from dataclasses import dataclass
from typing import List, Dict, Tuple


# Scoring weights. Tuning these is the point of Phase 4.
GENRE_POINTS = 2.0
MOOD_POINTS = 1.0
ENERGY_POINTS_MAX = 1.5
ACOUSTIC_BONUS = 0.5
ACOUSTIC_PENALTY = 0.3
ACOUSTIC_THRESHOLD = 0.6


@dataclass
class Song:
    """One song loaded from the CSV."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """A user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def _score_attrs(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    fav_genre: str,
    fav_mood: str,
    target_energy: float,
    likes_acoustic: bool,
) -> Tuple[float, List[str]]:
    """Core scoring. Shared by the OOP and functional paths."""
    score = 0.0
    reasons: List[str] = []

    if genre == fav_genre:
        score += GENRE_POINTS
        reasons.append(f"genre match (+{GENRE_POINTS})")

    if mood == fav_mood:
        score += MOOD_POINTS
        reasons.append(f"mood match (+{MOOD_POINTS})")

    energy_diff = abs(target_energy - energy)
    energy_points = ENERGY_POINTS_MAX * (1 - energy_diff)
    if energy_points < 0:
        # clamp so weird out-of-range inputs don't make a song score negative just from energy
        energy_points = 0.0
    score += energy_points
    reasons.append(f"energy closeness (+{energy_points:.2f})")

    if acousticness >= ACOUSTIC_THRESHOLD:
        if likes_acoustic:
            score += ACOUSTIC_BONUS
            reasons.append(f"acoustic bonus (+{ACOUSTIC_BONUS})")
        else:
            score -= ACOUSTIC_PENALTY
            reasons.append(f"acoustic penalty (-{ACOUSTIC_PENALTY})")

    return score, reasons


def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv into a list of dicts with numeric fields cast to float/int."""
    songs: List[Dict] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id": int(row["id"]),
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": row["mood"],
                "energy": float(row["energy"]),
                "tempo_bpm": float(row["tempo_bpm"]),
                "valence": float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song dict against a user_prefs dict. Returns (score, reasons)."""
    return _score_attrs(
        genre=song["genre"],
        mood=song["mood"],
        energy=song["energy"],
        acousticness=song["acousticness"],
        fav_genre=user_prefs.get("genre", ""),
        fav_mood=user_prefs.get("mood", ""),
        target_energy=user_prefs.get("energy", 0.5),
        likes_acoustic=user_prefs.get("likes_acoustic", False),
    )


def recommend_songs(
    user_prefs: Dict, songs: List[Dict], k: int = 5
) -> List[Tuple[Dict, float, str]]:
    """Score all songs, return top k as (song, score, explanation_string)."""
    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons) if reasons else "no matches"
        scored.append((song, score, explanation))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]


class Recommender:
    """OOP wrapper. Same scoring rules, but takes Song/UserProfile instances."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        return _score_attrs(
            genre=song.genre,
            mood=song.mood,
            energy=song.energy,
            acousticness=song.acousticness,
            fav_genre=user.favorite_genre,
            fav_mood=user.favorite_mood,
            target_energy=user.target_energy,
            likes_acoustic=user.likes_acoustic,
        )

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs for this user, highest score first."""
        scored = [(song, self._score(user, song)[0]) for song in self.songs]
        scored.sort(key=lambda item: item[1], reverse=True)
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Human readable explanation for why this song scored what it did."""
        score, reasons = self._score(user, song)
        if not reasons:
            return "no matches"
        return f"score {score:.2f}: " + ", ".join(reasons)
