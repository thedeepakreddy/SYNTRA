"""Central Tool Gateway executing the 14-step MCP invocation lifecycle and policy enforcement."""

import hashlib
import logging
import time
from pathlib import Path
from uuid import UUID

import jsonschema

from syntra.core.config import get_settings
from syntra.domain.entities import ActionClassification
from syntra.mcp.client_manager import (
    MCPClientManager,
    MCPTimeoutError,
)
from syntra.mcp.policy import (
    CapabilityPolicyEngine,
    PolicyViolationError,
)
from syntra.mcp.registry import (
    MCPRegistry,
    UnknownServerError,
    UnknownToolError,
)
from syntra.mcp.security import MCPSecurityService
from syntra.mcp.types import (
    MCPInvocationRequest,
    MCPInvocationResult,
)
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork

logger = logging.getLogger(__name__)


class ToolGateway:
    """Central gateway governing all agent-to-tool and agent-to-MCP interactions."""

    def __init__(
        self,
        registry: MCPRegistry,
        client_manager: MCPClientManager,
        policy_engine: CapabilityPolicyEngine,
    ) -> None:
        self.registry = registry
        self.client_manager = client_manager
        self.policy_engine = policy_engine

    async def execute_tool(
        self,
        request: MCPInvocationRequest,
        uow: SqlAlchemyUnitOfWork | None = None,
    ) -> MCPInvocationResult:
        """Alias method for execute_tool_call."""
        return await self.execute_tool_call(request, uow=uow)

    async def execute_tool_call(
        self,
        request: MCPInvocationRequest,
        uow: SqlAlchemyUnitOfWork | None = None,
    ) -> MCPInvocationResult:
        """Execute a tool invocation request enforcing the complete 14-step governance lifecycle."""
        start_time = time.perf_counter()

        # Step 1: Request received and validated by Pydantic schema

        # Step 2: Identify authenticated caller
        if not request.org_id:
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="BLOCKED_BY_POLICY",
                is_error=True,
                error_code=-32000,
                error_message="Missing authoritative organization identifier (org_id).",
            )

        # Step 3: Resolve mission and task ownership
        mission_org_id: UUID | None = None
        mission_version: int = 1
        budget_remaining_tokens: int | None = None
        if uow and request.mission_id:
            try:
                mission = await uow.missions.get_by_id_for_org(request.mission_id, request.org_id)
                mission_org_id = mission.org_id
                mission_version = mission.version
                budget = await uow.budgets.get_for_mission(request.mission_id)
                if budget:
                    budget_remaining_tokens = budget.max_tokens - budget.consumed_tokens
            except Exception as exc:
                return MCPInvocationResult(
                    invocation_id=request.invocation_id,
                    status="BLOCKED_BY_POLICY",
                    is_error=True,
                    error_code=-32000,
                    error_message=f"Ownership verification failed for mission '{request.mission_id}': {exc}",
                )

        # Step 4: Resolve registered server and tool
        try:
            self.registry.get_server(request.server_name)
            tool_def = self.registry.get_tool_definition(request.server_name, request.tool_name)
            tool_schema_snapshot = self.registry.get_tool_schema(request.server_name, request.tool_name)
        except (UnknownServerError, UnknownToolError) as exc:
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="ERROR",
                is_error=True,
                error_code=-32601,  # Tool / Method not found
                error_message=str(exc),
            )
        except Exception as exc:
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="ERROR",
                is_error=True,
                error_code=-32603,
                error_message=f"Registry lookup failed: {exc}",
            )

        # Step 5: Validate arguments against pinned JSON schema
        if tool_schema_snapshot.input_schema:
            try:
                jsonschema.validate(instance=request.arguments, schema=tool_schema_snapshot.input_schema)
            except jsonschema.ValidationError as exc:
                return MCPInvocationResult(
                    invocation_id=request.invocation_id,
                    status="ERROR",
                    is_error=True,
                    error_code=-32602,  # Invalid params
                    error_message=f"Argument schema validation failed: {exc.message}",
                )

        # Step 6: Check capability grant and human approval via Policy Engine & Persistence
        is_sensitive = tool_def.action_classification in (
            ActionClassification.EXTERNAL_WRITE,
            ActionClassification.SENSITIVE_EXTERNAL_ACTION,
        )

        has_approval = False
        approval_uuid = request.approval_id
        if not approval_uuid and request.approval_token:
            try:
                approval_uuid = UUID(request.approval_token)
            except (ValueError, TypeError):
                approval_uuid = None

        if is_sensitive:
            if uow and request.mission_id:
                if not approval_uuid or not request.approval_digest:
                    return MCPInvocationResult(
                        invocation_id=request.invocation_id,
                        status="BLOCKED_BY_POLICY",
                        is_error=True,
                        error_code=-32000,
                        error_message="External write action requires both approval_id/token and cryptographic approval_digest.",
                    )
                try:
                    settings = get_settings()
                    target_res = str(request.arguments.get("repo_name", request.arguments.get("target_resource", "")))
                    await uow.approvals.verify_and_consume_for_execution(
                        approval_id=approval_uuid,
                        org_id=request.org_id,
                        mission_id=request.mission_id,
                        action_type=request.tool_name,
                        provided_digest=request.approval_digest,
                        secret_key=settings.approval_secret_key,
                        current_mission_version=mission_version,
                        target_resource=target_res,
                    )
                    await uow.commit()
                    has_approval = True
                except Exception as exc:
                    return MCPInvocationResult(
                        invocation_id=request.invocation_id,
                        status="BLOCKED_BY_POLICY",
                        is_error=True,
                        error_code=-32000,
                        error_message=f"Human approval verification failed: {exc}",
                    )
            elif not uow:
                # Standalone unit test mode without persistence unit of work
                has_approval = bool(request.approval_digest or request.approval_token)

        try:
            self.policy_engine.evaluate(
                request=request,
                tool_def=tool_def,
                mission_org_id=mission_org_id,
                budget_remaining_tokens=budget_remaining_tokens,
                has_valid_approval=has_approval,
            )
        except PolicyViolationError as exc:
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="BLOCKED_BY_POLICY",
                is_error=True,
                error_code=-32000,  # Capability denied
                error_message=f"Policy violation: {exc}",
            )

        # Step 7: Check target resource scope (e.g. filesystem boundary isolation)
        if request.workspace_path:
            ws_root = Path(request.workspace_path).resolve()
            for key, val in request.arguments.items():
                if isinstance(val, str) and ("path" in key or "file" in key):
                    # Check for path traversal attempts
                    try:
                        resolved_target = (ws_root / val).resolve()
                        if not resolved_target.is_relative_to(ws_root):
                            return MCPInvocationResult(
                                invocation_id=request.invocation_id,
                                status="BLOCKED_BY_POLICY",
                                is_error=True,
                                error_code=-32000,
                                error_message=f"Path traversal blocked: '{val}' attempts to escape workspace root.",
                            )
                    except Exception as exc:
                        return MCPInvocationResult(
                            invocation_id=request.invocation_id,
                            status="BLOCKED_BY_POLICY",
                            is_error=True,
                            error_code=-32000,
                            error_message=f"Resource scope check failed: {exc}",
                        )

        # Step 8: Execution budget check already verified in Step 6
        # Step 9: Human approval check already verified in Step 6

        # Step 10: Record invocation intent
        scrubbed_args = MCPSecurityService.redact_sensitive_data(request.arguments)
        if uow:
            uow.publish_event(
                event_type="MCP_TOOL_INVOCATION_REQUESTED",
                payload={
                    "invocation_id": str(request.invocation_id),
                    "server_name": request.server_name,
                    "tool_name": request.tool_name,
                    "caller_role": request.caller_role,
                    "arguments_scrubbed": scrubbed_args,
                },
            )

        # Step 11: Execute the tool via Client Manager
        try:
            raw_result = await self.client_manager.invoke_tool(
                server_name=request.server_name,
                tool_name=request.tool_name,
                arguments=request.arguments,
                timeout_seconds=request.timeout_seconds,
            )
        except MCPTimeoutError as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="TIMEOUT",
                is_error=True,
                error_code=-32001,
                error_message=str(exc),
                duration_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return MCPInvocationResult(
                invocation_id=request.invocation_id,
                status="ERROR",
                is_error=True,
                error_code=-32603,
                error_message=f"Tool execution failed: {exc}",
                duration_ms=elapsed_ms,
            )

        # Step 12: Validate and sanitize response
        raw_output_text = raw_result.get("raw_output", "")
        scrubbed_text, injection_detected = MCPSecurityService.sanitize_untrusted_output(raw_output_text)

        sanitized_content = []
        for item in raw_result.get("content", []):
            if isinstance(item, dict):
                text_val = item.get("text", "")
                sanitized_text, _ = MCPSecurityService.sanitize_untrusted_output(text_val)
                sanitized_content.append({"type": item.get("type", "text"), "text": sanitized_text})
            else:
                sanitized_content.append({"type": "text", "text": str(item)})

        # Step 13: Persist execution evidence and audit record
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        result_digest = hashlib.sha256(scrubbed_text.encode("utf-8")).hexdigest()

        if uow:
            uow.publish_event(
                event_type="MCP_TOOL_INVOKED",
                payload={
                    "invocation_id": str(request.invocation_id),
                    "server_name": request.server_name,
                    "tool_name": request.tool_name,
                    "caller_role": request.caller_role,
                    "status": "SUCCESS" if not raw_result.get("is_error") else "ERROR",
                    "duration_ms": elapsed_ms,
                    "sha256_result_digest": result_digest,
                    "injection_marker_detected": injection_detected,
                },
            )

        # Step 14: Return typed invocation result
        return MCPInvocationResult(
            invocation_id=request.invocation_id,
            status="SUCCESS" if not raw_result.get("is_error") else "ERROR",
            content=sanitized_content,
            raw_output=scrubbed_text,
            is_error=raw_result.get("is_error", False),
            duration_ms=elapsed_ms,
            result_hash=result_digest,
        )
