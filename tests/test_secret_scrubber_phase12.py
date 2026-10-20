"""Unit and adversarial tests for Systemic Secret Scrubber and Security Boundary Hardening (Milestone 12.2)."""

import json
import logging
from pathlib import Path

import pytest

from syntra.api.errors import create_problem_response
from syntra.cli.ui import render_error
from syntra.core.exceptions import SandboxSecurityViolationError
from syntra.core.redactor import (
    SecretRedactor,
    SecretScrubbingLogFilter,
    SecretScrubbingSpanProcessor,
)
from syntra.sandbox.safety import CommandSafetyValidator, validate_safe_path
from syntra.sandbox.workspace import WorkspaceManager


# ==============================================================================
# 1. Logging Filter Tests (Message Strings and Exception Tracebacks)
# ==============================================================================
def test_log_handler_message_scrubbing() -> None:
    """SecretScrubbingLogFilter scrubs credentials and high-entropy secrets from log records."""
    log_filter = SecretScrubbingLogFilter()

    # Create dummy LogRecord
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Authenticated user with API key AIzaSyD-12345678901234567890 and token sk-abcdef12345678901234567890",
        args=(),
        exc_info=None,
    )

    allowed = log_filter.filter(record)
    assert allowed is True
    assert "AIzaSyD-" not in str(record.msg)
    assert "[REDACTED_API_KEY]" in str(record.msg)
    assert "sk-" not in str(record.msg)
    assert "[REDACTED_API_TOKEN]" in str(record.msg)


def test_log_handler_args_scrubbing() -> None:
    """SecretScrubbingLogFilter scrubs credentials passed via record.args."""
    log_filter = SecretScrubbingLogFilter()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="Login failure for user %s with token %s",
        args=("alice", "ghp_123456789012345678901234567890123456"),
        exc_info=None,
    )

    allowed = log_filter.filter(record)
    assert allowed is True
    assert isinstance(record.args, tuple)
    assert record.args[0] == "alice"
    assert record.args[1] == "[REDACTED_GITHUB_TOKEN]"


def test_log_handler_exception_traceback_scrubbing() -> None:
    """SecretScrubbingLogFilter scrubs credentials out of exception tracebacks (exc_info)."""
    log_filter = SecretScrubbingLogFilter()

    try:
        raise ValueError("Database connection failed with password=SuperSecretPassword123!")
    except Exception:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname=__file__,
        lineno=30,
        msg="Unhandled database error",
        args=(),
        exc_info=exc_info,
    )

    allowed = log_filter.filter(record)
    assert allowed is True
    assert record.exc_text is not None
    assert "SuperSecretPassword123!" not in record.exc_text
    assert "[REDACTED_CREDENTIAL]" in record.exc_text


def test_log_filter_fail_closed_on_error() -> None:
    """SecretScrubbingLogFilter fails closed if an error occurs during redaction."""
    log_filter = SecretScrubbingLogFilter()

    class BuggyObject:
        def __str__(self) -> str:
            raise RuntimeError("Fatal error in string conversion")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.CRITICAL,
        pathname=__file__,
        lineno=40,
        msg=BuggyObject(),  # type: ignore[arg-type]
        args=(),
        exc_info=None,
    )

    allowed = log_filter.filter(record)
    assert allowed is True
    assert log_filter.redaction_failures == 1
    assert "[REDACTION_FAILURE]" in str(record.msg)
    assert "failed closed" in str(record.msg)


# ==============================================================================
# 2. OpenTelemetry Span Attribute Scrubber Tests
# ==============================================================================
class MockSpan:
    def __init__(self, attributes: dict[str, object]) -> None:
        self.attributes = attributes


def test_span_processor_scrubs_sensitive_attribute_keys() -> None:
    """SpanProcessor replaces attribute values for keys matching sensitive substrings."""
    processor = SecretScrubbingSpanProcessor()

    attrs = {
        "db.password": "SuperSecretPass",
        "api_key": "AIzaSyD-12345678901234567890",
        "service.auth_token": "token-12345",
        "jwt.secret": "my-secret-key",
        "user.credential": "secret-credential",
        "http.authorization": "Bearer eyJhbGciOi...",
        "http.method": "POST",
        "http.status_code": 200,
        "query.param": "token is sk-abcdef12345678901234567890",
    }
    span = MockSpan(attrs)

    processor.on_end(span)

    # Sensitive keys replaced with [REDACTED_SPAN_ATTR]
    assert span.attributes["db.password"] == "[REDACTED_SPAN_ATTR]"
    assert span.attributes["api_key"] == "[REDACTED_SPAN_ATTR]"
    assert span.attributes["service.auth_token"] == "[REDACTED_SPAN_ATTR]"
    assert span.attributes["jwt.secret"] == "[REDACTED_SPAN_ATTR]"
    assert span.attributes["user.credential"] == "[REDACTED_SPAN_ATTR]"
    assert span.attributes["http.authorization"] == "[REDACTED_SPAN_ATTR]"

    # Non-sensitive keys preserved
    assert span.attributes["http.method"] == "POST"
    assert span.attributes["http.status_code"] == 200

    # Non-matching key with embedded credentials in string value scrubbed
    assert "sk-" not in str(span.attributes["query.param"])
    assert "[REDACTED_API_TOKEN]" in str(span.attributes["query.param"])


