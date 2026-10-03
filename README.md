# Music Library Downloader

A small Python application that keeps a local folder in sync with one or more YouTube Music playlists, saving each song as an `m4a` file with embedded metadata and cover art.

## Features

- Downloads audio from configurable YouTube Music playlists using `yt-dlp`
- Converts audio to `m4a` and embeds metadata and thumbnails using `ffmpeg`
- Skips songs that are already in the output folder (delete a file to download it again)
- Runs periodically (hourly by default), or once with `--once`
- Stores logs in the `logs/` directory

## Requirements

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)
- `ffmpeg` and `ffprobe` on your `PATH`

On macOS:

```bash
brew install uv ffmpeg
```

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install ffmpeg
```

## Usage

Install dependencies and run from the repository root:

```bash
uv sync
uv run main.py
```

Options:

```text
uv run main.py [output_dir] [--once] [--interval SECONDS]
```

- `output_dir`: where to save songs. Defaults to `./auto-downloaded-songs/m4a`.
- `--once`: run a single download pass and exit.
- `--interval`: seconds between runs. Defaults to `DOWNLOAD_INTERVAL_SECONDS` or 3600.

## Configuration

Copy `.env.template` to `.env` and fill in what you need. When running locally, export the variables in your shell. Docker Compose loads `.env` automatically.

| Variable | Description |
| --- | --- |
| `DESTINATION_FOLDER` | Output directory. Takes priority over the `output_dir` argument. |
| `PLAYLIST_URLS` | Playlists to sync, separated by commas or whitespace. Defaults to `DEFAULT_PLAYLIST_URLS` in `src/download_songs.py`. |
| `DOWNLOAD_INTERVAL_SECONDS` | Seconds between runs. Defaults to 3600. |

## Docker

```bash
cp .env.template .env
docker compose up -d --build
```

Songs are saved to `./auto-downloaded-songs` and logs to `./logs` on the host. The container runs as UID 5678, so make sure those folders are writable by that user.

To debug in the container, run `docker compose -f compose.debug.yaml up` and attach a debugger to port 5678.

## Output

Downloaded songs are saved with the following filename format:

```text
<song title> - <uploader> - <video id>.m4a
```

The video ID at the end of the filename is how the app recognises songs it already downloaded, so don't rename the files.

## Development

```bash
uv run pytest
```

## License

This project is provided as-is for personal use.
