from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class ResearchState(TypedDict, total=False):
    """
    Shared LangGraph state.

    Each node returns a partial dict update. Lists are overwritten by each node
    intentionally; later versions can add reducers if parallelism is added.
    """

    user_question: str
    research_goal: str
    perspectives: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    sources: List[Dict[str, Any]]
    notes: List[Dict[str, Any]]
    verified_claims: List[Dict[str, Any]]
    verification_issues: List[Dict[str, Any]]
    needs_more_research: bool
    research_round: int
    max_research_rounds: int
    supervisor_decision: str
    supervisor_reason: str
    draft_report: str
    critique: str
    final_report: str
    logs: List[str]
