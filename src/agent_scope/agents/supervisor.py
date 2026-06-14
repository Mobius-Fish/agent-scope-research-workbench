from __future__ import annotations

from typing import Literal

from ..state import ResearchState


DEFAULT_MAX_RESEARCH_ROUNDS = 2


def supervisor_node(state: ResearchState) -> ResearchState:
    """
    Decide whether the graph should run another research round or proceed to writing.

    This first supervisor is deterministic: it reads the Verifier's quality signal
    instead of asking an LLM to make an opaque routing decision.
    """

    current_round = int(state.get("research_round", 1))
    max_rounds = int(state.get("max_research_rounds", DEFAULT_MAX_RESEARCH_ROUNDS))
    needs_more_research = bool(state.get("needs_more_research", False))

    issue_count = len(state.get("verification_issues", []))
    verified_claim_count = len(state.get("verified_claims", []))

    if needs_more_research and current_round < max_rounds:
        decision = "researcher"
        next_round = current_round + 1
        reason = (
            "Verifier signaled that more research is needed "
            f"and the workflow has remaining budget ({current_round}/{max_rounds})."
        )
    else:
        decision = "writer"
        next_round = current_round
        if needs_more_research:
            reason = (
                "Verifier still found evidence issues, but the workflow reached "
                f"the maximum research rounds ({current_round}/{max_rounds})."
            )
        else:
            reason = "Verifier quality signal is good enough to proceed to writing."

    logs = state.get("logs", []) + [
        "Supervisor decision: "
        f"next={decision}, round={next_round}/{max_rounds}, "
        f"verified_claims={verified_claim_count}, issues={issue_count}. "
        f"Reason: {reason}"
    ]

    return {
        "supervisor_decision": decision,
        "supervisor_reason": reason,
        "research_round": next_round,
        "max_research_rounds": max_rounds,
        "logs": logs,
    }


def route_after_supervisor(state: ResearchState) -> Literal["researcher", "writer"]:
    """Route to the next node based on the supervisor's decision."""

    if state.get("supervisor_decision") == "researcher":
        return "researcher"
    return "writer"
