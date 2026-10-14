"""Tester agent specialization for automated testing and test execution."""

from syntra.agents.base import BaseAgent
from syntra.agents.tools import ToolRegistry
from syntra.llm.client import BaseLLMClient
from syntra.llm.prompts import TESTER_SYSTEM_PROMPT


class TesterAgent(BaseAgent):
    """Specialized in writing tests, running suites, and analyzing failure traces."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="tester",
            llm_client=llm_client,
            tools=tools,
            system_prompt=TESTER_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
