# Skill: Security Review

## Overview
Perform static and dynamic security assessments of code changes and dependency updates.

## Methodology
1. **Threat Vectors**: Inspect for SQL injection, command execution, path traversal, and SSRF.
2. **Secret Detection**: Verify no hardcoded credentials, API keys, or tokens exist in diffs.
3. **Authorization**: Confirm tenant isolation and role permissions are strictly enforced.
