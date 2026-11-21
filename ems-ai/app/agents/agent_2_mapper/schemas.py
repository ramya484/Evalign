"""Pydantic schemas for Agent 2  Evaluator Mapping Agent."""
from __future__ import annotations
from typing import List, Optional, Dict
from pydantic import BaseModel

class MappingInput(BaseModel):
    cohort_id: int
    round_type: str   # INTERIM | FINAL
    attempt: int = 1

class MappingAssignment(BaseModel):
    candidate_id: int
    candidate_name: str
    evaluator_id: int
    evaluator_name: str
    round: str
    attempt: int
    reasoning: str

class MappingOutput(BaseModel):
    cohort_id: int
    round_type: str
    assignments: List[MappingAssignment]
    unassigned_candidates: List[str]
    summary: str
    workload_distribution: Dict[str, int]
