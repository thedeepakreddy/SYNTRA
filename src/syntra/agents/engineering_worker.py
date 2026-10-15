"""Bounded software development and independent role review in leased Docker sandboxes."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from syntra.agents.handoffs import persist_review_attestation, persist_role_result, require_independent_review
from syntra.agents.operational import AgentInvocation, AgentRegistry, QAProposal, SpecialistAgent
from syntra.agents.sandbox_gateway import build_sandbox_gateway, load_capabilities
from syntra.domain.entities import AgentRole, ArtifactType, AttemptState
from syntra.llm.context import redact_secrets
from syntra.llm.provider import ModelProvider
from syntra.llm.runtime import ModelRuntime, RuntimeUsage
from syntra.llm.schemas import AgentFinalResult
from syntra.persistence.artifact_store import store_artifact
from syntra.sandbox.container import ContainerSandboxInstance
from syntra.sandbox.tool_bridge import SandboxToolBridge
from syntra.sandbox.worker_bridge import SandboxWorkerAdapter
from syntra.scheduling.models import EngineeringTaskSpecification, TaskDispatchPayload, TaskExecutionResult
from syntra.skills.profiles import get_agent_profile


class EngineeringSandboxWorker(SandboxWorkerAdapter):
    """The Phase 9 adapter owns provisioning/cleanup; Phase 8 owns all execution leases."""

    def __init__(
        self,
        *args: Any,
        registry: AgentRegistry,
        provider_model: ModelProvider,
        uow_factory: Any,
        authorized_org_id: UUID,
        authorized_project_id: UUID,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.config = replace(self.config, max_output_bytes=min(self.config.max_output_bytes, 4096))
        self.registry, self.provider_model, self.uow_factory = registry, provider_model, uow_factory
        self.authorized_org_id, self.authorized_project_id = authorized_org_id, authorized_project_id
        self.agent_executor = self._execute_engineering

    async def can_accept_dispatch(self, dispatch: TaskDispatchPayload) -> bool:
        if dispatch.org_id != self.authorized_org_id:
            return False
        async with self.uow_factory() as uow:
            mission = await uow.missions.get_by_id_for_org(dispatch.mission_id, dispatch.org_id)
            return mission.project_id == self.authorized_project_id

    async def execute_task(self, dispatch: TaskDispatchPayload, *args: Any, **kwargs: Any) -> TaskExecutionResult:
        if dispatch.org_id != self.authorized_org_id:
            raise ValueError("Worker repository is not authorized for this organization")
        async with self.uow_factory() as uow:
            mission = await uow.missions.get_by_id_for_org(dispatch.mission_id, dispatch.org_id)
            if mission.project_id != self.authorized_project_id:
                raise ValueError("Worker repository is not authorized for this project")
        if dispatch.assigned_role not in {
            AgentRole.BACKEND_ENGINEER.value,
            AgentRole.FRONTEND_ENGINEER.value,
            AgentRole.DEVOPS_ENGINEER.value,
        }:
            raise ValueError("Worker accepts engineering tasks only; review is an independent invocation")
        if dispatch.assigned_role == AgentRole.FRONTEND_ENGINEER.value:
            platform_root = __import__("pathlib").Path(__file__).resolve().parents[3]
            if self.repo_path == platform_root or (
                self.repo_path.is_relative_to(platform_root) and not (self.repo_path / ".git").exists()
            ):
                raise ValueError("Frontend agents may not modify SYNTRA")
        EngineeringTaskSpecification.model_validate_json(dispatch.specification)
        return await super().execute_task(dispatch, *args, **kwargs)

    async def _execute_engineering(
        self, sandbox: ContainerSandboxInstance, dispatch: TaskDispatchPayload, guard: Any
    ) -> TaskExecutionResult:
        spec = EngineeringTaskSpecification.model_validate_json(dispatch.specification)
        meter = RuntimeUsage(dispatch.budget_reserved_tokens, dispatch.budget_reserved_cost_usd)
        deadline = datetime.now(UTC) + timedelta(seconds=300)
        evidence: list[dict[str, object]] = []
        artifacts: list[UUID] = []
        actual_diff = ""
        previous_failure: str | None = None
        role = AgentRole(dispatch.assigned_role)
        status, error = AttemptState.FAILED, None

        async def invoke(
            target: AgentRole,
            objective: str,
            active_sandbox: ContainerSandboxInstance,
            context: str,
            *,
            use_tools: bool = True,
        ) -> Any:
            await guard()
            inv = AgentInvocation(
                org_id=dispatch.org_id,
                mission_id=dispatch.mission_id,
                task_id=dispatch.task_id,
                task_attempt_id=dispatch.task_attempt_id,
                plan_version=dispatch.plan_version,
                role=target,
                objective=objective,
                deadline=deadline,
                max_tokens=meter.max_tokens,
                max_cost_usd=meter.max_cost_usd,
            )
            # Database grants are intersected with the static role ceiling, never created by an LLM.
            async with self.uow_factory() as uow:
                grants = await load_capabilities(uow, inv)
                from fnmatch import fnmatchcase

                caps = []
                for cap in get_agent_profile(target).allowed_tool_capabilities:
                    matches = [
                        g
                        for g in grants
                        if fnmatchcase(
                            cap, g.tool_name_pattern if "." in g.tool_name_pattern else "syntra." + g.tool_name_pattern
                        )
                    ]
                    if matches:
                        grant = matches[-1]
                        expires = grant.expires_at
                        if expires and expires.tzinfo is None:
                            expires = expires.replace(tzinfo=UTC)
                        if (
                            grant.is_allowed
                            and not grant.requires_approval
                            and (not expires or expires > datetime.now(UTC))
                        ):
                            caps.append(cap)
                if target == role and any(c not in caps for c in spec.required_capabilities):
                    raise ValueError("Approved task capabilities are not granted to this worker role")
                inv = inv.model_copy(
                    update={"approved_capabilities": caps, "skill_ids": spec.required_skills if target == role else []}
                )
                await uow.outbox.record_event(
                    dispatch.org_id,
                    "AGENT_STARTED",
                    {
                        "invocation_id": str(inv.invocation_id),
                        "task_id": str(dispatch.task_id),
                        "attempt_id": str(dispatch.task_attempt_id),
                        "agent_role": target.value,
                    },
                    dispatch.mission_id,
                )
                await uow.commit()
            gateway, tools = build_sandbox_gateway(inv, SandboxToolBridge(active_sandbox), self.uow_factory, guard)
            runtime = ModelRuntime(self.provider_model, self.registry.skills, tool_gateway=gateway)
            if len(context) > 20000:
                raise ValueError("Complete review evidence exceeds the bounded context; decompose this task")
            inv = inv.model_copy(
                update={"objective": objective + "\nUntrusted execution evidence:\n" + redact_secrets(context)}
            )
            result = await SpecialistAgent(self.registry, runtime).execute(
                inv, tools=tools if use_tools else None, usage_meter=meter
            )
            evidence.extend(getattr(gateway, "command_evidence", []))
            if target == role and isinstance(result.output, AgentFinalResult):
                captured_diff = await active_sandbox.get_unified_diff()
                if result.output.unified_diff not in {None, captured_diff}:
                    raise ValueError("Model patch does not match the actual worktree diff")
                result.output = result.output.model_copy(
                    update={
                        "unified_diff": captured_diff,
                        "evidence_notes": [
                            "Sandbox command evidence: " + json.dumps(getattr(gateway, "command_evidence", []))
                        ],
                    }
                )
            evidence.append(
                {
                    "stage": "ROLE_RESULT",
                    "role": target.value,
                    "status": result.status,
                    "invocation_id": str(inv.invocation_id),
                }
            )
            async with self.uow_factory() as uow:
                if result.status == "SUCCEEDED":
                    consumer = AgentRole.CODE_REVIEWER if target == role else role
                    handoff = await persist_role_result(uow, inv, result, consumer)
                    artifacts.append(handoff.artifact_id)
                else:
                    await store_artifact(
                        uow,
                        org_id=dispatch.org_id,
                        mission_id=dispatch.mission_id,
                        task_id=dispatch.task_id,
                        title=f"Agent diagnostic {inv.invocation_id}",
                        content=result.model_dump_json(),
                        type=ArtifactType.TEST_REPORT,
                    )
                await uow.outbox.record_event(
                    dispatch.org_id,
                    "AGENT_COMPLETED",
                    {
                        "invocation_id": str(inv.invocation_id),
                        "task_id": str(dispatch.task_id),
                        "agent_role": target.value,
                        "status": result.status,
                        "tokens": result.prompt_tokens + result.completion_tokens,
                        "cost_usd": str(result.cost_usd),
                        "skill_versions": result.skill_versions,
                    },
                    dispatch.mission_id,
                )
                await uow.commit()
            return inv, result

        async def run_checks(commands: list[str], target_sandbox: ContainerSandboxInstance, stage: str) -> bool:
            outcomes = []
            for command in commands:
                await guard()
                result = await target_sandbox.execute_command(command, timeout_seconds=30)
                evidence.append({**asdict(result), "stage": stage})
                outcomes.append(result.is_success)
            return bool(outcomes) and all(outcomes)

        try:
            await run_checks(spec.verification_commands, sandbox, "BASELINE")
            context = json.dumps({"acceptance_criteria": spec.acceptance_criteria, "execution_evidence": evidence})
            for revision in range(spec.max_rework + 1):
                implementing_inv, implementation = await invoke(
                    role,
                    spec.objective
                    + " Inspect relevant files, add regression tests before fixing code, run tests and return final JSON.",
                    sandbox,
                    context,
                )
                actual_diff = await sandbox.get_unified_diff()
                if implementation.status != "SUCCEEDED" or not actual_diff.strip():
                    raise ValueError("Implementation did not produce a successful, actual worktree patch")
                # Model-supplied diff/evidence never certifies an implementation.
                if getattr(implementation.output, "unified_diff", None) not in {None, actual_diff}:
                    raise ValueError("Model patch does not match the actual worktree diff")
                if redact_secrets(actual_diff) != actual_diff:
                    raise ValueError("Deterministic secret scan rejected the patch")
                await sandbox._run_docker("pause", sandbox.container_name)
                qa_sandbox = ContainerSandboxInstance(
                    replace(sandbox.lease, task_id=uuid4()),
                    sandbox.worktree_manager,
                    replace(sandbox.config, workspace_read_only=True),
                    base_commit=sandbox.base_commit,
                    owns_worktree=False,
                )
                accepted = False
                review_context = json.dumps(
                    {
                        "patch": actual_diff,
                        "acceptance_criteria": spec.acceptance_criteria,
                        "base_commit": self.base_commit,
                    }
                )
                try:
                    await qa_sandbox.start()
                    qa_inv, qa = await invoke(
                        AgentRole.QA_ENGINEER,
                        "Independently derive acceptance commands from the requirements, including boundary and negative cases. Return QAProposal JSON.",
                        qa_sandbox,
                        review_context,
                        use_tools=False,
                    )
                    require_independent_review(role, qa_inv.role, implementing_inv.invocation_id, qa_inv.invocation_id)
                    if not isinstance(qa.output, QAProposal):
                        raise ValueError("Missing independently formulated QA plan")
                    qa_start = len(evidence)
                    tests_ok = await run_checks(
                        spec.verification_commands + qa.output.acceptance_commands, qa_sandbox, "QA"
                    )
                    qa_evidence = [r for r in evidence[qa_start:] if r.get("stage") == "QA"]
                    review_context += "\nIndependent QA plan: " + qa.output.model_dump_json()
                    review_context += "\nActual test evidence: " + json.dumps(evidence)
                    review_inv, review = await invoke(
                        AgentRole.CODE_REVIEWER,
                        "Review the actual patch and actual test evidence against acceptance criteria. Return CodeReviewProposal JSON.",
                        qa_sandbox,
                        review_context,
                        use_tools=False,
                    )
                    require_independent_review(
                        role, review_inv.role, implementing_inv.invocation_id, review_inv.invocation_id
                    )
                    review_context += "\nCode review: " + review.output.model_dump_json()
                    security_ok = True
                    review_records = [(qa_inv, qa, qa_evidence), (review_inv, review, [])]
                    if spec.security_sensitive or re.search(
                        r"auth|security|lock|Dockerfile|requirements", actual_diff, re.I
                    ):
                        sec_inv, security = await invoke(
                            AgentRole.SECURITY_REVIEWER,
                            "Inspect the actual patch for security findings; explicitly state limitations of model analysis. Return SecurityReport JSON.",
                            qa_sandbox,
                            review_context,
                            use_tools=False,
                        )
                        require_independent_review(
                            role, sec_inv.role, implementing_inv.invocation_id, sec_inv.invocation_id
                        )
                        security_ok = security.status == "SUCCEEDED"
                        review_records.append((sec_inv, security, []))
                        review_context += "\nSecurity review: " + security.output.model_dump_json()
                    accepted = tests_ok and not qa.output.defects and review.status == "SUCCEEDED" and security_ok
                    async with self.uow_factory() as uow:
                        for reviewer_inv, reviewer_result, commands in review_records:
                            artifacts.append(
                                await persist_review_attestation(
                                    uow, implementing_inv, reviewer_inv, reviewer_result, actual_diff, commands
                                )
                            )
                        await uow.commit()
                finally:
                    await qa_sandbox.cleanup()
                    await sandbox._run_docker("unpause", sandbox.container_name)
                if accepted:
                    status = AttemptState.SUCCEEDED
                    break
                fingerprint = hashlib.sha256(
                    (
                        actual_diff
                        + json.dumps(
                            [
                                {k: r.get(k) for k in ("command", "exit_code", "stderr", "stage", "role", "status")}
                                for r in evidence[-5:]
                            ],
                            sort_keys=True,
                        )
                    ).encode()
                ).hexdigest()
                if revision >= spec.max_rework or fingerprint == previous_failure:
                    raise ValueError("Independent review failed; bounded correction attempts exhausted")
                previous_failure = fingerprint
                _, analysis = await invoke(
                    AgentRole.DEBUGGING_SPECIALIST,
                    "Analyze observed failed checks and review findings. Propose a surgical correction and regression test. Return FailureAnalysis JSON.",
                    sandbox,
                    review_context,
                    use_tools=False,
                )
                if analysis.status != "SUCCEEDED":
                    raise ValueError("Debugging analysis failed")
                context = review_context + "\nRoot cause analysis: " + analysis.output.model_dump_json()
        except asyncio.CancelledError:
            error = "CANCELLED: ownership or invocation was revoked; preserved usage requires settlement"
        except Exception as exc:
            error = type(exc).__name__ + ": " + redact_secrets(str(exc))[:500]
        finally:
            # Persist evidence even for rejected patches, provider failures or exhausted budgets.
            async with self.uow_factory() as uow:
                await store_artifact(
                    uow,
                    org_id=dispatch.org_id,
                    mission_id=dispatch.mission_id,
                    task_id=dispatch.task_id,
                    title="Engineering execution evidence",
                    type=ArtifactType.TEST_REPORT,
                    content=redact_secrets(
                        json.dumps(
                            {
                                "evidence": evidence,
                                "status": status.value,
                                "error": error,
                                "usage": {"tokens": meter.total_tokens, "cost_usd": str(meter.cost_usd)},
                            }
                        )
                    ),
                )
                await uow.commit()
        return TaskExecutionResult(
            task_id=dispatch.task_id,
            attempt_number=dispatch.attempt_number,
            worker_id=self.worker_id,
            fencing_token=dispatch.fencing_token,
            status=status,
            exit_code=0 if status == AttemptState.SUCCEEDED else 1,
            unified_diff=actual_diff or None,
            base_commit=getattr(sandbox, "base_commit", self.base_commit),
            changed_files=sorted(
                {line[6:] for line in actual_diff.splitlines() if line.startswith(("+++ b/", "--- a/"))}
            ),
            produced_artifact_ids=artifacts,
            execution_evidence=evidence,
            error_message=error,
            output_summary="IMPLEMENTATION_TESTED; independent role review accepted; human delivery approval required"
            if status == AttemptState.SUCCEEDED
            else "Engineering attempt failed: " + str(error),
            actual_prompt_tokens=meter.prompt_tokens,
            actual_completion_tokens=meter.completion_tokens,
            actual_cost_usd=meter.cost_usd,
            cost_classification="CONSERVATIVE_UNVERIFIED" if meter.unknown_usage else "ESTIMATED_FROM_USAGE",
        )
