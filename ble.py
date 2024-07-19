import os
import sys
import time
import threading
import subprocess
from fractions import Fraction

import numpy as np
import pyaudio
import picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput

# Configurable parameters
VIDEO_RESOLUTION = (1280, 720)  # Resolution for the video
FPS = 30                        # Frames per second for the video
AUDIO_SAMPLING_RATE = 16000     # Audio sampling rate in Hz
AUDIO_CHANNELS = 1              # Number of audio channels
BUFFER_LENGTH = 1024            # Audio buffer length
VIDEO_CODEC = 'libx264'         # Video codec
AUDIO_CODEC = 'aac'             # Audio codec
PIXEL_FORMAT = 'yuv420p'        # Pixel format

# Error handling and user input functions
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"An error occurred: {e}")
            sys.exit(1)
    return wrapper

@handle_errors
def get_user_input(prompt):
    return input(prompt)

# Audio recording setup
class AudioRecorder:
    def __init__(self, filename):
        self.filename = filename
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False

    def start_recording(self):
        self.stream = self.audio.open(format=pyaudio.paInt16,
                                      channels=AUDIO_CHANNELS,
                                      rate=AUDIO_SAMPLING_RATE,
                                      input=True,
                                      frames_per_buffer=BUFFER_LENGTH)
        self.is_recording = True
        print("Audio recording started")
        self._record()

    def _record(self):
        while self.is_recording:
            data = self.stream.read(BUFFER_LENGTH)
            self.frames.append(data)

    def stop_recording(self):
        self.is_recording = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        with open(self.filename, 'wb') as f:
            for frame in self.frames:
                f.write(frame)
        print("Audio recording stopped")

# Video recording setup
class VideoRecorder:
    def __init__(self, filename):
        self.filename = filename
        self.camera = picamera2.Picamera2()
        self.camera_config = self.camera.create_still_configuration(main={"size": VIDEO_RESOLUTION})
        self.camera.configure(self.camera_config)
        self.encoder = H264Encoder()
        self.output = FileOutput(self.filename)

    def start_recording(self):
        self.camera.start_recording(self.encoder, self.output)
        print("Video recording started")

    def stop_recording(self):
        self.camera.stop_recording()
        self.output.close()
        print("Video recording stopped")

# Function to start recording audio and video
def start_recording(video_file, audio_file):
    audio_recorder = AudioRecorder(audio_file)
    video_recorder = VideoRecorder(video_file)

    audio_thread = threading.Thread(target=audio_recorder.start_recording)
    video_thread = threading.Thread(target=video_recorder.start_recording)

    audio_thread.start()
    video_thread.start()

    get_user_input("Press Enter to stop recording...")

    audio_recorder.stop_recording()
    video_recorder.stop_recording()

    audio_thread.join()
    video_thread.join()

    return video_file, audio_file

# Function to merge audio and video using ffmpeg
@handle_errors
def merge_audio_video(video_file, audio_file, output_file):
    command = [
        'ffmpeg',
        '-y',  # Overwrite output file if it exists
        '-i', video_file,
        '-i', audio_file,
        '-c:v', VIDEO_CODEC,
        '-c:a', AUDIO_CODEC,
        '-pix_fmt', PIXEL_FORMAT,
        '-vsync', '1',  # Sync video with audio
        output_file
    ]
    subprocess.run(command, check=True)
    print(f"Audio and video merged into {output_file}")

def main():
    video_file = 'video.h264'
    audio_file = 'audio.wav'
    output_file = 'output.mp4'

    video_file, audio_file = start_recording(video_file, audio_file)
    merge_audio_video(video_file, audio_file, output_file)

if __name__ == "__main__":
    main()
