#!/usr/bin/env python3
"""
Generate synthetic test frames for photogrammetry and USD pipeline.

This script creates synthetic test images that can be used to test the photogrammetry
and USD generation pipeline.
"""

import os
import sys
import numpy as np
import cv2
import argparse
from pathlib import Path
from datetime import datetime

def parse_args():
    parser = argparse.ArgumentParser(description='Generate synthetic test frames')
    parser.add_argument('--output-dir', type=str, default='./test_frames',
                      help='Directory to save generated frames')
    parser.add_argument('--frames', type=int, default=30,
                      help='Number of frames to generate')
    parser.add_argument('--width', type=int, default=640,
                      help='Image width')
    parser.add_argument('--height', type=int, default=480,
                      help='Image height')
    parser.add_argument('--seed', type=int, default=42,
                      help='Random seed')
    return parser.parse_args()

def draw_3d_scene(img, frame_idx, total_frames, width, height):
    """Draw a simple 3D scene with varying camera angle"""
    # Set up scene parameters
    center_x, center_y = width // 2, height // 2
    base_size = min(width, height) // 4
    
    # Create background gradient
    for y in range(height):
        color = int(y * 255 / height)
        cv2.line(img, (0, y), (width, y), (color, 255-color, 128), 1)
    
    # Calculate camera position based on frame index (circular motion)
    angle = 2 * np.pi * frame_idx / total_frames
    camera_x = np.sin(angle) * 100
    camera_z = np.cos(angle) * 100
    perspective_factor = 1000 / (1000 + camera_z)
    
    # Draw cube
    points_3d = np.array([
        [-base_size, -base_size, -base_size],  # 0: bottom-back-left
        [base_size, -base_size, -base_size],   # 1: bottom-back-right
        [base_size, base_size, -base_size],    # 2: bottom-front-right
        [-base_size, base_size, -base_size],   # 3: bottom-front-left
        [-base_size, -base_size, base_size],   # 4: top-back-left
        [base_size, -base_size, base_size],    # 5: top-back-right
        [base_size, base_size, base_size],     # 6: top-front-right
        [-base_size, base_size, base_size]     # 7: top-front-left
    ])
    
    # Project 3D points to 2D screen
    points_2d = []
    for point in points_3d:
        x, y, z = point
        # Apply camera position offset
        x = x - camera_x
        z = z + 500  # Push away from camera
        
        # Simple perspective projection
        factor = 1000 / (1000 + z)
        screen_x = int(center_x + x * factor)
        screen_y = int(center_y + y * factor)
        points_2d.append((screen_x, screen_y))
    
    # Draw cube edges
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Bottom face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Top face
        (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting edges
    ]
    
    for edge in edges:
        start_point = points_2d[edge[0]]
        end_point = points_2d[edge[1]]
        cv2.line(img, start_point, end_point, (0, 255, 255), 2)
    
    # Draw a pyramid
    pyramid_height = base_size * 2
    pyramid_top = (int(center_x), int(center_y - pyramid_height * perspective_factor))
    pyramid_base = [
        (int(center_x - base_size * perspective_factor), int(center_y + base_size * perspective_factor)),
        (int(center_x + base_size * perspective_factor), int(center_y + base_size * perspective_factor)),
        (int(center_x + base_size * perspective_factor), int(center_y - base_size * perspective_factor)),
        (int(center_x - base_size * perspective_factor), int(center_y - base_size * perspective_factor))
    ]
    
    # Draw pyramid edges
    for point in pyramid_base:
        cv2.line(img, pyramid_top, point, (255, 0, 0), 2)
    
    for i in range(4):
        cv2.line(img, pyramid_base[i], pyramid_base[(i + 1) % 4], (255, 0, 0), 2)
    
    # Draw a sphere (circle from this view)
    sphere_x = center_x - 200 + camera_x * 0.5
    sphere_y = center_y + 50
    sphere_radius = int(50 * perspective_factor)
    cv2.circle(img, (int(sphere_x), sphere_y), sphere_radius, (0, 0, 255), -1)
    
    # Add some texture patterns for better feature detection
    for i in range(10):
        x = np.random.randint(0, width)
        y = np.random.randint(0, height)
        size = np.random.randint(5, 30)
        cv2.rectangle(img, (x, y), (x + size, y + size), (255, 255, 255), -1)
    
    # Add frame information
    cv2.putText(img, f"Frame: {frame_idx+1}/{total_frames}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return img

def main():
    args = parse_args()
    
    # Set random seed for reproducibility
    np.random.seed(args.seed)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {args.frames} synthetic test frames...")
    print(f"Saving frames to: {output_dir.absolute()}")
    
    # Generate frames
    for i in range(args.frames):
        # Create blank image
        img = np.zeros((args.height, args.width, 3), dtype=np.uint8)
        
        # Draw 3D scene with varying camera angle
        draw_3d_scene(img, i, args.frames, args.width, args.height)
        
        # Save the frame as JPG
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"frame_{i:03d}_{timestamp}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), img)
        
        print(f"Generated frame {i+1}/{args.frames}")
    
    print(f"Successfully generated {args.frames} test frames.")
    return 0

if __name__ == "__main__":
    sys.exit(main())