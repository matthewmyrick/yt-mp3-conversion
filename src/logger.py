"""Logging setup: console + timestamped file log."""
import logging
import sys
from datetime import datetime
from pathlib import Path

LOGGER_NAME = "yt_mp3"


def setup_logger(log_dir: Path, verbose: bool = False) -> logging.Logger:
    """Configure and return the project logger.

    - Console handler: INFO (or DEBUG when verbose), human-readable.
    - File handler: DEBUG, includes timestamps + levels, written to log_dir.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"yt-mp3-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)

    logger.debug("Logger initialized; log file: %s", log_path)
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
