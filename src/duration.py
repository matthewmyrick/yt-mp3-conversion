"""Compute total duration of MP3 files via ffprobe (bundled with ffmpeg)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .logger import get_logger


def get_mp3_duration_seconds(path: Path) -> float | None:
    """Return duration of an mp3 file in seconds, or None on error."""
    if shutil.which("ffprobe") is None:
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return None


def format_hms(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def total_library_duration(output_dir: Path) -> tuple[float, int, int]:
    """Sum durations of every .mp3 in output_dir (non-recursive).

    Returns (total_seconds, counted_files, unreadable_files).
    """
    log = get_logger()
    total = 0.0
    counted = 0
    unreadable = 0
    for mp3 in sorted(output_dir.glob("*.mp3")):
        dur = get_mp3_duration_seconds(mp3)
        if dur is None:
            log.debug("Could not read duration: %s", mp3.name)
            unreadable += 1
            continue
        total += dur
        counted += 1
    return total, counted, unreadable
