# SYNTRA Formal Contracts Index (`contract-index.md`)

**SYNTRA: Synchronized Intelligence for Autonomous Engineering**  
*Contract Standard: Pydantic v2 Strongly Typed Inter-Module Schemas*

---

## 1. Overview & Contract Supremacy Invariant

In SYNTRA, **Rule of Contract Supremacy** mandates that all inter-process, inter-subsystem, and inter-agent boundaries are governed by explicit, strongly typed Pydantic v2 models. Untrusted LLM outputs or raw tool payloads must validate against these contracts before touching authoritative persistence or triggering downstream events.

---

## 2. Core Subsystem Contract Registry

### 2.1 Agent Plane Contracts
- **`AgentInvocationRequest`**:
  ```python
  class AgentInvocationRequest(BaseModel):
      invocation_id: UUID = Field(default_factory=uuid4)
      mission_id: UUID
      task_id: UUID | None = None
      role: AgentRole
      objective: str
      context_artifacts: list[UUID] = Field(default_factory=list)
      loaded_skills: list[str] = Field(default_factory=list)
      budget_reservation_tokens: int = Field(default=32768)
      sandbox_id: UUID | None = None
      timeout_seconds: int = Field(default=300)
  ```
- **`AgentInvocationResult`**:
  ```python
  class AgentInvocationResult(BaseModel):
      invocation_id: UUID
      role: AgentRole
      status: Literal["SUCCESS", "FAILURE", "BLOCKED_BY_POLICY"]
      output_summary: str
      produced_artifacts: list[UUID] = Field(default_factory=list)
      unified_diff: str | None = None
      tokens_consumed: int
      cost_usd: Decimal
      execution_duration_ms: int
      error_message: str | None = None
  ```

### 2.2 Task Scheduler & Worker Contracts
- **`TaskClaimRequest`**:
  ```python
  class TaskClaimRequest(BaseModel):
      worker_id: str
      supported_roles: list[AgentRole]
      concurrency_capacity: int = 1
  ```
- **`WorkerLease`**:
  ```python
  class WorkerLeaseContract(BaseModel):
      task_id: UUID
      worker_id: str
      fencing_token: int
      lease_acquired_at: datetime
      lease_expires_at: datetime
  ```
- **`TaskHeartbeat`**:
  ```python
  class TaskHeartbeatContract(BaseModel):
      task_id: UUID
      worker_id: str
      fencing_token: int
      progress_message: str | None = None
  ```

### 2.3 MCP Gateway Contracts
- **`MCPToolCallRequest`**:
  ```python
  class MCPToolCallRequest(BaseModel):
      server_name: str
      tool_name: str
      arguments: dict[str, Any]
      call_id: str = Field(default_factory=lambda: str(uuid4()))
  ```
- **`MCPToolCallResponse`**:
  ```python
  class MCPToolCallResponse(BaseModel):
      call_id: str
      status: Literal["SUCCESS", "ERROR"]
      content: list[dict[str, Any]]
      is_error: bool = False
      error_code: int | None = None
      error_message: str | None = None
  ```

### 2.4 Sandbox Execution Contracts
- **`SandboxExecutionJob`**:
  ```python
  class SandboxExecutionJob(BaseModel):
      job_id: UUID = Field(default_factory=uuid4)
      task_id: UUID
      workspace_path: Path
      command: str
      env_vars: dict[str, str] = Field(default_factory=dict)
      timeout_seconds: int = 120
      max_output_bytes: int = 1048576
  ```
- **`SandboxExecutionResult`**:
  ```python
  class SandboxExecutionResult(BaseModel):
      job_id: UUID
      exit_code: int
      stdout: str
      stderr: str
      duration_ms: int
      timed_out: bool
      output_truncated: bool
  ```

### 2.5 Verification & Review Contracts
- **`VerificationRequest`**:
  ```python
  class VerificationRequest(BaseModel):
      task_id: UUID
      patch_artifact_id: UUID
      regression_test_suite_id: str
  ```
- **`VerificationReport`**:
  ```python
  class VerificationReport(BaseModel):
      verification_id: UUID = Field(default_factory=uuid4)
      task_id: UUID
      verdict: Literal["PASS", "FAIL", "ERROR"]
      tests_passed: int
      tests_failed: int
      coverage_percentage: float | None = None
      diagnostic_log: str
  ```

### 2.6 Governance & Approval Contracts
- **`ApprovalRequestContract`**:
  ```python
  class ApprovalRequestContract(BaseModel):
      approval_id: UUID = Field(default_factory=uuid4)
      mission_id: UUID
      action_type: str
      action_digest: str
      proposed_payload: dict[str, Any]
      expires_at: datetime
  ```
- **`ApprovalResolutionContract`**:
  ```python
  class ApprovalResolutionContract(BaseModel):
      approval_id: UUID
      decision: Literal["APPROVE", "REJECT", "MODIFY"]
      feedback: str | None = None
      modified_payload: dict[str, Any] | None = None
      resolved_by_user_id: UUID
  ```
