"""Logging configuration for the application.

Provides topic-based logging with support for:
- Console output (development)
- CloudWatch integration (AWS ECS production)
- File rotation (persistent logs)
"""

import logging
import logging.handlers
import re
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from app.core.config import settings


# Define log topics/streams
class LogTopic(StrEnum):
    """Available logging topics for stream segregation."""

    BACKEND = "backend"
    AGENTS = "agents"
    AUTH = "auth"
    DATABASE = "database"
    ERRORS = "errors"
    FLIGHTS = "flights"
    HOTELS = "hotels"
    PLACES = "places"


class ImmediateStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes immediately after each log emission."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def _create_console_formatter(
    prefix: str, debug: bool | None = None
) -> logging.Formatter:
    """Create a standardized console log formatter."""
    if debug is None:
        debug = settings.DEBUG

    if debug:
        format_str = f"[{prefix:<8s}] %(levelname)-8s | %(filename)-20s:%(lineno)-4d | %(name)-25s | %(message)s"
    else:
        format_str = (
            f"[{prefix:<8s}] %(filename)-20s:%(lineno)-4d | {settings.LOG_FORMAT}"
        )

    return logging.Formatter(format_str, datefmt=settings.LOG_DATE_FORMAT)


def _create_file_formatter(prefix: str) -> logging.Formatter:
    """Create a standardized file log formatter."""
    return logging.Formatter(
        f"[{prefix}] %(filename)s:%(lineno)d | {settings.LOG_FORMAT}",
        datefmt=settings.LOG_DATE_FORMAT,
    )


def _create_cloudwatch_formatter() -> logging.Formatter:
    """Create a standardized CloudWatch log formatter."""
    return logging.Formatter(
        "%(levelname)-8s | %(filename)s:%(lineno)d | %(name)s | %(message)s",
        datefmt=settings.LOG_DATE_FORMAT,
    )


# Global logger registry
_topic_loggers: dict[str, logging.Logger] = {}
_logging_initialized = False


def setup_logging() -> None:
    """Configure logging for the entire application."""
    global _logging_initialized

    if _logging_initialized:
        return

    # Create logs directory if file logging is enabled
    if settings.LOG_FILE_PATH:
        log_dir = Path(settings.LOG_FILE_PATH).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger with basic console handler only
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT,
        handlers=[],  # Clear default handlers
    )

    # Setup topic loggers
    setup_topic_logger(LogTopic.BACKEND, "/ecs/voya-backend")
    setup_topic_logger(LogTopic.AGENTS, "/ecs/voya-agents")
    setup_topic_logger(LogTopic.AUTH, "/ecs/voya-auth")
    setup_topic_logger(LogTopic.DATABASE, "/ecs/voya-database")
    setup_topic_logger(LogTopic.HOTELS, f"/ecs/{settings.ENVIRONMENT}-voya-hotels")
    setup_topic_logger(LogTopic.ERRORS, "/ecs/voya-errors")
    setup_topic_logger(LogTopic.FLIGHTS, "/ecs/voya-flights")
    setup_topic_logger(LogTopic.PLACES, "/ecs/voya-places")

    # Configure root logger with console handler only
    root_logger = logging.getLogger()
    console_handler = ImmediateStreamHandler(sys.stdout)
    console_handler.setFormatter(_create_console_formatter("APP"))
    root_logger.addHandler(console_handler)

    # Silence noisy libraries
    _configure_library_logging()

    # Mark as initialized
    _logging_initialized = True

    # Log initialization using backend logger specifically
    backend_logger = get_topic_logger(LogTopic.BACKEND)
    backend_logger.info(f"Logging initialized - Level: {settings.LOG_LEVEL}")
    if settings.LOG_FILE_PATH:
        backend_logger.info(f"File logging enabled: {settings.LOG_FILE_PATH}")


