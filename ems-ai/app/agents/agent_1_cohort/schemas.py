from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class EmailCitation(BaseModel):
    email_id: int
    message_id: str = ""
    sender: str
    recipient: str = ""
    subject: str
    received_date: str
    snippet: str = ""

class CohortFinding(BaseModel):
    category: str = Field(..., description="SCHEDULE | PARTICIPANTS | EVALUATOR_NOMINATION | AVAILABILITY | CONFLICT")
    title: str
    description: str
    severity: str = Field("INFO", description="INFO | WARNING | CRITICAL")
    source_email: Optional[EmailCitation] = None
    actionable_recommendation: str = ""

class CohortAnalysisRequest(BaseModel):
    cohort_id: Optional[int] = None
    batch_code: Optional[str] = None
    interview_from: Optional[str] = None
    interview_to: Optional[str] = None

class CohortAnalysisResult(BaseModel):
    cohort_id: Optional[int] = None
    cohort_name: str = "All Active Cohorts"
    batch_code: str = ""
    candidate_count: int = 0
    analyzed_emails_count: int = 0
    findings: List[CohortFinding] = Field(default_factory=list)
    email_citations: List[EmailCitation] = Field(default_factory=list)
    summary: str = ""
    status: str = "COMPLETED"
    last_synced_at: Optional[str] = None
