"""Architect agent specialization for system and contract design."""

from syntra.agents.base import BaseAgent
from syntra.agents.tools import ToolRegistry
from syntra.llm.client import BaseLLMClient
from syntra.llm.prompts import ARCHITECT_SYSTEM_PROMPT


class ArchitectAgent(BaseAgent):
    """Specialized in system architecture, API contracts, and schema design."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="architect",
            llm_client=llm_client,
            tools=tools,
            system_prompt=ARCHITECT_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
