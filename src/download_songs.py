import yt_dlp
import re
import os
import sys
import subprocess

# PLAYLIST_URL = ["https://music.youtube.com/browse/VLPL1Fdfnmz532fUiMPemHsxmyAyCJISoD9P"]  #test
PLAYLIST_URL = ["https://music.youtube.com/playlist?list=PL1Fdfnmz532d4UNrI7U1Uy9aQfsf_wcDs"]  #prod
DEFAULT_DOWNLOAD_DIR = "./auto-downloaded-songs"
FILENAME_FORMAT="%(title)s - %(uploader)s - %(id)s.%(ext)s"

def format_output_dir(output_dir):
    output_dir_formatted =  os.path.join(output_dir, FILENAME_FORMAT)

    return output_dir_formatted

def extract_ids_from_filenames(directory):
    """
    Extracts IDs from already downloaded files to filenames in a directory.

    Args:
        directory (str): The path to the directory.

    Returns:
        list: A list of extracted IDs.
    """

    ids = []
    try:
        for filename in os.listdir(directory):
            # improved regex
            match = re.search(r'- (?P<id>[^-]+)\.mp3$', filename)
            if match:
                extracted_id = match.group('id')
                ids.append(extracted_id)
        return ids
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found.8")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

def filter_url_ids_to_donwload(output_dir):
    """
    Checks if there are any already downloaded files
    If there are, remove them from the list of ids to download
    """
    print("\nIdentifying already downloaded songs, and new songs to download...\n")
    print("Identifying new songs to download...")

    command = ["yt-dlp", "--print", "id", "--no-warnings"] + PLAYLIST_URL
    result = subprocess.run(command, capture_output=True, text=True)
    all_ids_to_downlaod = result.stdout.strip().splitlines()

    print("Identifying already downloaded songs...\n")
    already_downloaded_ids = extract_ids_from_filenames(output_dir)

    id_subset_to_download = set(all_ids_to_downlaod) - set(already_downloaded_ids)

    ids = [ f"https://www.youtube.com/watch?v={id}" for id in id_subset_to_download ]

    print("All IDs to download: ", all_ids_to_downlaod)
    print("Already downloaded IDs: ",already_downloaded_ids)
    print("IDs that will be downloaded: ", id_subset_to_download)

    return ids

def download(output_dir=None, urls=PLAYLIST_URL):
    if output_dir is None:
        output_dir = DEFAULT_DOWNLOAD_DIR

    urls = filter_url_ids_to_donwload(output_dir)
    outtmpl = format_output_dir(output_dir)

    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'ffmpeg_location': './',
        'outtmpl': outtmpl,
        # ℹ️ See help(yt_dlp.postprocessor) for a list of available Postprocessors and their arguments
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }]
    }

    print("Starting donwload...\n")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(urls)
    print("\n!Donwload finished! 😁\n")

def main(output_dir=None):
    download(output_dir)

def usage():
    print("Usage: python download_songs.py <output_directory>")

if __name__ == '__main__':
    options = sys.argv
    if len(options) == 1:
        main()
    elif len(options) == 2:
        main(options[1])
    else:
        usage()

