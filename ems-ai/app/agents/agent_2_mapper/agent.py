"""
Agent 2  Evaluator Mapping Agent
Performs intelligent workload-balanced evaluator-to-candidate assignment.
"""
from __future__ import annotations
import json
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from app.agents.agent_2_mapper.schemas import MappingInput, MappingOutput
from app.agents.agent_2_mapper.prompts import SYSTEM_PROMPT
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
        """Get EMS data: candidates, shortlist, or mappings for a cohort.
        resource_type: candidates|shortlist|mappings. round_type: INTERIM|FINAL."""
        result = await get_ems_data(resource_type, cohort_id, round_type)
        return json.dumps(result)

    @tool
    async def tool_search_evaluator_data(cohort_id: int, availability_status: str = None) -> str:
        """Search evaluator availability data for a cohort."""
        result = await search_evaluator_data(cohort_id, availability_status=availability_status)
        return json.dumps(result)

    return [tool_get_ems_data, tool_search_evaluator_data]


class MappingAgent(BaseEMSAgent):
    """Agent 2: AI-powered evaluator-to-candidate mapping."""

    def __init__(self, llm):
        tools = _build_tools()
        super().__init__(llm, tools)
        prompt = PromptTemplate.from_template(REACT_TEMPLATE)
        agent = create_react_agent(llm, tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=15, handle_parsing_errors=True)

    async def run(self, input_data: MappingInput) -> MappingOutput:
        self.logger.info("Agent 2 starting: cohort=%d round=%s attempt=%d",
                         input_data.cohort_id, input_data.round_type, input_data.attempt)

        question = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Generate evaluator-to-candidate mappings for:\n"
            f"- Cohort ID: {input_data.cohort_id}\n"
            f"- Round: {input_data.round_type}\n"
            f"- Attempt: {input_data.attempt}\n"
            f"Return a complete MappingOutput JSON object."
        )

        try:
            result = await self.executor.ainvoke({"input": question})
            output_text = result.get("output", "{}")
            try:
                data = json.loads(output_text)
                return MappingOutput(**data)
            except Exception:
                self.logger.warning("Agent 2 output parse failed")
                return MappingOutput(
                    cohort_id=input_data.cohort_id,
                    round_type=input_data.round_type,
                    assignments=[],
                    unassigned_candidates=[],
                    summary="Agent output could not be parsed.",
                    workload_distribution={},
                )
        except Exception as exc:
            self.logger.error("Agent 2 failed: %s", exc)
            raise
