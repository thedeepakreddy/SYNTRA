# Skill: Frontend Development (Target Repositories Only)

## Overview
Builds responsive, accessible, and test-covered user interfaces and API client bindings exclusively inside user target project repositories.

## CRITICAL ARCHITECTURAL POLICY
SYNTRA is strictly a backend-only platform. The Frontend Engineer agent never modifies or creates UI components for SYNTRA. All work is targeted at external projects.

## Required Input Evidence
1. **Task Specification**: Target client requirements.
2. **API OpenAPI Specification**: Backend endpoint contracts and schemas.
3. **Target Repository Workspace**: Isolated sandbox pointing to the target repo worktree.

## Step-by-Step Procedure
1. **Inspect Target Workspace**:
   - Identify frontend framework (e.g. Next.js, React, Vue, Svelte) and package manager (npm/pnpm/yarn).
2. **Build API Client Interfaces**:
   - Generate or write typed fetchers based on the provided OpenAPI schema.
3. **Develop Components**:
   - Implement UI components adhering to design system guidelines and accessibility standards.
4. **Implement Client Tests**:
   - Author component unit tests verifying state transitions, form validation, and error states.
5. **Run Target Build & Test Suite**:
   - Execute linter, typecheck, and test runner inside sandbox.
6. **Generate Target Repo Unified Diff**:
   - Output clean patch for the target repository.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`, `syntra.git_diff`.

## Expected Output Artifacts
- `UnifiedDiff`: Patch targeting external client repository.
- `ComponentTestSuite`: Execution log of frontend test runner.

## Verification Procedure
- Verify target repository builds without TypeScript or bundling errors.
- Confirm zero files in SYNTRA platform were touched.

## Failure and Escalation Conditions
- Escalate immediately if instructed to build a UI for the SYNTRA core platform.
