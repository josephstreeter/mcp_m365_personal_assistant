"""Structured logging helpers with correlation IDs."""

from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4


_correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Return current correlation ID from context."""
    return _correlation_id_var.get()


def set_correlation_id(value: str | None = None) -> str:
    """Set and return a correlation ID for the current context."""
    correlation_id = value or str(uuid4())
    _correlation_id_var.set(correlation_id)
    return correlation_id


def clear_correlation_id() -> None:
    """Clear correlation ID from the current context."""
    _correlation_id_var.set(None)


class CorrelationIdFilter(logging.Filter):
    """Inject correlation ID into each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = get_correlation_id()
        if correlation_id is None:
            correlation_id = set_correlation_id()
        record.correlation_id = correlation_id
        return True


class JsonFormatter(logging.Formatter):
    """Render logs as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
        }

        event_name = getattr(record, "event_name", None)
        if event_name:
            payload["event"] = event_name

        fields = getattr(record, "fields", None)
        if isinstance(fields, dict) and fields:
            payload["fields"] = fields

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_structured_logging(level: int = logging.INFO) -> None:
    """Configure root logger for structured JSON output."""
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())

    root.handlers.clear()
    root.addHandler(handler)


def log_event(
    logger: logging.Logger,
    level: int,
    event_name: str,
    message: str,
    **fields: object,
) -> None:
    """Emit a structured log event with optional fields."""
    logger.log(level, message, extra={"event_name": event_name, "fields": fields})
