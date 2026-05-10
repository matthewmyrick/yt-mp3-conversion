"""Load and validate the YouTube links file."""
import json
from pathlib import Path

from .logger import get_logger


class LinksError(Exception):
    pass


def load_links(path: Path) -> list[str]:
    """Load a JSON array of URL strings from path.

    Raises LinksError on missing file, invalid JSON, or wrong shape.
    Items that aren't non-empty strings are skipped with a warning.
    """
    log = get_logger()

    if not path.exists():
        raise LinksError(f"Links file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise LinksError(f"Links file is not valid JSON ({path}): {e}") from e

    if not isinstance(data, list):
        raise LinksError(
            f"Links file must contain a JSON array of URL strings; got {type(data).__name__}"
        )

    urls: list[str] = []
    for i, item in enumerate(data):
        if isinstance(item, str) and item.strip():
            urls.append(item.strip())
        else:
            log.warning("Skipping invalid entry at index %d: %r", i, item)

    if not urls:
        raise LinksError(f"No valid URLs found in {path}")

    log.info("Loaded %d URL(s) from %s", len(urls), path)
    return urls
