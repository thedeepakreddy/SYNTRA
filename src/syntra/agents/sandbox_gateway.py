"""Bind a ToolGateway to exactly one leased task, role and sandbox bridge."""

import json
import posixpath
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import UTC, datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select

from syntra.agents.operational import AgentInvocation
from syntra.domain.entities import ActionClassification, AgentRole
from syntra.llm.models import ToolDefinition
from syntra.mcp.client_manager import MCPClientManager
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.policy import CapabilityPolicyEngine
from syntra.mcp.registry import MCPRegistry
from syntra.mcp.types import MCPInvocationRequest, MCPInvocationResult, MCPServerDefinition
from syntra.persistence.models import CapabilityGrantModel
from syntra.sandbox.tool_bridge import SandboxToolBridge
from syntra.skills.profiles import get_agent_profile


async def load_capabilities(uow: Any, invocation: AgentInvocation) -> list[CapabilityGrantModel]:
    return list(
        (
            await uow.session.execute(
                select(CapabilityGrantModel)
                .where(
                    CapabilityGrantModel.org_id == invocation.org_id,
                    CapabilityGrantModel.agent_role == invocation.role.value,
                )
                .order_by(CapabilityGrantModel.created_at, CapabilityGrantModel.id)
            )
        )
        .scalars()
        .all()
    )


async def effective_capabilities(uow: Any, invocation: AgentInvocation) -> list[str]:
    grants = await load_capabilities(uow, invocation)
    capabilities = []
    for cap in get_agent_profile(invocation.role).allowed_tool_capabilities:
        matched = [
            g
            for g in grants
            if fnmatchcase(cap, g.tool_name_pattern if "." in g.tool_name_pattern else "syntra." + g.tool_name_pattern)
        ]
        if not matched:
            continue
        grant = matched[-1]
        expires = grant.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if grant.is_allowed and not grant.requires_approval and (not expires or expires > datetime.now(UTC)):
            capabilities.append(cap)
    return capabilities


