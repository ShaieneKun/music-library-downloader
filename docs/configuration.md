# Configuration

Set in `.env` (copy from `.env.template`). `.env` is git-ignored.

| Variable | Default | Description |
| --- | --- | --- |
| `PLAYLIST_URL` | built-in sample | One or more playlist URLs (space or comma separated) |
| `INTERVAL_SECONDS` | `3600` | Time between checks |
| `MUSIC_DIR` | `~/Music` | Host directory for downloaded songs. Read by compose only, not by the app. Absolute path |
| `DRIVE_UPLOAD_ENABLED` | `false` | Upload new songs to Google Drive |
| `DRIVE_FOLDER_NAME` | `Music Library Downloader` | Folder in My Drive; `Music/Auto` creates nested folders |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | none | OAuth client (type "TVs and Limited Input devices") |
| `SKIP_DOWNLOAD_IF_UPLOADED` | `false` | `false`: download songs missing locally even if already in Drive (they are never re-uploaded). `true`: skip songs already uploaded |
| `HOST_HOSTNAME` | container hostname | Machine name shown in the cycle summary. In a container the default is a random id, so set the real one (compose passes it through; e.g. `export HOST_HOSTNAME=$(hostname)` or put it in `.env`) |
| `DOWNLOAD_WORKERS` | `4` | Songs downloaded in parallel |
| `DOWNLOAD_SLEEP_SECONDS` | `2` | Minimum pause between song download starts, shared by all workers |
| `DOWNLOAD_RETRIES` | `2` | Extra attempts per song after a transient error (HTTP 403/429/5xx, timeouts, dropped connections). Permanent errors such as removed videos are not retried. Leftover files of a song that still fails are deleted |
| `YTDLP_AUTO_UPDATE` | `true` | Upgrade `yt-dlp` at startup and periodically; restarts itself after an upgrade |
| `YTDLP_UPDATE_INTERVAL_SECONDS` | `86400` | Time between update checks |
| `LOG_KEEP_IDLE` | `false` | Keep (and upload) the run log even when a cycle did nothing |
| `LOG_RETENTION_DAYS` | `14` | Delete local run logs older than this |
| `DELETE_AFTER_UPLOAD` | `false` | Delete the local file once uploaded |

Set inside the container by the `Containerfile` (rarely changed): `DESTINATION_FOLDER`, `STATE_DIR`, `LOG_DIR`.

See `README.md` for the one-time Google Drive setup.

## Download parallelism

Songs are downloaded by `DOWNLOAD_WORKERS` threads in one container. A shared throttle keeps at least `DOWNLOAD_SLEEP_SECONDS` between song *starts* across all workers, so the gap, not the worker count, caps throughput: `songs × gap` is the minimum time for a cycle. Transient errors (HTTP 403/429/5xx, timeouts) are retried `DOWNLOAD_RETRIES` times; a song that still fails has its leftover files removed. Each cycle summary and run log shows the workers, gap and retry settings used and any retries done (per song, recovered or not).

Benchmark (38-song playlist, 33 downloadable, Drive off, one run each, Nov 2026):

| Workers | Gap | Time | Result |
| --- | --- | --- | --- |
| 1 (old behaviour) | 3 s | 273 s | 33 ok |
| 4 | 3 s | 115 s | 33 ok |
| 4 | 2 s (default) | 78 s | 33 ok, 0 retries needed |
| 4 | 1 s | 42 s | 32 ok, 1 HTTP 403 (before retries existed) |
| 8 | 1 s | 41 s | 33 ok |

The default is 4 workers and a 2 s gap (78 s for this playlist), a compromise between speed and the risk of YouTube rejecting requests at 1 s. Raise the gap if you see 403/429 errors in the run log. More than 4 workers gains nothing at these gaps.
