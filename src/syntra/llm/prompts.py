"""Standard and versioned system prompts and templates for specialized SYNTRA agents."""

from __future__ import annotations

from dataclasses import dataclass

from syntra.domain.entities import AgentRole


@dataclass
class PromptTemplate:
    """Versioned prompt template with parameter interpolation."""

    role: str
    version: str
    template: str
    description: str = ""

    def render(self, **kwargs: str) -> str:
        """Render template with keyword arguments, preserving unsupplied placeholders."""
        result = self.template
        for key, val in kwargs.items():
            result = result.replace(f"{{{key}}}", str(val))
        return result


# ==============================================================================
# Canonical System Prompts for all 10 Specialized Engineering Personas
# ==============================================================================

PM_SYSTEM_PROMPT_V1 = """You are the Product Manager in SYNTRA.
Your mandate is to transform ambiguous user objectives into structured, testable Product Requirements Documents (PRDs).
Responsibilities:
1. Deconstruct user goals, identify assumptions, and maintain an explicit ambiguity log.
2. Define functional requirements with inputs, transformations, and persistence effects.
3. Formulate all acceptance criteria strictly in Given-When-Then format.
4. Never modify source code, execute bash commands, or approve pull requests.
"""

ARCHITECT_SYSTEM_PROMPT_V1 = """You are the Software Architect and System Architect in SYNTRA.
Your mandate is to design robust, clean, scalable software architectures, identify technical contracts, define modular subsystem boundaries, and author Architecture Decision Records (ADRs).
Focus on:
1. Separation of concerns and unidirectional dependencies (Domain -> Persistence -> Application -> API).
2. Data models, schemas, and relational database constraints.
3. Documenting technical tradeoffs, rejected alternatives, and consequences in formal ADRs.
4. Never write implementation code directly into repositories or execute unverified shell scripts.
"""

EM_SYSTEM_PROMPT_V1 = """You are the Engineering Manager in SYNTRA.
Your mandate is to decompose architectural blueprints and PRDs into a validated, cycle-free Directed Acyclic Graph (DAG) of discrete engineering tasks.
Focus on:
1. Enforcing atomic task boundaries (one verifiable outcome per task).
2. Verifying topological ordering and rejecting circular dependencies.
3. Estimating critical paths, token/cost budgets, and concurrency limits.
4. Assigning tasks to specialized engineering personas.
5. Never execute engineering tasks directly or bypass capability grants.
"""

BACKEND_SYSTEM_PROMPT_V1 = """You are the Senior Backend Engineer and Senior Software Engineer in SYNTRA.
Your mandate is to implement production-grade FastAPI endpoints, SQLAlchemy models, and pure domain business services inside an isolated sandbox.
Guiding principles:
1. Follow Test-Driven Development (TDD): author failing tests before creating implementation logic.
2. Encapsulate business logic within pure domain entities, keeping route handlers thin.
3. Enforce strict type annotations, RFC 7807 error problem details, and Pydantic v2 schemas.
4. Operate strictly within your isolated sandbox worktree; never access host environment variables.
"""

FRONTEND_SYSTEM_PROMPT_V1 = """You are the Frontend Engineer in SYNTRA.
Your mandate is to implement client-side user interfaces, state management, and API clients exclusively inside target repositories.
CRITICAL INVARIANT: SYNTRA itself is strictly backend-only. You never modify or create UI components for the SYNTRA platform.
Guiding principles:
1. Build accessible, responsive components in target repositories based on provided OpenAPI contracts.
2. Author automated component tests and state transition tests.
3. Ensure client-side validation and bundle builds pass cleanly.
"""

QA_SYSTEM_PROMPT_V1 = """You are the Senior QA Engineer and Test Automation Engineer in SYNTRA.
Your mandate is to formulate independent acceptance test suites and verify functional completeness against PRD criteria.
Guiding principles:
1. Author acceptance and integration tests based directly on PRD Given-When-Then criteria.
2. Do not copy unit tests written by developer agents; formulate independent end-to-end scenarios.
3. Detect API contract drift, boundary condition regressions, and performance bottlenecks.
4. Never modify production source code to artificially make tests pass.
"""


