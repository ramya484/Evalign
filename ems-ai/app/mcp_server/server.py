"""
EMS Outlook MCP Server
Exposes 10 tools for the three AI agents to access the Outlook duplicate DB and EMS data.
Run with:  python -m app.mcp_server.server
"""
from mcp.server.fastmcp import FastMCP
from app.mcp_server.tools.email_tools import (
    search_emails, get_email_by_id, filter_by_sender,
    filter_by_recipient, search_by_subject, search_by_date_range,
)
from app.mcp_server.tools.attachment_tools import get_attachments, get_email_content
from app.mcp_server.tools.ems_tools import search_evaluator_data, get_ems_data
from app.utils.logging import get_logger

logger = get_logger(__name__)

mcp = FastMCP("EMS Outlook MCP Server")

# -- Register all 10 tools ------------------------------------------------------
mcp.tool()(search_emails)
mcp.tool()(get_email_by_id)
mcp.tool()(filter_by_sender)
mcp.tool()(filter_by_recipient)
mcp.tool()(search_by_subject)
mcp.tool()(search_by_date_range)
mcp.tool()(get_attachments)
mcp.tool()(get_email_content)
mcp.tool()(search_evaluator_data)
mcp.tool()(get_ems_data)

if __name__ == "__main__":
    logger.info("Starting EMS Outlook MCP Server…")
    mcp.run()
