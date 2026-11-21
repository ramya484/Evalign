from __future__ import annotations
import json
import re
from datetime import datetime
from typing import Optional, List

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate

from app.agents.agent_1_cohort.schemas import (
    CohortAnalysisRequest,
    CohortAnalysisResult,
    CohortFinding,
    EmailCitation,
)
from app.agents.agent_1_cohort.prompts import SYSTEM_PROMPT
from app.agents.base_agent import BaseEMSAgent
from app.database.connection import AsyncSessionLocal
from app.database.repositories.email_repository import EmailRepository
from app.mcp_server.tools.email_tools import (
    search_emails,
    search_by_subject,
    get_email_content,
)
from app.mcp_server.tools.ems_tools import get_ems_data
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _build_agent1_tools():
    @tool
    async def tool_search_cohort_emails(keywords: str, limit: int = 20) -> str:
        """Search Outlook emails for training cohort keywords."""
        res = await search_emails(keywords, limit)
        return json.dumps(res)

    @tool
    async def tool_search_subject(query: str, limit: int = 20) -> str:
        """Search email subject lines for specific batch codes."""
        res = await search_by_subject(query, limit)
        return json.dumps(res)

    return [tool_search_cohort_emails, tool_search_subject]


REACT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
Thought: I now know the final answer
Final Answer: the final answer in valid JSON

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


class TrainingCohortsAgent(BaseEMSAgent):
    """Agent 1: Audits Outlook communications for Training Cohorts page."""

    def __init__(self, llm=None):
        self.llm = llm
        tools = _build_agent1_tools()
        if llm:
            super().__init__(llm, tools)
            prompt = PromptTemplate.from_template(REACT_TEMPLATE)
            agent = create_react_agent(llm, tools, prompt)
            self.executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=8,
                handle_parsing_errors=True,
            )
        else:
            self.executor = None

    async def run(self, request: CohortAnalysisRequest) -> CohortAnalysisResult:
        logger.info("Agent 1 executing for cohort_id=%s batch_code=%s", request.cohort_id, request.batch_code)
        db_emails = await self._fetch_relevant_emails(request)
        ems_info = await self._fetch_ems_info(request.cohort_id) if request.cohort_id else {}
        return await self._analyze_deterministically(request, db_emails, ems_info)

    async def _fetch_relevant_emails(self, request: CohortAnalysisRequest) -> List[dict]:
        keywords = ["cohort", "batch", "schedule", "interview", "leave", "office", "nomination", "evaluator"]
        if request.batch_code:
            keywords.append(request.batch_code.lower())

        emails = []
        try:
            async with AsyncSessionLocal() as session:
                repo = EmailRepository(session)
                records = await repo.search_by_keywords(keywords, limit=50)
                for r in records:
                    emails.append(r.to_dict())
        except Exception as exc:
            logger.error("Error fetching emails for Agent 1: %s", exc)
        return emails

    async def _fetch_ems_info(self, cohort_id: int) -> dict:
        try:
            cands = await get_ems_data("candidates", cohort_id=cohort_id)
            shortlist = await get_ems_data("shortlist", cohort_id=cohort_id)
            return {"candidates": cands.get("candidates", []), "shortlist": shortlist.get("shortlist", [])}
        except Exception as exc:
            logger.error("Error fetching EMS info for Agent 1: %s", exc)
            return {}

    async def _analyze_deterministically(
        self,
        request: CohortAnalysisRequest,
        emails: List[dict],
        ems_info: dict,
    ) -> CohortAnalysisResult:
        findings: List[CohortFinding] = []
        citations: List[EmailCitation] = []
        candidate_count = len(ems_info.get("candidates", []))

        for em in emails:
            citation = EmailCitation(
                email_id=em.get("email_id", 0),
                message_id=em.get("message_id", ""),
                sender=em.get("sender_email", ""),
                recipient=em.get("recipient_email", ""),
                subject=em.get("subject", ""),
                received_date=str(em.get("received_date", ""))[:19],
                snippet=(em.get("body_text") or "")[:150] + "...",
            )
            citations.append(citation)

            subject_lower = (em.get("subject") or "").lower()
            body_lower = (em.get("body_text") or "").lower()

            if any(k in subject_lower or k in body_lower for k in ["interview schedule", "batch-1", "batch-2", "week of"]):
                date_match = re.search(r"(dec(ember)?\s+\d+(-\d+)?)", body_lower + " " + subject_lower)
                date_str = date_match.group(1).title() if date_match else "Upcoming Dates"
                findings.append(CohortFinding(
                    category="SCHEDULE",
                    title=f"Schedule Announcement: {em.get('subject')}",
                    description=f"Outlook email announces interview schedule window ({date_str}). Sent to {em.get('recipient_email')}.",
                    severity="INFO",
                    source_email=citation,
                    actionable_recommendation=f"Verify that EMS cohort interview dates align with {date_str}.",
                ))

            if any(k in subject_lower for k in ["out of office", "ooo", "leave request", "away"]):
                findings.append(CohortFinding(
                    category="CONFLICT",
                    title=f"Evaluator Leave Notice: {em.get('sender_email')}",
                    description=f"Sender reported leave/absence: '{em.get('subject')}'. Content: {(em.get('body_text') or '')[:120]}.",
                    severity="WARNING",
                    source_email=citation,
                    actionable_recommendation="Ensure this evaluator is marked unavailable or excluded from mapping for overlapping interview dates.",
                ))

            if any(k in subject_lower or k in body_lower for k in ["interview availability", "available for batch", "happy to take"]):
                findings.append(CohortFinding(
                    category="EVALUATOR_NOMINATION",
                    title=f"Evaluator Confirmed Availability: {em.get('sender_email')}",
                    description=f"Evaluator explicitly offered availability for evaluations in email '{em.get('subject')}'.",
                    severity="INFO",
                    source_email=citation,
                    actionable_recommendation="Evaluator can be shortlisted for upcoming cohort batches.",
                ))

            if "project reassignment" in subject_lower or "unavailable for interviews" in body_lower:
                findings.append(CohortFinding(
                    category="CONFLICT",
                    title=f"Project Conflict: {em.get('subject')}",
                    description=f"Manager notice: {(em.get('body_text') or '')[:140]}",
                    severity="CRITICAL",
                    source_email=citation,
                    actionable_recommendation="Update SME availability status to UNAVAILABLE in Master Pool.",
                ))

        cohort_label = f"Cohort #{request.cohort_id}" if request.cohort_id else "All Cohorts"
        summary = (
            f"Agent 1 analyzed {len(emails)} Outlook email records from duplicate database for {cohort_label}. "
            f"Detected {len([f for f in findings if f.category == 'CONFLICT'])} potential schedule/leave conflicts, "
            f"{len([f for f in findings if f.category == 'SCHEDULE'])} schedule notices, and "
            f"{len([f for f in findings if f.category == 'EVALUATOR_NOMINATION'])} evaluator nominations/confirmations."
        )

        return CohortAnalysisResult(
            cohort_id=request.cohort_id,
            cohort_name="Training Cohort Batch" if request.cohort_id else "All Active Cohorts",
            batch_code=request.batch_code or "",
            candidate_count=candidate_count,
            analyzed_emails_count=len(emails),
            findings=findings,
            email_citations=citations[:15],
            summary=summary,
            status="WARNING" if any(f.severity in ("WARNING", "CRITICAL") for f in findings) else "COMPLETED",
            last_synced_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ"),
        )
