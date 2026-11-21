"""
MCP Email Tools  6 tools for searching/retrieving Outlook emails.
All tools access the DB through EmailRepository only (no raw SQL exposed).
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import Optional

from app.database.connection import AsyncSessionLocal
from app.database.repositories.email_repository import EmailRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _safe_str(val: str, max_len: int = 100) -> str:
    return str(val).replace("%", "").replace("_", " ")[:max_len].strip()


async def search_emails(keywords: str, limit: int = 20) -> dict:
    """Search Outlook emails by keywords in subject and body.
    Args: keywords (str): space-separated terms. limit (int): max results (capped at 100).
    Returns: {emails: [...], total: int, query: str}"""
    limit = max(1, min(int(limit), 100))
    kw_list = [_safe_str(k) for k in keywords.split() if k.strip()][:5]
    if not kw_list:
        return {"error": "No valid keywords provided", "code": "VALIDATION_ERROR"}
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            emails = await repo.search_by_keywords(kw_list, limit)
            return {"emails": [e.to_dict() for e in emails], "total": len(emails), "query": keywords}
    except Exception as exc:
        logger.error("search_emails error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def get_email_by_id(email_id: int) -> dict:
    """Retrieve complete email details by ID.
    Args: email_id (int). Returns: full email record or error."""
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            email = await repo.get_by_id(int(email_id))
            if not email:
                return {"error": f"Email {email_id} not found", "code": "NOT_FOUND"}
            return email.to_dict()
    except Exception as exc:
        logger.error("get_email_by_id error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def filter_by_sender(sender_email: str, limit: int = 20) -> dict:
    """Find emails from a specific sender (partial match).
    Args: sender_email (str), limit (int). Returns: {emails: [...], total: int}"""
    limit = max(1, min(int(limit), 100))
    safe_sender = _safe_str(sender_email, 255)
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            emails = await repo.search_by_sender(safe_sender, limit)
            return {"emails": [e.to_dict() for e in emails], "total": len(emails)}
    except Exception as exc:
        logger.error("filter_by_sender error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def filter_by_recipient(recipient_email: str, limit: int = 20) -> dict:
    """Find emails sent to a specific recipient.
    Args: recipient_email (str), limit (int). Returns: {emails: [...], total: int}"""
    limit = max(1, min(int(limit), 100))
    safe = _safe_str(recipient_email, 255)
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            emails = await repo.search_by_recipient(safe, limit)
            return {"emails": [e.to_dict() for e in emails], "total": len(emails)}
    except Exception as exc:
        logger.error("filter_by_recipient error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def search_by_subject(subject_query: str, limit: int = 20) -> dict:
    """Search emails by subject line.
    Args: subject_query (str), limit (int). Returns: {emails: [...], total: int}"""
    limit = max(1, min(int(limit), 100))
    safe = _safe_str(subject_query, 500)
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            emails = await repo.search_by_subject(safe, limit)
            return {"emails": [e.to_dict() for e in emails], "total": len(emails)}
    except Exception as exc:
        logger.error("search_by_subject error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def search_by_date_range(from_date: str, to_date: str, limit: int = 50) -> dict:
    """Find emails received within a date range.
    Args: from_date (str YYYY-MM-DD), to_date (str YYYY-MM-DD), limit (int). Returns: {emails: [...], total: int}"""
    limit = max(1, min(int(limit), 100))
    try:
        from_dt = datetime.strptime(from_date.strip(), "%Y-%m-%d")
        to_dt = datetime.strptime(to_date.strip(), "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError as exc:
        return {"error": f"Invalid date format: {exc}", "code": "VALIDATION_ERROR"}
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            emails = await repo.search_by_date_range(from_dt, to_dt, limit)
            return {"emails": [e.to_dict() for e in emails], "total": len(emails),
                    "date_range": {"from": from_date, "to": to_date}}
    except Exception as exc:
        logger.error("search_by_date_range error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}
