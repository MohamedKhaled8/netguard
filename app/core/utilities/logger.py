"""Structured logging system for NetGuard AI."""

from __future__ import annotations
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formats log records as one-line JSON documents for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            log_entry["metadata"] = record.metadata
        return json.dumps(log_entry)


class ColoredConsoleFormatter(logging.Formatter):
    """Human-readable console formatter with ANSI color coding."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[1;31m",# Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        time_str = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
        msg = f"{color}[{time_str}] [{record.levelname:<8}] [{record.name}] {record.getMessage()}{self.RESET}"
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


def setup_logger(
    name: str = "netguard",
    level: str = "INFO",
    log_dir: Path | str = "logs",
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configures and returns the central NetGuard logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Avoid duplicate handlers if re-called
    if logger.handlers:
        return logger

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredConsoleFormatter())
        logger.addHandler(console_handler)

    if log_to_file:
        p_log_dir = Path(log_dir)
        p_log_dir.mkdir(parents=True, exist_ok=True)
        file_path = p_log_dir / "netguard.log"
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger
