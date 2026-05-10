"""Command-line entry point and orchestration."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    DEFAULT_BITRATE,
    DEFAULT_LINKS_FILE,
    DEFAULT_LOG_DIR,
    DEFAULT_OUTPUT_DIR,
)
from .converter import ConversionResult, convert_all, ensure_ffmpeg
from .duration import format_hms, total_library_duration
from .links import LinksError, load_links
from .logger import setup_logger
from .shuffle import reshuffle_directory


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="yt-mp3",
        description="Convert YouTube videos listed in a JSON file into MP3 files.",
    )
    p.add_argument(
        "--links",
        "-l",
        type=Path,
        default=DEFAULT_LINKS_FILE,
        help=f"Path to JSON array of YouTube URLs (default: {DEFAULT_LINKS_FILE.name})",
    )
    p.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write MP3s into (default: ./{DEFAULT_OUTPUT_DIR.name})",
    )
    p.add_argument(
        "--bitrate",
        "-b",
        default=DEFAULT_BITRATE,
        help=f"MP3 bitrate in kbps (default: {DEFAULT_BITRATE})",
    )
    p.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory for log files (default: {DEFAULT_LOG_DIR})",
    )
    p.add_argument(
        "--randomize",
        "-r",
        action="store_true",
        help="Shuffle the playlist and prefix each output file with its position (1 - ..., 2 - ...).",
    )
    p.add_argument(
        "--reshuffle",
        "-R",
        action="store_true",
        help="Skip conversion. Re-number existing .mp3 files in --output-dir with a fresh shuffle.",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose console output (DEBUG level).",
    )
    return p


def _print_summary(results: list[ConversionResult], output_dir: Path) -> int:
    """Print a final summary and return an exit code (0 if all succeeded)."""
    from .logger import get_logger

    log = get_logger()
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    log.info("")
    log.info("=" * 60)
    log.info("Summary")
    log.info("=" * 60)
    log.info("Output directory : %s", output_dir)
    log.info("Total            : %d", len(results))
    log.info("Succeeded        : %d", len(successes))
    log.info("Failed           : %d", len(failures))

    total_seconds, counted, unreadable = total_library_duration(output_dir)
    library_line = f"Library duration : {format_hms(total_seconds)}  ({counted} file{'s' if counted != 1 else ''}"
    if unreadable:
        library_line += f", {unreadable} unreadable"
    library_line += ")"
    log.info(library_line)

    if failures:
        log.info("")
        log.info("Failed conversions:")
        for r in failures:
            log.info("  • %s", r.url)
            log.info("      %s", r.error)

    return 0 if not failures else 1


def _print_reshuffle_summary(output_dir: Path, renamed: int, errors: int) -> int:
    from .logger import get_logger

    log = get_logger()
    total_seconds, counted, unreadable = total_library_duration(output_dir)
    log.info("")
    log.info("=" * 60)
    log.info("Reshuffle summary")
    log.info("=" * 60)
    log.info("Directory        : %s", output_dir)
    log.info("Renamed          : %d", renamed)
    log.info("Errors           : %d", errors)
    library_line = (
        f"Library duration : {format_hms(total_seconds)}  "
        f"({counted} file{'s' if counted != 1 else ''}"
    )
    if unreadable:
        library_line += f", {unreadable} unreadable"
    library_line += ")"
    log.info(library_line)
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    log = setup_logger(args.log_dir, verbose=args.verbose)

    try:
        ensure_ffmpeg()
    except RuntimeError as e:
        log.error(str(e))
        return 2

    if args.reshuffle:
        if args.randomize:
            log.warning("--randomize is ignored when --reshuffle is set.")
        log.info("Mode: reshuffle existing MP3s (no conversion)")
        log.info("Directory: %s", args.output_dir)
        log.info("")
        renamed, errors = reshuffle_directory(args.output_dir)
        return _print_reshuffle_summary(args.output_dir, renamed, errors)

    try:
        urls = load_links(args.links)
    except LinksError as e:
        log.error(str(e))
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", args.output_dir)
    log.info("Bitrate         : %s kbps", args.bitrate)
    log.info("Randomize       : %s", "yes" if args.randomize else "no")
    log.info("")

    results = convert_all(urls, args.output_dir, args.bitrate, randomize=args.randomize)
    return _print_summary(results, args.output_dir)


if __name__ == "__main__":
    sys.exit(main())
