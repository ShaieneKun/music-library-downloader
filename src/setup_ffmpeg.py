import requests
import tarfile
import os
import sys
import shutil

FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz'
FFMPEG_TAR_FILENAME = 'ffmpeg-master-latest-linux64-gpl.tar.xz'
# FFMPEG_URL = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2025-03-09-12-54/ffmpeg-N-118714-ge934fd96c1-linux64-gpl.tar.xz'
# FFMPEG_TAR_FILENAME = 'ffmpeg-N-118714-ge934fd96c1-linux64-gpl.tar.xz'

def ffmpeg_is_already_downloaded():
    return os.path.exists("ffmpeg")

def ffprobe_is_already_downloaded():
    return os.path.exists("ffprobe")


def download_file(url):
    print("Starting ffmpeg download now...")
    local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)
    print("ffmpeg download has finished...")
    return local_filename


def extract_and_move(tar_xz_path, file_path_in_tar):
    """
    Extracts a file from a .tar.xz archive, moves it to the current working directory,
    removes the extracted directory structure, and deletes the .tar.xz file.

    Args:
        tar_xz_path (str): The path to the .tar.xz archive.
        file_path_in_tar (str): The path to the file within the archive (e.g., "subdirectory/filename.txt").
        output_file_name (str): The desired name for the extracted file in the current working directory.
    """
    print("Starting ffmpeg and ffmprobe extract now...")
    for output_file_name in ("ffmpeg", "ffprobe"):
        file_in_tar = file_path_in_tar + output_file_name
        try:
            with tarfile.open(tar_xz_path, "r:xz") as tar:
                member = tar.getmember(file_in_tar)
                # get the directory inside the tar
                tar.extract(member)
            shutil.move(member.name, output_file_name)
            print(
                f"File '{file_in_tar}' extracted to '{output_file_name}', original directory and .tar.xz removed.")

        except FileNotFoundError:
            print(f"Error: File '{tar_xz_path}' not found.")
        except KeyError:
            print(f"Error: File '{file_path_in_tar}' not found in the archive.")
        except Exception as e:
            print(f"An error occurred: {e}")

    if not ffmpeg_is_already_downloaded() and not ffprobe_is_already_downloaded():
        print("There was an issue extracting ffmpeg, exiting...")
        sys.exit(1)

    # shutil.rmtree('ffmpeg-master-latest-linux64-gpl')
    os.remove(tar_xz_path)
    print("ffmpeg extract has finished...")

def main():
    print("Checking if ffmpeg is already setup...")
    if ffmpeg_is_already_downloaded() and ffprobe_is_already_downloaded():
        print("ffmpeg is already setup, skipping setup again...\n")
        return

    print("ffmpeg is not setup, starting setup now...\n")

    download_file(FFMPEG_URL)
    extract_and_move(
        FFMPEG_TAR_FILENAME,
        "ffmpeg-master-latest-linux64-gpl/bin/"
        # "ffmpeg-N-118714-ge934fd96c1-linux64-gpl/bin/ffmpeg"
    )

    print("\nffmpeg setup is finished!\n")


if __name__ == '__main__':
    main()
