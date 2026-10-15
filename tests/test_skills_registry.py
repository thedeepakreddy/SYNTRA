"""Comprehensive Test Suite for SYNTRA Phase 5: Agent Skills and Capability Registry.

Validates all 10 required test criteria:
1. Valid manifest loads.
2. Invalid manifest fails.
3. Missing dependencies fail.
4. Unsupported agent role fails.
5. Missing capability fails.
6. Correct skill version resolves.
7. Irrelevant skills are excluded.
8. Skill integrity validation works.
9. Unapproved external installation fails.
10. Recorded invocation references exact versions.
Plus deterministic evaluation harness and capability profile verification.
"""

from pathlib import Path
from uuid import uuid4

import pytest
import yaml

from syntra.domain.entities import AgentRole
from syntra.skills.evaluator import SkillEvaluator
from syntra.skills.manifest import (
    SkillDependencyError,
    SkillIntegrityError,
    SkillRoleError,
    SkillSecurityError,
    SkillSourceTrust,
    SkillValidationError,
)
from syntra.skills.profiles import (
    AgentCapabilityProfile,
    get_agent_profile,
)
from syntra.skills.registry import SkillRegistry


@pytest.fixture
def skills_registry() -> SkillRegistry:
    """Fixture providing an initialized SkillRegistry with discovered skills."""
    registry = SkillRegistry(root_dir=Path("skills"))
    registry.discover_skills()
    return registry


def test_01_valid_manifest_loads(skills_registry: SkillRegistry):
    """Test 1: Valid manifests load correctly and populate all required fields."""
    backend_pkg = skills_registry.resolve_skill_version("backend-api-development", "1.0.0")
    assert backend_pkg is not None
    manifest = backend_pkg.manifest

    assert manifest.id == "backend-api-development"
    assert manifest.version == "1.0.0"
    assert "backend_engineer" in manifest.supported_roles
    assert "task_specification" in manifest.required_inputs
    assert "syntra.write_file" in manifest.required_capabilities
    assert "syntra.write_file" in manifest.required_tools
    assert isinstance(manifest.output_schema, dict)
    assert len(manifest.verification_rules) > 0
    assert len(manifest.references) > 0
    assert len(manifest.evaluation_cases) > 0

    # Test requirements-analysis
    req_pkg = skills_registry.resolve_skill_version("requirements-analysis", "1.0.0")
    assert req_pkg.manifest.id == "requirements-analysis"
    assert "product_manager" in req_pkg.manifest.supported_roles


def test_02_invalid_manifest_fails(tmp_path: Path):
    """Test 2: Invalid manifests fail with descriptive validation errors."""
    registry = SkillRegistry(root_dir=tmp_path)

    # A. Missing required description
    bad_dir = tmp_path / "bad-skill-1"
    bad_dir.mkdir()
    (bad_dir / "manifest.yaml").write_text("id: bad-skill-1\nversion: 1.0.0\nsupported_roles: [backend_engineer]")
    (bad_dir / "SKILL.md").write_text(
        "Substantive instructions for bad skill 1 exceeding fifty characters in total length."
    )
    with pytest.raises(SkillValidationError, match="Skill manifest validation failed"):
        registry.validate_skill(bad_dir)

    # B. Invalid Semantic Versioning
    bad_dir_ver = tmp_path / "bad-skill-ver"
    bad_dir_ver.mkdir()
    bad_manifest = {
        "id": "bad-skill-ver",
        "version": "v1.0-alpha_beta",  # Invalid semver
        "description": "Valid description with sufficient length.",
        "supported_roles": ["backend_engineer"],
    }
    (bad_dir_ver / "manifest.yaml").write_text(yaml.dump(bad_manifest))
    (bad_dir_ver / "SKILL.md").write_text(
        "Substantive instructions for bad skill ver exceeding fifty characters in total length."
    )
    with pytest.raises(SkillValidationError, match="not a valid Semantic Version"):
        registry.validate_skill(bad_dir_ver)

    # C. Invalid uppercase slug ID
    bad_dir_slug = tmp_path / "BadSkill"
    bad_dir_slug.mkdir()
    bad_manifest_slug = {
        "id": "BadSkill_1",  # Invalid slug
        "version": "1.0.0",
        "description": "Valid description with sufficient length.",
        "supported_roles": ["backend_engineer"],
    }
    (bad_dir_slug / "manifest.yaml").write_text(yaml.dump(bad_manifest_slug))
    (bad_dir_slug / "SKILL.md").write_text(
        "Substantive instructions for bad skill slug exceeding fifty characters in total length."
    )
    with pytest.raises(SkillValidationError, match="must be lowercase kebab-case"):
        registry.validate_skill(bad_dir_slug)

    # D. Missing SKILL.md file
    no_doc_dir = tmp_path / "no-doc-skill"
    no_doc_dir.mkdir()
    valid_m = {
        "id": "no-doc-skill",
        "version": "1.0.0",
        "description": "Valid description with sufficient length.",
        "supported_roles": ["backend_engineer"],
    }
    (no_doc_dir / "manifest.yaml").write_text(yaml.dump(valid_m))
    with pytest.raises(SkillValidationError, match="Missing SKILL.md"):
        registry.validate_skill(no_doc_dir)


