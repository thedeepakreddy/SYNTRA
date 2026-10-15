"""SYNTRA Deterministic Skill Evaluation Harness.

Validates skills against formal contracts, input requirements, role permissions,
tool prerequisites, version conflicts, and output JSON schemas.
Stores deterministic evaluation outcomes without making unsubstantiated LLM quality claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from syntra.skills.manifest import SkillManifest
from syntra.skills.registry import SkillRegistry


@dataclass
class SkillEvaluationResult:
    """Deterministic result of evaluating a skill execution or contract."""

    skill_id: str
    version: str
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_inputs: bool = False
    checked_role: bool = False
    checked_tools: bool = False
    checked_capabilities: bool = False
    checked_output_schema: bool = False
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = field(default_factory=dict)


class SkillEvaluator:
    """Evaluation engine for testing skill packages and execution readiness."""

    def __init__(self, registry: SkillRegistry | None = None):
        self.registry = registry or SkillRegistry()
        self._history: list[SkillEvaluationResult] = []

    def evaluate_manifest(self, raw_data: dict[str, Any]) -> SkillEvaluationResult:
        """Evaluate raw manifest data for structural and semantic validity."""
        skill_id = str(raw_data.get("id") or raw_data.get("name") or "unknown")
        version = str(raw_data.get("version") or "unknown")
        errors: list[str] = []

        try:
            SkillManifest(**raw_data)
        except Exception as e:
            errors.append(f"Manifest validation error: {e}")

        result = SkillEvaluationResult(
            skill_id=skill_id,
            version=version,
            success=len(errors) == 0,
            errors=errors,
            details={"raw_keys": list(raw_data.keys())},
        )
        self._history.append(result)
        return result

    def evaluate_execution_readiness(
        self,
        skill_id: str,
        role: str,
        inputs: dict[str, Any],
        available_tools: list[str],
        available_capabilities: list[str],
        proposed_output: dict[str, Any] | None = None,
        version: str = "latest",
    ) -> SkillEvaluationResult:
        """Deterministically evaluate whether an execution request satisfies all skill requirements."""
        errors: list[str] = []
        warnings: list[str] = []

        try:
            pkg = self.registry.resolve_skill_version(skill_id, version)
        except Exception as e:
            result = SkillEvaluationResult(
                skill_id=skill_id,
                version=version,
                success=False,
                errors=[f"Skill resolution failed: {e}"],
            )
            self._history.append(result)
            return result

        manifest = pkg.manifest

        # 1. Check Role Compatibility
        checked_role = True
        normalized_role = role.strip().lower()
        if normalized_role not in manifest.supported_roles:
            errors.append(
                f"Unsupported agent role '{role}' for skill '{skill_id}'. Supported roles: {manifest.supported_roles}"
            )

        # 2. Check Required Inputs
        checked_inputs = True
        missing_inputs = [req for req in manifest.required_inputs if req not in inputs or inputs[req] is None]
        if missing_inputs:
            errors.append(f"Missing required inputs for skill '{skill_id}': {missing_inputs}")

        # 3. Check Required Tools
        checked_tools = True
        available_tool_set = {t.lower() for t in available_tools}
        missing_tools = [tool for tool in manifest.required_tools if tool.lower() not in available_tool_set]
        if missing_tools:
            errors.append(f"Missing required tools for skill '{skill_id}': {missing_tools}")

        # 4. Check Required Capabilities
        checked_capabilities = True
        missing_caps: list[str] = []
        for req_cap in manifest.required_capabilities:
            matched = False
            for grant in available_capabilities:
                if grant.endswith(".*"):
                    if req_cap.lower().startswith(grant[:-2].lower()):
                        matched = True
                        break
                elif req_cap.lower() == grant.lower():
                    matched = True
                    break
            if not matched:
                missing_caps.append(req_cap)
        if missing_caps:
            errors.append(f"Missing required capabilities for skill '{skill_id}': {missing_caps}")

        # 5. Check Output Schema if proposed_output provided
        checked_output_schema = False
        if proposed_output is not None:
            checked_output_schema = True
            schema = manifest.output_schema
            if schema and isinstance(schema, dict):
                required_props = schema.get("required", [])
                missing_props = [p for p in required_props if p not in proposed_output]
                if missing_props:
                    errors.append(f"Output schema mismatch: missing required properties {missing_props}")

                props = schema.get("properties", {})
                for p_name, p_val in proposed_output.items():
                    if p_name in props:
                        expected_type = props[p_name].get("type")
                        if expected_type == "string" and not isinstance(p_val, str):
                            errors.append(f"Output property '{p_name}' expected string, got {type(p_val).__name__}")
                        elif expected_type == "integer" and not isinstance(p_val, int):
                            errors.append(f"Output property '{p_name}' expected integer, got {type(p_val).__name__}")
                        elif expected_type == "object" and not isinstance(p_val, dict):
                            errors.append(f"Output property '{p_name}' expected object, got {type(p_val).__name__}")
                        elif expected_type == "array" and not isinstance(p_val, list):
                            errors.append(f"Output property '{p_name}' expected array, got {type(p_val).__name__}")

        result = SkillEvaluationResult(
            skill_id=skill_id,
            version=manifest.version,
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checked_inputs=checked_inputs,
            checked_role=checked_role,
            checked_tools=checked_tools,
            checked_capabilities=checked_capabilities,
            checked_output_schema=checked_output_schema,
            details={
                "provided_input_keys": list(inputs.keys()),
                "available_tools_count": len(available_tools),
                "available_capabilities_count": len(available_capabilities),
            },
        )
        self._history.append(result)
        return result

    def get_history(self, skill_id: str | None = None) -> list[SkillEvaluationResult]:
        """Retrieve stored evaluation outcomes."""
        if skill_id:
            return [r for r in self._history if r.skill_id == skill_id]
        return list(self._history)
