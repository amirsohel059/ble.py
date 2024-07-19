import os
import subprocess
import threading
import logging
import time
import signal
import sys
import pyaudio
from picamera2 import Picamera2, Preview

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Configuration settings
RESOLUTION = (1280, 720)
FPS = 30
SAMPLING_RATE = 44100
BUFFER_SIZE = 1024
VCODEC = 'libx264'
ACODEC = 'aac'
PIX_FMT = 'yuv420p'
OUTPUT_FILE = 'output.mp4'

# Initialize the camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = RESOLUTION
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.main.framerate = FPS
picam2.configure("preview")

# Initialize audio recording
p = pyaudio.PyAudio()
audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLING_RATE, input=True, frames_per_buffer=BUFFER_SIZE)

# FFmpeg command
ffmpeg_cmd = [
    'ffmpeg',
    '-y',  # Overwrite output file if it exists
    '-f', 'rawvideo',
    '-pixel_format', 'rgb24',
    '-video_size', f'{RESOLUTION[0]}x{RESOLUTION[1]}',
    '-framerate', str(FPS),
    '-i', '-',  # Video input from stdin
    '-f', 's16le',
    '-ar', str(SAMPLING_RATE),
    '-ac', '1',
    '-i', '-',  # Audio input from stdin
    '-c:v', VCODEC,
    '-c:a', ACODEC,
    '-pix_fmt', PIX_FMT,
    '-vsync', '1',
    OUTPUT_FILE
]

def signal_handler(sig, frame):
    logger.info("Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def capture_video():
    logger.info("Starting video capture")
    picam2.start()
    try:
        while True:
            frame = picam2.capture_array()
            video_pipe.stdin.write(frame.tobytes())
    except Exception as e:
        logger.error(f"Error capturing video: {e}")
    finally:
        picam2.stop()

def capture_audio():
    logger.info("Starting audio capture")
    try:
        while True:
            audio_data = audio_stream.read(BUFFER_SIZE)
            audio_pipe.stdin.write(audio_data)
    except Exception as e:
        logger.error(f"Error capturing audio: {e}")

def main():
    global video_pipe, audio_pipe

    try:
        video_pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        audio_pipe = video_pipe

        video_thread = threading.Thread(target=capture_video)
        audio_thread = threading.Thread(target=capture_audio)
        
        video_thread.start()
        audio_thread.start()
        
        logger.info("Press Ctrl+C to stop recording")
        video_thread.join()
        audio_thread.join()
        
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
    finally:
        audio_stream.stop_stream()
        audio_stream.close()
        p.terminate()
        if video_pipe:
            video_pipe.stdin.close()
            video_pipe.stderr.close()
            video_pipe.wait()

if __name__ == "__main__":
    main()
