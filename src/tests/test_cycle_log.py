import logging
import os
import tempfile
import time
import unittest
from unittest import mock

import main
from src import download_songs, report


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

        text = open(rep.log_file).read()
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


class ReportTests(unittest.TestCase):
    def test_render_without_drive(self):
        text = report.CycleReport(download_dir="/x/songs", log_file="/x/l.log").render()
        self.assertIn("/x/songs", text)
        self.assertIn("Google Drive upload:            disabled", text)


if __name__ == "__main__":
    unittest.main()
