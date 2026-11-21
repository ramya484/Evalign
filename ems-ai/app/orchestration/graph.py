"""
LangGraph StateGraph  EMS multi-agent orchestration.
Builds and compiles the graph with interrupt_before=["human_approval"] for human-in-the-loop.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.orchestration.state import EMSWorkflowState
from app.orchestration.nodes import (
    initialize_workflow_node,
    availability_check_node,
    mapping_suggestion_node,
    validation_node,
    human_approval_node,
    submit_to_ems_node,
    handle_error_node,
)
from app.orchestration.routing import (
    route_after_initialization,
    route_after_availability,
    route_after_mapping,
    route_after_validation,
    route_after_approval,
    route_after_error,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def build_ems_workflow() -> StateGraph:
    """Build and compile the EMS LangGraph StateGraph."""
    workflow = StateGraph(EMSWorkflowState)

    # -- Add nodes --------------------------------------------------------------
    workflow.add_node("initialize", initialize_workflow_node)
    workflow.add_node("availability_check", availability_check_node)
    workflow.add_node("mapping_suggestion", mapping_suggestion_node)
    workflow.add_node("validation", validation_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("submit_to_ems", submit_to_ems_node)
    workflow.add_node("handle_error", handle_error_node)

    # -- Entry point ------------------------------------------------------------
    workflow.set_entry_point("initialize")

    # -- Conditional edges ------------------------------------------------------
    workflow.add_conditional_edges("initialize", route_after_initialization, {
        "availability_check": "availability_check",
        "handle_error": "handle_error",
    })
    workflow.add_conditional_edges("availability_check", route_after_availability, {
        "mapping_suggestion": "mapping_suggestion",
        "handle_error": "handle_error",
    })
    workflow.add_conditional_edges("mapping_suggestion", route_after_mapping, {
        "validation": "validation",
        "handle_error": "handle_error",
    })
    workflow.add_conditional_edges("validation", route_after_validation, {
        "human_approval": "human_approval",
        "handle_error": "handle_error",
    })
    workflow.add_conditional_edges("human_approval", route_after_approval, {
        "submit_to_ems": "submit_to_ems",
        "__end__": END,
        "human_approval": "human_approval",
    })
    workflow.add_conditional_edges("handle_error", route_after_error, {
        "availability_check": "availability_check",
        "__end__": END,
    })
    workflow.add_edge("submit_to_ems", END)

    # -- Compile with MemorySaver checkpointer + human approval interrupt ------
    checkpointer = MemorySaver()
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"],
    )


# Global compiled graph
ems_graph = build_ems_workflow()


async def run_ems_workflow(
    cohort_id: int,
    round_type: str,
    attempt: int = 1,
    interview_from: Optional[str] = None,
    interview_to: Optional[str] = None,
) -> dict:
    """Start a new EMS agent workflow."""
    workflow_id = str(uuid.uuid4())
    initial_state: EMSWorkflowState = {
        "workflow_id": workflow_id,
        "cohort_id": cohort_id,
        "round_type": round_type,
        "attempt": attempt,
        "interview_from": interview_from,
        "interview_to": interview_to,
        "availability_check_done": False,
        "availability_results": None,
        "mapping_suggestions": None,
        "validation_done": False,
        "validation_results": None,
        "can_proceed": False,
        "human_approval_requested": False,
        "human_approved": None,
        "human_feedback": None,
        "submission_done": False,
        "submission_results": None,
        "current_stage": "INIT",
        "error_message": None,
        "retry_count": 0,
        "max_retries": 3,
        "execution_log": [f"[{datetime.utcnow().isoformat()}Z] Workflow {workflow_id} created"],
    }
    config = {"configurable": {"thread_id": workflow_id}}
    final_state = await ems_graph.ainvoke(initial_state, config=config)
    logger.info("Workflow %s completed at stage: %s", workflow_id, final_state.get("current_stage"))
    return {
        "workflow_id": workflow_id,
        "status": final_state.get("current_stage"),
        "mapping_suggestions": final_state.get("mapping_suggestions"),
        "validation_results": final_state.get("validation_results"),
        "human_approval_requested": final_state.get("human_approval_requested", False),
        "execution_log": final_state.get("execution_log", []),
    }


async def resume_workflow(
    workflow_id: str,
    approved: bool,
    feedback: Optional[str] = None,
) -> dict:
    """Resume a workflow paused at human_approval interrupt."""
    config = {"configurable": {"thread_id": workflow_id}}
    update = {"human_approved": approved, "human_feedback": feedback}
    final_state = await ems_graph.ainvoke(Command(resume=update), config=config)
    logger.info("Workflow %s resumed: approved=%s stage=%s", workflow_id, approved, final_state.get("current_stage"))
    return {
        "workflow_id": workflow_id,
        "status": final_state.get("current_stage"),
        "submission_results": final_state.get("submission_results"),
        "execution_log": final_state.get("execution_log", []),
    }


async def get_workflow_state(workflow_id: str) -> dict:
    """Get the current saved state of a workflow by ID."""
    config = {"configurable": {"thread_id": workflow_id}}
    state = await ems_graph.aget_state(config)
    if state is None:
        return {"error": f"Workflow {workflow_id} not found"}
    return dict(state.values) if hasattr(state, "values") else {}
