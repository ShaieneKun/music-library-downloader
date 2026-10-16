"""Upload downloaded songs to the user's personal Google Drive.

Uses the OAuth "limited input device" flow so that authorisation can be done
once on a headless server, and the narrow `drive.file` scope, so the app can
only see files and folders it created itself.
"""
import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

log = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/drive.file"
DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
FOLDER_MIME = "application/vnd.google-apps.folder"
AUDIO_MIME = {"m4a": "audio/mp4"}
ID_RE = r"- (?P<id>[\w-]{11})\.%s$"


def _state_path():
    return os.path.join(config.state_dir(), "drive.json")


def load_state():
    try:
        with open(_state_path()) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_state(state):
    os.makedirs(config.state_dir(), exist_ok=True)
    tmp = _state_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, _state_path())


def _post(url, data):
    req = urllib.request.Request(
        url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        return json.load(exc)


def _client_credentials(env=None):
    env = os.environ if env is None else env
    client_id = env.get("GOOGLE_CLIENT_ID")
    client_secret = env.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set "
            "(see README: Google Drive setup).")
    return client_id, client_secret


def authorize():
    """Interactive one-time login (device flow). Stores a refresh token."""
    client_id, client_secret = _client_credentials()
    dev = _post(DEVICE_CODE_URL, {"client_id": client_id, "scope": SCOPE})
    if "device_code" not in dev:
        raise RuntimeError(f"Could not start device login: {dev}")

    print(f"\nOpen {dev['verification_url']} on any device and enter the code:"
          f"\n\n    {dev['user_code']}\n\nWaiting for approval...", flush=True)

    interval = int(dev.get("interval", 5))
    deadline = time.time() + int(dev.get("expires_in", 1800))
    while time.time() < deadline:
        time.sleep(interval)
        tok = _post(TOKEN_URL, {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        })
        err = tok.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err:
            raise RuntimeError(f"Authorisation failed: {tok}")
        state = load_state()
        state["refresh_token"] = tok["refresh_token"]
        save_state(state)
        print("Google Drive authorised. You can now start the container.")
        return
    raise RuntimeError("Login code expired; run the auth command again.")


def _service(state):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if "refresh_token" not in state:
        raise RuntimeError(
            "Google Drive is not authorised yet. Run the `auth` command "
            "(see README).")
    client_id, client_secret = _client_credentials()
    creds = Credentials(
        None,
        refresh_token=state["refresh_token"],
        token_uri=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[SCOPE],
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _escape(name):
    return name.replace("\\", "\\\\").replace("'", "\\'")


def _ensure_folder(service, state, path):
    """Return the Drive folder id for `path` (a/b/c), creating it if needed."""
    cached = state.get("folder")
    if cached and cached.get("path") == path:
        try:
            meta = service.files().get(
                fileId=cached["id"], fields="id,trashed").execute(num_retries=3)
            if not meta.get("trashed"):
                return cached["id"]
        except Exception:
            log.warning("Cached Drive folder is gone, recreating it.")

    parent = "root"
    for part in [p for p in path.split("/") if p]:
        q = (f"name = '{_escape(part)}' and mimeType = '{FOLDER_MIME}' "
             f"and '{parent}' in parents and trashed = false")
        found = service.files().list(
            q=q, fields="files(id)", pageSize=1).execute(num_retries=3)
        if found["files"]:
            parent = found["files"][0]["id"]
        else:
            created = service.files().create(
                body={"name": part, "mimeType": FOLDER_MIME, "parents": [parent]},
                fields="id").execute(num_retries=3)
            parent = created["id"]
    state["folder"] = {"path": path, "id": parent}
    save_state(state)
    return parent


def local_song_ids(directory, file_format="m4a"):
    """Map video id -> filename for songs present in `directory`."""
    found = {}
    if not os.path.isdir(directory):
        return found
    pattern = re.compile(ID_RE % re.escape(file_format))
    for name in os.listdir(directory):
        m = pattern.search(name)
        if m:
            found[m.group("id")] = name
    return found


def uploaded_ids():
    return set(load_state().get("uploaded", {}))


def upload_new_songs(directory, file_format="m4a"):
    """Upload every local song not yet uploaded. Returns number uploaded."""
    from googleapiclient.http import MediaFileUpload

    state = load_state()
    done = state.setdefault("uploaded", {})
    pending = {i: n for i, n in local_song_ids(directory, file_format).items()
               if i not in done}
    if not pending:
        log.info("Drive: nothing new to upload.")
        return 0

    service = _service(state)
    folder_id = _ensure_folder(service, state, config.drive_folder_name())
    count = 0
    for song_id, name in pending.items():
        full = os.path.join(directory, name)
        log.info("Drive: uploading %s", name)
        try:
            media = MediaFileUpload(
                full, mimetype=AUDIO_MIME.get(file_format, "application/octet-stream"),
                resumable=True)
            created = service.files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media, fields="id").execute(num_retries=5)
        except Exception as exc:
            log.error("Drive: failed to upload %s: %s", name, exc)
            continue
        done[song_id] = created["id"]
        save_state(state)
        count += 1
        if config.delete_after_upload():
            os.remove(full)
    log.info("Drive: uploaded %d song(s).", count)
    return count
