# ADR-004: Model Context Protocol (MCP) as Standard Tool Integration Standard

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, MCP Protocol Engineer

---

## 1. Context & Problem Statement
AI agents require tools to search repositories, inspect file trees, read source files, apply diffs, and execute commands. Proprietary, ad-hoc tool calling formats create tight coupling and make integrating external enterprise systems (GitHub, Jira, databases) brittle. We need an open, standardized, secure protocol for tool discovery, capability declaration, and invocation.

---

## 2. Decision Drivers
- **Standardization**: Industry standard protocol for LLM tool invocation.
- **Interoperability**: Ability to integrate local command-line tools and remote enterprise servers seamlessly.
- **Security & Authorization**: Strict server-side capability policy enforcement before tool execution.
- **Official Specification**: Conformance to official `mcp` Python SDK and specification version `2024-11-05`.

---

## 3. Considered Options
1. **Option A: Proprietary OpenAI/Gemini Function Calling Schema Only**: Simple, but tightly binds tool logic to specific LLM provider schemas and prevents external server sharing.
2. **Option B: LangChain Tool System**: High dependency footprint and frequent breaking API changes.
3. **Option C: Official Model Context Protocol (MCP)**: Open standard backed by Anthropic/industry, supporting stdio and HTTP/SSE transports with formal JSON-RPC 2.0 schemas.

---

## 4. Decision Outcome
**Chosen Option**: **Option C: Model Context Protocol (MCP) Specification `2024-11-05` using official `mcp` SDK (`mcp>=1.1.2`, current `2.3.0`)**.

### Key Rules:
- SYNTRA hosts an internal MCP server (`syntra`) exposing standard filesystem, task, and artifact tools.
- External MCP servers must be explicitly allowlisted in the `mcp_servers` table.
- All tool calls pass through the **Capability Policy Engine**; LLMs cannot authorize their own access.
- Local tools use `stdio` transport under an isolated non-root user; remote tools use authenticated `sse` transport.

### Tradeoffs:
- **Pros**: Interoperability across diverse tools, strongly typed JSON-RPC contracts, standardized protocol.
- **Cons**: Requires managing JSON-RPC subprocess lifecycles and connection pooling.
