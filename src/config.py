"""Runtime configuration, read from environment variables."""
import os
import socket

DEFAULT_PLAYLIST_URL = "https://music.youtube.com/playlist?list=PL1Fdfnmz532fUiMPemHsxmyAyCJISoD9P"


def _bool(value, default=False):
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def playlist_urls(env=None):
    env = os.environ if env is None else env
    raw = env.get("PLAYLIST_URL") or DEFAULT_PLAYLIST_URL
    return [u.strip() for u in raw.replace(",", " ").split() if u.strip()]


def interval_seconds(env=None):
    env = os.environ if env is None else env
    return int(env.get("INTERVAL_SECONDS") or 3600)


def auto_update_enabled(env=None):
    env = os.environ if env is None else env
    return _bool(env.get("YTDLP_AUTO_UPDATE"), default=True)


def update_interval_seconds(env=None):
    env = os.environ if env is None else env
    return int(env.get("YTDLP_UPDATE_INTERVAL_SECONDS") or 86400)


def log_keep_idle(env=None):
    """Keep/upload run logs even when nothing happened in the cycle."""
    env = os.environ if env is None else env
    return _bool(env.get("LOG_KEEP_IDLE"))


def log_retention_days(env=None):
    env = os.environ if env is None else env
    return int(env.get("LOG_RETENTION_DAYS") or 14)


def state_dir(env=None):
    env = os.environ if env is None else env
    return os.path.expanduser(env.get("STATE_DIR") or "./state")


def drive_enabled(env=None):
    env = os.environ if env is None else env
    return _bool(env.get("DRIVE_UPLOAD_ENABLED"))


def drive_folder_name(env=None):
    env = os.environ if env is None else env
    return env.get("DRIVE_FOLDER_NAME") or "Music Library Downloader"


def hostname(env=None):
    """Name of the machine running the app.

    Inside a container `socket.gethostname()` is the container id, so compose
    passes the real host name in as HOST_HOSTNAME when it is available.
    """
    env = os.environ if env is None else env
    return env.get("HOST_HOSTNAME") or socket.gethostname()


def host_music_dir(env=None):
    """Songs directory as seen on the host (set by compose from MUSIC_DIR).

    Only used for display: inside a container the songs path is the mount
    point (/data/songs), which means nothing to the user.
    """
    env = os.environ if env is None else env
    return env.get("HOST_MUSIC_DIR") or ""


def skip_download_if_uploaded(env=None):
    """If true, songs already uploaded to Drive are not downloaded again."""
    env = os.environ if env is None else env
    return _bool(env.get("SKIP_DOWNLOAD_IF_UPLOADED"))


def delete_after_upload(env=None):
    env = os.environ if env is None else env
    return _bool(env.get("DELETE_AFTER_UPLOAD"))


def download_workers(env=None):
    """Number of songs downloaded in parallel (minimum 1)."""
    env = os.environ if env is None else env
    return max(1, int(env.get("DOWNLOAD_WORKERS") or 4))


def download_sleep_seconds(env=None):
    """Minimum gap between song download starts, across all workers."""
    env = os.environ if env is None else env
    return max(0.0, float(env.get("DOWNLOAD_SLEEP_SECONDS") or 2))


def download_retries(env=None):
    """Extra attempts for a song after a transient download error."""
    env = os.environ if env is None else env
    return max(0, int(env.get("DOWNLOAD_RETRIES") or 2))
