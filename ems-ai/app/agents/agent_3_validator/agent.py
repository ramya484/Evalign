"""
Agent 3 – Mapping Validation Agent
Validates proposed assignments against all 5 EMS business rules.
"""
from __future__ import annotations
import json
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from app.agents.agent_3_validator.schemas import ValidationInput, ValidationOutput
from app.agents.agent_3_validator.prompts import SYSTEM_PROMPT
from app.agents.base_agent import BaseEMSAgent
from app.mcp_server.tools.ems_tools import get_ems_data, search_evaluator_data
from app.utils.logging import get_logger

logger = get_logger(__name__)

REACT_TEMPLATE = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (Thought/Action/Action Input/Observation repeats)
Thought: I now know the final answer
Final Answer: the final answer

Begin!

Question: {input}
Thought: {agent_scratchpad}"""


def _build_tools():
    @tool
    async def tool_get_ems_data(resource_type: str, cohort_id: int = None, round_type: str = None) -> str:
        """Get EMS data for validation: shortlist, mappings, or candidates."""
        result = await get_ems_data(resource_type, cohort_id, round_type)
        return json.dumps(result)

    @tool
    async def tool_search_evaluator_data(cohort_id: int) -> str:
        """Get evaluator availability data for a cohort."""
        result = await search_evaluator_data(cohort_id)
        return json.dumps(result)

    return [tool_get_ems_data, tool_search_evaluator_data]


class ValidationAgent(BaseEMSAgent):
    """Agent 3: Validates proposed mappings against all 5 EMS business rules."""

    def __init__(self, llm):
        tools = _build_tools()
        super().__init__(llm, tools)
        prompt = PromptTemplate.from_template(REACT_TEMPLATE)
        agent = create_react_agent(llm, tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, handle_parsing_errors=True)

    async def run(self, input_data: ValidationInput) -> ValidationOutput:
        self.logger.info("Agent 3 starting: cohort=%d assignments=%d",
                         input_data.cohort_id, len(input_data.proposed_assignments))

        assignments_json = json.dumps([a.model_dump() for a in input_data.proposed_assignments], indent=2)
        question = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Validate the following proposed assignments for Cohort ID {input_data.cohort_id}:\n"
            f"{assignments_json}\n\n"
            f"Return a complete ValidationOutput JSON object."
        )

        try:
            result = await self.executor.ainvoke({"input": question})
            output_text = result.get("output", "{}")
            try:
                data = json.loads(output_text)
                return ValidationOutput(**data)
            except Exception:
                self.logger.warning("Agent 3 output parse failed")
                return ValidationOutput(
                    cohort_id=input_data.cohort_id,
                    total_assignments=len(input_data.proposed_assignments),
                    valid_count=0,
                    invalid_count=len(input_data.proposed_assignments),
                    validation_results=[],
                    can_proceed=False,
                    summary="Validation output could not be parsed. Manual review required.",
                )
        except Exception as exc:
            self.logger.error("Agent 3 failed: %s", exc)
            raise
