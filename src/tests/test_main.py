import unittest

import main


class ResolveDownloadDirectoryTests(unittest.TestCase):
    def test_env_var_has_priority_over_cli_argument(self):
        env = {"DESTINATION_FOLDER": "/env/downloads"}

        result = main.resolve_download_directory("/cli/downloads", env=env)

        self.assertEqual(result, "/env/downloads")

    def test_cli_argument_is_used_when_env_var_is_not_set(self):
        result = main.resolve_download_directory("/cli/downloads", env={})

        self.assertEqual(result, "/cli/downloads")

    def test_cli_argument_is_used_when_env_var_is_empty(self):
        env = {"DESTINATION_FOLDER": ""}

        result = main.resolve_download_directory("/cli/downloads", env=env)

        self.assertEqual(result, "/cli/downloads")

    def test_none_is_returned_when_nothing_is_provided(self):
        result = main.resolve_download_directory(None, env={})

        self.assertIsNone(result)


class ResolveIntervalTests(unittest.TestCase):
    def test_cli_argument_has_priority_over_env_var(self):
        env = {"DOWNLOAD_INTERVAL_SECONDS": "60"}

        self.assertEqual(main.resolve_interval(10, env=env), 10)

    def test_env_var_is_used_when_cli_argument_is_not_set(self):
        env = {"DOWNLOAD_INTERVAL_SECONDS": "60"}

        self.assertEqual(main.resolve_interval(None, env=env), 60)

    def test_default_is_used_when_env_var_is_empty(self):
        env = {"DOWNLOAD_INTERVAL_SECONDS": ""}

        self.assertEqual(main.resolve_interval(None, env=env),
                         main.DEFAULT_INTERVAL_SECONDS)


class ParseArgsTests(unittest.TestCase):
    def test_defaults(self):
        args = main.parse_args([])

        self.assertIsNone(args.output_dir)
        self.assertFalse(args.once)
        self.assertIsNone(args.interval)

    def test_all_options(self):
        args = main.parse_args(["./songs", "--once", "--interval", "30"])

        self.assertEqual(args.output_dir, "./songs")
        self.assertTrue(args.once)
        self.assertEqual(args.interval, 30)


if __name__ == "__main__":
    unittest.main()
