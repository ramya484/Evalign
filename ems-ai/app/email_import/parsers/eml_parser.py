"""Parse .eml files using Python standard library email module."""
from __future__ import annotations
import email, email.policy, uuid, json
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, Any, List
from app.utils.logging import get_logger

logger = get_logger(__name__)

class EMLEmailParser:
    """Parse a single .eml file into a normalized email dict."""

    def parse(self, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"EML file not found: {file_path}")
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)
        return self._extract(msg, str(file_path))

    def parse_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        results = []
        for eml_file in Path(dir_path).rglob("*.eml"):
            try:
                results.append(self.parse(str(eml_file)))
            except Exception as exc:
                logger.warning("Failed to parse %s: %s", eml_file, exc)
        return results

    def _extract(self, msg, source_path: str) -> Dict[str, Any]:
        message_id = msg.get("Message-ID","").strip() or f"<eml-{uuid.uuid4()}@ems-import.local>"
        sender = msg.get("From","").strip()
        to_field = msg.get("To","")
        cc_field = msg.get("Cc","")
        subject = msg.get("Subject","").strip()

        # Date parsing
        received_date = None
        date_str = msg.get("Date","")
        if date_str:
            try:
                received_date = parsedate_to_datetime(date_str).replace(tzinfo=None)
            except Exception:
                pass

        # Body extraction
        body_text, body_html = "", ""
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                disp = str(part.get("Content-Disposition",""))
                if "attachment" in disp:
                    attachments.append({
                        "file_name": part.get_filename("attachment"),
                        "content_type": ct,
                        "file_size_bytes": len(part.get_payload(decode=True) or b""),
                    })
                elif ct == "text/plain" and not body_text:
                    body_text = part.get_content() or ""
                elif ct == "text/html" and not body_html:
                    body_html = part.get_content() or ""
        else:
            ct = msg.get_content_type()
            if ct == "text/html":
                body_html = msg.get_content() or ""
            else:
                body_text = msg.get_content() or ""

        return {
            "message_id": message_id,
            "sender_email": sender,
            "recipient_emails": json.dumps([to_field]) if to_field else None,
            "cc_emails": cc_field or None,
            "subject": subject,
            "body_text": body_text[:65535] if body_text else None,
            "body_html": body_html[:65535] if body_html else None,
            "received_date": received_date,
            "has_attachments": len(attachments) > 0,
            "folder_name": "INBOX",
            "data_source": "MANUAL_IMPORT",
            "_attachments": attachments,
        }
