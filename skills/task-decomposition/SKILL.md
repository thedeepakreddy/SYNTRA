# Skill: Task Decomposition

## Overview
Transforms architectural specifications and PRDs into atomic, cycle-free Directed Acyclic Graphs (DAGs) of discrete engineering tasks.

## Required Input Evidence
1. **ArchitectureSpecification**: Subsystem boundaries and contract definitions.
2. **PRDDocument**: Acceptance criteria and functional requirements.

## Step-by-Step Procedure
1. **Identify Atomic Work Units**:
   - Split work so each task produces exactly one verifiable outcome (e.g. model migration, domain service, API route, test suite).
2. **Map Dependency Relationships**:
   - Establish strict prerequisite ordering (e.g. migration before API implementation).
3. **Assign Engineering Personas**:
   - Backend Engineer for APIs/services, Frontend Engineer for target UI, DevOps for CI/CD, QA for test suites.
4. **Validate Graph Structure**:
   - Run `syntra.validate_dag` to programmatically reject cyclic dependencies and calculate topological order.
5. **Estimate Budget Reservations**:
   - Allocate token budgets and timeout limits per task.
6. **Submit TaskPlan Artifact**:
   - Register authoritative task records in the persistence plane.

## Tool Requirements
- `syntra.workspace_search`, `syntra.read_file`, `syntra.validate_dag`, `syntra.artifact_write`.

## Expected Output Artifacts
- `TaskPlan`: Ordered DAG containing validated task records.

## Verification Procedure
- Topological sort terminates with 0 cycles.
- Critical path and max concurrency are computed.

## Failure and Escalation Conditions
- Escalate if circular dependencies cannot be reconciled without re-architecting components.
