# ADR-005: Ephemeral Git Worktrees and Non-Root Process Isolation

- **Status**: ACCEPTED
- **Date**: 2026-10-15
- **Deciders**: Principal Software Architect, Security Engineer, Platform Engineer

---

## 1. Context & Problem Statement
Autonomous coding agents must edit files, install packages, and run tests on real codebases. Executing untrusted, generated code directly on the host machine presents catastrophic security risks (accidental deletion, host compromise, credential exfiltration, resource starvation). We need an isolated execution environment that is fast to provision, strictly sandboxed, and easily cleaned up.

---

## 2. Decision Drivers
- **Host Protection**: No arbitrary code execution inside the control plane.
- **Speed & Efficiency**: Instantaneous environment spin-up for rapid TDD loops.
- **Repository Isolation**: Git operations in one task must not interfere with concurrent tasks.
- **Clean Patch Generation**: Ability to extract clean unified diffs for verification and review.

---

## 3. Considered Options
1. **Option A: Heavyweight Virtual Machines (Firecracker / QEMU)**: Exceptional security boundary, but high resource overhead and slower startup time (several seconds per task).
2. **Option B: In-Memory Virtual Filesystem**: Fast, but cannot run real external binaries, compilers, or test runners (pytest, npm).
3. **Option C: Ephemeral Git Worktrees with Non-Root Process Sandboxing**: Near-instantaneous worktree creation, complete branch isolation, non-root user execution (UID 1000), strict execution timeouts (120s), output capping (1MB), and canonical path traversal verification.

---

## 4. Decision Outcome
**Chosen Option**: **Option C: Ephemeral Git Worktrees with Non-Root Process Sandboxing via `SandboxProvider`**.

### Key Rules:
- Every task attempt provisions a dedicated Git worktree at `.syntra/sandboxes/{sandbox_id}`.
- All file operations enforce canonical path checking (`Path.resolve().is_relative_to(sandbox_root)`).
- Subprocesses run under non-root UID with host secrets scrubbed from environment variables.
- Execution is strictly bounded by a 120-second timeout and 1MB output capture limit.
- Patches are extracted via `git diff -u` and uploaded to MinIO artifact storage.

### Tradeoffs:
- **Pros**: Fast ($< 100\text{ms}$ startup), lightweight, native Git integration, robust path and timeout guards.
- **Cons**: Requires Linux kernel namespaces / cgroups or container runtime in production multi-tenant environments for full kernel-level isolation.
