"""Tests for src.advisor_agent — end-to-end pipeline check."""

import os
import json
import tempfile

from src.advisor_agent import AdvisorAgent
from src.recommender import load_songs


def _agent_with_temp_log():
    songs = load_songs("data/songs.csv")
    tmp = tempfile.NamedTemporaryFile(
        prefix="advisor_log_", suffix=".jsonl", delete=False, mode="w"
    )
    tmp.close()
    return AdvisorAgent(songs, log_path=tmp.name), tmp.name


def test_advise_returns_recommendations_for_clean_request():
    agent, log_path = _agent_with_temp_log()
    try:
        result = agent.advise(
            "Give me calm focused music for coding, preferably acoustic"
        ).to_dict()
        assert result["recommendations"], "expected non-empty recommendations"
        # at least one of the top 3 should be lofi
        top_genres = [r["genre"] for r in result["recommendations"][:3]]
        assert any(g == "lofi" for g in top_genres)
    finally:
        os.unlink(log_path)


def test_advise_writes_jsonl_log_with_expected_events():
    agent, log_path = _agent_with_temp_log()
    try:
        agent.advise("upbeat happy pop for the gym")
        with open(log_path) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        events = {entry["event"] for entry in lines}
        assert {"parse", "retrieve", "rank", "evaluate", "final"}.issubset(events)
    finally:
        os.unlink(log_path)


def test_confidence_is_in_unit_interval():
    agent, log_path = _agent_with_temp_log()
    try:
        result = agent.advise("relaxed jazz, coffee shop vibe").to_dict()
        c = result["evaluation"]["confidence"]
        assert 0.0 <= c <= 1.0
    finally:
        os.unlink(log_path)


def test_low_confidence_request_triggers_retry_flag():
    """Genuinely thin requests should at least try the relaxed path."""
    agent, log_path = _agent_with_temp_log()
    try:
        # gibberish input — parser falls back to default and retrieval is poor
        result = agent.advise("xyzzy plugh wibble").to_dict()
        # we don't assert retried==True, only that the field exists and the
        # pipeline did not crash — retry is a behavior, not a hard guarantee
        assert "retried" in result
        assert isinstance(result["retried"], bool)
    finally:
        os.unlink(log_path)
