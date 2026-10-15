#!/usr/bin/env python3
"""Manual Test Scenario 5: Checkpoint State & Metadata Inspection.

Verifies:
- Checkpoint persistence in checkpointer.
- Retrieval of state tuples via thread_id ("mission:{mission_id}").
- State channel inspection (domain_state, phase, replan_count, executed_nodes).
- Absence of sensitive secret keys or credentials in checkpoint payload/metadata.
"""

import asyncio
import sys
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.orchestration.checkpointer import build_mission_thread_id, create_checkpoint_metadata
from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main() -> None:
    print("[*] Scenario 5: Checkpoint State & Metadata Inspection")
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)

    mission_id = uuid4()
    org_id = uuid4()
    thread_id = build_mission_thread_id(mission_id)

    print(f"[*] Starting mission {mission_id} on thread {thread_id}...")
    await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Inspect internal checkpoint representation and metadata",
    )

    # 1. Retrieve checkpoint tuple directly from checkpointer
    print(f"[*] Querying checkpointer for thread_id={thread_id}...")
    checkpoint_tuple = await checkpointer.aget_tuple({"configurable": {"thread_id": thread_id}})

    if not checkpoint_tuple:
        print("[!] FAIL: No checkpoint tuple found for thread!")
        sys.exit(1)

    print(f"[+] Retrieved checkpoint ID: {checkpoint_tuple.checkpoint.get('id')}")
    channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
    print(f"[+] Channel Domain State:   {channel_values.get('domain_state')}")
    print(f"[+] Channel Current Phase:  {channel_values.get('current_phase')}")
    print(f"[+] Channel Mission Version: {channel_values.get('mission_version')}")
    print(f"[+] Executed Nodes Count:   {len(channel_values.get('executed_nodes', []))}")

    if channel_values.get("domain_state") != "AWAITING_APPROVAL":
        print(f"[!] FAIL: Expected domain_state=AWAITING_APPROVAL, got {channel_values.get('domain_state')}")
        sys.exit(1)

    # 2. Verify security guard: create_checkpoint_metadata strips secret keys
    print("[*] Verifying secret stripping in checkpoint metadata helper...")
    meta = create_checkpoint_metadata(
        mission_id=str(mission_id),
        phase="AWAITING_APPROVAL",
        version=1,
        extra={
            "safe_tag": "release-v1",
            "api_key": "sk-secret-12345",
            "approval_secret_key": "top-secret-hmac-key",
            "access_token": "bearer-token-abc",
        },
    )
    print(f"[+] Filtered Metadata Keys: {list(meta.keys())}")
    if "api_key" in meta or "approval_secret_key" in meta or "access_token" in meta:
        print("[!] FAIL: Sensitive credentials were not stripped from checkpoint metadata!")
        sys.exit(1)

    if meta.get("safe_tag") != "release-v1":
        print("[!] FAIL: Safe metadata field was dropped!")
        sys.exit(1)

    print("[SUCCESS] Scenario 5 passed: Checkpoint channels and metadata integrity verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
