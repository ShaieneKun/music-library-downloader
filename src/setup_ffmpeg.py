import logging
import shutil
import sys

REQUIRED_EXECUTABLES = ("ffmpeg", "ffprobe")

log = logging.getLogger(__name__)


def missing_executables():
    return [name for name in REQUIRED_EXECUTABLES if shutil.which(name) is None]


def main():
    log.info("Checking for system-installed ffmpeg and ffprobe...")
    missing = missing_executables()

    if not missing:
        log.info("System ffmpeg and ffprobe are available on PATH, continuing...")
        return

    log.error(
        "The following required executable(s) are not available on PATH: %s. "
        "Please install the system ffmpeg package and try again.",
        ", ".join(missing)
    )
    sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
