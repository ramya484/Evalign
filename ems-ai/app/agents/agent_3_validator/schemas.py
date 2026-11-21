"""Pydantic schemas for Agent 3 – Mapping Validation Agent."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel

class ProposedAssignment(BaseModel):
    candidate_id: int
    candidate_name: str
    evaluator_id: int
    evaluator_name: str
    round_type: str
    attempt: int

class ValidationInput(BaseModel):
    cohort_id: int
    proposed_assignments: List[ProposedAssignment]

class RuleCheckResult(BaseModel):
    rule_number: int
    rule_description: str
    passed: bool
    message: Optional[str] = None

class AssignmentValidationResult(BaseModel):
    candidate_name: str
    evaluator_name: str
    is_valid: bool
    rule_checks: List[RuleCheckResult]
    overall_message: str

class ValidationOutput(BaseModel):
    cohort_id: int
    total_assignments: int
    valid_count: int
    invalid_count: int
    validation_results: List[AssignmentValidationResult]
    can_proceed: bool
    summary: str
