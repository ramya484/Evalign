"""
Shared LangGraph workflow state for EMS multi-agent orchestration.
"""
from __future__ import annotations
from typing import TypedDict, Optional, List, Annotated
import operator


class EMSWorkflowState(TypedDict):
    # Identification
    workflow_id: str
    cohort_id: int
    round_type: str               # INTERIM | FINAL
    attempt: int

    # Interview window (optional, used by Agent 1)
    interview_from: Optional[str]  # YYYY-MM-DD
    interview_to: Optional[str]

    # Agent 1 output
    availability_check_done: bool
    availability_results: Optional[dict]

    # Agent 2 output
    mapping_suggestions: Optional[dict]

    # Agent 3 output
    validation_done: bool
    validation_results: Optional[dict]
    can_proceed: bool

    # Human approval (LangGraph interrupt)
    human_approval_requested: bool
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # EMS submission
    submission_done: bool
    submission_results: Optional[List[dict]]

    # Execution tracking
    current_stage: str            # INIT|AVAILABILITY|MAPPING|VALIDATION|AWAITING_APPROVAL|SUBMISSION|DONE|FAILED|REJECTED
    error_message: Optional[str]
    retry_count: int
    max_retries: int

    # Log
    execution_log: Annotated[List[str], operator.add]
