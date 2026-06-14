from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_chat_model
from ..prompts import REVISER_SYSTEM_PROMPT
from ..state import ResearchState


def reviser_node(state: ResearchState) -> ResearchState:
    """Revise the draft report using the critic's feedback and produce final_report."""

    llm = get_chat_model(temperature=0.1)

    payload = {
        "user_question": state["user_question"],
        "research_goal": state.get("research_goal", ""),
        "draft_report": state.get("draft_report", ""),
        "critique": state.get("critique", ""),
        "tasks": state.get("tasks", []),
        "notes": state.get("notes", []),
        "verified_claims": state.get("verified_claims", []),
        "verification_issues": state.get("verification_issues", []),
        "needs_more_research": state.get("needs_more_research", False),
        "sources": state.get("sources", []),
    }

    response = llm.invoke(
        [
            SystemMessage(content=REVISER_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )

    final_report = str(response.content).strip()
    logs = state.get("logs", []) + ["Reviser produced final Markdown report."]
    return {"final_report": final_report, "logs": logs}
