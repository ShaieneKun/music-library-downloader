import os
import unittest

import main


class ResolveDownloadDirectoryTests(unittest.TestCase):
    def test_env_var_has_priority_over_cli_argument(self):
        env = {"DESTINATION_FOLDER": "/env/downloads"}

        result = main.resolve_download_directory(
            cli_args=["main.py", "/cli/downloads"],
            env=env,
        )

        self.assertEqual(result, "/env/downloads")

    def test_cli_argument_is_used_when_env_var_is_not_set(self):
        env = {}

        result = main.resolve_download_directory(
            cli_args=["main.py", "/cli/downloads"],
            env=env,
        )

        self.assertEqual(result, "/cli/downloads")

    def test_default_download_directory_is_used_when_nothing_is_provided(self):
        env = {}

        result = main.resolve_download_directory(
            cli_args=["main.py"],
            env=env,
        )

        self.assertEqual(result, None)


if __name__ == "__main__":
    unittest.main()
