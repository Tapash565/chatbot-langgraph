"""
Structured Logging Configuration for LangGraph Chatbot

Provides:
- JSON structured logging with correlation IDs
- Thread/context isolation for multi-threaded conversations
- Context propagation across LangGraph nodes
- Standardized log levels and formatting
"""

import logging
import sys
import json
import uuid
import contextvars
from datetime import datetime, timezone
from typing import Any, Optional
from contextlib import contextmanager

# Context variable for correlation ID (thread-safe)
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_thread_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "thread_id", default=None
)
_span_name_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_name", default=None
)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return f"corr-{uuid.uuid4().hex[:12]}"


def get_correlation_id() -> str:
    """Get current correlation ID or generate new one."""
    cid = _correlation_id_var.get()
    if not cid:
        cid = generate_correlation_id()
        _correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    _correlation_id_var.set(correlation_id)


def get_thread_id() -> Optional[str]:
    """Get current thread ID from context."""
    return _thread_id_var.get()


def set_thread_id(thread_id: str) -> None:
    """Set thread ID for current context."""
    _thread_id_var.set(thread_id)


def get_span_name() -> Optional[str]:
    """Get current span name from context."""
    return _span_name_var.get()


def set_span_name(span_name: str) -> None:
    """Set span name for current context."""
    _span_name_var.set(span_name)


@contextmanager
def log_context(**kwargs):
    """
    Context manager to add additional context to logs within a block.

    Usage:
        with log_context(user_id="123", action="upload"):
            logger.info("User uploaded file")
    """
    # Store previous values
    previous_correlation = _correlation_id_var.get()
    previous_thread = _thread_id_var.get()
    previous_span = _span_name_var.get()

    # Set new context values if provided
    if "correlation_id" in kwargs:
        _correlation_id_var.set(kwargs["correlation_id"])
    if "thread_id" in kwargs:
        _thread_id_var.set(kwargs["thread_id"])
    if "span_name" in kwargs:
        _span_name_var.set(kwargs["span_name"])

    try:
        yield
    finally:
        # Restore previous values
        _correlation_id_var.set(previous_correlation)
        _thread_id_var.set(previous_thread)
        _span_name_var.set(previous_span)


@contextmanager
def log_span(span_name: str, **attributes):
    """
    Context manager to track a span/operation with timing.

    Usage:
        with log_span("pdf_ingestion", filename="doc.pdf"):
            # perform operation
            pass
    """
    import time

    _span_name_var.set(span_name)
    start_time = time.perf_counter()

    logger = get_logger(__name__)
    logger.debug(
        "span_start",
        span_name=span_name,
        **attributes
    )

    try:
        yield
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "span_error",
            span_name=span_name,
            duration_ms=round(duration_ms, 2),
            error_type=type(e).__name__,
            error_message=str(e),
            **attributes
        )
        raise
    else:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            "span_end",
            span_name=span_name,
            duration_ms=round(duration_ms, 2),
            **attributes
        )


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs log records as JSON with standardized fields:
    - timestamp: ISO 8601 format
    - level: log level (DEBUG, INFO, WARNING, ERROR)
    - correlation_id: request tracing ID
    - thread_id: conversation thread ID
    - span_name: current operation span
    - logger: source logger name
    - message: log message
    - extras: additional context
    """

    def format(self, record: logging.LogRecord) -> str:
        # Build base log structure
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation context
        correlation_id = _correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        thread_id = _thread_id_var.get()
        if thread_id:
            log_data["thread_id"] = thread_id

        span_name = _span_name_var.get()
        if span_name:
            log_data["span_name"] = span_name

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields (from log_context, log_span, etc.)
        if hasattr(record, "extra_fields"):
            log_data["extras"] = record.extra_fields

        # Add any other standard attributes
        for key in ["duration_ms", "error_type", "model", "tool_name", "operation"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data, default=str)


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Custom logger adapter that automatically includes context.

    Usage:
        logger = get_logger("my.component")
        logger.info("message", extra_field="value")
    """

    def process(self, msg: str, kwargs: dict) -> tuple:
        # Collect extra fields from kwargs
        extra_fields = {}

        # Extract known fields
        for key in ["duration_ms", "error_type", "model", "tool_name",
                    "operation", "filename", "documents", "chunks"]:
            if key in kwargs:
                extra_fields[key] = kwargs.pop(key)

        # Extract any additional kwargs
        for k, v in list(kwargs.items()):
            if k not in ["extra", "exc_info", "stack_info", "stacklevel"]:
                extra_fields[k] = v
                kwargs.pop(k, None)

        if extra_fields:
            kwargs["extra"] = {**kwargs.get("extra", {}), "extra_fields": extra_fields}

        return msg, kwargs


def get_logger(name: str) -> StructuredLoggerAdapter:
    """
    Get a structured logger instance.

    Usage:
        logger = get_logger(__name__)
        logger.info("Chat request received", thread_id="abc123")
    """
    logger = logging.getLogger(name)

    # Ensure the logger has our adapter
    if not isinstance(logger, StructuredLoggerAdapter):
        logger = StructuredLoggerAdapter(logger, {})

    return logger


def configure_logging(
    level: str = "INFO",
    json_format: bool = True,
    handlers: Optional[list] = None
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Whether to use JSON structured format
        handlers: Optional list of custom handlers
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    if handlers:
        for handler in handlers:
            root_logger.addHandler(handler)
    else:
        # Default: console output
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))

        if json_format:
            handler.setFormatter(StructuredFormatter())
        else:
            # Human-readable format
            handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | "
                "%(correlation_id)s | %(message)s"
            ))

        root_logger.addHandler(handler)

    # Set levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("faiss").setLevel(logging.WARNING)


# Initialize logging on module import
configure_logging(level="INFO", json_format=True)
