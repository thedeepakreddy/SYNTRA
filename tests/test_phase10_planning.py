"""Read-only planning binding checks; container effects are explicitly simulated.

The live Docker acceptance test remains separate and must not be replaced by
these policy/lifecycle checks when the container runtime is unavailable.
"""

import hashlib
from types import SimpleNamespace

import pytest

from syntra.agents.handoffs import ArtifactHandoff, RoleArtifact
from syntra.domain.entities import AgentRole, MissionState
from syntra.llm.schemas import ArchitectureProposal, TaskPlanItem, TaskPlanProposal
from syntra.persistence.artifact_store import read_artifact
from syntra.persistence.models import CapabilityGrantModel
from syntra.sandbox.models import ContainerConfig, ExecutionResult, SandboxLease
from syntra.sandbox.provider import DockerSandboxProvider
from syntra.skills.profiles import get_agent_profile

pytest_plugins = ["test_phase10_independent_qa"]


@pytest.mark.parametrize("cancel_during_read", [False, True])
async def test_planning_binds_read_only_repository_and_cleans_on_revocation(
    qa_planner, qa_scope, uow_factory, tmp_path, monkeypatch, cancel_during_read
):
    provider = qa_planner.provider
    final = provider._responses_queue[0]
    provider._responses_queue[:] = [
        {"tool_calls": [{"id": "inspect", "name": "syntra.read_file", "arguments": {"relative_path": "app.py"}}]},
        final.model_dump_json(),
    ]
    commands = []
    snapshot = SimpleNamespace(
        lease=SandboxLease(worktree_path=tmp_path),
        config=ContainerConfig(workspace_read_only=True),
        cleaned=False,
    )

    async def execute(command, **kwargs):
        commands.append(command)
        if cancel_during_read:
            async with uow_factory() as uow:
                owner = await uow.missions.get_by_id_for_org(qa_scope.mission, qa_scope.org)
                owner.state = MissionState.CANCELLED
                await uow.commit()
        return ExecutionResult(exit_code=0, stdout="if quantity < 0: reject()", stderr="", duration_ms=1)

    async def cleanup():
        snapshot.cleaned = True

    async def create(_self, **kwargs):
        assert kwargs["repository_path"] == tmp_path
        assert kwargs["config"].workspace_read_only
        assert kwargs["config"].network_mode == "none"
        return snapshot

    snapshot.execute_command, snapshot.cleanup = execute, cleanup
    monkeypatch.setattr(DockerSandboxProvider, "create_sandbox", create)
    qa_planner.service.planning_repository_path = tmp_path
    if cancel_during_read:
        with pytest.raises(ValueError, match="[Mm]ission"):
            await qa_planner.service.node("requirements_analysis", qa_planner.state)
    else:
        result = await qa_planner.service.node("requirements_analysis", qa_planner.state)
        assert result["prd_artifact_id"]
    assert snapshot.cleaned and len(commands) == 1
    assert commands[0].startswith("python -I -c ")
    assert {tool.name for tool in provider.call_history[0].tools} <= {
        "syntra.read_file",
        "syntra.list_directory",
        "syntra.workspace_search",
    }
    assert any(
        "if quantity < 0" in msg.content for msg in provider.call_history[1].messages if msg.role.value == "tool"
    )
    async with uow_factory() as uow:
        budget = await uow.budgets.get_for_mission(qa_scope.mission)
        assert budget.reserved_tokens == 0 and budget.consumed_tokens > 0
        if cancel_during_read:
            artifacts, _, _ = await uow.artifacts.list_for_mission(qa_scope.mission, qa_scope.org)
            assert not artifacts


