from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..llm import get_chat_model
from ..models import PlannerOutput, ResearchTask
from ..prompts import PLANNER_SYSTEM_PROMPT
from ..state import ResearchState
from ..utils.json_utils import extract_json


def planner_node(state: ResearchState) -> ResearchState:
    question = state["user_question"]
    perspectives = state.get("perspectives", [])
    settings = get_settings()
    llm = get_chat_model(temperature=0.1)

    planner_input = {
        "user_question": question,
        "perspectives": perspectives,
    }

    response = llm.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(planner_input, ensure_ascii=False, indent=2)),
        ]
    )

    try:
        data = extract_json(str(response.content))
        plan = PlannerOutput.model_validate(data)
        tasks = plan.tasks[: settings.max_tasks]
        research_goal = plan.research_goal
    except Exception as exc:  # noqa: BLE001 - fallback keeps MVP runnable
        fallback_perspective = "general"
        if perspectives:
            fallback_perspective = str(perspectives[0].get("name", "general"))

        tasks = [
            ResearchTask(
                id="t1",
                question=question,
                perspective=fallback_perspective,
                priority=1,
                search_queries=[question],
            )
        ]
        research_goal = question
        logs = state.get("logs", []) + [f"Planner JSON parsing failed; fallback plan used: {exc}"]
        return {
            "research_goal": research_goal,
            "tasks": [task.model_dump() for task in tasks],
            "logs": logs,
        }

    logs = state.get("logs", []) + [f"Planner produced {len(tasks)} research tasks."]
    return {
        "research_goal": research_goal,
        "tasks": [task.model_dump() for task in tasks],
        "logs": logs,
    }
