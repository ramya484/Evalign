"""Pydantic schemas for Agent 1  Evaluator Availability Agent."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel

class AvailabilityInput(BaseModel):
    cohort_id: int
    interview_from: str   # YYYY-MM-DD
    interview_to: str     # YYYY-MM-DD
    evaluator_emails: List[str]

class EvaluatorAvailabilityResult(BaseModel):
    evaluator_email: str
    evaluator_name: str
    is_available: bool
    unavailability_reason: Optional[str] = None
    email_evidence: Optional[str] = None  # subject of the email found

class AvailabilityOutput(BaseModel):
    cohort_id: int
    interview_period: str
    results: List[EvaluatorAvailabilityResult]
    summary: str
    emails_analyzed: int
