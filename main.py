import sys
import src.setup_ffmpeg
import src.download_songs


def main():
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