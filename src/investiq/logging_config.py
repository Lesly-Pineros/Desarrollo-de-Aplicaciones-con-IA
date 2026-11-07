"""Safe console logging helpers for the local application runtime."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import logging
import sys
from time import perf_counter
from traceback import extract_tb
from uuid import uuid4

_request_id: ContextVar[str] = ContextVar("investiq_request_id", default="-")


class _SafeLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Third-party HTTP/LLM loggers can include request URLs or payloads.
        if not (record.name == "investiq" or record.name.startswith("investiq.")):
            return False
        record.request_id = _request_id.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Configure concise stderr logs without printing exception payloads."""
    normalized_level = str(level).upper().strip()
    numeric_level = getattr(logging, normalized_level, logging.INFO)
    if normalized_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        numeric_level = logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(_SafeLogFilter())
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)


@contextmanager
def request_context():
    token = _request_id.set(uuid4().hex[:8])
    try:
        yield _request_id.get()
    finally:
        _request_id.reset(token)


@contextmanager
def log_stage(logger: logging.Logger, stage: str, *, failure_level: int = logging.ERROR, **fields):
    """Log a controlled stage name, elapsed time and safe exception location."""
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    suffix = f" {details}" if details else ""
    started = perf_counter()
    logger.info("stage.start name=%s%s", stage, suffix)
    try:
        yield
    except Exception as error:
        elapsed_ms = round((perf_counter() - started) * 1000)
        logger.log(failure_level, "stage.failed name=%s duration_ms=%d error_type=%s location=%s%s",
                   stage, elapsed_ms, type(error).__name__, _safe_location(error), suffix)
        raise
    else:
        elapsed_ms = round((perf_counter() - started) * 1000)
        logger.info("stage.done name=%s duration_ms=%d%s", stage, elapsed_ms, suffix)


def log_unexpected(logger: logging.Logger, event: str, error: Exception) -> None:
    """Report an exception class and stack locations, never its raw message."""
    logger.error("event=%s error_type=%s location=%s", event, type(error).__name__, _safe_location(error))


def _safe_location(error: Exception) -> str:
    frames = extract_tb(error.__traceback__)
    if not frames:
        return "unknown"
    return " <- ".join(f"{frame.filename.rsplit('/', 1)[-1]}:{frame.lineno}:{frame.name}"
                       for frame in frames[-6:])
