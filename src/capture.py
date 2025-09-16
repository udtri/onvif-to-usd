#!/usr/bin/env python3
"""
ONVIF Camera Frame Capture Module

This module connects to ONVIF cameras, retrieves RTSP stream URLs,
and captures frames at regular intervals.
"""

import os
import sys
import time
import logging
import yaml
import cv2
import numpy as np
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

# Try to import zeep for ONVIF
try:
    from onvif import ONVIFCamera
    from zeep.exceptions import Fault as ZeepFault
    HAS_ONVIF = True
except ImportError:
    HAS_ONVIF = False
    logging.warning("onvif-zeep package not found. ONVIF discovery disabled.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('camera_capture.log')
    ]
)

logger = logging.getLogger('onvif_capture')

class CameraCapture:
    """Handles ONVIF camera discovery and frame capture"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the camera capture system
        
        Args:
            config_path: Path to the YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.cameras = self.config.get('cameras', [])
        self.settings = self.config.get('settings', {})
        self.capture_settings = self.settings.get('capture', {})
        self.output_dir = self._prepare_output_dir()
        self.retry_delay = 5  # seconds
        self.max_retries = 5
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Load YAML configuration
        
        Args:
            config_path: Path to the config file
            
        Returns:
            Dict containing configuration values
        """
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            sys.exit(1)
    
    def _prepare_output_dir(self) -> Path:
        """
        Create output directory if it doesn't exist
        
        Returns:
            Path to output directory
        """
        # Use config output_dir or default to ./images
        output_dir = self.capture_settings.get('output_dir', './images')
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving frames to {path.absolute()}")
        return path
    
    def get_rtsp_uri(self, camera: Dict) -> str:
        """
        Get RTSP stream URI from camera
        
        Args:
            camera: Camera configuration dictionary
            
        Returns:
            RTSP URI string
        """
        # If RTSP URL is provided in config, use it directly
        if 'rtsp_url' in camera and camera['rtsp_url']:
            logger.info(f"Using provided RTSP URL for camera '{camera.get('name', 'unnamed')}'")
            return camera['rtsp_url']
        
        # If no ONVIF support or missing parameters, return empty string
        if not HAS_ONVIF or not all(k in camera for k in ['host', 'onvif_port', 'username', 'password']):
            logger.error(f"Cannot get RTSP URI for camera '{camera.get('name', 'unnamed')}': "
                       f"Missing ONVIF library or required parameters")
            return ""
        
        # Try to get RTSP URI using ONVIF
        try:
            logger.info(f"Discovering RTSP URI for camera '{camera.get('name', 'unnamed')}' via ONVIF")
            mycam = ONVIFCamera(
                camera['host'], 
                camera['onvif_port'], 
                camera['username'], 
                camera['password']
            )
            
            # Create media service
            media_service = mycam.create_media_service()
            profiles = media_service.GetProfiles()
            
            # Get URI from first profile
            if profiles:
                token = profiles[0]._token
                request = media_service.create_type('GetStreamUri')
                request.ProfileToken = token
                request.StreamSetup = {'Stream': 'RTP-Unicast', 'Transport': {'Protocol': 'RTSP'}}
                uri = media_service.GetStreamUri(request)
                
                # Return the URI
                if hasattr(uri, 'Uri') and uri.Uri:
                    logger.info(f"Successfully discovered RTSP URI via ONVIF")
                    return uri.Uri
            
            logger.warning(f"No stream profiles found for camera '{camera.get('name', 'unnamed')}'")
            return ""
            
        except ZeepFault as zf:
            logger.error(f"ONVIF fault for camera '{camera.get('name', 'unnamed')}': {zf}")
            return ""
        except Exception as e:
            logger.error(f"Failed to get RTSP URI for camera '{camera.get('name', 'unnamed')}': {e}")
            return ""
    
    def capture_frames_opencv(self, rtsp_uri: str, camera_name: str) -> bool:
        """
        Capture frames using OpenCV
        
        Args:
            rtsp_uri: RTSP URI to capture from
            camera_name: Name of the camera for logging
            
        Returns:
            True if successful, False otherwise
        """
        if not rtsp_uri:
            logger.error(f"Empty RTSP URI for camera '{camera_name}'")
            return False
        
        # Get capture settings from config
        frame_interval = self.capture_settings.get('frame_interval', 5)  # frames
        total_frames = self.capture_settings.get('total_frames', 100)  # total frames to capture
        fps = 1  # 1 frame per second
        
        # Open video capture with FFMPEG backend
        cap = cv2.VideoCapture(rtsp_uri, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            logger.error(f"Failed to open video stream for camera '{camera_name}'")
            return False
        
        logger.info(f"Successfully opened stream for camera '{camera_name}'")
        
        # Calculate frame delay based on source FPS and our target FPS
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 30  # Assume 30 if we can't detect
        frame_delay = 1.0 / fps  # in seconds
        
        frames_captured = 0
        frame_count = 0
        retry_count = 0
        last_frame_time = time.time()
        
        try:
            while frames_captured < total_frames:
                # Respect frame rate
                current_time = time.time()
                time_elapsed = current_time - last_frame_time
                
                if time_elapsed < frame_delay:
                    time.sleep(frame_delay - time_elapsed)
                
                # Capture frame
                ret, frame = cap.read()
                
                if not ret:
                    retry_count += 1
                    logger.warning(f"Failed to read frame {frame_count}. Retry {retry_count}/{self.max_retries}")
                    
                    if retry_count >= self.max_retries:
                        logger.error(f"Max retries reached. Stopping capture for camera '{camera_name}'")
                        break
                    
                    # Try to reopen the stream
                    cap.release()
                    time.sleep(self.retry_delay)
                    cap = cv2.VideoCapture(rtsp_uri, cv2.CAP_FFMPEG)
                    
                    if not cap.isOpened():
                        logger.error(f"Failed to reopen stream for camera '{camera_name}'")
                        break
                    
                    continue
                
                # Reset retry counter on successful frame
                retry_count = 0
                frame_count += 1
                
                # Capture every Nth frame based on frame_interval
                if frame_count % frame_interval == 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{camera_name}_img_{frames_captured:06d}.jpg"
                    filepath = self.output_dir / filename
                    
                    cv2.imwrite(str(filepath), frame)
                    frames_captured += 1
                    
                    logger.info(f"Captured frame {frames_captured}/{total_frames} for camera '{camera_name}'")
                
                last_frame_time = time.time()
                
            logger.info(f"Completed capturing {frames_captured} frames for camera '{camera_name}'")
            return frames_captured > 0
            
        except KeyboardInterrupt:
            logger.info("Capture interrupted by user")
            return frames_captured > 0
        except Exception as e:
            logger.error(f"Error during OpenCV capture: {e}")
            return False
        finally:
            cap.release()
    
    def capture_frames_ffmpeg(self, rtsp_uri: str, camera_name: str) -> bool:
        """
        Capture frames using ffmpeg command line as fallback
        
        Args:
            rtsp_uri: RTSP URI to capture from
            camera_name: Name of the camera for logging
            
        Returns:
            True if successful, False otherwise
        """
        if not rtsp_uri:
            logger.error(f"Empty RTSP URI for camera '{camera_name}'")
            return False
        
        # Get capture settings from config
        frame_interval = self.capture_settings.get('frame_interval', 5)  # frames
        total_frames = self.capture_settings.get('total_frames', 100)  # total frames to capture
        fps = 1  # 1 frame per second
        
        # Prepare output filename pattern
        output_pattern = str(self.output_dir / f"{camera_name}_img_%06d.jpg")
        
        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', rtsp_uri,            # Input URI
            '-r', str(fps),            # Output frame rate
            '-vf', f'select=not(mod(n\\,{frame_interval}))',  # Select every Nth frame
            '-frames:v', str(total_frames),  # Limit total frames
            '-q:v', '1',               # Quality (1 = highest)
            '-update', '1',            # Overwrite existing files
            output_pattern             # Output pattern
        ]
        
        logger.info(f"Starting ffmpeg capture for camera '{camera_name}'")
        
        try:
            # Execute ffmpeg command
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor the process
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"ffmpeg failed with return code {process.returncode}: {stderr}")
                return False
            
            logger.info(f"Successfully captured frames using ffmpeg for camera '{camera_name}'")
            return True
            
        except subprocess.SubprocessError as e:
            logger.error(f"Subprocess error during ffmpeg capture: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during ffmpeg capture: {e}")
            return False
    
    def capture_all_cameras(self):
        """Capture frames from all configured cameras"""
        for camera in self.cameras:
            camera_name = camera.get('name', 'unnamed')
            logger.info(f"Processing camera '{camera_name}'")
            
            # Get RTSP URI (try ONVIF first, then fallback to config)
            rtsp_uri = self.get_rtsp_uri(camera)
            
            if not rtsp_uri:
                logger.error(f"No RTSP URI available for camera '{camera_name}'. Skipping.")
                continue
            
            # Try OpenCV first
            logger.info(f"Attempting to capture frames using OpenCV for camera '{camera_name}'")
            opencv_success = self.capture_frames_opencv(rtsp_uri, camera_name)
            
            # If OpenCV fails, try ffmpeg
            if not opencv_success:
                logger.warning(f"OpenCV capture failed for camera '{camera_name}'. Trying ffmpeg...")
                ffmpeg_success = self.capture_frames_ffmpeg(rtsp_uri, camera_name)
                
                if not ffmpeg_success:
                    logger.error(f"All capture methods failed for camera '{camera_name}'")
                else:
                    logger.info(f"Successfully captured frames using ffmpeg for camera '{camera_name}'")
            else:
                logger.info(f"Successfully captured frames using OpenCV for camera '{camera_name}'")

def main():
    """Main entry point"""
    try:
        logger.info("Starting ONVIF camera capture")
        capture = CameraCapture('config.yaml')
        capture.capture_all_cameras()
        logger.info("Completed camera capture")
    except KeyboardInterrupt:
        logger.info("Capture interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)

if __name__ == "__main__":
    main()