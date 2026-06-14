from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_chat_model
from ..prompts import CRITIC_SYSTEM_PROMPT
from ..state import ResearchState


def critic_node(state: ResearchState) -> ResearchState:
    """Critique the draft report before final revision."""

    llm = get_chat_model(temperature=0.1)

    payload = {
        "user_question": state["user_question"],
        "research_goal": state.get("research_goal", ""),
        "tasks": state.get("tasks", []),
        "notes": state.get("notes", []),
        "verified_claims": state.get("verified_claims", []),
        "verification_issues": state.get("verification_issues", []),
        "needs_more_research": state.get("needs_more_research", False),
        "supervisor_decision": state.get("supervisor_decision", ""),
        "supervisor_reason": state.get("supervisor_reason", ""),
        "sources": state.get("sources", []),
        "draft_report": state.get("draft_report", ""),
    }

    response = llm.invoke(
        [
            SystemMessage(content=CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, indent=2)),
        ]
    )

    critique = str(response.content).strip()
    logs = state.get("logs", []) + ["Critic reviewed draft report and produced critique."]
    return {"critique": critique, "logs": logs}
