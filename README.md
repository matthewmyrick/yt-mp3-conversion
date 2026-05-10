# yt-mp3-conversion

Batch-convert a list of YouTube links into MP3 files using [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) + `ffmpeg`.

- Input: a JSON file containing an array of YouTube URLs.
- Output: an `.mp3` file per link in an output directory (default `./mp3-yt-output/`).
- Safe overwrite: each file is downloaded + converted to a temp location first, then atomically moved over any existing file — you don't lose the old MP3 unless the new one was produced successfully.
- Per-run logs are written to `./logs/` so failed conversions are easy to inspect.

## Requirements

- Python 3.10+
- [`ffmpeg`](https://ffmpeg.org/) on your `PATH`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`

## Setup

```bash
# Create + activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python deps
pip install -r requirements.txt
```

## Usage

The defaults are designed so you can usually just run:

```bash
python main.py
```

This reads `./yt-mp3-links.json` and writes MP3s to `./mp3-yt-output/`.

### Input file format

`yt-mp3-links.json` is a JSON array of URL strings:

```json
[
  "https://www.youtube.com/watch?v=10yrPDf92hY",
  "https://youtu.be/dQw4w9WgXcQ"
]
```

### Optional flags

| Flag | Default | Description |
| --- | --- | --- |
| `--links`, `-l` | `./yt-mp3-links.json` | Path to the JSON links file. |
| `--output-dir`, `-o` | `./mp3-yt-output/` | Where to write the MP3s. Created if missing. |
| `--bitrate`, `-b` | `192` | MP3 bitrate in kbps (e.g. `128`, `192`, `320`). |
| `--randomize`, `-r` | off | Shuffle the playlist; output files get prefixed with `01 - `, `02 - `, … (zero-padded to fit N) so they sort in the new order. |
| `--reshuffle`, `-R` | off | **Skip conversion.** Renumber the `.mp3`s already in `--output-dir` with a fresh shuffle. Useful for re-shuffling an existing library without re-downloading. |
| `--log-dir` | `./logs/` | Directory for per-run log files. |
| `--verbose`, `-v` | off | Show DEBUG output in the console (the log file is always DEBUG). |

Examples:

```bash
# Use a different links file and output dir
python main.py --links my-links.json --output-dir ~/Music/yt

# 320kbps + verbose console
python main.py -b 320 -v

# Shuffle playlist order with numbered prefixes
python main.py --randomize

# Re-shuffle existing MP3s in ./mp3-yt-output/ without re-downloading
python main.py --reshuffle

# Re-shuffle a different directory
python main.py --reshuffle --output-dir ~/Music/yt
```

> **Note on `--randomize` re-runs:** the order is shuffled fresh each run, so re-running may leave behind orphaned numbered files from the previous shuffle (different titles). Wipe `mp3-yt-output/` first if you want a clean re-shuffle — or use `--reshuffle` afterwards to renumber whatever's there.

### How `--reshuffle` works

It strips any existing `NN - ` prefix from each `.mp3` in the target directory, shuffles, and renumbers — using a **two-phase rename** (originals → temp names → new names) so files that swap prefixes never collide and clobber each other. No re-downloading, no conversion, just renaming.

## BoneBeat shortcut script

`scripts/convert.sh` is a wrapper for switching the music on a BoneBeat earphones drive (mounted at `/Volumes/BoneBeat`). It reads the prepared playlist JSON files in `playlists/`.

**The convert path is destructive:** each `rap` / `edm` run wipes the BoneBeat volume root first (preserving hidden files and the FAT32 `System Volume Information` folder), then writes the fresh playlist flat onto the root. That's the intended workflow — switching playlists means swapping the contents of the device.

```bash
# Switch BoneBeat to the rap playlist  (wipe + write randomized + numbered)
./scripts/convert.sh rap

# Switch BoneBeat to the edm playlist
./scripts/convert.sh edm

# Re-shuffle what's already on BoneBeat — NO wipe, NO re-downloading
./scripts/convert.sh -r
```

Exit codes:

- `0` — success
- `1` — bad arguments / unknown playlist
- `2` — missing venv or links file
- `3` — BoneBeat is not mounted at `/Volumes/BoneBeat`

> To find any USB/audio mount yourself: `ls /Volumes/` or `mount | grep -i <name>`.

## How safe-overwrite works

For each URL the script:

1. Downloads and converts into `<output-dir>/.tmp/<title>.mp3`.
2. Only after the MP3 is fully written, calls `os.replace()` to atomically move it over `<output-dir>/<title>.mp3`.

If the download or conversion fails, the old MP3 is left untouched and the temp file is cleaned up.

## Logging & summary

Two streams:

- **Console** — concise progress: `→ Converting`, `✓ Saved/Overwrote`, `✗ Failed`, plus a summary at the end with all failed URLs and their error messages.
- **Log file** at `./logs/yt-mp3-<timestamp>.log` — full DEBUG output, including yt-dlp's internal messages and full tracebacks.

The end-of-run summary also prints `Library duration` (HH:MM:SS) — the total play time of every `.mp3` currently in the output directory, computed via `ffprobe`. So you can re-run later and see total music length grow.

The script exits with code:

- `0` — all conversions succeeded
- `1` — at least one conversion failed
- `2` — setup error (missing ffmpeg, bad links file, etc.)

## Project layout

```
yt-mp3-conversion/
├── main.py                  # thin entry point → src.cli.main()
├── scripts/
│   └── convert.sh           # BoneBeat wrapper: rap | edm [-r]
├── playlists/
│   ├── yt-mp3-links-rap.json
│   └── yt-mp3-links-edm.json
├── src/
│   ├── cli.py               # argparse + orchestration
│   ├── config.py            # defaults
│   ├── converter.py         # yt-dlp wrapper + safe overwrite + shuffle/prefix
│   ├── duration.py          # ffprobe-based total library duration
│   ├── links.py             # load/validate JSON links file
│   ├── logger.py            # console + file logging setup
│   └── shuffle.py           # --reshuffle: two-phase rename of existing MP3s
├── yt-mp3-links.json        # default input list (used when running main.py directly)
├── mp3-yt-output/           # default output (gitignored)
└── logs/                    # per-run logs (gitignored)
```