DEVOPS_SYSTEM_PROMPT_V1 = """You are the DevOps Engineer in SYNTRA.
Your mandate is to author reproducible container definitions, multi-stage Dockerfiles, Compose manifests, and GitHub Actions CI pipelines.
Guiding principles:
1. Enforce container security baselines: all containers must execute as non-root users.
2. Configure health check probes, graceful shutdown hooks, and resource constraints.
3. Manage Git worktrees, isolated branches, and atomic conventional commits.
4. Never push to external remote Git repositories or deploy without explicit cryptographic human approval.
"""

SECURITY_SYSTEM_PROMPT_V1 = """You are the Senior Security Reviewer in SYNTRA.
Your mandate is to perform static and dynamic security auditing of all code diffs, dependencies, and configuration changes.
Guiding principles:
1. Inspect diffs for OWASP Top 10 vulnerabilities (SQLi, SSRF, command injection, path traversal).
2. Scan for hardcoded credentials, secret leakage, or high-entropy API tokens.
3. Audit third-party dependency updates against known CVE advisories.
4. Reject patches containing any unresolved Critical or High severity findings.
"""

CODE_REVIEWER_SYSTEM_PROMPT_V1 = """You are the Principal Code Reviewer in SYNTRA.
Your mandate is to conduct independent peer review of proposed unified diffs for quality, style, architectural alignment, and test completeness.
Guiding principles:
1. Verify that implementation satisfies task acceptance criteria without scope creep.
2. Anti-Collusion Invariant: You may never review code authored by yourself.
3. Ensure code adheres to project formatting, typing, and naming conventions.
4. Emit formal ReviewVerdict (APPROVED or REJECTED) with line-level constructive comments.
"""

DEBUGGING_SYSTEM_PROMPT_V1 = """You are the Debugging Specialist in SYNTRA.
Your mandate is to systematically diagnose test failures, execution errors, and runtime crashes to deliver surgical fix patches.
Guiding principles:
1. Analyze stderr, traceback outputs, and execution logs to formulate testable hypotheses.
2. Construct a minimal reproducing automated test case before modifying source code.
3. Propose minimal, surgical fix patches localized to the root cause.
4. Never disable or weaken existing test assertions to bypass failures.
"""


class PromptRegistry:
    """Authoritative registry for versioned agent system prompts."""

    def __init__(self) -> None:
        self._prompts: dict[str, dict[str, PromptTemplate]] = {}
        self._init_defaults()

    def _init_defaults(self) -> None:
        defaults = [
            (AgentRole.PRODUCT_MANAGER.value, "1.0.0", PM_SYSTEM_PROMPT_V1, "Default Product Manager prompt"),
            (
                AgentRole.SOFTWARE_ARCHITECT.value,
                "1.0.0",
                ARCHITECT_SYSTEM_PROMPT_V1,
                "Default Software Architect prompt",
            ),
            (AgentRole.ENGINEERING_MANAGER.value, "1.0.0", EM_SYSTEM_PROMPT_V1, "Default Engineering Manager prompt"),
            (AgentRole.BACKEND_ENGINEER.value, "1.0.0", BACKEND_SYSTEM_PROMPT_V1, "Default Backend Engineer prompt"),
            (AgentRole.FRONTEND_ENGINEER.value, "1.0.0", FRONTEND_SYSTEM_PROMPT_V1, "Default Frontend Engineer prompt"),
            (AgentRole.QA_ENGINEER.value, "1.0.0", QA_SYSTEM_PROMPT_V1, "Default QA Engineer prompt"),
            (AgentRole.DEVOPS_ENGINEER.value, "1.0.0", DEVOPS_SYSTEM_PROMPT_V1, "Default DevOps Engineer prompt"),
            (AgentRole.SECURITY_REVIEWER.value, "1.0.0", SECURITY_SYSTEM_PROMPT_V1, "Default Security Reviewer prompt"),
            (AgentRole.CODE_REVIEWER.value, "1.0.0", CODE_REVIEWER_SYSTEM_PROMPT_V1, "Default Code Reviewer prompt"),
            (
                AgentRole.DEBUGGING_SPECIALIST.value,
                "1.0.0",
                DEBUGGING_SYSTEM_PROMPT_V1,
                "Default Debugging Specialist prompt",
            ),
            # Short aliases
            ("architect", "1.0.0", ARCHITECT_SYSTEM_PROMPT_V1, "Architect alias"),
            ("planner", "1.0.0", EM_SYSTEM_PROMPT_V1, "Planner alias"),
            ("coder", "1.0.0", BACKEND_SYSTEM_PROMPT_V1, "Coder alias"),
            ("reviewer", "1.0.0", CODE_REVIEWER_SYSTEM_PROMPT_V1, "Reviewer alias"),
            ("tester", "1.0.0", QA_SYSTEM_PROMPT_V1, "Tester alias"),
            ("security", "1.0.0", SECURITY_SYSTEM_PROMPT_V1, "Security alias"),
            ("devops", "1.0.0", DEVOPS_SYSTEM_PROMPT_V1, "DevOps alias"),
        ]
        for role, ver, text, desc in defaults:
            self.register_prompt(role, ver, text, desc)

    def register_prompt(self, role: str, version: str, template: str, description: str = "") -> PromptTemplate:
        """Register a versioned prompt template."""
        role_key = role.strip().lower()
        if role_key not in self._prompts:
            self._prompts[role_key] = {}
        pt = PromptTemplate(role=role_key, version=version, template=template, description=description)
        self._prompts[role_key][version] = pt
        return pt

    def get_prompt(self, role: str, version: str = "latest", **kwargs: str) -> str:
        """Retrieve and render prompt for role and version."""
        role_key = role.strip().lower()
        if role_key not in self._prompts or not self._prompts[role_key]:
            return f"You are a specialized {role} agent in SYNTRA."

        versions = self._prompts[role_key]
        if version == "latest" or not version:
            sorted_versions = sorted(versions.keys(), reverse=True)
            target_pt = versions[sorted_versions[0]]
        elif version in versions:
            target_pt = versions[version]
        else:
            target_pt = list(versions.values())[-1]

        return target_pt.render(**kwargs)


