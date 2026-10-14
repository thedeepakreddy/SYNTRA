"""Deterministic State Graph execution engine for multi-agent workflows."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any
from syntra.core.events import Event, EventType, get_event_bus
from syntra.core.exceptions import SwarmOrchestrationError
from syntra.swarm.state import SwarmState

logger = logging.getLogger(__name__)

StateNodeFunc = Callable[[SwarmState], Coroutine[Any, Any, SwarmState]]
ConditionalRouterFunc = Callable[[SwarmState], str]


class StateGraph:
    """Directed state graph supporting cyclic iterative refinement and conditional routing."""

    def __init__(self, name: str = "swarm_workflow") -> None:
        self.name = name
        self._nodes: dict[str, StateNodeFunc] = {}
        self._edges: dict[str, str] = {}
        self._conditional_edges: dict[str, tuple[ConditionalRouterFunc, dict[str, str]]] = {}
        self._entry_point: str | None = None
        self._finish_nodes: set[str] = set()

    def add_node(self, name: str, func: StateNodeFunc) -> None:
        """Register a processing node."""
        if name in self._nodes:
            raise SwarmOrchestrationError(f"Node '{name}' already registered in graph.")
        self._nodes[name] = func

    def add_edge(self, from_node: str, to_node: str) -> None:
        """Register a deterministic edge from one node to another."""
        self._edges[from_node] = to_node

    def add_conditional_edges(
        self,
        from_node: str,
        router: ConditionalRouterFunc,
        path_map: dict[str, str],
    ) -> None:
        """Register a conditional branch evaluated at runtime."""
        self._conditional_edges[from_node] = (router, path_map)

    def set_entry_point(self, name: str) -> None:
        """Set starting node."""
        self._entry_point = name

    def set_finish_point(self, name: str) -> None:
        """Set terminal node."""
        self._finish_nodes.add(name)

    async def execute(self, state: SwarmState, max_steps: int = 40) -> SwarmState:
        """Execute the state graph starting from entry point."""
        if not self._entry_point:
            raise SwarmOrchestrationError("Graph has no entry point configured.")

        current_node_name = self._entry_point
        step_count = 0

        while current_node_name and step_count < max_steps:
            step_count += 1
            node_func = self._nodes.get(current_node_name)
            if not node_func:
                raise SwarmOrchestrationError(f"Node '{current_node_name}' not found in graph.")

            state.current_node = current_node_name

            await get_event_bus().publish(
                Event(
                    type=EventType.TASK_PROGRESS,
                    session_id=state.session_id,
                    data={
                        "node": current_node_name,
                        "stage": state.stage,
                        "step": step_count,
                        "iteration": state.iteration,
                    },
                )
            )

            # Execute node logic
            try:
                state = await node_func(state)
            except Exception as exc:
                state.error = f"Error in node '{current_node_name}': {exc}"
                state.is_completed = False
                logger.exception(state.error)
                raise SwarmOrchestrationError(state.error) from exc

            # Check if this node is terminal
            if current_node_name in self._finish_nodes or state.is_completed:
                state.is_completed = True
                break

            # Resolve next node
            if current_node_name in self._conditional_edges:
                router, path_map = self._conditional_edges[current_node_name]
                route_key = router(state)
                next_node = path_map.get(route_key)
                if not next_node:
                    raise SwarmOrchestrationError(
                        f"Router for '{current_node_name}' returned unmapped key '{route_key}'. Valid: {list(path_map.keys())}"
                    )
                current_node_name = next_node
            elif current_node_name in self._edges:
                current_node_name = self._edges[current_node_name]
            else:
                # No outgoing edge: finish
                state.is_completed = True
                break
        else:
            raise SwarmOrchestrationError(
                f"State graph exceeded max step execution threshold ({max_steps}) without terminating."
            )

        return state
