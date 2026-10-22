from __future__ import annotations

import logging
from typing import cast

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure structured logging for applications and framework modules."""
    logging.basicConfig(level=level.upper(), format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(_logging_level(level)),
        cache_logger_on_first_use=True,
    )


def _logging_level(level: str) -> int:
    """Convert a logging level name to its numeric value."""
    return logging.getLevelNamesMapping().get(level.upper(), logging.INFO)


def get_logger(name: str, **context: object) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound to the provided context."""
    return cast("structlog.stdlib.BoundLogger", structlog.get_logger(name).bind(**context))
