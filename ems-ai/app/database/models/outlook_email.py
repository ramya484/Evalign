"""OutlookEmail ORM model."""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, String, Text, func
from app.database.connection import Base

class OutlookEmail(Base):
    __tablename__ = "outlook_emails"
    email_id = Column(BigInteger, primary_key=True, autoincrement=True)
    message_id = Column(String(500), nullable=False, unique=True)
    sender_email = Column(String(255), nullable=False, index=True)
    recipient_emails = Column(Text)
    cc_emails = Column(Text)
    bcc_emails = Column(Text)
    subject = Column(String(1000), index=True)
    body_text = Column(Text)
    body_html = Column(Text)
    received_date = Column(DateTime, index=True)
    sent_date = Column(DateTime)
    folder_name = Column(String(255), default="INBOX")
    is_read = Column(Boolean, default=False)
    has_attachments = Column(Boolean, default=False)
    data_source = Column(String(50), default="MANUAL_IMPORT")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("idx_email_sender","sender_email"), Index("idx_email_received","received_date"),)
    def to_dict(self):
        return {"email_id":self.email_id,"message_id":self.message_id,"sender_email":self.sender_email,
                "recipient_emails":self.recipient_emails,"cc_emails":self.cc_emails,"subject":self.subject,
                "body_text":(self.body_text or "")[:500],"received_date":str(self.received_date) if self.received_date else None,
                "folder_name":self.folder_name,"is_read":self.is_read,"has_attachments":self.has_attachments,"data_source":self.data_source}
