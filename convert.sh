#!/usr/bin/env bash
# Wrapper around ../main.py for the rap / edm playlists.
#
# Convert mode (default):
#   Wipes /Volumes/BoneBeat (preserving hidden files + System Volume Information),
#   then converts the chosen playlist directly onto the volume root.
#
#   ./convert.sh rap         # wipe BoneBeat + convert rap playlist (randomized + numbered)
#   ./convert.sh edm         # wipe BoneBeat + convert edm playlist (randomized + numbered)
#
# Reshuffle mode:
#   Skips the wipe and the conversion. Just renumbers whatever .mp3s are
#   already on BoneBeat with a fresh shuffle.
#
#   ./convert.sh -r          # reshuffle whatever's on BoneBeat
#   ./convert.sh rap -r      # same — the playlist arg is ignored in -r mode

set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PYTHON="$PROJECT_ROOT/venv/bin/python"
MAIN="$PROJECT_ROOT/main.py"
PLAYLISTS_DIR="$PROJECT_ROOT/playlists"
BONEBEAT_MOUNT="/Volumes/BoneBeat"

usage() {
    cat <<EOF
Usage:
  ./$(basename "$0") <rap|edm>      Wipe BoneBeat and convert that playlist.
  ./$(basename "$0") -r             Reshuffle whatever is on BoneBeat.

Flags:
  -r, --reshuffle   Skip wipe + conversion. Renumber existing .mp3s.
  -h, --help        Show this help.

Examples:
  ./$(basename "$0") rap
  ./$(basename "$0") edm
  ./$(basename "$0") -r
EOF
}

PLAYLIST=""
RESHUFFLE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--reshuffle)
            RESHUFFLE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        rap|edm)
            PLAYLIST="$1"
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if ! $RESHUFFLE && [[ -z "$PLAYLIST" ]]; then
    echo "Missing playlist (rap or edm)." >&2
    usage >&2
    exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
    echo "Python venv not found at $PYTHON" >&2
    echo "Run from the project root: python3 -m venv venv && ./venv/bin/pip install -r requirements.txt" >&2
    exit 2
fi

if [[ ! -d "$BONEBEAT_MOUNT" ]]; then
    echo "BoneBeat is not mounted at $BONEBEAT_MOUNT" >&2
    echo "Plug it in and wait for macOS to mount it, then re-run." >&2
    exit 3
fi

wipe_bonebeat() {
    # Delete everything at the volume root EXCEPT hidden files (e.g. .Trashes,
    # .fseventsd) and the Windows-created 'System Volume Information' folder
    # that FAT32 drives rely on.
    echo "Wiping $BONEBEAT_MOUNT (preserving hidden files + 'System Volume Information')..."
    find "$BONEBEAT_MOUNT" -mindepth 1 -maxdepth 1 \
        ! -name '.*' \
        ! -name 'System Volume Information' \
        -exec rm -rf {} +
    echo "Wipe complete."
    echo
}

if $RESHUFFLE; then
    exec "$PYTHON" "$MAIN" --reshuffle --output-dir "$BONEBEAT_MOUNT"
fi

LINKS_FILE="$PLAYLISTS_DIR/yt-mp3-links-${PLAYLIST}.json"
if [[ ! -f "$LINKS_FILE" ]]; then
    echo "Links file not found: $LINKS_FILE" >&2
    exit 2
fi

wipe_bonebeat

exec "$PYTHON" "$MAIN" \
    --links "$LINKS_FILE" \
    --output-dir "$BONEBEAT_MOUNT" \
    --randomize
