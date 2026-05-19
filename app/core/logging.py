from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Any

from app.core.config import settings

SENSITIVE_FIELDS = {"password", "password_hash", "token", "secret", "authorization", "jwt"}


class FlushRotatingFileHandler(RotatingFileHandler):
    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


class SensitiveDataFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        lower = msg.lower()
        for field in SENSITIVE_FIELDS:
            idx = lower.find(field)
            if idx == -1:
                continue
            after = idx + len(field)
            rest = msg[after:]
            if rest.startswith("=") or rest.startswith(':"'):
                msg = msg[:after] + "=[REDACTED]"
        record.msg = msg
        record.args = ()
        return True


class JSONFormatter(logging.Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        dt = datetime.fromtimestamp(record.created, tz=UTC)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{record.msecs:03.0f}Z"

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "trace_id"):
            payload["trace_id"] = record.trace_id
        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code
        if hasattr(record, "method"):
            payload["method"] = record.method
        if hasattr(record, "path"):
            payload["path"] = record.path
        if hasattr(record, "user_id"):
            payload["user_id"] = str(record.user_id)
        if hasattr(record, "extra_data"):
            payload["extra"] = record.extra_data
        return json.dumps(payload, default=str)


class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        prefix = f"[{self.formatTime(record, '%H:%M:%S')}] {record.levelname:<7} {record.name}"
        trace = getattr(record, "trace_id", None)
        if trace:
            prefix += f" [{trace[:8]}]"
        msg = record.getMessage()
        lines = msg.split("\n")
        out = [f"{prefix}  {lines[0]}"]
        for line in lines[1:]:
            out.append(f"{'':>{len(prefix)}}  {line}")
        if record.exc_info and record.exc_info[0]:
            out.append(self.formatException(record.exc_info))
        return "\n".join(out)


def _ensure_log_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _build_handler(
    filename: str,
    level: str,
    formatter: logging.Formatter,
    max_bytes: int,
    backup_count: int,
) -> FlushRotatingFileHandler:
    path = os.path.join(settings.log_dir, filename)
    handler = FlushRotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(formatter)
    handler.addFilter(SensitiveDataFilter())
    return handler


def setup_logging() -> None:
    _ensure_log_dir(settings.log_dir)

    log_level = settings.log_level.upper()
    json_logs = settings.json_logs
    max_bytes = settings.log_max_bytes
    backup_count = settings.log_backup_count

    json_fmt = JSONFormatter()
    plain_fmt = PlainFormatter("%(asctime)s %(levelname)-7s %(name)s  %(message)s")

    console_fmt = json_fmt if json_logs else plain_fmt
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(console_fmt)
    console.addFilter(SensitiveDataFilter())

    app_file = _build_handler("app.log", log_level, json_fmt, max_bytes, backup_count)
    error_file = _build_handler("error.log", "ERROR", json_fmt, max_bytes, backup_count)
    requests_file = _build_handler("requests.log", "INFO", json_fmt, max_bytes, backup_count)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(app_file)
    root.addHandler(error_file)

    requests_logger = logging.getLogger("requests")
    requests_logger.handlers.clear()
    requests_logger.addHandler(requests_file)
    requests_logger.setLevel(log_level)
    requests_logger.propagate = False

    for uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.handlers.append(console)
        uvicorn_logger.propagate = False

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
