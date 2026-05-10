# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repo.

## What this project is

A small Python CLI that batch-converts YouTube videos into MP3 files via `yt-dlp` + `ffmpeg`. It is not a web app. There is no framework, no server, no deployment target — just `python main.py`.

## Conventions

- **Always use the project venv.** Run Python via `./venv/bin/python` (or `source venv/bin/activate` first). Don't fall back to system Python.
- **Keep modules small and focused.** Don't move everything into `main.py`. The split is:
  - `src/cli.py` — argparse + orchestration only
  - `src/converter.py` — yt-dlp wrapper, all conversion + filesystem logic, shuffle/prefix
  - `src/duration.py` — ffprobe-based duration calculation for the library summary
  - `src/shuffle.py` — `--reshuffle` mode: two-phase rename of existing MP3s in a directory
  - `src/links.py` — load/validate the JSON input
  - `src/logger.py` — logger setup
  - `src/config.py` — defaults / constants
  - `main.py` — thin entrypoint; should stay a few lines
- **Safe overwrite is a contract.** Never write directly to the final output path. Download to `<output>/.tmp/`, then use `os.replace()` to atomically swap. If you change conversion logic, preserve this invariant.
- **Reshuffle uses two-phase rename.** When changing `src/shuffle.py`, keep the originals → temp → final pattern. Renaming directly into final names would clobber files that are swapping prefixes (e.g. `01 - A` ↔ `02 - B`).
- **Logging matters.** Every failure must surface in the end-of-run summary with the URL and a useful error string. The full log file under `./logs/` should be enough to debug after the fact. Don't silently swallow exceptions.
- **Defaults must work with no arguments.** `python main.py` (no flags) should read `./yt-mp3-links.json` and write to `./mp3-yt-output/`. All flags are optional.

## Dependencies

- `yt-dlp` is the only Python dependency (see `requirements.txt`).
- `ffmpeg` is a system-level dependency, checked at startup via `ensure_ffmpeg()` in `src/converter.py`. If it's missing the script exits with code 2 and a clear install hint.

## Exit codes

- `0` — all conversions succeeded
- `1` — at least one conversion failed
- `2` — setup error (no ffmpeg, bad links file, etc.)

## When making changes

- Prefer editing existing modules over adding new files.
- Don't add features beyond what's asked. This is a small focused tool.
- After changes, re-run `python main.py` against `yt-mp3-links.json` to verify the happy path still works.