# ==============================================================================
# 3. Deep Dict and JSON Scrubbing Tests
# ==============================================================================
def test_deep_json_and_dict_scrubbing() -> None:
    """Recursive scrubbing sanitizes nested JSON strings and dicts."""
    raw_payload = {
        "user": "developer",
        "auth": {
            "password": "Password123!",
            "tokens": ["sk-1111111111111111111111111111", "ghp_222222222222222222222222222222222222"],
        },
        "metadata": {
            "api_key": "secret-api-key",
            "safe_field": "public_data",
        },
    }

    # Dict scrubbing
    sanitized_dict = SecretRedactor.redact_sensitive_data(raw_payload)
    assert sanitized_dict["auth"]["password"] == "[REDACTED_SECRET]"
    assert sanitized_dict["metadata"]["api_key"] == "[REDACTED_SECRET]"
    assert sanitized_dict["metadata"]["safe_field"] == "public_data"
    assert "[REDACTED_API_TOKEN]" in sanitized_dict["auth"]["tokens"][0]
    assert "[REDACTED_GITHUB_TOKEN]" in sanitized_dict["auth"]["tokens"][1]

    # JSON string scrubbing
    json_str = json.dumps(raw_payload)
    sanitized_json = SecretRedactor.redact_deep_json_or_text(json_str)
    parsed = json.loads(sanitized_json)
    assert parsed["auth"]["password"] == "[REDACTED_SECRET]"
    assert parsed["metadata"]["api_key"] == "[REDACTED_SECRET]"


# ==============================================================================
# 4. Sandbox Environment Variable Scrubbing Tests
# ==============================================================================
def test_subprocess_env_scrubbing() -> None:
    """CommandSafetyValidator.sanitize_env strips credential variables and masks logs."""
    test_env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": "/workspace/src",
        "GEMINI_API_KEY": "AIzaSyD-12345678901234567890",
        "MY_API_KEY": "sk-12345",
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/syntra",
        "REDIS_URL": "redis://:pass@localhost:6379",
        "APP_SECRET": "jwt-signing-secret",
        "AUTH_TOKEN": "bearer-token-123",
        "POSTGRES_PASSWORD": "supersecretpassword",
        "SAFE_SETTING": "enabled",
    }

    # Stripped environment
    clean_env = CommandSafetyValidator.sanitize_env(test_env)
    assert "PATH" in clean_env
    assert "PYTHONPATH" in clean_env
    assert "SAFE_SETTING" in clean_env

    assert "GEMINI_API_KEY" not in clean_env
    assert "MY_API_KEY" not in clean_env
    assert "DATABASE_URL" not in clean_env
    assert "REDIS_URL" not in clean_env
    assert "APP_SECRET" not in clean_env
    assert "AUTH_TOKEN" not in clean_env
    assert "POSTGRES_PASSWORD" not in clean_env

    # Masked environment for logs
    masked = CommandSafetyValidator.mask_env_for_logs(test_env)
    assert masked["GEMINI_API_KEY"] == "[SCRUBBED]"
    assert masked["DATABASE_URL"] == "[SCRUBBED]"
    assert masked["POSTGRES_PASSWORD"] == "[SCRUBBED]"
    assert masked["SAFE_SETTING"] == "enabled"


# ==============================================================================
# 5. Sandbox Symlink Hardening (Category I Adversarial Matrix)
# ==============================================================================
def test_sandbox_symlink_escape_blocked(tmp_path: Path) -> None:
    """Category I: Symlink pointing outside workspace root is detected and blocked using realpath."""
    workspace_root = tmp_path / "sandbox_workspace"
    workspace_root.mkdir()

    outside_dir = tmp_path / "host_secrets"
    outside_dir.mkdir()
    secret_file = outside_dir / "shadow.txt"
    secret_file.write_text("root:secret_hash\n", encoding="utf-8")

    # Inside workspace, create an adversarial symlink targeting the outside directory
    escape_link = workspace_root / "host_link"
    try:
        escape_link.symlink_to(outside_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not permitted in test environment")

    # 1. Direct path check fails
    with pytest.raises(SandboxSecurityViolationError) as exc_info:
        validate_safe_path(workspace_root, "host_link/shadow.txt")
    assert "Path traversal or symlink escape detected" in str(exc_info.value)

    # 2. WorkspaceManager fails
    wm = WorkspaceManager(workspace_root)
    with pytest.raises(SandboxSecurityViolationError):
        wm.read_file("host_link/shadow.txt")

    # 3. Standard relative path traversal also blocked
    with pytest.raises(SandboxSecurityViolationError):
        validate_safe_path(workspace_root, "../host_secrets/shadow.txt")


# ==============================================================================
# 6. API and CLI Error Handler Sanitization Tests
# ==============================================================================
def test_api_error_response_sanitization() -> None:
    """FastAPI RFC 7807 problem responses scrub credentials from detail and extra."""
    resp = create_problem_response(
        status_code=400,
        title="Invalid credentials supplied",
        detail="Token sk-abcdef12345678901234567890 expired",
        instance="/api/v1/auth",
        extra={"secret_key": "AIzaSyD-12345678901234567890", "diagnostic": "failed"},
    )

    body = json.loads(resp.body.decode("utf-8"))
    assert "sk-" not in body["detail"]
    assert "[REDACTED_API_TOKEN]" in body["detail"]
    assert body["secret_key"] == "[REDACTED_SECRET]"
    assert body["diagnostic"] == "failed"


def test_cli_render_error_sanitization(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI render_error sanitizes credentials before printing to terminal."""
    render_error("Failed to connect with password=MySecretPassword123")
    captured = capsys.readouterr()
    # Console might write to stderr or stdout
    output = captured.out + captured.err
    assert "MySecretPassword123" not in output
    assert "[REDACTED_CREDENTIAL]" in output
