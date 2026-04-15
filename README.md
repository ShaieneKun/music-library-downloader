# Music Library Downloader

A simple Python application that downloads songs from a configured YouTube Music playlist and converts them to `m4a` audio files.

## Overview

This project uses `yt-dlp` to fetch playlist items and download audio from YouTube Music. It also includes a setup helper to download a portable `ffmpeg` binary so audio extraction and metadata embedding can run without requiring a system-wide `ffmpeg` install.

## Features

- Downloads audio from a configured YouTube Music playlist
- Converts downloaded audio to `m4a` using `ffmpeg`
- Embeds metadata and thumbnails into the audio files
- Avoids re-downloading already downloaded songs
- Stores logs in the `logs/` directory

## Requirements

- Python 3.12 or newer
- Network access to download playlist information and FFmpeg
- `requests` and `yt-dlp` Python packages

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
> python -m pip install requests yt-dlp
> ```

## Usage

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

## Configuration

The playlist URL is defined in `src/download_songs.py` under `PLAYLIST_URL`.

Update this value to download from your own playlist:

```python
PLAYLIST_URL = [
    "https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID"
]
```

## FFmpeg setup

The application automatically downloads a portable `ffmpeg` build when first run via `src/setup_ffmpeg.py`.

If the binary is already present, the setup step is skipped.

## Output

Downloaded songs are saved with the following filename format:

```text
<song title> - <uploader> - <video id>.m4a
```

## Logs

Execution logs are written to the `logs/` directory with timestamped filenames.

## Notes

- The current playlist URL is set to a YouTube Music playlist and may need to be updated for your own library.
- The app is primarily targeted at Linux environments because the bundled FFmpeg binary is downloaded for Linux64.

## License

This project is provided as-is for personal use.
