"""Operational node implementation for the existing LangGraph mission graph.

No second scheduler, approval store, worker ownership or model provider is created.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shlex
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from langgraph.types import interrupt
from sqlalchemy import select

from syntra.agents.handoffs import (
    ArtifactHandoff,
    RoleArtifact,
    consume_handoff,
    persist_role_result,
    validate_task_reviews,
)
from syntra.agents.operational import AgentInvocation, AgentRegistry, AgentResult, SpecialistAgent
from syntra.agents.sandbox_gateway import effective_capabilities
from syntra.domain.entities import AgentRole, ApprovalDecision, ArtifactType, MissionState, TaskPlanStatus, TaskState
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.persistence.artifact_store import read_artifact, store_artifact
from syntra.persistence.models import ArtifactModel, MembershipModel, TaskPlanModel, UserModel
from syntra.sandbox.models import ContainerConfig
from syntra.sandbox.provider import DockerSandboxProvider
from syntra.scheduling.models import EngineeringTaskSpecification, TaskExecutionResult
from syntra.scheduling.scheduler import TaskScheduler
from syntra.skills.profiles import get_agent_profile


class EngineeringMissionService:
    def __init__(
        self,
        uow_factory: Any,
        registry: AgentRegistry,
        runtime: ModelRuntime,
        verification_commands: list[str],
        repository_context: str = "",
        integration_repository_path: Path | None = None,
        integration_config: ContainerConfig | None = None,
    ) -> None:
        if not verification_commands:
            raise ValueError("Operational engineering requires configured verification commands")
        self.uow_factory, self.registry, self.runtime = uow_factory, registry, runtime
        self.verification_commands, self.repository_context = verification_commands, repository_context
        self.scheduler = TaskScheduler(uow_factory)
        self.integration_repository_path = integration_repository_path
        self.integration_config = integration_config or ContainerConfig()

    async def selected_results(self, uow: Any, state: dict[str, Any]) -> list[dict[str, Any]]:
        org, mission = UUID(state["org_id"]), UUID(state["mission_id"])
        owner = await uow.missions.get_by_id_for_org(mission, org)
        if owner.state in {MissionState.CANCELLED, MissionState.FAILED, MissionState.PAUSED}:
            raise ValueError("Mission cannot publish a delivery candidate")
        selected = []
        for entry in state["task_dag"]:
            task = await uow.tasks.get_by_id_for_org(UUID(entry["task_key"]), org)
            plan = await uow.session.get(TaskPlanModel, task.task_plan_id)
            attempt = await uow.tasks.get_latest_attempt(task.id)
            if (
                task.mission_id != mission
                or task.state != TaskState.COMPLETED
                or not plan
                or plan.plan_version != owner.active_plan_version
                or not attempt
                or attempt.state.value != "SUCCEEDED"
            ):
                raise ValueError("Authoritative task and attempt are not independently completed")
            artifact = (
                await uow.session.execute(
                    select(ArtifactModel).where(
                        ArtifactModel.mission_id == mission,
                        ArtifactModel.task_id == task.id,
                        ArtifactModel.title == f"Execution attempt {attempt.attempt_number}",
                    )
                )
            ).scalar_one_or_none()
            if not artifact:
                raise ValueError("Missing authoritative result artifact")
            body = await read_artifact(uow, artifact_id=artifact.id, mission_id=mission, org_id=org)
            result = TaskExecutionResult.model_validate_json(body)
            if (
                result.status.value != "SUCCEEDED"
                or result.attempt_number != attempt.attempt_number
                or result.task_id != task.id
                or not result.unified_diff
                or not result.base_commit
            ):
                raise ValueError("Result artifact does not match the completed attempt")
            reviewers = await validate_task_reviews(uow, task, attempt, result.unified_diff)
            selected.append(
                {
                    "task_id": str(task.id),
                    "attempt_id": str(attempt.id),
                    "result_artifact_id": str(artifact.id),
                    "patch_hash": hashlib.sha256(result.unified_diff.encode()).hexdigest(),
                    "patch": result.unified_diff,
                    "base_commit": result.base_commit,
                    "review_artifact_ids": [str(a) for a in reviewers],
                }
            )
        if not selected:
            raise ValueError("No completed tasks to integrate")
        return selected

    async def integrate_candidate(self, state: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, Any]:
        if len({r["base_commit"] for r in selected}) != 1:
            raise ValueError("Integration patches do not share the approved base commit")
        if len(selected) > 1 and self.integration_repository_path is None:
            raise ValueError("Combined integration requires an operator-authorized repository path")
        evidence = []
        if self.integration_repository_path is not None:
            provider = DockerSandboxProvider()
            sandbox = await provider.create_sandbox(
                task_id=uuid5(NAMESPACE_URL, f"syntra:integration:{state['mission_id']}:{state['plan_digest']}"),
                attempt_number=1,
                repository_path=self.integration_repository_path,
                base_commit=selected[0]["base_commit"],
                config=self.integration_config,
            )
            try:
                for record in selected:
                    encoded = base64.b64encode(record["patch"].encode()).decode()
                    script = (
                        "import base64,pathlib; pathlib.Path('/tmp/candidate.patch').write_bytes(base64.b64decode("
                        + repr(encoded)
                        + "))"
                    )
                    prepared = await sandbox.execute_command("python -I -c " + shlex.quote(script))
                    applied = await sandbox.execute_command(
                        "git init -q /tmp/candidate-git && git --git-dir=/tmp/candidate-git/.git --work-tree="
                        + shlex.quote(sandbox.config.workspace_mount_path)
                        + " apply /tmp/candidate.patch"
                    )
                    if not prepared.is_success or not applied.is_success:
                        raise ValueError(
                            "Candidate patch application failed: " + (prepared.stderr + applied.stderr)[:600]
                        )
                for command in self.verification_commands:
                    execution = await sandbox.execute_command(command, timeout_seconds=30)
                    evidence.append(asdict(execution))
                    if not execution.is_success:
                        raise ValueError("Combined candidate failed actual clean-sandbox integration tests")
            finally:
                await sandbox.cleanup()
        manifest = [{k: v for k, v in r.items() if k != "patch"} for r in selected]
        content = json.dumps(
            {
                "org_id": state["org_id"],
                "mission_id": state["mission_id"],
                "plan_version": state["mission_version"],
                "selected_results": manifest,
                "integration_commands": evidence,
                "mode": "CLEAN_SANDBOX" if evidence else "SINGLE_PATCH_WITH_INDEPENDENT_QA",
            },
            sort_keys=True,
        )
        async with self.uow_factory() as uow:
            aid, checksum = await store_artifact(
                uow,
                org_id=UUID(state["org_id"]),
                mission_id=UUID(state["mission_id"]),
                title=f"Integrated candidate {state['plan_digest']}",
                content=content,
                type=ArtifactType.TEST_REPORT,
            )
            await uow.commit()
        return {"current_phase": "INTEGRATION", "delivery_digest": checksum, "integration_artifact_id": str(aid)}

    async def validate_approver(self, org_id: UUID, user_id: UUID) -> None:
        async with self.uow_factory() as uow:
            member = (
                await uow.session.execute(
                    select(MembershipModel).where(
                        MembershipModel.org_id == org_id,
                        MembershipModel.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            user = await uow.session.get(UserModel, user_id)
            if (
                not member
                or member.role.value not in {"admin", "owner"}
                or not user
                or not user.is_active
                or user.is_service_account
            ):
                raise ValueError("An active human organization admin or owner must approve")

    async def _planning(
        self, state: dict[str, Any], role: AgentRole, consumer: AgentRole, refs: list[ArtifactHandoff]
    ) -> tuple[Any, ArtifactHandoff]:
        org, mission = UUID(state["org_id"]), UUID(state["mission_id"])
        version = state.get("mission_version", 1)
        iid = uuid5(NAMESPACE_URL, f"syntra:phase10:{org}:{mission}:{version}:{role.value}")
        definition = self.registry.get(role)
        inputs = []
        async with self.uow_factory() as uow:
            authoritative = await uow.missions.get_by_id_for_org(mission, org)
            await uow.session.refresh(authoritative, with_for_update=True)
            if authoritative.state not in {MissionState.PLANNING, MissionState.REPLANNING}:
                raise ValueError("Mission no longer authorizes planning")
            if authoritative.active_plan_version != version:
                raise ValueError("Planning uses a stale authoritative plan version")
            for ref in refs:
                data = await consume_handoff(
                    uow, self.registry, ref, org_id=org, mission_id=mission, consumer_role=role
                )
                inputs.append(
                    {
                        "id": str(ref.artifact_id),
                        "sha256": ref.artifact_hash,
                        "content": data.model_dump_json(),
                        "name": ref.producer_role.value,
                    }
                )
            existing = (
                await uow.session.execute(
                    select(ArtifactModel).where(
                        ArtifactModel.mission_id == mission,
                        ArtifactModel.title == f"agent:{iid}",
                    )
                )
            ).scalar_one_or_none()
            if existing:
                raw = await read_artifact(uow, artifact_id=existing.id, org_id=org, mission_id=mission)
                env = RoleArtifact.model_validate_json(raw)
                if (
                    env.producer_role != role
                    or env.plan_version != version
                    or env.org_id != org
                    or env.mission_id != mission
                    or env.invocation_id != iid
                    or env.task_id is not None
                ):
                    raise ValueError("Cached artifact provenance mismatch")
                pair = await uow.artifacts.get_by_id(existing.id)
                assert pair and pair[1]
                ref = ArtifactHandoff(
                    producer_role=role,
                    consumer_role=consumer,
                    org_id=org,
                    mission_id=mission,
                    plan_version=version,
                    invocation_id=iid,
                    artifact_id=existing.id,
                    artifact_hash=pair[1].sha256_checksum,
                )
                return definition.output_schema.model_validate_json(env.output_json), ref
            claim_key = f"phase10:agent:{iid}"
            if await uow.idempotency.get(claim_key, org):
                raise ValueError(
                    "Agent invocation is already running or requires recovery; refusing duplicate model effects"
                )
            await uow.idempotency.record(claim_key, org, 102, {"status": "STARTED"})
            await uow.budgets.reserve(mission, definition.budget_tokens, definition.budget_cost_usd)
            await uow.outbox.record_event(
                org,
                "AGENT_STARTED",
                {"agent_role": role.value, "invocation_id": str(iid), "plan_version": version},
                mission,
            )
            await uow.commit()
        meter = RuntimeUsage(definition.budget_tokens, definition.budget_cost_usd)
        inv = AgentInvocation(
            invocation_id=iid,
            org_id=org,
            mission_id=mission,
            plan_version=version,
            role=role,
            objective=state["objective"] + "\nApproved repository context:\n" + self.repository_context,
            input_artifacts=inputs,
            approved_capabilities=get_agent_profile(role).allowed_tool_capabilities,
            deadline=datetime.now(UTC) + timedelta(seconds=definition.timeout_seconds),
        )
        result: AgentResult | None = None
        try:
            async with self.uow_factory() as uow:
                inv = inv.model_copy(update={"approved_capabilities": await effective_capabilities(uow, inv)})
                budget = await uow.budgets.get_for_mission(mission)
                if role == AgentRole.ENGINEERING_MANAGER and budget:
                    inv = inv.model_copy(
                        update={
                            "max_tokens": max(1, budget.max_tokens - budget.consumed_tokens - budget.reserved_tokens),
                            "max_cost_usd": max(
                                0, budget.max_cost_usd - budget.consumed_cost_usd - budget.reserved_cost_usd
                            ),
                        }
                    )
            result = await SpecialistAgent(self.registry, self.runtime).execute(inv, usage_meter=meter)
            if result.status != "SUCCEEDED":
                raise ValueError(f"{role.value} returned {result.status}; clarification or intervention required")
        finally:
            async with self.uow_factory() as uow:
                await uow.budgets.commit_usage(
                    mission,
                    meter.total_tokens,
                    meter.cost_usd,
                    reserved_tokens=definition.budget_tokens,
                    reserved_cost_usd=definition.budget_cost_usd,
                )
                await uow.budgets.add_usage_record(
                    org, mission, definition.model_id, meter.prompt_tokens, meter.completion_tokens, meter.cost_usd
                )
                await uow.outbox.record_event(
                    org,
                    "AGENT_COMPLETED" if result and result.status == "SUCCEEDED" else "AGENT_FAILED",
                    {
                        "agent_role": role.value,
                        "invocation_id": str(iid),
                        "tokens": meter.total_tokens,
                        "cost_usd": str(meter.cost_usd),
                    },
                    mission,
                )
                await uow.commit()
        async with self.uow_factory() as uow:
            ref = await persist_role_result(uow, inv, result, consumer)
            await uow.commit()
        return result.output, ref

    async def node(self, name: str, state: dict[str, Any]) -> dict[str, Any]:
        base = {"executed_nodes": state.get("executed_nodes", []) + [name]}
        if name == "requirements_analysis":
            output, ref = await self._planning(state, AgentRole.PRODUCT_MANAGER, AgentRole.SOFTWARE_ARCHITECT, [])
            return {
                **base,
                "current_phase": "REQUIREMENTS_ANALYSIS",
                "prd_summary": output.summary,
                "prd_artifact_id": str(ref.artifact_id),
                "prd_handoff": ref.model_dump(mode="json"),
            }
        if name == "architecture_planning":
            output, ref = await self._planning(
                state,
                AgentRole.SOFTWARE_ARCHITECT,
                AgentRole.ENGINEERING_MANAGER,
                [ArtifactHandoff.model_validate(state["prd_handoff"])],
            )
            return {
                **base,
                "current_phase": "ARCHITECTURE_PLANNING",
                "architecture_summary": output.title,
                "architecture_artifact_id": str(ref.artifact_id),
                "architecture_handoff": ref.model_dump(mode="json"),
            }
        if name == "task_plan_generation":
            output, ref = await self._planning(
                state,
                AgentRole.ENGINEERING_MANAGER,
                AgentRole.BACKEND_ENGINEER,
                [ArtifactHandoff.model_validate(state["architecture_handoff"])],
            )
            keys = {
                t.task_key: str(
                    uuid5(NAMESPACE_URL, f"{state['mission_id']}:{state.get('mission_version', 1)}:{t.task_key}")
                )
                for t in output.tasks
            }
            tasks = []
            for task in output.tasks:
                spec = EngineeringTaskSpecification(
                    objective=task.objective,
                    acceptance_criteria=task.acceptance_criteria,
                    required_skills=task.required_skills,
                    required_capabilities=task.required_capabilities,
                    verification_commands=self.verification_commands,
                    estimated_tokens=task.estimated_tokens,
                    estimated_cost_usd=task.estimated_cost_usd,
                )
                tasks.append(
                    {
                        **task.model_dump(mode="json"),
                        "task_key": keys[task.task_key],
                        "dependencies": [keys[d] for d in task.dependencies],
                        "execution_spec": spec.model_dump(mode="json"),
                    }
                )
            digest = hashlib.sha256(json.dumps(tasks, sort_keys=True).encode()).hexdigest()
            return {
                **base,
                "current_phase": "TASK_PLAN_GENERATION",
                "task_dag": tasks,
                "plan_digest": digest,
                "plan_handoff": ref.model_dump(mode="json"),
            }
        org, mission = UUID(state["org_id"]), UUID(state["mission_id"])
        if name == "ready":
            digest = hashlib.sha256(json.dumps(state["task_dag"], sort_keys=True).encode()).hexdigest()
            if digest != state["plan_digest"]:
                raise ValueError("Approved plan digest changed")
            async with self.uow_factory() as uow:
                from syntra.orchestration.approval_interceptor import generate_deterministic_approval_id

                aid = generate_deterministic_approval_id(mission, "TASK_PLAN_APPROVAL", state["mission_version"])
                approval = await uow.approvals.get_by_id_for_org(aid, org)
                if (
                    approval.decision != ApprovalDecision.CONSUMED
                    or approval.target_resource != f"mission:{mission}:plan:{digest}"
                ):
                    raise ValueError("Exact plan lacks consumed human approval")
                obj = await uow.missions.get_by_id_for_org(mission, org)
                await uow.session.refresh(obj, with_for_update=True)
                if obj.state not in {MissionState.AWAITING_APPROVAL, MissionState.READY}:
                    raise ValueError("Mission no longer authorizes the approved plan")
                if obj.active_plan_version != state["mission_version"]:
                    raise ValueError("Approved plan is no longer authoritative")
                plan = await uow.tasks.get_plan_by_version(mission, state["mission_version"])
                if plan is None:
                    pid = uuid5(NAMESPACE_URL, f"syntra:plan:{mission}:{state['mission_version']}")
                    plan = await uow.tasks.create_plan(pid, mission, state["mission_version"], TaskPlanStatus.APPROVED)
                    for task in state["task_dag"]:
                        spec = EngineeringTaskSpecification.model_validate(task["execution_spec"])
                        await uow.tasks.create_task(
                            UUID(task["task_key"]),
                            plan.id,
                            mission,
                            org,
                            task["task_key"],
                            task["objective"],
                            spec.model_dump_json(),
                            task["role"],
                        )
                    for task in state["task_dag"]:
                        for dep in task["dependencies"]:
                            await uow.tasks.add_dependency(UUID(task["task_key"]), UUID(dep))
                obj.active_plan_version = state["mission_version"]
                obj.state = MissionState.READY
                await uow.commit()
            return {**base, "current_phase": "READY", "domain_state": "READY"}
        if name == "task_scheduling":
            async with self.uow_factory() as uow:
                obj = await uow.missions.get_by_id_for_org(mission, org)
                await uow.session.refresh(obj, with_for_update=True)
                if obj.state not in {MissionState.READY, MissionState.RUNNING}:
                    raise ValueError("Mission is not ready for scheduling")
                obj.state = MissionState.RUNNING
                await uow.commit()
            dispatched = await self.scheduler.schedule_ready_tasks(mission, org)
            return {
                **base,
                "current_phase": "TASK_SCHEDULING",
                "domain_state": "RUNNING",
                "running_task_ids": [str(d.task_id) for d in dispatched],
            }
        if name == "execution_coordination":
            await self.scheduler.schedule_ready_tasks(mission, org)
            async with self.uow_factory() as uow:
                obj = await uow.missions.get_by_id_for_org(mission, org)
                if obj.state == MissionState.CANCELLED:
                    return {**base, "control_signal": "CANCEL"}
                tasks, _, _ = await uow.tasks.list_for_mission(mission, org, limit=500)
                current = [t for t in tasks if str(t.id) in {x["task_key"] for x in state["task_dag"]}]
                if not current or any(t.state in {TaskState.FAILED, TaskState.BLOCKED} for t in current):
                    return {
                        **base,
                        "error_message": "Engineering worker failed or required evidence is blocked",
                        "control_signal": "FAIL",
                    }
                remaining = [str(t.id) for t in current if t.state != TaskState.COMPLETED]
                completed = [str(t.id) for t in current if t.state == TaskState.COMPLETED]
            if remaining:
                interrupt({"kind": "WORKERS_PENDING", "mission_id": str(mission), "task_ids": remaining})
                # Replayed node re-queries PostgreSQL; worker results are never taken from resume payloads.
                return await self.node(name, state)
            return {
                **base,
                "current_phase": "EXECUTION_COORDINATION",
                "running_task_ids": [],
                "pending_task_ids": [],
                "completed_task_ids": completed,
            }
        if name == "integration":
            async with self.uow_factory() as uow:
                selected = await self.selected_results(uow, state)
            return {**base, **await self.integrate_candidate(state, selected)}
        if name == "independent_verification":
            async with self.uow_factory() as uow:
                try:
                    await self.selected_results(uow, state)
                    passed = True
                except ValueError:
                    passed = False
                obj = await uow.missions.get_by_id_for_org(mission, org)
                if passed:
                    from syntra.domain.state_machines import transition_mission_state

                    if obj.state != MissionState.VERIFYING:
                        transition_mission_state(obj.state, MissionState.VERIFYING)
                    obj.state = MissionState.VERIFYING
                    await uow.commit()
                domain_state = obj.state.value
            return {
                **base,
                "current_phase": "INDEPENDENT_VERIFICATION",
                "domain_state": domain_state,
                "verification_passed": passed,
            }
        raise ValueError(f"Unsupported operational node: {name}")
