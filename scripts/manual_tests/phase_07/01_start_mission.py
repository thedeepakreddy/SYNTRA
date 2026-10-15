#!/usr/bin/env python3
"""Manual Test Scenario 1: Mission Startup and Initial Checkpoint.

Verifies:
- Mission initiates in INTAKE and progresses through PLANNING to AWAITING_APPROVAL.
- State is checkpointed cleanly in checkpointer.
- Graph pauses deterministically at human interrupt checkpoint.
"""

import asyncio
import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main() -> None:
    print("[*] Scenario 1: Mission Startup & Interrupt Checkpoint")
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)

    mission_id = uuid4()
    org_id = uuid4()
    objective = "Build high-throughput Redis caching layer for user session state"

    print(f"[*] Starting mission {mission_id} (org: {org_id})...")
    result = await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective=objective,
    )

    # 1. Assert interrupt payload
    if "__interrupt__" not in result:
        print("[!] FAIL: Expected __interrupt__ in graph result")
        sys.exit(1)

    interrupts = result["__interrupt__"]
    if not interrupts:
        print("[!] FAIL: Empty interrupts list")
        sys.exit(1)

    payload = interrupts[0].value
    print(f"[+] Caught interrupt: action_type={payload.get('action_type')}")
    print(f"[+] Approval ID: {payload.get('approval_id')}")
    print(f"[+] Action Digest: {payload.get('action_digest')}")

    # 2. Assert snapshot state
    snap = await engine.get_mission_state(mission_id)
    current_phase = snap["values"].get("current_phase")
    domain_state = snap["values"].get("domain_state")
    print(f"[+] Snapshot Current Phase: {current_phase}")
    print(f"[+] Snapshot Domain State:  {domain_state}")

    if current_phase != "AWAITING_APPROVAL" or domain_state != "AWAITING_APPROVAL":
        print(f"[!] FAIL: Expected AWAITING_APPROVAL, got {current_phase} / {domain_state}")
        sys.exit(1)

    executed_nodes = snap["values"].get("executed_nodes", [])
    print(f"[+] Executed Nodes Trail: {executed_nodes}")
    expected_trail = [
        "intake",
        "requirements_analysis",
        "architecture_planning",
        "task_plan_generation",
        "plan_validation",
    ]
    if not all(node in executed_nodes for node in expected_trail):
        print(f"[!] FAIL: Missing expected nodes in execution trail: {executed_nodes}")
        sys.exit(1)

    print("[SUCCESS] Scenario 1 passed: Mission started, planned, and halted at human interrupt.\n")


if __name__ == "__main__":
    asyncio.run(main())
