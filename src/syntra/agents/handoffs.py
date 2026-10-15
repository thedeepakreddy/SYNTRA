"""Validated, hashed role artifacts; consumers load bytes through tenant-scoped persistence."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from syntra.agents.operational import ROLE_CONTRACTS, AgentInvocation, AgentRegistry, AgentResult
from syntra.domain.entities import AgentRole, ArtifactType, MissionState
from syntra.persistence.artifact_store import read_artifact, store_artifact
from syntra.persistence.models import ArtifactModel, TaskAttemptModel, TaskModel
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork


class ArtifactHandoff(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    producer_role: AgentRole
    consumer_role: AgentRole
    org_id: UUID
    mission_id: UUID
    task_id: UUID | None = None
    plan_version: int = Field(ge=1)
    invocation_id: UUID
    artifact_id: UUID
    artifact_version: int = 1
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    validation_status: Literal["VALIDATED"] = "VALIDATED"


class RoleArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invocation_id: UUID
    producer_role: AgentRole
    org_id: UUID
    mission_id: UUID
    task_id: UUID | None
    task_attempt_id: UUID | None
    plan_version: int
    agent_version: str
    prompt_version: str
    model_id: str
    skill_versions: list[str]
    output_json: str


async def persist_role_result(
    uow: SqlAlchemyUnitOfWork, invocation: AgentInvocation, result: AgentResult, consumer: AgentRole
) -> ArtifactHandoff:
    if result.status != "SUCCEEDED" or result.output is None or result.role != invocation.role:
        raise ValueError("Only validated successful results can be handed off")
    if result.invocation_id != invocation.invocation_id:
        raise ValueError("Result invocation provenance does not match request")
    ROLE_CONTRACTS[invocation.role][0].model_validate(result.output.model_dump())
    mission = await uow.missions.get_by_id_for_org(invocation.mission_id, invocation.org_id)
    await uow.session.refresh(mission, with_for_update=True)
    if mission.active_plan_version != invocation.plan_version or mission.state in {
        MissionState.CANCELLED,
        MissionState.FAILED,
        MissionState.PAUSED,
    }:
        raise ValueError("Mission no longer authorizes artifact publication")
    envelope = RoleArtifact(
        invocation_id=invocation.invocation_id,
        producer_role=result.role,
        org_id=invocation.org_id,
        mission_id=invocation.mission_id,
        task_id=invocation.task_id,
        task_attempt_id=invocation.task_attempt_id,
        plan_version=invocation.plan_version,
        agent_version=result.agent_version,
        prompt_version=result.prompt_version,
        model_id=result.model_id,
        skill_versions=result.skill_versions,
        output_json=result.output.model_dump_json(),
    )
    artifact_type = {
        AgentRole.PRODUCT_MANAGER: ArtifactType.PRD,
        AgentRole.SOFTWARE_ARCHITECT: ArtifactType.ARCHITECTURE_SPEC,
        AgentRole.SECURITY_REVIEWER: ArtifactType.SECURITY_REPORT,
    }.get(result.role, ArtifactType.TEST_REPORT)
    aid, digest = await store_artifact(
        uow,
        mission_id=invocation.mission_id,
        org_id=invocation.org_id,
        task_id=invocation.task_id,
        title=f"agent:{invocation.invocation_id}",
        content=envelope.model_dump_json(),
        type=artifact_type,
    )
    handoff = ArtifactHandoff(
        producer_role=result.role,
        consumer_role=consumer,
        org_id=invocation.org_id,
        mission_id=invocation.mission_id,
        task_id=invocation.task_id,
        plan_version=invocation.plan_version,
        invocation_id=invocation.invocation_id,
        artifact_id=aid,
        artifact_hash=digest,
    )
    uow.publish_event("AGENT_HANDOFF_CREATED", handoff.model_dump(mode="json"))
    return handoff


async def consume_handoff(
    uow: SqlAlchemyUnitOfWork,
    registry: AgentRegistry,
    handoff: ArtifactHandoff,
    *,
    org_id: UUID,
    mission_id: UUID,
    consumer_role: AgentRole,
) -> BaseModel:
    if handoff.org_id != org_id or handoff.mission_id != mission_id or handoff.consumer_role != consumer_role:
        raise ValueError("Unauthorized handoff consumer or tenant")
    mission = await uow.missions.get_by_id_for_org(mission_id, org_id)
    if mission.state in {MissionState.CANCELLED, MissionState.FAILED, MissionState.PAUSED}:
        raise ValueError("Mission does not authorize handoff consumption")
    if handoff.plan_version != mission.active_plan_version:
        raise ValueError("Stale handoff plan version")
    body = await read_artifact(
        uow,
        artifact_id=handoff.artifact_id,
        mission_id=mission_id,
        org_id=org_id,
        checksum=handoff.artifact_hash,
        version=handoff.artifact_version,
    )
    envelope = RoleArtifact.model_validate_json(body)
    if (
        envelope.org_id != org_id
        or envelope.mission_id != mission_id
        or envelope.producer_role != handoff.producer_role
        or envelope.invocation_id != handoff.invocation_id
        or envelope.task_id != handoff.task_id
        or envelope.plan_version != handoff.plan_version
    ):
        raise ValueError("Artifact provenance does not match handoff")
    return registry.get(envelope.producer_role).output_schema.model_validate_json(envelope.output_json)


def require_independent_review(
    implementer: AgentRole, reviewer: AgentRole, producer_id: UUID, reviewer_id: UUID
) -> None:
    if (
        implementer == reviewer
        or producer_id == reviewer_id
        or reviewer
        not in {
            AgentRole.CODE_REVIEWER,
            AgentRole.QA_ENGINEER,
            AgentRole.SECURITY_REVIEWER,
        }
    ):
        raise ValueError("Implementer cannot review or certify its own patch")


class CommandEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1)
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = Field(default=0, ge=0)
    timed_out: bool = False
    output_truncated: bool = False
    stage: Literal["QA"] = "QA"


class ReviewAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    mission_id: UUID
    task_id: UUID
    task_attempt_id: UUID
    plan_version: int
    implementer_role: AgentRole
    implementation_invocation_id: UUID
    reviewer_role: AgentRole
    reviewer_invocation_id: UUID
    input_patch_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_output_json: str
    command_evidence: list[CommandEvidence] = Field(default_factory=list)

    def accepted(self) -> bool:
        from syntra.agents.operational import QAProposal, SecurityReport
        from syntra.llm.schemas import CodeReviewProposal

        require_independent_review(
            self.implementer_role, self.reviewer_role, self.implementation_invocation_id, self.reviewer_invocation_id
        )
        output = ROLE_CONTRACTS[self.reviewer_role][0].model_validate_json(self.review_output_json)
        if isinstance(output, QAProposal):
            return (
                not output.defects
                and bool(self.command_evidence)
                and all(e.exit_code == 0 and not e.timed_out for e in self.command_evidence)
            )
        if isinstance(output, CodeReviewProposal):
            return (
                output.verdict == "APPROVED"
                and output.test_coverage_adequate
                and bool(output.checklist_verifications)
                and all(output.checklist_verifications.values())
                and not any(c.severity == "BLOCKER" for c in output.line_level_comments)
            )
        if isinstance(output, SecurityReport):
            return not any(f.severity in {"HIGH", "CRITICAL"} for f in output.findings)
        return False


async def persist_review_attestation(
    uow: SqlAlchemyUnitOfWork,
    implementer: AgentInvocation,
    reviewer: AgentInvocation,
    result: AgentResult,
    patch: str,
    commands: list[dict[str, object]] | None = None,
) -> UUID:
    if (
        implementer.task_id is None
        or implementer.task_attempt_id is None
        or result.invocation_id != reviewer.invocation_id
        or result.role != reviewer.role
        or (reviewer.org_id, reviewer.mission_id, reviewer.task_id, reviewer.task_attempt_id)
        != (implementer.org_id, implementer.mission_id, implementer.task_id, implementer.task_attempt_id)
        or result.output is None
    ):
        raise ValueError("Review provenance does not match the authoritative implementation attempt")
    record = ReviewAttestation(
        org_id=implementer.org_id,
        mission_id=implementer.mission_id,
        task_id=implementer.task_id,
        task_attempt_id=implementer.task_attempt_id,
        plan_version=implementer.plan_version,
        implementer_role=implementer.role,
        implementation_invocation_id=implementer.invocation_id,
        reviewer_role=reviewer.role,
        reviewer_invocation_id=reviewer.invocation_id,
        input_patch_hash=hashlib.sha256(patch.encode()).hexdigest(),
        review_output_json=result.output.model_dump_json(),
        command_evidence=[CommandEvidence.model_validate(c) for c in commands or []],
    )
    record.accepted()  # Validate role contracts and independence even for a rejection.
    aid, _ = await store_artifact(
        uow,
        org_id=record.org_id,
        mission_id=record.mission_id,
        task_id=record.task_id,
        title=f"review:{record.task_attempt_id}:{record.reviewer_role.value}:{record.reviewer_invocation_id}",
        content=record.model_dump_json(),
        type=ArtifactType.TEST_REPORT,
    )
    return aid


async def validate_task_reviews(
    uow: SqlAlchemyUnitOfWork, task: TaskModel, attempt: TaskAttemptModel, patch: str
) -> list[UUID]:
    """A claimed QA dictionary cannot substitute for independent, patch-bound artifacts."""

    from syntra.llm.schemas import AgentFinalResult
    from syntra.scheduling.models import EngineeringTaskSpecification

    spec = EngineeringTaskSpecification.model_validate_json(task.description)
    digest = hashlib.sha256(patch.encode()).hexdigest()
    required = {AgentRole.QA_ENGINEER, AgentRole.CODE_REVIEWER}
    if spec.security_sensitive or re.search(r"auth|security|lock|Dockerfile|requirements", patch, re.I):
        required.add(AgentRole.SECURITY_REVIEWER)
    artifacts = list(
        (
            await uow.session.execute(
                select(ArtifactModel)
                .where(
                    ArtifactModel.task_id == task.id,
                    ArtifactModel.mission_id == task.mission_id,
                    ArtifactModel.title.like(f"review:{attempt.id}:%"),
                )
                .limit(501)
            )
        )
        .scalars()
        .all()
    )
    if len(artifacts) > 500:
        raise ValueError("Review artifact limit exceeded")
    groups: dict[UUID, dict[AgentRole, UUID]] = {}
    for artifact in artifacts:
        body = await read_artifact(uow, artifact_id=artifact.id, org_id=task.org_id, mission_id=task.mission_id)
        review = ReviewAttestation.model_validate_json(body)
        if (
            review.org_id != task.org_id
            or review.mission_id != task.mission_id
            or review.task_id != task.id
            or review.task_attempt_id != attempt.id
            or review.implementer_role.value != task.assigned_role
            or review.input_patch_hash != digest
            or not review.accepted()
        ):
            continue
        author = (
            await uow.session.execute(
                select(ArtifactModel).where(
                    ArtifactModel.mission_id == task.mission_id,
                    ArtifactModel.task_id == task.id,
                    ArtifactModel.title == f"agent:{review.implementation_invocation_id}",
                )
            )
        ).scalar_one_or_none()
        if not author:
            continue
        env = RoleArtifact.model_validate_json(
            await read_artifact(uow, artifact_id=author.id, org_id=task.org_id, mission_id=task.mission_id)
        )
        if (
            env.invocation_id != review.implementation_invocation_id
            or env.org_id != task.org_id
            or env.mission_id != task.mission_id
            or env.task_id != task.id
            or env.task_attempt_id != attempt.id
            or env.producer_role != review.implementer_role
            or env.plan_version != review.plan_version
        ):
            continue
        output = AgentFinalResult.model_validate_json(env.output_json)
        if output.unified_diff != patch:
            continue
        groups.setdefault(review.implementation_invocation_id, {})[review.reviewer_role] = artifact.id
    for approved in groups.values():
        if required.issubset(approved):
            return [approved[r] for r in sorted(required, key=lambda role: role.value)]
    raise ValueError("Missing independent review artifacts for the exact patch and attempt")
