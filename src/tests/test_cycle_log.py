import logging
import os
import tempfile
import time
import unittest
from unittest import mock

import main
from src import download_songs, report


def read(path):
    with open(path) as f:
        return f.read()


def song(i):
    return f"Title - Artist - {i}.m4a"


class CycleLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.songs = os.path.join(self.tmp.name, "songs")
        self.logs = os.path.join(self.tmp.name, "logs")
        os.makedirs(self.songs)
        os.makedirs(self.logs)
        env = {"LOG_DIR": self.logs, "STATE_DIR": os.path.join(self.tmp.name, "state"),
               "DRIVE_UPLOAD_ENABLED": "true", "DRIVE_FOLDER_NAME": "Music"}
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_download(self, opts, url):
        song_id = url.rsplit("=", 1)[1]
        if song_id != "FAILFAILFAI":
            open(os.path.join(self.songs, song(song_id)), "w").close()

    def test_full_cycle_report_and_log_upload(self):
        open(os.path.join(self.songs, song("aaaaaaaaaaa")), "w").close()
        ids = ["aaaaaaaaaaa", "bbbbbbbbbbb", "FAILFAILFAI"]
        with mock.patch.object(download_songs, "list_playlist_ids", return_value=ids), \
                mock.patch.object(download_songs, "download_song", self.fake_download), \
                mock.patch.object(download_songs.time, "sleep"), \
                mock.patch.object(download_songs.drive_upload, "upload_new_songs",
                                  return_value=([song("bbbbbbbbbbb")], [])), \
                mock.patch.object(main.src.drive_upload, "upload_logfile") as up:
            rep = main.run_logged_cycle(self.songs)

        self.assertEqual(rep.playlist_total, 3)
        self.assertEqual(len(rep.already_downloaded), 1)
        self.assertEqual(rep.to_download, ["bbbbbbbbbbb", "FAILFAILFAI"])
        self.assertEqual(rep.downloaded, [song("bbbbbbbbbbb")])
        self.assertEqual(rep.download_failed, ["FAILFAILFAI"])
        self.assertEqual(rep.uploaded, [song("bbbbbbbbbbb")])
        up.assert_called_once_with(rep.log_file)

        text = read(rep.log_file)
        self.assertIn("CYCLE SUMMARY", text)
        self.assertIn(os.path.abspath(self.songs), text)
        self.assertIn("My Drive/Music", text)
        self.assertIn("My Drive/Music/logs", text)
        self.assertIn("Already downloaded (skipped):   1", text)
        self.assertIn("Actually downloaded:            1", text)
        self.assertIn("Uploaded to Google Drive:       1", text)

    def test_idle_cycle_removes_log_and_skips_upload(self):
        with mock.patch.object(download_songs, "list_playlist_ids", return_value=[]), \
                mock.patch.object(download_songs.drive_upload, "upload_new_songs",
                                  return_value=([], [])), \
                mock.patch.object(main.src.drive_upload, "upload_logfile") as up:
            rep = main.run_logged_cycle(self.songs)
        self.assertFalse(os.path.exists(rep.log_file))
        up.assert_not_called()

    def run_cycle_with(self, ids=(), env=None, upload_raises=None, cycle_raises=None,
                       download=None):
        """Run a logged cycle with all external calls mocked."""
        patches = [
            mock.patch.object(download_songs, "list_playlist_ids", return_value=list(ids)),
            mock.patch.object(download_songs, "download_song", download or self.fake_download),
            mock.patch.object(download_songs.time, "sleep"),
            mock.patch.object(download_songs.drive_upload, "upload_new_songs",
                              return_value=([], [])),
            mock.patch.object(main.src.drive_upload, "upload_logfile",
                              side_effect=upload_raises),
            mock.patch.dict(os.environ, env or {}),
        ]
        if cycle_raises:
            patches.append(mock.patch.object(download_songs, "run_cycle",
                                             side_effect=cycle_raises))
        mocks = [p.start() for p in patches]
        for p in patches:
            self.addCleanup(p.stop)
        return main.run_logged_cycle(self.songs), mocks[4]

    def test_drive_disabled_keeps_log_but_does_not_upload(self):
        rep, up = self.run_cycle_with(
            ids=["bbbbbbbbbbb"], env={"DRIVE_UPLOAD_ENABLED": "false"})
        self.assertTrue(os.path.exists(rep.log_file))
        self.assertFalse(rep.drive_enabled)
        up.assert_not_called()
        self.assertIn("Google Drive upload:            disabled",
                      read(rep.log_file))

    def test_keep_idle_uploads_idle_log(self):
        rep, up = self.run_cycle_with(env={"LOG_KEEP_IDLE": "true"})
        self.assertTrue(os.path.exists(rep.log_file))
        up.assert_called_once_with(rep.log_file)

    def test_log_upload_failure_does_not_crash_and_keeps_local_log(self):
        rep, up = self.run_cycle_with(ids=["bbbbbbbbbbb"],
                                      upload_raises=OSError("drive down"))
        up.assert_called_once()
        self.assertTrue(os.path.exists(rep.log_file))

    def test_cycle_exception_is_logged_counted_and_log_still_shipped(self):
        rep, up = self.run_cycle_with(cycle_raises=RuntimeError("kaboom"))
        text = read(rep.log_file)
        self.assertIn("Cycle failed.", text)
        self.assertIn("RuntimeError: kaboom", text)
        self.assertGreaterEqual(rep.errors, 1)
        up.assert_called_once_with(rep.log_file)  # error cycles count as activity

    def test_errors_during_cycle_are_counted_in_summary(self):
        def noisy(opts, url):
            logging.getLogger("yt_dlp").error("boom")

        rep, _ = self.run_cycle_with(ids=["bbbbbbbbbbb"], download=noisy)
        self.assertEqual(rep.errors, 1)
        self.assertIn("Errors logged this cycle:       1", read(rep.log_file))

    def test_log_contains_debug_lines_and_handlers_are_cleaned_up(self):
        root = logging.getLogger()
        handlers_before, level_before = list(root.handlers), root.level

        def chatty(opts, url):
            logging.getLogger("yt_dlp").debug("[download] details")

        rep, _ = self.run_cycle_with(ids=["bbbbbbbbbbb"], download=chatty)
        self.assertIn("DEBUG - yt_dlp - [download] details", read(rep.log_file))
        self.assertEqual(root.handlers, handlers_before)
        self.assertEqual(root.level, level_before)

    def test_prune_old_logs(self):
        old = os.path.join(self.logs, "cycle-old.log")
        new = os.path.join(self.logs, "cycle-new.log")
        other = os.path.join(self.logs, "app.log")
        for p in (old, new, other):
            open(p, "w").close()
        past = time.time() - 30 * 86400
        os.utime(old, (past, past))
        os.utime(other, (past, past))
        main.prune_old_logs(self.logs, 14)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(new))
        self.assertTrue(os.path.exists(other))


