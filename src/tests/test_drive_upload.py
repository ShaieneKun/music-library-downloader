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


class DownloadFilterTests(unittest.TestCase):
    """filter_url_ids_to_donwload: which playlist songs get downloaded."""

    def run_filter(self, env, local=(), uploaded=("upload00001",)):
        from unittest import mock
        from src import download_songs
        with tempfile.TemporaryDirectory() as d:
            for i in local:
                open(os.path.join(d, f"T - A - {i}.m4a"), "w").close()
            with mock.patch.dict(os.environ, env, clear=True), \
                    mock.patch.object(download_songs, "list_playlist_ids",
                                      return_value=["upload00001", "local000001", "newsong0001"]), \
                    mock.patch.object(drive_upload, "uploaded_ids",
                                      return_value=set(uploaded)):
                urls = download_songs.filter_url_ids_to_donwload(d, "m4a", ["x"])
        return [u.split("=")[-1] for u in urls]

    def test_skip_flag_defaults_to_false(self):
        self.assertFalse(config.skip_download_if_uploaded({}))
        self.assertTrue(config.skip_download_if_uploaded(
            {"SKIP_DOWNLOAD_IF_UPLOADED": "true"}))

    def test_default_downloads_songs_already_in_drive(self):
        ids = self.run_filter({}, local=["local000001"])
        self.assertEqual(ids, ["upload00001", "newsong0001"])

    def test_skip_flag_keeps_uploaded_songs_out(self):
        ids = self.run_filter({"SKIP_DOWNLOAD_IF_UPLOADED": "true"}, local=["local000001"])
        self.assertEqual(ids, ["newsong0001"])

    def test_locally_present_songs_are_never_downloaded(self):
        ids = self.run_filter({}, local=["local000001", "upload00001", "newsong0001"])
        self.assertEqual(ids, [])

    def test_redownloaded_song_is_not_uploaded_again(self):
        # upload_new_songs only picks local files whose id is not in state.
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "T - A - upload00001.m4a"), "w").close()
            with mock.patch.object(drive_upload, "load_state",
                                   return_value={"uploaded": {"upload00001": "fid"}}), \
                    mock.patch.object(drive_upload, "_service") as service:
                self.assertEqual(drive_upload.upload_new_songs(d), 0)
                service.assert_not_called()


if __name__ == "__main__":
    unittest.main()
