import sys
import os
import signal
import threading
import logging
from logging.handlers import RotatingFileHandler

import src.setup_ffmpeg
import src.download_songs
import src.drive_upload
from src import config

stop_event = threading.Event()


def setup_logging():
    """Log to stdout (docker logs) and a size-capped file."""
    logs_dir = os.environ.get('LOG_DIR') or './logs'
    os.makedirs(logs_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(f'{logs_dir}/app.log',
                                maxBytes=5_000_000, backupCount=3),
        ]
    )


def resolve_download_directory(cli_args=None, env=None):
    """Resolve the download destination with env var priority over CLI args."""
    env = os.environ if env is None else env
    cli_args = sys.argv if cli_args is None else cli_args

    destination_folder = env.get('DESTINATION_FOLDER')
    if destination_folder:
        return os.path.expanduser(destination_folder)

    if len(cli_args) == 2:
        return os.path.expanduser(cli_args[1])

    return None


def run_forever(download_dir=None):
    log = logging.getLogger("main")
    interval = config.interval_seconds()
    while not stop_event.is_set():
        try:
            src.download_songs.main(download_dir)
        except Exception:
            # Never let one bad cycle kill the long-running container.
            log.exception("Cycle failed; will retry after the interval.")
        log.info("Sleeping %d seconds until next check.", interval)
        stop_event.wait(interval)


def main(argv=None):
    argv = sys.argv if argv is None else argv
    command = argv[1] if len(argv) > 1 and argv[1] in ("run", "once", "auth") else "run"
    if command == "auth":
        src.drive_upload.authorize()
        return 0

    setup_logging()
    src.setup_ffmpeg.main()

    path_args = [a for a in argv[1:] if a not in ("run", "once")]
    if len(path_args) > 1:
        usage()
        return 1
    download_dir = resolve_download_directory(["main.py"] + path_args)

    if command == "once":
        src.download_songs.main(download_dir)
        return 0

    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    run_forever(download_dir)
    return 0


def usage():
    print("Usage: python main.py [run|once|auth] [output_directory]")


if __name__ == '__main__':
    sys.exit(main())
