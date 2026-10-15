"""SYNTRA Agent Skills Registry.

Manages discovery, validation, semantic version resolution, dependency checking,
progressive disclosure selection, integrity verification, and usage recording.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import yaml

from syntra.skills.manifest import (
    SkillDependencyError,
    SkillIntegrityError,
    SkillManifest,
    SkillRoleError,
    SkillSecurityError,
    SkillSourceTrust,
    SkillValidationError,
)
from syntra.skills.profiles import get_agent_profile


def parse_semver_key(v: str) -> tuple[int, int, int]:
    """Parse semver string into comparable (major, minor, patch) integer tuple."""
    clean = re.split(r"[-+]", v.strip())[0]
    parts = clean.split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return (0, 0, 0)


@dataclass
class SkillPackage:
    """A loaded, validated skill package."""

    manifest: SkillManifest
    skill_dir: Path
    instructions_markdown: str
    schemas: dict[str, Any] = field(default_factory=dict)
    references: dict[str, str] = field(default_factory=dict)
    computed_checksum: str = ""
    source_trust: SkillSourceTrust = SkillSourceTrust.TRUSTED_CORE


@dataclass
class SkillUsageRecord:
    """Audit record capturing exact skill invocation."""

    id: UUID = field(default_factory=uuid4)
    mission_id: UUID = field(default_factory=uuid4)
    task_id: UUID = field(default_factory=uuid4)
    agent_role: str = ""
    skill_id: str = ""
    version: str = ""
    status: str = "SUCCESS"  # SUCCESS, FAILED, REJECTED
    invoked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)


class SkillRegistry:
    """Authoritative registry for SYNTRA skills."""

    def __init__(self, root_dir: Path | str | None = None):
        self.root_dir = Path(root_dir) if root_dir else Path("skills")
        # Structure: _registry[skill_id][version] = SkillPackage
        self._registry: dict[str, dict[str, SkillPackage]] = {}
        self._usage_log: list[SkillUsageRecord] = []
        self._approved_sources: set[str] = {
            "core",
            "internal",
            "syntra-official",
            "trusted-partner",
        }

    @property
    def registered_skill_ids(self) -> list[str]:
        """List of all registered skill IDs."""
        return list(self._registry.keys())

    def compute_package_checksum(self, skill_dir: Path) -> str:
        """Compute SHA-256 digest of manifest.yaml and SKILL.md combined."""
        hasher = hashlib.sha256()
        manifest_path = skill_dir / "manifest.yaml"
        doc_path = skill_dir / "SKILL.md"

        if manifest_path.exists():
            hasher.update(manifest_path.read_bytes())
        if doc_path.exists():
            hasher.update(doc_path.read_bytes())

        # Include schemas if present
        schemas_dir = skill_dir / "schemas"
        if schemas_dir.exists() and schemas_dir.is_dir():
            for p in sorted(schemas_dir.glob("*.json")):
                hasher.update(p.read_bytes())

        return hasher.hexdigest()

    def validate_skill(self, skill_dir: Path) -> SkillManifest:
        """Validate that a skill directory adheres to SYNTRA standards."""
        if not skill_dir.is_dir():
            raise SkillValidationError(f"Skill path '{skill_dir}' is not a directory")

        manifest_path = skill_dir / "manifest.yaml"
        doc_path = skill_dir / "SKILL.md"

        if not manifest_path.exists():
            raise SkillValidationError(f"Missing manifest.yaml in '{skill_dir}'")
        if not doc_path.exists():
            raise SkillValidationError(f"Missing SKILL.md in '{skill_dir}'")

        try:
            raw_yaml = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(raw_yaml, dict):
                raise SkillValidationError(f"manifest.yaml in '{skill_dir}' must be a YAML dictionary")
        except Exception as e:
            raise SkillValidationError(f"Failed to parse YAML in '{manifest_path}': {e}") from e

        # Validate with Pydantic
        try:
            manifest = SkillManifest(**raw_yaml)
        except Exception as e:
            raise SkillValidationError(f"Skill manifest validation failed for '{skill_dir.name}': {e}") from e

        # Verify SKILL.md contains meaningful substantive content
        doc_content = doc_path.read_text(encoding="utf-8").strip()
        if len(doc_content) < 50:
            raise SkillValidationError(
                f"SKILL.md in '{skill_dir.name}' is too short ({len(doc_content)} chars). "
                "Must provide substantive engineering instructions."
            )

        return manifest

    def register_skill(
        self,
        manifest: SkillManifest,
        skill_path: Path,
        source_trust: SkillSourceTrust = SkillSourceTrust.TRUSTED_CORE,
    ) -> SkillPackage:
        """Register a validated skill package into memory."""
        doc_path = skill_path / "SKILL.md"
        instructions = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""

        # Load schemas if present
        schemas: dict[str, Any] = {}
        schemas_dir = skill_path / "schemas"
        if schemas_dir.exists() and schemas_dir.is_dir():
            for s_file in schemas_dir.glob("*.json"):
                try:
                    schemas[s_file.stem] = yaml.safe_load(s_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # Load references if present
        references: dict[str, str] = {}
        refs_dir = skill_path / "references"
        if refs_dir.exists() and refs_dir.is_dir():
            for r_file in refs_dir.glob("*.md"):
                try:
                    references[r_file.stem] = r_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        checksum = self.compute_package_checksum(skill_path)

        # Integrity verification if checksum specified
        if manifest.checksum_sha256 and manifest.checksum_sha256 != checksum:
            raise SkillIntegrityError(
                f"Integrity check failed for skill '{manifest.id}' version '{manifest.version}'. "
                f"Expected: {manifest.checksum_sha256}, Computed: {checksum}"
            )

        package = SkillPackage(
            manifest=manifest,
            skill_dir=skill_path,
            instructions_markdown=instructions,
            schemas=schemas,
            references=references,
            computed_checksum=checksum,
            source_trust=source_trust,
        )

        if manifest.id not in self._registry:
            self._registry[manifest.id] = {}

        self._registry[manifest.id][manifest.version] = package
        return package

    def discover_skills(self, directory: Path | None = None) -> list[SkillManifest]:
        """Discover and register all valid skill packages in target directory."""
        search_dir = Path(directory) if directory else self.root_dir
        manifests: list[SkillManifest] = []

        if not search_dir.exists() or not search_dir.is_dir():
            return manifests

        for sub_dir in sorted(search_dir.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                continue

            manifest_file = sub_dir / "manifest.yaml"
            if manifest_file.exists():
                try:
                    manifest = self.validate_skill(sub_dir)
                    self.register_skill(manifest, sub_dir)
                    manifests.append(manifest)
                except SkillValidationError:
                    # Skip invalid packages during passive discovery, but log or re-raise if explicitly targeted
                    pass

        return manifests

    def resolve_skill_version(self, skill_id: str, version_spec: str = "latest") -> SkillPackage:
        """Resolve a specific or latest semantic version for a skill ID."""
        normalized_id = skill_id.strip().lower()
        if normalized_id not in self._registry or not self._registry[normalized_id]:
            raise SkillValidationError(f"Skill '{skill_id}' is not registered in registry")

        available_versions = self._registry[normalized_id]

        if version_spec == "latest" or not version_spec:
            # Sort versions by semantic versioning descending
            sorted_versions = sorted(
                available_versions.keys(),
                key=parse_semver_key,
                reverse=True,
            )
            latest_version = sorted_versions[0]
            return available_versions[latest_version]

        # Exact match requested
        if version_spec in available_versions:
            return available_versions[version_spec]

        raise SkillValidationError(
            f"Skill '{skill_id}' version '{version_spec}' not found. "
            f"Available versions: {list(available_versions.keys())}"
        )

    def check_dependencies(self, skill_id: str, version: str | None = None) -> tuple[bool, list[str]]:
        """Verify that all dependencies declared by a skill are registered and available."""
        package = self.resolve_skill_version(skill_id, version or "latest")
        missing_dependencies: list[str] = []

        for dep in package.manifest.dependencies:
            dep_clean = dep.strip()
            # Match optional semver constraint like 'system-architecture>=1.0.0'
            match = re.match(r"^([a-z0-9-]+)(?:([><=]+)(.+))?$", dep_clean)
            if not match:
                missing_dependencies.append(dep_clean)
                continue

            dep_id = match.group(1).lower()
            op = match.group(2)
            required_ver = match.group(3)

            if dep_id not in self._registry or not self._registry[dep_id]:
                missing_dependencies.append(dep_clean)
                continue

            if op and required_ver:
                req_key = parse_semver_key(required_ver)
                # Check if any registered version satisfies
                satisfied = False
                for avail_v in self._registry[dep_id].keys():
                    avail_key = parse_semver_key(avail_v)
                    if op == ">=" and avail_key >= req_key:
                        satisfied = True
                        break
                    elif op == "==" and avail_key == req_key:
                        satisfied = True
                        break
                    elif op == ">" and avail_key > req_key:
                        satisfied = True
                        break
                if not satisfied:
                    missing_dependencies.append(dep_clean)

        return (len(missing_dependencies) == 0, missing_dependencies)

    def resolve_required_capabilities(self, skill_ids: list[str]) -> list[str]:
        """Aggregate unique required capabilities across all specified skills."""
        capabilities: set[str] = set()
        for s_id in skill_ids:
            try:
                pkg = self.resolve_skill_version(s_id, "latest")
                capabilities.update(pkg.manifest.required_capabilities)
            except SkillValidationError:
                pass
        return sorted(list(capabilities))

    def select_skills_for_task(
        self,
        role: str,
        task_domain: str,
        requested_skills: list[str] | None = None,
        active_grants: list[str] | None = None,
    ) -> list[SkillPackage]:
        """Select, validate, and load skills for a specific agent role and task.

        Enforces:
        1. Role compatibility (role must be supported by every selected skill).
        2. Progressive disclosure (only requested/relevant skills loaded, no prompt bloat).
        3. Capability grants (every required capability must be covered by active_grants if supplied).
        4. Dependency integrity.
        """
        profile = get_agent_profile(role)
        target_skill_ids = requested_skills or []

        # If none requested, default to role-supported skills matching task_domain if possible
        if not target_skill_ids:
            for s_id in profile.supported_skills:
                if task_domain.lower() in s_id.lower() or s_id in self._registry:
                    target_skill_ids.append(s_id)
                    break

        selected_packages: list[SkillPackage] = []

        for skill_id in target_skill_ids:
            pkg = self.resolve_skill_version(skill_id, "latest")

            # 1. Enforce Role Compatibility
            normalized_role = role.strip().lower()
            if normalized_role not in pkg.manifest.supported_roles:
                raise SkillRoleError(
                    f"Agent role '{role}' is not authorized for skill '{skill_id}'. "
                    f"Supported roles: {pkg.manifest.supported_roles}"
                )

            # 2. Check Dependencies
            ok, missing = self.check_dependencies(skill_id)
            if not ok:
                raise SkillDependencyError(f"Skill '{skill_id}' has unsatisfied dependencies: {missing}")

            # 3. Check Required Capabilities against active_grants
            if active_grants is not None:
                for req_cap in pkg.manifest.required_capabilities:
                    cap_matched = False
                    for grant in active_grants:
                        if grant.endswith(".*"):
                            prefix = grant[:-2]
                            if req_cap.startswith(prefix):
                                cap_matched = True
                                break
                        elif req_cap.lower() == grant.lower():
                            cap_matched = True
                            break
                    if not cap_matched:
                        raise SkillSecurityError(
                            f"Skill '{skill_id}' requires capability '{req_cap}', "
                            f"but calling agent does not hold an active grant for it."
                        )

            selected_packages.append(pkg)

        return selected_packages

    def load_skill_instructions(self, skill_id: str, version: str | None = None) -> str:
        """Load the formatted execution instructions for a skill."""
        pkg = self.resolve_skill_version(skill_id, version or "latest")
        output = [
            f"# Active Skill: {pkg.manifest.name} (v{pkg.manifest.version})",
            f"**Description**: {pkg.manifest.description}",
            f"**Category**: {pkg.manifest.category}",
            "",
            "## Required Verification Checklist",
        ]
        for rule in pkg.manifest.verification_rules:
            output.append(f"- [ ] {rule}")

        output.append("")
        output.append("## Operational Instructions & Methodology")
        output.append(pkg.instructions_markdown)

        return "\n".join(output)

    def record_skill_usage(
        self,
        mission_id: UUID,
        task_id: UUID,
        role: str,
        skill_id: str,
        version: str,
        status: str = "SUCCESS",
        details: dict[str, Any] | None = None,
    ) -> SkillUsageRecord:
        """Record an authoritative audit log entry for a skill invocation."""
        record = SkillUsageRecord(
            mission_id=mission_id,
            task_id=task_id,
            agent_role=role,
            skill_id=skill_id,
            version=version,
            status=status,
            invoked_at=datetime.now(UTC),
            details=details or {},
        )
        self._usage_log.append(record)
        return record

    def get_usage_records(self, task_id: UUID | None = None) -> list[SkillUsageRecord]:
        """Query recorded skill usage."""
        if task_id:
            return [r for r in self._usage_log if r.task_id == task_id]
        return list(self._usage_log)

    def verify_skill_integrity(self, skill_id: str, version: str | None = None) -> bool:
        """Verify the cryptographic integrity of a registered skill package."""
        pkg = self.resolve_skill_version(skill_id, version or "latest")
        current_checksum = self.compute_package_checksum(pkg.skill_dir)
        return current_checksum == pkg.computed_checksum

    def install_external_skill(
        self,
        package_path: Path,
        source_id: str,
        expected_checksum: str | None = None,
    ) -> SkillManifest:
        """Install an external skill package subject to authorization and integrity policies."""
        # 1. Authorize Source
        normalized_source = source_id.strip().lower()
        if normalized_source not in self._approved_sources:
            raise SkillSecurityError(
                f"External skill installation denied: Source '{source_id}' is not in the approved sources allowlist: {sorted(list(self._approved_sources))}"
            )

        # 2. Validate Manifest & Directory Structure
        manifest = self.validate_skill(package_path)

        # 3. Verify Checksum / Integrity
        actual_checksum = self.compute_package_checksum(package_path)
        if expected_checksum and actual_checksum != expected_checksum:
            raise SkillIntegrityError(
                f"External skill checksum mismatch. Expected: {expected_checksum}, Actual: {actual_checksum}"
            )

        # 4. Register as VERIFIED_PARTNER / VERIFIED_INTERNAL
        trust_level = (
            SkillSourceTrust.VERIFIED_INTERNAL
            if normalized_source in ("internal", "core")
            else SkillSourceTrust.VERIFIED_PARTNER
        )

        manifest.source_trust = trust_level
        manifest.checksum_sha256 = actual_checksum
        self.register_skill(manifest, package_path, source_trust=trust_level)

        return manifest
