#!/usr/bin/env python3
"""Manual Test Scenario 1: Task DAG Creation and Topological Ordering.

Verifies:
- Creation of a structured DAG with multiple engineering tasks and dependency relationships.
- Validation and topological ordering via TaskDAGEngine.
- Invariant: Dependencies execute strictly before their downstream dependents.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

from syntra.scheduling.dag_engine import TaskDAGEngine


async def main() -> None:
    print("[*] Scenario 1: Task DAG Creation and Topological Ordering")
    dag_engine = TaskDAGEngine()

    # Define tasks
    t1_id, t2_id, t3_id, t4_id = uuid4(), uuid4(), uuid4(), uuid4()
    tasks = [
        {"id": t1_id, "identifier": "T-ARCH", "title": "System Architecture"},
        {"id": t2_id, "identifier": "T-BE-MODELS", "title": "Database Models"},
        {"id": t3_id, "identifier": "T-BE-API", "title": "REST API Endpoints"},
        {"id": t4_id, "identifier": "T-QA", "title": "Acceptance Tests"},
    ]

    # Dependencies: T1 -> T2 -> T3 -> T4
    dependencies = [
        {"task_id": t2_id, "depends_on_task_id": t1_id},
        {"task_id": t3_id, "depends_on_task_id": t2_id},
        {"task_id": t4_id, "depends_on_task_id": t3_id},
    ]

    print(f"[*] Validating DAG with {len(tasks)} tasks and {len(dependencies)} dependency edges...")
    topo_order = dag_engine.validate_graph(tasks, dependencies, plan_version=1)
    print(f"[+] Topological order computed: {[str(t)[:8] for t in topo_order]}")

    # Verify order
    indices = {t_id: idx for idx, t_id in enumerate(topo_order)}
    assert indices[t1_id] < indices[t2_id], "T1 must precede T2"
    assert indices[t2_id] < indices[t3_id], "T2 must precede T3"
    assert indices[t3_id] < indices[t4_id], "T3 must precede T4"

    print("[+] All topological ordering invariants verified successfully.")
    print("[*] PASS: Scenario 1 complete.")


if __name__ == "__main__":
    asyncio.run(main())
