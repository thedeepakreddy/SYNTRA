"""Pre-configured multi-agent software engineering workflows."""

import logging
from devswarm.agents.roles import (
    ArchitectAgent,
    CoderAgent,
    PlannerAgent,
    ReviewerAgent,
    SecurityAgent,
    TesterAgent,
)
from devswarm.checkpoints.engine import CheckpointEngine
from devswarm.checkpoints.models import CheckpointActionType
from devswarm.swarm.graph import StateGraph
from devswarm.swarm.state import SwarmState, SwarmTask

logger = logging.getLogger(__name__)


def create_feature_workflow(
    architect: ArchitectAgent,
    planner: PlannerAgent,
    coder: CoderAgent,
    tester: TesterAgent,
    reviewer: ReviewerAgent,
    security: SecurityAgent,
    checkpoint_engine: CheckpointEngine | None = None,
) -> StateGraph:
    """Build production multi-agent feature development workflow with self-healing feedback loop."""
    graph = StateGraph(name="feature_development")

    async def architect_node(state: SwarmState) -> SwarmState:
        state.update_stage("architecting", "architect")
        prompt = (
            f"Design a clean architecture and component contracts for the following objective:\n"
            f"{state.objective}\n"
            f"Specify target directory structure, interfaces, schemas, and dependencies."
        )
        res = await architect.run_task(prompt)
        state.architecture_design = res.output
        architect.context.memory.record_note("architecture_spec", res.output, "architect")
        return state

    async def plan_checkpoint_node(state: SwarmState) -> SwarmState:
        state.update_stage("checkpoint_plan", "plan_checkpoint")
        if checkpoint_engine:
            required, risk = checkpoint_engine.should_checkpoint(
                action_type=CheckpointActionType.PLAN_APPROVAL,
                custom_mode=state.autonomy_mode,
            )
            if required:
                cp = await checkpoint_engine.create_checkpoint(
                    session_id=state.session_id,
                    agent_id=architect.agent_id,
                    agent_role="architect",
                    action_type=CheckpointActionType.PLAN_APPROVAL,
                    description=f"Approve architectural design for: {state.objective[:80]}",
                    metadata={"design_preview": (state.architecture_design or "")[:500]},
                )
                resolved = await checkpoint_engine.wait_for_resolution(cp.checkpoint_id)
                if resolved.status.value == "rejected":
                    state.error = f"Architecture rejected by human: {resolved.human_feedback}"
                    state.is_completed = False
        return state

    async def planner_node(state: SwarmState) -> SwarmState:
        state.update_stage("planning", "planner")
        prompt = (
            f"Break down this architecture into discrete, actionable implementation tasks:\n"
            f"{state.architecture_design}\n"
            f"List tasks with title, description, and dependencies."
        )
        res = await planner.run_task(prompt)
        # Parse basic tasks
        state.tasks = [
            SwarmTask(
                id=f"task-1",
                title="Implement Core Architecture",
                description=res.output[:300],
                assigned_role="coder",
            )
        ]
        return state

    async def coder_node(state: SwarmState) -> SwarmState:
        state.update_stage("coding", "coder")
        feedback_context = ""
        if state.review_comments:
            feedback_context = f"\nPrevious review feedback to address:\n" + "\n".join(state.review_comments)

        prompt = (
            f"Implement the solution for objective:\n{state.objective}\n"
            f"Architectural specification:\n{state.architecture_design}\n"
            f"{feedback_context}\n"
            f"Write the required source files to workspace using the write_file or replace_content tools."
        )
        res = await coder.run_task(prompt)
        state.implemented_files = coder.tools.get("list_files") and ["src/"] or []
        state.blackboard["coder_output"] = res.output
        return state

    async def tester_node(state: SwarmState) -> SwarmState:
        state.update_stage("testing", "tester")
        prompt = (
            f"Write unit tests verifying the implementation and execute pytest.\n"
            f"Ensure edge cases and core requirements for '{state.objective}' are verified."
        )
        res = await tester.run_task(prompt)
        state.test_results = {"summary": res.output, "passed": "error" not in res.output.lower() and "failed" not in res.output.lower()}
        return state

    async def reviewer_node(state: SwarmState) -> SwarmState:
        state.update_stage("reviewing", "reviewer")
        prompt = (
            f"Review the code changes and test results for objective: '{state.objective}'.\n"
            f"Test results: {state.test_results.get('summary', '')[:500]}\n"
            f"Determine if the implementation is production-ready. Say 'APPROVED' if acceptable, or list corrective items."
        )
        res = await reviewer.run_task(prompt)
        is_approved = "approved" in res.output.lower()
        state.review_approved = is_approved
        if not is_approved:
            state.review_comments.append(res.output)
            state.iteration += 1
        return state

    async def security_node(state: SwarmState) -> SwarmState:
        state.update_stage("security_scan", "security")
        prompt = (
            f"Perform a security audit on the workspace.\n"
            f"Check for secret leaks, unsafe commands, or improper validations."
        )
        res = await security.run_task(prompt)
        state.security_passed = "vulnerability found" not in res.output.lower()
        return state

    async def complete_node(state: SwarmState) -> SwarmState:
        state.update_stage("completed", "complete")
        state.is_completed = True
        return state

    def route_review_decision(state: SwarmState) -> str:
        """Route to next node based on review and test results."""
        if state.error:
            return "complete"

        # If tests passed or review approved or reached max iterations
        if state.review_approved or state.iteration >= state.max_iterations:
            return "security"
        else:
            return "retry_coder"

    # Assemble graph
    graph.add_node("architect", architect_node)
    graph.add_node("plan_checkpoint", plan_checkpoint_node)
    graph.add_node("planner", planner_node)
    graph.add_node("coder", coder_node)
    graph.add_node("tester", tester_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("security", security_node)
    graph.add_node("complete", complete_node)

    graph.set_entry_point("architect")
    graph.add_edge("architect", "plan_checkpoint")
    graph.add_edge("plan_checkpoint", "planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "tester")
    graph.add_edge("tester", "reviewer")

    graph.add_conditional_edges(
        "reviewer",
        route_review_decision,
        {"security": "security", "retry_coder": "coder", "complete": "complete"},
    )

    graph.add_edge("security", "complete")
    graph.set_finish_point("complete")

    return graph
