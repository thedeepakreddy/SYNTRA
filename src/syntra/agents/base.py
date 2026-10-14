"""Base agent abstraction, ReAct reasoning loop, and lifecycle management."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from syntra.agents.context import AgentContext
from syntra.agents.tools import ToolRegistry
from syntra.core.config import get_settings
from syntra.core.events import Event, EventType, get_event_bus
from syntra.core.exceptions import AgentMaxStepsExceededError
from syntra.llm.client import BaseLLMClient
from syntra.llm.models import LLMMessage, MessageRole, ToolCall
from syntra.llm.prompts import get_role_prompt
from syntra.llm.router import ModelRouter

logger = logging.getLogger(__name__)


@dataclass
class AgentStepResult:
    """Outcome of a single agent step."""

    is_complete: bool
    thought: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_outputs: list[dict[str, Any]] = field(default_factory=list)
    final_output: str | None = None
    requires_checkpoint: bool = False
    checkpoint_details: dict[str, Any] | None = None


@dataclass
class AgentExecutionResult:
    """Final summary of an agent's task execution."""

    agent_id: str
    role: str
    success: bool
    output: str
    steps_taken: int
    tool_calls_count: int


class BaseAgent:
    """Foundational agent executing the ReAct (Reasoning + Acting) loop."""

    def __init__(
        self,
        role: str,
        llm_client: BaseLLMClient,
        tools: ToolRegistry | None = None,
        system_prompt: str | None = None,
        agent_id: str | None = None,
        session_id: str = "default",
    ) -> None:
        self.role = role.lower()
        self.agent_id = agent_id or f"{self.role}-{uuid.uuid4().hex[:8]}"
        self.session_id = session_id
        self.llm_client = llm_client
        self.tools = tools or ToolRegistry()
        self.system_prompt = system_prompt or get_role_prompt(self.role)
        self.context = AgentContext(session_id=self.session_id, agent_id=self.agent_id, role=self.role)

    def _build_llm_messages(self) -> list[LLMMessage]:
        """Construct prompt message sequence including system prompt and memory."""
        memory_dump = self.context.memory.dump_context()
        sys_content = self.system_prompt
        if memory_dump:
            sys_content += f"\n\n{memory_dump}"

        messages = [LLMMessage(role=MessageRole.SYSTEM, content=sys_content)]
        messages.extend(self.context.history)
        return messages

    async def step(self) -> AgentStepResult:
        """Perform one reasoning and action cycle."""
        messages = self._build_llm_messages()
        model = ModelRouter.resolve_model(self.role)
        tool_defs = self.tools.get_definitions()

        await get_event_bus().publish(
            Event(
                type=EventType.AGENT_STEP_STARTED,
                session_id=self.session_id,
                agent_id=self.agent_id,
                agent_role=self.role,
                data={"messages_count": len(messages)},
            )
        )

        response = await self.llm_client.generate(
            messages=messages,
            model=model,
            tools=tool_defs if tool_defs else None,
            session_id=self.session_id,
            agent_id=self.agent_id,
            agent_role=self.role,
        )

        thought_text = response.text
        if thought_text:
            await get_event_bus().publish(
                Event(
                    type=EventType.AGENT_THOUGHT,
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    data={"thought": thought_text},
                )
            )

        # Record assistant response in history
        self.context.add_assistant_message(
            content=thought_text,
            tool_calls=response.tool_calls,
        )

        # Check if agent issued tool calls
        if not response.tool_calls:
            # No tool call: agent has finished reasoning or reached conclusion
            return AgentStepResult(
                is_complete=True,
                thought=thought_text,
                final_output=thought_text,
            )

        # Execute tool calls
        tool_outputs = []
        for tc in response.tool_calls:
            await get_event_bus().publish(
                Event(
                    type=EventType.AGENT_TOOL_CALL_STARTED,
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    data={"tool": tc.name, "arguments": tc.arguments},
                )
            )

            output = await self.tools.execute(tc.name, tc.arguments)
            tool_outputs.append({"name": tc.name, "output": output})

            await get_event_bus().publish(
                Event(
                    type=EventType.AGENT_TOOL_CALL_COMPLETED,
                    session_id=self.session_id,
                    agent_id=self.agent_id,
                    agent_role=self.role,
                    data={"tool": tc.name, "output": str(output)[:500]},
                )
            )

            self.context.add_tool_result(
                call_id=tc.id,
                tool_name=tc.name,
                result=output,
            )

        return AgentStepResult(
            is_complete=False,
            thought=thought_text,
            tool_calls=response.tool_calls,
            tool_outputs=tool_outputs,
        )

    async def run_task(self, task: str, max_steps: int | None = None) -> AgentExecutionResult:
        """Run task until completion or max steps limit."""
        settings = get_settings()
        limit = max_steps or settings.max_agent_steps
        self.context.task = task
        self.context.add_user_message(task)

        steps_taken = 0
        total_tools_called = 0
        final_output = ""

        while steps_taken < limit:
            steps_taken += 1
            step_result = await self.step()
            total_tools_called += len(step_result.tool_calls)

            if step_result.is_complete:
                final_output = step_result.final_output or step_result.thought
                break
        else:
            raise AgentMaxStepsExceededError(
                f"Agent '{self.role}' exceeded max step limit of {limit} without concluding."
            )

        return AgentExecutionResult(
            agent_id=self.agent_id,
            role=self.role,
            success=True,
            output=final_output,
            steps_taken=steps_taken,
            tool_calls_count=total_tools_called,
        )
