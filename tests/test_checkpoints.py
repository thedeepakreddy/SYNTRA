"""Tests for DevSwarm hybrid autonomy checkpoints."""

import asyncio
import pytest
from devswarm.checkpoints import (
    CheckpointActionType,
    CheckpointEngine,
    CheckpointPolicy,
    CheckpointStatus,
    RiskLevel,
)
from devswarm.core.config import AutonomyMode
from devswarm.core.exceptions import CheckpointError


def test_checkpoint_policy_risk_evaluation():
    # Git push is CRITICAL
    assert CheckpointPolicy.evaluate_risk(CheckpointActionType.GIT_PUSH) == RiskLevel.CRITICAL

    # High-risk command
    assert CheckpointPolicy.evaluate_risk(
        CheckpointActionType.COMMAND_EXECUTION,
        command="git reset --hard HEAD~1",
    ) == RiskLevel.HIGH

    # Safe command
    assert CheckpointPolicy.evaluate_risk(
        CheckpointActionType.COMMAND_EXECUTION,
        command="pytest tests/",
    ) == RiskLevel.MEDIUM

    # Config file edit
    assert CheckpointPolicy.evaluate_risk(
        CheckpointActionType.FILE_WRITE,
        path="src/config.py",
    ) == RiskLevel.HIGH


def test_checkpoint_policy_mode_gating():
    # Semi-autonomous: allows MEDIUM, gates HIGH and CRITICAL
    assert not CheckpointPolicy.should_require_checkpoint(
        AutonomyMode.SEMI_AUTONOMOUS,
        CheckpointActionType.COMMAND_EXECUTION,
        RiskLevel.MEDIUM,
    )
    assert CheckpointPolicy.should_require_checkpoint(
        AutonomyMode.SEMI_AUTONOMOUS,
        CheckpointActionType.COMMAND_EXECUTION,
        RiskLevel.HIGH,
    )

    # Supervised: gates handoffs and plans
    assert CheckpointPolicy.should_require_checkpoint(
        AutonomyMode.SUPERVISED,
        CheckpointActionType.ROLE_HANDOFF,
        RiskLevel.LOW,
    )

    # Autonomous: only gates CRITICAL
    assert not CheckpointPolicy.should_require_checkpoint(
        AutonomyMode.AUTONOMOUS,
        CheckpointActionType.COMMAND_EXECUTION,
        RiskLevel.HIGH,
    )
    assert CheckpointPolicy.should_require_checkpoint(
        AutonomyMode.AUTONOMOUS,
        CheckpointActionType.GIT_PUSH,
        RiskLevel.CRITICAL,
    )


@pytest.mark.asyncio
async def test_checkpoint_engine_lifecycle():
    engine = CheckpointEngine()

    cp = await engine.create_checkpoint(
        session_id="s1",
        agent_id="coder-1",
        agent_role="coder",
        action_type=CheckpointActionType.COMMAND_EXECUTION,
        description="Run migration",
        proposed_command="alembic upgrade head",
    )
    assert cp.status == CheckpointStatus.PENDING

    # Test rejection without feedback errors
    with pytest.raises(CheckpointError):
        await engine.resolve(cp.checkpoint_id, "reject", feedback="")

    # Approve checkpoint asynchronously
    async def async_resolve():
        await asyncio.sleep(0.05)
        await engine.resolve(cp.checkpoint_id, "approve", feedback="Looks safe to execute")

    asyncio.create_task(async_resolve())

    resolved_cp = await engine.wait_for_resolution(cp.checkpoint_id, timeout=1.0)
    assert resolved_cp.status == CheckpointStatus.APPROVED
    assert resolved_cp.human_feedback == "Looks safe to execute"
