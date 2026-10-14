"""Comprehensive verification tests for Phase 1: Project Initialization."""

from pathlib import Path

import httpx
import pytest
import yaml

from syntra.api.app import app
from syntra.core.config import get_settings


@pytest.mark.asyncio
async def test_readiness_probe_endpoints():
    """Verify that both /health/ready and /api/health/ready return structured readiness data."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # /health/ready
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "database" in data["components"]
        assert data["components"]["database"]["status"] == "healthy"
        assert "sandbox" in data["components"]
        assert data["components"]["sandbox"]["status"] == "healthy"
        assert "redis" in data["components"]
        assert "minio" in data["components"]

        # /api/health/ready
        api_resp = await client.get("/api/health/ready")
        assert api_resp.status_code == 200
        api_data = api_resp.json()
        assert api_data["status"] == "ready"


def test_all_16_skills_manifests():
    """Verify all 16 required skill packages have valid manifests and documentation."""
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
        "documentation-generation",
    ]

    skills_root = Path("skills")
    assert skills_root.exists(), "skills directory must exist"

    found_skills = [d.name for d in skills_root.iterdir() if d.is_dir()]
    for expected in expected_skills:
        assert expected in found_skills, f"Skill '{expected}' is missing from skills/"

        skill_dir = skills_root / expected
        manifest_file = skill_dir / "manifest.yaml"
        doc_file = skill_dir / "SKILL.md"

        assert manifest_file.exists(), f"manifest.yaml missing in {skill_dir}"
        assert doc_file.exists(), f"SKILL.md missing in {skill_dir}"

        manifest_data = yaml.safe_load(manifest_file.read_text())
        assert manifest_data["name"] == expected
        assert "version" in manifest_data
        assert "description" in manifest_data
        assert "compatible_roles" in manifest_data
        assert isinstance(manifest_data["compatible_roles"], list)
        assert len(manifest_data["compatible_roles"]) > 0
        assert "required_tools" in manifest_data
        assert isinstance(manifest_data["required_tools"], list)

        doc_content = doc_file.read_text()
        assert len(doc_content.strip()) > 50, f"SKILL.md in {skill_dir} must contain substantive instructions"


def test_monorepo_packages_structure():
    """Verify Section 24 monorepo packages and apps structure."""
    expected_packages = [
        "domain",
        "contracts",
        "persistence",
        "agents",
        "model_runtime",
        "mcp_gateway",
        "tool_registry",
        "skill_registry",
        "sandbox",
        "memory",
        "evaluation",
        "security",
        "telemetry",
    ]

    packages_root = Path("packages")
    assert packages_root.exists(), "packages/ directory must exist"

    for pkg in expected_packages:
        pkg_dir = packages_root / pkg
        assert pkg_dir.exists(), f"Package directory {pkg_dir} must exist"
        assert (pkg_dir / "__init__.py").exists(), f"__init__.py missing in {pkg_dir}"
        assert (pkg_dir / "py.typed").exists(), f"py.typed missing in {pkg_dir}"

    expected_apps = [
        "api",
        "orchestrator",
        "scheduler",
        "worker_controller",
        "mcp_server",
    ]

    apps_root = Path("apps")
    assert apps_root.exists(), "apps/ directory must exist"

    for app_name in expected_apps:
        app_dir = apps_root / app_name
        assert app_dir.exists(), f"App directory {app_dir} must exist"
        assert (app_dir / "__init__.py").exists(), f"__init__.py missing in {app_dir}"
        assert (app_dir / "main.py").exists(), f"main.py missing in {app_dir}"


def test_configuration_infrastructure_fields():
    """Verify that settings include Redis and MinIO / S3 configuration parameters."""
    settings = get_settings()
    assert hasattr(settings, "redis_url")
    assert settings.redis_url.startswith("redis://")
    assert hasattr(settings, "s3_endpoint")
    assert hasattr(settings, "s3_access_key")
    assert hasattr(settings, "s3_secret_key")
    assert hasattr(settings, "s3_bucket")
    assert hasattr(settings, "s3_secure")


def test_compose_yaml_services():
    """Verify compose.yaml contains postgres, redis, minio, and backend services with health checks."""
    compose_path = Path("compose.yaml")
    assert compose_path.exists(), "compose.yaml must exist"

    compose_data = yaml.safe_load(compose_path.read_text())
    services = compose_data.get("services", {})

    for service_name in ["backend", "postgres", "redis", "minio"]:
        assert service_name in services, f"Service '{service_name}' must be declared in compose.yaml"

    assert "healthcheck" in services["postgres"], "postgres must declare a healthcheck"
    assert "healthcheck" in services["redis"], "redis must declare a healthcheck"
    assert "healthcheck" in services["minio"], "minio must declare a healthcheck"
