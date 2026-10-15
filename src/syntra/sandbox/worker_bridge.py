"""Worker execution adapter executing tasks inside isolated container sandboxes."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
from typing import Mapping
from uuid import NAMESPACE_URL, uuid5

from syntra.domain.entities import AttemptState
from syntra.sandbox.models import ContainerConfig
from syntra.sandbox.provider import DockerSandboxProvider, SandboxProvider
from syntra.scheduling.models import TaskDispatchPayload, TaskExecutionResult

logger = logging.getLogger(__name__)


class SandboxWorkerAdapter:
    """Production-grade worker adapter that executes tasks within isolated container sandboxes.

    Guarantees:
    1. Zero execution directly on the host machine.
    2. Ephemeral Git worktree branched per task attempt.
    3. Strict container isolation (read-only root, tmpfs, network none, non-root user, limits).
    4. Deterministic unified diff extraction.
    5. Clean teardown and process pruning in finally blocks.
    """

    def __init__(
        self,
        repository_path: Path | str,
        provider: SandboxProvider | None = None,
        worker_id: str = "sandbox-worker-01",
        config: ContainerConfig | None = None,
        base_commit: str = "HEAD",
    ) -> None:
        self.repo_path = Path(repository_path).resolve()
        self.provider = provider or DockerSandboxProvider(default_config=config)
        self.worker_id = worker_id
        self.config = config or ContainerConfig()
        self.base_commit = base_commit

    async def execute_task(
        self,
        dispatch: TaskDispatchPayload,
        code_changes: Mapping[str, str] | None = None,
        commands_to_run: list[str] | None = None,
        tokens_consumed: int = 0,
        cost_usd: Decimal = Decimal("0"),
        before_effect: Callable[[], Awaitable[None]] | None = None,
    ) -> TaskExecutionResult:
        """Execute an engineering task inside an ephemeral worktree and isolated container."""
        logger.info(
            "[SANDBOX_WORKER] Executing task %s attempt %d for role %s in isolated container",
            dispatch.task_id,
            dispatch.attempt_number,
            dispatch.assigned_role,
        )

        executor = getattr(self, "agent_executor", None)
        if executor and before_effect is None:
            raise ValueError("Autonomous execution requires an authoritative lease guard")

        if before_effect:
            await before_effect()
        sandbox = await self.provider.create_sandbox(
            task_id=dispatch.task_id,
            attempt_number=dispatch.attempt_number,
            repository_path=self.repo_path,
            base_commit=self.base_commit,
            config=self.config,
        )

        all_stdout: list[str] = []
        all_stderr: list[str] = []
        overall_exit_code = 0
        timed_out = False
        error_msg: str | None = None
        evidence: list[dict[str, object]] = []

        try:
            if executor:
                return await executor(sandbox, dispatch, before_effect)
            # 1. Apply code changes if provided (e.g. agent edits)
            if code_changes:
                for rel_path, content in code_changes.items():
                    if before_effect:
                        await before_effect()
                    sandbox.write_file(rel_path, content)

            # 2. Execute commands inside the isolated container
            if commands_to_run:
                for cmd in commands_to_run:
                    if before_effect:
                        await before_effect()
                    exec_res = await sandbox.execute_command(cmd)
                    evidence.append(asdict(exec_res))
                    all_stdout.append(f"$ {cmd}\n{exec_res.stdout}")
                    if exec_res.stderr:
                        all_stderr.append(exec_res.stderr)

                    if exec_res.timed_out:
                        timed_out = True
                        overall_exit_code = -1
                        error_msg = f"Command timed out: {cmd}"
                        break
                    elif exec_res.exit_code != 0:
                        overall_exit_code = exec_res.exit_code
                        error_msg = f"Command '{cmd}' failed with exit code {exec_res.exit_code}: {exec_res.stderr}"
                        break

            # 3. Extract unified diff from the worktree
            diff = await sandbox.get_unified_diff()
            artifact_ids = []
            if diff:
                # Standalone adapter evidence is durable locally; the consumer also
                # persists the authoritative copy through ArtifactRepository.
                digest = hashlib.sha256(diff.encode()).hexdigest()
                artifact_dir = self.repo_path / ".syntra" / "artifacts"
                artifact_dir.mkdir(parents=True, exist_ok=True)
                (artifact_dir / f"{digest}.patch").write_text(diff, encoding="utf-8")
                artifact_ids.append(uuid5(NAMESPACE_URL, f"syntra:patch:{digest}"))

            status = AttemptState.SUCCEEDED if overall_exit_code == 0 and not timed_out else AttemptState.FAILED
            summary = (
                f"Task {dispatch.task_id} completed successfully inside container sandbox."
                if status == AttemptState.SUCCEEDED
                else f"Task {dispatch.task_id} failed in container sandbox: {error_msg}"
            )

            return TaskExecutionResult(
                task_id=dispatch.task_id,
                attempt_number=dispatch.attempt_number,
                worker_id=self.worker_id,
                fencing_token=dispatch.fencing_token,
                status=status,
                exit_code=overall_exit_code,
                output_summary=summary,
                error_message=error_msg,
                unified_diff=diff if diff else None,
                execution_evidence=evidence,
                produced_artifact_ids=artifact_ids,
                actual_prompt_tokens=tokens_consumed // 2,
                actual_completion_tokens=tokens_consumed // 2,
                actual_cost_usd=cost_usd,
            )

        except Exception as exc:
            logger.exception("Unexpected error during sandbox task execution: %s", exc)
            return TaskExecutionResult(
                task_id=dispatch.task_id,
                attempt_number=dispatch.attempt_number,
                worker_id=self.worker_id,
                fencing_token=dispatch.fencing_token,
                status=AttemptState.FAILED,
                exit_code=1,
                output_summary=f"Execution error: {exc}",
                error_message=str(exc),
                actual_prompt_tokens=0,
                actual_completion_tokens=0,
                actual_cost_usd=Decimal("0.000000"),
            )
        finally:
            # 4. Mandatory teardown: stop container, prune worktree, delete ephemeral branch
            await sandbox.cleanup()
