# Music Library Downloader

A simple Python application that downloads songs from a configured YouTube Music playlist and converts them to `m4a` audio files.

## Overview

This project uses `yt-dlp` to fetch playlist items and download audio from YouTube Music. It requires a system-installed `ffmpeg` package so audio extraction and metadata embedding can run using the system `ffmpeg` executable.

## Features

- Downloads audio from a configured YouTube Music playlist
- Converts downloaded audio to `m4a` using `ffmpeg`
- Embeds metadata and thumbnails into the audio files
- Avoids re-downloading already downloaded songs
- Stores logs in the `logs/` directory

## Requirements

- Python 3.12 or newer
- Network access to download playlist information
- `yt-dlp` Python package

## Installation

1. Clone or download the repository.
2. Create and activate a Python environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

> If `requirements.txt` is not present, install directly:
>
> ```bash
> python -m pip install yt-dlp

Run the main script from the repository root:

```bash
python main.py
```

To specify an output directory for downloaded files:

```bash
python main.py ./my-downloads
```

If no output directory is provided, downloads will go to:

```text
./auto-downloaded-songs/m4a
```

Use Docker to build and then run an interactive shell.

```bash
docker build -t musiclibrarydownloader:latest -f Containerfile .
docker run --rm -it --entrypoint /bin/bash musiclibrarydownloader:latest
```

## Configuration

The playlist URL is defined in `src/download_songs.py` under `PLAYLIST_URL`.

Update this value to download from your own playlist:

```python
PLAYLIST_URL = [
    "https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
]
```

## FFmpeg setup

The application requires a system-installed `ffmpeg` package. Make sure `ffmpeg` and `ffprobe` are available on your `PATH` before running the app.

On Debian/Ubuntu:

```bash
sudo apt update && sudo apt install ffmpeg
```

## Output

Downloaded songs are saved with the following filename format:

```text
<song title> - <uploader> - <video id>.m4a
```

## Logs

Execution logs are written to the `logs/` directory with timestamped filenames.

## Notes

- The current playlist URL is set to a YouTube Music playlist and may need to be updated for your own library.
- The app is primarily targeted at Linux environments because it relies on the system `ffmpeg` package.

## License

This project is provided as-is for personal use.
