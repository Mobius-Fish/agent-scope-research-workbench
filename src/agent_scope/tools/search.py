from __future__ import annotations

import hashlib
from typing import Dict, List

from ..config import get_settings
from ..models import Source


def _source_id(url: str, fallback: str) -> str:
    raw = url or fallback
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:8]
    return f"s_{digest}"


def search_web(query: str, max_results: int | None = None) -> List[Source]:
    """
    Search the web with Tavily.

    If TAVILY_API_KEY is not set, TavilyClient may use keyless mode depending on
    the installed SDK/version and current service limits. If search fails, this
    function returns an empty list instead of crashing the whole graph.
    """

    settings = get_settings()
    max_results = max_results or settings.max_search_results

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else TavilyClient()
        response: Dict = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
            include_raw_content=False,
        )
    except Exception as exc:  # noqa: BLE001 - keep MVP resilient
        return [
            Source(
                id=_source_id("", f"search-error:{query}"),
                title="Search failed",
                url="",
                content=f"Search failed for query {query!r}: {exc}",
                score=0.0,
            )
        ]

    results = response.get("results", []) or []
    sources: List[Source] = []
    for idx, item in enumerate(results):
        url = item.get("url", "") or ""
        title = item.get("title", "Untitled source") or "Untitled source"
        content = item.get("content", "") or item.get("raw_content", "") or ""
        score = item.get("score")
        sources.append(
            Source(
                id=_source_id(url, f"{query}:{idx}"),
                title=title,
                url=url,
                content=content[:3000],
                score=score,
            )
        )

    return sources
