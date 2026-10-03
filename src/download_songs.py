import argparse
import logging
import os
import re
import time

import yt_dlp

DEFAULT_PLAYLIST_URLS = [
    "https://music.youtube.com/playlist?list=PL1Fdfnmz532fUiMPemHsxmyAyCJISoD9P"
]
DEFAULT_DOWNLOAD_DIR = "./auto-downloaded-songs"
DEFAULT_FILE_FORMAT = "m4a"
FILENAME_FORMAT = "%(title)s - %(uploader)s - %(id)s.%(ext)s"
SECONDS_BETWEEN_DOWNLOADS = 3

# YouTube video IDs are exactly 11 characters from [A-Za-z0-9_-]
VIDEO_ID_PATTERN = r'[A-Za-z0-9_-]{11}'

log = logging.getLogger(__name__)


def playlist_urls_from_env(env=None):
    """
    Reads playlist URLs from the PLAYLIST_URLS env var (comma or whitespace
    separated), falling back to DEFAULT_PLAYLIST_URLS.
    """
    env = os.environ if env is None else env
    raw = env.get('PLAYLIST_URLS', '')
    urls = [url for url in re.split(r'[,\s]+', raw) if url]
    return urls or list(DEFAULT_PLAYLIST_URLS)


def extract_ids_from_filenames(directory, file_format=DEFAULT_FILE_FORMAT):
    """
    Extracts video IDs from the filenames of already downloaded files.

    Args:
        directory (str): The path to the directory.
        file_format (str): The audio file extension to look for.

    Returns:
        set: The extracted IDs.
    """
    pattern = re.compile(
        r'- (?P<id>{})\.{}$'.format(VIDEO_ID_PATTERN, re.escape(file_format)))

    try:
        filenames = os.listdir(directory)
    except FileNotFoundError:
        log.warning("Directory '%s' not found.", directory)
        return set()

    ids = set()
    for filename in filenames:
        match = pattern.search(filename)
        if match:
            ids.add(match.group('id'))
    return ids


def fetch_playlist_ids(playlist_urls):
    """Lists the video IDs of every playlist without downloading anything."""
    ids = []
    with yt_dlp.YoutubeDL({'extract_flat': True, 'quiet': True, 'no_warnings': True}) as ydl:
        for playlist_url in playlist_urls:
            try:
                info = ydl.extract_info(playlist_url, download=False)
            except yt_dlp.utils.DownloadError as exc:
                log.error("Failed to list playlist %s: %s", playlist_url, exc)
                continue
            ids.extend(entry['id'] for entry in info.get('entries') or [] if entry)
    return ids


def filter_urls_to_download(output_dir, playlist_urls, file_format):
    """
    Returns the video URLs from the playlists that have not been downloaded yet.
    """
    log.info("Identifying new songs to download...")
    all_ids = fetch_playlist_ids(playlist_urls)

    log.info("Identifying already downloaded songs...")
    already_downloaded_ids = extract_ids_from_filenames(output_dir, file_format)

    ids_to_download = [id for id in dict.fromkeys(all_ids)
                       if id not in already_downloaded_ids]

    log.info("Playlist IDs: %d, already downloaded: %d, to download: %d",
             len(set(all_ids)), len(already_downloaded_ids), len(ids_to_download))
    log.debug("IDs that will be downloaded: %s", ids_to_download)

    return [f"https://www.youtube.com/watch?v={id}" for id in ids_to_download]


def build_ydl_opts(output_dir, file_format):
    return {
        'format': f'{file_format}/bestaudio/best',
        'writethumbnail': True,
        'embedthumbnail': True,
        'outtmpl': {
            'default': os.path.join(output_dir, FILENAME_FORMAT),
            'pl_thumbnail': ''
        },
        # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [
            # Don't change postprocessors order, otherwise metadata or thumbnail may fail to be embedded
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file_format,
            },
            {
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
                'add_infojson': 'if_exists',
            },
            {
                # Leave this as the last item on the list
                'key': 'EmbedThumbnail',
            },
        ]
    }


def download_main(output_dir=None, playlist_urls=None, file_format=DEFAULT_FILE_FORMAT):
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)
    if playlist_urls is None:
        playlist_urls = playlist_urls_from_env()

    os.makedirs(output_dir, exist_ok=True)

    urls = filter_urls_to_download(output_dir, playlist_urls, file_format)
    if not urls:
        log.info("No new songs to download.")
        return

    log.info("Starting downloads...")
    with yt_dlp.YoutubeDL(build_ydl_opts(output_dir, file_format)) as ydl:
        for url in urls:
            time.sleep(SECONDS_BETWEEN_DOWNLOADS)
            try:
                ydl.download([url])
            except Exception as exc:
                log.error("Failed to download %s: %s", url, exc)

    log.info("Download finished!")


def main(output_dir=None):
    download_main(output_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Download new songs from the configured playlists once.")
    parser.add_argument('output_dir', nargs='?', help="Directory to save songs to.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    main(args.output_dir)
