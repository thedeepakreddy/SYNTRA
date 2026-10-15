"""Workflow Orchestration Engine for SYNTRA.

Coordinates compiled LangGraph workflows, injectable ModelRuntime, PostgreSQL
checkpointing, human approval interruptions, and authoritative UnitOfWork persistence.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.runtime import ModelRuntime
from syntra.orchestration.checkpointer import build_mission_thread_id, build_task_thread_id
from syntra.orchestration.lifecycle_service import (
    cancel_mission,
    pause_mission,
    reconcile_mission,
    recover_mission,
    resume_mission,
)
from syntra.orchestration.mission_graph import compile_mission_graph
from syntra.orchestration.state import MissionWorkflowState, TaskExecutionState
from syntra.orchestration.task_graph import compile_task_graph
from syntra.persistence.unit_of_work import UnitOfWork
from syntra.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class WorkflowOrchestrationEngine:
    """Production orchestrator running LangGraph mission and task execution graphs."""

    def __init__(
        self,
        runtime: ModelRuntime | None = None,
        checkpointer: BaseCheckpointSaver | None = None,
        skill_registry: SkillRegistry | None = None,
        engineering_service: Any | None = None,
    ) -> None:
        self.runtime = runtime or ModelRuntime(provider=MockModelProvider())
        self.checkpointer = checkpointer or MemorySaver()
        self.skill_registry = skill_registry or SkillRegistry()
        self.engineering_service = engineering_service

        # Compile LangGraph instances
        self.mission_graph = compile_mission_graph(checkpointer=self.checkpointer)
        self.task_graph = compile_task_graph(checkpointer=self.checkpointer)

    async def start_mission(
        self,
        mission_id: UUID | str,
        org_id: UUID | str,
        objective: str,
        context_files: list[str] | None = None,
        uow: UnitOfWork | None = None,
        max_replan_limit: int = 3,
    ) -> dict[str, Any]:
        """Initiate or advance a mission workflow graph execution."""
        m_id_str = str(mission_id)
        org_id_str = str(org_id)
        thread_id = build_mission_thread_id(m_id_str)
        if self.engineering_service and uow is None:
            raise ValueError("Operational missions require an authoritative UnitOfWork")
        from syntra.core.config import get_settings

        if self.engineering_service is None and (
            get_settings().environment == "production" or not isinstance(self.runtime.provider, MockModelProvider)
        ):
            raise RuntimeError("Operational missions require EngineeringMissionService; legacy simulation is test-only")

        initial_state: MissionWorkflowState = {
            "mission_id": m_id_str,
            "org_id": org_id_str,
            "thread_id": thread_id,
            "objective": objective,
            "context_files": context_files or [],
            "current_phase": "INTAKE",
            "domain_state": "DRAFT",
            "mission_version": 1,
            "replan_count": 0,
            "max_replan_limit": max_replan_limit,
            "pending_task_ids": [],
            "running_task_ids": [],
            "completed_task_ids": [],
            "failed_task_ids": [],
            "executed_nodes": [],
            "idempotency_keys": {},
        }

        config = {
            "configurable": {
                "thread_id": thread_id,
                "runtime": self.runtime,
                "uow": uow,
                "skill_registry": self.skill_registry,
                "engineering_service": self.engineering_service,
            }
        }

        logger.info("Starting mission workflow for %s on thread %s", m_id_str, thread_id)
        result = await self.mission_graph.ainvoke(initial_state, config=config)
        return result

    async def resume_approval(
        self,
        mission_id: UUID | str,
        decision_payload: dict[str, Any] | None = None,
        uow: UnitOfWork | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resume a suspended mission graph from a human approval interrupt."""
        decision_data = decision_payload if decision_payload is not None else (payload or {})
        if self.engineering_service:
            if uow is None:
                raise ValueError("Operational missions require an authoritative UnitOfWork")
            if decision_data.get("decision"):
                await self.engineering_service.validate_approver(
                    UUID(str(decision_data["org_id"])), UUID(str(decision_data["user_id"]))
                )
        thread_id = build_mission_thread_id(mission_id)
        config = {
            "configurable": {
                "thread_id": thread_id,
                "runtime": self.runtime,
                "uow": uow,
                "skill_registry": self.skill_registry,
                "engineering_service": self.engineering_service,
            }
        }

        logger.info("Resuming mission workflow for %s with decision %s", mission_id, decision_data.get("decision"))
        result = await self.mission_graph.ainvoke(Command(resume=decision_data), config=config)
        return result

    async def execute_task(
        self,
        task_id: UUID | str,
        mission_id: UUID | str,
        org_id: UUID | str,
        agent_role: str,
        objective: str,
        task_specification: str = "",
        requested_skills: list[str] | None = None,
        is_test_adapter: bool = True,
    ) -> dict[str, Any]:
        """Execute an individual task micro workflow."""
        t_id_str = str(task_id)
        m_id_str = str(mission_id)
        thread_id = build_task_thread_id(t_id_str)

        initial_state: TaskExecutionState = {
            "task_id": t_id_str,
            "mission_id": m_id_str,
            "org_id": str(org_id),
            "thread_id": thread_id,
            "attempt_number": 1,
            "current_stage": "PREPARE_CONTEXT",
            "task_state": "PENDING",
            "agent_role": agent_role,
            "objective": objective,
            "task_specification": task_specification,
            "requested_skills": requested_skills or [],
            "loaded_skills": [],
            "active_grants": [],
            "context_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "output_text": None,
            "unified_diff": None,
            "produced_artifact_ids": [],
            "review_verdict": None,
            "review_comments": [],
            "verification_outcome": None,
            "error_message": None,
            "is_test_adapter": is_test_adapter,
        }

        config = {
            "configurable": {
                "thread_id": thread_id,
                "runtime": self.runtime,
                "skill_registry": self.skill_registry,
            }
        }

        logger.info("Executing task %s on thread %s", t_id_str, thread_id)
        result = await self.task_graph.ainvoke(initial_state, config=config)
        return result

    async def get_mission_state(self, mission_id: UUID | str) -> dict[str, Any]:
        """Retrieve current graph checkpoint state for a mission."""
        thread_id = build_mission_thread_id(mission_id)
        config = {"configurable": {"thread_id": thread_id}}
        state_snap = await self.mission_graph.aget_state(config)
        return {
            "values": state_snap.values,
            "next": state_snap.next,
            "tasks": [
                {
                    "name": t.name,
                    "interrupts": [i.value for i in t.interrupts] if hasattr(t, "interrupts") else [],
                }
                for t in state_snap.tasks
            ],
        }

    async def pause_mission(
        self, mission_id: UUID, org_id: UUID, reason: str, uow: UnitOfWork | None = None
    ) -> dict[str, Any]:
        return await pause_mission(mission_id, org_id, reason, uow=uow, checkpointer=self.checkpointer)

    async def resume_mission(self, mission_id: UUID, org_id: UUID, uow: UnitOfWork | None = None) -> dict[str, Any]:
        return await resume_mission(mission_id, org_id, uow=uow, checkpointer=self.checkpointer)

    async def cancel_mission(
        self, mission_id: UUID, org_id: UUID, reason: str, uow: UnitOfWork | None = None
    ) -> dict[str, Any]:
        return await cancel_mission(mission_id, org_id, reason, uow=uow, checkpointer=self.checkpointer)

    async def recover_mission(self, mission_id: UUID, org_id: UUID, uow: UnitOfWork | None = None) -> dict[str, Any]:
        return await recover_mission(mission_id, org_id, uow=uow, checkpointer=self.checkpointer)

    async def reconcile_mission(self, mission_id: UUID, org_id: UUID, uow: UnitOfWork | None = None) -> dict[str, Any]:
        return await reconcile_mission(mission_id, org_id, uow=uow, checkpointer=self.checkpointer)
