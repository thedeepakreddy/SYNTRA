"""Structured logging setup for SYNTRA using structlog and standard logging."""

import contextvars
import logging
import sys
import uuid

import structlog
from rich.console import Console
from rich.logging import RichHandler

from syntra.core.redactor import SecretRedactor, SecretScrubbingLogFilter

_initialized = False
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retrieve current correlation ID or generate a new UUIDv4."""
    cid = correlation_id_ctx.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id_ctx.set(cid)
    return cid


def _add_correlation_id(_logger, _method_name, event_dict):
    """Processor to inject correlation_id into all structlog events."""
    cid = correlation_id_ctx.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def _scrub_structlog_processor(_logger, _method_name, event_dict):
    """Processor to scrub secrets from structlog event dictionaries."""
    return SecretRedactor.redact_sensitive_data(event_dict)


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure root, standard, and structlog loggers with systemic secret scrubbing."""
    global _initialized
    if _initialized:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # 1. Configure standard root logger with fail-closed secret scrubbing filter
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    scrubber_filter = SecretScrubbingLogFilter()
    root_logger.addFilter(scrubber_filter)

    if json_format:
        stream_handler: logging.Handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
        )
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(scrubber_filter)
        root_logger.addHandler(stream_handler)
    else:
        console = Console(stderr=True)
        rich_handler: logging.Handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        rich_handler.setLevel(numeric_level)
        rich_handler.addFilter(scrubber_filter)
        root_logger.addHandler(rich_handler)

    # 2. Configure structlog with secret scrubbing processor
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _add_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _scrub_structlog_processor,
            structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Quiet external noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _initialized = True