def setup_topic_logger(topic: LogTopic, log_group: str) -> logging.Logger:
    """Setup a logger for a specific topic/stream."""
    logger_name = f"{topic.value}_logger"
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    # Clear any existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = ImmediateStreamHandler(sys.stdout)
    console_handler.setFormatter(_create_console_formatter(topic.value.upper()))
    logger.addHandler(console_handler)

    # CloudWatch handler for AWS ECS production
    if _is_running_in_ecs():
        _setup_cloudwatch_handler(logger, topic, log_group)

    # File handler for persistent logging
    if settings.LOG_FILE_PATH:
        _setup_file_handler(logger, topic)

    _topic_loggers[topic.value] = logger
    return logger


def get_topic_logger(topic: LogTopic) -> logging.Logger:
    """Get a logger for a specific topic."""
    logger = _topic_loggers.get(topic.value)
    if not logger:
        # Create logger if not exists
        logger = setup_topic_logger(topic, f"/ecs/voya-{topic.value}")
    return logger


def get_agents_logger() -> logging.Logger:
    """Convenience function to get the agents logger."""
    return get_topic_logger(LogTopic.AGENTS)


def get_backend_logger() -> logging.Logger:
    """Convenience function to get the backend logger."""
    return get_topic_logger(LogTopic.BACKEND)


def get_flights_logger() -> logging.Logger:
    """Convenience function to get the flights logger."""
    return get_topic_logger(LogTopic.FLIGHTS)


def get_hotels_logger() -> logging.Logger:
    """Convenience function to get the hotels logger."""
    return get_topic_logger(LogTopic.HOTELS)


def get_places_logger() -> logging.Logger:
    """Convenience function to get the places logger."""
    return get_topic_logger(LogTopic.PLACES)


def _setup_cloudwatch_handler(
    logger: logging.Logger, topic: LogTopic, log_group: str
) -> None:
    """Setup CloudWatch handler for production logging."""
    try:
        import watchtower

        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group=log_group,
            stream_name=f"{topic.value}-{_get_task_id()}",
            create_log_group=True,
            create_log_stream=True,
        )
        cloudwatch_handler.setFormatter(_create_cloudwatch_formatter())
        logger.addHandler(cloudwatch_handler)
        print(f"CloudWatch logging enabled for {topic.value} -> {log_group}")
    except Exception as e:
        print(f"Failed to setup CloudWatch logging for {topic}: {e}")


def _setup_file_handler(logger: logging.Logger, topic: LogTopic) -> None:
    """Setup file handler for persistent logging."""
    try:
        base_path = Path(cast("str", settings.LOG_FILE_PATH))
        topic_log_path = (
            base_path.parent / f"{base_path.stem}_{topic.value}{base_path.suffix}"
        )
        topic_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Flights logger overwrites on restart for clean dev logs
        if topic == LogTopic.FLIGHTS:
            file_handler = logging.FileHandler(
                filename=topic_log_path,
                mode="w",
                encoding="utf-8",
            )
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=topic_log_path,
                maxBytes=settings.LOG_FILE_MAX_BYTES,
                backupCount=settings.LOG_FILE_BACKUP_COUNT,
                encoding="utf-8",
            )

        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(_create_file_formatter(topic.value.upper()))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging for {topic}: {e}")


def _is_running_in_ecs() -> bool:
    """Check if running in ECS Fargate environment."""
    import os

    return bool(os.environ.get("ECS_CONTAINER_METADATA_URI_V4"))


def _get_task_id() -> str:
    """Get ECS task ID for unique stream naming."""
    import os

    task_arn = os.environ.get("ECS_CONTAINER_METADATA_URI_V4", "")
    if task_arn:
        # Extract task ID from metadata URI
        return task_arn.split("/")[-1][:8]  # Use first 8 chars of task ID
    return "local"


