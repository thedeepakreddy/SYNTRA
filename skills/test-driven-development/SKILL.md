# Skill: Test-Driven Development (TDD)

## Overview
Enforces the Red-Green-Refactor development cycle: write minimal failing automated tests asserting expected behavior before creating implementation logic.

## Required Input Evidence
1. **Task Specification**: Target behaviors and requirements.
2. **Acceptance Criteria**: Given-When-Then criteria from PRD.

## Step-by-Step Procedure
1. **Red Phase (Write Failing Test)**:
   - Create test case in `tests/` capturing the desired functional contract.
   - Run `uv run pytest <test_path>` inside the sandbox. Confirm the test fails for the expected reason (e.g. `AttributeError` or assertion failure), not a syntax error.
2. **Green Phase (Minimal Implementation)**:
   - Write the simplest code necessary to satisfy the test assertion.
   - Re-run test; confirm test passes.
3. **Refactor Phase (Clean & Harden)**:
   - Clean up code structure, enforce strong typing, remove duplication.
   - Re-run full test suite to guarantee zero regressions.
4. **Edge Case Coverage**:
   - Add negative tests for invalid inputs, boundary values, and exceptions.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`.

## Expected Output Artifacts
- `UnitTestSuite`: Automated test files with 100% pass status.

## Verification Procedure
- Verify tests pass with `uv run pytest`.
- Verify coverage covers new logic branches.

## Failure and Escalation Conditions
- Escalate if existing tests are failing before work begins (broken baseline).