class SplitPlaylistIdsTests(unittest.TestCase):
    ALL = ["ddddddddddd", "aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]

    def split(self, env):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, song("aaaaaaaaaaa")), "w").close()
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(download_songs.drive_upload, "uploaded_ids",
                                      return_value={"bbbbbbbbbbb"}):
                return download_songs.split_playlist_ids(self.ALL, d, "m4a")

    def test_default_only_skips_local_songs_and_keeps_order(self):
        already, todo = self.split({"SKIP_DOWNLOAD_IF_UPLOADED": ""})
        self.assertEqual(already, ["aaaaaaaaaaa"])
        self.assertEqual(todo, ["ddddddddddd", "bbbbbbbbbbb", "ccccccccccc"])

    def test_skip_flag_also_skips_drive_uploaded_ids(self):
        already, todo = self.split({"SKIP_DOWNLOAD_IF_UPLOADED": "true"})
        self.assertEqual(already, ["aaaaaaaaaaa", "bbbbbbbbbbb"])
        self.assertEqual(todo, ["ddddddddddd", "ccccccccccc"])


class DownloadMainTests(unittest.TestCase):
    def test_nothing_to_download_skips_downloader_and_reports_counts(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, song("aaaaaaaaaaa")), "w").close()
            with mock.patch.object(download_songs, "list_playlist_ids",
                                   return_value=["aaaaaaaaaaa"]), \
                    mock.patch.object(download_songs.drive_upload, "uploaded_ids",
                                      return_value=set()), \
                    mock.patch.object(download_songs, "download_song") as dl:
                rep = download_songs.download_main(d)
        dl.assert_not_called()
        self.assertEqual((rep.playlist_total, len(rep.already_downloaded),
                          rep.to_download, rep.downloaded), (1, 1, [], []))
        self.assertEqual(rep.download_dir, os.path.abspath(d))


class ReportTests(unittest.TestCase):
    def test_render_without_drive(self):
        text = report.CycleReport(download_dir="/x/songs", log_file="/x/l.log").render()
        self.assertIn("/x/songs", text)
        self.assertIn("Google Drive upload:            disabled", text)

    def test_render_uses_absolute_paths(self):
        text = report.CycleReport(download_dir="rel/songs", log_file="rel/l.log").render()
        self.assertIn(os.path.abspath("rel/songs"), text)
        self.assertIn(os.path.abspath("rel/l.log"), text)

    def test_render_with_drive_lists_files_failures_and_paths(self):
        rep = report.CycleReport(
            download_dir="/d", log_file="/l.log", drive_enabled=True,
            drive_songs_path="My Drive/Music", drive_logs_path="My Drive/Music/logs",
            playlist_total=4, already_downloaded=["a"], to_download=["b", "c", "d"],
            downloaded=["B.m4a", "C.m4a"], download_failed=["d"],
            uploaded=["B.m4a"], upload_failed=["C.m4a"], errors=2)
        text = rep.render()
        for expected in (
                "Already downloaded (skipped):   1",
                "To be downloaded:               3",
                "Actually downloaded:            2",
                "Download failed:                1",
                "Uploaded to Google Drive:       1",
                "Upload failed:                  1",
                "Google Drive songs path:        My Drive/Music",
                "Google Drive logs path:         My Drive/Music/logs",
                "      - B.m4a", "Errors logged this cycle:       2"):
            self.assertIn(expected, text)

    def test_had_activity(self):
        self.assertFalse(report.CycleReport().had_activity)
        self.assertTrue(report.CycleReport(to_download=["a"]).had_activity)
        self.assertTrue(report.CycleReport(uploaded=["a"]).had_activity)
        self.assertTrue(report.CycleReport(upload_failed=["a"]).had_activity)
        self.assertTrue(report.CycleReport(errors=1).had_activity)
        # Skipped-only cycles are not activity.
        self.assertFalse(report.CycleReport(already_downloaded=["a"]).had_activity)


if __name__ == "__main__":
    unittest.main()
