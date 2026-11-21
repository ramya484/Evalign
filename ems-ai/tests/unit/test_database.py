"""Unit tests for database models, repositories, and email parsers."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestCSVEmailParser:
    def test_parse_valid_csv(self, tmp_path):
        from app.email_import.parsers.csv_parser import CSVEmailParser
        csv_content = "message_id,sender_email,recipient_email,subject,body_text,received_date\n"
        csv_content += "<test-001@test.com>,sender@test.com,recv@test.com,Test Subject,Test body,2024-11-20 09:00:00\n"
        f = tmp_path / "test.csv"
        f.write_text(csv_content)
        parser = CSVEmailParser()
        result = parser.parse(str(f))
        assert len(result) == 1
        assert result[0]["subject"] == "Test Subject"
        assert result[0]["sender_email"] == "sender@test.com"

    def test_parse_generates_message_id_when_missing(self, tmp_path):
        from app.email_import.parsers.csv_parser import CSVEmailParser
        csv_content = "sender_email,subject,body_text,received_date\n"
        csv_content += "sender@test.com,No ID Email,body,2024-11-20\n"
        f = tmp_path / "test2.csv"
        f.write_text(csv_content)
        parser = CSVEmailParser()
        result = parser.parse(str(f))
        assert len(result) == 1
        assert result[0]["message_id"].startswith("<csv-import-")

    def test_parse_missing_file_raises(self):
        from app.email_import.parsers.csv_parser import CSVEmailParser
        parser = CSVEmailParser()
        with pytest.raises(FileNotFoundError):
            parser.parse("/nonexistent/path.csv")


class TestEMLEmailParser:
    def test_parse_eml_file(self, tmp_path):
        from app.email_import.parsers.eml_parser import EMLEmailParser
        eml_content = (
            "From: sender@test.com\n"
            "To: recv@test.com\n"
            "Subject: Test EML\n"
            "Date: Thu, 21 Nov 2024 09:00:00 +0000\n"
            "Message-ID: <eml-test-001@test.com>\n"
            "Content-Type: text/plain\n\n"
            "This is the email body."
        )
        f = tmp_path / "test.eml"
        f.write_bytes(eml_content.encode())
        parser = EMLEmailParser()
        result = parser.parse(str(f))
        assert result["subject"] == "Test EML"
        assert result["sender_email"] == "sender@test.com"
        assert result["message_id"] == "<eml-test-001@test.com>"
        assert "email body" in (result["body_text"] or "")


class TestEmailRepository:
    @pytest.mark.asyncio
    async def test_save_email_new(self):
        from app.database.repositories.email_repository import EmailRepository
        mock_session = AsyncMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        repo = EmailRepository(mock_session)
        email_data = {
            "message_id": "<new-001@test.com>",
            "sender_email": "sender@test.com",
            "subject": "Test",
            "body_text": "Body",
            "folder_name": "INBOX",
        }
        # Test skips when message_id exists
        repo.email_exists = AsyncMock(return_value=False)
        repo.get_by_message_id = AsyncMock(return_value=None)
        # Should add to session
        result = await repo.save_email(email_data)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_email_duplicate_skipped(self):
        from app.database.repositories.email_repository import EmailRepository
        from app.database.models.outlook_email import OutlookEmail
        mock_session = AsyncMock()
        existing = MagicMock(spec=OutlookEmail)
        existing.message_id = "<existing@test.com>"
        repo = EmailRepository(mock_session)
        repo.get_by_message_id = AsyncMock(return_value=existing)
        result = await repo.save_email({"message_id": "<existing@test.com>"})
        mock_session.add.assert_not_called()
        assert result == existing


class TestAgentSchemas:
    def test_availability_input_valid(self):
        from app.agents.agent_1_availability.schemas import AvailabilityInput
        inp = AvailabilityInput(
            cohort_id=1,
            interview_from="2024-12-01",
            interview_to="2024-12-05",
            evaluator_emails=["e@test.com"]
        )
        assert inp.cohort_id == 1

    def test_mapping_input_valid(self):
        from app.agents.agent_2_mapper.schemas import MappingInput
        inp = MappingInput(cohort_id=1, round_type="INTERIM", attempt=1)
        assert inp.round_type == "INTERIM"

    def test_validation_input_valid(self):
        from app.agents.agent_3_validator.schemas import ValidationInput, ProposedAssignment
        inp = ValidationInput(
            cohort_id=1,
            proposed_assignments=[
                ProposedAssignment(candidate_id=1, candidate_name="Test", evaluator_id=1,
                                   evaluator_name="Eval", round_type="INTERIM", attempt=1)
            ]
        )
        assert len(inp.proposed_assignments) == 1
