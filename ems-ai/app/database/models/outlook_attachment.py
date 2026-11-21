"""OutlookAttachment ORM model."""
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, func
from app.database.connection import Base

class OutlookAttachment(Base):
    __tablename__ = "outlook_attachments"
    attachment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    email_id = Column(BigInteger, ForeignKey("outlook_emails.email_id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(500))
    file_type = Column(String(100))
    content_type = Column(String(255))
    file_size_bytes = Column(BigInteger)
    file_path = Column(String(1000))
    created_at = Column(DateTime, server_default=func.now())
    def to_dict(self):
        return {"attachment_id":self.attachment_id,"email_id":self.email_id,"file_name":self.file_name,
                "file_type":self.file_type,"content_type":self.content_type,"file_size_bytes":self.file_size_bytes}
