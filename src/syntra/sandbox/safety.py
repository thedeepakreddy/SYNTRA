"""Command safety analysis, blacklisting, and sanitization for sandbox execution."""

import os
import re
from collections.abc import Mapping
from pathlib import Path

from syntra.core.exceptions import SandboxSecurityViolationError

# Dangerous commands and command fragments that could compromise host system
DANGEROUS_PATTERNS = [
    r"\brm\s+-[a-zA-Z]*[rfRF]+[a-zA-Z]*\s+/(?:\s|$|[a-zA-Z0-9_\-\.\*]+)",  # rm -rf / or /etc etc
    r"\bmkfs\b",  # format disk
    r"\bfdisk\b",  # partition disk
    r"\bdd\s+if=",  # direct disk overwrite
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # fork bomb
    r"\bshutdown\b",  # system shutdown
    r"\breboot\b",  # system reboot
    r"\bhalt\b",  # system halt
    r"\binit\s+0\b",  # system halt
    r">\s*/dev/sd[a-z]",  # raw device write
    r">\s*/dev/nvme",  # raw device write
    r"\bchmod\s+-[R\s]*777\s+/(?:\s|$|[a-zA-Z0-9_\-\.\*]+)",  # permission compromise
]

# Sensitive environment variables to redact from sandbox process environment
SENSITIVE_ENV_VARS = frozenset(
    {
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GITHUB_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SSH_PRIVATE_KEY",
    }
)

# Mandatory substring matches for credential environment variables (uppercase check)
SCRUBBED_ENV_SUBSTRINGS = (
    "GEMINI",
    "API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET",
    "TOKEN",
    "PASSWORD",
)


def is_sensitive_env_key(key: str) -> bool:
    """Determine whether an environment variable name contains sensitive credential substrings."""
    upper = key.upper()
    return upper in SENSITIVE_ENV_VARS or any(sub in upper for sub in SCRUBBED_ENV_SUBSTRINGS)


def validate_safe_path(base_dir: str | Path, target_path: str | Path) -> Path:
    """Validate that target_path strictly resides within base_dir.

    Resolves symlinks using os.path.realpath() before checking containment to
    prevent symlink directory traversal / breakout attacks.

    Raises:
        SandboxSecurityViolationError: If target_path resolves outside base_dir.
    """
    base_real = os.path.realpath(str(base_dir))
    if os.path.isabs(str(target_path)):
        target_real = os.path.realpath(str(target_path))
    else:
        target_real = os.path.realpath(os.path.join(base_real, str(target_path)))

    common = os.path.commonpath([base_real, target_real])
    if common != base_real:
        raise SandboxSecurityViolationError(
            f"Path traversal or symlink escape detected: '{target_path}' resolves to '{target_real}', "
            f"which escapes workspace root '{base_real}'."
        )
    return Path(target_real)


class CommandSafetyValidator:
    """Validates commands before executing them in the sandbox worker."""

    @classmethod
    def validate_command(cls, command: str) -> None:
        """Inspect command string for dangerous patterns."""
        cmd_clean = command.strip()
        if not cmd_clean:
            raise SandboxSecurityViolationError("Cannot execute empty command")

        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                raise SandboxSecurityViolationError(
                    f"Command rejected by security policy: matches dangerous pattern '{pattern}'"
                )

    validate_safe_path = staticmethod(validate_safe_path)

    @classmethod
    def sanitize_env(cls, env: Mapping[str, str] | None = None) -> dict[str, str]:
        """Produce sanitized environment dictionary free of sensitive tokens."""
        base_env = dict(env if env is not None else os.environ)
        sanitized: dict[str, str] = {}
        for k, v in base_env.items():
            if is_sensitive_env_key(k):
                continue
            sanitized[k] = v
        return sanitized

    @classmethod
    def mask_env_for_logs(cls, env: Mapping[str, str]) -> dict[str, str]:
        """Produce log-safe environment dictionary replacing sensitive values with [SCRUBBED]."""
        return {k: ("[SCRUBBED]" if is_sensitive_env_key(k) else v) for k, v in env.items()}


# Module-level aliases
sanitize_env = CommandSafetyValidator.sanitize_env
mask_env_for_logs = CommandSafetyValidator.mask_env_for_logs
