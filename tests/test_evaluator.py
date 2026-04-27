"""Tests for src.evaluator."""

from src.profile_parser import ParsedProfile
from src.evaluator import evaluate


def _recs_pop_happy_high_energy():
    """A clean recommendation set that should score well."""
    return [
        ({"title": "A", "artist": "x", "genre": "pop", "mood": "happy",
          "energy": 0.82, "acousticness": 0.18}, 4.5, "..."),
        ({"title": "B", "artist": "x", "genre": "pop", "mood": "energetic",
          "energy": 0.85, "acousticness": 0.10}, 3.5, "..."),
        ({"title": "C", "artist": "x", "genre": "indie pop", "mood": "happy",
          "energy": 0.78, "acousticness": 0.20}, 3.2, "..."),
    ]


def test_confidence_in_unit_interval():
    profile = ParsedProfile(
        genre="pop", mood="happy", energy=0.80, likes_acoustic=False,
    )
    result = evaluate(profile, _recs_pop_happy_high_energy())
    assert 0.0 <= result.confidence <= 1.0


def test_clean_request_passes_guardrails():
    profile = ParsedProfile(
        genre="pop", mood="happy", energy=0.80, likes_acoustic=False,
    )
    result = evaluate(profile, _recs_pop_happy_high_energy())
    assert result.passed_guardrails is True


def test_empty_recs_does_not_pass_guardrails():
    profile = ParsedProfile(genre="pop", mood="happy", energy=0.5)
    result = evaluate(profile, [])
    assert result.passed_guardrails is False
    assert any("only" in w or "missed" in w for w in result.warnings)


def test_metrics_contains_expected_keys():
    profile = ParsedProfile(
        genre="pop", mood="happy", energy=0.80, likes_acoustic=False,
    )
    result = evaluate(profile, _recs_pop_happy_high_energy())
    expected = {
        "genre_ratio", "mood_ratio", "energy_score",
        "acoustic_score", "coverage_score", "n_recommendations",
    }
    assert expected.issubset(result.metrics.keys())
