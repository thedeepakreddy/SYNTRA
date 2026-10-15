"""Deterministic model decisions, REAL PostgreSQL/Redis/Docker development and review.

This is explicitly MOCK_VERIFIED model evidence, not Gemini autonomy evidence.
"""

import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from syntra.agents.engineering_worker import EngineeringSandboxWorker
from syntra.agents.operational import AgentRegistry, QAProposal, SecurityReport
from syntra.domain.entities import AgentRole, MembershipRole, MissionState, TaskState
from syntra.llm.mock_provider import MockModelProvider
from syntra.llm.runtime import ModelRuntime
from syntra.llm.schemas import (
    AgentFinalResult,
    ArchitectureProposal,
    CodeReviewProposal,
    FailureAnalysis,
    RequirementsAnalysis,
    TaskPlanItem,
    TaskPlanProposal,
)
from syntra.orchestration.checkpointer import CheckpointerFactory
from syntra.orchestration.engine import WorkflowOrchestrationEngine
from syntra.orchestration.engineering_service import EngineeringMissionService
from syntra.persistence.artifact_store import read_artifact
from syntra.persistence.models import CapabilityGrantModel, MembershipModel, ProjectModel, UserModel
from syntra.sandbox.models import ContainerConfig
from syntra.scheduling.consumer import SandboxWorkerConsumer
from syntra.scheduling.outbox_relay import OutboxRelay
from syntra.scheduling.redis_dispatcher import RedisTaskDispatcher
from syntra.skills.profiles import get_agent_profile
from syntra.skills.registry import SkillRegistry

FIXTURE_ROOT = Path(__file__).parent / "fixtures/phase10_fastapi"
ACCEPTANCE = 'python -c \'from fastapi.testclient import TestClient; from app import app; c=TestClient(app); assert c.post("/orders",json={"quantity":0}).status_code==422; assert c.post("/orders",json={"quantity":-1}).status_code==422; assert c.post("/orders",json={"quantity":2}).json()=={"quantity":2}\''


