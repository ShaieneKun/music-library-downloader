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
| `YTDLP_AUTO_UPDATE` | `true` | Upgrade `yt-dlp` at startup and periodically; restarts itself after an upgrade |
| `YTDLP_UPDATE_INTERVAL_SECONDS` | `86400` | Time between update checks |
| `LOG_KEEP_IDLE` | `false` | Keep (and upload) the run log even when a cycle did nothing |
| `LOG_RETENTION_DAYS` | `14` | Delete local run logs older than this |
| `DELETE_AFTER_UPLOAD` | `false` | Delete the local file once uploaded |

Set inside the container by the `Containerfile` (rarely changed): `DESTINATION_FOLDER`, `STATE_DIR`, `LOG_DIR`.

See `README.md` for the one-time Google Drive setup.
