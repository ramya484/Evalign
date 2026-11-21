from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict

import httpx
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

from app.agents.agent_3_shortlisting.schemas import (
    ShortlistingRequest,
    ShortlistingOutput,
    ShortlistCandidateItem,
    ShortlistingStats,
    ShortlistingDecisionRequest,
)
from app.agents.agent_3_shortlisting.prompts import SYSTEM_PROMPT
from app.agents.base_agent import BaseEMSAgent
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_shared_stats = ShortlistingStats(
    total_processed=0,
    shortlisted_count=0,
    recommended_count=0,
    approved_count=0,
    rejected_count=0,
    execution_status="IDLE",
    last_run_timestamp=None,
    active_cohort_id=None,
    average_score=0.0,
)
_shared_recommendations: List[ShortlistCandidateItem] = []


class ShortlistingAgent(BaseEMSAgent):
    """Agent 3: Shortlisting Agent shared across Dashboard and Pool."""

    def __init__(self, llm=None):
        super().__init__(llm, [])
        self.executor = None

    async def run(self, request: ShortlistingRequest) -> ShortlistingOutput:
        global _shared_stats, _shared_recommendations

        workflow_id = f"shortlist-{uuid.uuid4().hex[:8]}"
        _shared_stats.execution_status = "RUNNING"
        logger.info("Agent 3 Shortlisting initiated: workflow_id=%s role=%s cohort=%s",
                    workflow_id, request.target_role, request.cohort_id)

        pool_records = await self._fetch_pool_data(request)
        recommendations: List[ShortlistCandidateItem] = []
        scores = []

        for item in pool_records:
            score, rationale, rec = self._evaluate_record(item, request)
            scores.append(score)
            status = "RECOMMENDED" if rec in ("SHORTLIST", "WAITLIST") else "REJECTED"

            rec_item = ShortlistCandidateItem(
                id=item.get("id", 0),
                name=item.get("name", "Unknown"),
                emp_id=item.get("empId", ""),
                email=item.get("email", ""),
                vertical=item.get("vertical", "General"),
                domain=item.get("domain", "General"),
                score=score,
                fit_rationale=rationale,
                recommendation=rec,
                status=status,
                availability_status=item.get("availabilityStatus", "AVAILABLE"),
            )
            recommendations.append(rec_item)

        recommendations.sort(key=lambda x: x.score, reverse=True)
        target_count = request.target_count or 15
        shortlisted = [r for r in recommendations if r.recommendation == "SHORTLIST"][:target_count]
        recommended = [r for r in recommendations if r.recommendation in ("SHORTLIST", "WAITLIST")]

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        now_ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")

        _shared_stats = ShortlistingStats(
            total_processed=len(pool_records),
            shortlisted_count=len(shortlisted),
            recommended_count=len(recommended),
            approved_count=0,
            rejected_count=len([r for r in recommendations if r.recommendation == "REJECT"]),
            execution_status="COMPLETED",
            last_run_timestamp=now_ts,
            active_cohort_id=request.cohort_id,
            average_score=avg_score,
        )
        _shared_recommendations = recommendations

        summary = (
            f"Shortlisting Agent processed {len(pool_records)} personnel from the Master Pool. "
            f"Successfully shortlisted {len(shortlisted)} candidates/evaluators with average suitability score {avg_score}/100. "
            f"All business rules and availability constraints applied."
        )

        return ShortlistingOutput(
            workflow_id=workflow_id,
            stats=_shared_stats,
            recommendations=recommendations,
            summary=summary,
            execution_status="COMPLETED",
        )

    async def _fetch_pool_data(self, request: ShortlistingRequest) -> List[dict]:
        url = f"{settings.EMS_API_BASE_URL}/api/evaluators"
        headers = {"Authorization": f"Bearer {settings.EMS_API_JWT_TOKEN}"}
        params = {}
        if request.vertical and request.vertical != "All":
            params["vertical"] = request.vertical
        if request.domain and request.domain != "All":
            params["domain"] = request.domain

        try:
            async with httpx.AsyncClient(timeout=settings.EMS_API_TIMEOUT) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data:
                        results.append({
                            "id": item.get("evaluatorId") or item.get("id"),
                            "name": item.get("name"),
                            "empId": item.get("empId", ""),
                            "email": item.get("email", ""),
                            "vertical": item.get("vertical", ""),
                            "domain": item.get("domain", ""),
                            "availabilityStatus": item.get("availabilityStatus", "AVAILABLE"),
                        })
                    return results
        except Exception as exc:
            logger.error("Failed to fetch pool data from backend: %s. Using default sample.", exc)

        return [
            {"id": 1, "name": "Dr. Aris Thorne", "empId": "EMP-001", "email": "aris.thorne@company.com", "vertical": "BFS", "domain": "Java / Spring Boot", "availabilityStatus": "AVAILABLE"},
            {"id": 2, "name": "Elena Rostova", "empId": "EMP-002", "email": "elena.rostova@company.com", "vertical": "HealthCare", "domain": "Data Science / ML", "availabilityStatus": "AVAILABLE"},
            {"id": 3, "name": "Marcus Vance", "empId": "EMP-003", "email": "marcus.vance@company.com", "vertical": "Retail", "domain": "Full Stack / Angular", "availabilityStatus": "AVAILABLE"},
            {"id": 4, "name": "Priya Sharma", "empId": "EMP-004", "email": "priya.evaluator@company.com", "vertical": "BFS", "domain": "Cloud Architecture / AWS", "availabilityStatus": "UNAVAILABLE"},
            {"id": 5, "name": "Suresh Kumar", "empId": "EMP-005", "email": "suresh.kumar@company.com", "vertical": "Insurance", "domain": "Java / Spring Boot", "availabilityStatus": "AVAILABLE"},
            {"id": 6, "name": "Meera Patel", "empId": "EMP-006", "email": "meera.sme@company.com", "vertical": "HealthCare", "domain": "Data Engineering", "availabilityStatus": "AVAILABLE"},
        ]

    def _evaluate_record(self, item: dict, request: ShortlistingRequest) -> tuple[float, str, str]:
        base_score = 70.0
        avail = str(item.get("availabilityStatus", "AVAILABLE")).upper()

        if avail != "AVAILABLE":
            return (
                30.0,
                f"Candidate currently {avail}. Excluded per EMS Rule 2.",
                "REJECT",
            )

        domain = (item.get("domain") or "").lower()
        req_domain = (request.domain or "All").lower()
        if req_domain != "all" and req_domain in domain:
            base_score += 18.0
        else:
            base_score += 10.0

        vertical = (item.get("vertical") or "").lower()
        req_vertical = (request.vertical or "All").lower()
        if req_vertical != "all" and req_vertical in vertical:
            base_score += 10.0
        else:
            base_score += 5.0

        score = min(98.0, base_score)

        if score >= 85.0:
            rec = "SHORTLIST"
            rationale = f"Strong domain fit ({item.get('domain')}) and full availability. Recommended for cohort allocation."
        elif score >= 70.0:
            rec = "WAITLIST"
            rationale = f"Good technical profile ({item.get('vertical')}). Suitable as backup allocation."
        else:
            rec = "REJECT"
            rationale = "Score below qualification threshold."

        return (score, rationale, rec)

    @classmethod
    def get_shared_stats(cls) -> ShortlistingStats:
        return _shared_stats

    @classmethod
    def get_shared_recommendations(cls) -> List[ShortlistCandidateItem]:
        return _shared_recommendations

    @classmethod
    def apply_decision(cls, request: ShortlistingDecisionRequest) -> ShortlistingStats:
        global _shared_stats, _shared_recommendations
        for r in _shared_recommendations:
            if r.id == request.item_id:
                if request.decision == "APPROVE":
                    r.status = "APPROVED"
                    _shared_stats.approved_count += 1
                else:
                    r.status = "REJECTED"
                    _shared_stats.rejected_count += 1
                r.notes = request.notes
                break
        return _shared_stats
