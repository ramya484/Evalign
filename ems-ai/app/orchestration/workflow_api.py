# -*- coding: utf-8 -*-
"""
FastAPI HTTP wrapper for the EMS LangGraph orchestration service and the three specialized AI agents:
  - Agent 1: Training Cohorts & Outlook Intelligence Agent (Training Cohorts page)
  - Agent 2: Evaluator Mapping Agent + Outlook Integration (Evaluator Mapping page)
  - Agent 3: Shortlisting Agent (Dashboard and Pool pages)
"""
from __future__ import annotations
from typing import Optional, List
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database.connection import create_all_tables
from app.orchestration.graph import run_ems_workflow, resume_workflow, get_workflow_state
from app.agents.agent_1_cohort.agent import TrainingCohortsAgent
from app.agents.agent_1_cohort.schemas import CohortAnalysisRequest, CohortAnalysisResult
from app.agents.agent_3_shortlisting.agent import ShortlistingAgent
from app.agents.agent_3_shortlisting.schemas import (
    ShortlistingRequest,
    ShortlistingOutput,
    ShortlistingDecisionRequest,
)
from app.database.connection import AsyncSessionLocal
from app.database.repositories.email_repository import EmailRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Cache for latest cohort analyses by cohort_id
_cohort_analysis_cache: dict[int, CohortAnalysisResult] = {}
_latest_global_cohort_analysis: Optional[CohortAnalysisResult] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_all_tables()
    logger.info("EMS AI Workflow API started with all 3 Agents registered")
    yield
    logger.info("EMS AI Workflow API shutting down")


app = FastAPI(
    title="EMS AI Multi-Agent API",
    description=(
        "Centralized Python AI services for Evaluator Mapping System.\n"
        "- Agent 1: Training Cohorts Intelligence (Training Cohorts page)\n"
        "- Agent 2: Evaluator Mapping + Outlook Integration (Evaluator Mapping page)\n"
        "- Agent 3: Shortlisting Agent (Dashboard and Pool pages)"
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Agent 1 - Training Cohorts Page + Outlook Integration
# ------------------------------------------------------------------------------

@app.post("/api/ai/cohort/analyze", response_model=CohortAnalysisResult)
async def analyze_cohort(request: CohortAnalysisRequest):
    """
    Trigger Agent 1: Audits Outlook communications, schedule announcements,
    nominations, and conflicts for training cohorts.
    """
    global _latest_global_cohort_analysis, _cohort_analysis_cache
    try:
        agent = TrainingCohortsAgent()
        result = await agent.run(request)
        if request.cohort_id:
            _cohort_analysis_cache[request.cohort_id] = result
        _latest_global_cohort_analysis = result
        return result
    except Exception as exc:
        logger.error("Agent 1 analysis failed: %s", exc)
        raise HTTPException(500, f"Agent 1 analysis failed: {exc}")


@app.get("/api/ai/cohort/{cohort_id}/analysis", response_model=CohortAnalysisResult)
async def get_cohort_analysis(cohort_id: int):
    """Retrieve the cached or live Agent 1 analysis for a specific cohort."""
    if cohort_id in _cohort_analysis_cache:
        return _cohort_analysis_cache[cohort_id]
    req = CohortAnalysisRequest(cohort_id=cohort_id)
    agent = TrainingCohortsAgent()
    res = await agent.run(req)
    _cohort_analysis_cache[cohort_id] = res
    return res


# ------------------------------------------------------------------------------
# Agent 2 - Evaluator Mapping Page + Outlook Integration
# ------------------------------------------------------------------------------

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
    """Start Agent 2 AI workflow: workload-balanced mapping verified against Outlook emails."""
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
        logger.error("Agent 2 start_workflow error: %s", exc)
        raise HTTPException(500, f"Agent 2 workflow failed: {exc}")


@app.post("/api/ai/workflow/approve")
async def approve_workflow(request: ApprovalRequest):
    """Submit human approval or rejection for Agent 2 mapping suggestions."""
    try:
        result = await resume_workflow(
            workflow_id=request.workflow_id,
            approved=request.approved,
            feedback=request.feedback,
        )
        return result
    except Exception as exc:
        logger.error("Agent 2 approve_workflow error: %s", exc)
        raise HTTPException(500, f"Resume failed: {exc}")


@app.get("/api/ai/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get current state of an Agent 2 workflow."""
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


# ------------------------------------------------------------------------------
# Agent 3 - Shortlisting Agent (Shared by Dashboard & Pool Pages)
# ------------------------------------------------------------------------------

@app.post("/api/ai/shortlist/run", response_model=ShortlistingOutput)
async def run_shortlisting(request: ShortlistingRequest):
    """
    Trigger Agent 3: Evaluates candidates/evaluators from the pool.
    Updates shared state visible on both Dashboard and Pool pages.
    """
    try:
        agent = ShortlistingAgent()
        result = await agent.run(request)
        return result
    except Exception as exc:
        logger.error("Agent 3 shortlisting failed: %s", exc)
        raise HTTPException(500, f"Shortlisting failed: {exc}")


@app.get("/api/ai/shortlist/stats")
async def get_shortlist_stats():
    """Retrieve shared shortlisting statistics for Dashboard and Pool."""
    stats = ShortlistingAgent.get_shared_stats()
    return stats.model_dump()


@app.get("/api/ai/shortlist/results")
async def get_shortlist_results():
    """Retrieve current shortlisting candidate recommendations for Pool & Dashboard."""
    results = ShortlistingAgent.get_shared_recommendations()
    stats = ShortlistingAgent.get_shared_stats()
    return {
        "stats": stats.model_dump(),
        "recommendations": [r.model_dump() for r in results],
        "total": len(results),
    }


@app.post("/api/ai/shortlist/decision")
async def submit_shortlist_decision(request: ShortlistingDecisionRequest):
    """Approve or reject a shortlisting recommendation from the Pool page."""
    try:
        updated_stats = ShortlistingAgent.apply_decision(request)
        return {
            "success": True,
            "message": f"Candidate #{request.item_id} marked as {request.decision}ED",
            "stats": updated_stats.model_dump(),
        }
    except Exception as exc:
        logger.error("submit_shortlist_decision error: %s", exc)
        raise HTTPException(500, f"Decision submission failed: {exc}")


# ------------------------------------------------------------------------------
# Centralized Outlook Duplicate Database Tools & Utilities
# ------------------------------------------------------------------------------

@app.get("/api/ai/emails/preview")
async def search_email_preview(keywords: str = "schedule", limit: int = 10):
    """Preview emails in the duplicate database matching query terms."""
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            kw_list = [k.strip() for k in keywords.split() if k.strip()][:5]
            records = await repo.search_by_keywords(kw_list, limit)
            return {"emails": [r.to_dict() for r in records], "count": len(records)}
    except Exception as exc:
        return {"error": str(exc), "emails": [], "count": 0}


@app.post("/api/ai/email/import")
async def import_emails(dir_path: str = "./data/imports"):
    """Trigger email import from the configured import directory into the Outlook DB."""
    from app.email_import.import_service import EmailImportService
    svc = EmailImportService()
    result = await svc.import_from_directory(dir_path)
    return result


@app.get("/api/ai/health")
async def health_check():
    return {
        "status": "ok",
        "service": "EMS AI Multi-Agent API",
        "version": "2.0.0",
        "agents": {
            "agent_1": "Training Cohorts & Outlook Intelligence Agent",
            "agent_2": "Evaluator Mapping Agent + Outlook Integration",
            "agent_3": "Shortlisting Agent (Dashboard and Pool)",
        },
    }