async def test_all_planning_roles_read_snapshot_and_consume_typed_handoffs(
    qa_planner, qa_scope, uow_factory, tmp_path, monkeypatch
):
    """Real gateway/SQLite effects; container commands and provider are simulated."""
    provider = qa_planner.provider
    requirements = provider._responses_queue.pop(0)
    outputs = [
        requirements,
        ArchitectureProposal(
            title="Minimal validation change",
            architectural_decisions=["Retain existing API"],
            component_contracts=["Reject nonpositive quantities"],
            data_persistence_spec="No schema change",
            security_invariants=["Reject invalid input"],
            tradeoffs_and_alternatives=["Prefer bounded correction"],
            requirement_refs=requirements.acceptance_criteria,
        ),
        TaskPlanProposal(
            plan_summary="One bounded validation correction",
            tasks=[
                TaskPlanItem(
                    task_key="READ-001",
                    role="backend_engineer",
                    objective="Correct zero quantity validation",
                    acceptance_criteria=requirements.acceptance_criteria,
                    required_skills=["backend-api-development"],
                    required_capabilities=["syntra.read_file"],
                    expected_artifacts=["UnifiedDiff"],
                    verification_requirements=["Run boundary checks"],
                    estimated_tokens=100000,
                )
            ],
            critical_path=["READ-001"],
            concurrency_limits=1,
        ),
    ]
    roles = [AgentRole.PRODUCT_MANAGER, AgentRole.SOFTWARE_ARCHITECT, AgentRole.ENGINEERING_MANAGER]
    async with uow_factory() as uow:
        for role in roles[1:]:
            for cap in get_agent_profile(role).allowed_tool_capabilities:
                uow.session.add(
                    CapabilityGrantModel(
                        org_id=qa_scope.org,
                        agent_role=role.value,
                        tool_name_pattern=cap,
                        is_allowed=True,
                    )
                )
        await uow.commit()
    for role, output in zip(roles, outputs, strict=True):
        provider.queue_response(
            {
                "tool_calls": [
                    {
                        "id": "inspect-" + role.value,
                        "name": "syntra.read_file",
                        "arguments": {"relative_path": "app.py"},
                    }
                ]
            }
        )
        provider.queue_response(output.model_dump_json())
    snapshots, reads = [], []

    async def create(_self, **kwargs):
        assert kwargs["repository_path"] == tmp_path
        assert kwargs["config"].workspace_read_only and kwargs["config"].network_mode == "none"
        snapshot = SimpleNamespace(lease=SandboxLease(worktree_path=tmp_path), config=kwargs["config"], cleaned=False)

        async def execute(command, **kwargs):
            assert command.startswith("python -I -c ")
            reads.append((snapshot, command))
            return ExecutionResult(exit_code=0, stdout="PLANNING_SOURCE_MARKER quantity < 0", stderr="", duration_ms=1)

        async def cleanup():
            snapshot.cleaned = True

        snapshot.execute_command, snapshot.cleanup = execute, cleanup
        snapshots.append(snapshot)
        return snapshot

    monkeypatch.setattr(DockerSandboxProvider, "create_sandbox", create)
    qa_planner.service.planning_repository_path = tmp_path
    state = dict(qa_planner.state)
    upstream_ids = []
    for index, (node, key) in enumerate(
        [
            ("requirements_analysis", "prd_handoff"),
            ("architecture_planning", "architecture_handoff"),
            ("task_plan_generation", "plan_handoff"),
        ]
    ):
        before = len(provider.call_history)
        state.update(await qa_planner.service.node(node, state))
        requests = provider.call_history[before:]
        assert len(requests) == 2
        assert all(request.agent_role == roles[index].value for request in requests)
        for request in requests:
            assert {tool.name for tool in request.tools} == {
                "syntra.read_file",
                "syntra.list_directory",
                "syntra.workspace_search",
            }
        assert any("PLANNING_SOURCE_MARKER" in msg.content for msg in requests[-1].messages if msg.role.value == "tool")
        if upstream_ids:
            assert str(upstream_ids[-1]) in "\n".join(msg.content for msg in requests[0].messages)
        ref = ArtifactHandoff.model_validate(state[key])
        assert ref.producer_role == roles[index] and ref.plan_version == 1
        assert ref.org_id == qa_scope.org and ref.mission_id == qa_scope.mission
        async with uow_factory() as uow:
            body = await read_artifact(
                uow, artifact_id=ref.artifact_id, org_id=qa_scope.org, mission_id=qa_scope.mission
            )
        assert hashlib.sha256(body.encode()).hexdigest() == ref.artifact_hash
        envelope = RoleArtifact.model_validate_json(body)
        assert envelope.producer_role == roles[index] and envelope.invocation_id == ref.invocation_id
        assert envelope.output_json == outputs[index].model_dump_json()
        upstream_ids.append(ref.artifact_id)
    assert len(reads) == len(snapshots) == 3 and all(s.cleaned for s in snapshots)
