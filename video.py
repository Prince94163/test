import os
import requests
import urllib.parse
from pydub import AudioSegment
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to create a directory if it does not exist
def create_directory(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    except OSError as e:
        logger.error(f"Error creating directory {directory}: {e}")
        raise

# Function to download a file from a URL
def download_file(url, filename):
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            chunk_size = 1024 * 1024  # 1 MB chunks
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    logger.info(f"Downloading... {os.path.basename(filename)} - {os.path.getsize(filename)} bytes / {total_size} bytes")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file from {url}: {e}")
        raise

# Function to merge video with multiple audio tracks
def merge_video_with_multiple_audios(video_file, audio_files, output_file):
    try:
        # Merge audio files using pydub
        merged_audio = None
        for audio_file in audio_files:
            audio = AudioSegment.from_file(audio_file)
            if merged_audio is None:
                merged_audio = audio
            else:
                merged_audio = merged_audio.overlay(audio)

        # Export merged audio to a temporary file
        temp_audio_file = "merged_audio.mp3"
        merged_audio.export(temp_audio_file, format="mp3")

        # Run ffmpeg command to merge video with merged audio
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", video_file,
            "-i", temp_audio_file,
            "-c:v", "copy",
            "-c:a", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-y",  # Overwrite output file if exists
            output_file
        ]
        
        subprocess.run(ffmpeg_cmd, check=True)

        logger.info(f"Merging completed successfully. Output file: {output_file}")

    except Exception as e:
        logger.error(f"Error merging video with audio: {e}")
        raise

# Function to upload file to Google Drive
def upload_to_google_drive(file_path, folder_id):
    try:
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("/workspaces/filepress/credentials.json")  # Path to your credentials.json file
        drive = GoogleDrive(gauth)

        file = drive.CreateFile({'title': os.path.basename(file_path),
                                 'parents': [{'kind': 'drive#fileLink', 'id': folder_id}]})
        file.SetContentFile(file_path)
        file.Upload()
        logger.info(f"File '{os.path.basename(file_path)}' uploaded successfully to Google Drive!")
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {e}")
        raise

# Example usage
if __name__ == "__main__":
    # URLs of the video and audio files
    video_url = "https://iron-goindex.smitgoswami401.workers.dev/1:/Mirzapur%20S03%20E01%202024%20Hindi%20480p%20WEBRip%20ESub%20x264.mkv"
    audio_urls = [
        "https://iron-goindex.smitgoswami401.workers.dev/1:/HUB4VF_KAN_KAN.eac3"
    ]

    # Temporary filenames for downloaded files
    video_filename = os.path.basename(urllib.parse.urlparse(video_url).path)
    audio_filenames = []

    try:
        # Download video file
        logger.info("Downloading video file...")
        download_file(video_url, video_filename)

        # Download audio files
        for idx, audio_url in enumerate(audio_urls):
            audio_filename = f"audio_{idx}.mp3"  # Using mp3 format for simplicity
            logger.info(f"Downloading audio file {idx + 1}...")
            download_file(audio_url, audio_filename)
            audio_filenames.append(audio_filename)

        # Create download folder if not exists
        download_folder = "downloads"
        create_directory(download_folder)

        # Merge video with multiple audio tracks
        output_filename = os.path.join(download_folder, "tgmerged.mkv")
        logger.info("Merging video with multiple audio tracks...")
        merge_video_with_multiple_audios(video_filename, audio_filenames, output_filename)

        # Upload merged file to Google Drive
        drive_folder_id = "1H4G7vDV9WiDsKRqi3Tr7vEp-_oaZuVrt"  # Replace with your Google Drive folder ID
        logger.info(f"Uploading '{output_filename}' to Google Drive...")
        upload_to_google_drive(output_filename, drive_folder_id)

    except Exception as e:
        logger.error(f"Error: {e}")

    finally:
        # Clean up temporary files
        if os.path.exists(video_filename):
            os.remove(video_filename)
        for audio_filename in audio_filenames:
            if os.path.exists(audio_filename):
                os.remove(audio_filename)
