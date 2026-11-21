"""
FastAPI HTTP wrapper for the EMS LangGraph orchestration service.
Exposes REST endpoints that the Spring Boot backend calls to trigger AI workflows.
"""
from __future__ import annotations
from typing import Optional
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database.connection import create_all_tables
from app.orchestration.graph import run_ems_workflow, resume_workflow, get_workflow_state
from app.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_all_tables()
    logger.info("EMS AI Workflow API started")
    yield
    logger.info("EMS AI Workflow API shutting down")


app = FastAPI(
    title="EMS AI Workflow API",
    description="Python AI services for the Evaluator Mapping System – LangGraph multi-agent orchestration.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WorkflowStartRequest(BaseModel):
    cohort_id: int
    round_type: str               # INTERIM | FINAL
    attempt: int = 1
    interview_from: Optional[str] = None  # YYYY-MM-DD
    interview_to: Optional[str] = None


class ApprovalRequest(BaseModel):
    workflow_id: str
    approved: bool
    feedback: Optional[str] = None


@app.post("/api/ai/workflow/start")
async def start_workflow(request: WorkflowStartRequest):
    """Start the EMS AI agent workflow for a cohort+round."""
    if request.round_type not in ("INTERIM", "FINAL"):
        raise HTTPException(400, "round_type must be INTERIM or FINAL")
    try:
        result = await run_ems_workflow(
            cohort_id=request.cohort_id,
            round_type=request.round_type,
            attempt=request.attempt,
            interview_from=request.interview_from,
            interview_to=request.interview_to,
        )
        return result
    except Exception as exc:
        logger.error("start_workflow error: %s", exc)
        raise HTTPException(500, f"Workflow failed: {exc}")


@app.post("/api/ai/workflow/approve")
async def approve_workflow(request: ApprovalRequest):
    """Submit human approval or rejection for a paused workflow."""
    try:
        result = await resume_workflow(
            workflow_id=request.workflow_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        return result
    except Exception as exc:
        logger.error("approve_workflow error: %s", exc)
        raise HTTPException(500, f"Resume failed: {exc}")


@app.get("/api/ai/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get current state of a workflow."""
    state = await get_workflow_state(workflow_id)
    if "error" in state:
        raise HTTPException(404, state["error"])
    return {
        "workflow_id": workflow_id,
        "current_stage": state.get("current_stage"),
        "can_proceed": state.get("can_proceed"),
        "human_approval_requested": state.get("human_approval_requested"),
        "mapping_suggestions": state.get("mapping_suggestions"),
        "validation_results": state.get("validation_results"),
        "error_message": state.get("error_message"),
    }


@app.post("/api/ai/email/import")
async def import_emails(dir_path: str = "./data/imports"):
    """Trigger email import from the configured import directory."""
    from app.email_import.import_service import EmailImportService
    svc = EmailImportService()
    result = await svc.import_from_directory(dir_path)
    return result


@app.get("/api/ai/health")
async def health_check():
    return {"status": "ok", "service": "EMS AI Workflow API", "version": "1.0.0"}