def test_03_missing_dependencies_fail(tmp_path: Path):
    """Test 3: Missing dependencies fail dependency check and task selection."""
    registry = SkillRegistry(root_dir=tmp_path)

    # Skill with non-existent dependency
    dep_skill_dir = tmp_path / "dependent-skill"
    dep_skill_dir.mkdir()
    dep_manifest = {
        "id": "dependent-skill",
        "version": "1.0.0",
        "description": "Requires non-existent dependency skill.",
        "supported_roles": ["backend_engineer"],
        "dependencies": ["non-existent-framework>=2.0.0"],
        "required_capabilities": ["syntra.read_file"],
    }
    (dep_skill_dir / "manifest.yaml").write_text(yaml.dump(dep_manifest))
    (dep_skill_dir / "SKILL.md").write_text(
        "Substantive instructions for dependent skill exceeding fifty characters in total length."
    )

    manifest = registry.validate_skill(dep_skill_dir)
    registry.register_skill(manifest, dep_skill_dir)

    # Check dependency failure
    satisfied, missing = registry.check_dependencies("dependent-skill")
    assert not satisfied
    assert "non-existent-framework>=2.0.0" in missing

    # Selection raises SkillDependencyError
    with pytest.raises(SkillDependencyError, match="unsatisfied dependencies"):
        registry.select_skills_for_task(
            role="backend_engineer",
            task_domain="testing",
            requested_skills=["dependent-skill"],
            active_grants=["syntra.read_file"],
        )


