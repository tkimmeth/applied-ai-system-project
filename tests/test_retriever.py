"""Tests for src.retriever."""

from src.profile_parser import ParsedProfile
from src.retriever import retrieve, ENERGY_TOL


def _catalog():
    return [
        {"id": 1, "title": "Pop A", "artist": "X", "genre": "pop", "mood": "happy",
         "energy": 0.85, "tempo_bpm": 120, "valence": 0.8, "danceability": 0.8,
         "acousticness": 0.10},
        {"id": 2, "title": "Lofi A", "artist": "Y", "genre": "lofi", "mood": "focused",
         "energy": 0.40, "tempo_bpm": 80, "valence": 0.5, "danceability": 0.5,
         "acousticness": 0.85},
        {"id": 3, "title": "Folk Sad", "artist": "Z", "genre": "folk", "mood": "sad",
         "energy": 0.20, "tempo_bpm": 70, "valence": 0.3, "danceability": 0.3,
         "acousticness": 0.90},
        {"id": 4, "title": "Rock Far", "artist": "W", "genre": "rock", "mood": "intense",
         "energy": 0.95, "tempo_bpm": 150, "valence": 0.5, "danceability": 0.5,
         "acousticness": 0.05},
    ]


def test_strict_retrieval_finds_an_obvious_match():
    profile = ParsedProfile(
        genre="lofi", mood="focused", energy=0.40, likes_acoustic=True,
    )
    cands = retrieve(profile, _catalog(), relaxed=False)
    titles = [c.song["title"] for c in cands]
    assert "Lofi A" in titles
    # the exact match should sort first
    assert cands[0].song["title"] == "Lofi A"


def test_relaxed_retrieval_returns_more_than_strict_for_sparse_request():
    profile = ParsedProfile(
        genre="metal", mood="intense", energy=0.95, likes_acoustic=False,
    )
    strict = retrieve(profile, _catalog(), relaxed=False)
    relaxed = retrieve(profile, _catalog(), relaxed=True)
    assert len(relaxed) >= len(strict)


def test_evidence_list_is_populated():
    profile = ParsedProfile(
        genre="lofi", mood="focused", energy=0.40, likes_acoustic=True,
    )
    cands = retrieve(profile, _catalog(), relaxed=False)
    assert cands, "expected at least one candidate"
    assert all(len(c.evidence) >= 1 for c in cands)
