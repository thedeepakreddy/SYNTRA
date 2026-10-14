# ADR-006: Multi-Tier Hybrid Autonomy with Cryptographic Approval Digests

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, Security Engineer, AI Governance Lead

---

## 1. Context & Problem Statement
Full unconstrained AI autonomy in software engineering poses grave risks of unintended destructive actions (deleting repositories, force-pushing broken code to production, runaway token spend). Conversely, requiring human approval for every single line of code or read operation paralyzes autonomous throughput. We need a governance model that provides high velocity for safe operations while enforcing immutable human oversight at critical risk gates.

---

## 2. Decision Drivers
- **Safety First**: Dangerous actions (external git pushes, PR merges, production releases, budget increases) must never occur without verified human authorization.
- **Velocity**: Harmless actions (reading files, running tests in isolated sandboxes, creating draft plans) must execute autonomously.
- **Tamper-Resistance**: Approvals must be cryptographically bound to the exact payload presented to the human, preventing replay attacks or modification after approval.

---

## 3. Considered Options
1. **Option A: Full Unconstrained Autonomy**: AI has full access to git remotes and production deployments. Rejected due to extreme risk.
2. **Option B: Strict Step-by-Step Approval**: Human must click approve on every shell command and file read. Rejected due to severe latency and developer fatigue.
3. **Option C: Tiered Hybrid Autonomy with Cryptographic Approval Digests**: Autonomous execution within approved sandbox boundaries; mandatory, single-use, HMAC-SHA256 bound human approvals for external side effects and plan changes.

---

## 4. Decision Outcome
**Chosen Option**: **Option C: Tiered Hybrid Autonomy with Cryptographic Approval Digests**.

### Key Rules:
- Supports four operational modes: `AUTONOMOUS`, `SEMI_AUTONOMOUS`, `SUPERVISED`, `STRICT_APPROVAL`.
- Mandatory Human Approval is strictly required for:
  1. Initial mission scope
  2. Material plan changes
  3. External repository writes
  4. Pull request creation
  5. Protected branch merges
  6. Production deployments
  7. Budget increases
  8. Security policy changes
- Approvals verify an HMAC-SHA256 digest:
  $$\text{ActionDigest} = \text{HMAC-SHA256}_{K}(\text{mission\_id} \parallel \text{action\_type} \parallel \text{payload} \parallel \text{version} \parallel \text{expiry})$$
- Resolved approvals cannot be reused or replayed.

### Tradeoffs:
- **Pros**: Balanced velocity and safety, tamper-proof audit trail, zero unauthorized production mutations.
- **Cons**: Workflow pauses until human operator responds to pending approval checkpoints.
