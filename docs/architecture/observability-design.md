# SYNTRA Observability, Audit & Telemetry Architecture

**SYNTRA: Synchronized Intelligence for Autonomous Engineering**  
*Standards: OpenTelemetry, Structured JSON Logging, Transactional Outbox Events*

---

## 1. Observability Triad in SYNTRA

```mermaid
flowchart LR
    subgraph ObservabilityTriad["SYNTRA Observability Triad"]
        Logs["Structured JSON Logs\n(Correlation IDs: mission_id, task_id)"]
        Traces["OpenTelemetry Traces\n(Distributed Spans across LLM, Tools, Sandboxes)"]
        Audit["Immutable Audit Events\n(PostgreSQL events & Outbox)"]
    end

    Execution["Agent & System Operations"] --> Logs
    Execution --> Traces
    Execution --> Audit
```

---

## 2. Distributed Tracing with OpenTelemetry

Every mission execution produces a distributed OpenTelemetry trace:
- **Root Span**: `mission.execute` (`trace_id` assigned at mission creation).
- **Child Spans**:
  - `orchestrator.node` (LangGraph state transition)
  - `agent.react_loop` (Agent prompt formulation & response parsing)
  - `model.gemini_generate` (API latency, prompt/completion token count, model name)
  - `mcp.tool_invocation` (Tool name, parameter verification, execution duration)
  - `sandbox.command_run` (Exit code, execution wall-clock time)
  - `verification.run` (Test execution, assertion counts)

### Context Propagation:
Spans propagate across async tasks and background worker queues using OpenTelemetry W3C `traceparent` headers.

---

## 3. Structured Logging Specification

Logs are emitted in structured JSON format with guaranteed correlation metadata:

```json
{
  "timestamp": "2026-10-15T01:15:00.123456Z",
  "level": "INFO",
  "logger": "syntra.agents.runtime",
  "message": "Agent completed task attempt successfully",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "mission_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "task_id": "1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed",
  "agent_role": "backend_engineer",
  "tokens_consumed": 2841,
  "cost_usd": 0.00071,
  "duration_ms": 3412
}
```

---

## 4. Token & Cost Accounting Ledger

1. **Real-time Atomic Metering**:
   - Every Gemini model invocation records prompt tokens, completion tokens, and dollar cost based on model pricing into `usage_records`.
2. **Budget Protection**:
   - `budgets.reserved_tokens` is atomically incremented prior to model dispatch.
   - If `consumed_tokens + reserved_tokens > max_tokens`, the invocation is rejected before sending requests to Google Gemini.

---

## 5. Automated Sensitive Data Redaction

All log formatters and trace exporters pass text through a redaction pipeline:
- API Keys (`AIzaSy...`, `sk-...`, `Bearer ...`) $\to$ `[REDACTED_API_KEY]`
- Private Keys (`-----BEGIN RSA PRIVATE KEY-----`) $\to$ `[REDACTED_PRIVATE_KEY]`
- High-Entropy Strings ($\text{Entropy} > 4.5$ with length $> 20$) $\to$ `[REDACTED_SECRET]`
