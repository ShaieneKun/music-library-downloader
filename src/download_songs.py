import yt_dlp
import re
import os
import sys
import subprocess
import logging
import time

PLAYLIST_URL = [
    # "https://music.youtube.com/browse/VLPL1Fdfnmz532d3N5F-LoMCzAEkUhKctMY7",
    "https://music.youtube.com/playlist?list=PL1Fdfnmz532fUiMPemHsxmyAyCJISoD9P"
]
DEFAULT_DOWNLOAD_DIR = "./auto-downloaded-songs"
FILENAME_FORMAT = "%(title)s - %(uploader)s - %(id)s.%(ext)s"

log = logging.getLogger(__name__)


def extract_ids_from_filenames(directory, file_format="m4a"):
    """
    Extracts IDs from already downloaded files to filenames in a directory.

    Args:
        directory (str): The path to the directory.

    Returns:
        list: A list of extracted IDs.
    """

    ids = []
    try:
        for filename in os.listdir(directory):
            # improved regex
            match = re.search(
                r'- (?P<id>[^-]+)\.{}$'.format(file_format), filename)
            if match:
                extracted_id = match.group('id')
                ids.append(extracted_id)
        return ids
    except FileNotFoundError:
        log.info(f"Error: Directory '{directory}' not found.8")
        return []
    except Exception as e:
        log.info(f"An unexpected error occurred: {e}")
        return []


def filter_url_ids_to_donwload(output_dir, file_format):
    """
    Checks if there are any already downloaded files.
    If there are, removes them from the list of ids to download.
    """
    log.info("\nIdentifying already downloaded songs, and new songs to download...\n")
    log.info("Identifying new songs to download...")

    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--flat-playlist",
        "-O",
        "id",
        "--no-warnings",
    ] + PLAYLIST_URL
    result = subprocess.run(command, capture_output=True, text=True)
    all_ids_to_downlaod = result.stdout.strip().splitlines()

    if result.returncode != 0:
        log.error(
            "yt-dlp failed while listing playlist IDs: %s",
            result.stderr.strip() or "<no stderr>"
        )

    log.info("Identifying already downloaded songs...\n")
    already_downloaded_ids = extract_ids_from_filenames(
        output_dir, file_format)

    id_subset_to_download = set(all_ids_to_downlaod) - \
        set(already_downloaded_ids)

    ids = [
        f"https://www.youtube.com/watch?v={id}" for id in id_subset_to_download]

    log.info("All IDs to download: %s", all_ids_to_downlaod)
    log.info("Already downloaded IDs: %s", already_downloaded_ids)
    log.info("IDs that will be downloaded: %s", id_subset_to_download)

    return ids


def download(output_dir=None, urls=PLAYLIST_URL, file_format="m4a"):
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)

    os.makedirs(output_dir, exist_ok=True)

    urls = filter_url_ids_to_donwload(output_dir, file_format=file_format)
    if not urls:
        log.info("No new songs to download.")
        return

    outtmpl = os.path.join(output_dir, FILENAME_FORMAT)

    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        # 'ffmpeg_location': './',
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
        time.sleep(5)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                error_code = ydl.download(url)
            except Exception as exc:
                log.error(
                    "An error occurred during the download process: %s", exc)

    log.info("\nDownload finished!\n")


def main(output_dir=None):
    download(output_dir)


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
