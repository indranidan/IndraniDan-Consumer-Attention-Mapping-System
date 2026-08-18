"""
AI Module — Utility Helpers
============================
Shared utilities used across the AI module:
- Professional logging setup
- Device detection (CUDA / CPU)
- Execution timer context manager
- Directory creation helper
- Output directory initialization
"""

import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Generator, Optional


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
_LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create and return a professionally formatted logger.

    Parameters
    ----------
    name : str
        Logger name (typically ``__name__`` of the calling module).
    level : int
        Logging level (default: INFO).

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------
def get_device(preference: str = "auto") -> str:
    """
    Determine the best available compute device.

    Parameters
    ----------
    preference : str
        ``"auto"`` | ``"cpu"`` | ``"cuda"`` | ``"cuda:0"`` etc.

    Returns
    -------
    str
        Device string suitable for Ultralytics / PyTorch.
    """
    # pyrefly: ignore [missing-import]
    import torch

    logger = setup_logger(__name__)

    if preference.lower() == "cpu":
        logger.info("Device: CPU (forced by configuration)")
        return "cpu"

    if preference.lower().startswith("cuda"):
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"Device: CUDA — {gpu_name}")
            return preference.lower()
        logger.warning("CUDA requested but not available — falling back to CPU")
        return "cpu"

    # auto
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"Device: CUDA (auto-detected) — {gpu_name}")
        return "cuda:0"

    logger.info("Device: CPU (no CUDA device detected)")
    return "cpu"


# ---------------------------------------------------------------------------
# Timer context manager
# ---------------------------------------------------------------------------
@contextmanager
def timer(description: str, logger: Optional[logging.Logger] = None) -> Generator[None, None, None]:
    """
    Context manager that logs the elapsed time for a block.

    Usage::

        with timer("Running inference", logger):
            model.predict(...)

    Parameters
    ----------
    description : str
        Human-readable label for the timed block.
    logger : logging.Logger, optional
        If provided, logs via this logger; otherwise prints to stdout.
    """
    start = time.perf_counter()
    _log(logger, f"{description}...")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        _log(logger, f"{description} — completed in {elapsed:.2f}s")


def _log(logger: Optional[logging.Logger], message: str) -> None:
    """Log via logger if available, else print."""
    if logger:
        logger.info(message)
    else:
        print(message)


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------
def ensure_directory(path: Path) -> Path:
    """
    Create a directory (and parents) if it does not exist.

    Parameters
    ----------
    path : Path
        Directory path to ensure.

    Returns
    -------
    Path
        The same path, guaranteed to exist.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_output_directories(base_output_path: Path) -> Dict[str, Path]:
    """
    Automatically create required pipeline output subdirectories:
    - outputs/training
    - outputs/evaluation
    - outputs/logs
    - outputs/weights
    - outputs/plots
    - outputs/reports

    Parameters
    ----------
    base_output_path : Path
        Base output directory path (e.g. ai/outputs).

    Returns
    -------
    Dict[str, Path]
        Dictionary mapping directory keys to their absolute Path objects.
    """
    subdirs = ["training", "evaluation", "logs", "weights", "plots", "reports"]
    created_paths: Dict[str, Path] = {}

    ensure_directory(base_output_path)
    created_paths["outputs"] = base_output_path

    for sub in subdirs:
        dir_path = base_output_path / sub
        ensure_directory(dir_path)
        created_paths[sub] = dir_path

    return created_paths


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def print_banner(title: str) -> None:
    """Print a professional section banner to stdout."""
    width = 60
    border = "=" * width
    print(f"\n{border}")
    print(f"  {title}")
    print(f"{border}\n")
