"""Mandatory secret redaction and credential sanitization service.

Enforces fail-closed sanitization for sensitive API keys, bearer tokens,
cryptographic private keys, passwords, and high-entropy secrets before persistence.
"""

from __future__ import annotations

import json
import logging
import math
import re
import traceback
from collections.abc import Mapping
from typing import Any

from opentelemetry.sdk.trace import SpanProcessor

from syntra.domain.exceptions import SecretRedactionError

# Substrings for environment variables that must be scrubbed before passing to processes
SENSITIVE_ENV_SUBSTRINGS = (
    "GEMINI",
    "API_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET",
    "TOKEN",
    "PASSWORD",
)

# OpenTelemetry span attribute keys that must be redacted
SPAN_REDACTED_KEY_SUBSTRINGS = (
    "password",
    "key",
    "token",
    "secret",
    "credential",
    "authorization",
    "api_key",
)

# Standard patterns for credential recognition
API_KEY_PATTERNS = [
    # Google API Key
    (re.compile(r"AIza[0-9A-Za-z-_]{20,}"), "[REDACTED_API_KEY]"),
    # OpenAI & Anthropic secret tokens
    (re.compile(r"sk-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_API_TOKEN]"),
    # GitHub Personal Access Token
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"github_pat_[a-zA-Z0-9_]{30,}"), "[REDACTED_GITHUB_TOKEN]"),
    # JWT Tokens (three base64 segments separated by dots)
    (re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED_JWT_TOKEN]"),
    # Bearer Tokens
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]{15,}"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Cryptographic Private Keys
    (
        re.compile(
            r"-----BEGIN\s+(?:[A-Z0-9 ]+\s+)?PRIVATE\s+KEY-----[\s\S]*?-----END\s+(?:[A-Z0-9 ]+\s+)?PRIVATE\s+KEY-----",
            re.MULTILINE,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # Common Key-Value credential assignments in JSON, YAML, or prose
    (
        re.compile(
            r'(?i)(["\']?(?:password|secret|api_key|token|auth_token|access_token|private_key)["\']?)\s*(?:[:=]|\bis\b)\s*(["\'])([^"\']+)(\2)'
        ),
        r"\1: \2[REDACTED_CREDENTIAL]\2",
    ),
    (
        re.compile(
            r"(?i)\b(password|secret|api_key|token|auth_token|access_token|private_key)\s*(?:[:=]|\bis\b)\s*([A-Za-z0-9_\-\.\!\@\#\$\%\^\&\*]{8,})"
        ),
        r"\1: [REDACTED_CREDENTIAL]",
    ),
]

# Sensitive keys in JSON/dict structures
SENSITIVE_KEY_NAMES = frozenset(
    {"password", "secret", "token", "key", "auth", "private_key", "credential", "api_key", "access_token"}
)

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
HEX_PATTERN = re.compile(r"^[0-9a-fA-F]+$")


def calculate_shannon_entropy(data: str) -> float:
    """Calculate the Shannon entropy of a string."""
    if not data:
        return 0.0
    probabilities = [float(data.count(c)) / len(data) for c in set(data)]
    return -sum(p * math.log2(p) for p in probabilities)


class SecretRedactor:
    """Sanitizes text and structured payloads to prevent credential leakage.

    Fails closed: if any error occurs during redaction or input is invalid,
    it raises SecretRedactionError rather than allowing uninspected data through.
    """

    @classmethod
    def redact(cls, text: str) -> str:
        """Sanitize all credentials, keys, and high-entropy tokens from text.

        Raises:
            SecretRedactionError: If input is not a string, or if sanitization fails.
        """
        if not isinstance(text, str):
            raise SecretRedactionError(f"SecretRedactor expected str input, received {type(text).__name__}.")

        if not text:
            return ""

        try:
            sanitized = text

            # 1. Apply canonical regex patterns
            for pattern, replacement in API_KEY_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)

            # 2. Check for high-entropy standalone tokens (potential raw secrets)
            words = re.findall(r"[A-Za-z0-9_\-\.]{20,}", sanitized)
            for word in words:
                # Skip already redacted tokens or UUIDs
                if word.startswith("[REDACTED_") or UUID_PATTERN.match(word):
                    continue
                entropy = calculate_shannon_entropy(word)
                is_hex = bool(HEX_PATTERN.match(word))
                # Pure hex tokens have max theoretical entropy of 4.0 (log2(16))
                if is_hex and len(word) >= 24 and entropy >= 3.0:
                    sanitized = sanitized.replace(word, "[REDACTED_HIGH_ENTROPY_SECRET]")
                elif not is_hex and len(word) >= 20 and entropy >= 3.8:
                    sanitized = sanitized.replace(word, "[REDACTED_HIGH_ENTROPY_SECRET]")

            # 3. Fail-closed post-check: verify no raw private keys escaped
            if "-----BEGIN" in sanitized and "PRIVATE KEY" in sanitized:
                raise SecretRedactionError("Private key structure detected after redaction pass.")

            return sanitized

        except SecretRedactionError:
            raise
        except Exception as exc:
            raise SecretRedactionError(f"Secret redaction failed closed: {exc}") from exc

    @classmethod
    def redact_sensitive_data(cls, value: Any) -> Any:
        """Recursively redact secrets from dictionaries, lists, and strings."""
        try:
            if isinstance(value, str):
                return cls.redact(value)

            if isinstance(value, dict):
                redacted_dict: dict[str, Any] = {}
                for k, v in value.items():
                    key_lower = str(k).lower()
                    if isinstance(v, (dict, list)):
                        redacted_dict[k] = cls.redact_sensitive_data(v)
                    elif any(s in key_lower for s in SENSITIVE_KEY_NAMES):
                        redacted_dict[k] = "[REDACTED_SECRET]"
                    else:
                        redacted_dict[k] = cls.redact_sensitive_data(v)
                return redacted_dict

            if isinstance(value, list):
                return [cls.redact_sensitive_data(item) for item in value]

            return value
        except SecretRedactionError:
            raise
        except Exception as exc:
            raise SecretRedactionError(f"Recursive secret redaction failed closed: {exc}") from exc

    @classmethod
    def redact_deep_json_or_text(cls, text: str) -> str:
        """Deeply sanitize text, inspecting and redacting JSON payloads recursively."""
        if not isinstance(text, str) or not text.strip():
            return text if isinstance(text, str) else ""

        stripped = text.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            try:
                parsed = json.loads(stripped)
                sanitized_data = cls.redact_sensitive_data(parsed)
                return json.dumps(sanitized_data)
            except Exception:
                # If parsing fails or invalid JSON, fall back to standard text redaction
                pass

        return cls.redact(text)

    @classmethod
    def is_sensitive_env_key(cls, key: str) -> bool:
        """Check whether an environment variable name matches sensitive credential patterns."""
        upper = key.upper()
        return any(sub in upper for sub in SENSITIVE_ENV_SUBSTRINGS)

    @classmethod
    def scrub_env(cls, env: Mapping[str, str]) -> dict[str, str]:
        """Strip all sensitive credential environment variables."""
        return {k: v for k, v in env.items() if not cls.is_sensitive_env_key(k)}

    @classmethod
    def mask_env_for_logs(cls, env: Mapping[str, str]) -> dict[str, str]:
        """Produce a safe representation of environment variables replacing secrets with [SCRUBBED]."""
        return {k: ("[SCRUBBED]" if cls.is_sensitive_env_key(k) else v) for k, v in env.items()}


