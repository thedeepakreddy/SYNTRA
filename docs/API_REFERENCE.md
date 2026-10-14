# SYNTRA REST & WebSocket API Reference

The SYNTRA backend exposes a production FastAPI server on port 8000. Interactive Swagger documentation is accessible at `http://localhost:8000/docs` and Redoc at `http://localhost:8000/redoc`.

---

## 1. Health & Telemetry

### `GET /api/health`
Returns system operational status, model configuration, and basic metrics.
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "gemini_configured": true,
  "autonomy_mode": "semi_autonomous",
  "telemetry": {
    "total_invocations": 12,
    "successful_invocations": 12,
    "failed_invocations": 0,
    "total_prompt_tokens": 4210,
    "total_completion_tokens": 1250,
    "total_tokens": 5460,
    "total_estimated_cost_usd": 0.000691,
    "average_latency_seconds": 0.42
  }
}
```

### `GET /api/telemetry`
Returns detailed token breakdown and cost analytics.

---

## 2. Engineering Sessions

### `POST /api/sessions`
Create a new engineering session.
**Request Body**:
```json
{
  "objective": "Build user authentication microservice with JWT and FastAPI",
  "autonomy_mode": "semi_autonomous",
  "workspace_dir": null
}
```
**Response** (`201 Created`):
```json
{
  "session_id": "sess-a1b2c3d4",
  "objective": "Build user authentication microservice with JWT and FastAPI",
  "status": "created",
  "autonomy_mode": "semi_autonomous",
  "created_at": "2026-10-15T00:30:00Z"
}
```

### `GET /api/sessions`
List historical sessions with pagination.
**Query Parameters**:
- `limit` (int, default: 50, max: 100)

### `GET /api/sessions/{session_id}`
Retrieve session details by ID.

### `POST /api/sessions/{session_id}/run`
Trigger autonomous swarm execution.
**Request Body**:
```json
{
  "objective": "Optional objective override",
  "max_iterations": 3,
  "autonomy_mode": "semi_autonomous"
}
```

---

## 3. Checkpoint Governance

### `GET /api/checkpoints`
Query pending or historical checkpoints.
**Query Parameters**:
- `session_id` (string, optional)
- `status` (`pending`, `approved`, `rejected`, `modified`, optional)

### `GET /api/checkpoints/{checkpoint_id}`
Fetch single checkpoint details.

### `POST /api/checkpoints/{checkpoint_id}/resolve`
Approve, reject, or modify a checkpoint.
**Request Body**:
```json
{
  "decision": "approve",
  "feedback": "Approved with recommendation to run linters"
}
```

---

## 4. Workspace Inspection

### `GET /api/sessions/{session_id}/files`
List files or directory tree in the session's isolated workspace.
**Query Parameters**:
- `tree` (boolean, default: false)

### `GET /api/sessions/{session_id}/files/{file_path}`
Read raw file content from workspace.

---

## 5. Real-Time WebSocket Streaming

### `WebSocket /ws/events`
Stream all platform events in real-time.

**Event Schema**:
```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "type": "agent.thought",
  "session_id": "sess-a1b2c3d4",
  "agent_id": "coder-1",
  "agent_role": "coder",
  "timestamp": "2026-10-15T00:32:00Z",
  "data": {
    "thought": "I will inspect the workspace files..."
  }
}
```
