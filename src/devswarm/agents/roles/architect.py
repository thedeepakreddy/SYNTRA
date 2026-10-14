"""Architect agent specialization for system and contract design."""

from devswarm.agents.base import BaseAgent
from devswarm.agents.tools import ToolRegistry
from devswarm.llm.client import BaseLLMClient
from devswarm.llm.prompts import ARCHITECT_SYSTEM_PROMPT


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