class SecretScrubbingLogFilter(logging.Filter):
    """Logging filter enforcing fail-closed secret redaction across all logger outputs."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.redaction_failures: int = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize message, args, and exception tracebacks on the log record."""
        try:
            # 1. Sanitize msg
            if isinstance(record.msg, str):
                record.msg = SecretRedactor.redact_deep_json_or_text(record.msg)
            elif isinstance(record.msg, (dict, list)):
                record.msg = SecretRedactor.redact_sensitive_data(record.msg)
            elif record.msg is not None:
                record.msg = SecretRedactor.redact(str(record.msg))

            # 2. Sanitize args
            if record.args:
                if isinstance(record.args, tuple):
                    record.args = tuple(
                        SecretRedactor.redact_sensitive_data(arg)
                        if isinstance(arg, (dict, list))
                        else (SecretRedactor.redact_deep_json_or_text(str(arg)) if isinstance(arg, str) else arg)
                        for arg in record.args
                    )
                elif isinstance(record.args, dict):
                    record.args = SecretRedactor.redact_sensitive_data(record.args)

            # 3. Sanitize exc_text and exc_info
            if record.exc_text:
                record.exc_text = SecretRedactor.redact(record.exc_text)

            if record.exc_info:
                try:
                    formatted_tb = "".join(traceback.format_exception(*record.exc_info))
                    record.exc_text = SecretRedactor.redact(formatted_tb)
                except Exception:
                    record.exc_text = "[REDACTED_EXCEPTION_TRACEBACK]"

            return True

        except Exception:
            # Fail closed: never propagate the unscrubbed string
            self.redaction_failures += 1
            record.msg = "[REDACTION_FAILURE] Log message sanitization failed closed"
            record.args = ()
            record.exc_info = None
            record.exc_text = "[REDACTION_FAILURE] Traceback suppressed for security"
            return True


class SecretScrubbingSpanProcessor(SpanProcessor):
    """OpenTelemetry SpanProcessor protocol sanitizing span attributes on completion."""

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        pass

    def _on_ending(self, span: Any) -> None:
        pass

    def on_end(self, span: Any) -> None:
        """Intercept and sanitize all attributes on span completion."""
        target_dict: dict[Any, Any] | None = None
        try:
            if hasattr(span, "attributes") and isinstance(span.attributes, dict):
                target_dict = span.attributes
            elif hasattr(span, "_attributes"):
                raw_attrs = getattr(span, "_attributes")
                if isinstance(raw_attrs, dict):
                    target_dict = raw_attrs
                elif hasattr(raw_attrs, "_dict") and isinstance(raw_attrs._dict, dict):
                    target_dict = raw_attrs._dict

            if target_dict is not None:
                for k in list(target_dict.keys()):
                    k_str = str(k).lower()
                    if any(sub in k_str for sub in SPAN_REDACTED_KEY_SUBSTRINGS):
                        target_dict[k] = "[REDACTED_SPAN_ATTR]"
                    elif isinstance(target_dict[k], str):
                        target_dict[k] = SecretRedactor.redact(target_dict[k])
                    elif isinstance(target_dict[k], (dict, list)):
                        target_dict[k] = SecretRedactor.redact_sensitive_data(target_dict[k])
        except Exception:
            # Fail closed for span attributes
            if target_dict is not None:
                for k in list(target_dict.keys()):
                    target_dict[k] = "[REDACTED_SPAN_ATTR]"

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int | None = None) -> bool:
        return True


def redact_secrets(text: str) -> str:
    """Convenience functional interface for SecretRedactor.redact."""
    return SecretRedactor.redact(text)
