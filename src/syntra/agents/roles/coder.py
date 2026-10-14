"""Coder agent specialization for code implementation and targeted refactoring."""

from syntra.agents.base import BaseAgent
from syntra.agents.tools import ToolRegistry
from syntra.llm.client import BaseLLMClient
from syntra.llm.prompts import CODER_SYSTEM_PROMPT


class CoderAgent(BaseAgent):
    """Specialized in writing code, editing files, and implementing features."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="coder",
            llm_client=llm_client,
            tools=tools,
            system_prompt=CODER_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
