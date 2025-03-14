"""
Video Recording, Compression, and OneDrive Upload System

This program continuously records traffic videos in 5-minute segments, compresses them using FFmpeg, and uploads them to OneDrive.

Classes:VideoRecorder
Handles:
- Continuous video recording from the webcam
- Compression of recorded video segments using FFmpeg
- Uploading compressed videos to OneDrive

Usage:
-Run the program to start recording:
-Press 'q' to manually stop recording.

Pipeline:
1. Video Capture: Captures live footage from the webcam.
2. Video Segmentation: Saves recordings in 5-minute segments.
3. Compression: Uses FFmpeg to reduce file size.
4. Cloud Upload: Uploads the compressed video to OneDrive.
5. Loop: The process continues indefinitely until manually stopped.

Requirements:
- Python 3.x
- OpenCV (`pip install opencv-python`)
- Requests (`pip install requests`)
- FFmpeg (must be installed on your system)
- A valid OneDrive API access token
"""

import os
import cv2
import time
import threading
import requests
import subprocess


class VideoRecorder:
    """
    Handles continuous video recording in 5-minute segments, compresses videos using FFmpeg,
    and uploads them to OneDrive using Microsoft Graph API.
    """

    def __init__(self, output_directory, folder_id, access_token, segment_duration=300, fps=20):
        """
        Initializes the VideoRecorder class.

        :param output_directory: Directory where video files will be saved.
        :param folder_id: OneDrive folder ID for uploading videos.
        :param access_token: Access token for OneDrive API authentication.
        :param segment_duration: Duration of each video segment in seconds (default is 300 seconds / 5 minutes).
        :param fps: Frames per second for recording (default is 20 fps).
        """
        self.output_directory = self.setup_output_directory(output_directory)
        self.folder_id = folder_id
        self.access_token = access_token
        self.segment_duration = segment_duration
        self.fps = fps
        self.cap = self.initialize_camera()
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    def setup_output_directory(self, directory):
        """
        Ensures the output directory exists, creating it if necessary.

        :param directory: Path of the output directory.
        :return: The same directory path.
        """
        os.makedirs(directory, exist_ok=True)
        return directory

    def initialize_camera(self):
        """
        Initializes the camera and sets resolution.

        :return: OpenCV VideoCapture object.
        """
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not cap.isOpened():
            print("Error: Could not access the camera.")
            exit()
        return cap

    def generate_filename(self):
        """
        Generates a timestamped filename for video storage.

        :return: Full path of the video filename.
        """
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        return os.path.join(self.output_directory, f"video_{timestamp}.mp4")

    def compress_video(self, input_file):
        """
        Compresses a video file using FFmpeg and removes the original file upon success.

        :param input_file: Path of the original uncompressed video file.
        :return: Path of the compressed video file.
        """
        base_name, ext = os.path.splitext(input_file)
        compressed_file = f"{base_name}_compressed{ext}"

        command = [
            "ffmpeg", "-i", input_file,
            "-vcodec", "libx264", "-crf", "28", "-preset", "fast",
            compressed_file, "-y"
        ]

        try:
            subprocess.run(command, check=True)
            os.remove(input_file)  # Delete the original file after compression
            print(f"Compressed video saved: {compressed_file}")
            return compressed_file
        except subprocess.CalledProcessError as e:
            print(f"Error compressing video: {e}")
            return input_file  # Upload original if compression fails

    def get_upload_url(self, video_filename):
        """
        Constructs the OneDrive API upload URL.

        :param video_filename: Name of the file to be uploaded.
        :return: OneDrive API upload URL.
        """
        return f"https://graph.microsoft.com/v1.0/me/drive/items/{self.folder_id}:/{os.path.basename(video_filename)}:/content"

    def get_headers(self):
        """
        Generates the authentication headers for OneDrive API requests.

        :return: Dictionary containing authorization and content type headers.
        """
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "video/mp4"
        }

    def upload_video(self, video_filename):
        """
        Uploads a video file to OneDrive using Microsoft Graph API.

        :param video_filename: Path of the file to be uploaded.
        """

        def upload():
            upload_url = self.get_upload_url(video_filename)
            headers = self.get_headers()

            try:
                with open(video_filename, "rb") as video_file:
                    response = requests.put(upload_url, headers=headers, data=video_file)

                if response.status_code == 201:
                    print(f"Successfully uploaded: {video_filename}")
                else:
                    print(f"Upload error: {response.status_code}")
                    print(response.json())
            except Exception as e:
                print(f"An error occurred during upload: {e}")

        threading.Thread(target=upload, daemon=True).start()

    def process_video(self, video_filename):
        """
        Runs video compression and uploads the compressed file in a separate thread.

        :param video_filename: Path of the recorded video file.
        """

        def process():
            compressed_filename = self.compress_video(video_filename)
            self.upload_video(compressed_filename)

        threading.Thread(target=process, daemon=True).start()

    def record_continuous(self):
        """
        Records continuous 5-minute video segments and processes them asynchronously.
        """
        frame_size = (640, 480)
        print(f"Continuous recording started. Videos will be saved to: {self.output_directory}")

        while True:
            video_filename = self.generate_filename()
            out = cv2.VideoWriter(video_filename, self.fourcc, self.fps, frame_size)
            print(f"Recording: {video_filename}")

            start_time = time.monotonic()
            end_time = start_time + self.segment_duration
            frame_interval = 1 / self.fps

            try:
                while time.monotonic() < end_time:
                    frame_start = time.monotonic()

                    ret, frame = self.cap.read()
                    if not ret:
                        print("Error: Failed to capture frame.")
                        break

                    out.write(frame)
                    cv2.imshow("Recording... Press 'q' to stop", frame)

                    elapsed = time.monotonic() - frame_start
                    remaining_time = frame_interval - elapsed
                    if remaining_time > 0:
                        time.sleep(remaining_time)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("Stopping recording manually.")
                        out.release()
                        self.close_camera()
                        return
            finally:
                out.release()
                print(f"Video saved: {video_filename}")

            self.process_video(video_filename)
            print("Processing (compression & upload) in background... Starting next segment.")

    def close_camera(self):
        """
        Releases the camera and closes OpenCV windows.
        """
        self.cap.release()
        cv2.destroyAllWindows()


# Main script execution
def main():
    # Define the local folder path to store recorded videos
    output_directory = "YOUR LOCAL FOLDER PATH"
    # Specify the OneDrive folder ID where videos will be uploaded
    folder_id = "YOUR_ONEDRIVE_FOLDER_ID"
    # Provide the OneDrive access token for authentication
    access_token = "YOUR_ACCESS_TOKEN"

    # Create an instance of VideoRecorder with the specified parameters
    recorder = VideoRecorder(output_directory, folder_id, access_token)
    # Start continuous video recording in 5-minute segments
    recorder.record_continuous()


if __name__ == "__main__":
    main()
