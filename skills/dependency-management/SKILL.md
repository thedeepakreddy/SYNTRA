# Skill: Dependency Management

## Overview
Manage Python and platform dependencies deterministically using uv and pinned lockfiles.

## Methodology
1. **Minimal Additions**: Only add dependencies with proven architectural necessity.
2. **Deterministic Locking**: Maintain synchronized uv.lock with SHA-256 hashes.
3. **Vulnerability Audits**: Scan for CVEs and unmaintained libraries.
