"""Structured logging for flight domain operations."""

import time
import uuid
from typing import Any

from app.core.logging import get_flights_logger

logger = get_flights_logger()


class FlightLogger:
    """Structured logger for flight operations with correlation tracking.

    Provides consistent logging format across all flight operations:
    - Request correlation (request_id)
    - Performance metrics (duration_ms)
    - Structured context (environment, user_id, route, etc.)

    Example:
        log = FlightLogger(
            "SEARCH",
            environment="TEST",
            user_id="123",
            route="AMS→CDG"
        )
        log.started("route=AMS→CDG")
        # ... operation ...
        log.success("results=15", results=15)
    """

    def __init__(self, operation: str, **base_context) -> None:
        """Initialize flight logger.

        Args:
            operation: Operation name (SEARCH, BOOK, CANCEL, etc.)
            **base_context: Base context included in all logs (env, user_id, route, etc.)
        """
        self.operation = operation
        self.request_id = str(uuid.uuid4())[:8]
        self.base_context = base_context
        self.start_time = time.time()

    def _build_extra(self, **additional) -> dict[str, Any]:
        """Build structured logging context."""
        return {
            "operation": self.operation,
            "request_id": self.request_id,
            **self.base_context,
            **additional,
        }

    def _format_context(self) -> str:
        """Format ALL base_context fields for console display.

        Prints all context that's stored in structured logs for complete visibility.

        Returns:
            Formatted context string like "route=AMS→JFK journey=OneWay user_id=123 environment=TEST"
        """
        if not self.base_context:
            return ""

        parts = []

        for key, value in self.base_context.items():
            if value is None:
                continue

            # Handle nested dicts (e.g., passengers)
            if isinstance(value, dict):
                # Format passenger dict as "2A/1C/0I"
                if key == "passengers":
                    pax = f"{value.get('adults', 0)}A/{value.get('children', 0)}C/{value.get('infants', 0)}I"
                    parts.append(f"pax={pax}")
                else:
                    # Other dicts: flatten key-value pairs
                    for nested_key, nested_value in value.items():
                        parts.append(f"{key}.{nested_key}={nested_value}")
                continue

            parts.append(f"{key}={value}")

        return " ".join(parts)

    def started(self, msg: str = "", **ctx):
        """Log operation start with optional context.

        Args:
            msg: Additional message to include in log
            **ctx: Additional context fields
        """
        context_str = self._format_context()
        message_parts = [self.operation, "Started", self.request_id]
        if context_str:
            message_parts.append(context_str)
        if msg:
            message_parts.append(msg)

        logger.info(
            " | ".join(message_parts), extra=self._build_extra(status="Started", **ctx)
        )

    def success(self, msg: str = "", **metrics):
        """Log successful completion with timing and metrics.

        Args:
            msg: Additional message to include in log
            **metrics: Metrics to include (results, count, etc.)
        """
        duration_ms = int((time.time() - self.start_time) * 1000)
        context_str = self._format_context()
        message_parts = [self.operation, "Success", self.request_id]
        if context_str:
            message_parts.append(context_str)
        if msg:
            message_parts.append(msg)

        # Add metrics to message (e.g., results=50)
        if metrics:
            metrics_str = " ".join(f"{k}={v}" for k, v in metrics.items())
            message_parts.append(metrics_str)

        message_parts.append(f"{duration_ms}ms")

        logger.info(
            " | ".join(message_parts),
            extra=self._build_extra(
                status="Success", duration_ms=duration_ms, **metrics
            ),
        )

    def error(self, msg: str, exc: Exception | None = None, **ctx):
        """Log error with exception details and timing.

        Args:
            msg: Error message
            exc: Exception instance (optional)
            **ctx: Additional context fields
        """
        duration_ms = int((time.time() - self.start_time) * 1000)
        context_str = self._format_context()
        message_parts = [self.operation, "Failed", self.request_id]
        if context_str:
            message_parts.append(context_str)
        message_parts.append(msg)

        extra = self._build_extra(
            status="Failed",
            duration_ms=duration_ms,
            error_type=type(exc).__name__ if exc else "Unknown",
            error_message=str(exc) if exc else msg,
            **ctx,
        )
        logger.error(" | ".join(message_parts), extra=extra, exc_info=True)

    def warning(self, msg: str, **ctx):
        """Log warning with context and error details.

        Args:
            msg: Warning message
            **ctx: Additional context fields (including error_message)
        """
        context_str = self._format_context()
        message_parts = [self.operation, "Warning", self.request_id]
        if context_str:
            message_parts.append(context_str)
        message_parts.append(msg)

        # Include error_message in the displayed message if available
        if ctx.get("error_message"):
            message_parts.append(f"error: {ctx['error_message']}")

        logger.warning(
            " | ".join(message_parts), extra=self._build_extra(status="Warning", **ctx)
        )

    def info(self, msg: str, **ctx):
        """Log informational message with context.

        Args:
            msg: Informational message
            **ctx: Additional context fields
        """
        context_str = self._format_context()
        message_parts = [self.operation, "Info", self.request_id]
        if context_str:
            message_parts.append(context_str)
        message_parts.append(msg)

        logger.info(
            " | ".join(message_parts), extra=self._build_extra(status="Info", **ctx)
        )
