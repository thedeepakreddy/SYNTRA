# Skill: Code Review

## Overview
Conducts rigorous, independent peer review of proposed unified diffs for correctness, architectural integrity, typing, test coverage, and code hygiene.

## Required Input Evidence
1. **Unified Diff Patch**: Proposed changes from execution engineer.
2. **Task Specification**: Scope of work and acceptance criteria.
3. **QA Verification Evidence**: Automated test execution reports.
4. **Security Audit Report**: Static and dynamic vulnerability audit.

## Step-by-Step Procedure
1. **Enforce Self-Review Invariant**:
   - Verify that the reviewer agent role did not author the patch.
2. **Scope & Acceptance Verification**:
   - Check that changes fulfill task requirements without unrequested refactorings or scope creep.
3. **Correctness & Type Safety**:
   - Inspect edge-case handling, null checks, error handling, and strict typing.
4. **Test Adequacy Review**:
   - Confirm test suite exercises modified branches and boundary conditions.
5. **Issue Line-Level Comments**:
   - Provide constructive, actionable feedback referencing specific file lines.
6. **Issue Review Verdict**:
   - Emit `ReviewVerdict` (APPROVED or REJECTED) with summary.

## Tool Requirements
- `syntra.read_file`, `syntra.workspace_search`, `syntra.list_directory`, `syntra.artifact_write`.

## Expected Output Artifacts
- `ReviewVerdict`: Authoritative review decision artifact.

## Verification Procedure
- If verdict is APPROVED, compute cryptographic patch digest.
- If REJECTED, list explicit blocking defects.

## Failure and Escalation Conditions
- Reject immediately if QA or Security gates failed.
