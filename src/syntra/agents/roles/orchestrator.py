"""Orchestrator agent specialization for supervising multi-agent workflows."""

from syntra.agents.base import BaseAgent
from syntra.agents.tools import ToolRegistry
from syntra.llm.client import BaseLLMClient
from syntra.llm.prompts import COORDINATOR_SYSTEM_PROMPT


class OrchestratorAgent(BaseAgent):
    """Specialized in supervising agents, monitoring progress, and guiding workflow transitions."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="coordinator",
            llm_client=llm_client,
            tools=tools,
            system_prompt=COORDINATOR_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
