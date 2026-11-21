from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class ShortlistingRequest(BaseModel):
    cohort_id: Optional[int] = None
    target_role: str = "Evaluator"
    vertical: Optional[str] = "All"
    domain: Optional[str] = "All"
    target_count: Optional[int] = 10
    min_score: float = 75.0

class ShortlistCandidateItem(BaseModel):
    id: int
    name: str
    emp_id: str = ""
    email: str = ""
    vertical: str = ""
    domain: str = ""
    score: float = 0.0
    fit_rationale: str = ""
    recommendation: str = "SHORTLIST"
    status: str = "RECOMMENDED"
    notes: Optional[str] = None
    availability_status: str = "AVAILABLE"

class ShortlistingStats(BaseModel):
    total_processed: int = 0
    shortlisted_count: int = 0
    recommended_count: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    execution_status: str = "IDLE"
    last_run_timestamp: Optional[str] = None
    active_cohort_id: Optional[int] = None
    average_score: float = 0.0

class ShortlistingOutput(BaseModel):
    workflow_id: str
    stats: ShortlistingStats
    recommendations: List[ShortlistCandidateItem] = Field(default_factory=list)
    summary: str = ""
    execution_status: str = "COMPLETED"

class ShortlistingDecisionRequest(BaseModel):
    item_id: int
    decision: str = "APPROVE"
    cohort_id: Optional[int] = None
    notes: Optional[str] = None
