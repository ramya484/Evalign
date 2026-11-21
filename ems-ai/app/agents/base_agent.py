"""Base class for all EMS AI agents."""
from __future__ import annotations
import json, logging
from abc import ABC, abstractmethod
from pydantic import BaseModel
from app.utils.logging import get_logger

class BaseEMSAgent(ABC):
    def __init__(self, llm, tools: list):
        self.llm = llm
        self.tools = tools
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def run(self, input_data: BaseModel) -> BaseModel:
        """Execute the agent and return structured output."""

    def _tools_dict(self) -> dict:
        return {t.name: t for t in self.tools}
