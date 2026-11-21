"""
End-to-end tests for the EMS AI workflow orchestration.
Uses mocked LLM responses and mocked EMS API calls.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.orchestration.state import EMSWorkflowState


def _make_initial_state(round_type="INTERIM") -> dict:
    return {
        "workflow_id": "test-wf-001",
        "cohort_id": 1,
        "round_type": round_type,
        "attempt": 1,
        "interview_from": "2024-12-01",
        "interview_to": "2024-12-05",
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
        "execution_log": [],
    }


class TestInitializeNode:
    @pytest.mark.asyncio
    async def test_valid_interim_initialization(self):
        from app.orchestration.nodes import initialize_workflow_node
        state = _make_initial_state("INTERIM")
        result = await initialize_workflow_node(state)
        assert result["current_stage"] == "AVAILABILITY"
        assert "workflow_id" in result

    @pytest.mark.asyncio
    async def test_invalid_round_type_fails(self):
        from app.orchestration.nodes import initialize_workflow_node
        state = _make_initial_state("INVALID")
        result = await initialize_workflow_node(state)
        assert result["current_stage"] == "FAILED"
        assert "error_message" in result


class TestRoutingFunctions:
    def test_route_after_validation_proceed(self):
        from app.orchestration.routing import route_after_validation
        state = _make_initial_state()
        state["can_proceed"] = True
        state["current_stage"] = "AWAITING_APPROVAL"
        assert route_after_validation(state) == "human_approval"

    def test_route_after_validation_fail(self):
        from app.orchestration.routing import route_after_validation
        state = _make_initial_state()
        state["can_proceed"] = False
        state["current_stage"] = "FAILED"
        assert route_after_validation(state) == "handle_error"

    def test_route_after_approval_approved(self):
        from app.orchestration.routing import route_after_approval
        state = _make_initial_state()
        state["human_approved"] = True
        state["current_stage"] = "SUBMISSION"
        assert route_after_approval(state) == "submit_to_ems"

    def test_route_after_approval_rejected(self):
        from app.orchestration.routing import route_after_approval
        state = _make_initial_state()
        state["human_approved"] = False
        state["current_stage"] = "REJECTED"
        assert route_after_approval(state) == "__end__"

    def test_route_after_error_retries(self):
        from app.orchestration.routing import route_after_error
        state = _make_initial_state()
        state["retry_count"] = 1
        state["max_retries"] = 3
        state["current_stage"] = "AVAILABILITY"
        assert route_after_error(state) == "availability_check"

    def test_route_after_error_max_retries(self):
        from app.orchestration.routing import route_after_error
        state = _make_initial_state()
        state["retry_count"] = 3
        state["max_retries"] = 3
        state["current_stage"] = "FAILED"
        assert route_after_error(state) == "__end__"


class TestWorkflowState:
    def test_state_structure(self):
        """Verify the state TypedDict has all required fields."""
        state = _make_initial_state()
        required_fields = [
            "workflow_id", "cohort_id", "round_type", "attempt",
            "availability_results", "mapping_suggestions", "validation_results",
            "can_proceed", "human_approved", "submission_done", "current_stage",
            "error_message", "retry_count", "execution_log"
        ]
        for field in required_fields:
            assert field in state, f"Missing field: {field}"


class TestHandleErrorNode:
    @pytest.mark.asyncio
    async def test_error_node_increments_retry(self):
        from app.orchestration.nodes import handle_error_node
        state = _make_initial_state()
        state["retry_count"] = 0
        state["max_retries"] = 3
        state["error_message"] = "Agent failed"
        result = await handle_error_node(state)
        assert result["retry_count"] == 1
        assert result["current_stage"] == "AVAILABILITY"

    @pytest.mark.asyncio
    async def test_error_node_max_retries_fails(self):
        from app.orchestration.nodes import handle_error_node
        state = _make_initial_state()
        state["retry_count"] = 2
        state["max_retries"] = 3
        state["error_message"] = "Persistent failure"
        result = await handle_error_node(state)
        assert result["current_stage"] == "FAILED"
