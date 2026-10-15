# Skill: Integration Testing

## Overview
Authors and executes independent end-to-end integration test suites directly derived from PRD Given-When-Then criteria to verify complete user workflows.

## Required Input Evidence
1. **PRD Acceptance Criteria**: Authoritative Given-When-Then specifications.
2. **Unified Diff Patch**: Proposed implementation under verification.
3. **Sandbox Environment**: Clean test database and execution workspace.

## Step-by-Step Procedure
1. **Formulate Acceptance Test Scenarios**:
   - Author integration tests independently; never reuse unit test assertions written by the developer.
2. **Execute Full Flow Against Test Harness**:
   - Exercise multiple layers: API -> Service -> Persistence -> Event Outbox.
3. **Assert Invariants**:
   - Check response codes, payload schemas, database state changes, and outbox event emissions.
4. **Execute Regression Suite**:
   - Run complete suite to ensure existing features were not broken.
5. **Emit VerificationRun Record**:
   - Persist test outcomes, pass/fail counts, and coverage metrics.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `VerificationRun`: Formal integration test verification report.

## Verification Procedure
- 100% of integration test scenarios pass with zero failures.

## Failure and Escalation Conditions
- If any acceptance criteria fail, emit a `TestFailureReport` and route to Debugging Specialist.
