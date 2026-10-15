# Skill: DevOps and CI/CD

## Overview
Authors secure, reproducible container manifests, local Compose orchestration environments, and automated CI/CD pipeline definitions.

## Required Input Evidence
1. **System Architecture Specification**: Service components, ports, and storage volumes.
2. **Dependency Manifests**: Python `pyproject.toml`, Node `package.json`.

## Step-by-Step Procedure
1. **Author Multi-Stage Dockerfile**:
   - Builder stage: Install build tools and compile dependencies.
   - Runtime stage: Use minimal distroless/slim base image, copy artifacts, set `USER nonroot`.
2. **Configure Compose Services**:
   - Declare environment variables, volume mappings, and health check probes.
3. **Configure CI Automation**:
   - Write GitHub Actions workflow (`.github/workflows/ci.yml`) executing lint, typecheck, and pytest.
4. **Build Verification**:
   - Validate Dockerfile syntax with `dockerfile_lint` or static checks.
5. **Publish Infrastructure Artifacts**:
   - Output container manifests and pipeline configuration.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `ContainerManifest`: Dockerfile and Compose definitions.
- `CIPipelineConfig`: GitHub Actions workflow YAML.

## Verification Procedure
- Verify non-root execution baseline.
- Verify health check probes respond correctly.

## Failure and Escalation Conditions
- Escalate if privileged root execution is requested.
