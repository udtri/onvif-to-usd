#!/usr/bin/env python3
"""
Simple RTSP Stream Capture Script

This script captures frames from a public RTSP stream and saves them for photogrammetry processing.
"""

import os
import sys
import time
import cv2
import argparse
from pathlib import Path
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description='Capture frames from public RTSP stream')
    parser.add_argument('--output-dir', type=str, default='./test_frames', 
                      help='Directory to save captured frames')
    parser.add_argument('--frames', type=int, default=30,
                      help='Number of frames to capture')
    parser.add_argument('--interval', type=float, default=1.0,
                      help='Interval between frames in seconds')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Public test RTSP stream
    rtsp_url = "rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4"
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Connecting to RTSP stream: {rtsp_url}")
    print(f"Saving frames to: {output_dir.absolute()}")
    
    # Open RTSP stream with OpenCV
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print("Failed to open RTSP stream with OpenCV.")
        # Try with explicit FFMPEG backend
        print("Trying with FFMPEG backend...")
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            print("Failed to open RTSP stream with FFMPEG backend.")
            return 1
    
    print("Successfully connected to RTSP stream.")
    
    # Capture frames
    frames_captured = 0
    while frames_captured < args.frames:
        ret, frame = cap.read()
        if not ret:
            print("Error reading frame from stream.")
            break
        
        # Save the frame as JPG
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{timestamp}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), frame)
        
        frames_captured += 1
        print(f"Captured frame {frames_captured}/{args.frames}")
        
        # Wait for the specified interval
        time.sleep(args.interval)
    
    # Release the capture
    cap.release()
    
    print(f"Captured {frames_captured} frames successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())