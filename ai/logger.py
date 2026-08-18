"""
AI Module — Logging System
===========================
Provides professional, structured logging for dataset verification,
configuration loading, model downloading, and infrastructure setup.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# Reconfigure standard streams to UTF-8 for cross-platform stability
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "sku110k_pipeline",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Create and return a professionally formatted logger.

    Parameters
    ----------
    name : str
        Logger identifier name.
    level : int
        Logging level (default: logging.INFO).
    log_file : Optional[Path]
        Optional path to log file where logs will be appended.

    Returns
    -------
    logging.Logger
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Stream Handler (stdout)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # File Handler (optional)
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as exc:
            logger.warning(f"Could not attach file handler to {log_file}: {exc}")

    return logger


# Default global logger instance
logger = setup_logger("sku110k_pipeline")
