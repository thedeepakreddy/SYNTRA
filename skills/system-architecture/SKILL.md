# Skill: System Architecture

## Overview
Defines robust component boundaries, interface contracts, persistence schemas, and architectural decision records for engineering execution.

## Required Input Evidence
1. **Validated PRDDocument**: Accepted product requirements and Given-When-Then acceptance criteria.
2. **Current Codebase State**: Existing module boundaries, database schemas, and contracts.

## Step-by-Step Procedure
1. **Subsystem Boundary Definition**:
   - Group functional capabilities into cohesive, isolated packages.
   - Enforce unidirectional dependencies: Domain -> Persistence -> Application -> API.
2. **Contract & Interface Formulation**:
   - Define Pydantic v2 domain schemas and data transfer objects.
   - Specify HTTP endpoint signatures, status codes, and error models.
3. **Persistence Design**:
   - Design normalized relational models, primary/foreign keys, and indexes.
   - Plan Alembic migration steps without destructive table alterations.
4. **Author Architecture Decision Records (ADRs)**:
   - Document technical choices, rejected alternatives, and consequences.
5. **Publish Architecture Specification**:
   - Submit formal `ArchitectureSpecification` artifact.

## Tool Requirements
- `syntra.workspace_search`, `syntra.read_file`, `syntra.list_directory`, `syntra.artifact_write`.

## Expected Output Artifacts
- `ArchitectureSpecification`: High-level system design with Mermaid diagrams.
- `ArchitectureDecisionRecord` (ADR): Formal decisions on technology and boundaries.

## Verification Procedure
- Verify dependency graph contains zero circular dependencies.
- Verify zero implementation code was written.

## Failure and Escalation Conditions
- Escalate if requirements require distributed transactions or unsafe breaking schema changes without migration path.
