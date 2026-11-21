"""
LangGraph node functions for the EMS multi-agent orchestration.
Each node runs an agent or performs a workflow step, then returns updated state.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Optional

import httpx

from app.agents.agent_1_availability.agent import AvailabilityAgent
from app.agents.agent_1_availability.schemas import AvailabilityInput
from app.agents.agent_2_mapper.agent import MappingAgent
from app.agents.agent_2_mapper.schemas import MappingInput, MappingAssignment
from app.agents.agent_3_validator.agent import ValidationAgent
from app.agents.agent_3_validator.schemas import ValidationInput, ProposedAssignment
from app.agents.llm_factory import create_llm
from app.config.settings import settings
from app.orchestration.state import EMSWorkflowState
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _log(state: EMSWorkflowState, msg: str) -> list:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return [f"[{ts}] {msg}"]


async def initialize_workflow_node(state: EMSWorkflowState) -> dict:
    """Initialize workflow: validate inputs, assign workflow_id, set stage."""
    wf_id = state.get("workflow_id") or str(uuid.uuid4())
    logger.info("Workflow %s starting: cohort=%s round=%s", wf_id, state["cohort_id"], state["round_type"])

    if state["round_type"] not in ("INTERIM", "FINAL"):
        return {
            "workflow_id": wf_id,
            "current_stage": "FAILED",
            "error_message": f"Invalid round_type: {state['round_type']}. Must be INTERIM or FINAL.",
            "execution_log": _log(state, f"INIT FAILED: invalid round_type"),
        }
    return {
        "workflow_id": wf_id,
        "current_stage": "AVAILABILITY",
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 3),
        "execution_log": _log(state, f"Workflow {wf_id} initialized"),
    }


async def availability_check_node(state: EMSWorkflowState) -> dict:
    """Run Agent 1  Evaluator Availability Agent."""
    logger.info("Node: availability_check | workflow=%s", state["workflow_id"])
    try:
        # Fetch evaluator emails from EMS API
        async with httpx.AsyncClient(timeout=settings.EMS_API_TIMEOUT) as client:
            resp = await client.get(
                f"{settings.EMS_API_BASE_URL}/api/cohorts/{state['cohort_id']}/shortlist",
                headers={"Authorization": f"Bearer {settings.EMS_API_JWT_TOKEN}"},
            )
            shortlist = resp.json() if resp.status_code == 200 else []

        evaluator_emails = [e.get("email", e.get("empId", "")) for e in shortlist if isinstance(e, dict)]

        llm = create_llm()
        agent = AvailabilityAgent(llm)
        result = await agent.run(AvailabilityInput(
            cohort_id=state["cohort_id"],
            interview_from=state.get("interview_from") or datetime.utcnow().strftime("%Y-%m-%d"),
            interview_to=state.get("interview_to") or datetime.utcnow().strftime("%Y-%m-%d"),
            evaluator_emails=evaluator_emails,
        ))
        return {
            "availability_check_done": True,
            "availability_results": result.model_dump(),
            "current_stage": "MAPPING",
            "error_message": None,
            "execution_log": _log(state, f"Agent 1 done: {result.summary}"),
        }
    except Exception as exc:
        logger.error("availability_check_node failed: %s", exc)
        return {
            "current_stage": "ERROR",
            "error_message": str(exc),
            "execution_log": _log(state, f"Agent 1 FAILED: {exc}"),
        }


async def mapping_suggestion_node(state: EMSWorkflowState) -> dict:
    """Run Agent 2  Evaluator Mapping Agent."""
    logger.info("Node: mapping_suggestion | workflow=%s", state["workflow_id"])
    try:
        llm = create_llm()
        agent = MappingAgent(llm)
        result = await agent.run(MappingInput(
            cohort_id=state["cohort_id"],
            round_type=state["round_type"],
            attempt=state.get("attempt", 1),
        ))
        return {
            "mapping_suggestions": result.model_dump(),
            "current_stage": "VALIDATION",
            "error_message": None,
            "execution_log": _log(state, f"Agent 2 done: {len(result.assignments)} assignments suggested"),
        }
    except Exception as exc:
        logger.error("mapping_suggestion_node failed: %s", exc)
        return {
            "current_stage": "ERROR",
            "error_message": str(exc),
            "execution_log": _log(state, f"Agent 2 FAILED: {exc}"),
        }


async def validation_node(state: EMSWorkflowState) -> dict:
    """Run Agent 3  Mapping Validation Agent."""
    logger.info("Node: validation | workflow=%s", state["workflow_id"])
    try:
        suggestions = state.get("mapping_suggestions") or {}
        assignments_raw = suggestions.get("assignments", [])
        proposed = [
            ProposedAssignment(
                candidate_id=a["candidate_id"],
                candidate_name=a["candidate_name"],
                evaluator_id=a["evaluator_id"],
                evaluator_name=a["evaluator_name"],
                round_type=a["round"],
                attempt=a["attempt"],
            )
            for a in assignments_raw
        ]

        llm = create_llm()
        agent = ValidationAgent(llm)
        result = await agent.run(ValidationInput(
            cohort_id=state["cohort_id"],
            proposed_assignments=proposed,
        ))
        stage = "AWAITING_APPROVAL" if result.can_proceed else "FAILED"
        return {
            "validation_done": True,
            "validation_results": result.model_dump(),
            "can_proceed": result.can_proceed,
            "current_stage": stage,
            "error_message": None if result.can_proceed else f"Validation failed: {result.summary}",
            "execution_log": _log(state, f"Agent 3 done: can_proceed={result.can_proceed} valid={result.valid_count}/{result.total_assignments}"),
        }
    except Exception as exc:
        logger.error("validation_node failed: %s", exc)
        return {
            "current_stage": "ERROR",
            "error_message": str(exc),
            "execution_log": _log(state, f"Agent 3 FAILED: {exc}"),
        }


async def human_approval_node(state: EMSWorkflowState) -> dict:
    """
    Interrupt point  pauses workflow for human approval.
    LangGraph interrupt() pauses here until resume is called with human_approved=True/False.
    """
    from langgraph.types import interrupt
    logger.info("Node: human_approval | workflow=%s | waiting for human decision", state["workflow_id"])
    response = interrupt({
        "message": "Please review the proposed mappings and approve (True) or reject (False).",
        "workflow_id": state["workflow_id"],
        "mappings": state.get("mapping_suggestions"),
        "validation": state.get("validation_results"),
    })
    # After resume, response contains human_approved
    approved = state.get("human_approved")
    stage = "SUBMISSION" if approved else "REJECTED"
    return {
        "human_approval_requested": True,
        "current_stage": stage,
        "execution_log": _log(state, f"Human decision: approved={approved} feedback={state.get('human_feedback')}"),
    }


async def submit_to_ems_node(state: EMSWorkflowState) -> dict:
    """Submit approved mappings to EMS Spring Boot backend via REST API."""
    logger.info("Node: submit_to_ems | workflow=%s", state["workflow_id"])
    suggestions = state.get("mapping_suggestions") or {}
    assignments = suggestions.get("assignments", [])
    results = []
    errors = []

    async with httpx.AsyncClient(timeout=settings.EMS_API_TIMEOUT) as client:
        h = {"Authorization": f"Bearer {settings.EMS_API_JWT_TOKEN}", "Content-Type": "application/json"}
        for a in assignments:
            payload = {
                "cohortId": state["cohort_id"],
                "candidateId": a["candidate_id"],
                "evaluatorId": a["evaluator_id"],
                "round": a["round"],
                "attempt": a["attempt"],
            }
            try:
                resp = await client.post(f"{settings.EMS_API_BASE_URL}/api/mappings", json=payload, headers=h)
                if resp.status_code in (200, 201):
                    results.append(resp.json())
                else:
                    errors.append({"assignment": a, "error": resp.text})
            except Exception as exc:
                errors.append({"assignment": a, "error": str(exc)})

    logger.info("Submitted %d mappings, %d errors", len(results), len(errors))
    return {
        "submission_done": True,
        "submission_results": results,
        "current_stage": "DONE",
        "execution_log": _log(state, f"Submitted {len(results)} mappings to EMS, {len(errors)} errors"),
    }


async def handle_error_node(state: EMSWorkflowState) -> dict:
    """Handle errors with retry logic."""
    retry = state.get("retry_count", 0) + 1
    max_r = state.get("max_retries", 3)
    logger.warning("handle_error: retry %d/%d error=%s", retry, max_r, state.get("error_message"))
    if retry < max_r:
        return {
            "retry_count": retry,
            "current_stage": "AVAILABILITY",   # restart from availability
            "error_message": None,
            "execution_log": _log(state, f"Retrying ({retry}/{max_r}): {state.get('error_message')}"),
        }
    return {
        "retry_count": retry,
        "current_stage": "FAILED",
        "execution_log": _log(state, f"Max retries reached. Workflow FAILED: {state.get('error_message')}"),
    }
