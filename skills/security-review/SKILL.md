# Skill: Security Review

## Overview
Inspects source code diffs, dependencies, and configuration changes for security vulnerabilities, secret leakage, and permission escalations.

## Required Input Evidence
1. **Unified Diff Patch**: Proposed source code changes.
2. **Dependency Lockfile**: Updated dependency manifests (`uv.lock`, `package-lock.json`).
3. **Task Specification**: Intended changes.

## Step-by-Step Procedure
1. **Vulnerability Analysis (OWASP Top 10)**:
   - Check SQL queries for parameterization (no string formatting/concatenation).
   - Check file operations for path traversal (`../`) and safe path confinement.
   - Check shell invocations for command injection (`shell=False`, argument lists).
   - Check remote network calls for SSRF and IP validation.
2. **Secret & Credential Leakage Scan**:
   - Inspect diff for API keys, bearer tokens, private keys, passwords, or test credentials.
3. **Dependency CVE Audit**:
   - Cross-reference updated packages against vulnerability databases.
4. **Issue Line-Level Findings**:
   - Categorize findings by severity (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL).
5. **Issue Security Audit Report**:
   - Publish `SecurityAuditReport` artifact with PASS/FAIL status.

## Tool Requirements
- `syntra.read_file`, `syntra.workspace_search`, `syntra.security_scan`, `syntra.artifact_write`.

## Expected Output Artifacts
- `SecurityAuditReport`: Comprehensive security evaluation artifact.

## Verification Procedure
- Verify 0 Critical or High severity issues remain open for PASS verdict.

## Failure and Escalation Conditions
- Escalate immediately if diff attempts to alter core security policies or bypass approvals.
