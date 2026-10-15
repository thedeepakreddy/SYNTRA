#!/usr/bin/env python3
"""Manual Test Scenario 2: Approval Interrupt & Digest Validation.

Verifies:
- Extraction of approval interrupt payload.
- Cryptographic verification of HMAC-SHA256 action digest.
- Rejection of tampered action digest (DigestMismatchError).
- Rejection of expired approval token (ApprovalExpiredError).
- Resumption with valid approval.
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import MemorySaver

from syntra.core.config import get_settings
from syntra.domain.entities import compute_action_digest
from syntra.domain.exceptions import ApprovalExpiredError, DigestMismatchError
from syntra.orchestration.approval_interceptor import _IN_MEMORY_APPROVALS
from syntra.orchestration.engine import WorkflowOrchestrationEngine


async def main() -> None:
    print("[*] Scenario 2: Approval Interrupt, Cryptographic Digest & Expiration Enforcement")
    checkpointer = MemorySaver()
    engine = WorkflowOrchestrationEngine(checkpointer=checkpointer)
    settings = get_settings()

    mission_id = uuid4()
    org_id = uuid4()

    print("[*] Starting mission to reach approval interrupt...")
    result = await engine.start_mission(
        mission_id=mission_id,
        org_id=org_id,
        objective="Implement security authorization interceptor",
    )

    interrupt_payload = result["__interrupt__"][0].value
    approval_id = UUID(interrupt_payload["approval_id"])
    action_digest = interrupt_payload["action_digest"]
    action_type = interrupt_payload["action_type"]
    target_resource = interrupt_payload["target_resource"]
    mission_version = interrupt_payload["mission_version"]
    expires_at = datetime.fromisoformat(interrupt_payload["expires_at"])

    print(f"[+] Emitted Approval ID:   {approval_id}")
    print(f"[+] Emitted Action Digest: {action_digest}")

    # 1. Independent HMAC-SHA256 recomputation
    recomputed = compute_action_digest(
        secret=settings.approval_secret_key,
        mission_id=mission_id,
        action_type=action_type,
        target_resource=target_resource,
        mission_version=mission_version,
        expires_at=expires_at,
    )
    print(f"[+] Recomputed Digest:     {recomputed}")
    if action_digest != recomputed:
        print("[!] FAIL: Recomputed digest does not match emitted digest!")
        sys.exit(1)
    print("[+] Digest cryptographic verification: MATCH")

    # 2. Tampered digest test
    print("[*] Testing resumption with tampered digest...")
    tampered_payload = {
        "approval_id": str(approval_id),
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "APPROVED",
        "action_digest": "tampered_digest_9876543210abcdef",
    }
    try:
        await engine.resume_approval(mission_id, tampered_payload)
        print("[!] FAIL: Tampered digest did not raise DigestMismatchError!")
        sys.exit(1)
    except DigestMismatchError:
        print("[+] Caught expected DigestMismatchError on tampered payload.")

    # 3. Expired approval test
    print("[*] Testing resumption with expired approval...")
    _IN_MEMORY_APPROVALS[approval_id]["expires_at"] = datetime.now(UTC) - timedelta(seconds=10)
    expired_payload = {
        "approval_id": str(approval_id),
        "org_id": str(org_id),
        "user_id": str(uuid4()),
        "decision": "APPROVED",
        "action_digest": action_digest,
    }
    try:
        await engine.resume_approval(mission_id, expired_payload)
        print("[!] FAIL: Expired approval did not raise ApprovalExpiredError!")
        sys.exit(1)
    except ApprovalExpiredError:
        print("[+] Caught expected ApprovalExpiredError on expired approval.")

    # 4. Verify unexpired resumption succeeds on new mission
    print("[*] Testing valid unexpired resumption...")
    m2_id = uuid4()
    r2 = await engine.start_mission(m2_id, org_id, "Valid unexpired approval test")
    p2 = r2["__interrupt__"][0].value
    resumed = await engine.resume_approval(
        m2_id,
        {
            "approval_id": p2["approval_id"],
            "org_id": str(org_id),
            "user_id": str(uuid4()),
            "decision": "APPROVED",
            "action_digest": p2["action_digest"],
        },
    )
    print(f"[+] Advanced past approval to phase: {resumed['current_phase']}")

    print("[SUCCESS] Scenario 2 passed: All digest, tampering, and expiration security checks verified.\n")


if __name__ == "__main__":
    asyncio.run(main())
