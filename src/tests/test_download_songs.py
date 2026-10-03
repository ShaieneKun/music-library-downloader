import os
import tempfile
import unittest

from src import download_songs


class ExtractIdsFromFilenamesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def touch(self, filename):
        open(os.path.join(self.tmp.name, filename), 'w').close()

    def test_extracts_plain_id(self):
        self.touch("Song - Artist - dQw4w9WgXcQ.m4a")

        ids = download_songs.extract_ids_from_filenames(self.tmp.name)

        self.assertEqual(ids, {"dQw4w9WgXcQ"})

    def test_extracts_ids_containing_hyphens(self):
        self.touch("Song - Artist - a-bC_d3fGh1.m4a")
        self.touch("Song - Artist - -xYz123abcd.m4a")

        ids = download_songs.extract_ids_from_filenames(self.tmp.name)

        self.assertEqual(ids, {"a-bC_d3fGh1", "-xYz123abcd"})

    def test_handles_hyphens_in_title_and_uploader(self):
        self.touch("Some - Song - The-Artist - dQw4w9WgXcQ.m4a")

        ids = download_songs.extract_ids_from_filenames(self.tmp.name)

        self.assertEqual(ids, {"dQw4w9WgXcQ"})

    def test_ignores_other_formats_and_partial_files(self):
        self.touch("Song - Artist - dQw4w9WgXcQ.webp")
        self.touch("Song - Artist - dQw4w9WgXcQ.m4a.part")

        ids = download_songs.extract_ids_from_filenames(self.tmp.name)

        self.assertEqual(ids, set())

    def test_respects_file_format(self):
        self.touch("Song - Artist - dQw4w9WgXcQ.mp3")

        ids = download_songs.extract_ids_from_filenames(self.tmp.name, "mp3")

        self.assertEqual(ids, {"dQw4w9WgXcQ"})

    def test_missing_directory_returns_empty_set(self):
        missing = os.path.join(self.tmp.name, "missing")

        self.assertEqual(download_songs.extract_ids_from_filenames(missing), set())


class PlaylistUrlsFromEnvTests(unittest.TestCase):
    def test_default_when_unset_or_empty(self):
        self.assertEqual(download_songs.playlist_urls_from_env({}),
                         download_songs.DEFAULT_PLAYLIST_URLS)
        self.assertEqual(download_songs.playlist_urls_from_env({"PLAYLIST_URLS": " "}),
                         download_songs.DEFAULT_PLAYLIST_URLS)

    def test_splits_on_commas_and_whitespace(self):
        env = {"PLAYLIST_URLS": "https://a, https://b\nhttps://c"}

        self.assertEqual(download_songs.playlist_urls_from_env(env),
                         ["https://a", "https://b", "https://c"])


class FilterUrlsToDownloadTests(unittest.TestCase):
    def test_skips_downloaded_ids_and_keeps_playlist_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "Song - Artist - a-bC_d3fGh1.m4a"), 'w').close()
            playlist_ids = ["zzzzzzzzzzz", "a-bC_d3fGh1", "aaaaaaaaaaa", "zzzzzzzzzzz"]

            original = download_songs.fetch_playlist_ids
            download_songs.fetch_playlist_ids = lambda urls: playlist_ids
            self.addCleanup(setattr, download_songs, "fetch_playlist_ids", original)

            urls = download_songs.filter_urls_to_download(tmp, ["playlist"], "m4a")

        self.assertEqual(urls, [
            "https://www.youtube.com/watch?v=zzzzzzzzzzz",
            "https://www.youtube.com/watch?v=aaaaaaaaaaa",
        ])


if __name__ == "__main__":
    unittest.main()
