import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from src import download_songs
from src.download_songs import StartThrottle, download_all


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class StartThrottleTests(unittest.TestCase):
    def test_spaces_starts_by_gap(self):
        clock = FakeClock()
        throttle = StartThrottle(3, clock=clock, sleep=clock.sleep)
        starts = []
        for _ in range(3):
            throttle.wait()
            starts.append(clock.now)
        self.assertEqual(starts[1] - starts[0], 3)
        self.assertEqual(starts[2] - starts[1], 3)

    def test_first_start_does_not_wait(self):
        clock = FakeClock()
        StartThrottle(3, clock=clock, sleep=clock.sleep).wait()
        self.assertEqual(clock.sleeps, [])

    def test_no_wait_when_gap_already_elapsed(self):
        clock = FakeClock()
        throttle = StartThrottle(3, clock=clock, sleep=clock.sleep)
        throttle.wait()
        clock.now += 10
        throttle.wait()
        self.assertEqual(clock.sleeps, [])

    def test_concurrent_waiters_get_distinct_slots(self):
        throttle = StartThrottle(0.05)
        starts = []
        lock = threading.Lock()

        def go():
            throttle.wait()
            with lock:
                starts.append(time.monotonic())

        threads = [threading.Thread(target=go) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        starts.sort()
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        self.assertTrue(all(g >= 0.04 for g in gaps), gaps)


class NoThrottle:
    def wait(self):
        pass


class DownloadAllTests(unittest.TestCase):
    def run_all(self, ids, workers=1, **kwargs):
        calls = []
        lock = threading.Lock()

        def fake(opts, url):
            with lock:
                calls.append(url)

        attempted = download_all(ids, {}, workers=workers, downloader=fake,
                                 throttle=NoThrottle(), **kwargs)
        return attempted, calls

    def test_downloads_every_song(self):
        attempted, calls = self.run_all(["a", "b", "c"], workers=2)
        self.assertEqual(sorted(attempted), ["a", "b", "c"])
        self.assertEqual(len(calls), 3)
        self.assertIn("https://www.youtube.com/watch?v=a", calls)

    def test_duplicates_downloaded_once(self):
        attempted, calls = self.run_all(["a", "b", "a"], workers=3)
        self.assertEqual(sorted(attempted), ["a", "b"])
        self.assertEqual(len(calls), 2)

    def test_sequential_with_one_worker_keeps_order(self):
        _, calls = self.run_all(["a", "b", "c"], workers=1)
        self.assertEqual([c[-1] for c in calls], ["a", "b", "c"])

    def test_never_exceeds_worker_count(self):
        running = [0]
        peak = [0]
        lock = threading.Lock()

        def fake(opts, url):
            with lock:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            time.sleep(0.05)
            with lock:
                running[0] -= 1

        download_all([str(i) for i in range(8)], {}, workers=3,
                     downloader=fake, throttle=NoThrottle())
        self.assertLessEqual(peak[0], 3)
        self.assertGreater(peak[0], 1)

    def test_failing_song_does_not_stop_others(self):
        calls = []

        def fake(opts, url):
            calls.append(url)
            if url.endswith("b"):
                raise RuntimeError("boom")

        attempted = download_all(["a", "b", "c"], {}, workers=2,
                                 downloader=fake, throttle=NoThrottle())
        self.assertEqual(sorted(attempted), ["a", "b", "c"])
        self.assertEqual(len(calls), 3)

    def test_stop_event_skips_pending_songs(self):
        stop = threading.Event()
        calls = []

        def fake(opts, url):
            calls.append(url)
            stop.set()

        attempted = download_all(["a", "b", "c"], {}, workers=1, stop_event=stop,
                                 downloader=fake, throttle=NoThrottle())
        self.assertEqual(attempted, ["a"])
        self.assertEqual(len(calls), 1)

    def test_stop_event_already_set_downloads_nothing(self):
        stop = threading.Event()
        stop.set()
        attempted, calls = self.run_all(["a", "b"], stop_event=stop)
        self.assertEqual(attempted, [])
        self.assertEqual(calls, [])


class FakeYDL:
    """Stands in for yt_dlp.YoutubeDL; `outcomes` is consumed one per download."""
    outcomes = []
    calls = 0

    def __init__(self, opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def download(self, url):
        type(self).calls += 1
        outcome = type(self).outcomes.pop(0)
        if outcome is not None:
            raise outcome


class DownloadSongTests(unittest.TestCase):
    ID = "aaaaaaaaaaa"
    URL = "https://www.youtube.com/watch?v=aaaaaaaaaaa"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.opts = {"outtmpl": {"default": os.path.join(self.tmp.name, "%(title)s.%(ext)s")},
                     "postprocessors": [{"preferredcodec": "m4a"}]}
        FakeYDL.calls = 0
        patcher = mock.patch.object(download_songs.yt_dlp, "YoutubeDL", FakeYDL)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sleeps = []

    def run_song(self, outcomes, retries=2):
        FakeYDL.outcomes = list(outcomes)
        return download_songs.download_song(
            self.opts, self.URL, retries=retries, sleep=self.sleeps.append)

    def touch(self, name):
        path = os.path.join(self.tmp.name, name)
        open(path, "w").close()
        return path

    def test_success_needs_one_attempt(self):
        self.assertTrue(self.run_song([None]))
        self.assertEqual(FakeYDL.calls, 1)

    def test_transient_error_is_retried_then_succeeds(self):
        err = Exception("ERROR: unable to download video data: HTTP Error 403: Forbidden")
        self.assertTrue(self.run_song([err, None]))
        self.assertEqual(FakeYDL.calls, 2)
        self.assertEqual(self.sleeps, [5])

    def test_transient_error_gives_up_after_retries(self):
        err = Exception("HTTP Error 429: Too Many Requests")
        self.assertFalse(self.run_song([err, err, err]))
        self.assertEqual(FakeYDL.calls, 3)
        self.assertEqual(self.sleeps, [5, 10])

    def test_permanent_error_is_not_retried(self):
        err = Exception("[youtube] x: Video unavailable. This video is no longer available")
        self.assertFalse(self.run_song([err]))
        self.assertEqual(FakeYDL.calls, 1)
        self.assertEqual(self.sleeps, [])

    def test_zero_retries(self):
        err = Exception("HTTP Error 403: Forbidden")
        self.assertFalse(self.run_song([err], retries=0))
        self.assertEqual(FakeYDL.calls, 1)

    def test_failed_song_leftovers_removed_but_other_files_kept(self):
        leftover = self.touch(f"Song - Artist - {self.ID}.webp")
        part = self.touch(f"Song - Artist - {self.ID}.m4a.part")
        other = self.touch("Other - Artist - bbbbbbbbbbb.webp")
        done = self.touch("Other - Artist - bbbbbbbbbbb.m4a")
        self.assertFalse(self.run_song([Exception("Video unavailable")]))
        self.assertFalse(os.path.exists(leftover))
        self.assertFalse(os.path.exists(part))
        self.assertTrue(os.path.exists(other))
        self.assertTrue(os.path.exists(done))

    def test_success_leaves_files_alone(self):
        thumb = self.touch(f"Song - Artist - {self.ID}.webp")
        self.assertTrue(self.run_song([None]))
        self.assertTrue(os.path.exists(thumb))

    def test_failed_song_keeps_its_m4a(self):
        song = self.touch(f"Song - Artist - {self.ID}.m4a")
        self.assertFalse(self.run_song([Exception("Video unavailable")]))
        self.assertTrue(os.path.exists(song))


if __name__ == "__main__":
    unittest.main()
