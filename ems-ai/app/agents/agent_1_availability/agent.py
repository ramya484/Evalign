"""
Agent 1  Evaluator Availability Agent
Uses LangChain ReAct agent + MCP tools to detect evaluator OOO/leave from Outlook emails.
"""
from __future__ import annotations
import json
from typing import Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from app.agents.agent_1_availability.schemas import AvailabilityInput, AvailabilityOutput, EvaluatorAvailabilityResult
from app.agents.agent_1_availability.prompts import SYSTEM_PROMPT
from app.agents.base_agent import BaseEMSAgent
from app.mcp_server.tools.email_tools import filter_by_sender, search_by_subject, search_by_date_range, get_email_content
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _build_tools():
    @tool
    async def tool_filter_by_sender(sender_email: str, limit: int = 10) -> str:
        """Find emails sent from a specific evaluator email address."""
        result = await filter_by_sender(sender_email, limit)
        return json.dumps(result)

    @tool
    async def tool_search_by_subject(subject_query: str, limit: int = 10) -> str:
        """Search emails by subject. Use terms like 'out of office', 'OOO', 'leave', 'unavailable'."""
        result = await search_by_subject(subject_query, limit)
        return json.dumps(result)

    @tool
    async def tool_search_by_date_range(from_date: str, to_date: str, limit: int = 20) -> str:
        """Find emails received in a date range (YYYY-MM-DD format)."""
        result = await search_by_date_range(from_date, to_date, limit)
        return json.dumps(result)

    @tool
    async def tool_get_email_content(email_id: int, format: str = "text") -> str:
        """Get the full body content of an email by ID."""
        result = await get_email_content(email_id, format)
        return json.dumps(result)

    return [tool_filter_by_sender, tool_search_by_subject, tool_search_by_date_range, tool_get_email_content]


REACT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


class AvailabilityAgent(BaseEMSAgent):
    """Agent 1: Checks Outlook emails to determine evaluator availability."""

    def __init__(self, llm):
        tools = _build_tools()
        super().__init__(llm, tools)
        prompt = PromptTemplate.from_template(REACT_TEMPLATE)
        agent = create_react_agent(llm, tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10, handle_parsing_errors=True)

    async def run(self, input_data: AvailabilityInput) -> AvailabilityOutput:
        self.logger.info("Agent 1 starting: cohort=%d period=%s to %s evaluators=%d",
                         input_data.cohort_id, input_data.interview_from,
                         input_data.interview_to, len(input_data.evaluator_emails))

        question = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Check availability for evaluators: {input_data.evaluator_emails}\n"
            f"Interview period: {input_data.interview_from} to {input_data.interview_to}\n"
            f"Cohort ID: {input_data.cohort_id}\n"
            f"Return a JSON AvailabilityOutput object."
        )

        try:
            result = await self.executor.ainvoke({"input": question})
            output_text = result.get("output", "{}")

            # Try to parse structured output
            try:
                data = json.loads(output_text)
                return AvailabilityOutput(**data)
            except Exception:
                # Fallback: assume all available
                self.logger.warning("Agent 1 output parse failed, returning default availability")
                results = [EvaluatorAvailabilityResult(
                    evaluator_email=e, evaluator_name=e, is_available=True
                ) for e in input_data.evaluator_emails]
                return AvailabilityOutput(
                    cohort_id=input_data.cohort_id,
                    interview_period=f"{input_data.interview_from} to {input_data.interview_to}",
                    results=results,
                    summary="Could not parse agent output; defaulting to all available.",
                    emails_analyzed=0,
                )
        except Exception as exc:
            self.logger.error("Agent 1 failed: %s", exc)
            raise
