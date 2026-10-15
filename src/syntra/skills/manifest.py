"""SYNTRA Skill Package Manifest Contract and Validation.

Implements the official Pydantic v2 SkillManifest schema with semantic versioning,
input/output contracts, capability declarations, and integrity checks.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEMVER_REGEX = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SkillSourceTrust(str, Enum):
    TRUSTED_CORE = "TRUSTED_CORE"
    VERIFIED_INTERNAL = "VERIFIED_INTERNAL"
    VERIFIED_PARTNER = "VERIFIED_PARTNER"
    UNAPPROVED_EXTERNAL = "UNAPPROVED_EXTERNAL"


class SkillValidationError(Exception):
    """Raised when a skill manifest or directory structure fails validation."""


class SkillIntegrityError(Exception):
    """Raised when skill checksum or file contents have been altered."""


class SkillDependencyError(Exception):
    """Raised when a skill's required dependencies cannot be resolved."""


class SkillSecurityError(Exception):
    """Raised when a skill violates security policy or capability restrictions."""


class SkillRoleError(Exception):
    """Raised when a skill is assigned to an incompatible or unauthorized agent role."""


class SkillReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Title of the reference standard or guide")
    uri: str = Field(..., description="URL or relative path to authoritative reference")


class SkillEvaluationCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Unique test case identifier")
    description: str = Field(default="", description="Test objective")
    input_data: dict[str, Any] = Field(default_factory=dict, description="Input fixture data")
    expected_status: str = Field(default="SUCCESS", description="Expected execution status")


class SkillManifest(BaseModel):
    """Authoritative Pydantic contract for SYNTRA Skill Manifests."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique lowercase kebab-case skill identifier")
    name: str | None = Field(default=None, description="Human-readable skill name or identifier")
    version: str = Field(..., description="Semantic version string (e.g. 1.0.0)")
    description: str = Field(..., min_length=10, description="Detailed explanation of the engineering skill")
    category: str = Field(default="engineering", description="Skill category or functional domain")

    supported_roles: list[str] = Field(
        default_factory=list,
        description="List of agent roles authorized to load and execute this skill",
    )
    compatible_roles: list[str] = Field(
        default_factory=list,
        description="Alias for supported_roles maintaining backwards compatibility",
    )

    required_inputs: list[str] = Field(
        default_factory=list,
        description="Required input evidence or data keys (e.g. task_specification, git_diff)",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Required capability permission keys evaluated by the Policy Engine",
    )
    required_tools: list[str] = Field(
        default_factory=list,
        description="List of specific MCP or workspace tools required for execution",
    )

    output_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema dictionary validating the skill's output artifacts",
    )
    verification_rules: list[str] = Field(
        default_factory=list,
        description="Checklist of explicit verification assertions required before approval",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="List of dependent skill IDs or version specifications (e.g. 'system-architecture>=1.0.0')",
    )
    references: list[dict[str, str]] = Field(
        default_factory=list,
        description="Authoritative reference documents, checklists, or industry standards",
    )
    evaluation_cases: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Deterministic evaluation fixtures for benchmark validation",
    )

    checksum_sha256: str | None = Field(
        default=None,
        description="Cryptographic SHA-256 digest of the manifest and instruction contents",
    )
    source_trust: SkillSourceTrust = Field(
        default=SkillSourceTrust.TRUSTED_CORE,
        description="Trust classification of the skill origin",
    )

    @field_validator("id")
    @classmethod
    def validate_id_slug(cls, v: str) -> str:
        v = v.strip().lower()
        if not SLUG_REGEX.match(v):
            raise ValueError(f"Skill id '{v}' must be lowercase kebab-case (e.g. 'backend-api-development')")
        return v

    @field_validator("version")
    @classmethod
    def validate_semver(cls, v: str) -> str:
        v = v.strip()
        if not SEMVER_REGEX.match(v):
            raise ValueError(f"Skill version '{v}' is not a valid Semantic Version (MAJOR.MINOR.PATCH)")
        return v

    @model_validator(mode="after")
    def sync_name_and_roles(self) -> SkillManifest:
        # Default name to id if omitted
        if not self.name:
            self.name = self.id

        # Synchronize supported_roles and compatible_roles
        if self.supported_roles and not self.compatible_roles:
            self.compatible_roles = list(self.supported_roles)
        elif self.compatible_roles and not self.supported_roles:
            self.supported_roles = list(self.compatible_roles)

        # Normalize role names to lowercase
        self.supported_roles = [r.strip().lower() for r in self.supported_roles]
        self.compatible_roles = [r.strip().lower() for r in self.compatible_roles]

        if not self.supported_roles:
            raise ValueError("Skill manifest must specify at least one supported role in supported_roles")

        return self
