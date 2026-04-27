"""
advisor_agent
=============

The agentic loop that ties parser → retriever → ranker → evaluator
together. This is what makes the project an applied AI *system*
instead of just a scoring function.

The "agent" here is small and explicit on purpose. It runs a fixed
sequence of steps, records each step as a JSONL event, and decides
based on the evaluator's confidence whether to retry once with a
relaxed retrieval pass. There is no chain-of-thought LLM and no
external tool use — the deliberation is the control flow.

Public API:
    AdvisorAgent(songs, log_path=...).advise(text) -> dict
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.profile_parser import ParsedProfile, parse_request
from src.retriever import Candidate, retrieve
from src.evaluator import EvaluationResult, evaluate, CONFIDENCE_PASS
from src.recommender import score_song


DEFAULT_LOG_PATH = "logs/run_log.jsonl"
DEFAULT_K = 5


@dataclass
class AgentStep:
    """One observable step in the agent loop."""
    name: str
    detail: str
    elapsed_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {"name": self.name, "detail": self.detail, "elapsed_ms": round(self.elapsed_ms, 2)}


@dataclass
class AdvisorResult:
    request: str
    parsed_profile: Dict
    agent_steps: List[Dict]
    retrieval_evidence: List[Dict]
    recommendations: List[Dict]
    evaluation: Dict
    warnings: List[str]
    log_path: str
    run_id: str
    retried: bool = False

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "parsed_profile": self.parsed_profile,
            "agent_steps": self.agent_steps,
            "retrieval_evidence": self.retrieval_evidence,
            "recommendations": self.recommendations,
            "evaluation": self.evaluation,
            "warnings": self.warnings,
            "retried": self.retried,
            "log_path": self.log_path,
        }


def _rank_candidates(
    profile: ParsedProfile, candidates: List[Candidate], k: int
) -> List[Tuple[Dict, float, str]]:
    """Score every candidate with the original recommender weights and take top k."""
    user_prefs = profile.to_user_prefs()
    scored: List[Tuple[Dict, float, str]] = []
    for cand in candidates:
        score, reasons = score_song(user_prefs, cand.song)
        explanation = ", ".join(reasons) if reasons else "no matches"
        scored.append((cand.song, score, explanation))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]


class AdvisorAgent:
    """
    Run the full advise pipeline for one user request.

    Caller provides a list-of-dicts song catalog (matching the shape
    `recommender.load_songs` returns). The agent owns parsing,
    retrieval, ranking, evaluation, the retry decision, and logging.
    """

    def __init__(
        self,
        songs: List[Dict],
        log_path: str = DEFAULT_LOG_PATH,
        confidence_threshold: float = CONFIDENCE_PASS,
        k: int = DEFAULT_K,
    ):
        self.songs = songs
        self.log_path = log_path
        self.confidence_threshold = confidence_threshold
        self.k = k

    # --- logging ---------------------------------------------------------

    def _log(self, run_id: str, event: str, payload: Dict) -> None:
        """Append one JSONL line. Errors are swallowed so logging never
        breaks the user-facing flow."""
        try:
            os.makedirs(os.path.dirname(self.log_path) or ".", exist_ok=True)
            record = {
                "ts": time.time(),
                "run_id": run_id,
                "event": event,
                "payload": payload,
            }
            with open(self.log_path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError as e:
            # Don't crash the pipeline if logging fails — just note it on stderr.
            import sys
            print(f"[advisor_agent] logging failed: {e}", file=sys.stderr)

    # --- pipeline --------------------------------------------------------

    def advise(self, text: str) -> AdvisorResult:
        run_id = uuid.uuid4().hex[:8]
        steps: List[AgentStep] = []

        # Step 1: parse
        t0 = time.perf_counter()
        profile = parse_request(text)
        steps.append(AgentStep(
            "parse",
            f"genre={profile.genre} mood={profile.mood} "
            f"energy={profile.energy:.2f} acoustic={profile.likes_acoustic} "
            f"warnings={len(profile.warnings)}",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))
        self._log(run_id, "parse", profile.to_dict())

        # Step 2: retrieve (strict)
        t0 = time.perf_counter()
        candidates = retrieve(profile, self.songs, relaxed=False)
        steps.append(AgentStep(
            "retrieve",
            f"strict pass kept {len(candidates)} candidates",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))
        self._log(run_id, "retrieve", {
            "mode": "strict",
            "n_candidates": len(candidates),
            "candidates": [c.to_dict() for c in candidates[:10]],
        })

        # Step 3: rank
        t0 = time.perf_counter()
        recs = _rank_candidates(profile, candidates, k=self.k) if candidates else []
        steps.append(AgentStep(
            "rank",
            f"ranked {len(recs)} recommendations",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))
        self._log(run_id, "rank", {
            "recommendations": [
                {"title": s["title"], "artist": s["artist"], "score": round(score, 3),
                 "why": why}
                for s, score, why in recs
            ]
        })

        # Step 4: evaluate
        t0 = time.perf_counter()
        ev: EvaluationResult = evaluate(profile, recs)
        steps.append(AgentStep(
            "evaluate",
            f"confidence={ev.confidence:.2f} passed={ev.passed_guardrails}",
            elapsed_ms=(time.perf_counter() - t0) * 1000,
        ))
        self._log(run_id, "evaluate", ev.to_dict())

        # Step 5: retry once with relaxed retrieval if confidence is low
        retried = False
        relaxed_candidates: List[Candidate] = []
        if ev.confidence < self.confidence_threshold or len(recs) < 3:
            retried = True
            t0 = time.perf_counter()
            relaxed_candidates = retrieve(profile, self.songs, relaxed=True)
            new_recs = _rank_candidates(profile, relaxed_candidates, k=self.k)
            new_ev = evaluate(profile, new_recs)
            steps.append(AgentStep(
                "retry",
                f"relaxed pass kept {len(relaxed_candidates)} candidates, "
                f"new confidence={new_ev.confidence:.2f}",
                elapsed_ms=(time.perf_counter() - t0) * 1000,
            ))
            self._log(run_id, "retry", {
                "mode": "relaxed",
                "n_candidates": len(relaxed_candidates),
                "evaluation": new_ev.to_dict(),
            })
            # Only adopt the retry if it actually improved confidence.
            if new_ev.confidence > ev.confidence:
                candidates = relaxed_candidates
                recs = new_recs
                ev = new_ev
            else:
                ev.warnings.append(
                    "relaxed retry did not improve confidence — keeping strict result"
                )

        # Step 6: assemble final response
        result = AdvisorResult(
            run_id=run_id,
            request=text,
            parsed_profile=profile.to_dict(),
            agent_steps=[s.to_dict() for s in steps],
            retrieval_evidence=[c.to_dict() for c in candidates],
            recommendations=[
                {
                    "title": s["title"], "artist": s["artist"],
                    "genre": s["genre"], "mood": s["mood"],
                    "energy": s["energy"], "acousticness": s["acousticness"],
                    "score": round(score, 3), "why": why,
                }
                for s, score, why in recs
            ],
            evaluation=ev.to_dict(),
            warnings=list(ev.warnings),
            retried=retried,
            log_path=self.log_path,
        )
        self._log(run_id, "final", result.to_dict())
        return result
