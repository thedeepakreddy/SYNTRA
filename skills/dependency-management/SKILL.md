# Skill: Dependency Management

## Overview
Maintains reproducible dependency trees, performs security advisory auditing, updates lockfiles, and pins versions deterministically.

## Required Input Evidence
1. **Dependency Request**: Package name and required version constraint.
2. **Manifest Path**: `pyproject.toml` or `package.json`.

## Step-by-Step Procedure
1. **Inspect Existing Dependencies**:
   - Check current lockfile and dependency tree for compatibility.
2. **Check Vulnerability Advisories**:
   - Audit target package against PyPI/OSV advisory databases.
3. **Update Manifest & Lockfile**:
   - Execute `uv add <package>` or edit `pyproject.toml` with strict pins.
   - Regenerate `uv.lock`.
4. **Verify Environment Consistency**:
   - Run `uv sync --locked` to ensure lockfile is internally consistent.
5. **Run Test Regression**:
   - Execute full test suite to confirm zero dependency breakage.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `LockfileDiff`: Updated `pyproject.toml` and `uv.lock` diff.

## Verification Procedure
- `uv sync --locked` completes with exit code 0.

## Failure and Escalation Conditions
- Escalate if new dependency introduces transitive security vulnerabilities or license incompatibilities (GPL in proprietary code).
