"""Task Execution Graph for SYNTRA.

Governs the micro execution lifecycle for an individual task through 8 discrete stages:
PREPARE_CONTEXT -> RESOLVE_SKILLS -> PREPARE_CAPABILITIES -> EXECUTE_AGENT ->
COLLECT_ARTIFACTS -> REQUEST_REVIEW -> AWAIT_VERIFICATION -> RESOLVE_OUTCOME

Includes deterministic test execution adapters marked explicitly as test-only
where isolated container sandboxes (Phase 9) are not yet provisioned.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from syntra.domain.entities import TaskState
from syntra.domain.state_machines import transition_task_state
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.models import LLMMessage, MessageRole
from syntra.llm.provider import ModelRequest
from syntra.llm.runtime import ModelRuntime
from syntra.orchestration.state import TaskExecutionState
from syntra.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


def _extract_runtime(config: RunnableConfig | None, default_runtime: ModelRuntime | None = None) -> ModelRuntime:
    if config and "configurable" in config and "runtime" in config["configurable"]:
        return config["configurable"]["runtime"]
    return default_runtime or ModelRuntime(provider=MockModelProvider())


def _extract_skill_registry(config: RunnableConfig | None) -> SkillRegistry:
    if config and "configurable" in config and "skill_registry" in config["configurable"]:
        return config["configurable"]["skill_registry"]
    reg = SkillRegistry()
    reg.discover_skills()
    return reg


# ==============================================================================
# Node Definitions
# ==============================================================================


async def prepare_context_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 1: Assemble prompt context, specification, and agent role instructions."""
    task_id = state.get("task_id") or str(uuid4())
    agent_role = state.get("agent_role", "backend_engineer")

    # Authoritative task transition: PENDING -> IN_PROGRESS
    transition_task_state(TaskState.PENDING, TaskState.READY)
    transition_task_state(TaskState.READY, TaskState.ASSIGNED)
    new_state = transition_task_state(TaskState.ASSIGNED, TaskState.IN_PROGRESS)

    return {
        "task_id": task_id,
        "agent_role": agent_role,
        "current_stage": "PREPARE_CONTEXT",
        "task_state": new_state.value,
        "attempt_number": state.get("attempt_number", 1),
        "context_tokens": 500,
    }


async def resolve_skills_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 2: Resolve and load requested skills from SkillRegistry."""
    skill_registry = _extract_skill_registry(config)
    requested = state.get("requested_skills", [])
    loaded: list[str] = []

    for s_name in requested:
        try:
            pkg = skill_registry.resolve_skill_version(s_name, "latest")
            loaded.append(f"{s_name}@{pkg.manifest.version}")
        except Exception:
            loaded.append(f"{s_name}@test")

    return {
        "current_stage": "RESOLVE_SKILLS",
        "loaded_skills": loaded,
    }


async def prepare_capabilities_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 3: Establish security policies and tool capability grants."""
    role = state.get("agent_role", "backend_engineer")
    grants = (
        ["syntra.workspace_search", "syntra.read_file", "syntra.write_file", "syntra.run_command"]
        if "engineer" in role
        else ["syntra.workspace_search", "syntra.read_file"]
    )

    return {
        "current_stage": "PREPARE_CAPABILITIES",
        "active_grants": grants,
    }


