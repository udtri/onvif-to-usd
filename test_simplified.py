#!/usr/bin/env python3
"""
Simplified Test of ONVIF to USD Pipeline Using Mock Data

This script directly tests the code in the src directory focusing on:
1. Analyzing the test frames (mock data)
2. USD generation using the UsdBuilder
"""

import os
import sys
import logging
import glob
from pathlib import Path
import cv2
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the UsdBuilder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.usd_builder import UsdSceneBuilder

# Define paths
TEST_FRAMES_DIR = "./test_frames"
USD_OUTPUT = "./direct_test_scene.usda"

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def analyze_test_frames():
    """Analyze the test frames to understand what we're working with"""
    # Get list of test frames
    test_frames = sorted(glob.glob(os.path.join(TEST_FRAMES_DIR, "*.jpg")))
    print(f"Found {len(test_frames)} test frames in {TEST_FRAMES_DIR}")
    
    if not test_frames:
        print("No test frames found!")
        return None
    
    # Print info about first and last frames
    first_frame = test_frames[0]
    last_frame = test_frames[-1]
    
    print(f"First frame: {os.path.basename(first_frame)}")
    print(f"Last frame: {os.path.basename(last_frame)}")
    
    # Load and analyze a sample frame
    sample_img = cv2.imread(first_frame)
    if sample_img is not None:
        height, width, channels = sample_img.shape
        print(f"Frame dimensions: {width}x{height}, {channels} channels")
        
        # Save a small thumbnail for visualization
        thumbnail = cv2.resize(sample_img, (320, 240))
        thumbnail_path = "sample_frame_thumbnail.jpg"
        cv2.imwrite(thumbnail_path, thumbnail)
        print(f"Saved thumbnail of first frame to {thumbnail_path}")
        
        # Basic image stats
        brightness = np.mean(sample_img)
        contrast = np.std(sample_img)
        print(f"Image stats - Brightness: {brightness:.2f}, Contrast: {contrast:.2f}")
    else:
        print("Could not read sample frame")
    
    return test_frames

def generate_usd_scene(test_frames):
    """Generate a USD scene using the UsdBuilder"""
    print_section("GENERATING USD SCENE")
    
    if not test_frames:
        print("No test frames available")
        return False
    
    # Create USD builder
    builder = UsdSceneBuilder(
        image_dir=TEST_FRAMES_DIR,
        output_file=USD_OUTPUT
    )
    
    # Generate USD scene
    print(f"Generating USD scene at {USD_OUTPUT}")
    success = builder.build_scene()
    print(f"USD generation success: {success}")
    
    # Print the generated USD file
    if os.path.exists(USD_OUTPUT):
        print("\nGenerated USD file contents:")
        print("-" * 50)
        with open(USD_OUTPUT, 'r') as f:
            print(f.read())
        print("-" * 50)
        
        # Get file size
        file_size = os.path.getsize(USD_OUTPUT)
        print(f"USD file size: {file_size} bytes")
    else:
        print(f"USD file not created at {USD_OUTPUT}")
        return False
    
    return True

def main():
    """Main entry point"""
    print_section("ANALYZING TEST FRAMES")
    test_frames = analyze_test_frames()
    
    if test_frames:
        generate_usd_scene(test_frames)
    
    print_section("TEST COMPLETE")

if __name__ == "__main__":
    main()