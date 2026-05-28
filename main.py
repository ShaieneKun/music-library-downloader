import sys
import os
import time
import src.setup_ffmpeg
import src.download_songs
import logging
from datetime import datetime


def setup_logging():
    """Setup logging configuration."""
    logs_dir = './logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    datetime_for_log = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{logs_dir}/{datetime_for_log}.log', mode='w')
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


def main():
    while True:
        setup_logging()
        src.setup_ffmpeg.main()

        options = sys.argv
        download_dir = resolve_download_directory(options)

        if len(options) > 2:
            usage()
            break

        if download_dir is not None:
            src.download_songs.main(download_dir)
        else:
            src.download_songs.main()

        time.sleep(3600)


def usage():
    print("Usage: python main.py <output_directory>")


if __name__ == '__main__':
    main()
