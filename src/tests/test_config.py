import unittest

from src import config


class LogConfigTests(unittest.TestCase):
    def test_log_keep_idle_defaults_false_and_parses_truthy(self):
        self.assertFalse(config.log_keep_idle({}))
        self.assertFalse(config.log_keep_idle({"LOG_KEEP_IDLE": ""}))
        self.assertFalse(config.log_keep_idle({"LOG_KEEP_IDLE": "no"}))
        for value in ("true", "TRUE", "1", "yes", "on", " True "):
            self.assertTrue(config.log_keep_idle({"LOG_KEEP_IDLE": value}), value)

    def test_log_retention_days(self):
        self.assertEqual(config.log_retention_days({}), 14)
        self.assertEqual(config.log_retention_days({"LOG_RETENTION_DAYS": "3"}), 3)


class UpdateConfigTests(unittest.TestCase):
    def test_auto_update_defaults_on(self):
        self.assertTrue(config.auto_update_enabled({}))
        self.assertTrue(config.auto_update_enabled({"YTDLP_AUTO_UPDATE": ""}))
        self.assertFalse(config.auto_update_enabled({"YTDLP_AUTO_UPDATE": "false"}))
        self.assertFalse(config.auto_update_enabled({"YTDLP_AUTO_UPDATE": "0"}))

    def test_update_interval(self):
        self.assertEqual(config.update_interval_seconds({}), 86400)
        self.assertEqual(
            config.update_interval_seconds({"YTDLP_UPDATE_INTERVAL_SECONDS": "60"}), 60)


if __name__ == "__main__":
    unittest.main()


class DownloadConfigTests(unittest.TestCase):
    def test_workers_default_and_minimum(self):
        self.assertEqual(config.download_workers({}), 4)
        self.assertEqual(config.download_workers({"DOWNLOAD_WORKERS": ""}), 4)
        self.assertEqual(config.download_workers({"DOWNLOAD_WORKERS": "4"}), 4)
        self.assertEqual(config.download_workers({"DOWNLOAD_WORKERS": "0"}), 1)

    def test_sleep_default_and_parsing(self):
        self.assertEqual(config.download_sleep_seconds({}), 2)
        self.assertEqual(
            config.download_sleep_seconds({"DOWNLOAD_SLEEP_SECONDS": "0.5"}), 0.5)
        self.assertEqual(
            config.download_sleep_seconds({"DOWNLOAD_SLEEP_SECONDS": "0"}), 0)

    def test_retries_default_and_minimum(self):
        self.assertEqual(config.download_retries({}), 2)
        self.assertEqual(config.download_retries({"DOWNLOAD_RETRIES": "0"}), 0)
        self.assertEqual(config.download_retries({"DOWNLOAD_RETRIES": "5"}), 5)
        self.assertEqual(config.download_retries({"DOWNLOAD_RETRIES": "-1"}), 0)
