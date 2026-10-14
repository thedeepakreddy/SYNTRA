"""Pure domain task DAG validator.

Verifies cycle-freedom, mission containment, self-dependency prohibitions, and topological order.
"""

from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from syntra.domain.entities import TaskState
from syntra.domain.exceptions import (
    CrossMissionDependencyError,
    CyclicDependencyError,
    InvalidTaskGraphError,
)


def validate_task_dag(
    tasks: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    plan_version: int = 1,
) -> list[UUID]:
    """Validate a task DAG against all structural and relational invariants.

    Returns:
        List of task IDs in valid topological execution order.

    Raises:
        InvalidTaskGraphError: If tasks or plan versions are malformed, or references are unknown.
        CrossMissionDependencyError: If a dependency spans tasks from different missions.
        CyclicDependencyError: If circular dependencies or self-dependencies exist.
    """
    if plan_version < 1:
        raise InvalidTaskGraphError(f"Invalid plan version: {plan_version}. Must be >= 1.")

    if not tasks:
        return []

    # 1. Check duplicate task IDs and extract metadata
    task_map: dict[UUID, dict[str, Any]] = {}
    for t in tasks:
        t_id = t["id"] if isinstance(t["id"], UUID) else UUID(str(t["id"]))
        if t_id in task_map:
            raise InvalidTaskGraphError(f"Duplicate task ID detected: {t_id}")

        # Validate task state if present
        if "state" in t and t["state"] is not None:
            state_val = t["state"]
            if isinstance(state_val, str):
                try:
                    TaskState(state_val)
                except ValueError:
                    raise InvalidTaskGraphError(f"Invalid task state for task {t_id}: {state_val}")

        task_map[t_id] = t

    # 2. Check dependencies
    adj_list: dict[UUID, list[UUID]] = defaultdict(list)
    in_degree: dict[UUID, int] = {t_id: 0 for t_id in task_map}

    for dep in dependencies:
        t_id = dep["task_id"] if isinstance(dep["task_id"], UUID) else UUID(str(dep["task_id"]))
        dep_id = (
            dep["depends_on_task_id"]
            if isinstance(dep["depends_on_task_id"], UUID)
            else UUID(str(dep["depends_on_task_id"]))
        )

        # Check self-dependency
        if t_id == dep_id:
            raise CyclicDependencyError(f"Self-dependency detected for task {t_id} -> {dep_id}.")

        # Check unknown task reference
        if t_id not in task_map:
            raise InvalidTaskGraphError(f"Dependency references unknown task_id: {t_id}")
        if dep_id not in task_map:
            raise InvalidTaskGraphError(f"Dependency references unknown depends_on_task_id: {dep_id}")

        # Check cross-mission dependency
        t_mission = task_map[t_id].get("mission_id")
        dep_mission = task_map[dep_id].get("mission_id")
        if t_mission is not None and dep_mission is not None and t_mission != dep_mission:
            raise CrossMissionDependencyError(
                f"Cross-mission dependency detected: task {t_id} (mission {t_mission}) depends on {dep_id} (mission {dep_mission})."
            )

        adj_list[dep_id].append(t_id)
        in_degree[t_id] += 1

    # 3. Kahn's algorithm for cycle detection and topological sorting
    queue: deque[UUID] = deque([t_id for t_id, deg in in_degree.items() if deg == 0])
    topological_order: list[UUID] = []

    while queue:
        curr = queue.popleft()
        topological_order.append(curr)

        for neighbor in adj_list[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(topological_order) != len(task_map):
        unresolved = [str(t_id) for t_id, deg in in_degree.items() if deg > 0]
        raise CyclicDependencyError(f"Cyclic dependency detected among tasks: {', '.join(unresolved)}")

    return topological_order
