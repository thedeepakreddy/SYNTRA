"""Hybrid autonomy policy evaluation and risk assessment."""

import re
from syntra.core.config import AutonomyMode
from syntra.checkpoints.models import CheckpointActionType, RiskLevel

# Commands that are always high risk even in semi-autonomous mode
HIGH_RISK_COMMAND_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\brm\s+",
    r"\bdrop\s+database\b",
    r"\bdrop\s+table\b",
    r"\balembic\s+downgrade\b",
    r"\bpip\s+uninstall\b",
    r"\bcurl\s+.*\|\s*bash\b",
]


class CheckpointPolicy:
    """Evaluates whether an action requires human checkpoint intervention."""

    @classmethod
    def evaluate_risk(
        cls,
        action_type: CheckpointActionType,
        command: str | None = None,
        path: str | None = None,
    ) -> RiskLevel:
        """Determine risk level of proposed action."""
        if action_type == CheckpointActionType.GIT_PUSH:
            return RiskLevel.CRITICAL

        if action_type == CheckpointActionType.COMMAND_EXECUTION and command:
            cmd_lower = command.lower()
            for pattern in HIGH_RISK_COMMAND_PATTERNS:
                if re.search(pattern, cmd_lower):
                    return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        if action_type in (CheckpointActionType.FILE_WRITE, CheckpointActionType.FILE_PATCH):
            if path and any(k in path.lower() for k in ("settings", "config", ".env", "schema", "migration")):
                return RiskLevel.HIGH
            return RiskLevel.MEDIUM

        if action_type == CheckpointActionType.ROLE_HANDOFF:
            return RiskLevel.LOW

        if action_type == CheckpointActionType.PLAN_APPROVAL:
            return RiskLevel.HIGH

        return RiskLevel.LOW

    @classmethod
    def should_require_checkpoint(
        cls,
        mode: AutonomyMode,
        action_type: CheckpointActionType,
        risk_level: RiskLevel,
    ) -> bool:
        """Decide if a checkpoint gate must be triggered."""
        if mode == AutonomyMode.AUTONOMOUS:
            # Fully autonomous: only CRITICAL actions (e.g. git push to remote) pause
            return risk_level == RiskLevel.CRITICAL

        if mode == AutonomyMode.STRICT_APPROVAL:
            # Strict: everything except read requires approval
            return True

        if mode == AutonomyMode.SUPERVISED:
            # Supervised: pauses on role handoffs, plans, and high/critical mutations
            if action_type in (CheckpointActionType.ROLE_HANDOFF, CheckpointActionType.PLAN_APPROVAL):
                return True
            return risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        if mode == AutonomyMode.SEMI_AUTONOMOUS:
            # Semi-autonomous: allows standard code edits and safe commands,
            # pauses on high risk commands, destructive writes, and plans
            if action_type == CheckpointActionType.PLAN_APPROVAL:
                return True
            return risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        return False
