import yt_dlp
import re
import os
import sys
import subprocess
import logging

PLAYLIST_URL = [
    "https://music.youtube.com/browse/VLPL1Fdfnmz532d3N5F-LoMCzAEkUhKctMY7"]
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
            match = re.search(r'- (?P<id>[^-]+)\.{}$'.format(file_format), filename)
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
    Checks if there are any already downloaded files
    If there are, remove them from the list of ids to download
    """
    log.info("\nIdentifying already downloaded songs, and new songs to download...\n")
    log.info("Identifying new songs to download...")

    command = ["yt-dlp", "--log.info", "id", "--no-warnings"] + PLAYLIST_URL
    result = subprocess.run(command, capture_output=True, text=True)
    all_ids_to_downlaod = result.stdout.strip().splitlines()

    log.info("Identifying already downloaded songs...\n")
    already_downloaded_ids = extract_ids_from_filenames(output_dir, file_format)

    id_subset_to_download = set(all_ids_to_downlaod) - \
        set(already_downloaded_ids)

    ids = [
        f"https://www.youtube.com/watch?v={id}" for id in id_subset_to_download]

    log.info("All IDs to download: ", all_ids_to_downlaod)
    log.info("Already downloaded IDs: ", already_downloaded_ids)
    log.info("IDs that will be downloaded: ", id_subset_to_download)

    return ids


def download(output_dir=None, urls=PLAYLIST_URL, file_format="m4a"):
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)
    # output_dir_formatted = os.path.join(output_dir, FILENAME_FORMAT)

    urls = filter_url_ids_to_donwload(output_dir, file_format=file_format)
    outtmpl = os.path.join(output_dir, FILENAME_FORMAT)

    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'ffmpeg_location': './',
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

    log.info("Starting donwload...\n")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            error_code = ydl.download(urls)
        except:
            log.info("An error occurred during the download process.")

    log.info("\nDonwload finished! 😁\n")


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
