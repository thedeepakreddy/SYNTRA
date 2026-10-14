"""Scaffolding utility for SYNTRA skills system."""

import os
import yaml

SKILLS_DEFINITIONS = [
    {
        "dir": "requirements-analysis",
        "name": "requirements-analysis",
        "version": "1.0.0",
        "description": "Dissects ambiguous problem statements into structured, verifiable functional and non-functional requirements.",
        "category": "specification",
        "compatible_roles": ["product_manager", "architect"],
        "required_tools": ["syntra.workspace_search", "syntra.read_file"],
        "instructions": """# Skill: Requirements Analysis

## Overview
Transform raw user requests into an unambiguous, structured Product Requirements Document (PRD).

## Methodology
1. **Scope Ingestion**: Parse user goals, context, and existing repository constraints.
2. **Ambiguity Resolution**: Identify implicit assumptions, unstated edge cases, and missing inputs.
3. **Acceptance Criteria**: Formulate verifiable criteria in Given-When-Then format.
4. **Non-Functional Bounds**: Establish latency, security, concurrency, and persistence limits.
"""
    },
    {
        "dir": "system-architecture",
        "name": "system-architecture",
        "version": "1.0.0",
        "description": "Designs modular, maintainable, and scalable component architectures with formal boundaries.",
        "category": "architecture",
        "compatible_roles": ["architect"],
        "required_tools": ["syntra.workspace_search", "syntra.read_file"],
        "instructions": """# Skill: System Architecture

## Overview
Produce rigorous architecture decision records (ADRs) and component diagrams.

## Methodology
1. **Boundary Definition**: Enforce strict separation between Domain, Contracts, and Infrastructure.
2. **Data Flow Modeling**: Define state transitions, transactional boundaries, and outbox patterns.
3. **Decision Records**: Formulate context, decision, consequences, and alternatives considered.
"""
    },
    {
        "dir": "task-decomposition",
        "name": "task-decomposition",
        "version": "1.0.0",
        "description": "Breaks high-level architectures into a cycle-free directed acyclic graph (DAG) of actionable tasks.",
        "category": "planning",
        "compatible_roles": ["engineering_manager", "architect"],
        "required_tools": ["syntra.workspace_search"],
        "instructions": """# Skill: Task Decomposition

## Overview
Decompose system specifications into parallelizable, dependency-ordered engineering tasks.

## Methodology
1. **Atomicity**: Ensure each task delivers a distinct, independently testable change.
2. **DAG Validation**: Enforce cycle-free topological order.
3. **Role Assignment**: Assign specialized agent personas based on task domain.
"""
    },
    {
        "dir": "backend-api-development",
        "name": "backend-api-development",
        "version": "1.0.0",
        "description": "Implements robust, strongly typed FastAPI endpoints, services, and domain logic.",
        "category": "implementation",
        "compatible_roles": ["backend_engineer"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Backend API Development

## Overview
Develop production-grade FastAPI endpoints with Pydantic v2 schemas and pure domain business services.

## Methodology
1. **Schema First**: Define input and output Pydantic v2 models.
2. **Domain Encapsulation**: Keep business rules inside domain entities or services.
3. **Error Boundaries**: Handle known exceptions gracefully with RFC 7807 problem details.
"""
    },
    {
        "dir": "frontend-development",
        "name": "frontend-development",
        "version": "1.0.0",
        "description": "Develops web and client applications inside target repositories.",
        "category": "implementation",
        "compatible_roles": ["frontend_engineer"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Frontend Development

## Overview
Develop client components and state flows inside the target repository. Note: SYNTRA itself is backend-first with zero GUI.

## Methodology
1. **Target Repository Focus**: Execute changes strictly inside the designated workspace.
2. **Type Safety**: Use TypeScript/modern JavaScript with strict checks.
3. **Accessibility**: Implement accessible components with automated UI testing.
"""
    },
    {
        "dir": "database-engineering",
        "name": "database-engineering",
        "version": "1.0.0",
        "description": "Designs relational schemas, indexes, and Alembic migrations for PostgreSQL.",
        "category": "database",
        "compatible_roles": ["backend_engineer", "architect"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Database Engineering

## Overview
Architect reliable relational models with SQLAlchemy 2.x and manage zero-downtime Alembic migrations.

## Methodology
1. **Relational Constraints**: Use explicit foreign keys, check constraints, and unique indexes.
2. **Concurrency**: Implement optimistic locking and transactional outbox.
3. **Reversible Migrations**: Provide deterministic upgrade() and downgrade() scripts.
"""
    },
    {
        "dir": "test-driven-development",
        "name": "test-driven-development",
        "version": "1.0.0",
        "description": "Executes Red-Green-Refactor cycles with pytest, fixtures, and contract assertions.",
        "category": "quality",
        "compatible_roles": ["qa_engineer", "backend_engineer"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Test Driven Development

## Overview
Write failing tests before code, implement minimal passing logic, and refactor under green tests.

## Methodology
1. **Test First**: Formulate edge cases, boundary conditions, and invalid inputs before code.
2. **Isolation**: Use mock doubles strictly for external network dependencies.
3. **Coverage & Assertions**: Verify code paths with high precision assertions.
"""
    },
    {
        "dir": "debugging-and-root-cause-analysis",
        "name": "debugging-and-root-cause-analysis",
        "version": "1.0.0",
        "description": "Isolates defects, inspects execution traces, and crafts minimal regression-proof fixes.",
        "category": "debugging",
        "compatible_roles": ["debugging_specialist"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Debugging and Root Cause Analysis

## Overview
Systematically isolate the root cause of test failures or runtime crashes without guesswork.

## Methodology
1. **Trace Analysis**: Inspect stderr, stdout, and stack traces.
2. **Minimal Reproducer**: Write an automated test reproducing the exact failure.
3. **Targeted Remediation**: Apply the minimal surgical patch to fix the defect.
"""
    },
    {
        "dir": "code-review",
        "name": "code-review",
        "version": "1.0.0",
        "description": "Evaluates code diffs for correctness, architectural compliance, readability, and security.",
        "category": "review",
        "compatible_roles": ["code_reviewer"],
        "required_tools": ["syntra.read_file", "syntra.workspace_search"],
        "instructions": """# Skill: Code Review

## Overview
Provide rigorous peer review on proposed patches before merge approval.

## Methodology
1. **Verification Check**: Ensure tests pass and cover modified code.
2. **Design Conformance**: Verify changes respect module boundaries and coding standards.
3. **Structured Verdict**: Issue APPROVED or REJECTED with specific, actionable critique.
"""
    },
    {
        "dir": "security-review",
        "name": "security-review",
        "version": "1.0.0",
        "description": "Audits code changes for injection flaws, secret leakage, authorization bypasses, and CVEs.",
        "category": "security",
        "compatible_roles": ["security_reviewer"],
        "required_tools": ["syntra.read_file", "syntra.workspace_search"],
        "instructions": """# Skill: Security Review

## Overview
Perform static and dynamic security assessments of code changes and dependency updates.

## Methodology
1. **Threat Vectors**: Inspect for SQL injection, command execution, path traversal, and SSRF.
2. **Secret Detection**: Verify no hardcoded credentials, API keys, or tokens exist in diffs.
3. **Authorization**: Confirm tenant isolation and role permissions are strictly enforced.
"""
    },
    {
        "dir": "git-workflow",
        "name": "git-workflow",
        "version": "1.0.0",
        "description": "Manages isolated Git worktrees, atomic commits, branch lifecycles, and unified patches.",
        "category": "platform",
        "compatible_roles": ["devops_engineer", "engineering_manager"],
        "required_tools": ["syntra.run_command"],
        "instructions": """# Skill: Git Workflow

## Overview
Manage version control operations cleanly inside isolated worker sandboxes.

## Methodology
1. **Worktree Isolation**: Create separate worktrees per task to eliminate race conditions.
2. **Patch Extraction**: Generate clean unified diffs for verification.
3. **Commit Quality**: Enforce Conventional Commits (feat, fix, chore).
"""
    },
    {
        "dir": "devops-and-ci",
        "name": "devops-and-ci",
        "version": "1.0.0",
        "description": "Configures containerization, GitHub Actions workflows, healthchecks, and build scripts.",
        "category": "devops",
        "compatible_roles": ["devops_engineer"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: DevOps and CI

## Overview
Create reproducible deployment artifacts, container definitions, and CI automation.

## Methodology
1. **Multi-Stage Builds**: Keep container images minimal, non-root, and secure.
2. **Health Probes**: Implement liveness and readiness probes for all services.
3. **Fast Pipelines**: Optimize CI caches for dependencies and test suites.
"""
    },
    {
        "dir": "api-contract-testing",
        "name": "api-contract-testing",
        "version": "1.0.0",
        "description": "Validates REST and RPC interfaces against published OpenAPI schemas and proto contracts.",
        "category": "testing",
        "compatible_roles": ["qa_engineer"],
        "required_tools": ["syntra.read_file", "syntra.run_command"],
        "instructions": """# Skill: API Contract Testing

## Overview
Guarantee that API implementations adhere strictly to their published contracts without breaking drift.

## Methodology
1. **Schema Comparison**: Validate runtime JSON responses against Pydantic/OpenAPI specs.
2. **Status Codes**: Confirm error scenarios return appropriate HTTP status codes.
3. **Idempotency**: Test that repeated requests behave according to HTTP semantics.
"""
    },
    {
        "dir": "dependency-management",
        "name": "dependency-management",
        "version": "1.0.0",
        "description": "Maintains pinned dependencies, lockfiles, security updates, and minimal build trees.",
        "category": "platform",
        "compatible_roles": ["devops_engineer", "backend_engineer"],
        "required_tools": ["syntra.read_file", "syntra.write_file", "syntra.run_command"],
        "instructions": """# Skill: Dependency Management

## Overview
Manage Python and platform dependencies deterministically using uv and pinned lockfiles.

## Methodology
1. **Minimal Additions**: Only add dependencies with proven architectural necessity.
2. **Deterministic Locking**: Maintain synchronized uv.lock with SHA-256 hashes.
3. **Vulnerability Audits**: Scan for CVEs and unmaintained libraries.
"""
    },
    {
        "dir": "integration-testing",
        "name": "integration-testing",
        "version": "1.0.0",
        "description": "Validates cross-component interactions across databases, queues, and external services.",
        "category": "testing",
        "compatible_roles": ["qa_engineer"],
        "required_tools": ["syntra.read_file", "syntra.run_command"],
        "instructions": """# Skill: Integration Testing

## Overview
Test end-to-end flows involving real databases, Redis queues, and local MinIO storage.

## Methodology
1. **Real Infrastructure**: Test against running Compose services where appropriate.
2. **State Cleanup**: Ensure tests clean up databases or run inside isolated transactions.
3. **Asynchronous Verification**: Test async message delivery and event stream ordering.
"""
    },
    {
        "dir": "documentation-generation",
        "name": "documentation-generation",
        "version": "1.0.0",
        "description": "Produces clear, structured technical documentation, architecture specs, and user guides.",
        "category": "documentation",
        "compatible_roles": ["product_manager", "architect"],
        "required_tools": ["syntra.read_file", "syntra.write_file"],
        "instructions": """# Skill: Documentation Generation

## Overview
Maintain comprehensive, accurate, and up-to-date documentation across all phases and APIs.

## Methodology
1. **Clarity & Structure**: Use concise GitHub-flavored markdown with diagrams.
2. **Accuracy**: Reflect actual implementation details, verified by automated tests.
3. **Traceability**: Link requirements, architecture decisions, and code files directly.
"""
    }
]


def scaffold_skills(base_dir: str = "skills") -> None:
    for skill in SKILLS_DEFINITIONS:
        target_dir = os.path.join(base_dir, skill["dir"])
        os.makedirs(target_dir, exist_ok=True)

        manifest = {
            "name": skill["name"],
            "version": skill["version"],
            "description": skill["description"],
            "category": skill["category"],
            "compatible_roles": skill["compatible_roles"],
            "required_tools": skill["required_tools"],
        }

        manifest_path = os.path.join(target_dir, "manifest.yaml")
        with open(manifest_path, "w", encoding="utf-8") as f:
            yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

        doc_path = os.path.join(target_dir, "SKILL.md")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(skill["instructions"])

    print(f"Scaffolded {len(SKILLS_DEFINITIONS)} skill packages in {base_dir}/")


if __name__ == "__main__":
    scaffold_skills()
