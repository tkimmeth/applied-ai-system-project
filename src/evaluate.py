"""
evaluate
========

Reliability harness. Runs the agent against a fixed list of test
cases, each with an expected genre/mood/energy bracket, and prints a
pass/fail summary.

A test "passes" when:
    * the parsed profile matches the expected slots
    * the agent does not throw
    * the evaluator's confidence meets the case's expected band
    * any expected warnings appear in the result

Run with:

    python -m src.evaluate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.advisor_agent import AdvisorAgent
from src.recommender import load_songs


# Expected energy is given as a (lo, hi) band rather than a point so
# the parser doesn't have to guess to two decimal places.
@dataclass
class TestCase:
    name: str
    request: str
    expected_genre: Optional[str] = None
    expected_mood: Optional[str] = None
    expected_energy_band: Optional[Tuple[float, float]] = None
    expected_acoustic: Optional[bool] = None
    expect_min_confidence: float = 0.0
    expect_warning_substring: Optional[str] = None
    expect_passes_guardrails: Optional[bool] = None
    notes: str = ""


CASES: List[TestCase] = [
    TestCase(
        name="gym_high_energy",
        request="I need upbeat happy music for the gym",
        expected_mood="happy",
        expected_energy_band=(0.70, 1.0),
        expect_min_confidence=0.40,
        notes="activity sets gym defaults; explicit 'happy' overrides mood; "
              "'upbeat' pins energy ~0.75",
    ),
    TestCase(
        name="coding_acoustic_focus",
        request="Give me calm focused music for coding, preferably acoustic",
        expected_genre="lofi",
        expected_mood="focused",
        expected_energy_band=(0.20, 0.45),
        expected_acoustic=True,
        expect_min_confidence=0.55,
        expect_passes_guardrails=True,
        notes="textbook well-supported request — should be the highest confidence",
    ),
    TestCase(
        name="sad_acoustic_low_energy",
        request="I'm feeling lonely, give me sad acoustic music",
        expected_mood="sad",
        expected_acoustic=True,
        expected_energy_band=(0.0, 0.5),
        expect_min_confidence=0.40,
        notes="catalog has only one sad song; mood default should pull "
              "energy down even without an explicit phrase",
    ),
    TestCase(
        name="contradictory_sad_high_energy",
        request="I want sad acoustic music but still high energy",
        expected_mood="sad",
        expected_acoustic=True,
        expected_energy_band=(0.7, 1.0),
        expect_warning_substring="low-arousal",
        notes="adversarial: parser must flag the contradiction",
    ),
    TestCase(
        name="empty_request",
        request="",
        expect_warning_substring="empty",
        notes="empty input must not crash",
    ),
    TestCase(
        name="rock_intense_workout",
        request="give me intense rock for an aggressive workout",
        expected_genre="rock",
        expected_mood="intense",
        expected_energy_band=(0.7, 1.0),
        expect_min_confidence=0.45,
    ),
    TestCase(
        name="jazz_coffee_shop",
        request="relaxed jazz, coffee shop vibe",
        expected_genre="jazz",
        expected_mood="relaxed",
        expected_energy_band=(0.20, 0.55),
        expect_min_confidence=0.50,
    ),
]


@dataclass
class CaseResult:
    name: str
    passed: bool
    failures: List[str] = field(default_factory=list)
    confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


def _run_one(agent: AdvisorAgent, case: TestCase) -> CaseResult:
    failures: List[str] = []
    try:
        result = agent.advise(case.request).to_dict()
    except Exception as e:  # pragma: no cover — meant to surface in the harness
        return CaseResult(
            name=case.name, passed=False,
            failures=[f"agent raised: {type(e).__name__}: {e}"],
        )

    profile = result["parsed_profile"]
    confidence = result["evaluation"]["confidence"]
    warnings = result["warnings"]

    if case.expected_genre is not None and profile["genre"] != case.expected_genre:
        failures.append(
            f"genre: expected '{case.expected_genre}', got '{profile['genre']}'"
        )
    if case.expected_mood is not None and profile["mood"] != case.expected_mood:
        failures.append(
            f"mood: expected '{case.expected_mood}', got '{profile['mood']}'"
        )
    if case.expected_energy_band is not None:
        lo, hi = case.expected_energy_band
        if not (lo <= profile["energy"] <= hi):
            failures.append(
                f"energy: expected band [{lo}, {hi}], got {profile['energy']:.2f}"
            )
    if case.expected_acoustic is not None and profile["likes_acoustic"] != case.expected_acoustic:
        failures.append(
            f"acoustic: expected {case.expected_acoustic}, got {profile['likes_acoustic']}"
        )
    if confidence < case.expect_min_confidence:
        failures.append(
            f"confidence: expected ≥ {case.expect_min_confidence}, got {confidence}"
        )
    if case.expect_passes_guardrails is True and not result["evaluation"]["passed_guardrails"]:
        failures.append("expected to pass guardrails but did not")
    if case.expect_warning_substring is not None:
        if not any(case.expect_warning_substring in w for w in warnings):
            failures.append(
                f"expected a warning containing '{case.expect_warning_substring}'; "
                f"got {warnings!r}"
            )

    return CaseResult(
        name=case.name,
        passed=not failures,
        failures=failures,
        confidence=confidence,
        warnings=warnings,
    )


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = AdvisorAgent(songs)
    print(f"Loaded {len(songs)} songs from catalog")
    print(f"Running {len(CASES)} reliability cases\n")

    results: List[CaseResult] = []
    for case in CASES:
        outcome = _run_one(agent, case)
        results.append(outcome)
        marker = "PASS" if outcome.passed else "FAIL"
        print(f"  [{marker}] {case.name}  (confidence={outcome.confidence:.2f})")
        for f in outcome.failures:
            print(f"        - {f}")

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0

    print()
    print("=" * 56)
    print(f"  Total cases     : {len(results)}")
    print(f"  Passed          : {passed}")
    print(f"  Failed          : {failed}")
    print(f"  Average conf.   : {avg_conf:.3f}")
    print("=" * 56)

    if failed:
        print("\nNotes about failures:")
        for r in results:
            if not r.passed:
                print(f"  {r.name}: {'; '.join(r.failures)}")


if __name__ == "__main__":
    main()