def build_sandbox_gateway(
    invocation: AgentInvocation, bridge: SandboxToolBridge, uow_factory: Any, guard: Callable[[], Awaitable[None]]
) -> tuple[ToolGateway, list[ToolDefinition]]:
    registry = MCPRegistry()
    manager = MCPClientManager(registry)
    manager.register_server(MCPServerDefinition(name="syntra", command_or_url="python"))
    server = MCPServer("syntra-sandbox", version="1.0.0")
    evidence: list[dict[str, object]] = []

    @server.tool(name="read_file", description="Read a relative file inside the assigned container worktree")
    async def read_file(relative_path: str) -> str:
        return await bridge.isolated_file_operation("read", relative_path)

    @server.tool(name="write_file", description="Write a relative file inside the assigned container worktree")
    async def write_file(relative_path: str, content: str) -> str:
        if invocation.role == AgentRole.QA_ENGINEER:
            normalized = posixpath.normpath(relative_path)
            root = Path(bridge.sandbox.lease.worktree_path).resolve()
            if not normalized.startswith("tests/") or not (root / normalized).resolve().is_relative_to(root / "tests"):
                raise ValueError("QA may author tests only")
        return await bridge.isolated_file_operation("write", relative_path, content)

    @server.tool(name="list_directory", description="List bounded directory entries in the container worktree")
    async def list_directory(relative_path: str = ".") -> str:
        return await bridge.isolated_file_operation("list", relative_path)

    @server.tool(name="workspace_search", description="Search bounded directory entries within the task worktree")
    async def workspace_search(relative_path: str = ".") -> str:
        return await bridge.isolated_file_operation("list", relative_path)

    @server.tool(
        name="run_command", description="Run a bounded command INSIDE the isolated container, never on the host"
    )
    async def run_command(command: str) -> str:
        result = await bridge.execute_command(command, timeout_seconds=min(30, bridge.sandbox.config.timeout_seconds))
        record = asdict(result)
        evidence.append(record)
        return json.dumps(record)

    @server.tool(name="git_diff", description="Retrieve the actual unified diff, including newly created files")
    async def git_diff() -> str:
        return await bridge.get_unified_diff()

    manager.register_in_process_server("syntra", server)
    declarations = {
        "read_file": {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "required": ["relative_path"],
            "additionalProperties": False,
        },
        "write_file": {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "maxLength": 1000},
                "content": {"type": "string", "maxLength": 100000},
            },
            "required": ["relative_path", "content"],
            "additionalProperties": False,
        },
        "list_directory": {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "additionalProperties": False,
        },
        "workspace_search": {
            "type": "object",
            "properties": {"relative_path": {"type": "string"}},
            "additionalProperties": False,
        },
        "run_command": {
            "type": "object",
            "properties": {"command": {"type": "string", "maxLength": 20000}},
            "required": ["command"],
            "additionalProperties": False,
        },
        "git_diff": {"type": "object", "properties": {}, "additionalProperties": False},
    }
    for name, schema in declarations.items():
        registry.snapshot_tool_schema(
            "syntra",
            name,
            schema,
            action_classification=ActionClassification.SANDBOX_WRITE
            if name in {"write_file", "run_command"}
            else ActionClassification.READ_ONLY,
        )

    class BoundGateway(ToolGateway):
        command_evidence = evidence

        async def execute_tool_call(self, request: MCPInvocationRequest, uow: Any = None) -> MCPInvocationResult:
            if (
                request.org_id != invocation.org_id
                or request.mission_id != invocation.mission_id
                or request.task_id != invocation.task_id
                or request.caller_role != invocation.role.value
                or request.server_name != "syntra"
                or datetime.now(UTC) >= invocation.deadline
                or "syntra." + request.tool_name not in invocation.approved_capabilities
                or not get_agent_profile(invocation.role).is_capability_allowed("syntra." + request.tool_name)
            ):
                return MCPInvocationResult(
                    invocation_id=request.invocation_id,
                    status="BLOCKED_BY_POLICY",
                    is_error=True,
                    error_message="Invocation does not match bound task, role, deadline or capabilities",
                )
            await guard()
            async with uow_factory() as scoped_uow:
                budget = await scoped_uow.budgets.get_for_mission(invocation.mission_id)
                if (
                    budget is None
                    or budget.consumed_tokens >= budget.max_tokens
                    or budget.consumed_cost_usd >= budget.max_cost_usd
                ):
                    return MCPInvocationResult(
                        invocation_id=request.invocation_id,
                        status="BLOCKED_BY_POLICY",
                        is_error=True,
                        error_message="Authoritative mission budget is exhausted",
                    )
                policy = CapabilityPolicyEngine()
                for grant in await load_capabilities(scoped_uow, invocation):
                    pattern = grant.tool_name_pattern.removeprefix("syntra.")
                    expires = grant.expires_at
                    if expires and expires.tzinfo is None:
                        expires = expires.replace(tzinfo=UTC)
                    policy.register_grant(
                        invocation.org_id,
                        invocation.role.value,
                        pattern,
                        grant.is_allowed,
                        grant.requires_approval,
                        expires,
                    )
                # Fresh gateway per call avoids sharing mutable policy across concurrent invocations.
                inner = ToolGateway(registry, manager, policy)
                request = request.model_copy(update={"workspace_path": str(bridge.sandbox.lease.worktree_path)})
                result = await inner.execute_tool_call(request, scoped_uow)
                await scoped_uow.commit()
                return result

    gateway = BoundGateway(registry, manager, CapabilityPolicyEngine())
    tools = [
        ToolDefinition(name="syntra." + name, description=f"Sandbox {name}", parameters=schema)
        for name, schema in declarations.items()
        if "syntra." + name in invocation.approved_capabilities
    ]
    return gateway, tools
