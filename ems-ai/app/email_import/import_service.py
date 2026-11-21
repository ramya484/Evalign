"""
EmailImportService  orchestrates importing emails from CSV / EML into the Outlook duplicate DB.
"""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from app.database.connection import AsyncSessionLocal
from app.database.models.sync_log import OutlookSyncLog
from app.database.repositories.email_repository import EmailRepository
from app.email_import.parsers.csv_parser import CSVEmailParser
from app.email_import.parsers.eml_parser import EMLEmailParser
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EmailImportService:
    """Imports emails from CSV or EML files into the shared Outlook duplicate database."""

    def __init__(self):
        self.csv_parser = CSVEmailParser()
        self.eml_parser = EMLEmailParser()

    async def import_from_csv(self, file_path: str) -> Dict[str, Any]:
        """Import emails from a CSV file."""
        sync_id = await self._start_sync_log("MANUAL_IMPORT", file_path)
        imported, skipped, failed = 0, 0, 0
        try:
            emails = self.csv_parser.parse(file_path)
            async with AsyncSessionLocal() as session:
                repo = EmailRepository(session)
                for ed in emails:
                    try:
                        existing = await repo.email_exists(ed.get("message_id",""))
                        if existing:
                            skipped += 1
                        else:
                            await repo.save_email(ed)
                            imported += 1
                    except Exception as exc:
                        logger.warning("Failed to save email: %s", exc)
                        failed += 1
                await session.commit()
        except Exception as exc:
            await self._finish_sync_log(sync_id, "FAILED", imported, failed, str(exc))
            return {"imported": imported, "skipped": skipped, "failed": failed, "error": str(exc)}

        await self._finish_sync_log(sync_id, "COMPLETED", imported, failed)
        logger.info("CSV import done: imported=%d skipped=%d failed=%d", imported, skipped, failed)
        return {"imported": imported, "skipped": skipped, "failed": failed}

    async def import_from_eml(self, file_path: str) -> Dict[str, Any]:
        """Import a single .eml file."""
        sync_id = await self._start_sync_log("MANUAL_IMPORT", file_path)
        try:
            email_data = self.eml_parser.parse(file_path)
            attachments = email_data.pop("_attachments", [])
            async with AsyncSessionLocal() as session:
                repo = EmailRepository(session)
                if await repo.email_exists(email_data.get("message_id","")):
                    await self._finish_sync_log(sync_id, "COMPLETED", 0, 0)
                    return {"imported": 0, "skipped": 1, "failed": 0}
                saved = await repo.save_email(email_data)
                for att in attachments:
                    att["email_id"] = saved.email_id
                    await repo.save_attachment(att)
                await session.commit()
        except Exception as exc:
            await self._finish_sync_log(sync_id, "FAILED", 0, 1, str(exc))
            return {"imported": 0, "skipped": 0, "failed": 1, "error": str(exc)}
        await self._finish_sync_log(sync_id, "COMPLETED", 1, 0)
        return {"imported": 1, "skipped": 0, "failed": 0}

    async def import_from_directory(self, dir_path: str) -> Dict[str, Any]:
        """Scan directory for .eml and .csv files and import all."""
        total = {"imported": 0, "skipped": 0, "failed": 0}
        p = Path(dir_path)
        for csv_file in p.rglob("*.csv"):
            r = await self.import_from_csv(str(csv_file))
            for k in total: total[k] += r.get(k, 0)
        for eml_file in p.rglob("*.eml"):
            r = await self.import_from_eml(str(eml_file))
            for k in total: total[k] += r.get(k, 0)
        logger.info("Directory import done: %s", total)
        return total

    async def _start_sync_log(self, sync_type: str, source_file: str) -> int:
        async with AsyncSessionLocal() as session:
            rec = OutlookSyncLog(sync_type=sync_type, started_at=datetime.utcnow(), status="RUNNING", source_file=source_file)
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            return rec.sync_id

    async def _finish_sync_log(self, sync_id: int, status: str, imported: int, failed: int, error: str = None):
        async with AsyncSessionLocal() as session:
            rec = await session.get(OutlookSyncLog, sync_id)
            if rec:
                rec.status = status
                rec.completed_at = datetime.utcnow()
                rec.records_imported = imported
                rec.records_failed = failed
                rec.error_details = error
                await session.commit()
