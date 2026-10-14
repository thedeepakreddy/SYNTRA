"""Structured logging setup for SYNTRA."""

import logging
import sys
from rich.console import Console
from rich.logging import RichHandler

_initialized = False


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure root and SYNTRA loggers."""
    global _initialized
    if _initialized:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    if json_format:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","name":"%(name)s","level":"%(levelname)s","message":"%(message)s"}'
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        console = Console(stderr=True)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            rich_tracebacks=True,
            markup=True,
        )
        handler.setLevel(numeric_level)
        root_logger.addHandler(handler)

    # Quiet external noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _initialized = True
