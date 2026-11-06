import unittest
from unittest import mock

from src import updater


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class AutoUpdaterTests(unittest.TestCase):
    def test_checks_first_time_then_waits_for_interval(self):
        clock = FakeClock()
        u = updater.AutoUpdater(interval=100, enabled=True, clock=clock)
        with mock.patch.object(updater, "upgrade", return_value=False) as up:
            u.maybe_update()
            clock.now += 50
            u.maybe_update()
            self.assertEqual(up.call_count, 1)
            clock.now += 60
            u.maybe_update()
            self.assertEqual(up.call_count, 2)

    def test_disabled_never_upgrades(self):
        u = updater.AutoUpdater(interval=1, enabled=False, clock=FakeClock())
        with mock.patch.object(updater, "upgrade") as up:
            u.maybe_update()
            up.assert_not_called()

    def test_restarts_only_when_version_changed(self):
        u = updater.AutoUpdater(interval=1, enabled=True, clock=FakeClock())
        with mock.patch.object(updater, "upgrade", return_value=True), \
                mock.patch.object(updater.os, "execv") as execv:
            u.maybe_update()
            execv.assert_called_once()

    def test_upgrade_crash_does_not_propagate(self):
        u = updater.AutoUpdater(interval=1, enabled=True, clock=FakeClock())
        with mock.patch.object(updater, "upgrade", side_effect=OSError("boom")):
            u.maybe_update()


class UpgradeTests(unittest.TestCase):
    def run_upgrade(self, versions, returncode=0, uv="/usr/bin/uv"):
        completed = mock.Mock(returncode=returncode, stderr="resolution failed")
        with mock.patch.object(updater.shutil, "which", return_value=uv), \
                mock.patch.object(updater, "installed_version", side_effect=versions), \
                mock.patch.object(updater.subprocess, "run",
                                  return_value=completed) as run:
            return updater.upgrade(), run

    def test_returns_true_only_when_version_changed(self):
        changed, run = self.run_upgrade(["1.0", "2.0"])
        self.assertTrue(changed)
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:3], ["/usr/bin/uv", "pip", "install"])
        self.assertIn("--upgrade", cmd)
        self.assertIn("yt-dlp[default]", cmd)
        self.assertIn(updater.sys.executable, cmd)
        self.assertFalse(self.run_upgrade(["2.0", "2.0"])[0])

    def test_install_failure_returns_false_without_reading_new_version(self):
        changed, _ = self.run_upgrade(["1.0"], returncode=1)
        self.assertFalse(changed)

    def test_missing_uv_skips_upgrade(self):
        with mock.patch.object(updater.shutil, "which", return_value=None), \
                mock.patch.object(updater.subprocess, "run") as run:
            self.assertFalse(updater.upgrade())
        run.assert_not_called()


class AutoUpdaterRestartTests(unittest.TestCase):
    def test_restart_reexecs_same_interpreter_and_args(self):
        u = updater.AutoUpdater(interval=1, enabled=True, clock=FakeClock())
        with mock.patch.object(updater, "upgrade", return_value=True), \
                mock.patch.object(updater.os, "execv") as execv:
            u.maybe_update()
        execv.assert_called_once_with(
            updater.sys.executable, [updater.sys.executable] + updater.sys.argv)

    def test_no_restart_when_unchanged_or_failed(self):
        for result in (False, OSError("boom")):
            u = updater.AutoUpdater(interval=1, enabled=True, clock=FakeClock())
            kwargs = ({"side_effect": result} if isinstance(result, Exception)
                      else {"return_value": result})
            with mock.patch.object(updater, "upgrade", **kwargs), \
                    mock.patch.object(updater.os, "execv") as execv:
                u.maybe_update()
            execv.assert_not_called()

    def test_failed_check_still_waits_full_interval(self):
        clock = FakeClock()
        u = updater.AutoUpdater(interval=100, enabled=True, clock=clock)
        with mock.patch.object(updater, "upgrade", side_effect=OSError("boom")) as up:
            u.maybe_update()
            clock.now += 10
            u.maybe_update()
        self.assertEqual(up.call_count, 1)


if __name__ == "__main__":
    unittest.main()
