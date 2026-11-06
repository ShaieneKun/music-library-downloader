# Docker

The service ships as a container (`Containerfile`, based on `python:3.14-slim` with `ffmpeg` and `uv`). Run it with `docker compose up -d --build`.

## Where data lives

| Container path | Host location | Contents |
| --- | --- | --- |
| `/data/songs` | **`MUSIC_DIR`** on the host (bind mount) | Downloaded `.m4a` files |
| `/data/state` | `data` named volume | Google Drive token and upload record |
| `/data/logs` | `data` named volume | Rotating `app.log` (5 MB x 3) and per-cycle `cycle-*.log` run logs |

The container sets `DESTINATION_FOLDER=/data/songs`, `STATE_DIR=/data/state`, `LOG_DIR=/data/logs`.

## `MUSIC_DIR`

Host directory for the downloaded songs.

- Set it in `.env` (or the shell). Default: `${HOME}/Music`.
- Use an absolute path; `~` is not expanded inside `.env`.
- The compose files use `${MUSIC_DIR:-${HOME}/Music}` with `create_host_path: true`, so Docker creates the directory if it does not exist. An empty value falls back to the default; a shell value beats `.env`.
- On Linux a directory created by Docker is owned by root, and the container user (`appuser`, uid 5678) may not be able to write to it. Create it beforehand and make it writable (e.g. `chown 5678 ~/Music/...` or `chmod`).
- Defined in both `compose.yaml` and `compose.debug.yaml`; keep them in sync.

## Files

- `compose.yaml`: normal service (`restart: unless-stopped`, 30 s stop grace period, `.env` as `env_file`).
- `compose.debug.yaml`: same mounts, starts under `debugpy` on port 5678.
- `.dockerignore` excludes `.env`, `compose*` and the git directory from the build context, so the image never contains secrets.

## Commands

```bash
docker compose up -d --build
docker compose logs -f
docker compose run --rm music-library-downloader python main.py once
docker compose run --rm music-library-downloader python main.py auth
docker compose down
```
