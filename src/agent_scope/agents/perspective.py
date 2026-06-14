from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_chat_model
from ..models import Perspective, PerspectiveOutput
from ..prompts import PERSPECTIVE_SYSTEM_PROMPT
from ..state import ResearchState
from ..utils.json_utils import extract_json


FALLBACK_PERSPECTIVES = [
    Perspective(
        name="technical",
        description="Focuses on architecture, implementation, tooling, and engineering tradeoffs.",
        core_questions=[
            "What architecture and implementation choices matter most?",
            "What technical constraints or tradeoffs should be investigated?",
        ],
    ),
    Perspective(
        name="product",
        description="Focuses on user needs, workflows, adoption, and product value.",
        core_questions=[
            "What user problems does this address?",
            "What features would make the solution practically useful?",
        ],
    ),
    Perspective(
        name="market",
        description="Focuses on ecosystem trends, competitors, positioning, and opportunities.",
        core_questions=[
            "What existing alternatives or competitors should be compared?",
            "Where are the practical opportunities or gaps?",
        ],
    ),
    Perspective(
        name="safety",
        description="Focuses on reliability, security, evaluation, and failure modes.",
        core_questions=[
            "What reliability or safety risks need to be controlled?",
            "How should the system be evaluated before being trusted?",
        ],
    ),
    Perspective(
        name="open_source",
        description="Focuses on open-source projects, maintainability, community, and extensibility.",
        core_questions=[
            "Which open-source implementations are worth studying?",
            "How can the project be designed for maintainability and extension?",
        ],
    ),
]


def perspective_node(state: ResearchState) -> ResearchState:
    """Generate STORM-style expert perspectives before planning tasks."""

    question = state["user_question"]
    llm = get_chat_model(temperature=0.2)

    response = llm.invoke(
        [
            SystemMessage(content=PERSPECTIVE_SYSTEM_PROMPT),
            HumanMessage(content=f"User research question:\n{question}"),
        ]
    )

    try:
        data = extract_json(str(response.content))
        output = PerspectiveOutput.model_validate(data)
        perspectives = output.perspectives[:6]
        if not perspectives:
            raise ValueError("Perspective list is empty.")
    except Exception as exc:  # noqa: BLE001 - fallback keeps workflow runnable
        perspectives = FALLBACK_PERSPECTIVES
        logs = state.get("logs", []) + [
            f"Perspective generation failed; fallback perspectives used: {exc}"
        ]
        return {
            "perspectives": [p.model_dump() for p in perspectives],
            "logs": logs,
        }

    logs = state.get("logs", []) + [
        f"Perspective Generator produced {len(perspectives)} perspectives."
    ]
    return {
        "perspectives": [p.model_dump() for p in perspectives],
        "logs": logs,
    }
