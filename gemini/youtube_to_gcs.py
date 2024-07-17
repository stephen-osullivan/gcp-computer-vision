from dotenv import load_dotenv
from google.cloud import storage
import moviepy.editor as mp
import yt_dlp

import os

load_dotenv()
PROJECT_ID = os.environ.get('PROJECT_ID')
BUCKET_ID = os.environ.get('BUCKET_ID')
YOUTUBE_URL = "https://youtu.be/cwLgUYg4Gn8?si=vWAt4vG-egnMnxxv"
FILE_PREFIX = "formulae_2021_london"

# Set up GCS client
client = storage.Client(project=PROJECT_ID)

# Function to download YouTube video
def download_youtube_video(url, output_path, quality='720p'):
    ydl_opts = {
        'format': f'bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality[:-1]}][ext=mp4]/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s')
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        filename = ydl.prepare_filename(info)
        
        # Ensure the filename ends with .mp4
        if not filename.endswith('.mp4'):
            filename = os.path.splitext(filename)[0] + '.mp4'
        
        if os.path.exists(filename):
            print(f"File {filename} already exists. Skipping download.")
            return filename
        
        # If the file doesn't exist, proceed with the download
        ydl.download([url])
    
    return filename

# Function to split video into chunks
def split_video(input_file, output_path, chunk_length=600):  # 600 seconds = 10 minutes
    video = mp.VideoFileClip(input_file)
    duration = video.duration
    chunks = []

    for start in range(0, int(duration), chunk_length):
        end = min(start + chunk_length, duration)
        chunk = video.subclip(start, end)
        output_file = os.path.join(output_path, f"chunk_{start//chunk_length+1}.mp4")
        chunk.write_videofile(output_file)
        chunks.append(output_file)

    video.close()
    return chunks

# Function to upload file to GCS
def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name} in bucket {bucket_name}.")

# Main process
def main():
    youtube_url = YOUTUBE_URL  # Replace with your YouTube video URL
    local_file_path = "youtube"
    chunks_path = "video_chunks"
    bucket_name = BUCKET_ID  # Replace with your GCS bucket name

    # Create directories if they don't exist
    os.makedirs(local_file_path, exist_ok=True)
    os.makedirs(chunks_path, exist_ok=True)

    # Download YouTube video
    downloaded_file = download_youtube_video(youtube_url, local_file_path)
    print('Video downloaded.')
    # Split video into chunks
    chunk_files = split_video(downloaded_file, chunks_path)

    # Upload chunks to GCS
    for i, chunk in enumerate(chunk_files):
        gcs_file_name = f"{FILE_PREFIX}_{i+1}.mp4"
        upload_to_gcs(bucket_name, chunk, gcs_file_name)

    # Clean up local files
    os.remove(downloaded_file)
    for chunk in chunk_files:
        os.remove(chunk)

if __name__ == "__main__":
    main()