import os
import shutil
import sys


def ffmpeg_is_available():
    return shutil.which("ffmpeg") is not None


def ffprobe_is_available():
    return shutil.which("ffprobe") is not None


def main():
    print("Checking for system-installed ffmpeg and ffprobe...")
    ffmpeg_available = ffmpeg_is_available()
    ffprobe_available = ffprobe_is_available()

    if ffmpeg_available and ffprobe_available:
        print("System ffmpeg and ffprobe are available on PATH, continuing...\n")
        return

    missing = []
    if not ffmpeg_available:
        missing.append("ffmpeg")
    if not ffprobe_available:
        missing.append("ffprobe")

    print(
        "Error: The following required executable(s) are not available on PATH: "
        + ", ".join(missing)
        + ".\nPlease install the system ffmpeg package and try again."
    )
    sys.exit(1)


if __name__ == '__main__':
    main()
