from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class Perspective(BaseModel):
    """An expert lens used to broaden the research plan."""

    name: str = Field(description="Short perspective name, e.g. technical, market, safety")
    description: str = Field(description="What this perspective focuses on")
    core_questions: List[str] = Field(default_factory=list)


class PerspectiveOutput(BaseModel):
    perspectives: List[Perspective] = Field(default_factory=list)


class ResearchTask(BaseModel):
    """A single research task produced by the planner."""

    id: str = Field(description="Stable task id, e.g. t1")
    question: str = Field(description="The concrete research question for this task")
    perspective: str = Field(description="The lens used for this task, e.g. technical, market, academic")
    priority: int = Field(default=1, ge=1, le=5)
    search_queries: List[str] = Field(default_factory=list)


class Source(BaseModel):
    """A source used as evidence for claims."""

    id: str
    title: str
    url: str
    content: str = ""
    score: Optional[float] = None
    source_type: str = "web"
    search_query: Optional[str] = None
    task_id: Optional[str] = None
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    accessed_at: Optional[str] = None
    credibility_score: Optional[float] = None


class ClaimDraft(BaseModel):
    """A claim drafted by the researcher before system metadata is attached."""

    text: str = Field(description="One concrete source-grounded claim")
    source_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class Claim(BaseModel):
    """A source-grounded atomic claim that can later be verified."""

    id: str = Field(description="Stable claim id, e.g. c_t1_1")
    text: str = Field(description="One concrete claim")
    task_id: str
    perspective: str
    source_ids: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    verification_status: str = "unverified"
    verification_reason: Optional[str] = None


class ResearchNote(BaseModel):
    """The research output for one task."""

    task_id: str
    perspective: str
    question: str
    summary: str
    claims: List[Claim] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class VerificationIssue(BaseModel):
    """A problem found when checking whether a claim is source-grounded."""

    claim_id: str
    severity: str = Field(description="info | warning | error")
    reason: str
    suggested_fix: Optional[str] = None


class VerifierOutput(BaseModel):
    """Structured output produced by the verifier node."""

    verified_claims: List[Claim] = Field(default_factory=list)
    issues: List[VerificationIssue] = Field(default_factory=list)
    needs_more_research: bool = False


class PlannerOutput(BaseModel):
    research_goal: str
    tasks: List[ResearchTask]


class ResearcherOutput(BaseModel):
    summary: str
    claims: List[ClaimDraft] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
