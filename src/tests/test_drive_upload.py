import os
import tempfile
import unittest
from unittest import mock

from src import config, drive_upload


class LocalSongIdsTests(unittest.TestCase):
    def test_ids_containing_dashes_are_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ["Song - Artist - ab-cdefghi_.m4a",
                         "Other - Band - xyzXYZ12345.m4a",
                         "notes.txt"]:
                open(os.path.join(d, name), "w").close()
            ids = drive_upload.local_song_ids(d)
        self.assertEqual(set(ids), {"ab-cdefghi_", "xyzXYZ12345"})

    def test_missing_directory_returns_empty(self):
        self.assertEqual(drive_upload.local_song_ids("/nonexistent"), {})


class ConfigTests(unittest.TestCase):
    def test_playlist_urls_split_on_space_and_comma(self):
        env = {"PLAYLIST_URL": "https://a, https://b https://c"}
        self.assertEqual(config.playlist_urls(env),
                         ["https://a", "https://b", "https://c"])

    def test_drive_disabled_by_default(self):
        self.assertFalse(config.drive_enabled({}))
        self.assertTrue(config.drive_enabled({"DRIVE_UPLOAD_ENABLED": "true"}))


class FakeRequest:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def execute(self, num_retries=0):
        if self.error:
            raise self.error
        return self.result


class FakeFiles:
    """Minimal stand-in for the Drive v3 `files()` resource."""

    def __init__(self, existing=None):
        self.existing = existing or {}  # (name, parent) -> id
        self.created = []
        self.trashed = {}
        self.missing = set()

    def list(self, q, fields, pageSize):
        name = q.split("name = '")[1].split("' and")[0].replace("\\'", "'")
        parent = q.split("and '")[1].split("' in parents")[0]
        found = self.existing.get((name, parent))
        return FakeRequest({"files": [{"id": found}] if found else []})

    def create(self, body, fields):
        new_id = f"id{len(self.created) + 1}"
        self.created.append((body["name"], body["parents"][0], new_id))
        return FakeRequest({"id": new_id})

    def get(self, fileId, fields):
        if fileId in self.missing:
            return FakeRequest(error=RuntimeError("404"))
        return FakeRequest({"id": fileId, "trashed": self.trashed.get(fileId, False)})


class FakeService:
    def __init__(self, files):
        self._files = files

    def files(self):
        return self._files


class DriveEnvTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env = {"STATE_DIR": os.path.join(self.tmp.name, "state"),
               "DRIVE_FOLDER_NAME": "Music/Auto"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)


class DrivePathTests(DriveEnvTestCase):
    def test_paths(self):
        self.assertEqual(drive_upload.drive_path(), "My Drive/Music/Auto")
        self.assertEqual(drive_upload.drive_path("logs"), "My Drive/Music/Auto/logs")


class EnsureFolderTests(DriveEnvTestCase):
    def test_creates_nested_folders_and_caches_each_path(self):
        files = FakeFiles()
        service = FakeService(files)
        state = {}
        leaf = drive_upload._ensure_folder(service, state, "Music/Auto")
        self.assertEqual([(n, p) for n, p, _ in files.created],
                         [("Music", "root"), ("Auto", "id1")])
        self.assertEqual(leaf, "id2")
        self.assertEqual(state["folders"]["Music/Auto"]["id"], "id2")
        # Cached: no further API creates, and it is persisted to disk.
        self.assertEqual(drive_upload._ensure_folder(service, state, "Music/Auto"), "id2")
        self.assertEqual(len(files.created), 2)
        self.assertEqual(drive_upload.load_state()["folders"]["Music/Auto"]["id"], "id2")

    def test_logs_folder_is_separate_from_songs_folder(self):
        files = FakeFiles(existing={("Music", "root"): "m", ("Auto", "m"): "a"})
        service = FakeService(files)
        state = {}
        self.assertEqual(drive_upload._ensure_folder(service, state, "Music/Auto"), "a")
        self.assertEqual(drive_upload._ensure_folder(service, state, "Music/Auto/logs"), "id1")
        self.assertEqual(files.created, [("logs", "a", "id1")])

    def test_reuses_existing_folder_instead_of_creating(self):
        files = FakeFiles(existing={("Music", "root"): "m"})
        drive_upload._ensure_folder(FakeService(files), {}, "Music")
        self.assertEqual(files.created, [])

    def test_recreates_when_cached_folder_trashed_or_gone(self):
        for broken in ("trashed", "missing"):
            files = FakeFiles()
            if broken == "trashed":
                files.trashed["old"] = True
            else:
                files.missing.add("old")
            state = {"folders": {"Music": {"id": "old"}}}
            new = drive_upload._ensure_folder(FakeService(files), state, "Music")
            self.assertNotEqual(new, "old", broken)
            self.assertEqual(state["folders"]["Music"]["id"], new)

    def test_quote_in_folder_name_is_escaped(self):
        files = FakeFiles(existing={("Bob's", "root"): "b"})
        self.assertEqual(
            drive_upload._ensure_folder(FakeService(files), {}, "Bob's"), "b")


