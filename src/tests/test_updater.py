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


if __name__ == "__main__":
    unittest.main()
