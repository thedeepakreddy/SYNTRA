"""SYNTRA Model Runtime Engine.

Connects Agent Context, Model Providers, Skills Registry, and MCP Gateway
with token accounting, cost calculation, timeout enforcement, tool execution,
and budget boundaries.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel

from syntra.core.telemetry import get_telemetry
from syntra.llm.config import UnknownCostPolicy, compute_token_cost, get_model_spec
from syntra.llm.context import AgentContextBuilder
from syntra.llm.exceptions import (
    ModelBudgetExceededError,
    ModelOutputValidationError,
    ModelPricingError,
    ModelProviderUnavailableError,
    ModelToolExecutionError,
)
from syntra.llm.models import LLMMessage, MessageRole, ToolCall, ToolDefinition
from syntra.llm.provider import ModelProvider, ModelRequest
from syntra.llm.router import ModelRouter
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.types import MCPInvocationRequest
from syntra.persistence.unit_of_work import UnitOfWork
from syntra.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


@dataclass
class ModelRuntimeResult:
    """Outcome of a complete multi-step agent model execution turn."""

    text: str = ""
    structured_output: Any | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0.0")
    latency_seconds: float = 0.0
    messages: list[LLMMessage] = field(default_factory=list)
    finish_reason: str | None = None
    # Telemetry metadata (Task 7)
    invocation_id: UUID = field(default_factory=uuid4)
    agent_role: str = ""
    provider: str = ""
    model_id: str = ""
    prompt_version: str = "latest"
    skill_versions: list[str] = field(default_factory=list)
    validation_outcome: str = "SUCCESS"
    tool_invocation_ids: list[str] = field(default_factory=list)


class ModelRuntime:
    """Production runtime orchestrating LLM interactions, tool calls, and skills."""

    def __init__(
        self,
        provider: ModelProvider,
        skill_registry: SkillRegistry | None = None,
        context_builder: AgentContextBuilder | None = None,
        tool_gateway: ToolGateway | None = None,
    ) -> None:
        self.provider = provider
        self.skill_registry = skill_registry or SkillRegistry()
        self.context_builder = context_builder or AgentContextBuilder(skill_registry=self.skill_registry)
        self.tool_gateway = tool_gateway

    async def execute_turn(
        self,
        agent_role: str,
        user_prompt: str,
        mission_id: UUID | None = None,
        task_id: UUID | None = None,
        org_id: UUID | None = None,
        task_specification: str | None = None,
        requested_skills: list[str] | None = None,
        active_grants: list[str] | None = None,
        available_tools: list[ToolDefinition] | None = None,
        response_model: type[T] | None = None,
        input_artifacts: list[dict[str, Any]] | None = None,
        conversation_history: list[LLMMessage] | None = None,
        max_tool_steps: int = 5,
        timeout_seconds: float = 60.0,
        prompt_version: str = "latest",
        model_name: str | None = None,
        uow: UnitOfWork | None = None,
    ) -> ModelRuntimeResult:
        """Execute an agent turn with progressive skills, MCP tool dispatch, and token accounting."""
        start_time = time.perf_counter()
        session_id = str(mission_id) if mission_id else str(uuid4())

        # 1. Resolve Target Model
        target_model = model_name or ModelRouter.resolve_model(agent_role)
        spec = get_model_spec(target_model)

        if not spec.enabled or spec.lifecycle_status == "SHUTDOWN":
            raise ModelProviderUnavailableError(
                f"Model '{spec.model_id}' is disabled or shut down (lifecycle: {spec.lifecycle_status}). "
                f"Active replacement: '{spec.replacement or 'gemini-2.5-flash'}'."
            )

        if not spec.is_pricing_known and spec.pricing_configuration.unknown_cost_policy == UnknownCostPolicy.REJECT:
            raise ModelPricingError(
                f"Model '{spec.model_id}' has unverified pricing and unknown-cost policy is REJECT."
            )

        # 2. Build Agent Context (System Instruction + Messages)
        system_instruction, messages = self.context_builder.build_context(
            agent_role=agent_role,
            user_prompt=user_prompt,
            mission_id=mission_id,
            task_id=task_id,
            task_specification=task_specification,
            requested_skills=requested_skills,
            active_grants=active_grants,
            input_artifacts=input_artifacts,
            conversation_history=conversation_history,
            prompt_version=prompt_version,
        )

        # 3. Audit Record for loaded skills
        loaded_skill_versions: list[str] = []
        if requested_skills:
            for s_id in requested_skills:
                try:
                    pkg = self.skill_registry.resolve_skill_version(s_id, "latest")
                    loaded_skill_versions.append(f"{s_id}@{pkg.manifest.version}")
                    if mission_id and task_id:
                        self.skill_registry.record_skill_usage(
                            mission_id=mission_id,
                            task_id=task_id,
                            role=agent_role,
                            skill_id=s_id,
                            version=pkg.manifest.version,
                            status="LOADED_INTO_CONTEXT",
                        )
                except Exception:
                    pass

        # 4. Multi-step Execution Loop (Model Generation <-> Tool Calling)
        current_step = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        accumulated_tool_calls: list[ToolCall] = []
        accumulated_tool_results: list[dict[str, Any]] = []
        final_text = ""
        structured_data: Any | None = None
        finish_reason: str | None = None

        while current_step < max_tool_steps:
            current_step += 1

            # Check mission budget before next model generation if UOW is available
            if uow and mission_id:
                try:
                    budget = await uow.budgets.get_for_mission(mission_id)
                    if budget:
                        accumulated_tokens = total_prompt_tokens + total_completion_tokens
                        if budget.consumed_tokens + accumulated_tokens >= budget.max_tokens:
                            raise ModelBudgetExceededError(
                                f"Token budget exceeded for mission '{mission_id}'. "
                                f"Limit: {budget.max_tokens}, Attempted: {budget.consumed_tokens + accumulated_tokens}"
                            )
                        accumulated_cost = compute_token_cost(
                            target_model, total_prompt_tokens, total_completion_tokens
                        )
                        if budget.consumed_cost_usd + accumulated_cost >= budget.max_cost_usd:
                            raise ModelBudgetExceededError(
                                f"Cost budget exceeded for mission '{mission_id}'. "
                                f"Limit: ${budget.max_cost_usd}, Attempted: ${budget.consumed_cost_usd + accumulated_cost}"
                            )
                except (ModelBudgetExceededError, ModelPricingError):
                    raise
                except Exception as exc:
                    logger.debug("Budget check skipped: %s", exc)

            # Construct Request
            request = ModelRequest(
                messages=messages,
                model=target_model,
                tools=available_tools,
                temperature=spec.default_temperature,
                max_tokens=spec.max_output_tokens,
                timeout_seconds=timeout_seconds,
                session_id=session_id,
                agent_id=str(task_id or uuid4()),
                agent_role=agent_role,
                system_instruction=system_instruction,
            )

            try:
                # If structured output requested AND no tools provided (pure structured generation)
                if response_model and not available_tools:
                    structured_data, response = await self.provider.generate_structured(request, response_model)
                else:
                    response = await self.provider.generate(request)
            except asyncio.CancelledError:
                logger.warning("Agent turn cancelled by caller for mission %s", mission_id)
                raise

            # Accumulate Token Usage
            total_prompt_tokens += response.usage.prompt_tokens
            total_completion_tokens += response.usage.completion_tokens
            finish_reason = response.finish_reason
            final_text = response.text

            # Append model response to conversation history
            messages.append(
                LLMMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.text,
                    tool_calls=response.tool_calls,
                )
            )

            # Check if model proposed tool calls
            if not response.tool_calls:
                # Model finished generating without further tool calls
                break

            accumulated_tool_calls.extend(response.tool_calls)

            # Execute Tool Calls via MCP Gateway
            for tc in response.tool_calls:
                # Dissect server and tool name (e.g. 'syntra.workspace_search' -> server='syntra', tool='workspace_search')
                if "." in tc.name:
                    parts = tc.name.split(".", 1)
                    server_name = parts[0]
                    tool_name = parts[1]
                else:
                    server_name = "syntra"
                    tool_name = tc.name

                if not self.tool_gateway:
                    raise ModelToolExecutionError(
                        f"Model requested tool '{tc.name}', but no ToolGateway is configured in ModelRuntime."
                    )

                mcp_req = MCPInvocationRequest(
                    mission_id=mission_id,
                    task_id=task_id,
                    org_id=org_id or uuid4(),
                    caller_role=agent_role,
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=tc.arguments,
                )

                tool_result = await self.tool_gateway.execute_tool_call(mcp_req, uow=uow)

                accumulated_tool_results.append(
                    {
                        "tool_call_id": tc.id,
                        "tool_name": tc.name,
                        "status": tool_result.status,
                        "output": tool_result.output,
                        "is_error": tool_result.is_error,
                        "error_message": tool_result.error_message,
                    }
                )

                # Format tool output back into conversation as TOOL message
                output_str = (
                    str(tool_result.output) if tool_result.output is not None else (tool_result.error_message or "")
                )
                messages.append(
                    LLMMessage(
                        role=MessageRole.TOOL,
                        name=tc.name,
                        tool_call_id=tc.id,
                        content=output_str,
                    )
                )

        else:
            # Reached max_tool_steps without model producing final answer
            logger.warning("Agent exceeded maximum tool steps (%d)", max_tool_steps)

        # If response_model was requested but tools were used, validate final_text
        if response_model and structured_data is None and final_text:
            try:
                structured_data = response_model.model_validate_json(final_text)
            except Exception as exc:
                raise ModelOutputValidationError(
                    f"Final response failed Pydantic validation for {response_model.__name__}: {exc}. "
                    f"Raw output: {final_text[:500]}"
                ) from exc

        latency = time.perf_counter() - start_time
        total_tokens = total_prompt_tokens + total_completion_tokens
        cost_usd = compute_token_cost(target_model, total_prompt_tokens, total_completion_tokens)

        # 14. Reconcile usage and budget in UnitOfWork
        if uow and mission_id:
            try:
                budget = await uow.budgets.get_for_mission(mission_id)
                if budget:
                    budget.consumed_tokens += total_tokens
                    budget.consumed_cost_usd += cost_usd
            except Exception as exc:
                logger.debug("Failed to record consumed budget in uow: %s", exc)

        turn_invocation_id = uuid4()
        tool_invocation_ids = [tc.id for tc in accumulated_tool_calls]

        # Record telemetry event (Task 7)
        get_telemetry().record_call(
            session_id=session_id,
            agent_id=str(task_id or turn_invocation_id),
            agent_role=agent_role,
            model=target_model,
            latency_seconds=latency,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            success=True,
        )

        return ModelRuntimeResult(
            text=final_text,
            structured_output=structured_data,
            tool_calls=accumulated_tool_calls,
            tool_results=accumulated_tool_results,
            prompt_tokens=total_prompt_tokens,
            completion_tokens=total_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost_usd,
            latency_seconds=latency,
            messages=messages,
            finish_reason=finish_reason,
            invocation_id=turn_invocation_id,
            agent_role=agent_role,
            provider=spec.provider,
            model_id=target_model,
            prompt_version=prompt_version,
            skill_versions=loaded_skill_versions,
            validation_outcome="SUCCESS",
            tool_invocation_ids=tool_invocation_ids,
        )
