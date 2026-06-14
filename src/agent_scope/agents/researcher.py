from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..llm import get_chat_model
from ..models import Claim, ResearchNote, ResearcherOutput, ResearchTask, Source
from ..prompts import RESEARCHER_SYSTEM_PROMPT
from ..state import ResearchState
from ..tools.search import search_web
from ..utils.json_utils import extract_json


def _dedupe_sources(sources: List[Source]) -> List[Source]:
    seen: Dict[str, Source] = {}
    for source in sources:
        key = source.url or source.id
        if key and key not in seen:
            seen[key] = source
    return list(seen.values())


def _format_sources_for_prompt(sources: List[Source]) -> str:
    if not sources:
        return "No sources were retrieved."

    chunks = []
    for source in sources:
        chunks.append(
            f"SOURCE_ID: {source.id}\n"
            f"TITLE: {source.title}\n"
            f"URL: {source.url}\n"
            f"SNIPPET:\n{source.content}\n"
        )
    return "\n---\n".join(chunks)


def _normalize_researcher_json(data: Any) -> Any:
    """Make the researcher parser tolerant during the findings -> claims migration."""

    if not isinstance(data, dict):
        return data

    if "claims" not in data and "findings" in data:
        data["claims"] = data.pop("findings")

    normalized_claims = []
    for raw in data.get("claims", []) or []:
        if isinstance(raw, dict):
            if "text" not in raw and "claim" in raw:
                raw["text"] = raw.pop("claim")
            normalized_claims.append(raw)

    data["claims"] = normalized_claims
    return data


def _attach_claim_metadata(
    result: ResearcherOutput,
    task: ResearchTask,
    task_sources: List[Source],
) -> List[Claim]:
    """Turn LLM claim drafts into stable system-level Claim objects."""

    valid_source_ids = {source.id for source in task_sources}
    claims: List[Claim] = []

    for idx, draft in enumerate(result.claims, start=1):
        source_ids = [sid for sid in draft.source_ids if sid in valid_source_ids]
        claims.append(
            Claim(
                id=f"c_{task.id}_{idx}",
                text=draft.text,
                task_id=task.id,
                perspective=task.perspective,
                source_ids=source_ids,
                confidence=draft.confidence,
            )
        )

    return claims


def researcher_node(state: ResearchState) -> ResearchState:
    settings = get_settings()
    llm = get_chat_model(temperature=0.2)

    all_sources: List[Source] = []
    notes: List[ResearchNote] = []

    for task_raw in state.get("tasks", []):
        task = ResearchTask.model_validate(task_raw)
        task_sources: List[Source] = []

        queries = task.search_queries or [task.question]
        for query in queries[:3]:
            results = search_web(query, max_results=settings.max_search_results)
            for source in results:
                source.search_query = query
                source.task_id = task.id
            task_sources.extend(results)

        task_sources = _dedupe_sources(task_sources)[: settings.max_search_results * 2]
        all_sources.extend(task_sources)

        prompt = f"""
Research goal:
{state.get("research_goal", state["user_question"])}

Task:
- id: {task.id}
- perspective: {task.perspective}
- question: {task.question}

Sources:
{_format_sources_for_prompt(task_sources)}
""".strip()

        response = llm.invoke(
            [
                SystemMessage(content=RESEARCHER_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        try:
            data = _normalize_researcher_json(extract_json(str(response.content)))
            result = ResearcherOutput.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            result = ResearcherOutput(
                summary="The researcher could not produce valid structured notes for this task.",
                claims=[],
                limitations=[f"Researcher JSON parsing failed: {exc}"],
            )

        claims = _attach_claim_metadata(result, task, task_sources)

        notes.append(
            ResearchNote(
                task_id=task.id,
                perspective=task.perspective,
                question=task.question,
                summary=result.summary,
                claims=claims,
                limitations=result.limitations,
            )
        )

    all_sources = _dedupe_sources(all_sources)
    total_claims = sum(len(note.claims) for note in notes)
    logs = state.get("logs", []) + [
        f"Researcher produced {len(notes)} notes, {total_claims} claims, and collected {len(all_sources)} unique sources."
    ]

    return {
        "sources": [source.model_dump() for source in all_sources],
        "notes": [note.model_dump() for note in notes],
        "logs": logs,
    }
