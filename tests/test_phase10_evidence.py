"""Acceptance assertions and synthetic negative probes, not live verification."""

import hashlib
import json
from copy import deepcopy
from uuid import UUID

import pytest

from syntra.agents.handoffs import ReviewAttestation, RoleArtifact
from syntra.agents.operational import QAProposal, SecurityReport
from syntra.domain.entities import AgentRole
from syntra.llm.schemas import AgentFinalResult, CodeReviewProposal, FailureAnalysis


def assert_mission_evidence(bodies, *, rework, baseline_command, expected_attempt_id):
    documents = []
    for body in bodies:
        try:
            value = json.loads(body)
        except json.JSONDecodeError:  # Unified diffs are separate opaque artifacts.
            continue
        if isinstance(value, dict):
            documents.append(value)
    executions = [d for d in documents if "evidence" in d and "usage" in d]
    assert len(executions) == 1 and executions[0]["status"] == "SUCCEEDED"
    events = executions[0]["evidence"]
    commands = [e for e in events if "command" in e]
    assert commands and all(not c["timed_out"] and not c["output_truncated"] for c in commands)
    assert all(c["duration_ms"] > 0 for c in commands)
    baseline = [c for c in commands if c.get("stage") == "BASELINE"]
    assert len(baseline) == 1 and baseline[0]["command"] == baseline_command
    assert baseline[0]["exit_code"] == 1 and "AssertionError" in baseline[0]["stderr"]
    regression = next(c for c in commands if c["command"].endswith("tests/test_zero.py"))
    assert regression["exit_code"] == 1 and "AssertionError: assert 200 == 422" in regression["stdout"]
    fixed = next(c for c in commands if c["command"].endswith(" tests") and c["exit_code"] == 0)
    assert "passed" in fixed["stdout"]
    assert events.index(baseline[0]) < events.index(regression) < events.index(fixed)
    qa = [c for c in commands if c.get("stage") == "QA"]
    assert len(qa) >= 2 * (1 + int(rework))
    assert all(c["command"] == baseline_command and c["exit_code"] == 0 for c in qa)

    envelopes = [RoleArtifact.model_validate(d) for d in documents if "producer_role" in d and "output_json" in d]
    by_invocation = {str(e.invocation_id): e for e in envelopes}
    role_events = [(i, e) for i, e in enumerate(events) if e.get("stage") == "ROLE_RESULT"]
    implementations = [
        (i, by_invocation[e["invocation_id"]]) for i, e in role_events if e["role"] == "backend_engineer"
    ]
    assert len(implementations) == 1 + int(rework)
    reviews = [ReviewAttestation.model_validate(d) for d in documents if "input_patch_hash" in d]
    assert len(reviews) == 3 * len(implementations)
    required = {AgentRole.QA_ENGINEER, AgentRole.CODE_REVIEWER, AgentRole.SECURITY_REVIEWER}
    patches, reviewer_ids = [], []
    for index, (position, author) in enumerate(implementations):
        assert author.task_attempt_id == expected_attempt_id
        output = AgentFinalResult.model_validate_json(author.output_json)
        patch = output.unified_diff
        assert output.verdict == "SUCCESS" and patch
        assert "+    if quantity <= 0:" in patch and "tests/test_zero.py" in patch
        patches.append(patch)
        group = [r for r in reviews if r.implementation_invocation_id == author.invocation_id]
        assert len(group) == 3 and {r.reviewer_role for r in group} == required
        group_ids = {r.reviewer_invocation_id for r in group}
        assert len(group_ids) == 3 and author.invocation_id not in group_ids
        reviewer_ids.append(group_ids)
        for review in group:
            assert (review.org_id, review.mission_id, review.task_id, review.task_attempt_id, review.plan_version) == (
                author.org_id,
                author.mission_id,
                author.task_id,
                expected_attempt_id,
                author.plan_version,
            )
            assert review.input_patch_hash == hashlib.sha256(patch.encode()).hexdigest()
            event_index = next(
                i for i, event in role_events if event["invocation_id"] == str(review.reviewer_invocation_id)
            )
            assert event_index > position
            if index + 1 < len(implementations):
                assert event_index < implementations[index + 1][0]
            if review.reviewer_role == AgentRole.QA_ENGINEER:
                assert review.command_evidence and all(
                    c.exit_code == 0 and not c.timed_out and not c.output_truncated for c in review.command_evidence
                )
            if rework and index == 0 and review.reviewer_role == AgentRole.CODE_REVIEWER:
                assert not review.accepted()
                assert CodeReviewProposal.model_validate_json(review.review_output_json).verdict == "CHANGES_REQUESTED"
            else:
                assert review.accepted()
    if rework:
        assert patches[0] != patches[1] and reviewer_ids[0].isdisjoint(reviewer_ids[1])
        assert "tests/test_invalid_type.py" in patches[1]
        debugging = [(i, e) for i, e in role_events if e["role"] == "debugging_specialist"]
        assert len(debugging) == 1 and implementations[0][0] < debugging[0][0] < implementations[1][0]
        analysis = FailureAnalysis.model_validate_json(by_invocation[debugging[0][1]["invocation_id"]].output_json)
        assert analysis.error_type == "ReviewRejection"
    else:
        assert not any(e["role"] == "debugging_specialist" for _, e in role_events)
    return patches[-1]


