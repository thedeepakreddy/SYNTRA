"""Planner agent specialization for task breakdown and dependency management."""

from devswarm.agents.base import BaseAgent
from devswarm.agents.tools import ToolRegistry
from devswarm.llm.client import BaseLLMClient
from devswarm.llm.prompts import PLANNER_SYSTEM_PROMPT


class PlannerAgent(BaseAgent):
    """Specialized in work breakdown, task DAG generation, and risk estimation."""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        super().__init__(
            role="planner",
            llm_client=llm_client,
            tools=tools,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            agent_id=agent_id,
            session_id=session_id,
        )
