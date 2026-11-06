import yt_dlp
import os
import sys
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor

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


# Errors worth retrying: network hiccups and YouTube rejecting a request.
# Anything else (video removed, private, not available in your country) is
# permanent and is not retried.
TRANSIENT_ERRORS = (
    "HTTP Error 403", "HTTP Error 429", "HTTP Error 5", "timed out",
    "Connection reset", "Connection aborted", "Remote end closed",
    "IncompleteRead", "Temporary failure", "Unable to connect",
)
RETRY_BACKOFF_SECONDS = 5


def is_transient_error(exc):
    message = str(exc)
    return any(marker in message for marker in TRANSIENT_ERRORS)


def remove_leftover_files(directory, song_id, keep_format="m4a"):
    """Delete files a failed download left behind (.webp, .part, ...)."""
    if not os.path.isdir(directory):
        return []
    marker = f" - {song_id}."
    removed = []
    for name in os.listdir(directory):
        if marker in name and not name.endswith("." + keep_format):
            try:
                os.remove(os.path.join(directory, name))
                removed.append(name)
            except OSError as exc:
                log.warning("Could not remove leftover %s: %s", name, exc)
    return removed


def download_song(ydl_opts: dict, url: str, retries=None, sleep=None):
    """Download one song. Retries transient errors; returns True on success.

    After the last failed attempt, files left behind by the song are removed.
    """
    retries = config.download_retries() if retries is None else retries
    sleep = sleep or (lambda seconds: time.sleep(seconds))
    song_id = url.rsplit("=", 1)[-1]
    for attempt in range(retries + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download(url)
            return True
        except Exception as exc:
            if attempt < retries and is_transient_error(exc):
                delay = RETRY_BACKOFF_SECONDS * (attempt + 1)
                log.warning("Transient error downloading %s (attempt %d/%d), "
                            "retrying in %ds: %s", song_id, attempt + 1,
                            retries + 1, delay, exc)
                sleep(delay)
                continue
            log.error(
                "An error occurred during the download process: %s", exc)
            break
    directory = os.path.dirname(ydl_opts["outtmpl"]["default"])
    codec = ydl_opts["postprocessors"][0].get("preferredcodec", "m4a")
    for name in remove_leftover_files(directory, song_id, codec):
        log.info("Removed leftover file from failed download: %s", name)
    return False


class StartThrottle:
    """Keeps at least `gap` seconds between song starts across all workers."""

    def __init__(self, gap, clock=None, sleep=None):
        self.gap = gap
        # Looked up at call time so tests can patch time.sleep.
        self._clock = clock or (lambda: time.monotonic())
        self._sleep = sleep or (lambda seconds: time.sleep(seconds))
        self._lock = threading.Lock()
        self._next_start = None

    def wait(self):
        # Reserve the next start slot under the lock, sleep outside of it.
        with self._lock:
            now = self._clock()
            start = now if self._next_start is None else max(now, self._next_start)
            self._next_start = start + self.gap
        if start > now:
            self._sleep(start - now)


def download_all(ids, ydl_opts, workers=1, gap=3, stop_event=None,
                 downloader=None, throttle=None):
    """Download `ids` with a pool of worker threads pulling from one queue.

    Starts are spaced `gap` seconds apart across all workers. Songs not yet
    started are skipped once `stop_event` is set; songs in progress finish.
    Returns the list of ids that were actually attempted.
    """
    downloader = downloader or download_song
    throttle = throttle or StartThrottle(gap)
    ids = list(dict.fromkeys(ids))  # drop duplicates, keep order
    attempted = []
    lock = threading.Lock()

    def one(song_id):
        if stop_event is not None and stop_event.is_set():
            return
        throttle.wait()
        if stop_event is not None and stop_event.is_set():
            return
        with lock:
            attempted.append(song_id)
        log.info("Downloading %s", song_id)
        downloader(ydl_opts, f"https://www.youtube.com/watch?v={song_id}")

    with ThreadPoolExecutor(max_workers=max(1, workers),
                            thread_name_prefix="dl") as pool:
        for future in [pool.submit(one, i) for i in ids]:
            try:
                future.result()
            except Exception:
                log.exception("Unexpected error in download worker.")
    return attempted


def download_main(output_dir=None, urls=None, file_format="m4a", report=None,
                  stop_event=None):
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
    workers = config.download_workers()
    log.info("Starting downloads (%d worker(s), %ss between starts)...",
             workers, config.download_sleep_seconds())
    download_all(todo, ydl_opts, workers=workers,
                 gap=config.download_sleep_seconds(), stop_event=stop_event)

    after = drive_upload.local_song_ids(output_dir, file_format)
    report.downloaded = [n for i, n in after.items() if i not in before]
    report.download_failed = [i for i in todo if i not in after]
    log.info("Download finished: %d downloaded, %d failed.",
             len(report.downloaded), len(report.download_failed))
    return report


def run_cycle(output_dir=None, file_format="m4a", report=None, stop_event=None):
    """One full cycle: download new songs, then upload to Drive if enabled."""
    report = report or CycleReport()
    if output_dir is None:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, file_format)
    report.drive_enabled = config.drive_enabled()
    report.drive_songs_path = drive_upload.drive_path()
    report.drive_logs_path = drive_upload.drive_path("logs")

    download_main(output_dir, file_format=file_format, report=report,
                  stop_event=stop_event)
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
