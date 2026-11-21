"""Conditional routing functions for the EMS LangGraph workflow."""
from app.orchestration.state import EMSWorkflowState


def route_after_initialization(state: EMSWorkflowState) -> str:
    if state.get("current_stage") == "FAILED":
        return "handle_error"
    return "availability_check"


def route_after_availability(state: EMSWorkflowState) -> str:
    if state.get("current_stage") == "ERROR":
        return "handle_error"
    return "mapping_suggestion"


def route_after_mapping(state: EMSWorkflowState) -> str:
    if state.get("current_stage") == "ERROR":
        return "handle_error"
    return "validation"


def route_after_validation(state: EMSWorkflowState) -> str:
    stage = state.get("current_stage", "")
    if stage == "ERROR":
        return "handle_error"
    if state.get("can_proceed"):
        return "human_approval"
    return "handle_error"


def route_after_approval(state: EMSWorkflowState) -> str:
    stage = state.get("current_stage", "")
    if stage == "SUBMISSION":
        return "submit_to_ems"
    if stage == "REJECTED":
        return "__end__"
    return "human_approval"


def route_after_error(state: EMSWorkflowState) -> str:
    stage = state.get("current_stage", "FAILED")
    retry = state.get("retry_count", 0)
    max_r = state.get("max_retries", 3)
    if stage == "FAILED" or retry >= max_r:
        return "__end__"
    return "availability_check"
