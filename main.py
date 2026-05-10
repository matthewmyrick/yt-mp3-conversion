"""Entry point: `python main.py [--links ...] [--output-dir ...] [--bitrate ...]`."""
import sys

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