@pytest.fixture
def phase10_fixture_repo():
    target = Path(__file__).parent.parent / ".syntra/test_sandboxes" / ("phase10_" + uuid4().hex)
    shutil.copytree(FIXTURE_ROOT, target)
    for command in (
        ["git", "init", "-b", "main"],
        ["git", "config", "user.name", "Phase10 Fixture"],
        ["git", "config", "user.email", "fixture@syntra.local"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Known zero-quantity validation defect"],
    ):
        subprocess.run(command, cwd=target, check=True, capture_output=True)
    try:
        yield target
    finally:
        shutil.rmtree(target)


def queued_provider(rework=False):
    provider = MockModelProvider()
    req = RequirementsAnalysis(
        summary="Correct zero-quantity input validation in the authorized fixture",
        functional_requirements=[
            "Reject nonpositive integer quantities with HTTP 422",
            "Accept positive integer quantities",
        ],
        acceptance_criteria=["Given quantity zero, When POST /orders is called, Then return HTTP 422"],
        risk_assessment="Invalid orders must not be silently accepted",
        out_of_scope=["Production deployment"],
    )
    provider.queue_response(req)
    provider.queue_response(
        ArchitectureProposal(
            title="Minimal input validation correction",
            architectural_decisions=["Preserve FastAPI and existing public API"],
            component_contracts=["POST /orders preserves JSON responses"],
            data_persistence_spec="No database changes required",
            security_invariants=["Reject invalid quantities"],
            tradeoffs_and_alternatives=["Surgical change avoids unnecessary replacements"],
            requirement_refs=["Reject nonpositive quantities"],
        )
    )
    provider.queue_response(
        TaskPlanProposal(
            plan_summary="Correct one fixture validation defect with independent acceptance tests",
            tasks=[
                TaskPlanItem(
                    task_key="FIX-001",
                    role="backend_engineer",
                    objective="Inspect app.py, reject zero quantities and add a regression test",
                    acceptance_criteria=req.acceptance_criteria,
                    required_skills=["backend-api-development"],
                    required_capabilities=[
                        "syntra.read_file",
                        "syntra.write_file",
                        "syntra.run_command",
                        "syntra.git_diff",
                    ],
                    expected_artifacts=["UnifiedDiff", "TestReport"],
                    verification_requirements=["Run regression and independent HTTP acceptance checks"],
                    estimated_tokens=100000,
                )
            ],
            critical_path=["FIX-001"],
            concurrency_limits=1,
        )
    )

    def tools(*calls):
        provider.queue_response(
            {"tool_calls": [{"id": uuid4().hex, "name": name, "arguments": args} for name, args in calls]}
        )

    tools(("syntra.read_file", {"relative_path": "app.py"}), ("syntra.workspace_search", {"relative_path": "tests"}))
    regression = "from fastapi.testclient import TestClient\nfrom app import app\n\ndef test_zero_quantity_rejected():\n    assert TestClient(app).post('/orders', json={'quantity': 0}).status_code == 422\n"
    tools(("syntra.write_file", {"relative_path": "tests/test_zero.py", "content": regression}))
    tools(("syntra.run_command", {"command": "python -m pytest -q -p no:cacheprovider tests/test_zero.py"}))
    fixed = (FIXTURE_ROOT / "app.py").read_text().replace("if quantity < 0:", "if quantity <= 0:")
    tools(("syntra.write_file", {"relative_path": "app.py", "content": fixed}))
    tools(("syntra.run_command", {"command": "python -m pytest -q -p no:cacheprovider tests"}))
    provider.queue_response(
        AgentFinalResult(
            summary="Corrected zero-quantity validation and added a regression test",
            verdict="SUCCESS",
            evidence_notes=["Actual command results are recorded by the sandbox gateway"],
        ).model_dump_json()
    )
    provider.queue_response(
        QAProposal(
            test_plan=["Independently verify zero, negative and positive HTTP inputs"],
            acceptance_commands=[ACCEPTANCE],
            requirement_refs=["Reject nonpositive integer quantities"],
        )
    )
    provider.queue_response(
        CodeReviewProposal(
            verdict="CHANGES_REQUESTED" if rework else "APPROVED",
            summary_evaluation="Actual patch and regression evidence meet the approved acceptance criteria",
            checklist_verifications={"scope": True, "tests_pass": True},
            test_coverage_adequate=True,
        )
    )
    provider.queue_response(
        SecurityReport(
            summary="No high severity finding in the inspected validation patch",
            findings=[],
            limitations=["Model inspection and deterministic secret scan are not a complete security audit"],
        )
    )
    if rework:
        provider.queue_response(
            FailureAnalysis(
                error_type="ReviewRejection",
                root_cause_hypothesis="The regression suite omits invalid boolean quantities",
                reproducing_steps=["Inspect the missing boolean quantity regression case"],
                affected_components=["tests/test_zero.py"],
                proposed_surgical_fix="Add a boolean input regression without changing accepted positive input behavior",
                prevention_recommendations=["Keep independent HTTP acceptance coverage"],
            )
        )
        tools(
            (
                "syntra.write_file",
                {
                    "relative_path": "tests/test_invalid_type.py",
                    "content": "from fastapi.testclient import TestClient\nfrom app import app\n\ndef test_boolean_quantity_rejected():\n    assert TestClient(app).post('/orders',json={'quantity': True}).status_code == 422\n",
                },
            )
        )
        tools(("syntra.run_command", {"command": "python -m pytest -q -p no:cacheprovider tests"}))
        provider.queue_response(
            AgentFinalResult(
                summary="Added the missing boolean-quantity regression required by the independent reviewer",
                verdict="SUCCESS",
                evidence_notes=["Actual tests recorded by the sandbox gateway"],
            ).model_dump_json()
        )
        provider.queue_response(
            QAProposal(
                test_plan=["Recheck all independently specified HTTP boundaries"],
                acceptance_commands=[ACCEPTANCE],
                requirement_refs=["Reject invalid quantities"],
            )
        )
        provider.queue_response(
            CodeReviewProposal(
                verdict="APPROVED",
                summary_evaluation="The revised actual patch includes the requested regression and passed actual QA",
                checklist_verifications={"scope": True, "tests_pass": True},
                test_coverage_adequate=True,
            )
        )
        provider.queue_response(
            SecurityReport(
                summary="No high severity finding in the revised validation patch",
                findings=[],
                limitations=["Model analysis cannot replace a complete deterministic security audit"],
            )
        )
    return provider


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.parametrize("rework", [False, True], ids=["accepted", "review_rejection_and_debugging"])
async def test_complete_engineering_mission_real_infrastructure(
    phase10_database, phase10_fixture_repo, rework, live=False
):
    uow_factory, checkpoint_url = phase10_database
    org, mission, project, human = uuid4(), uuid4(), uuid4(), uuid4()
    async with uow_factory() as uow:
        await uow.organizations.create(org, "Phase10 acceptance", "phase10-" + org.hex)
        uow.session.add(ProjectModel(id=project, org_id=org, name="Fixture", slug="fixture"))
        uow.session.add(
            UserModel(
                id=human,
                email=f"{human}@syntra.local",
                full_name="Test Approver",
                is_active=True,
                is_service_account=False,
            )
        )
        await uow.session.flush()
        uow.session.add(MembershipModel(org_id=org, user_id=human, role=MembershipRole.ADMIN))
        await uow.missions.create(
            mission,
            org,
            project,
            "Fix the documented input validation defect, add a regression test and supply a reviewed patch",
        )
        await uow.budgets.create(
            org, mission, max_tokens=1000000, max_cost_usd=Decimal("1.00") if live else Decimal("50.00")
        )
        for role in AgentRole:
            for cap in get_agent_profile(role).allowed_tool_capabilities:
                uow.session.add(
                    CapabilityGrantModel(org_id=org, agent_role=role.value, tool_name_pattern=cap, is_allowed=True)
                )
        await uow.commit()
    skills = SkillRegistry()
    skills.discover_skills()
    registry = AgentRegistry(skills, model_name=None if live else "mock-model")
    if live:
        from syntra.llm.gemini_provider import GeminiModelProvider

        provider = GeminiModelProvider()
    else:
        provider = queued_provider(rework)
    runtime = ModelRuntime(provider, skills)
    service = EngineeringMissionService(
        uow_factory,
        registry,
        runtime,
        [ACCEPTANCE],
        repository_context="FastAPI app.py and tests/, no persistence changes; use one backend task estimated at 100000 tokens with backend-api-development skill",
        integration_repository_path=phase10_fixture_repo,
        integration_config=ContainerConfig(image="syntra-phase10-acceptance:local"),
    )
    pool, saver = await CheckpointerFactory.create_postgres_checkpointer(checkpoint_url)
    dispatcher = RedisTaskDispatcher(
        os.environ.get("SYNTRA_REDIS_URL", "redis://localhost:6379/0"), stream_key="syntra:phase10:" + uuid4().hex
    )
    try:
        engine = WorkflowOrchestrationEngine(runtime, saver, skills, engineering_service=service)
        async with uow_factory() as uow:
            started = await engine.start_mission(
                mission,
                org,
                "Fix the documented zero-quantity defect, preserve positive quantities and add a regression test",
                uow=uow,
            )
        approval = started["__interrupt__"][0].value
        assert approval["action_type"] == "TASK_PLAN_APPROVAL" and started["plan_digest"] in approval["target_resource"]
        # Simulate a restart with the same durable PostgreSQL checkpoints.
        await pool.close()
        pool, saver = await CheckpointerFactory.create_postgres_checkpointer(checkpoint_url, run_setup=False)
        engine = WorkflowOrchestrationEngine(runtime, saver, skills, engineering_service=service)
        async with uow_factory() as uow:
            resumed = await engine.resume_approval(
                mission,
                {
                    "decision": "APPROVED",
                    "org_id": str(org),
                    "user_id": str(human),
                    "action_digest": approval["action_digest"],
                },
                uow=uow,
            )
        assert resumed["__interrupt__"][0].value["kind"] == "WORKERS_PENDING"
        assert await OutboxRelay(uow_factory, dispatcher).relay_batch() == 1
        adapter = EngineeringSandboxWorker(
            phase10_fixture_repo,
            worker_id="phase10-engineer",
            registry=registry,
            provider_model=provider,
            uow_factory=uow_factory,
            authorized_org_id=org,
            authorized_project_id=project,
            config=ContainerConfig(image="syntra-phase10-acceptance:local"),
        )
        assert await SandboxWorkerConsumer(service.scheduler, dispatcher, adapter, "phase10-engineer").run_once() == 1
        async with uow_factory() as uow:
            tasks, _, _ = await uow.tasks.list_for_mission(mission, org)
            attempt = await uow.tasks.get_latest_attempt(tasks[0].id)
            assert tasks[0].state == TaskState.COMPLETED, attempt.error_message
        async with uow_factory() as uow:
            delivery = await engine.resume_approval(mission, {"org_id": str(org)}, uow=uow)
        delivery_approval = delivery["__interrupt__"][0].value
        assert delivery_approval["action_type"] == "DELIVERY_APPROVAL"
        assert delivery["delivery_digest"] in delivery_approval["target_resource"]
        async with uow_factory() as uow:
            final = await engine.resume_approval(
                mission,
                {
                    "decision": "APPROVED",
                    "org_id": str(org),
                    "user_id": str(human),
                    "action_digest": delivery_approval["action_digest"],
                },
                uow=uow,
            )
        assert final["domain_state"] == MissionState.COMPLETED.value
        if not live:
            assert ("debugging_specialist" in [r.agent_role for r in provider.call_history]) == rework
        async with uow_factory() as uow:
            artifacts, _, _ = await uow.artifacts.list_for_mission(mission, org, limit=100)
            bodies = [await read_artifact(uow, artifact_id=a.id, org_id=org, mission_id=mission) for a, _ in artifacts]
            assert any("+    if quantity <= 0:" in body for body in bodies)
            assert any('"stage": "BASELINE"' in body and '"stage": "QA"' in body for body in bodies)
            budget = await uow.budgets.get_for_mission(mission)
            assert budget.reserved_tokens == 0 and budget.consumed_tokens > 0
            if export := os.environ.get("SYNTRA_PHASE10_EVIDENCE_DIR"):
                root = Path(__file__).resolve().parents[1] / ".syntra/phase10-evidence"
                output = Path(export).resolve() / ("rework" if rework else "accepted")
                if not output.is_relative_to(root.resolve()):
                    raise ValueError("Evidence exports must remain in .syntra/phase10-evidence")
                output.mkdir(parents=True, exist_ok=True)
                for (artifact, _), body in zip(artifacts, bodies, strict=True):
                    extension = ".patch" if artifact.type.value == "UNIFIED_DIFF" else ".json"
                    (output / (str(artifact.id) + extension)).write_text(body)
                (output / "outcome.json").write_text(
                    json.dumps(
                        {
                            "mode": "GEMINI_LIVE" if live else "MOCK_VERIFIED",
                            "mission_state": final["domain_state"],
                            "artifact_count": len(artifacts),
                            "consumed_tokens": budget.consumed_tokens,
                            "estimated_cost_usd": str(budget.consumed_cost_usd),
                            "delivery_digest": final["delivery_digest"],
                            "infrastructure": ["PostgreSQL", "Redis Streams", "Docker"],
                            "review_rework_exercised": rework,
                        },
                        indent=2,
                    )
                )
        assert "if quantity < 0:" in (phase10_fixture_repo / "app.py").read_text()
        assert not list((phase10_fixture_repo / ".syntra/sandboxes").glob("wt_*"))
    finally:
        await pool.close()
        client = await dispatcher.get_client()
        await client.delete(dispatcher.stream_key)
        await dispatcher.close()


@pytest.mark.integration
@pytest.mark.docker
async def test_live_gemini_engineering_mission(phase10_database, phase10_fixture_repo):
    from syntra.llm.gemini_provider import GeminiModelProvider

    if os.environ.get("SYNTRA_RUN_PHASE10_GEMINI") != "1" or not GeminiModelProvider().is_configured():
        pytest.skip("BLOCKED_BY_CREDENTIALS: opt-in live Gemini execution is unavailable")
    await test_complete_engineering_mission_real_infrastructure(
        phase10_database, phase10_fixture_repo, False, live=True
    )


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.parametrize("conflicting", [False, True], ids=["two-compatible-patches", "conflicting-patches-blocked"])
async def test_combined_candidate_applies_real_patches_and_tests_clean_snapshot(
    phase10_database, phase10_fixture_repo, conflicting
):
    """Real Docker application of two diffs, not a claimed result dictionary."""
    import hashlib

    factory, _ = phase10_database
    org, project, mission = uuid4(), uuid4(), uuid4()
    async with factory() as uow:
        await uow.organizations.create(org, "Combined integration", "combined-" + org.hex)
        uow.session.add(ProjectModel(id=project, org_id=org, name="Fixture", slug="fixture"))
        await uow.missions.create(mission, org, project, "Integrate two independent candidate patches")
        await uow.commit()
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=phase10_fixture_repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    app_path = phase10_fixture_repo / "app.py"
    original = app_path.read_text()

    def capture_patch(path, text):
        previous = path.read_text()
        try:
            path.write_text(text)
            return subprocess.run(
                ["git", "diff", "--no-ext-diff", "--binary"],
                cwd=phase10_fixture_repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        finally:
            path.write_text(previous)

    first = capture_patch(app_path, original.replace("quantity < 0", "quantity <= 0"))
    if conflicting:
        second = capture_patch(app_path, original.replace("quantity < 0", "quantity < 1"))
    else:
        readme = phase10_fixture_repo / "README.md"
        second = capture_patch(readme, readme.read_text() + "\nCOMBINED_CANDIDATE_MARKER\n")
    assert first.startswith("diff --git") and second.startswith("diff --git")
    skills = SkillRegistry()
    skills.discover_skills()
    service = EngineeringMissionService(
        factory,
        AgentRegistry(skills, model_name="mock-model"),
        ModelRuntime(MockModelProvider()),
        [
            ACCEPTANCE,
            "python -c \"from pathlib import Path; assert 'COMBINED_CANDIDATE_MARKER' in Path('README.md').read_text()\"",
        ],
        integration_repository_path=phase10_fixture_repo,
        integration_config=ContainerConfig(image="syntra-phase10-acceptance:local"),
    )
    state = {"org_id": str(org), "mission_id": str(mission), "mission_version": 1, "plan_digest": "combined"}
    selected = [
        {
            "task_id": str(uuid4()),
            "base_commit": base,
            "patch": patch,
            "patch_hash": hashlib.sha256(patch.encode()).hexdigest(),
        }
        for patch in [first, second]
    ]
    if conflicting:
        with pytest.raises(ValueError, match="patch application failed"):
            await service.integrate_candidate(state, selected)
        async with factory() as uow:
            artifacts, _, _ = await uow.artifacts.list_for_mission(mission, org)
            assert artifacts == []
    else:
        result = await service.integrate_candidate(state, selected)
        from uuid import UUID

        async with factory() as uow:
            report = json.loads(
                await read_artifact(
                    uow, artifact_id=UUID(result["integration_artifact_id"]), org_id=org, mission_id=mission
                )
            )
        assert report["mode"] == "CLEAN_SANDBOX"
        assert len(report["selected_results"]) == 2
        assert len(report["integration_commands"]) == 2
        assert all(run["exit_code"] == 0 for run in report["integration_commands"])
    assert app_path.read_text() == original
    assert not list((phase10_fixture_repo / ".syntra/sandboxes").glob("wt_*"))
