"""Tests for the MUSIC_DIR bind mount in the compose files.

They run `docker compose config` against copies of the compose files in a
temporary project directory, so the real `.env` and the real `$HOME`
never influence the result.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMPOSE_FILES = ["compose.yaml", "compose.debug.yaml"]


def docker_compose_available():
    try:
        return subprocess.run(["docker", "compose", "version"],
                              capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


@unittest.skipUnless(docker_compose_available(), "docker compose not installed")
class MusicDirComposeTests(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.project, ignore_errors=True)
        for name in COMPOSE_FILES:
            shutil.copy(os.path.join(ROOT, name), self.project)
        self.write_env("")

    def write_env(self, content):
        with open(os.path.join(self.project, ".env"), "w") as f:
            f.write(content)

    def service(self, compose_file, **env):
        # Minimal environment: no inherited MUSIC_DIR, controlled HOME.
        full_env = {"PATH": os.environ["PATH"], "HOME": "/home/tester"}
        # The fake HOME hides the docker CLI config (and its compose plugin).
        full_env["DOCKER_CONFIG"] = os.environ.get(
            "DOCKER_CONFIG", os.path.expanduser("~/.docker"))
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT"):
            if key in os.environ:
                full_env[key] = os.environ[key]
        full_env.update(env)
        out = subprocess.run(
            ["docker", "compose", "-f", compose_file, "config", "--format", "json"],
            cwd=self.project, env=full_env, capture_output=True, text=True,
            check=True).stdout
        return json.loads(out)["services"]["music-library-downloader"]

    def volumes(self, compose_file, **env):
        return {v["target"]: v
                for v in self.service(compose_file, **env)["volumes"]}

    def environment(self, compose_file, **env):
        return self.service(compose_file, **env)["environment"]

    def test_defaults_to_music_folder_in_home(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                songs = self.volumes(f)["/data/songs"]
                self.assertEqual(songs["type"], "bind")
                self.assertEqual(songs["source"], "/home/tester/Music")

    def test_music_dir_env_var_overrides_default(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                songs = self.volumes(f, MUSIC_DIR="/mnt/media")["/data/songs"]
                self.assertEqual(songs["source"], "/mnt/media")

    def test_music_dir_is_read_from_dot_env(self):
        self.write_env("MUSIC_DIR=/from/dotenv\n")
        songs = self.volumes("compose.yaml")["/data/songs"]
        self.assertEqual(songs["source"], "/from/dotenv")

    def test_shell_env_beats_dot_env(self):
        self.write_env("MUSIC_DIR=/from/dotenv\n")
        songs = self.volumes("compose.yaml", MUSIC_DIR="/from/shell")["/data/songs"]
        self.assertEqual(songs["source"], "/from/shell")

    def test_empty_music_dir_falls_back_to_default(self):
        songs = self.volumes("compose.yaml", MUSIC_DIR="")["/data/songs"]
        self.assertEqual(songs["source"], "/home/tester/Music")

    def test_missing_host_directory_is_created_by_docker(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                songs = self.volumes(f)["/data/songs"]
                self.assertTrue(songs["bind"]["create_host_path"])

    def test_host_dir_is_passed_to_container_for_the_summary(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                self.assertEqual(self.environment(f)["HOST_MUSIC_DIR"],
                                 "/home/tester/Music")
                self.assertEqual(
                    self.environment(f, MUSIC_DIR="/mnt/media")["HOST_MUSIC_DIR"],
                    "/mnt/media")

    def test_host_hostname_is_passed_through_or_empty(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                self.assertEqual(self.environment(f)["HOST_HOSTNAME"], "")
                self.assertEqual(
                    self.environment(f, HOST_HOSTNAME="my-mac")["HOST_HOSTNAME"],
                    "my-mac")

    def test_state_and_logs_stay_in_named_volume(self):
        for f in COMPOSE_FILES:
            with self.subTest(file=f):
                data = self.volumes(f)["/data"]
                self.assertEqual(data["type"], "volume")
                self.assertEqual(data["source"], "data")


if __name__ == "__main__":
    unittest.main()
