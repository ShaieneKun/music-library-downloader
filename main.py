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


def main():
    while True:
        setup_logging()
        src.setup_ffmpeg.main()

        options = sys.argv
        # No arguments, use default download path
        if len(options) == 1:
            src.download_songs.main()
        elif len(options) == 2:
        # Given argument, use given download path

            src.download_songs.main(options[1])
        else:
            usage()
        time.sleep(3600)


def usage():
    print("Usage: python main.py <output_directory>")


if __name__ == '__main__':
    main()
