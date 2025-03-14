import os
import ffmpeg
import requests


def check_file_exists(file_path):
    """Check if the input file exists before processing."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Error: The input file '{file_path}' does not exist.")
    else:
        print(f"✔ File found: {file_path}")


def decompress_video(input_file, decompressed_file):
    """Decompress the video using FFmpeg and save it in MP4 format."""
    check_file_exists(input_file)

    # Ensure the output folder exists
    output_folder = os.path.dirname(decompressed_file)
    os.makedirs(output_folder, exist_ok=True)

    print(f"Decompressing video: {input_file} to {decompressed_file}")

    try:
        # FFmpeg command to decompress (remove audio, improve video quality)
        ffmpeg.input(input_file).output(
            decompressed_file,
            vcodec="libx264",  # Use H.264 codec for better quality
            preset="slow",  # Slower preset = better compression efficiency
            crf=18,  # Lower CRF = higher quality (18 is visually lossless)
            **{"b:v": "5M"},  # Set a higher bitrate (5 Mbps for better quality)
        ).run(overwrite_output=True)

        print(f"Decompression completed! File saved at: {decompressed_file}")
        return True

    except ffmpeg.Error as e:
        print(f"FFmpeg error: {e}")
        return False


def upload_to_onedrive(file_path, access_token, folder_id):
    """Uploads the given file to OneDrive using Microsoft Graph API."""
    file_name = os.path.basename(file_path)
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}:/{file_name}:/content"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream"
    }

    try:
        print(f"Uploading {file_name} to OneDrive...")

        with open(file_path, "rb") as file_data:
            response = requests.put(upload_url, headers=headers, data=file_data)

        if response.status_code in [200, 201]:
            print("Upload successful!")
        else:
            print("Upload failed:", response.json())

    except Exception as e:
        print("Upload Error:", str(e))


def main():
    # OneDrive API details (hardcoded)
    access_token = "YOUR_ACCESS_TOKEN"
    folder_id = "YOUR_ONEDRIVE_FOLDER_ID"

    # Input (compressed) video file
    input_video = r"INPUT VIDEO FILE PATH"

    # Output (decompressed) video file in a different location
    decompressed_video = r"Output (decompressed) video file in a different location PATH"

    # Run decompression
    success = decompress_video(input_video, decompressed_video)

    if success:
        # Upload the decompressed video to OneDrive
        upload_to_onedrive(decompressed_video, access_token, folder_id)


if __name__ == "__main__":
    main()