class UploadNewSongsTests(DriveEnvTestCase):
    def setUp(self):
        super().setUp()
        self.songs = os.path.join(self.tmp.name, "songs")
        os.makedirs(self.songs)
        for i in ("aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"):
            open(os.path.join(self.songs, f"T - A - {i}.m4a"), "w").close()

    def run_upload(self, upload_side_effect=None):
        patches = [
            mock.patch.object(drive_upload, "_service"),
            mock.patch.object(drive_upload, "_ensure_folder", return_value="folder"),
            mock.patch.object(drive_upload, "_upload_file",
                              side_effect=upload_side_effect or (lambda *a, **k: "drive-id")),
        ]
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        return drive_upload.upload_new_songs(self.songs), mocks[2]

    def test_uploads_pending_and_records_state(self):
        (uploaded, failed), up = self.run_upload()
        self.assertEqual(sorted(uploaded), sorted(os.listdir(self.songs)))
        self.assertEqual(failed, [])
        self.assertEqual(up.call_count, 3)
        self.assertEqual(drive_upload.uploaded_ids(),
                         {"aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"})

    def test_second_run_uploads_nothing(self):
        self.run_upload()
        (uploaded, failed), up = self.run_upload()
        self.assertEqual((uploaded, failed), ([], []))
        up.assert_not_called()

    def test_failed_upload_is_reported_and_retried_next_time(self):
        def flaky(service, folder, path, name, mime):
            if "bbbbbbbbbbb" in name:
                raise OSError("network")
            return "drive-id"

        (uploaded, failed), _ = self.run_upload(flaky)
        self.assertEqual(len(uploaded), 2)
        self.assertEqual(failed, ["T - A - bbbbbbbbbbb.m4a"])
        self.assertNotIn("bbbbbbbbbbb", drive_upload.uploaded_ids())
        (uploaded, failed), _ = self.run_upload()
        self.assertEqual(uploaded, ["T - A - bbbbbbbbbbb.m4a"])

    def test_delete_after_upload_removes_local_files(self):
        with mock.patch.dict(os.environ, {"DELETE_AFTER_UPLOAD": "true"}):
            self.run_upload()
        self.assertEqual(os.listdir(self.songs), [])


class UploadLogfileTests(DriveEnvTestCase):
    def test_uploads_into_logs_subfolder(self):
        log_path = os.path.join(self.tmp.name, "cycle-x.log")
        open(log_path, "w").close()
        with mock.patch.object(drive_upload, "_service"), \
                mock.patch.object(drive_upload, "_ensure_folder",
                                  return_value="logs-folder") as ensure, \
                mock.patch.object(drive_upload, "_upload_file") as up:
            drive_upload.upload_logfile(log_path)
        self.assertEqual(ensure.call_args.args[2], "Music/Auto/logs")
        self.assertEqual(up.call_args.args[1:], (
            "logs-folder", log_path, "cycle-x.log", "text/plain"))


if __name__ == "__main__":
    unittest.main()