def test_04_unsupported_agent_role_fails(skills_registry: SkillRegistry):
    """Test 4: Loading skill with an unsupported agent role fails with SkillRoleError."""
    # backend-api-development is supported for backend_engineer, NOT product_manager
    with pytest.raises(SkillRoleError, match="Agent role 'product_manager' is not authorized for skill"):
        skills_registry.select_skills_for_task(
            role="product_manager",
            task_domain="api",
            requested_skills=["backend-api-development"],
            active_grants=["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        )

    # Verify role profile checks
    pm_profile = get_agent_profile("product_manager")
    assert not pm_profile.is_skill_supported("backend-api-development")
    assert pm_profile.is_skill_supported("requirements-analysis")


def test_05_missing_capability_fails(skills_registry: SkillRegistry):
    """Test 5: Missing capability grant fails with SkillSecurityError."""
    # backend-api-development requires syntra.write_file, syntra.run_command, syntra.read_file
    with pytest.raises(SkillSecurityError, match="requires capability 'syntra.write_file'"):
        skills_registry.select_skills_for_task(
            role="backend_engineer",
            task_domain="api",
            requested_skills=["backend-api-development"],
            active_grants=["syntra.read_file"],  # Missing write_file and run_command
        )

    # With full grants, selection succeeds
    selected = skills_registry.select_skills_for_task(
        role="backend_engineer",
        task_domain="api",
        requested_skills=["backend-api-development"],
        active_grants=["syntra.read_file", "syntra.write_file", "syntra.run_command", "syntra.git_diff"],
    )
    assert len(selected) == 1
    assert selected[0].manifest.id == "backend-api-development"


def test_06_correct_skill_version_resolves(tmp_path: Path):
    """Test 6: Correct skill version resolves via latest or exact semver."""
    registry = SkillRegistry(root_dir=tmp_path)

    v1_dir = tmp_path / "test-v1"
    v1_dir.mkdir()
    (v1_dir / "manifest.yaml").write_text(
        yaml.dump(
            {
                "id": "version-test",
                "version": "1.0.0",
                "description": "Version 1.0.0 description with required length.",
                "supported_roles": ["backend_engineer"],
            }
        )
    )
    (v1_dir / "SKILL.md").write_text("Instructions for version 1.0.0 with adequate character count length.")

    v2_dir = tmp_path / "test-v2"
    v2_dir.mkdir()
    (v2_dir / "manifest.yaml").write_text(
        yaml.dump(
            {
                "id": "version-test",
                "version": "2.1.0",
                "description": "Version 2.1.0 description with required length.",
                "supported_roles": ["backend_engineer"],
            }
        )
    )
    (v2_dir / "SKILL.md").write_text("Instructions for version 2.1.0 with adequate character count length.")

    registry.register_skill(registry.validate_skill(v1_dir), v1_dir)
    registry.register_skill(registry.validate_skill(v2_dir), v2_dir)

    # Resolve latest
    latest_pkg = registry.resolve_skill_version("version-test", "latest")
    assert latest_pkg.manifest.version == "2.1.0"

    # Resolve exact
    v1_pkg = registry.resolve_skill_version("version-test", "1.0.0")
    assert v1_pkg.manifest.version == "1.0.0"

    # Non-existent version raises
    with pytest.raises(SkillValidationError, match="version '3.0.0' not found"):
        registry.resolve_skill_version("version-test", "3.0.0")


def test_07_irrelevant_skills_are_excluded(skills_registry: SkillRegistry):
    """Test 7: Irrelevant skills are excluded (progressive disclosure)."""
    # A backend task requesting only backend-api-development should not load frontend or devops skills
    selected = skills_registry.select_skills_for_task(
        role="backend_engineer",
        task_domain="api",
        requested_skills=["backend-api-development"],
        active_grants=["syntra.*"],
    )
    loaded_ids = [p.manifest.id for p in selected]
    assert loaded_ids == ["backend-api-development"]
    assert "frontend-development" not in loaded_ids
    assert "devops-and-ci" not in loaded_ids
    assert "requirements-analysis" not in loaded_ids


def test_08_skill_integrity_validation_works(tmp_path: Path):
    """Test 8: Skill cryptographic integrity validation detects tampering."""
    registry = SkillRegistry(root_dir=tmp_path)

    skill_dir = tmp_path / "integrity-skill"
    skill_dir.mkdir()
    (skill_dir / "manifest.yaml").write_text(
        yaml.dump(
            {
                "id": "integrity-skill",
                "version": "1.0.0",
                "description": "Integrity test skill with adequate description length.",
                "supported_roles": ["backend_engineer"],
            }
        )
    )
    doc_path = skill_dir / "SKILL.md"
    doc_path.write_text("Original pristine instructions with sufficient length.")

    registry.register_skill(registry.validate_skill(skill_dir), skill_dir)
    assert registry.verify_skill_integrity("integrity-skill", "1.0.0") is True

    # Tamper with SKILL.md
    doc_path.write_text("TAMPERED INSTRUCTIONS INJECTED BY ATTACKER")
    assert registry.verify_skill_integrity("integrity-skill", "1.0.0") is False


def test_09_unapproved_external_installation_fails(tmp_path: Path):
    """Test 9: Unapproved external skill installation fails with SkillSecurityError."""
    registry = SkillRegistry(root_dir=tmp_path)

    ext_dir = tmp_path / "external-skill"
    ext_dir.mkdir()
    (ext_dir / "manifest.yaml").write_text(
        yaml.dump(
            {
                "id": "external-skill",
                "version": "1.0.0",
                "description": "External untrusted skill with adequate description length.",
                "supported_roles": ["backend_engineer"],
            }
        )
    )
    (ext_dir / "SKILL.md").write_text("External instructions with sufficient length for validation.")

    # 1. Deny installation from unapproved source
    with pytest.raises(SkillSecurityError, match="External skill installation denied"):
        registry.install_external_skill(ext_dir, source_id="untrusted-random-repo")

    # 2. Deny installation if checksum mismatch
    with pytest.raises(SkillIntegrityError, match="External skill checksum mismatch"):
        registry.install_external_skill(ext_dir, source_id="trusted-partner", expected_checksum="bad_checksum_12345")

    # 3. Allow installation from approved source with valid checksum
    computed_checksum = registry.compute_package_checksum(ext_dir)
    installed_manifest = registry.install_external_skill(
        ext_dir, source_id="trusted-partner", expected_checksum=computed_checksum
    )
    assert installed_manifest.id == "external-skill"
    assert installed_manifest.source_trust == SkillSourceTrust.VERIFIED_PARTNER


def test_10_recorded_invocation_references_exact_versions(skills_registry: SkillRegistry):
    """Test 10: Recorded skill invocation references exact version and task UUID."""
    mission_id = uuid4()
    task_id = uuid4()

    record = skills_registry.record_skill_usage(
        mission_id=mission_id,
        task_id=task_id,
        role="backend_engineer",
        skill_id="backend-api-development",
        version="1.0.0",
        status="SUCCESS",
        details={"tokens_used": 1250},
    )

    assert record.id is not None
    assert record.mission_id == mission_id
    assert record.task_id == task_id
    assert record.agent_role == "backend_engineer"
    assert record.skill_id == "backend-api-development"
    assert record.version == "1.0.0"
    assert record.status == "SUCCESS"
    assert record.details["tokens_used"] == 1250

    # Query back
    records = skills_registry.get_usage_records(task_id=task_id)
    assert len(records) == 1
    assert records[0].id == record.id


def test_11_deterministic_evaluation_harness(skills_registry: SkillRegistry):
    """Test 11: SkillEvaluator deterministic evaluation of execution readiness and output schemas."""
    evaluator = SkillEvaluator(skills_registry)

    # 1. Successful evaluation with valid inputs, tools, capabilities, and outputs
    valid_res = evaluator.evaluate_execution_readiness(
        skill_id="backend-api-development",
        role="backend_engineer",
        inputs={
            "task_specification": "Build items endpoint",
            "api_contracts": "OpenAPI spec",
            "sandbox_workspace": "/tmp/sandbox",
        },
        available_tools=["syntra.read_file", "syntra.write_file", "syntra.run_command", "syntra.git_diff"],
        available_capabilities=["syntra.read_file", "syntra.write_file", "syntra.run_command", "syntra.git_diff"],
        proposed_output={
            "unified_diff": "diff content",
            "changed_files": ["api.py"],
            "unit_test_results": {"passed": 5},
        },
    )
    assert valid_res.success is True
    assert len(valid_res.errors) == 0
    assert valid_res.checked_inputs is True
    assert valid_res.checked_role is True
    assert valid_res.checked_tools is True
    assert valid_res.checked_capabilities is True
    assert valid_res.checked_output_schema is True

    # 2. Missing input evaluation failure
    missing_input_res = evaluator.evaluate_execution_readiness(
        skill_id="backend-api-development",
        role="backend_engineer",
        inputs={"task_specification": "Only 1 input provided"},
        available_tools=["syntra.read_file", "syntra.write_file", "syntra.run_command", "syntra.git_diff"],
        available_capabilities=["syntra.*"],
    )
    assert missing_input_res.success is False
    assert any("Missing required inputs" in err for err in missing_input_res.errors)

    # 3. Missing required tools failure
    missing_tool_res = evaluator.evaluate_execution_readiness(
        skill_id="backend-api-development",
        role="backend_engineer",
        inputs={"task_specification": "Build items", "api_contracts": "Spec", "sandbox_workspace": "/tmp"},
        available_tools=["syntra.read_file"],  # Missing write_file, run_command, git_diff
        available_capabilities=["syntra.*"],
    )
    assert missing_tool_res.success is False
    assert any("Missing required tools" in err for err in missing_tool_res.errors)

    # 4. Output schema mismatch failure (missing required property in output)
    bad_output_res = evaluator.evaluate_execution_readiness(
        skill_id="backend-api-development",
        role="backend_engineer",
        inputs={"task_specification": "Spec", "api_contracts": "Contracts", "sandbox_workspace": "/tmp"},
        available_tools=["syntra.read_file", "syntra.write_file", "syntra.run_command", "syntra.git_diff"],
        available_capabilities=["syntra.*"],
        proposed_output={"changed_files": ["api.py"]},  # Missing unified_diff and unit_test_results
    )
    assert bad_output_res.success is False
    assert any("missing required properties" in err for err in bad_output_res.errors)


def test_12_all_10_agent_capability_profiles():
    """Test 12: Verify all 10 agent roles have defined capability profiles with limitations."""
    all_roles = [
        AgentRole.PRODUCT_MANAGER,
        AgentRole.SOFTWARE_ARCHITECT,
        AgentRole.ENGINEERING_MANAGER,
        AgentRole.BACKEND_ENGINEER,
        AgentRole.FRONTEND_ENGINEER,
        AgentRole.QA_ENGINEER,
        AgentRole.DEVOPS_ENGINEER,
        AgentRole.SECURITY_REVIEWER,
        AgentRole.CODE_REVIEWER,
        AgentRole.DEBUGGING_SPECIALIST,
    ]

    for role in all_roles:
        profile = get_agent_profile(role)
        assert isinstance(profile, AgentCapabilityProfile)
        assert profile.role == role
        assert len(profile.supported_skills) > 0
        assert len(profile.required_artifact_types) > 0
        assert len(profile.allowed_tool_capabilities) > 0
        assert len(profile.execution_limitations) > 0

        # Also test retrieval by string
        profile_by_str = get_agent_profile(role.value)
        assert profile_by_str.role == role


def test_13_discover_all_16_skills(skills_registry: SkillRegistry):
    """Test 13: Verify all 16 standard skills are discovered and loaded."""
    expected_skills = [
        "requirements-analysis",
        "system-architecture",
        "task-decomposition",
        "backend-api-development",
        "frontend-development",
        "database-engineering",
        "test-driven-development",
        "debugging-and-root-cause-analysis",
        "code-review",
        "security-review",
        "git-workflow",
        "devops-and-ci",
        "api-contract-testing",
        "dependency-management",
        "integration-testing",
        "technical-documentation",
    ]

    discovered = skills_registry.registered_skill_ids
    for exp in expected_skills:
        assert exp in discovered, f"Skill '{exp}' not discovered in registry"

    # Verify load_skill_instructions outputs formatted instructions
    instructions = skills_registry.load_skill_instructions("requirements-analysis")
    assert "# Active Skill: requirements-analysis" in instructions
    assert "Operational Instructions & Methodology" in instructions
    assert len(instructions) > 200
