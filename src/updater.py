"""Keep yt-dlp current inside a long-running container.

YouTube breaks old yt-dlp releases every few weeks (typically as HTTP 403),
so the service upgrades it periodically and restarts itself when a newer
version was installed.
"""
import importlib
import importlib.metadata
import logging
import os
import shutil
import subprocess
import sys
import time

from . import config

log = logging.getLogger(__name__)

PACKAGE = "yt-dlp"
REQUIREMENT = "yt-dlp[default]"


def installed_version():
    importlib.invalidate_caches()
    return importlib.metadata.version(PACKAGE)


def upgrade():
    """Upgrade yt-dlp in the running environment. Returns True if changed."""
    uv = shutil.which("uv")
    if uv is None:
        log.warning("yt-dlp auto-update skipped: `uv` not found.")
        return False
    before = installed_version()
    result = subprocess.run(
        [uv, "pip", "install", "--python", sys.executable,
         "--upgrade", REQUIREMENT],
        capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log.error("yt-dlp auto-update failed: %s",
                  result.stderr.strip() or "<no stderr>")
        return False
    after = installed_version()
    log.info("yt-dlp version: %s%s", after,
             "" if after == before else f" (updated from {before})")
    return after != before


class AutoUpdater:
    """Call `maybe_update()` between cycles; it re-execs after an upgrade."""

    def __init__(self, interval=None, enabled=None, clock=time.monotonic):
        self.interval = config.update_interval_seconds() if interval is None else interval
        self.enabled = config.auto_update_enabled() if enabled is None else enabled
        self.clock = clock
        self.last_check = None

    def due(self):
        return self.enabled and (
            self.last_check is None
            or self.clock() - self.last_check >= self.interval)

    def maybe_update(self):
        if not self.due():
            return
        self.last_check = self.clock()
        try:
            changed = upgrade()
        except Exception:
            log.exception("yt-dlp auto-update crashed; continuing.")
            return
        if changed:
            log.info("Restarting to load the new yt-dlp.")
            logging.shutdown()
            os.execv(sys.executable, [sys.executable] + sys.argv)
