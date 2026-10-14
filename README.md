# SYNTRA

**Synchronized Intelligence for Autonomous Engineering**

> *One Vision. Multiple AI Agents. Autonomous Engineering.*

SYNTRA coordinates teams of specialized AI agents powered by Google Gemini (`google-genai` SDK) to autonomously architect, plan, write, review, test, and release production-quality code under a robust **hybrid autonomy** model with isolated execution sandboxes.

## Core Features
- **Synchronized Multi-Agent Collaboration**: Specialized roles (Product Manager, Software Architect, Engineering Manager, Backend Engineer, Frontend Engineer, QA Engineer, DevOps Engineer, Security Reviewer, Code Reviewer, Debugging Specialist).
- **Primary Model Provider**: Google Gemini via the supported modern `google-genai` Python SDK.
- **Hybrid Autonomy**: Multi-tier autonomy levels with cryptographically bound human-in-the-loop checkpoint gates (Approve, Reject with corrective guidance, Modify).
- **Isolated Execution Sandboxes**: Safe process sandboxing (`SandboxProvider`) with path traversal defenses, resource limits, and execution timeouts.
- **First-Class MCP Integration**: Native Model Context Protocol (MCP) server (`syntra`) and client gateway.
- **Deterministic State Graphs**: Cyclic, stateful workflow orchestration powered by LangGraph with PostgreSQL checkpointing.
- **Production API & CLI**: Headless-first architecture operable via FastAPI REST/WebSocket endpoints and the `syntra` CLI.
