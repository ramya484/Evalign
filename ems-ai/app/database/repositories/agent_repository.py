"""AgentRepository  operations for agent_execution_log."""
from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.agent_execution import AgentExecution
from app.utils.logging import get_logger

logger = get_logger(__name__)

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_execution(self, workflow_id: str, agent_name: str, cohort_id=None, round_type=None, input_data=None) -> AgentExecution:
        rec = AgentExecution(workflow_id=workflow_id, agent_name=agent_name, cohort_id=cohort_id,
                             round_type=round_type, status="PENDING", started_at=datetime.utcnow(),
                             input_data=json.dumps(input_data) if input_data else None)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def mark_running(self, execution_id: int) -> None:
        rec = await self.session.get(AgentExecution, execution_id)
        if rec: rec.status="RUNNING"; rec.started_at=datetime.utcnow()

    async def mark_completed(self, execution_id: int, output_data: dict, tokens_used=None) -> None:
        rec = await self.session.get(AgentExecution, execution_id)
        if rec: rec.status="COMPLETED"; rec.completed_at=datetime.utcnow(); rec.output_data=json.dumps(output_data); rec.tokens_used=tokens_used

    async def mark_failed(self, execution_id: int, error: str) -> None:
        rec = await self.session.get(AgentExecution, execution_id)
        if rec: rec.status="FAILED"; rec.completed_at=datetime.utcnow(); rec.error_details=error

    async def get_by_workflow(self, workflow_id: str) -> List[AgentExecution]:
        r = await self.session.execute(select(AgentExecution).where(AgentExecution.workflow_id==workflow_id))
        return list(r.scalars().all())
