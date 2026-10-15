"""Security tests verifying that external-write authorization strictly requires an actual persisted, valid, unexpired, unrevoked, single-use approval."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from syntra.core.config import get_settings
from syntra.domain.entities import ActionClassification, ApprovalDecision, MCPTransportType, TrustClassification
from syntra.mcp.client_manager import MCPClientManager
from syntra.mcp.gateway import ToolGateway
from syntra.mcp.policy import CapabilityPolicyEngine
from syntra.mcp.registry import MCPRegistry
from syntra.mcp.types import MCPInvocationRequest, MCPServerDefinition
from syntra.persistence.unit_of_work import SqlAlchemyUnitOfWork
from syntra.storage.database import DatabaseManager


@pytest.fixture
async def approval_test_env():
    """Setup temporary database and ToolGateway configured with a real test stdio MCP server."""
    db = DatabaseManager("sqlite+aiosqlite:///:memory:")
    await db.init_tables()
    session_factory = db.get_session_factory()

    registry = MCPRegistry()
    client_manager = MCPClientManager(registry)
    policy_engine = CapabilityPolicyEngine()
    gateway = ToolGateway(registry, client_manager, policy_engine)

    server_def = MCPServerDefinition(
        name="real_test_mcp",
        transport=MCPTransportType.STDIO,
        trust_classification=TrustClassification.LOCAL_TRUSTED,
        command_or_url="uv",
        args=["run", "python", "scripts/test_mcp_server.py"],
        is_enabled=True,
    )
    client_manager.register_server(server_def)
    await client_manager.discover_tools("real_test_mcp")

    # Mark external_publish as EXTERNAL_WRITE
    tool_def = registry.get_tool_definition("real_test_mcp", "external_publish")
    tool_def.action_classification = ActionClassification.EXTERNAL_WRITE

    yield {
        "db": db,
        "session_factory": session_factory,
        "gateway": gateway,
        "policy_engine": policy_engine,
        "registry": registry,
    }
    await db.close()


@pytest.mark.asyncio
async def test_supplied_digest_alone_without_persisted_approval_rejected(approval_test_env):
    """Verify that a supplied digest alone without a valid persisted approval is rejected."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]

    org_id = uuid4()
    mission_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="external_publish")

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Project A", "project-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Objective A")
        await uow.commit()

    # Pass fabricated digest with NO approval_id
    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_digest="fake-hmac-sha256-digest-without-approval",
        approval_id=None,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "requires both approval_id/token and cryptographic approval_digest" in (result.error_message or "")


