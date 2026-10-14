"""Scaffolding utility for SYNTRA packages and apps."""

import os

PACKAGES = [
    ("domain", "Pure domain entities, invariants, and business state machines (zero external framework dependencies)."),
    ("contracts", "Pydantic v2 schemas, event envelopes, and inter-service RPC contracts."),
    ("persistence", "SQLAlchemy 2.x models, Alembic migrations, and repository implementations."),
    ("agents", "Specialized AI engineering agent definitions, prompt templates, and ReAct loops."),
    ("model_runtime", "Google Gen AI SDK adapters, router, cost/token ledger, and test doubles."),
    ("mcp_gateway", "MCP client manager, capability grants, and tool proxy gateway."),
    ("tool_registry", "Tool catalog, schema registry, and runtime execution bindings."),
    ("skill_registry", "Skill loader, manifest validator, and progressive disclosure manager."),
    ("sandbox", "SandboxProvider abstraction, Git worktree manager, and isolated execution plane."),
    ("memory", "Execution, project, and organizational memory storage engines."),
    ("evaluation", "Independent verification service, benchmark runner, and quality gates."),
    ("security", "Secrets scrubber, cryptographic approval digests, and permission enforcement."),
    ("telemetry", "OpenTelemetry tracing, metrics collection, and structured audit logger."),
]

APPS = [
    (
        "api",
        "SYNTRA REST & WebSocket API control plane application.",
        "from syntra.api.app import app\n\nif __name__ == '__main__':\n    import uvicorn\n    uvicorn.run(app, host='0.0.0.0', port=8000)\n",
    ),
    (
        "orchestrator",
        "LangGraph mission coordination daemon.",
        "def main():\n    print('SYNTRA Orchestrator Daemon initialized.')\n\nif __name__ == '__main__':\n    main()\n",
    ),
    (
        "scheduler",
        "Deterministic DAG task scheduler and lease manager daemon.",
        "def main():\n    print('SYNTRA Task Scheduler Daemon initialized.')\n\nif __name__ == '__main__':\n    main()\n",
    ),
    (
        "worker_controller",
        "Sandbox runner and worker supervision daemon.",
        "def main():\n    print('SYNTRA Worker Controller Daemon initialized.')\n\nif __name__ == '__main__':\n    main()\n",
    ),
    (
        "mcp_server",
        "SYNTRA Model Context Protocol (MCP) server daemon.",
        "def main():\n    print('SYNTRA MCP Server Daemon initialized.')\n\nif __name__ == '__main__':\n    main()\n",
    ),
]


def scaffold_monorepo():
    # Packages
    for pkg_name, doc in PACKAGES:
        target_dir = os.path.join("packages", pkg_name)
        os.makedirs(target_dir, exist_ok=True)

        init_file = os.path.join(target_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(f'"""SYNTRA {pkg_name} package.\n\n{doc}\n"""\n')

        typed_file = os.path.join(target_dir, "py.typed")
        if not os.path.exists(typed_file):
            with open(typed_file, "w", encoding="utf-8") as f:
                f.write("")

    # Apps
    for app_name, doc, entry_code in APPS:
        target_dir = os.path.join("apps", app_name)
        os.makedirs(target_dir, exist_ok=True)

        init_file = os.path.join(target_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write(f'"""SYNTRA {app_name} application.\n\n{doc}\n"""\n')

        main_file = os.path.join(target_dir, "main.py")
        if not os.path.exists(main_file):
            with open(main_file, "w", encoding="utf-8") as f:
                f.write(entry_code)

    print("Monorepo packages and apps scaffolded successfully.")


if __name__ == "__main__":
    scaffold_monorepo()
