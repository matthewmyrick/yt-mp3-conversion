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

# macOS auto-creates AppleDouble sidecars (._<file>) on FAT32 volumes to store
# extended attributes. They're invisible in Finder but show up to glob() and
# break the reshuffle. dot_clean merges/removes them.
clean_appledouble() {
    if command -v dot_clean >/dev/null 2>&1; then
        dot_clean -m "$BONEBEAT_MOUNT" 2>/dev/null || true
    fi
}

wipe_bonebeat() {
    # Delete everything at the volume root EXCEPT macOS system dotfiles
    # (.Trashes, .fseventsd, .Spotlight-V100, etc.) and the Windows-created
    # 'System Volume Information' folder that FAT32 drives rely on.
    # AppleDouble sidecars (._*) ARE deleted — clean_appledouble already
    # cleared them, but this guards against any new ones that re-appeared.
    echo "Wiping $BONEBEAT_MOUNT (preserving system metadata folders)..."
    find "$BONEBEAT_MOUNT" -mindepth 1 -maxdepth 1 \
        ! -name '.Trashes' \
        ! -name '.fseventsd' \
        ! -name '.Spotlight-V100' \
        ! -name '.DocumentRevisions-V100' \
        ! -name '.TemporaryItems' \
        ! -name 'System Volume Information' \
        -exec rm -rf {} +
    echo "Wipe complete."
    echo
}

if $RESHUFFLE; then
    clean_appledouble
    exec "$PYTHON" "$MAIN" --reshuffle --output-dir "$BONEBEAT_MOUNT"
fi

LINKS_FILE="$PLAYLISTS_DIR/yt-mp3-links-${PLAYLIST}.json"
if [[ ! -f "$LINKS_FILE" ]]; then
    echo "Links file not found: $LINKS_FILE" >&2
    exit 2
fi

clean_appledouble
wipe_bonebeat

"$PYTHON" "$MAIN" \
    --links "$LINKS_FILE" \
    --output-dir "$BONEBEAT_MOUNT" \
    --randomize

# Scrub any new AppleDouble sidecars yt-dlp/ffmpeg created during conversion,
# so the device sees only the real .mp3 files.
clean_appledouble