def execution_prefix():
    """Minimal synthetic prefix to prove weak evidence is rejected early."""

    def command(command, exit_code, **kwargs):
        return {
            "command": command,
            "exit_code": exit_code,
            "duration_ms": 10,
            "timed_out": False,
            "output_truncated": False,
            "stdout": "",
            "stderr": "",
            **kwargs,
        }

    return {
        "status": "SUCCEEDED",
        "usage": {},
        "evidence": [
            command("acceptance", 1, stage="BASELINE", stderr="AssertionError"),
            command("pytest tests/test_zero.py", 1, stdout="AssertionError: assert 200 == 422"),
            command("pytest tests", 0, stdout="3 passed"),
        ],
    }


@pytest.mark.parametrize(
    "tamper",
    [
        "baseline_pass",
        "wrong_failure",
        "timeout",
        "truncated",
        "no_real_duration",
        "missing_regression",
        "wrong_order",
        "labels_only",
    ],
)
def test_acceptance_rejects_weak_or_incomplete_execution_evidence(tamper):
    doc = deepcopy(execution_prefix())
    events = doc["evidence"]
    if tamper == "baseline_pass":
        events[0]["exit_code"] = 0
    elif tamper == "wrong_failure":
        events[1]["stdout"] = "could not import dependency"
    elif tamper == "timeout":
        events[2]["timed_out"] = True
    elif tamper == "truncated":
        events[1]["output_truncated"] = True
    elif tamper == "no_real_duration":
        events[2]["duration_ms"] = 0
    elif tamper == "missing_regression":
        events[1]["command"] = "pytest other.py"
    elif tamper == "wrong_order":
        events.reverse()
    else:
        doc["evidence"] = [{"stage": "BASELINE"}, {"stage": "QA"}]
    with pytest.raises((AssertionError, StopIteration)):
        assert_mission_evidence(
            [json.dumps(doc)], rework=False, baseline_command="acceptance", expected_attempt_id=UUID(int=1)
        )


def synthetic_mission(*, rework):
    """Complete synthetic records test the assertions, not infrastructure effects."""
    execution = execution_prefix()
    documents = [execution]
    org, mission, task, attempt = [UUID(int=i) for i in (2, 3, 4, 1)]

    def envelope(invocation, role, output):
        documents.append(
            json.loads(
                RoleArtifact(
                    invocation_id=invocation,
                    producer_role=role,
                    org_id=org,
                    mission_id=mission,
                    task_id=task,
                    task_attempt_id=attempt,
                    plan_version=1,
                    agent_version="1",
                    prompt_version="1",
                    model_id="synthetic-only",
                    skill_versions=[],
                    output_json=output.model_dump_json(),
                ).model_dump_json()
            )
        )

    def event(invocation, role):
        execution["evidence"].append(
            {"stage": "ROLE_RESULT", "role": role.value, "status": "SUCCEEDED", "invocation_id": str(invocation)}
        )

    for revision in range(1 + int(rework)):
        author_id = UUID(int=10 + revision)
        patch = "diff --git a/app.py b/app.py\n+    if quantity <= 0:\ndiff --git a/tests/test_zero.py b/tests/test_zero.py\n"
        if revision:
            patch += "diff --git a/tests/test_invalid_type.py b/tests/test_invalid_type.py\n"
            execution["evidence"].append({**execution["evidence"][2]})
        envelope(
            author_id,
            AgentRole.BACKEND_ENGINEER,
            AgentFinalResult(
                summary="Synthetic validation patch output",
                verdict="SUCCESS",
                unified_diff=patch,
                evidence_notes=["Synthetic fixture, not execution evidence"],
            ),
        )
        event(author_id, AgentRole.BACKEND_ENGINEER)
        qa_commands = [
            {
                "command": "acceptance",
                "exit_code": 0,
                "stage": "QA",
                "stdout": "",
                "stderr": "",
                "duration_ms": 10,
                "timed_out": False,
                "output_truncated": False,
            }
        ] * 2
        for offset, (role, output) in enumerate(
            [
                (
                    AgentRole.QA_ENGINEER,
                    QAProposal(
                        test_plan=["Boundary check"],
                        acceptance_commands=["acceptance"],
                        requirement_refs=["Reject zero"],
                    ),
                ),
                (
                    AgentRole.CODE_REVIEWER,
                    CodeReviewProposal(
                        verdict="CHANGES_REQUESTED" if rework and revision == 0 else "APPROVED",
                        summary_evaluation="Synthetic review of validation behavior",
                        checklist_verifications={"tests": True},
                        test_coverage_adequate=True,
                    ),
                ),
                (
                    AgentRole.SECURITY_REVIEWER,
                    SecurityReport(
                        summary="Synthetic bounded security review", findings=[], limitations=["Not real review"]
                    ),
                ),
            ]
        ):
            reviewer_id = UUID(int=100 + revision * 10 + offset)
            event(reviewer_id, role)
            if role == AgentRole.QA_ENGINEER:
                execution["evidence"].extend(deepcopy(qa_commands))
            documents.append(
                json.loads(
                    ReviewAttestation(
                        org_id=org,
                        mission_id=mission,
                        task_id=task,
                        task_attempt_id=attempt,
                        plan_version=1,
                        implementer_role=AgentRole.BACKEND_ENGINEER,
                        implementation_invocation_id=author_id,
                        reviewer_role=role,
                        reviewer_invocation_id=reviewer_id,
                        input_patch_hash=hashlib.sha256(patch.encode()).hexdigest(),
                        review_output_json=output.model_dump_json(),
                        command_evidence=qa_commands if role == AgentRole.QA_ENGINEER else [],
                    ).model_dump_json()
                )
            )
        if rework and revision == 0:
            debugger_id = UUID(int=50)
            envelope(
                debugger_id,
                AgentRole.DEBUGGING_SPECIALIST,
                FailureAnalysis(
                    error_type="ReviewRejection",
                    root_cause_hypothesis="Synthetic missing regression diagnosis",
                    reproducing_steps=["Inspect tests"],
                    affected_components=["tests"],
                    proposed_surgical_fix="Add the missing boolean regression",
                ),
            )
            event(debugger_id, AgentRole.DEBUGGING_SPECIALIST)
    return documents


