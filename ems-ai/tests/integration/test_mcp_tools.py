"""Integration tests for MCP tools (with mocked DB and EMS API)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestEmailTools:
    @pytest.mark.asyncio
    async def test_search_emails_returns_results(self):
        with patch("app.mcp_server.tools.email_tools.AsyncSessionLocal") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_email = MagicMock()
            mock_email.to_dict.return_value = {"email_id": 1, "subject": "OOO Test", "sender_email": "a@b.com"}
            mock_repo.search_by_keywords.return_value = [mock_email]
            with patch("app.mcp_server.tools.email_tools.EmailRepository", return_value=mock_repo):
                from app.mcp_server.tools.email_tools import search_emails
                result = await search_emails("OOO leave", limit=10)
                assert "emails" in result
                assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_email_by_id_not_found(self):
        with patch("app.mcp_server.tools.email_tools.AsyncSessionLocal") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            with patch("app.mcp_server.tools.email_tools.EmailRepository", return_value=mock_repo):
                from app.mcp_server.tools.email_tools import get_email_by_id
                result = await get_email_by_id(9999)
                assert result.get("code") == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_filter_by_sender(self):
        with patch("app.mcp_server.tools.email_tools.AsyncSessionLocal") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.search_by_sender.return_value = []
            with patch("app.mcp_server.tools.email_tools.EmailRepository", return_value=mock_repo):
                from app.mcp_server.tools.email_tools import filter_by_sender
                result = await filter_by_sender("sender@test.com")
                assert "emails" in result
                assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_search_by_date_range_invalid_date(self):
        from app.mcp_server.tools.email_tools import search_by_date_range
        result = await search_by_date_range("not-a-date", "2024-12-01")
        assert result.get("code") == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_search_emails_empty_keywords(self):
        from app.mcp_server.tools.email_tools import search_emails
        result = await search_emails("   ")
        assert result.get("code") == "VALIDATION_ERROR"


class TestAttachmentTools:
    @pytest.mark.asyncio
    async def test_get_attachments_email_not_found(self):
        with patch("app.mcp_server.tools.attachment_tools.AsyncSessionLocal") as mock_ctx:
            mock_session = AsyncMock()
            mock_ctx.return_value.__aenter__.return_value = mock_session
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            with patch("app.mcp_server.tools.attachment_tools.EmailRepository", return_value=mock_repo):
                from app.mcp_server.tools.attachment_tools import get_attachments
                result = await get_attachments(9999)
                assert result.get("code") == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_email_content_invalid_format(self):
        from app.mcp_server.tools.attachment_tools import get_email_content
        result = await get_email_content(1, format="xml")
        assert result.get("code") == "VALIDATION_ERROR"


class TestEMSTools:
    @pytest.mark.asyncio
    async def test_get_ems_data_invalid_resource_type(self):
        from app.mcp_server.tools.ems_tools import get_ems_data
        result = await get_ems_data("invalid_type")
        assert result.get("code") == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_get_ems_data_missing_cohort_id(self):
        from app.mcp_server.tools.ems_tools import get_ems_data
        result = await get_ems_data("candidates", cohort_id=None)
        assert result.get("code") == "VALIDATION_ERROR"
