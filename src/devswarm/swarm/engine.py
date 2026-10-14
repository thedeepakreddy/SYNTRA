"""DevSwarm high-level multi-agent orchestration engine."""

import logging
import uuid
from pathlib import Path
from typing import Any
from devswarm.agents.roles import (
    ArchitectAgent,
    CoderAgent,
    OrchestratorAgent,
    PlannerAgent,
    ReviewerAgent,
    SecurityAgent,
    TesterAgent,
)
from devswarm.agents.tools import create_standard_workspace_tools
from devswarm.checkpoints.engine import CheckpointEngine, get_checkpoint_engine
from devswarm.core.config import AutonomyMode, get_settings
from devswarm.core.events import Event, EventType, get_event_bus
from devswarm.llm.client import BaseLLMClient, GeminiClient
from devswarm.sandbox.runner import SandboxRunner
from devswarm.sandbox.workspace import WorkspaceManager
from devswarm.swarm.state import SwarmState
from devswarm.swarm.workflows import create_feature_workflow

logger = logging.getLogger(__name__)


class SwarmEngine:
    """Manages the full multi-agent engineering lifecycle."""

    def __init__(
        self,
        workspace_dir: str | Path | None = None,
        llm_client: BaseLLMClient | None = None,
        checkpoint_engine: CheckpointEngine | None = None,
        session_id: str | None = None,
        autonomy_mode: Any = None,
    ) -> None:
        self.session_id = session_id or f"sess-{uuid.uuid4().hex[:8]}"
        settings = get_settings()
        self.autonomy_mode = autonomy_mode or settings.autonomy_mode

        # Setup isolated workspace
        base_dir = Path(workspace_dir or (settings.sandbox_base_dir / self.session_id))
        self.workspace = WorkspaceManager(root_dir=base_dir, session_id=self.session_id)
        self.runner = SandboxRunner(cwd=self.workspace.root_path, session_id=self.session_id)
        self.tools = create_standard_workspace_tools(self.workspace, self.runner)

        # Setup LLM client
        self.llm_client = llm_client or GeminiClient()
        self.checkpoint_engine = checkpoint_engine or get_checkpoint_engine()

        # Initialize specialized agent team
        self.architect = ArchitectAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.planner = PlannerAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.coder = CoderAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.tester = TesterAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.reviewer = ReviewerAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.security = SecurityAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)
        self.orchestrator = OrchestratorAgent(llm_client=self.llm_client, tools=self.tools, session_id=self.session_id)

    async def execute_task(
        self,
        objective: str,
        max_iterations: int = 3,
        autonomy_mode: Any = None,
    ) -> SwarmState:
        """Run the full autonomous multi-agent feature workflow."""
        await get_event_bus().publish(
            Event(
                type=EventType.SESSION_STARTED,
                session_id=self.session_id,
                data={"objective": objective},
            )
        )

        mode = autonomy_mode or self.autonomy_mode
        state = SwarmState(
            session_id=self.session_id,
            objective=objective,
            autonomy_mode=mode,
            max_iterations=max_iterations,
        )

        workflow = create_feature_workflow(
            architect=self.architect,
            planner=self.planner,
            coder=self.coder,
            tester=self.tester,
            reviewer=self.reviewer,
            security=self.security,
            checkpoint_engine=self.checkpoint_engine,
        )

        try:
            final_state = await workflow.execute(state)
            ev_type = EventType.SESSION_COMPLETED if final_state.is_completed and not final_state.error else EventType.SESSION_FAILED
            await get_event_bus().publish(
                Event(
                    type=ev_type,
                    session_id=self.session_id,
                    data={"is_completed": final_state.is_completed, "error": final_state.error},
                )
            )
            return final_state
        except Exception as exc:
            await get_event_bus().publish(
                Event(
                    type=EventType.SESSION_FAILED,
                    session_id=self.session_id,
                    data={"error": str(exc)},
                )
            )
            raise
