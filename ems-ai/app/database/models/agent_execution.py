"""AgentExecution ORM model."""
from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func
from app.database.connection import Base

class AgentExecution(Base):
    __tablename__ = "agent_execution_log"
    execution_id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(100), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    cohort_id = Column(Integer, nullable=True)
    round_type = Column(String(20), nullable=True)
    status = Column(String(20), default="PENDING")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_exec_workflow","workflow_id"),Index("idx_exec_agent","agent_name"),Index("idx_exec_status","status"),)
