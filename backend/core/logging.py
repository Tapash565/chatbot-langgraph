"""Logging configuration - re-export from observability for backward compatibility."""
from observability.logging_config import (
    get_logger,
    configure_logging,
    log_span,
    log_context,
    set_thread_id,
    get_correlation_id,
    generate_correlation_id,
)

__all__ = [
    "get_logger",
    "configure_logging",
    "log_span",
    "log_context",
    "set_thread_id",
    "get_correlation_id",
    "generate_correlation_id",
]
