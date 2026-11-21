"""OutlookFolder ORM model."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from app.database.connection import Base

class OutlookFolder(Base):
    __tablename__ = "outlook_folders"
    folder_id = Column(Integer, primary_key=True, autoincrement=True)
    folder_name = Column(String(255), nullable=False)
    folder_type = Column(String(50), default="CUSTOM")
    parent_folder_id = Column(Integer, ForeignKey("outlook_folders.folder_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
