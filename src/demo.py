"""
demo
====

End-to-end walk-through of VibeFinder. Three free-form requests, one
per "shape" of input the system is meant to handle:

    1. clean / well-supported request
    2. focused / acoustic request (multi-feature)
    3. adversarial / contradictory request

Run with:

    python -m src.demo
"""

from __future__ import annotations

from src.advisor_agent import AdvisorAgent
from src.recommender import load_songs


REQUESTS = [
    "I need upbeat happy music for the gym",
    "Give me calm focused music for coding, preferably acoustic",
    "I want sad acoustic music but still high energy",
]


def _hr(char: str = "─", width: int = 72) -> str:
    return char * width


def _print_result(result_dict: dict) -> None:
    profile = result_dict["parsed_profile"]
    print(f"REQUEST  : {result_dict['request']}")
    print(f"RUN ID   : {result_dict['run_id']}  (retried={result_dict['retried']})")
    print()
    print("PARSED PROFILE")
    print(f"  genre={profile['genre']}  mood={profile['mood']}  "
          f"energy={profile['energy']:.2f}  acoustic={profile['likes_acoustic']}")
    if profile.get("matched_terms"):
        print(f"  matched_terms: {profile['matched_terms']}")
    print()

    print("AGENT STEPS")
    for step in result_dict["agent_steps"]:
        print(f"  [{step['name']:<8}] {step['detail']}  ({step['elapsed_ms']} ms)")
    print()

    print("TOP RECOMMENDATIONS")
    if not result_dict["recommendations"]:
        print("  (none)")
    for r in result_dict["recommendations"]:
        print(f"  {r['title']} — {r['artist']}")
        print(f"    score {r['score']}  | {r['genre']} / {r['mood']} / "
              f"energy {r['energy']:.2f} / acousticness {r['acousticness']:.2f}")
        print(f"    why : {r['why']}")
    print()

    ev = result_dict["evaluation"]
    print("EVALUATION")
    print(f"  confidence       : {ev['confidence']}")
    print(f"  passed_guardrails: {ev['passed_guardrails']}")
    print(f"  explanation      : {ev['explanation']}")
    print(f"  metrics          : {ev['metrics']}")
    print()

    if result_dict["warnings"]:
        print("WARNINGS")
        for w in result_dict["warnings"]:
            print(f"  - {w}")
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")
    agent = AdvisorAgent(songs)
    print(f"Loaded {len(songs)} songs from catalog")
    print(_hr("="))

    for i, req in enumerate(REQUESTS, start=1):
        print(f"\n=== EXAMPLE {i} / {len(REQUESTS)} ===\n")
        result = agent.advise(req)
        _print_result(result.to_dict())
        print(_hr())


if __name__ == "__main__":
    main()
