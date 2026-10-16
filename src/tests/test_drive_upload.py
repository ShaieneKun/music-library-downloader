import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
