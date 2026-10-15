"""Small durable artifact bodies in the existing version repository.

The inline locator is self-contained PostgreSQL storage, not an unbacked filename.
Large objects must use a separately configured object store; no silent fallback.
"""

import base64
import hashlib
from uuid import UUID

from syntra.domain.entities import ArtifactType
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

MAX_INLINE_BYTES = 1_048_576


async def store_artifact(
    uow: SqlAlchemyUnitOfWork,
    *,
    mission_id: UUID,
    org_id: UUID,
    title: str,
    content: str,
    type: ArtifactType,
    task_id: UUID | None = None,
) -> tuple[UUID, str]:
    await uow.missions.get_by_id_for_org(mission_id, org_id)
    raw = content.encode("utf-8")
    if len(raw) > MAX_INLINE_BYTES:
        raise ValueError("Artifact exceeds configured inline storage capacity")
    checksum = hashlib.sha256(raw).hexdigest()
    artifact = await uow.artifacts.create(mission_id, title, type, task_id)
    await uow.artifacts.add_version(
        artifact.id,
        1,
        "inline:" + base64.b64encode(raw).decode("ascii"),
        checksum,
        len(raw),
    )
    return artifact.id, checksum


async def read_artifact(
    uow: SqlAlchemyUnitOfWork,
    *,
    artifact_id: UUID,
    mission_id: UUID,
    org_id: UUID,
    checksum: str | None = None,
    version: int = 1,
) -> str:
    await uow.missions.get_by_id_for_org(mission_id, org_id)
    pair = await uow.artifacts.get_by_id(artifact_id)
    if pair is None or pair[0].mission_id != mission_id or pair[1] is None:
        raise ValueError("Missing or unauthorized artifact")
    artifact, body = pair
    assert body is not None
    if artifact.current_version != version or body.version != version:
        raise ValueError("Stale artifact version")
    if not body.storage_path.startswith("inline:"):
        raise ValueError("Artifact locator requires an unavailable object store")
    raw = base64.b64decode(body.storage_path[7:], validate=True)
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) != body.size_bytes or digest != body.sha256_checksum or (checksum and checksum != digest):
        raise ValueError("Artifact hash validation failed")
    return raw.decode("utf-8")
