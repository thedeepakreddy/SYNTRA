#!/usr/bin/env python3
"""Manual Test Scenario 4: Authorization and Full End-to-End Progression.

Verifies:
- Authorized human approval advances workflow from AWAITING_APPROVAL through READY.
- Schedules, executes, integrates, and verifies tasks.
- Reaches second human interrupt gate at AWAITING_DELIVERY_APPROVAL.
- Final delivery approval transitions mission to terminal COMPLETED.
"""

import asyncio
import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main() -> None:
    print("[*] Scenario 4: Plan Approval, Execution, Delivery Gate & Completion")
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)

    mission_id = uuid4()
    org_id = uuid4()

    print(f"[*] Starting mission {mission_id}...")
    res = await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Author and release token rate limiter middleware",
    )

    p1 = res["__interrupt__"][0].value
    print(f"[+] Paused at Gate 1: {p1['action_type']} (id={p1['approval_id']})")

    # 1. Authorize Task Plan
    print("[*] Submitting plan authorization...")
    r1 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": p1["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": p1["action_digest"],
        },
    )

    if "__interrupt__" not in r1 or not r1["__interrupt__"]:
        print(f"[!] FAIL: Expected __interrupt__ for delivery approval, got phase={r1.get('current_phase')}")
        sys.exit(1)

    p2 = r1["__interrupt__"][0].value
    print(f"[+] Paused at Gate 2: {p2['action_type']} (id={p2['approval_id']})")

    # 2. Authorize Delivery Release
    print("[*] Submitting delivery release authorization...")
    r2 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": p2["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": p2["action_digest"],
        },
    )

    print(f"[+] Final Reached Phase: {r2['current_phase']}")
    print(f"[+] Final Domain State:  {r2['domain_state']}")

    if r2["current_phase"] != "COMPLETED" or r2["domain_state"] != "COMPLETED":
        print(f"[!] FAIL: Expected COMPLETED state, got {r2['current_phase']} / {r2['domain_state']}")
        sys.exit(1)

    print(f"[+] Final Executed Nodes Trail: {r2['executed_nodes']}")
    print("[SUCCESS] Scenario 4 passed: Complete two-gate human approval and linear execution to COMPLETED.\n")


if __name__ == "__main__":
    asyncio.run(main())
