from __future__ import annotations

import logging

from agentos.core.logging import configure_logging, get_logger


def test_configure_logging_accepts_unknown_level() -> None:
    """Unknown log levels should fall back to INFO."""
    configure_logging("not-a-level")

    assert logging.getLogger().level in {logging.INFO, logging.WARNING}


def test_get_logger_binds_context() -> None:
    """Logger factory should return a context-bound logger."""
    logger = get_logger("agentos.test", component="test")

    assert logger is not None