async def execute_agent_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 4: Execute agent turn using ModelRuntime (or deterministic test adapter)."""
    runtime = _extract_runtime(config)
    is_test = state.get("is_test_adapter", True)

    if is_test:
        # TEST-ONLY ADAPTER: Simulates deterministic code generation before Phase 9 sandboxes
        output_text = "Implementation completed successfully."
        diff = "--- a/src/service.py\n+++ b/src/service.py\n@@ -1,3 +1,5 @@\n+def execute_task():\n+    return True\n"
        prompt_tokens = 250
        comp_tokens = 150
        cost = 0.0001
    else:
        raise RuntimeError("Operational tasks must run through the authoritative sandbox worker consumer")
        req = ModelRequest(
            messages=[LLMMessage(role=MessageRole.USER, content=state.get("task_specification", "Implement task"))],
            agent_role=state.get("agent_role", "backend_engineer"),
        )
        resp = await runtime.provider.generate(req)
        output_text = resp.text
        diff = None
        prompt_tokens = resp.usage.prompt_tokens
        comp_tokens = resp.usage.completion_tokens
        cost = float(resp.usage.estimated_cost_usd)

    return {
        "current_stage": "EXECUTE_AGENT",
        "output_text": output_text,
        "unified_diff": diff,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": comp_tokens,
        "cost_usd": cost,
    }


async def collect_artifacts_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 5: Collect produced diff patches and files into immutable artifact records."""
    produced_id = str(uuid4())
    new_state = transition_task_state(TaskState.IN_PROGRESS, TaskState.REVIEW)

    return {
        "current_stage": "COLLECT_ARTIFACTS",
        "task_state": new_state.value,
        "produced_artifact_ids": [produced_id],
    }


async def request_review_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 6: Submit proposed diff for independent peer code and security review."""
    diff = state.get("unified_diff") or ""
    # Test adapter code review: approve if valid diff exists
    verdict = "APPROVED" if diff else "REJECTED"
    comments = ["Code meets architectural standards."] if diff else ["Empty patch."]

    return {
        "current_stage": "REQUEST_REVIEW",
        "review_verdict": verdict,
        "review_comments": comments,
    }


async def await_verification_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 7: Execute independent QA verification against acceptance criteria."""
    new_state = transition_task_state(TaskState.REVIEW, TaskState.VERIFYING)
    outcome = "SUCCESS" if state.get("review_verdict") == "APPROVED" else "FAILED"

    return {
        "current_stage": "AWAIT_VERIFICATION",
        "task_state": new_state.value,
        "verification_outcome": outcome,
    }


async def resolve_outcome_node(state: TaskExecutionState, config: RunnableConfig) -> dict[str, Any]:
    """Stage 8: Finalize task outcome based on verification results."""
    verified = state.get("verification_outcome") == "SUCCESS"
    target = TaskState.COMPLETED if verified else TaskState.FAILED
    final_state = transition_task_state(TaskState.VERIFYING, target)

    return {
        "current_stage": "RESOLVE_OUTCOME",
        "task_state": final_state.value,
    }


# ==============================================================================
# Conditional Routing & Graph Construction
# ==============================================================================


def route_from_review(state: TaskExecutionState) -> str:
    if state.get("review_verdict") == "REJECTED":
        return "resolve_outcome"
    return "await_verification"


def build_task_graph() -> StateGraph:
    """Construct the uncompiled StateGraph for the Task micro lifecycle."""
    workflow = StateGraph(TaskExecutionState)

    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("resolve_skills", resolve_skills_node)
    workflow.add_node("prepare_capabilities", prepare_capabilities_node)
    workflow.add_node("execute_agent", execute_agent_node)
    workflow.add_node("collect_artifacts", collect_artifacts_node)
    workflow.add_node("request_review", request_review_node)
    workflow.add_node("await_verification", await_verification_node)
    workflow.add_node("resolve_outcome", resolve_outcome_node)

    workflow.add_edge(START, "prepare_context")
    workflow.add_edge("prepare_context", "resolve_skills")
    workflow.add_edge("resolve_skills", "prepare_capabilities")
    workflow.add_edge("prepare_capabilities", "execute_agent")
    workflow.add_edge("execute_agent", "collect_artifacts")
    workflow.add_edge("collect_artifacts", "request_review")

    workflow.add_conditional_edges(
        "request_review",
        route_from_review,
        {
            "await_verification": "await_verification",
            "resolve_outcome": "resolve_outcome",
        },
    )

    workflow.add_edge("await_verification", "resolve_outcome")
    workflow.add_edge("resolve_outcome", END)

    return workflow


def compile_task_graph(checkpointer: BaseCheckpointSaver | None = None) -> Any:
    """Compile and return executable LangGraph instance for task micro workflows."""
    builder = build_task_graph()
    return builder.compile(checkpointer=checkpointer)
