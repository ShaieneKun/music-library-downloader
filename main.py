import sys
import src.setup_ffmpeg
import src.download_songs
import logging
from datetime import datetime

def setup_logging():
    """Setup logging configuration."""
    datetime_for_log = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'./logs/{datetime_for_log}.log', mode='w')
        ]
    )

def main():
    setup_logging() 
    src.setup_ffmpeg.main()

    options = sys.argv
    if len(options) == 2:
        src.download_songs.main()
    elif len(options) == 3:
        src.download_songs.main(options[1])
    else:
        usage()

def usage():
    print("Usage: python main.py <output_directory>")

if __name__ == '__main__':
    main()