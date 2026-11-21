"""MCP Attachment Tools – 2 tools for attachments and email body content."""
from app.database.connection import AsyncSessionLocal
from app.database.repositories.email_repository import EmailRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_attachments(email_id: int) -> dict:
    """Get attachment metadata for a specific email (no binary data returned).
    Args: email_id (int). Returns: {attachments: [...], count: int}"""
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            email = await repo.get_by_id(int(email_id))
            if not email:
                return {"error": f"Email {email_id} not found", "code": "NOT_FOUND"}
            atts = await repo.get_attachments_by_email(int(email_id))
            return {"attachments": [a.to_dict() for a in atts], "count": len(atts)}
    except Exception as exc:
        logger.error("get_attachments error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}


async def get_email_content(email_id: int, format: str = "text") -> dict:
    """Get the full body content of an email.
    Args: email_id (int), format (str): 'text' or 'html'. Returns: {email_id, subject, content, format}"""
    if format not in ("text", "html"):
        return {"error": "format must be 'text' or 'html'", "code": "VALIDATION_ERROR"}
    try:
        async with AsyncSessionLocal() as session:
            repo = EmailRepository(session)
            email = await repo.get_by_id(int(email_id))
            if not email:
                return {"error": f"Email {email_id} not found", "code": "NOT_FOUND"}
            content = email.body_html if format == "html" else email.body_text
            return {"email_id": email.email_id, "subject": email.subject,
                    "content": content or "", "format": format}
    except Exception as exc:
        logger.error("get_email_content error: %s", exc)
        return {"error": str(exc), "code": "TOOL_ERROR"}