def _configure_library_logging() -> None:
    """Reduce noise from third-party libraries while keeping errors visible."""
    # Uvicorn access logs disabled - redundant with custom [FLIGHTS] logger
    logging.getLogger("uvicorn.access").disabled = True

    # Set appropriate log levels for third-party libraries
    noisy_loggers = {
        # FastAPI/Uvicorn - keep error logs only
        "uvicorn": logging.INFO,
        "uvicorn.error": logging.INFO,
        "watchfiles": logging.WARNING,
        # HTTP clients
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        # MongoDB/Database
        "pymongo": logging.INFO,
        "pymongo.topology": logging.WARNING,
        "pymongo.connection": logging.WARNING,
        "pymongo.serverSelection": logging.WARNING,
        "pymongo.command": logging.WARNING,
        # Auth libraries
        "passlib": logging.INFO,
        # Google AI (google-genai SDK)
        "google.genai": logging.INFO,
        # AWS/Boto3
        "boto3": logging.WARNING,
        "botocore": logging.WARNING,
        "watchtower": logging.WARNING,
        # PDF generation
        "xhtml2pdf": logging.WARNING,
        "xhtml2pdf.tables": logging.WARNING,
        # Image proxy - suppress DEBUG logs (high frequency, low value)
        # Keep WARNING/ERROR for security issues and failures
        "app.api.proxy": logging.WARNING,
    }

    for logger_name, level in noisy_loggers.items():
        lib_logger = logging.getLogger(logger_name)
        lib_logger.setLevel(level)

        # Uvicorn loggers get custom immediate handler
        if logger_name.startswith("uvicorn"):
            lib_logger.handlers.clear()
            handler = ImmediateStreamHandler(sys.stdout)
            handler.setFormatter(_create_console_formatter("UVICORN"))
            lib_logger.addHandler(handler)
            lib_logger.propagate = False


# Keys that structured log processors / future redactors may treat as sensitive.
# The key ``code`` is common for API error codes; only voucher-shaped values are masked
# (see ``_value_looks_like_voucher_code``). Other keys here always mask string values.
LOG_REDACTION_KEYS = frozenset({"code", "voucher_code", "discount_code", "promo_code"})
_ALWAYS_REDACT_KEYS = LOG_REDACTION_KEYS - {"code"}
_VOUCHER_CODE_SHAPE = re.compile(r"^VOYA[\w-]+$", re.IGNORECASE)


def _is_always_redact_key(key: str) -> bool:
    kl = key.lower()
    return kl in {k.lower() for k in _ALWAYS_REDACT_KEYS}


def _value_looks_like_voucher_code(value: str) -> bool:
    s = value.strip()
    if len(s) < 8:
        return False
    return bool(_VOUCHER_CODE_SHAPE.match(s))


def mask_voucher_code_for_log(code: str | None) -> str:
    """Mask a voucher or promo code for log lines (G2A SafeKeys are secrets at rest)."""
    if not code:
        return "***"
    c = code.strip()
    if len(c) <= 6:
        return "***"
    return f"{c[:4]}…{c[-2:]}"


def scrub_sensitive_structured_data(obj: Any, *, _depth: int = 0) -> None:
    """Recursively mask voucher-related fields in dict/list structures (in place).

    Used by Sentry ``before_send`` and any JSON-like structured payloads where
    plaintext SafeKeys must not be shipped to third parties.
    """
    if _depth > 30:
        return
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            key_str = str(k)
            v = obj[k]
            if _is_always_redact_key(key_str):
                if isinstance(v, str):
                    obj[k] = mask_voucher_code_for_log(v)
                else:
                    obj[k] = "[redacted]"
            elif key_str.lower() == "code":
                if isinstance(v, str) and _value_looks_like_voucher_code(v):
                    obj[k] = mask_voucher_code_for_log(v)
                else:
                    scrub_sensitive_structured_data(v, _depth=_depth + 1)
            else:
                scrub_sensitive_structured_data(v, _depth=_depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            scrub_sensitive_structured_data(item, _depth=_depth + 1)


def scrub_sentry_event(event: dict[str, Any]) -> None:
    """Mask voucher codes in a Sentry event payload (mutates *event* in place)."""
    scrub_sensitive_structured_data(event)