@pytest.mark.asyncio
async def test_wrong_mission_approval_rejected(approval_test_env):
    """Verify that an approval issued for Mission A cannot be used for Mission B."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_a = uuid4()
    mission_b = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_a, org_id, proj.id, "Mission A")
        await uow.missions.create(mission_b, org_id, proj.id, "Mission B")

        # Create and approve for Mission A
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_a,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_id,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest
        await uow.commit()

    # Attempt to use approval for Mission B!
    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_b,  # Wrong mission!
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "is bound to mission" in (result.error_message or "")


@pytest.mark.asyncio
async def test_wrong_org_approval_rejected(approval_test_env):
    """Verify cross-tenant approval usage is rejected."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_a = uuid4()
    org_b = uuid4()
    mission_b = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_a, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_a, "Org A", "org-a")
        await uow.organizations.create(org_b, "Org B", "org-b")
        proj_b = await uow.projects.create(uuid4(), org_b, "Proj B", "proj-b")
        await uow.missions.create(mission_b, org_b, proj_b.id, "Mission B")

        # Create and approve for Org B
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_b,
            mission_id=mission_b,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_b,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest
        await uow.commit()

    # Org A attempts to use Org B's approval
    req = MCPInvocationRequest(
        org_id=org_a,  # Org A caller
        mission_id=mission_b,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True


@pytest.mark.asyncio
async def test_expired_approval_rejected(approval_test_env):
    """Verify that an expired approval cannot be consumed."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    # Expired 5 minutes ago
    past_expiration = datetime.now(UTC) - timedelta(minutes=5)
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=past_expiration,
            secret_key=settings.approval_secret_key,
        )
        # Mark as approved but with expired timestamp
        appr.decision = ApprovalDecision.APPROVED
        appr.resolved_by = user_id
        digest = appr.action_digest
        await uow.commit()

    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "expired at" in (result.error_message or "")


@pytest.mark.asyncio
async def test_replayed_approval_rejected(approval_test_env):
    """Verify that an approval cannot be consumed twice (one-time-use policy)."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_id,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest
        await uow.commit()

    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    # First invocation: Slashes through and consumes the approval
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        res1 = await gateway.execute_tool_call(req, uow=uow)
        await uow.commit()

    assert res1.status == "SUCCESS"
    assert "Published to prod-repo" in (res1.raw_output or "")

    # Second invocation (Replay Attack): Must be BLOCKED
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        res2 = await gateway.execute_tool_call(req, uow=uow)

    assert res2.status == "BLOCKED_BY_POLICY"
    assert res2.is_error is True
    assert "already been consumed" in (res2.error_message or "")


@pytest.mark.asyncio
async def test_tampered_version_approval_rejected(approval_test_env):
    """Verify that an approval issued for version N is rejected if the mission has advanced to N+1."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        # Approval issued for version 1
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_id,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest

        # Advance mission to version 2 (simulating material change)
        await uow.missions.update_objective(mission_id, org_id, 1, "Altered Mission Objective")
        await uow.commit()

    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "Mission state modified" in (result.error_message or "")


@pytest.mark.asyncio
async def test_unapproved_pending_request_rejected(approval_test_env):
    """Verify that an approval still in PENDING state cannot authorize execution."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        # Created but NEVER resolved (remains PENDING)
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        digest = appr.action_digest
        await uow.commit()

    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "still PENDING" in (result.error_message or "")


@pytest.mark.asyncio
async def test_modified_action_argument_target_rejected(approval_test_env):
    """Verify that an approval issued for target resource A is rejected if called on resource B."""
    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        # Approval explicitly bound to target_resource="production-repo-authorized"
        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="production-repo-authorized",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_id,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest
        await uow.commit()

    # Tampered argument: targeting a different repo!
    req = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "tampered-unauthorized-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        result = await gateway.execute_tool_call(req, uow=uow)

    assert result.status == "BLOCKED_BY_POLICY"
    assert result.is_error is True
    assert "does not match requested resource" in (result.error_message or "")


@pytest.mark.asyncio
async def test_concurrent_approval_consumption_single_use(approval_test_env):
    """Verify that under concurrent execution, an approval is consumed only once."""
    import asyncio

    gateway: ToolGateway = approval_test_env["gateway"]
    policy_engine: CapabilityPolicyEngine = approval_test_env["policy_engine"]
    session_factory = approval_test_env["session_factory"]
    settings = get_settings()

    org_id = uuid4()
    mission_id = uuid4()
    user_id = uuid4()
    policy_engine.register_grant(org_id=org_id, agent_role="devops_engineer", tool_name_pattern="*")

    approval_id = uuid4()
    async with SqlAlchemyUnitOfWork(session_factory) as uow:
        await uow.organizations.create(org_id, "Org A", "org-a")
        proj = await uow.projects.create(uuid4(), org_id, "Proj A", "proj-a")
        await uow.missions.create(mission_id, org_id, proj.id, "Mission A")

        appr = await uow.approvals.create_request(
            approval_id=approval_id,
            org_id=org_id,
            mission_id=mission_id,
            action_type="external_publish",
            target_resource="prod-repo",
            mission_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            secret_key=settings.approval_secret_key,
        )
        await uow.approvals.resolve_decision(
            approval_id=approval_id,
            org_id=org_id,
            user_id=user_id,
            decision=ApprovalDecision.APPROVED,
            feedback="Approved",
            secret_key=settings.approval_secret_key,
            current_mission_version=1,
            provided_digest=appr.action_digest,
        )
        digest = appr.action_digest
        await uow.commit()

    req1 = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )
    req2 = MCPInvocationRequest(
        org_id=org_id,
        mission_id=mission_id,
        caller_role="devops_engineer",
        server_name="real_test_mcp",
        tool_name="external_publish",
        arguments={"repo_name": "prod-repo"},
        approval_id=approval_id,
        approval_digest=digest,
    )

    async def _call(req):
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            res = await gateway.execute_tool_call(req, uow=uow)
            await uow.commit()
            return res

    results = await asyncio.gather(_call(req1), _call(req2))
    statuses = [r.status for r in results]
    # Exactly one must succeed, and the other must be blocked by replay policy
    assert "SUCCESS" in statuses
    assert "BLOCKED_BY_POLICY" in statuses
