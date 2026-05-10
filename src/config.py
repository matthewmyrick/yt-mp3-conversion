"""Default configuration values."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_LINKS_FILE = PROJECT_ROOT / "yt-mp3-links.json"
DEFAULT_OUTPUT_DIR = Path.cwd() / "mp3-yt-output"
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_BITRATE = "192"

TMP_SUBDIR = ".tmp"
