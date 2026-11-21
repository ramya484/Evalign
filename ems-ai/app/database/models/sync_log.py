"""OutlookSyncLog ORM model."""
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.database.connection import Base

class OutlookSyncLog(Base):
    __tablename__ = "outlook_sync_log"
    sync_id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="RUNNING")
    records_imported = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_details = Column(Text, nullable=True)
    source_file = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
