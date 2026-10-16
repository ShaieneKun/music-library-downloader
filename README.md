# Music Library Downloader

A background service that mirrors a YouTube Music playlist as `m4a` files (with metadata and thumbnails embedded) and, optionally, uploads them to a folder in your personal Google Drive.

It runs as a Docker container, so it works the same on any Linux, macOS or Windows machine that has Docker (on Windows/macOS: Docker Desktop with Linux containers). The image is multi-arch friendly (x86_64 and ARM, e.g. Raspberry Pi / Apple Silicon).

## Quick start

```bash
cp .env.template .env        # then edit PLAYLIST_URL
docker compose up -d --build
docker compose logs -f
```

The container restarts automatically (`restart: unless-stopped`), checks the playlist every `INTERVAL_SECONDS` (default 1 hour) and only downloads songs it doesn't already have.

All persistent data lives in the `/data` volume:

| Path | Contents |
| --- | --- |
| `/data/songs` | downloaded `.m4a` files |
| `/data/state` | Google Drive token + record of what was uploaded |
| `/data/logs` | rotating `app.log` |

To browse songs on the host, change the volume in `compose.yaml` to `./data:/data`.

## Configuration (`.env`)

| Variable | Default | Description |
| --- | --- | --- |
| `PLAYLIST_URL` | built-in sample | One or more playlist URLs (space/comma separated) |
| `INTERVAL_SECONDS` | `3600` | Time between checks |
| `DRIVE_UPLOAD_ENABLED` | `false` | Upload new songs to Google Drive |
| `DRIVE_FOLDER_NAME` | `Music Library Downloader` | Folder in My Drive (`Music/Auto` creates nested folders) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | – | OAuth client, see below |
| `DELETE_AFTER_UPLOAD` | `false` | Delete the local file once uploaded |

## Google Drive setup (one time)

Service accounts have no storage quota on personal Drives, so the app signs in as *you* with OAuth. The login is done once, works on a headless server, and the app only gets the `drive.file` scope — it can see only the files/folders it created itself, not the rest of your Drive.

1. In [Google Cloud Console](https://console.cloud.google.com/) create a project and enable the **Google Drive API**.
2. **APIs & Services → OAuth consent screen**: configure it as *External*, add yourself as a test user, then **Publish app** (move it to *In production*). Do this: while the app is in *Testing*, Google expires refresh tokens after 7 days. Personal use of an unverified app is fine; you just click through a warning at login.
3. **Credentials → Create credentials → OAuth client ID**, application type **TVs and Limited Input devices**. Copy the client ID and secret into `.env`, and set `DRIVE_UPLOAD_ENABLED=true`.
4. Authorise (the container can be on a remote server; you open the link on any device):

   ```bash
   docker compose run --rm music-library-downloader python main.py auth
   ```

   Open the printed URL, enter the code, approve. The token is stored in the `/data/state` volume.
5. `docker compose up -d`. New songs are uploaded after each download cycle; songs already in `/data/songs` are uploaded too the first time.

## Commands

```bash
docker compose run --rm music-library-downloader python main.py once   # single cycle, then exit
docker compose run --rm music-library-downloader python main.py auth   # Google login
docker compose down                                                     # stop (data is kept)
```

## Running without Docker

Requires Python 3.14+, [uv](https://docs.astral.sh/uv/) and a system `ffmpeg` (`brew install ffmpeg`).

```bash
uv sync
uv run main.py once ./my-downloads
uv run python -m unittest discover -s src/tests -t .
```

## Notes

- Files are named `<title> - <uploader> - <video id>.m4a`; the video ID is how already-downloaded songs are recognised.
- If you delete a song from Drive, it is not re-uploaded (the upload is tracked in `/data/state/drive.json`). Delete that entry to force it.
- Respect YouTube's terms of service and copyright law; this is intended for personal use.
