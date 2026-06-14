from __future__ import annotations

import re
from typing import Any


REQUIRED_FINAL_REPORT_SECTIONS = [
    "executive summary",
    "research goal",
    "supported conclusions",
    "evidence by perspective",
    "weak evidence",
    "recommended implementation plan",
    "what to verify next",
    "sources",
]


_SOURCE_CITATION_RE = re.compile(r"\[s[^\]]+\]", re.IGNORECASE)


def collect_claims(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect claims from verified_claims, falling back to notes.claims."""

    verified_claims = result.get("verified_claims") or []
    if verified_claims:
        return list(verified_claims)

    claims: list[dict[str, Any]] = []
    for note in result.get("notes", []) or []:
        claims.extend(note.get("claims", []) or [])
    return claims


def _status_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"supported": 0, "weak": 0, "unsupported": 0, "unverified": 0}
    for claim in claims:
        status = claim.get("verification_status") or "unverified"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _section_coverage(markdown: str) -> tuple[float, list[str]]:
    lower = markdown.lower()
    present = [section for section in REQUIRED_FINAL_REPORT_SECTIONS if section in lower]
    return _safe_ratio(len(present), len(REQUIRED_FINAL_REPORT_SECTIONS)), present


def score_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    Produce deterministic, cheap, repeatable metrics for one agent run.

    These scores do not judge factual correctness directly. They measure the
    observable properties your workflow is designed to produce: sources, claims,
    verification, revision artifacts, and report structure.
    """

    sources = result.get("sources", []) or []
    notes = result.get("notes", []) or []
    tasks = result.get("tasks", []) or []
    perspectives = result.get("perspectives", []) or []
    issues = result.get("verification_issues", []) or []
    claims = collect_claims(result)
    counts = _status_counts(claims)

    final_report = result.get("final_report", "") or ""
    draft_report = result.get("draft_report", "") or ""
    critique = result.get("critique", "") or ""
    logs = result.get("logs", []) or []

    claims_with_sources = [claim for claim in claims if claim.get("source_ids")]
    section_coverage, present_sections = _section_coverage(final_report)
    citation_count = len(_SOURCE_CITATION_RE.findall(final_report))
    researcher_iterations = sum(1 for line in logs if "Researcher produced" in line)
    supervisor_researcher_routes = sum(
        1 for line in logs if "Supervisor decision: next=researcher" in line
    )

    has_final_report = bool(final_report.strip())
    has_revision_loop = bool(draft_report.strip()) and bool(critique.strip()) and has_final_report

    metrics: dict[str, Any] = {
        "perspective_count": len(perspectives),
        "task_count": len(tasks),
        "note_count": len(notes),
        "source_count": len(sources),
        "claim_count": len(claims),
        "supported_claim_count": counts.get("supported", 0),
        "weak_claim_count": counts.get("weak", 0),
        "unsupported_claim_count": counts.get("unsupported", 0),
        "unverified_claim_count": counts.get("unverified", 0),
        "claims_with_sources_count": len(claims_with_sources),
        "verification_issue_count": len(issues),
        "supported_claim_ratio": _safe_ratio(counts.get("supported", 0), len(claims)),
        "claims_with_sources_ratio": _safe_ratio(len(claims_with_sources), len(claims)),
        "section_coverage": section_coverage,
        "present_sections": present_sections,
        "source_citation_count_in_report": citation_count,
        "final_report_length": len(final_report),
        "draft_report_length": len(draft_report),
        "critique_length": len(critique),
        "has_final_report": has_final_report,
        "has_revision_loop": has_revision_loop,
        "needs_more_research": bool(result.get("needs_more_research", False)),
        "research_round": result.get("research_round"),
        "max_research_rounds": result.get("max_research_rounds"),
        "researcher_iterations": researcher_iterations,
        "supervisor_researcher_routes": supervisor_researcher_routes,
    }

    metrics["overall_score"] = compute_overall_score(metrics)
    metrics["grade"] = grade_score(metrics["overall_score"])
    return metrics


def compute_overall_score(metrics: dict[str, Any]) -> float:
    """Weighted score in [0, 100] for quick regression comparison."""

    score = 0.0

    # Workflow completeness: 20
    score += 5 if metrics["perspective_count"] >= 4 else metrics["perspective_count"] * 1.25
    score += 5 if metrics["task_count"] >= 3 else metrics["task_count"] * 1.67
    score += 5 if metrics["has_final_report"] else 0
    score += 5 if metrics["has_revision_loop"] else 0

    # Evidence and verification: 45
    score += min(metrics["source_count"], 10) / 10 * 10
    score += min(metrics["claim_count"], 12) / 12 * 10
    score += metrics["claims_with_sources_ratio"] * 10
    score += metrics["supported_claim_ratio"] * 10
    unsupported_penalty = min(metrics["unsupported_claim_count"], 5) / 5 * 5
    score += max(0, 5 - unsupported_penalty)

    # Report structure and citation usage: 25
    score += metrics["section_coverage"] * 10
    score += min(metrics["source_citation_count_in_report"], 8) / 8 * 8
    score += min(metrics["final_report_length"], 5000) / 5000 * 7

    # Control-loop behavior: 10
    score += 5 if metrics["researcher_iterations"] >= 1 else 0
    score += 5 if metrics["research_round"] is not None else 0

    return round(min(score, 100.0), 2)


def grade_score(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"
