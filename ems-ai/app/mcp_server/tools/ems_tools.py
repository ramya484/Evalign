"""MCP EMS Tools – 2 tools that call the EMS Spring Boot REST API."""
from __future__ import annotations
from typing import Optional
import httpx
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {settings.EMS_API_JWT_TOKEN}", "Content-Type": "application/json"}

def _base() -> str:
    return settings.EMS_API_BASE_URL.rstrip("/")


async def search_evaluator_data(
    cohort_id: int,
    vertical: Optional[str] = None,
    availability_status: Optional[str] = None,
    interview_from: Optional[str] = None,
    interview_to: Optional[str] = None,
) -> dict:
    """Search evaluator data from EMS for a cohort.
    Args: cohort_id (int), vertical (str), availability_status (str), interview_from/to (YYYY-MM-DD).
    Returns: {evaluators: [...], total: int, cohort_id: int}"""
    try:
        params = {}
        if vertical: params["vertical"] = vertical
        if availability_status: params["availability"] = availability_status
        if interview_from: params["interviewFrom"] = interview_from
        if interview_to: params["interviewTo"] = interview_to

        async with httpx.AsyncClient(timeout=settings.EMS_API_TIMEOUT) as client:
            # Get shortlisted evaluators for the cohort
            shortlist_resp = await client.get(f"{_base()}/api/cohorts/{cohort_id}/shortlist", headers=_auth_headers())
            shortlist = shortlist_resp.json() if shortlist_resp.status_code == 200 else []

            # Get full evaluator list with availability filter
            eval_resp = await client.get(f"{_base()}/api/evaluators", headers=_auth_headers(), params=params)
            all_evaluators = eval_resp.json() if eval_resp.status_code == 200 else []

        shortlist_ids = {e.get("evaluatorId") for e in shortlist} if isinstance(shortlist, list) else set()
        evaluators = [e for e in all_evaluators if isinstance(all_evaluators, list) and e.get("evaluatorId") in shortlist_ids]

        return {"evaluators": evaluators, "total": len(evaluators), "cohort_id": cohort_id}
    except Exception as exc:
        logger.error("search_evaluator_data error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def get_ems_data(
    resource_type: str,
    cohort_id: Optional[int] = None,
    round_type: Optional[str] = None,
) -> dict:
    """Retrieve authorized EMS data for agents.
    Args: resource_type (str): cohort|candidates|mappings|shortlist. cohort_id (int). round_type (str): INTERIM|FINAL.
    Returns: structured EMS data."""
    valid_types = {"cohort", "candidates", "mappings", "shortlist"}
    if resource_type not in valid_types:
        return {"error": f"resource_type must be one of {valid_types}", "code": "VALIDATION_ERROR"}

    try:
        async with httpx.AsyncClient(timeout=settings.EMS_API_TIMEOUT) as client:
            h = _auth_headers()
            if resource_type == "cohort":
                if not cohort_id:
                    return {"error": "cohort_id required", "code": "VALIDATION_ERROR"}
                r = await client.get(f"{_base()}/api/cohorts/{cohort_id}", headers=h)
                return {"cohort": r.json() if r.status_code == 200 else {}, "resource_type": resource_type}

            elif resource_type == "candidates":
                if not cohort_id:
                    return {"error": "cohort_id required", "code": "VALIDATION_ERROR"}
                r = await client.get(f"{_base()}/api/cohorts/{cohort_id}/candidates", headers=h)
                data = r.json() if r.status_code == 200 else []
                return {"candidates": data, "total": len(data) if isinstance(data, list) else 0, "resource_type": resource_type}

            elif resource_type == "shortlist":
                if not cohort_id:
                    return {"error": "cohort_id required", "code": "VALIDATION_ERROR"}
                r = await client.get(f"{_base()}/api/cohorts/{cohort_id}/shortlist", headers=h)
                data = r.json() if r.status_code == 200 else []
                return {"shortlist": data, "total": len(data) if isinstance(data, list) else 0, "resource_type": resource_type}

            elif resource_type == "mappings":
                if not cohort_id:
                    return {"error": "cohort_id required", "code": "VALIDATION_ERROR"}
                params = {}
                if round_type: params["round"] = round_type
                r = await client.get(f"{_base()}/api/cohorts/{cohort_id}/mappings", headers=h, params=params)
                data = r.json() if r.status_code == 200 else []
                return {"mappings": data, "total": len(data) if isinstance(data, list) else 0,
                        "resource_type": resource_type, "round_type": round_type}

    except Exception as exc:
        logger.error("get_ems_data error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}
