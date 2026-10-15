# Skill: Backend API Development

## Overview
Develops production-grade, type-safe FastAPI endpoints, pure domain entities, service aggregators, and repository queries inside an isolated sandbox environment.

## Required Input Evidence
1. **Task Specification**: Target requirements and acceptance criteria.
2. **Architecture Contract**: Defined schemas, Pydantic models, and database relationships.
3. **Sandbox Workspace Lease**: Isolated Git worktree path.

## Step-by-Step Procedure
1. **Review Contracts & Entities**:
   - Inspect existing domain entities in `src/syntra/domain/` and models in `src/syntra/persistence/`.
2. **Apply Test-Driven Development (TDD)**:
   - Write failing unit tests verifying the endpoint contract before implementing route handlers.
3. **Implement Domain Logic**:
   - Encapsulate business rules in pure domain functions or classes with zero framework imports.
4. **Implement FastAPI Route**:
   - Mount router, define status codes, request/response models, and error handlers (RFC 7807).
5. **Run Local Verification**:
   - Execute `uv run pytest` inside the sandbox; confirm all new and existing tests pass.
   - Run `uv run ruff check` and `uv run mypy src`.
6. **Generate Unified Diff**:
   - Output clean git diff patch against worktree baseline.

## Tool Requirements
- `syntra.read_file`, `syntra.write_file`, `syntra.run_command`, `syntra.git_diff`.

## Expected Output Artifacts
- `UnifiedDiff`: Unified diff patch containing implementation and unit tests.
- `UnitTestSuite`: Local pytest execution logs.

## Verification Procedure
- Diffs must not touch files outside assigned task scope.
- Code passes ruff, mypy, and pytest cleanly.

## Failure and Escalation Conditions
- Escalate if implementation requires architectural changes outside task boundaries.
