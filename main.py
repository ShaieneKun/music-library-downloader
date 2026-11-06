import sys
import os
import signal
import threading
import time
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import src.setup_ffmpeg
import src.download_songs
import src.drive_upload
import src.report
import src.updater
from src import config

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'

stop_event = threading.Event()


def setup_logging():
    """Log to stdout (docker logs) and a size-capped file."""
    logs_dir = os.environ.get('LOG_DIR') or './logs'
    os.makedirs(logs_dir, exist_ok=True)

    # Root logger passes everything; handlers decide what they keep. The
    # per-cycle run log (see cycle_logging) captures DEBUG, console/app.log INFO.
    console = logging.StreamHandler(sys.stdout)
    app_log = RotatingFileHandler(f'{logs_dir}/app.log',
                                  maxBytes=5_000_000, backupCount=3)
    for handler in (console, app_log):
        handler.setLevel(logging.INFO)
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT,
                        handlers=[console, app_log])
    # Keep chatty libraries out of the debug log.
    for noisy in ("urllib3", "googleapiclient", "google", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.INFO)


class _ErrorCounter(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.count = 0

    def emit(self, record):
        self.count += 1


def prune_old_logs(logs_dir, days):
    cutoff = time.time() - days * 86400
    for name in os.listdir(logs_dir):
        path = os.path.join(logs_dir, name)
        if name.startswith("cycle-") and name.endswith(".log") \
                and os.path.getmtime(path) < cutoff:
            os.remove(path)


def run_logged_cycle(download_dir=None, daemon_started=None, daemon_cycles=None):
    """Run one cycle writing a DEBUG run log, then ship it to Google Drive.

    `daemon_started` (time.monotonic() at start) and `daemon_cycles` are given
    only by the long-running service; without them this is a manual run.
    """
    log = logging.getLogger("main")
    logs_dir = os.environ.get('LOG_DIR') or './logs'
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(logs_dir, f"cycle-{stamp}.log")

    file_handler = logging.FileHandler(log_path, mode="w")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    errors = _ErrorCounter()
    root = logging.getLogger()
    previous_level = root.level
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(errors)

    report = src.report.CycleReport(log_file=log_path, hostname=config.hostname())
    if daemon_started is not None:
        report.mode = "daemon"
        report.daemon_uptime_seconds = time.monotonic() - daemon_started
        report.daemon_cycles = daemon_cycles
    try:
        try:
            src.download_songs.run_cycle(download_dir, report=report)
        except Exception:
            log.exception("Cycle failed.")
        report.errors = errors.count
        log.info("\n%s", report.render())
    finally:
        root.removeHandler(file_handler)
        root.removeHandler(errors)
        root.setLevel(previous_level)
        file_handler.close()

    keep = report.had_activity or config.log_keep_idle()
    if not keep:
        os.remove(log_path)
        return report
    if config.drive_enabled():
        try:
            src.drive_upload.upload_logfile(log_path)
        except Exception as exc:
            log.error("Could not upload run log to Google Drive: %s", exc)
    prune_old_logs(logs_dir, config.log_retention_days())
    return report


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
    updater = src.updater.AutoUpdater()
    started = time.monotonic()
    cycles = 0
    while not stop_event.is_set():
        updater.maybe_update()
        cycles += 1
        try:
            run_logged_cycle(download_dir, daemon_started=started,
                             daemon_cycles=cycles)
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
        run_logged_cycle(download_dir)
        return 0

    signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
    signal.signal(signal.SIGINT, lambda *_: stop_event.set())
    run_forever(download_dir)
    return 0


def usage():
    print("Usage: python main.py [run|once|auth] [output_directory]")


if __name__ == '__main__':
    sys.exit(main())
