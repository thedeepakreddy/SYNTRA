#!/usr/bin/env python3
"""Manual Test Scenario 3: Plan Rejection and Circuit Breaker Tripping.

Verifies:
- Human rejection routes to REPLANNING (domain: PLANNING).
- replan_count increments and a new plan is generated and paused at interrupt.
- Repeated rejections exceeding max_replan_limit trip the circuit breaker.
- Terminal FAILED state is reached in both workflow and domain aggregate.
- Post-failure resumes cannot restart the mission.
"""

import asyncio
import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main() -> None:
    print("[*] Scenario 3: Plan Rejection & Replanning Circuit Breaker")
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)

    mission_id = uuid4()
    org_id = uuid4()
    max_replan = 2

    print(f"[*] Starting mission {mission_id} with max_replan_limit={max_replan}...")
    res = await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Design multi-tenant event delivery bus",
        max_replan_limit=max_replan,
    )

    p1 = res["__interrupt__"][0].value
    print(f"[+] Reached initial interrupt (replan_count={res.get('replan_count', 0)})")

    # 1. Rejection 1 (replan_count -> 1)
    print("[*] Submitting rejection 1: 'Scope too broad. Narrow to Kafka broker.'")
    r1 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": p1["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "REJECTED",
            "feedback": "Scope too broad. Narrow to Kafka broker.",
            "action_digest": p1["action_digest"],
        },
    )
    print(f"[+] Post-Rejection 1 Phase: {r1['current_phase']}, replan_count: {r1['replan_count']}")
    if r1["replan_count"] != 1 or r1["current_phase"] != "AWAITING_APPROVAL":
        print("[!] FAIL: Expected replan_count=1 and phase=AWAITING_APPROVAL")
        sys.exit(1)
    p2 = r1["__interrupt__"][0].value

    # 2. Rejection 2 (replan_count -> 2, at limit)
    print("[*] Submitting rejection 2: 'Add partition key hashing spec.'")
    r2 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": p2["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "REJECTED",
            "feedback": "Add partition key hashing spec.",
            "action_digest": p2["action_digest"],
        },
    )
    print(f"[+] Post-Rejection 2 Phase: {r2['current_phase']}, replan_count: {r2['replan_count']}")
    if r2["replan_count"] != 2 or r2["current_phase"] != "AWAITING_APPROVAL":
        print("[!] FAIL: Expected replan_count=2 and phase=AWAITING_APPROVAL")
        sys.exit(1)
    p3 = r2["__interrupt__"][0].value

    # 3. Rejection 3 (replan_count -> 3 > max_replan_limit 2, circuit breaker trips)
    print("[*] Submitting rejection 3: Exceeding limit -> Circuit breaker trips...")
    r3 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": p3["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "REJECTED",
            "feedback": "Still inadequate.",
            "action_digest": p3["action_digest"],
        },
    )

    print(f"[+] Post-Rejection 3 Phase:        {r3['current_phase']}")
    print(f"[+] Post-Rejection 3 Domain State: {r3['domain_state']}")
    print(f"[+] Recorded Error Message:        {r3.get('error_message')}")

    if r3["current_phase"] != "FAILED" or r3["domain_state"] != "FAILED":
        print("[!] FAIL: Expected FAILED state after circuit breaker trip!")
        sys.exit(1)

    # 4. Verify post-failure resumption attempt is rejected/inactive
    print("[*] Attempting to resume failed mission...")
    r4 = await engine.resume_approval(
        mission_id,
        {
            "approval_id": str(uuid4()),
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": "dummy",
        },
    )
    if r4["current_phase"] != "FAILED":
        print("[!] FAIL: Mission restarted after terminal FAILED state!")
        sys.exit(1)

    print("[SUCCESS] Scenario 3 passed: Rejection replanning loop and circuit breaker verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
