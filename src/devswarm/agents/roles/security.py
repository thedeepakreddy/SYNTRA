"""Security agent specialization for vulnerability analysis and auditing."""

from devswarm.agents.base import BaseAgent
from devswarm.agents.tools import ToolRegistry
from devswarm.llm.client import BaseLLMClient
from devswarm.llm.prompts import SECURITY_SYSTEM_PROMPT


class SecurityAgent(BaseAgent):
    """Specialized in auditing vulnerabilities, secrets leakage, and compliance."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="security",
            llm_client=llm_client,
            tools=tools,
            system_prompt=SECURITY_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