@pytest.mark.parametrize("rework", [False, True])
def test_complete_synthetic_evidence_is_accepted_by_assertions(rework):
    patch = assert_mission_evidence(
        [json.dumps(d) for d in synthetic_mission(rework=rework)],
        rework=rework,
        baseline_command="acceptance",
        expected_attempt_id=UUID(int=1),
    )
    assert ("test_invalid_type.py" in patch) == rework


@pytest.mark.parametrize(
    "tamper",
    [
        "stale_patch",
        "wrong_attempt",
        "missing_review",
        "self_review",
        "reviewer_reused",
        "missing_debug",
        "no_rejection",
        "qa_timeout",
        "identical_patch",
    ],
)
def test_rework_requires_exact_patch_attempt_and_fresh_reviews(tamper):
    docs = synthetic_mission(rework=True)
    reviews = [d for d in docs if "input_patch_hash" in d]
    if tamper == "stale_patch":
        reviews[-1]["input_patch_hash"] = "0" * 64
    elif tamper == "wrong_attempt":
        reviews[-1]["task_attempt_id"] = str(UUID(int=999))
    elif tamper == "missing_review":
        docs.remove(reviews[-1])
    elif tamper == "self_review":
        reviews[-1]["reviewer_invocation_id"] = reviews[-1]["implementation_invocation_id"]
    elif tamper == "reviewer_reused":
        old = reviews[0]["reviewer_invocation_id"]
        current = reviews[3]["reviewer_invocation_id"]
        reviews[3]["reviewer_invocation_id"] = old
        for e in docs[0]["evidence"]:
            if e.get("invocation_id") == current:
                e["invocation_id"] = old
    elif tamper == "missing_debug":
        docs[0]["evidence"] = [e for e in docs[0]["evidence"] if e.get("role") != "debugging_specialist"]
    elif tamper == "no_rejection":
        output = json.loads(reviews[1]["review_output_json"])
        output["verdict"] = "APPROVED"
        reviews[1]["review_output_json"] = json.dumps(output)
    elif tamper == "qa_timeout":
        reviews[3]["command_evidence"][0]["timed_out"] = True
    else:
        authors = [d for d in docs if d.get("producer_role") == "backend_engineer"]
        authors[1]["output_json"] = authors[0]["output_json"]
        for review in reviews[3:]:
            review["input_patch_hash"] = reviews[0]["input_patch_hash"]
    with pytest.raises((AssertionError, StopIteration, ValueError)):
        assert_mission_evidence(
            [json.dumps(d) for d in docs], rework=True, baseline_command="acceptance", expected_attempt_id=UUID(int=1)
        )
