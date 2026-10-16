"""Runtime configuration, read from environment variables."""
import os

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


def state_dir(env=None):
    env = os.environ if env is None else env
    return os.path.expanduser(env.get("STATE_DIR") or "./state")


def drive_enabled(env=None):
    env = os.environ if env is None else env
    return _bool(env.get("DRIVE_UPLOAD_ENABLED"))


def drive_folder_name(env=None):
    env = os.environ if env is None else env
    return env.get("DRIVE_FOLDER_NAME") or "Music Library Downloader"


def delete_after_upload(env=None):
    env = os.environ if env is None else env
    return _bool(env.get("DELETE_AFTER_UPLOAD"))
