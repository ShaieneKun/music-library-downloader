# Architecture

A long-running service that mirrors YouTube Music playlists as `m4a` files and optionally uploads them to Google Drive.

## Modules

| File | Responsibility |
| --- | --- |
| `main.py` | CLI entry point. Commands `run` (loop forever, default), `once` (single cycle), `auth` (Google login). Sets up logging and handles SIGTERM/SIGINT for graceful stop. |
| `src/config.py` | Reads all runtime configuration from environment variables (playlist URLs, interval, state dir, Drive settings). |
| `src/download_songs.py` | Lists playlist IDs with yt-dlp, skips songs already present locally or already uploaded, downloads the rest as `m4a` with metadata and thumbnail embedded. |
| `src/drive_upload.py` | Google Drive upload using the OAuth "limited input device" flow and the narrow `drive.file` scope. Keeps its token and upload record in `STATE_DIR/drive.json`. |
| `src/report.py` | `CycleReport`: per-cycle summary (found / skipped / downloaded / failed / uploaded) printed at the end of each run and written to the cycle log. |
| `src/updater.py` | Upgrades `yt-dlp` at startup and periodically (YouTube breaks old versions), restarting the service when a new version was installed. |
| `src/setup_ffmpeg.py` | Checks that `ffmpeg` and `ffprobe` are on PATH and exits with an error if not. |
| `src/tests/` | `unittest` test suite. |

## Cycle

1. `download_songs.main` lists the IDs in every playlist in `PLAYLIST_URL`.
2. It subtracts IDs found in filenames in the songs directory. With `SKIP_DOWNLOAD_IF_UPLOADED=true` it also subtracts IDs recorded as uploaded in `drive.json` (so songs uploaded then deleted locally do not come back); by default they are downloaded again.
3. Each remaining song is downloaded (3 s pause between songs).
4. If `DRIVE_UPLOAD_ENABLED` is true, local songs not yet recorded in `drive.json` are uploaded (never uploaded twice, regardless of the setting above); with `DELETE_AFTER_UPLOAD` the local copy is removed.
5. A `CYCLE SUMMARY` block is logged and a DEBUG run log (`cycle-<timestamp>.log` in `LOG_DIR`) is written; with Drive enabled it is uploaded to a `logs` subfolder of the Drive folder. Idle cycles are discarded unless `LOG_KEEP_IDLE=true`; logs older than `LOG_RETENTION_DAYS` are deleted.
6. `run` sleeps `INTERVAL_SECONDS` and repeats. An exception in one cycle is logged and does not stop the loop.

## Conventions

- Files are named `<title> - <uploader> - <video id>.m4a`. The 11-character video ID at the end is how already-downloaded songs are recognised; do not change the naming without updating `drive_upload.ID_RE`.
- The songs directory is resolved as: `DESTINATION_FOLDER` env var, else the CLI argument, else `./auto-downloaded-songs/m4a`.
- Configuration is read from the environment at call time (functions take an optional `env` dict to make them testable).
