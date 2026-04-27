"""Tests for src.profile_parser."""

from src.profile_parser import parse_request


def test_coding_request_pulls_focused_lofi_acoustic():
    p = parse_request(
        "Give me calm focused music for coding, preferably acoustic"
    )
    assert p.genre == "lofi"
    assert p.mood == "focused"
    assert p.likes_acoustic is True
    # energy should be in the calm/focus band
    assert 0.20 <= p.energy <= 0.45


def test_gym_activity_sets_high_energy():
    p = parse_request("hype me up for the gym")
    assert p.energy >= 0.75
    # gym activity hint maps to energetic mood unless overridden
    assert p.mood in ("energetic", "happy")


def test_contradictory_sad_high_energy_warns():
    p = parse_request("I want sad acoustic music but still high energy")
    assert p.mood == "sad"
    assert p.likes_acoustic is True
    assert p.energy >= 0.7
    assert any("low-arousal" in w for w in p.warnings)


def test_acoustic_and_electronic_conflict_warns():
    p = parse_request("acoustic guitar but also synth electronic vibe")
    assert any("acoustic" in w and "electronic" in w for w in p.warnings)


def test_empty_request_does_not_crash():
    p = parse_request("")
    assert p.raw_request == ""
    assert any("empty" in w for w in p.warnings)


def test_no_recognised_terms_falls_back_with_warning():
    p = parse_request("flugelschmecker biscuits in space")
    assert any("no clear" in w for w in p.warnings)
    # default profile should still be valid
    assert 0.0 <= p.energy <= 1.0


def test_to_user_prefs_matches_recommender_shape():
    p = parse_request("upbeat happy pop please")
    prefs = p.to_user_prefs()
    assert set(prefs.keys()) == {"genre", "mood", "energy", "likes_acoustic"}
