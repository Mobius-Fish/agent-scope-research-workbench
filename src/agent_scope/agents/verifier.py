from __future__ import annotations

from typing import Dict, List, Tuple

from ..models import Claim, ResearchNote, Source, VerificationIssue
from ..state import ResearchState

LOW_CONFIDENCE_THRESHOLD = 0.4
MAX_WEAK_OR_UNSUPPORTED_CLAIMS = 2


def _is_failed_source(source: Source) -> bool:
    """Return True when a retrieved source is not usable evidence."""

    return (
        not source.url.strip()
        or source.title.strip().lower() == "search failed"
        or source.content.strip().lower().startswith("search failed")
    )


def _verify_claim(claim: Claim, source_map: Dict[str, Source]) -> Tuple[Claim, List[VerificationIssue]]:
    """Verify one claim with deterministic source-grounding checks."""

    issues: List[VerificationIssue] = []

    if not claim.text.strip():
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="error",
                reason="Claim text is empty.",
                suggested_fix="Regenerate this claim from the task sources.",
            )
        )

    if not claim.source_ids:
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="error",
                reason="Claim has no source_ids.",
                suggested_fix="Add at least one source id or remove this claim from the report.",
            )
        )

    missing_source_ids = [sid for sid in claim.source_ids if sid not in source_map]
    if missing_source_ids:
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="error",
                reason=f"Claim references missing sources: {missing_source_ids}.",
                suggested_fix="Only cite source ids that exist in the global sources list.",
            )
        )

    failed_source_ids = [
        sid
        for sid in claim.source_ids
        if sid in source_map and _is_failed_source(source_map[sid])
    ]
    if failed_source_ids:
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="error",
                reason=f"Claim cites failed or unusable sources: {failed_source_ids}.",
                suggested_fix="Run another search or remove the failed source ids.",
            )
        )

    empty_content_source_ids = [
        sid
        for sid in claim.source_ids
        if sid in source_map
        and not _is_failed_source(source_map[sid])
        and not source_map[sid].content.strip()
    ]
    if empty_content_source_ids:
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="warning",
                reason=f"Claim cites sources with empty snippets: {empty_content_source_ids}.",
                suggested_fix="Fetch richer page content or treat this claim as lower confidence.",
            )
        )

    if claim.confidence < LOW_CONFIDENCE_THRESHOLD:
        issues.append(
            VerificationIssue(
                claim_id=claim.id,
                severity="warning",
                reason=f"Claim confidence {claim.confidence:.2f} is below {LOW_CONFIDENCE_THRESHOLD:.2f}.",
                suggested_fix="Gather stronger evidence or soften the claim wording.",
            )
        )

    blocking_issues = [issue for issue in issues if issue.severity == "error"]
    if not issues:
        claim.verification_status = "supported"
        claim.verification_reason = "Claim has valid source ids and no deterministic verification issues."
    elif blocking_issues:
        if not claim.source_ids or len(failed_source_ids) + len(missing_source_ids) >= len(claim.source_ids):
            claim.verification_status = "unsupported"
        else:
            claim.verification_status = "weak"
        claim.verification_reason = " ".join(issue.reason for issue in issues)
    else:
        claim.verification_status = "weak"
        claim.verification_reason = " ".join(issue.reason for issue in issues)

    return claim, issues


def verifier_node(state: ResearchState) -> ResearchState:
    """
    Verify source-grounding for all claims.

    This first version is intentionally deterministic. It checks whether each
    claim has valid source ids, whether those source ids exist, whether sources
    look usable, and whether confidence is too low. A later version can add an
    LLM-based semantic entailment check.
    """

    sources = [Source.model_validate(source) for source in state.get("sources", [])]
    source_map: Dict[str, Source] = {source.id: source for source in sources}

    verified_claims: List[Claim] = []
    verification_issues: List[VerificationIssue] = []
    updated_notes: List[ResearchNote] = []

    for raw_note in state.get("notes", []):
        note = ResearchNote.model_validate(raw_note)
        updated_note_claims: List[Claim] = []

        for claim in note.claims:
            verified_claim, claim_issues = _verify_claim(claim, source_map)
            updated_note_claims.append(verified_claim)
            verified_claims.append(verified_claim)
            verification_issues.extend(claim_issues)

        note.claims = updated_note_claims
        updated_notes.append(note)

    weak_or_unsupported = [
        claim
        for claim in verified_claims
        if claim.verification_status in {"weak", "unsupported"}
    ]
    unsupported = [
        claim
        for claim in verified_claims
        if claim.verification_status == "unsupported"
    ]

    needs_more_research = (
        len(unsupported) > 0
        or len(weak_or_unsupported) > MAX_WEAK_OR_UNSUPPORTED_CLAIMS
        or len(verified_claims) == 0
    )

    logs = state.get("logs", []) + [
        "Verifier checked "
        f"{len(verified_claims)} claims; "
        f"supported={len([c for c in verified_claims if c.verification_status == 'supported'])}, "
        f"weak={len([c for c in verified_claims if c.verification_status == 'weak'])}, "
        f"unsupported={len(unsupported)}, "
        f"issues={len(verification_issues)}, "
        f"needs_more_research={needs_more_research}."
    ]

    return {
        "notes": [note.model_dump() for note in updated_notes],
        "verified_claims": [claim.model_dump() for claim in verified_claims],
        "verification_issues": [issue.model_dump() for issue in verification_issues],
        "needs_more_research": needs_more_research,
        "logs": logs,
    }
