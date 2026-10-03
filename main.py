import argparse
import logging
import os
import sys
import time
from datetime import datetime

import src.download_songs
import src.setup_ffmpeg

DEFAULT_INTERVAL_SECONDS = 3600

log = logging.getLogger(__name__)


def setup_logging():
    """Setup logging configuration."""
    logs_dir = './logs'
    os.makedirs(logs_dir, exist_ok=True)
    datetime_for_log = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{logs_dir}/{datetime_for_log}.log', mode='w')
        ]
    )


def resolve_download_directory(cli_dir=None, env=None):
    """Resolve the download destination with env var priority over CLI args."""
    env = os.environ if env is None else env

    destination_folder = env.get('DESTINATION_FOLDER')
    if destination_folder:
        return os.path.expanduser(destination_folder)

    if cli_dir:
        return os.path.expanduser(cli_dir)

    return None


def resolve_interval(cli_interval=None, env=None):
    """Resolve the seconds between runs: CLI arg, then env var, then default."""
    env = os.environ if env is None else env

    if cli_interval is not None:
        return cli_interval

    return int(env.get('DOWNLOAD_INTERVAL_SECONDS') or DEFAULT_INTERVAL_SECONDS)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Periodically download new songs from YouTube Music playlists.")
    parser.add_argument(
        'output_dir', nargs='?',
        help="Directory to save songs to (overridden by DESTINATION_FOLDER).")
    parser.add_argument(
        '--once', action='store_true',
        help="Run a single download pass and exit.")
    parser.add_argument(
        '--interval', type=int,
        help=f"Seconds between runs (default: DOWNLOAD_INTERVAL_SECONDS or {DEFAULT_INTERVAL_SECONDS}).")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    setup_logging()
    src.setup_ffmpeg.main()

    download_dir = resolve_download_directory(args.output_dir)
    interval = resolve_interval(args.interval)

    while True:
        src.download_songs.main(download_dir)

        if args.once:
            break

        log.info("Next run in %d seconds.", interval)
        time.sleep(interval)


if __name__ == '__main__':
    main()
