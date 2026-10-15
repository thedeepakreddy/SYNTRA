"""Security hardening, SSRF defense, credentials protection, and output sanitization for MCP."""

import hashlib
import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urlparse

# Regex patterns for identifying secrets, credentials, and sensitive tokens
SECRET_PATTERNS = [
    # JWT tokens (three base64 segments separated by dots)
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED_JWT_TOKEN]"),
    # Bearer authorization headers
    (re.compile(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{15,}"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Google GenAI / Gemini API keys
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GEMINI_KEY]"),
    # OpenAI API keys
    (re.compile(r"sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"sk-proj-[a-zA-Z0-9_\-]{30,}"), "[REDACTED_OPENAI_KEY]"),
    # Generic password / secret assignments in JSON or query params
    (
        re.compile(r'(?i)("password"|"secret"|"api_key"|"token"|"private_key")\s*:\s*"[^"]+"'),
        r'\1: "[REDACTED_SECRET]"',
    ),
    (
        re.compile(r"(?i)(password|secret|api_key|token|private_key)=([^\s&]+)"),
        r"\1=[REDACTED_SECRET]",
    ),
]

# Injection heuristics for untrusted tool outputs
INJECTION_MARKERS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)system\s+prompt\s+override"),
    re.compile(r"(?i)you\s+are\s+now\s+in\s+unrestricted\s+mode"),
    re.compile(r"(?i)disregard\s+all\s+safety\s+guidelines"),
    re.compile(r"(?i)begin\s+admin\s+execution\s+mode"),
]

# Approved binary executables for stdio MCP processes
APPROVED_STDIO_EXECUTABLES = {
    "uv",
    "python",
    "python3",
    "syntra",
    "node",
    "npx",
    "git",
}

# Forbidden command characters that could trigger shell expansion
FORBIDDEN_SHELL_CHARS = {";", "&", "|", "`", "$", "<", ">"}


class SecurityValidationError(Exception):
    """Raised when an MCP operation violates security policies."""


class SSRFViolationError(SecurityValidationError):
    """Raised when an MCP remote endpoint violates SSRF boundaries."""


class ProcessSecurityError(SecurityValidationError):
    """Raised when an MCP stdio process command violates execution restrictions."""


class MCPSecurityService:
    """Security operations, validation, and scrubbing for MCP transports and tools."""

    @staticmethod
    def compute_schema_hash(schema: dict[str, Any]) -> str:
        """Compute deterministic SHA-256 fingerprint for a tool input JSON schema."""
        canonical_json = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_remote_url(url_str: str) -> str:
        """Validate remote URL for SSRF protection against private, loopback, and metadata addresses."""
        parsed = urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            raise SSRFViolationError(f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are allowed.")

        hostname = parsed.hostname
        if not hostname:
            raise SSRFViolationError("Invalid remote URL: Missing hostname.")

        # Block cloud instance metadata hostnames
        if hostname.lower() in ("metadata.google.internal", "instance-data", "169.254.169.254"):
            raise SSRFViolationError(f"SSRF violation: Hostname '{hostname}' is a reserved metadata endpoint.")

        # Resolve IP and check address safety
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
        except Exception as exc:
            raise SSRFViolationError(f"Failed to resolve hostname '{hostname}': {exc}") from exc

        # Block loopback, private, link-local, multicast, reserved addresses
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or str(ip).startswith("169.254.")
        ):
            raise SSRFViolationError(f"SSRF violation: Target IP '{ip}' is in a private, loopback, or reserved range.")

        return url_str

    @staticmethod
    def validate_stdio_command(command: str, args: list[str]) -> None:
        """Verify that a stdio command is in the approved executable allowlist without shell injection."""
        base_cmd = command.strip().split("/")[-1].split("\\")[-1]
        if base_cmd not in APPROVED_STDIO_EXECUTABLES:
            raise ProcessSecurityError(
                f"Command '{base_cmd}' is not in the approved MCP stdio executables allowlist: "
                f"{sorted(APPROVED_STDIO_EXECUTABLES)}"
            )

        # Check command and arguments for illegal shell metacharacters
        for item in [command] + args:
            for char in FORBIDDEN_SHELL_CHARS:
                if char in item:
                    raise ProcessSecurityError(f"Command element '{item}' contains forbidden shell character '{char}'.")

    @classmethod
    def redact_sensitive_data(cls, value: Any) -> Any:
        """Recursively redact secrets, credentials, and API keys from text, dicts, and lists."""
        if isinstance(value, str):
            scrubbed = value
            for pattern, replacement in SECRET_PATTERNS:
                scrubbed = pattern.sub(replacement, scrubbed)
            return scrubbed

        if isinstance(value, dict):
            new_dict = {}
            for k, v in value.items():
                if any(sec in k.lower() for sec in ("password", "secret", "token", "key", "auth")):
                    new_dict[k] = "[REDACTED_SECRET]"
                else:
                    new_dict[k] = cls.redact_sensitive_data(v)
            return new_dict

        if isinstance(value, list):
            return [cls.redact_sensitive_data(item) for item in value]

        return value

    @classmethod
    def sanitize_untrusted_output(cls, raw_output: str, max_chars: int = 1_000_000) -> tuple[str, bool]:
        """Scrub sensitive data, cap excessive length, and flag injection markers in untrusted tool outputs.

        Returns: (sanitized_text, injection_detected)
        """
        if len(raw_output) > max_chars:
            raw_output = raw_output[:max_chars] + f"\n... [TRUNCATED: Exceeded {max_chars} character limit]"

        scrubbed = cls.redact_sensitive_data(raw_output)
        assert isinstance(scrubbed, str)

        injection_detected = False
        for marker in INJECTION_MARKERS:
            if marker.search(scrubbed):
                injection_detected = True
                break

        return scrubbed, injection_detected
