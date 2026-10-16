import yt_dlp
import os
import sys
import logging
import time

from . import config
from . import drive_upload

DEFAULT_DOWNLOAD_DIR = "./auto-downloaded-songs"
FILENAME_FORMAT = "%(title)s - %(uploader)s - %(id)s.%(ext)s"

log = logging.getLogger(__name__)


def extract_ids_from_filenames(directory, file_format="m4a"):
    """Return the video IDs of songs already present in a directory."""
    return list(drive_upload.local_song_ids(directory, file_format))


def list_playlist_ids(urls):
    """Return all video IDs in the configured playlists."""
    ids = []
    opts = {"extract_flat": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:
                log.error("Could not list playlist %s: %s", url, exc)
                continue
            for entry in info.get("entries") or []:
                if entry and entry.get("id"):
                    ids.append(entry["id"])
    return ids


def filter_url_ids_to_donwload(output_dir, file_format, urls=None):
    """Return watch URLs for playlist songs not yet downloaded/uploaded."""
    log.info("Identifying new songs to download...")
    all_ids = list_playlist_ids(urls or config.playlist_urls())

    already = set(extract_ids_from_filenames(output_dir, file_format))
    # Songs uploaded to Drive and then deleted locally must not come back.
    already |= drive_upload.uploaded_ids()

    to_download = [i for i in all_ids if i not in already]
    log.info("Playlist: %d songs, %d already have, %d to download",
             len(all_ids), len(already & set(all_ids)), len(to_download))
    return [f"https://www.youtube.com/watch?v={i}" for i in to_download]


def download_main(output_dir=None, urls=None, file_format="m4a"):
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)

    os.makedirs(output_dir, exist_ok=True)

    urls = filter_url_ids_to_donwload(output_dir, file_format, urls)
    if not urls:
        log.info("No new songs to download.")
        return

    outtmpl = os.path.join(output_dir, FILENAME_FORMAT)

    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'writethumbnail': True,
        'embedthumbnail': True,
        'outtmpl': {
            'default': outtmpl,
            'pl_thumbnail': ''
        },
        # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [
            # Don't change postprocessors order, othewise metadata or thumbnail mail fail to be embedded
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file_format,
                'preferredquality': 'best',
            },
            {
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
                'add_infojson': 'if_exists',
            },
            {
                # Leave this as the last item on the dict
                'key': 'EmbedThumbnail',
            },
        ]
    }

    log.info("Starting downloads...\n")
    for url in urls:
        time.sleep(3)
        download_song(ydl_opts, url)

    log.info("\nDownload finished!\n")


def download_song(ydl_opts: dict, url: str):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download(url)
        except Exception as exc:
            log.error(
                "An error occurred during the download process: %s", exc)


def main(output_dir=None):
    download_main(output_dir)
    if config.drive_enabled():
        drive_upload.upload_new_songs(
            output_dir or os.path.join(DEFAULT_DOWNLOAD_DIR, "m4a"))


def usage():
    log.info("Usage: python download_songs.py <output_directory>")


if __name__ == '__main__':
    options = sys.argv
    if len(options) == 1:
        main()
    elif len(options) == 2:
        main(options[1])
    else:
        usage()
