#!/usr/bin/env python3
"""Manual Test Scenario 2: Dependency Validation & Cyclic Graph Rejection.

Verifies:
- Cyclic graph structures (A -> B -> C -> A) are strictly rejected with DAGValidationError.
- Self-referencing dependencies (A -> A) are rejected.
- Dependencies referencing non-existent tasks are rejected.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from syntra.scheduling.dag_engine import TaskDAGEngine
from syntra.scheduling.exceptions import DAGValidationError


async def main() -> None:
    print("[*] Scenario 2: Dependency Validation & Cyclic Graph Rejection")
    dag_engine = TaskDAGEngine()

    t1, t2, t3 = uuid4(), uuid4(), uuid4()
    tasks = [
        {"id": t1, "identifier": "T-1", "title": "Task 1"},
        {"id": t2, "identifier": "T-2", "title": "Task 2"},
        {"id": t3, "identifier": "T-3", "title": "Task 3"},
    ]

    # Test 1: Cycle A -> B -> C -> A
    cycle_deps = [
        {"task_id": t2, "depends_on_task_id": t1},
        {"task_id": t3, "depends_on_task_id": t2},
        {"task_id": t1, "depends_on_task_id": t3},
    ]
    print("[*] Testing cyclic dependency rejection...")
    try:
        dag_engine.validate_graph(tasks, cycle_deps)
        print("[!] FAIL: Expected DAGValidationError for cyclic graph")
        sys.exit(1)
    except DAGValidationError as exc:
        print(f"[+] Successfully caught expected cyclic validation error: {exc}")

    # Test 2: Self reference
    self_deps = [{"task_id": t1, "depends_on_task_id": t1}]
    print("[*] Testing self-referencing dependency rejection...")
    try:
        dag_engine.validate_graph(tasks, self_deps)
        print("[!] FAIL: Expected DAGValidationError for self-reference")
        sys.exit(1)
    except DAGValidationError as exc:
        print(f"[+] Successfully caught expected self-reference error: {exc}")

    # Test 3: Unknown dependency
    unknown_deps = [{"task_id": t1, "depends_on_task_id": uuid4()}]
    print("[*] Testing unknown dependency rejection...")
    try:
        dag_engine.validate_graph(tasks, unknown_deps)
        print("[!] FAIL: Expected DAGValidationError for unknown dependency")
        sys.exit(1)
    except DAGValidationError as exc:
        print(f"[+] Successfully caught expected unknown dependency error: {exc}")

    print("[*] PASS: Scenario 2 complete.")


if __name__ == "__main__":
    import sys

    asyncio.run(main())
