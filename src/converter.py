"""YouTube -> MP3 conversion via yt-dlp, with safe overwrite."""
from __future__ import annotations

import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from .config import TMP_SUBDIR
from .logger import get_logger


@dataclass
class ConversionResult:
    url: str
    success: bool
    output_path: Path | None = None
    error: str | None = None


def ensure_ffmpeg() -> None:
    """Raise RuntimeError with a helpful message if ffmpeg is missing."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. yt-dlp needs ffmpeg to produce MP3 files.\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt-get install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


class _YDLLogger:
    """Adapter so yt-dlp's internal messages flow into our logger."""

    def __init__(self) -> None:
        self._log = get_logger()

    def debug(self, msg: str) -> None:
        if msg.startswith("[debug] "):
            self._log.debug(msg)
        else:
            self._log.debug(msg)

    def info(self, msg: str) -> None:
        self._log.debug(msg)

    def warning(self, msg: str) -> None:
        self._log.warning(msg)

    def error(self, msg: str) -> None:
        self._log.error(msg)


def _build_ydl_opts(tmp_dir: Path, bitrate: str) -> dict:
    return {
        "format": "bestaudio/best",
        "outtmpl": str(tmp_dir / "%(title)s.%(ext)s"),
        "restrictfilenames": False,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "overwrites": True,
        "logger": _YDLLogger(),
        # Auto-download the YouTube JS challenge solver from GitHub.
        # YouTube rotates the signature cipher often; bundling the solver
        # would force constant yt-dlp releases, so it's fetched on demand.
        "remote_components": ["ejs:github"],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": bitrate,
            }
        ],
    }


def _safe_overwrite(src: Path, dst: Path) -> None:
    """Atomically move src to dst, replacing dst if it exists.

    `os.replace` is atomic when src and dst are on the same filesystem
    (which they will be, since tmp lives inside the output dir).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    os.replace(src, dst)


def convert_one(
    url: str,
    output_dir: Path,
    bitrate: str,
    filename_prefix: str = "",
) -> ConversionResult:
    """Download + convert a single URL. Returns a ConversionResult.

    Strategy:
      1. Download + convert into <output_dir>/.tmp/.
      2. On success, os.replace() the resulting .mp3 into <output_dir>/.
         The old file is only replaced after the new one is fully written.

    `filename_prefix` is prepended to the final filename (used by --randomize
    to add e.g. "1 - ", "2 - ").
    """
    log = get_logger()
    tmp_dir = output_dir / TMP_SUBDIR
    tmp_dir.mkdir(parents=True, exist_ok=True)

    log.info("→ Converting: %s", url)

    final_tmp_path: Path | None = None
    try:
        with YoutubeDL(_build_ydl_opts(tmp_dir, bitrate)) as ydl:
            info = ydl.extract_info(url, download=True)

        requested = (info or {}).get("requested_downloads") or []
        if not requested or "filepath" not in requested[0]:
            return ConversionResult(
                url=url,
                success=False,
                error="yt-dlp did not report a final output filepath",
            )

        final_tmp_path = Path(requested[0]["filepath"])
        if not final_tmp_path.exists():
            return ConversionResult(
                url=url,
                success=False,
                error=f"Expected MP3 not found at {final_tmp_path}",
            )

        final_path = output_dir / f"{filename_prefix}{final_tmp_path.name}"
        existed = final_path.exists()
        _safe_overwrite(final_tmp_path, final_path)
        final_tmp_path = None  # moved; nothing to clean up

        log.info(
            "✓ %s: %s",
            "Overwrote" if existed else "Saved",
            final_path.name,
        )
        return ConversionResult(url=url, success=True, output_path=final_path)

    except DownloadError as e:
        log.error("✗ yt-dlp failed for %s: %s", url, e)
        return ConversionResult(url=url, success=False, error=str(e))
    except subprocess.CalledProcessError as e:
        log.error("✗ ffmpeg failed for %s: %s", url, e)
        return ConversionResult(url=url, success=False, error=f"ffmpeg error: {e}")
    except Exception as e:
        log.exception("✗ Unexpected error for %s", url)
        return ConversionResult(url=url, success=False, error=f"{type(e).__name__}: {e}")
    finally:
        # Clean up any leftover temp file on failure.
        if final_tmp_path is not None and final_tmp_path.exists():
            try:
                final_tmp_path.unlink()
            except OSError:
                pass


def convert_all(
    urls: list[str],
    output_dir: Path,
    bitrate: str,
    randomize: bool = False,
) -> list[ConversionResult]:
    """Convert each URL sequentially. Returns one ConversionResult per URL.

    When `randomize=True`, the URLs are shuffled and each output filename is
    prefixed with its position (e.g. "1 - ", "2 - "), zero-padded to fit N.
    """
    log = get_logger()
    output_dir.mkdir(parents=True, exist_ok=True)

    ordered = list(urls)
    if randomize:
        random.shuffle(ordered)
        log.info("Randomized order; output files will be numbered 1..%d", len(ordered))

    results: list[ConversionResult] = []
    total = len(ordered)
    width = len(str(total))
    for i, url in enumerate(ordered, start=1):
        log.info("[%d/%d]", i, total)
        prefix = f"{i:0{width}d} - " if randomize else ""
        results.append(convert_one(url, output_dir, bitrate, filename_prefix=prefix))

    # Tidy up the tmp dir if it's empty.
    tmp_dir = output_dir / TMP_SUBDIR
    try:
        if tmp_dir.exists() and not any(tmp_dir.iterdir()):
            tmp_dir.rmdir()
    except OSError:
        pass

    return results
