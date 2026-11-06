import yt_dlp
import os
import sys
import logging
import time

from . import config
from . import drive_upload
from .report import CycleReport

DEFAULT_DOWNLOAD_DIR = "./auto-downloaded-songs"
FILENAME_FORMAT = "%(title)s - %(uploader)s - %(id)s.%(ext)s"

log = logging.getLogger(__name__)
# yt-dlp output goes through logging so it ends up in the run's debug log.
ytdlp_log = logging.getLogger("yt_dlp")


def extract_ids_from_filenames(directory, file_format="m4a"):
    """Return the video IDs of songs already present in a directory."""
    return list(drive_upload.local_song_ids(directory, file_format))


def list_playlist_ids(urls):
    """Return all video IDs in the configured playlists."""
    ids = []
    opts = {"extract_flat": True, "quiet": True, "no_warnings": True,
            "logger": ytdlp_log}
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


def split_playlist_ids(all_ids, output_dir, file_format):
    """Split playlist ids into (already_have, to_download)."""
    have = set(extract_ids_from_filenames(output_dir, file_format))
    # Opt-in: songs uploaded to Drive and then deleted locally do not come
    # back. By default they are downloaded again (but never re-uploaded).
    if config.skip_download_if_uploaded():
        have |= drive_upload.uploaded_ids()
    already = [i for i in all_ids if i in have]
    todo = [i for i in all_ids if i not in have]
    return already, todo


def filter_url_ids_to_donwload(output_dir, file_format, urls=None):
    """Return watch URLs for playlist songs not yet downloaded/uploaded."""
    all_ids = list_playlist_ids(urls or config.playlist_urls())
    _, todo = split_playlist_ids(all_ids, output_dir, file_format)
    return [f"https://www.youtube.com/watch?v={i}" for i in todo]


def _ydl_opts(output_dir, file_format):
    return {
        'format': 'm4a/bestaudio/best',
        'writethumbnail': True,
        'embedthumbnail': True,
        'logger': ytdlp_log,
        'noprogress': True,
        'outtmpl': {
            'default': os.path.join(output_dir, FILENAME_FORMAT),
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


def download_song(ydl_opts: dict, url: str):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download(url)
        except Exception as exc:
            log.error(
                "An error occurred during the download process: %s", exc)


def download_main(output_dir=None, urls=None, file_format="m4a", report=None):
    """Download new songs. Fills `report` (a CycleReport) as it goes."""
    report = report or CycleReport()
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)
    os.makedirs(output_dir, exist_ok=True)
    report.download_dir = os.path.abspath(output_dir)
    report.host_download_dir = config.host_music_dir()
    log.info("Download directory: %s",
             report.host_download_dir or report.download_dir)

    log.info("Identifying new songs to download...")
    all_ids = list_playlist_ids(urls or config.playlist_urls())
    already, todo = split_playlist_ids(all_ids, output_dir, file_format)
    report.playlist_total = len(all_ids)
    report.already_downloaded = already
    report.to_download = todo
    log.info("Playlist: %d songs | already downloaded: %d | to download: %d",
             len(all_ids), len(already), len(todo))
    log.debug("To download: %s", todo)

    if not todo:
        log.info("No new songs to download.")
        return report

    before = drive_upload.local_song_ids(output_dir, file_format)
    ydl_opts = _ydl_opts(output_dir, file_format)
    log.info("Starting downloads...")
    for song_id in todo:
        time.sleep(3)
        log.info("Downloading %s", song_id)
        download_song(ydl_opts, f"https://www.youtube.com/watch?v={song_id}")

    after = drive_upload.local_song_ids(output_dir, file_format)
    report.downloaded = [n for i, n in after.items() if i not in before]
    report.download_failed = [i for i in todo if i not in after]
    log.info("Download finished: %d downloaded, %d failed.",
             len(report.downloaded), len(report.download_failed))
    return report


def run_cycle(output_dir=None, file_format="m4a", report=None):
    """One full cycle: download new songs, then upload to Drive if enabled."""
    report = report or CycleReport()
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)
    report.drive_enabled = config.drive_enabled()
    report.drive_songs_path = drive_upload.drive_path()
    report.drive_logs_path = drive_upload.drive_path("logs")

    download_main(output_dir, file_format=file_format, report=report)
    if report.drive_enabled:
        log.info("Google Drive songs path: %s", report.drive_songs_path)
        report.uploaded, report.upload_failed = drive_upload.upload_new_songs(
            output_dir, file_format)
    return report


def main(output_dir=None):
    return run_cycle(output_dir)


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
