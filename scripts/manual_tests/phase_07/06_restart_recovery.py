#!/usr/bin/env python3
"""Manual Test Scenario 6: Process Restart and Crash Recovery.

Verifies:
- Mission starts and suspends at approval gate in Process 1.
- Process 1 is discarded (simulating server crash).
- Fresh Process 2 initializes with shared checkpointer and recovers state.
- Lifecycle recover_mission verifies consistent thread checkpoint.
- Resumes execution seamlessly without re-running completed nodes.
"""

import asyncio
import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.orchestration.engine import WorkflowOrchestrationEngine
from syntra.orchestration.lifecycle_service import recover_mission


async def main() -> None:
    print("[*] Scenario 6: Process Restart & Crash Recovery")
    shared_checkpointer = MemorySaver()

    mission_id = uuid4()
    org_id = uuid4()

    # 1. Process 1: Start mission to reach human approval checkpoint
    print("[*] Process 1: Launching mission and advancing to interrupt...")
    engine_1 = WorkflowOrchestrationEngine(checkpointer=shared_checkpointer)
    res1 = await engine_1.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Verify durability across process crash boundaries",
    )
    p = res1["__interrupt__"][0].value
    approval_id = p["approval_id"]
    action_digest = p["action_digest"]
    print(f"[+] Process 1 reached approval gate: id={approval_id}")

    # 2. Simulate Process 1 crash / exit
    print("[*] Simulating Process 1 crash / termination (discarding engine_1)...")
    del engine_1

    # 3. Process 2: Fresh startup using shared checkpointer
    print("[*] Process 2: Initializing fresh engine against shared checkpointer...")
    engine_2 = WorkflowOrchestrationEngine(checkpointer=shared_checkpointer)

    # 4. State query in Process 2
    snap = await engine_2.get_mission_state(mission_id)
    print(f"[+] Process 2 retrieved domain_state: {snap['values'].get('domain_state')}")
    print(f"[+] Process 2 retrieved current_phase: {snap['values'].get('current_phase')}")

    if snap["values"].get("domain_state") != "AWAITING_APPROVAL":
        print("[!] FAIL: Process 2 failed to recover AWAITING_APPROVAL state from checkpointer!")
        sys.exit(1)

    # 5. Lifecycle recover_mission check
    recovery_report = await recover_mission(
        mission_id=mission_id,
        org_id=org_id,
        checkpointer=shared_checkpointer,
    )
    print(f"[+] Lifecycle recovery report: {recovery_report['recovered_from']}")
    if recovery_report["recovered_from"] != "CHECKPOINT_AND_DATABASE":
        print("[!] FAIL: Expected recovered_from=CHECKPOINT_AND_DATABASE")
        sys.exit(1)

    # 6. Process 2 resumes execution from checkpoint
    print("[*] Process 2: Resuming mission from recovered interrupt...")
    res2 = await engine_2.resume_approval(
        mission_id=mission_id,
        decision_payload={
            "approval_id": approval_id,
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": action_digest,
        },
    )

    executed_nodes = res2.get("executed_nodes", [])
    print(f"[+] Executed Nodes: {executed_nodes}")
    if executed_nodes.count("intake") > 1:
        print("[!] FAIL: 'intake' node was executed multiple times upon restart recovery!")
        sys.exit(1)

    print("[SUCCESS] Scenario 6 passed: Crash recovery and restart persistence verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
