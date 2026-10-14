# DevSwarm

**Production-Oriented Autonomous Multi-Agent Software Engineering Platform**

DevSwarm coordinates teams of specialized AI agents powered by Google Gemini (`google-genai` SDK) to autonomously architect, plan, write, review, test, and release production-quality code under a robust **hybrid autonomy** model.

## Features
- **Multi-Agent Collaboration**: Specialized roles (Architect, Tech Lead, Senior Coder, Code Reviewer, QA/Tester, Security Auditor).
- **Primary LLM Provider**: Google Gemini via modern `google-genai` SDK.
- **Hybrid Autonomy**: Multi-tier autonomy levels with human checkpoint gates (Approve, Reject, Modify, Replay).
- **Isolated Execution Workers**: Safe process sandboxing with path traversal defenses, resource limits, and execution timeouts.
- **Event-Driven Architecture**: High-throughput async event bus for real-time observability and WebSocket streaming.
- **Production API & CLI**: FastAPI REST & WebSocket server and rich terminal CLI.