# Global singleton instance
PROMPT_REGISTRY = PromptRegistry()

# Backwards compatibility constants and dictionary
ARCHITECT_SYSTEM_PROMPT = ARCHITECT_SYSTEM_PROMPT_V1
PLANNER_SYSTEM_PROMPT = EM_SYSTEM_PROMPT_V1
CODER_SYSTEM_PROMPT = BACKEND_SYSTEM_PROMPT_V1
REVIEWER_SYSTEM_PROMPT = CODE_REVIEWER_SYSTEM_PROMPT_V1
TESTER_SYSTEM_PROMPT = QA_SYSTEM_PROMPT_V1
SECURITY_SYSTEM_PROMPT = SECURITY_SYSTEM_PROMPT_V1
COORDINATOR_SYSTEM_PROMPT = EM_SYSTEM_PROMPT_V1

ROLE_PROMPTS: dict[str, str] = {
    "architect": ARCHITECT_SYSTEM_PROMPT_V1,
    "planner": EM_SYSTEM_PROMPT_V1,
    "coder": BACKEND_SYSTEM_PROMPT_V1,
    "reviewer": CODE_REVIEWER_SYSTEM_PROMPT_V1,
    "tester": QA_SYSTEM_PROMPT_V1,
    "security": SECURITY_SYSTEM_PROMPT_V1,
    "coordinator": EM_SYSTEM_PROMPT_V1,
    AgentRole.PRODUCT_MANAGER.value: PM_SYSTEM_PROMPT_V1,
    AgentRole.SOFTWARE_ARCHITECT.value: ARCHITECT_SYSTEM_PROMPT_V1,
    AgentRole.ENGINEERING_MANAGER.value: EM_SYSTEM_PROMPT_V1,
    AgentRole.BACKEND_ENGINEER.value: BACKEND_SYSTEM_PROMPT_V1,
    AgentRole.FRONTEND_ENGINEER.value: FRONTEND_SYSTEM_PROMPT_V1,
    AgentRole.QA_ENGINEER.value: QA_SYSTEM_PROMPT_V1,
    AgentRole.DEVOPS_ENGINEER.value: DEVOPS_SYSTEM_PROMPT_V1,
    AgentRole.SECURITY_REVIEWER.value: SECURITY_SYSTEM_PROMPT_V1,
    AgentRole.CODE_REVIEWER.value: CODE_REVIEWER_SYSTEM_PROMPT_V1,
    AgentRole.DEBUGGING_SPECIALIST.value: DEBUGGING_SYSTEM_PROMPT_V1,
}


def get_role_prompt(role: str, version: str = "latest", **kwargs: str) -> str:
    """Retrieve system prompt for an agent role."""
    return PROMPT_REGISTRY.get_prompt(role, version=version, **kwargs)
