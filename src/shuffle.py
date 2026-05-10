"""Reshuffle MP3 files already in a directory by renumbering their prefixes."""
from __future__ import annotations

import os
import random
import re
import uuid
from pathlib import Path

from .logger import get_logger

# Matches the prefix we produce in converter.py: "<digits> - "
PREFIX_RE = re.compile(r"^\d+ - ")


def strip_prefix(name: str) -> str:
    """Remove a leading 'NN - ' prefix if present."""
    return PREFIX_RE.sub("", name, count=1)


def reshuffle_directory(directory: Path) -> tuple[int, int]:
    """Shuffle and renumber every .mp3 in `directory`.

    Returns (renamed_count, error_count).

    Strategy (two-phase rename to avoid collisions when two files swap prefixes):
      1. Collect every .mp3 (non-recursive), strip any existing 'NN - ' prefix.
      2. Shuffle.
      3. Phase A: rename each original file to a unique temp name in the same dir.
      4. Phase B: rename each temp to its final 'NN - <bare-name>.mp3'.
    """
    log = get_logger()

    if not directory.exists():
        log.error("Directory does not exist: %s", directory)
        return (0, 1)

    mp3s = sorted(directory.glob("*.mp3"))
    if not mp3s:
        log.warning("No .mp3 files found in %s", directory)
        return (0, 0)

    files = [(p, strip_prefix(p.name)) for p in mp3s]
    random.shuffle(files)
    width = len(str(len(files)))

    log.info("Reshuffling %d file(s) in %s", len(files), directory)

    # Phase A: move all originals to unique temp names so no two final names collide.
    run_tag = uuid.uuid4().hex[:8]
    temps: list[tuple[Path, str]] = []
    for i, (orig, bare) in enumerate(files):
        temp = directory / f".reshuffle-{run_tag}-{i}.mp3"
        try:
            os.rename(orig, temp)
        except OSError as e:
            log.error("Failed to stage rename for %s: %s", orig.name, e)
            # Roll back: move any already-staged temps back to their originals.
            _rollback(temps + [(temp, bare)], files[: len(temps) + 1])
            return (0, 1)
        temps.append((temp, bare))

    # Phase B: move each temp to its final NN - <bare>.mp3 position.
    renamed = 0
    errors = 0
    for i, (temp, bare) in enumerate(temps, start=1):
        final = directory / f"{i:0{width}d} - {bare}"
        try:
            os.replace(temp, final)
            log.info("✓ %s", final.name)
            renamed += 1
        except OSError as e:
            log.error("✗ Failed to rename to %s: %s", final.name, e)
            errors += 1

    return (renamed, errors)


def _rollback(
    temps: list[tuple[Path, str]],
    originals: list[tuple[Path, str]],
) -> None:
    """Best-effort rollback if Phase A fails partway through."""
    log = get_logger()
    for (temp, _), (orig, _) in zip(temps, originals):
        if temp.exists() and not orig.exists():
            try:
                os.rename(temp, orig)
            except OSError as e:
                log.error("Rollback failed for %s -> %s: %s", temp, orig, e)
