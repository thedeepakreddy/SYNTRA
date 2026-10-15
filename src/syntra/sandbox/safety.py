"""Command safety analysis, blacklisting, and sanitization for sandbox execution."""

import re

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
SENSITIVE_ENV_VARS = {
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "SSH_PRIVATE_KEY",
}


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

    @classmethod
    def sanitize_env(cls, env: dict[str, str] | None = None) -> dict[str, str]:
        """Produce sanitized environment dictionary free of sensitive tokens."""
        import os

        base_env = dict(env if env is not None else os.environ)
        sanitized = {}
        for k, v in base_env.items():
            if k.upper() not in {
                "PATH",
                "LANG",
                "LC_ALL",
                "TZ",
                "TERM",
                "APP_ENV",
                "PYTHONPATH",
                "PYTHONDONTWRITEBYTECODE",
            }:
                continue
            if k.upper() in SENSITIVE_ENV_VARS:
                continue
            sanitized[k] = v
        return sanitized
