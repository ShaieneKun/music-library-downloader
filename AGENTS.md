# AGENTS.md

Guidance for AI coding agents (Codex, Cursor, Claude Code, etc.) working in this repo.

Music Library Downloader: a Dockerised background service that mirrors YouTube Music playlists as `m4a` files and optionally uploads them to Google Drive. Python 3.14+, managed with `uv`.

## Docs

Read these before changing the related area:

- [docs/architecture.md](docs/architecture.md): modules, download cycle, naming conventions
- [docs/docker.md](docs/docker.md): container layout, volumes, `MUSIC_DIR` host songs directory
- [docs/configuration.md](docs/configuration.md): environment variables
- [docs/testing.md](docs/testing.md): how to run tests
- [README.md](README.md): user-facing setup, Google Drive OAuth

## Commands

```bash
just test            # all tests, inside a docker container
just test-compose    # compose-file tests, on the host (needs docker CLI)
uv run main.py once ./my-downloads                       # one cycle, no Docker (needs ffmpeg)
docker compose up -d --build                             # run the service
```

## Rules

- Install tools with Homebrew when possible (`brew install ...`); mention it if falling back to something else.
- Do not use the system `python3` (3.9 on macOS); use `uv run` or the container.
- Songs go to the host directory `MUSIC_DIR` (default `~/Music`), bind-mounted at `/data/songs`; state and logs stay in the `data` named volume. Keep `compose.yaml` and `compose.debug.yaml` in sync and update `src/tests/test_compose.py` when changing them.
- Config is read from environment variables via `src/config.py`; add new settings there, to `.env.template`, `docs/configuration.md` and `README.md`.
- Tests use `unittest` (no pytest). Add tests under `src/tests/` for new behaviour.
- Never commit `.env`, tokens, or downloaded songs (all git-ignored).
- Keep these docs updated when behaviour changes.
