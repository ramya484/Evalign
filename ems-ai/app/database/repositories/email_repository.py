"""EmailRepository – all DB operations for Outlook email/attachment data."""
from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.outlook_attachment import OutlookAttachment
from app.database.models.outlook_email import OutlookEmail
from app.utils.logging import get_logger

logger = get_logger(__name__)

class EmailRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_email(self, email_data: dict) -> OutlookEmail:
        existing = await self.get_by_message_id(email_data.get("message_id",""))
        if existing:
            return existing
        email = OutlookEmail(**{k:v for k,v in email_data.items() if hasattr(OutlookEmail,k)})
        self.session.add(email)
        await self.session.flush()
        return email

    async def save_attachment(self, att_data: dict) -> OutlookAttachment:
        att = OutlookAttachment(**{k:v for k,v in att_data.items() if hasattr(OutlookAttachment,k)})
        self.session.add(att)
        await self.session.flush()
        return att

    async def email_exists(self, message_id: str) -> bool:
        r = await self.session.execute(select(OutlookEmail.email_id).where(OutlookEmail.message_id==message_id))
        return r.scalar_one_or_none() is not None

    async def get_by_message_id(self, message_id: str) -> Optional[OutlookEmail]:
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.message_id==message_id))
        return r.scalar_one_or_none()

    async def get_by_id(self, email_id: int) -> Optional[OutlookEmail]:
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.email_id==email_id))
        return r.scalar_one_or_none()

    async def search_by_sender(self, sender: str, limit: int = 20) -> List[OutlookEmail]:
        limit = min(limit,100)
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.sender_email.ilike(f"%{sender}%")).order_by(OutlookEmail.received_date.desc()).limit(limit))
        return list(r.scalars().all())

    async def search_by_recipient(self, recipient: str, limit: int = 20) -> List[OutlookEmail]:
        limit = min(limit,100)
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.recipient_emails.ilike(f"%{recipient}%")).order_by(OutlookEmail.received_date.desc()).limit(limit))
        return list(r.scalars().all())

    async def search_by_subject(self, subject: str, limit: int = 20) -> List[OutlookEmail]:
        limit = min(limit,100)
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.subject.ilike(f"%{subject}%")).order_by(OutlookEmail.received_date.desc()).limit(limit))
        return list(r.scalars().all())

    async def search_by_date_range(self, from_dt: datetime, to_dt: datetime, limit: int = 50) -> List[OutlookEmail]:
        limit = min(limit,100)
        r = await self.session.execute(select(OutlookEmail).where(OutlookEmail.received_date.between(from_dt,to_dt)).order_by(OutlookEmail.received_date.desc()).limit(limit))
        return list(r.scalars().all())

    async def search_by_keywords(self, keywords: List[str], limit: int = 20) -> List[OutlookEmail]:
        limit = min(limit,100)
        conditions = []
        for kw in keywords[:5]:
            safe = kw.replace("%","").replace("_","")[:50]
            conditions += [OutlookEmail.subject.ilike(f"%{safe}%"), OutlookEmail.body_text.ilike(f"%{safe}%")]
        r = await self.session.execute(select(OutlookEmail).where(or_(*conditions)).order_by(OutlookEmail.received_date.desc()).limit(limit))
        return list(r.scalars().all())

    async def get_attachments_by_email(self, email_id: int) -> List[OutlookAttachment]:
        r = await self.session.execute(select(OutlookAttachment).where(OutlookAttachment.email_id==email_id))
        return list(r.scalars().all())
