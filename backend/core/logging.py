"""Application logging helpers used across the backend.

This module keeps the existing structured logging call style used throughout the
project while removing the old standalone observability package.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from typing import Any, Iterator, Optional

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_thread_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "thread_id", default=None
)
_context_var: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "log_context", default=None
)
_json_logging_enabled = True
_logging_configured = False


def generate_correlation_id() -> str:
    """Generate a correlation ID for request-scoped logging."""
    return f"corr-{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> str:
    """Get or create the correlation ID for the current context."""
    correlation_id = _correlation_id_var.get()
    if not correlation_id:
        correlation_id = generate_correlation_id()
        _correlation_id_var.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    _correlation_id_var.set(correlation_id)


def get_thread_id() -> Optional[str]:
    """Return the active chat thread ID from context."""
    return _thread_id_var.get()


def set_thread_id(thread_id: Optional[str]) -> None:
    """Set the active chat thread ID for the current context."""
    _thread_id_var.set(thread_id)


def _serialize_log_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _serialize_log_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_log_value(item) for item in value]
    return str(value)


def _build_log_payload(event: str, fields: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"event": event, "correlation_id": get_correlation_id()}

    thread_id = get_thread_id()
    if thread_id:
        payload["thread_id"] = thread_id

    context_fields = _context_var.get() or {}
    if context_fields:
        payload.update({key: _serialize_log_value(value) for key, value in context_fields.items()})

    payload.update({key: _serialize_log_value(value) for key, value in fields.items()})
    return payload


class CompatibleLogger:
    """Small wrapper that preserves logger.info(event, key=value) semantics."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, level: int, event: str, **fields: Any) -> None:
        payload = _build_log_payload(event, fields)
        if _json_logging_enabled:
            message = json.dumps(payload, default=str)
        else:
            event_name = payload.pop("event")
            field_text = " ".join(f"{key}={value}" for key, value in payload.items())
            message = event_name if not field_text else f"{event_name} {field_text}"
        self._logger.log(level, message)

    def debug(self, event: str, **fields: Any) -> None:
        self._log(logging.DEBUG, event, **fields)

    def info(self, event: str, **fields: Any) -> None:
        self._log(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._log(logging.WARNING, event, **fields)

    def warn(self, event: str, **fields: Any) -> None:
        self.warning(event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._log(logging.ERROR, event, **fields)

    def exception(self, event: str, **fields: Any) -> None:
        payload = _build_log_payload(event, fields)
        message = json.dumps(payload, default=str) if _json_logging_enabled else event
        self._logger.exception(message)


def get_logger(name: str) -> CompatibleLogger:
    """Return a project logger that accepts structured keyword fields."""
    return CompatibleLogger(logging.getLogger(name))


def configure_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configure root logging for the application."""
    global _json_logging_enabled, _logging_configured

    if _logging_configured:
        return

    _logging_configured = True
    _json_logging_enabled = json_format

    log_level = getattr(logging, level.upper(), logging.INFO)
    formatter = logging.Formatter("%(message)s")
    if not json_format:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    for noisy_logger in ("urllib3", "requests", "httpx", "faiss"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


@contextmanager
def log_context(**kwargs: Any) -> Iterator[None]:
    """Temporarily attach fields to all log entries emitted in the block."""
    current = dict(_context_var.get() or {})
    updated = {**current, **kwargs}
    token = _context_var.set(updated)
    try:
        yield
    finally:
        _context_var.reset(token)


@contextmanager
def log_span(span_name: str, **attributes: Any) -> Iterator[None]:
    """Log duration and failures for a scoped operation."""
    started_at = time.perf_counter()
    with log_context(span_name=span_name, **attributes):
        try:
            yield
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            get_logger(__name__).error(
                "span_error",
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            get_logger(__name__).debug("span_complete", duration_ms=duration_ms)


__all__ = [
    "configure_logging",
    "generate_correlation_id",
    "get_correlation_id",
    "get_logger",
    "get_thread_id",
    "log_context",
    "log_span",
    "set_correlation_id",
    "set_thread_id",
]
