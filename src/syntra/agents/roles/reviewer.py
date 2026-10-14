"""Reviewer agent specialization for code review and quality verification."""

from syntra.agents.base import BaseAgent
from syntra.agents.tools import ToolRegistry
from syntra.llm.client import BaseLLMClient
from syntra.llm.prompts import REVIEWER_SYSTEM_PROMPT


class ReviewerAgent(BaseAgent):
    """Specialized in code diff inspection, architectural compliance, and security review."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="reviewer",
            llm_client=llm_client,
            tools=tools,
            system_prompt=REVIEWER_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
