# SYNTRA Architecture Specification

## 1. System Overview
**SYNTRA** is an enterprise-grade autonomous multi-agent software engineering platform built on Google Gemini via the modern `google-genai` SDK. The platform adopts a **backend-first, modular monolith architecture** with isolated execution worker subsystems, a deterministic multi-agent state graph, and a robust hybrid autonomy governance model.

```
+-------------------------------------------------------------------------+
|                         SYNTRA Interaction Layer                      |
|      +--------------------------+     +-------------------------------+ |
|      |       SYNTRA CLI       |     |   FastAPI REST & WebSocket   | |
|      +--------------------------+     +-------------------------------+ |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                           Core Orchestration                            |
|  +--------------------+  +----------------------+  +------------------+ |
|  |    StateGraph      |  |  Checkpoint Engine   |  |  Async EventBus  | |
|  |  (Cyclic / DAG)    |  |  (Hybrid Autonomy)   |  |   & Telemetry    | |
|  +--------------------+  +----------------------+  +------------------+ |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                          Multi-Agent Subsystem                          |
|  +------------+ +-----------+ +---------+ +----------+ +--------+ +----+ |
|  | Architect  | |  Planner  | |  Coder  | | Reviewer | | Tester | |Sec | |
|  +------------+ +-----------+ +---------+ +----------+ +--------+ +----+ |
|                          ReAct Reasoning Loops                          |
+-------------------------------------------------------------------------+
                  |                                     |
                  v                                     v
+-----------------------------------+ +-----------------------------------+
|      Gemini LLM Provider Layer    | |    Isolated Execution Sandbox     |
| - Google GenAI SDK (google-genai) | | - Path Traversal Guard            |
| - Gemini 2.5 Pro / Flash / Lite   | | - Subprocess Worker with Timeout  |
| - Structured Outputs & Tool Calls | | - Command Safety Whitelist/Black  |
| - Token & Cost Accounting Engine  | | - Exact Diff & Patcher Engine     |
+-----------------------------------+ +-----------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|                           Persistence Engine                            |
|             Async SQLAlchemy 2.0 (PostgreSQL / SQLite WAL)              |
|        Sessions | Executions | Checkpoints | Events | Artifacts         |
+-------------------------------------------------------------------------+
```

## 2. Core Modules & Domain Boundaries

### `syntra.core`
- **`config.py`**: Centralized configuration management using `pydantic-settings`. Supports environment variables, `.env` file parsing, and runtime overrides.
- **`events.py`**: High-performance in-memory pub-sub event bus supporting typed asynchronous events (`EventType`), subscriber hooks, and dedicated streaming queues.
- **`telemetry.py`**: Per-model token counting, cost tracking (USD per million tokens for Gemini models), request latency logging, and aggregate analytics.
- **`exceptions.py`**: Clear, domain-specific exception hierarchy (`SYNTRAError`, `LLMError`, `SandboxSecurityViolationError`, `CheckpointError`).

### `syntra.llm`
- **`client.py`**: Production integration with Google GenAI SDK (`from google import genai`). Translates generic `LLMMessage` objects to `types.Content`, handles tool definitions, streaming, and structured schema generation.
- **`mock.py`**: In-memory, deterministic mock client for offline tests, CI/CD pipelines, and simulating complex tool execution sequences without external API credits.
- **`router.py`**: Dynamic model routing selecting between Gemini tiers (`gemini-2.5-pro` for architecture and review, `gemini-2.5-flash` for coding and testing, `gemini-2.0-flash-lite` for fast triage).
- **`prompts.py`**: Engineered system prompts tailored to each engineering persona.

### `syntra.sandbox`
- **`workspace.py`**: Isolated filesystem sandbox. Guarantees that agent file operations (`read_file`, `write_file`, `delete_file`, `list_files`, `search_code`) cannot escape the project root directory via `Path.resolve().relative_to()`.
- **`safety.py`**: Regular expression security validator intercepting dangerous command patterns (`rm -rf /`, raw disk writes, fork bombs, privilege escalations) and scrubbing sensitive environment tokens.
- **`patcher.py`**: Surgical diff generator and text replacer ensuring accurate edits.
- **`runner.py`**: Asynchronous subprocess worker enforcing execution timeouts, maximum output buffers (truncation protection), and event streaming.

### `syntra.agents`
- **`base.py`**: `BaseAgent` implementing the ReAct loop: reasoning, tool invocation, working memory accumulation, and step execution.
- **`context.py`**: Agent conversational context with auto-compaction to preserve token headroom.
- **`memory.py`**: Ephemeral working memory and durable tagged notes shared across agents.
- **`tools.py`**: Dynamic tool registry generating JSON schema parameter definitions and supporting standard Model Context Protocol (MCP) exports.
- **`roles/`**: Concrete implementations of `ArchitectAgent`, `PlannerAgent`, `CoderAgent`, `TesterAgent`, `ReviewerAgent`, `SecurityAgent`, and `OrchestratorAgent`.

### `syntra.checkpoints`
- **`models.py`**: Checkpoint data models with risk grading (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and status lifecycle (`PENDING`, `APPROVED`, `REJECTED`, `MODIFIED`).
- **`policies.py`**: Autonomy mode matrix determining whether an action requires human intervention.
- **`engine.py`**: Pause-and-resume coordinator using `asyncio.Event` synchronization.

### `syntra.swarm`
- **`graph.py`**: LangGraph-inspired deterministic StateGraph with nodes, directed edges, and conditional routers.
- **`state.py`**: `SwarmState` representing the shared blackboard of the engineering workflow.
- **`workflows.py`**: Production feature development workflow with automated self-healing retry cycles.
- **`engine.py`**: High-level multi-agent lifecycle coordinator.

### `syntra.storage`
- **`database.py`**: Async SQLAlchemy 2.0 engine supporting PostgreSQL (`asyncpg`) in production and SQLite (`aiosqlite`) in local development.
- **`models.py`**: Relational models for sessions, executions, checkpoints, events, and artifacts.
- **`repositories.py`**: Repository design pattern isolating data persistence logic.

### `syntra.api`
- FastAPI REST API providing management endpoints for sessions, checkpoints, workspace files, and a WebSocket `/ws/events` stream for live telemetry.

### `syntra.cli`
- Typer-based command-line interface with Rich terminal formatting for running swarms, listing sessions, and resolving checkpoints interactively.
