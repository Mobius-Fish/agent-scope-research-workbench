from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_chat_model
from ..prompts import WRITER_SYSTEM_PROMPT
from ..state import ResearchState


def _collect_claims(notes: list[dict]) -> list[dict]:
    claims: list[dict] = []
    for note in notes:
        claims.extend(note.get("claims", []))
    return claims


def writer_node(state: ResearchState) -> ResearchState:
    """Write a draft report. Critic and Reviser will turn it into final_report."""

    llm = get_chat_model(temperature=0.2)
    notes = state.get("notes", [])
    verified_claims = state.get("verified_claims", []) or _collect_claims(notes)

    payload = {
        "user_question": state["user_question"],
        "research_goal": state.get("research_goal", ""),
        "tasks": state.get("tasks", []),
        "notes": notes,
        "verified_claims": verified_claims,
        "verification_issues": state.get("verification_issues", []),
        "needs_more_research": state.get("needs_more_research", False),
        "supervisor_decision": state.get("supervisor_decision", ""),
        "supervisor_reason": state.get("supervisor_reason", ""),
        "sources": state.get("sources", []),
    }

    response = llm.invoke(
        [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )

    draft_report = str(response.content).strip()
    logs = state.get("logs", []) + ["Writer produced draft Markdown report."]
    return {"draft_report": draft_report, "logs": logs}
