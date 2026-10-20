"""Hermetic Verification Runner executing tests against pristine repository worktrees."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Sequence

from syntra.domain.entities import ProtectedTestSuiteManifest, VerificationEvidence
from syntra.domain.exceptions import HermeticExecutionError
from syntra.verification.registry import ProtectedTestRegistry

# Environment variable keys that must be stripped before running untrusted test code
SENSITIVE_ENV_KEYS = frozenset(
    {
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "SYNTRA_DATABASE_URL",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ACCESS_KEY_ID",
        "SECRET_KEY",
        "JWT_SECRET",
        "REDIS_URL",
        "MINIO_ROOT_PASSWORD",
        "MINIO_SECRET_KEY",
    }
)


class HermeticVerificationRunner:
    """Executes verification test suites in an isolated, clean worktree environment."""

    def __init__(
        self,
        registry: ProtectedTestRegistry | None = None,
        default_timeout_seconds: int = 60,
    ) -> None:
        self.registry = registry or ProtectedTestRegistry()
        self.default_timeout_seconds = default_timeout_seconds

    def sanitize_environment(self) -> dict[str, str]:
        """Produce a sanitized copy of the current environment with secrets stripped."""
        clean_env = dict(os.environ)
        for key in list(clean_env.keys()):
            upper_key = key.upper()
            if upper_key in SENSITIVE_ENV_KEYS or any(
                term in upper_key for term in ("SECRET", "TOKEN", "API_KEY", "PASSWORD", "CREDENTIAL")
            ):
                del clean_env[key]
        clean_env["PYTHONUNBUFFERED"] = "1"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        return clean_env

    def parse_pytest_counts(self, stdout: str) -> tuple[int, int, int, int]:
        """Extract (passed, failed, skipped, errored) counts from pytest output."""
        passed = failed = skipped = errored = 0
        pass_match = re.search(r"(\d+)\s+passed", stdout)
        if pass_match:
            passed = int(pass_match.group(1))
        fail_match = re.search(r"(\d+)\s+failed", stdout)
        if fail_match:
            failed = int(fail_match.group(1))
        skip_match = re.search(r"(\d+)\s+skipped", stdout)
        if skip_match:
            skipped = int(skip_match.group(1))
        err_match = re.search(r"(\d+)\s+error", stdout)
        if err_match:
            errored = int(err_match.group(1))
        return passed, failed, skipped, errored

    async def run_verification(
        self,
        repo_root: Path | str,
        clean_base_commit: str,
        patch: str,
        test_command: Sequence[str] = ("pytest", "-v"),
        manifest: ProtectedTestSuiteManifest | None = None,
        timeout_seconds: int | None = None,
    ) -> VerificationEvidence:
        """Run tests against a pristine worktree with the patch applied.

        Raises:
            ProtectedTestViolationError: If patch violates protected test immutability.
            HermeticExecutionError: If worktree preparation or patch application fails fatally.
        """
        root = Path(repo_root).resolve()
        if not root.exists():
            raise HermeticExecutionError(f"Base repository directory not found: {root}")

        # 1. Fast-path check for protected test violations
        self.registry.check_patch(patch, manifest=manifest)

        timeout = timeout_seconds or self.default_timeout_seconds
        start_time = asyncio.get_event_loop().time()
        temp_dir = tempfile.mkdtemp(prefix="syntra_hermetic_")
        worktree_created = False

        try:
            # 2. Create clean worktree or clean working copy
            git_proc = await asyncio.create_subprocess_exec(
                "git",
                "worktree",
                "add",
                "--detach",
                temp_dir,
                clean_base_commit,
                cwd=str(root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await git_proc.communicate()
            if git_proc.returncode == 0:
                worktree_created = True
            else:
                # Fallback: copy repo files excluding git metadata/sandboxes
                worktree_created = False
                shutil.rmtree(temp_dir, ignore_errors=True)
                shutil.copytree(
                    root,
                    temp_dir,
                    ignore=shutil.ignore_patterns(".git", ".gemini", ".colima", "__pycache__", "sandbox_*"),
                )

            # 3. Apply the patch cleanly
            patch_file = Path(temp_dir) / "_syntra_verification.patch"
            patch_file.write_text(patch, encoding="utf-8")

            apply_proc = await asyncio.create_subprocess_exec(
                "git",
                "apply",
                "--whitespace=nowarn",
                patch_file.name,
                cwd=temp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            apply_out, apply_err = await apply_proc.communicate()
            if apply_proc.returncode != 0:
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                err_msg = apply_err.decode("utf-8", errors="replace")
                return VerificationEvidence(
                    exit_code=apply_proc.returncode or 1,
                    execution_duration_ms=duration_ms,
                    stdout_digest=hashlib.sha256(b"").hexdigest(),
                    stderr_digest=hashlib.sha256(apply_err).hexdigest(),
                    tests_passed=0,
                    tests_failed=1,
                    raw_stdout="",
                    raw_stderr=err_msg,
                    error_message=f"Git patch application failed: {err_msg.strip()}",
                )

            # Remove temporary patch file
            patch_file.unlink(missing_ok=True)

            # 4. Re-verify protected test suite integrity in workspace
            if manifest:
                self.registry.validate_workspace(temp_dir, manifest)

            # 5. Execute test command in hermetic environment
            clean_env = self.sanitize_environment()
            test_proc = await asyncio.create_subprocess_exec(
                *test_command,
                cwd=temp_dir,
                env=clean_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                test_stdout, test_stderr = await asyncio.wait_for(
                    test_proc.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                try:
                    test_proc.kill()
                    await test_proc.wait()
                except Exception:
                    pass
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                return VerificationEvidence(
                    exit_code=124,
                    execution_duration_ms=duration_ms,
                    stdout_digest=hashlib.sha256(b"").hexdigest(),
                    stderr_digest=hashlib.sha256(b"TIMEOUT").hexdigest(),
                    tests_passed=0,
                    tests_failed=1,
                    raw_stdout="",
                    raw_stderr=f"Verification execution timed out after {timeout} seconds",
                    error_message="Verification timed out",
                )

            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            stdout_str = test_stdout.decode("utf-8", errors="replace")
            stderr_str = test_stderr.decode("utf-8", errors="replace")

            p, f, s, e = self.parse_pytest_counts(stdout_str)
            if test_proc.returncode != 0 and f == 0 and e == 0:
                f = 1

            return VerificationEvidence(
                exit_code=test_proc.returncode or 0,
                execution_duration_ms=duration_ms,
                stdout_digest=hashlib.sha256(test_stdout).hexdigest(),
                stderr_digest=hashlib.sha256(test_stderr).hexdigest(),
                tests_passed=p,
                tests_failed=f,
                tests_skipped=s,
                tests_errored=e,
                raw_stdout=stdout_str,
                raw_stderr=stderr_str,
                error_message=None
                if test_proc.returncode == 0
                else f"Tests failed with exit code {test_proc.returncode}",
            )

        finally:
            # 6. Hermetic cleanup: prune worktree or remove directory
            if worktree_created:
                try:
                    clean_proc = await asyncio.create_subprocess_exec(
                        "git",
                        "worktree",
                        "remove",
                        "--force",
                        temp_dir,
                        cwd=str(root),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await clean_proc.communicate()
                except Exception:
                    pass
            shutil.rmtree(temp_dir, ignore_errors=True)
