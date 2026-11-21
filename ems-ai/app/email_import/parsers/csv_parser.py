"""Parse CSV email exports into normalized dicts for import."""
from __future__ import annotations
import csv, uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Column aliases  maps CSV header -> canonical field
_FIELD_MAP = {
    "subject":"subject","Subject":"subject","SUBJECT":"subject",
    "from":"sender_email","From":"sender_email","From:":"sender_email","sender":"sender_email","Sender":"sender_email",
    "to":"recipient_emails","To":"recipient_emails","To:":"recipient_emails","recipient":"recipient_emails",
    "cc":"cc_emails","CC":"cc_emails","Cc":"cc_emails",
    "date":"received_date","Date":"received_date","Date:":"received_date","received_date":"received_date",
    "body":"body_text","Body":"body_text","body_text":"body_text","Body Text":"body_text",
    "message_id":"message_id","Message-ID":"message_id","MessageId":"message_id",
    "folder":"folder_name","Folder":"folder_name",
}

def _parse_date(val: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M", "%m/%d/%Y"):
        try:
            return datetime.strptime(val.strip(), fmt)
        except (ValueError, AttributeError):
            pass
    return None

class CSVEmailParser:
    """Parse a CSV file of exported emails into a list of normalized email dicts."""

    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        emails = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    email = self._map_row(row)
                    if email:
                        emails.append(email)
                except Exception as exc:
                    logger.warning("Row %d parse error: %s", row_num, exc)
        logger.info("CSV parsed: %d emails from %s", len(emails), file_path)
        return emails

    def _map_row(self, row: dict) -> Dict[str, Any] | None:
        mapped: Dict[str, Any] = {}
        for col, val in row.items():
            canonical = _FIELD_MAP.get(col.strip())
            if canonical and val and val.strip():
                mapped[canonical] = val.strip()

        if not mapped.get("sender_email") and not mapped.get("subject"):
            return None  # skip empty rows

        # Generate synthetic message_id if missing
        if not mapped.get("message_id"):
            mapped["message_id"] = f"<csv-import-{uuid.uuid4()}@ems-import.local>"

        if "received_date" in mapped:
            mapped["received_date"] = _parse_date(mapped["received_date"])

        mapped.setdefault("folder_name", "INBOX")
        mapped["data_source"] = "MANUAL_IMPORT"
        return mapped
