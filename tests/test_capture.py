#!/usr/bin/env python3
"""
Unit tests for the camera capture module
"""

import os
import sys
import shutil
import tempfile
import subprocess
import yaml
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import module to test
from src.capture import CameraCapture

class TestCameraCapture:
    """Test cases for the CameraCapture class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        return {
            'cameras': [
                {
                    'name': 'TestCamera',
                    'host': '192.168.1.100',
                    'onvif_port': 80,
                    'username': 'admin',
                    'password': 'password',
                    'rtsp_url': 'rtsp://192.168.1.100:554/live/main'
                }
            ],
            'settings': {
                'capture': {
                    'frame_interval': 1,  # Capture every frame for faster testing
                    'total_frames': 5,    # Only capture a few frames for testing
                    'output_dir': './test_images'
                }
            }
        }
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test outputs"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup after test
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config_file(self, temp_dir, mock_config):
        """Create a temporary config file for testing"""
        config_path = os.path.join(temp_dir, 'test_config.yaml')
        with open(config_path, 'w') as f:
            yaml.dump(mock_config, f)
        return config_path
    
    @pytest.fixture
    def camera_capture(self, config_file, temp_dir):
        """Create a CameraCapture instance for testing"""
        # Modify the config to use the temp directory for output
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['settings']['capture']['output_dir'] = os.path.join(temp_dir, 'test_images')
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        return CameraCapture(config_file)
    
    def test_load_config(self, camera_capture, mock_config):
        """Test that configuration is loaded correctly"""
        # Check that cameras are loaded
        assert len(camera_capture.cameras) == len(mock_config['cameras'])
        assert camera_capture.cameras[0]['name'] == mock_config['cameras'][0]['name']
        
        # Check that settings are loaded
        assert camera_capture.capture_settings['frame_interval'] == mock_config['settings']['capture']['frame_interval']
        assert camera_capture.capture_settings['total_frames'] == mock_config['settings']['capture']['total_frames']
    
    def test_prepare_output_dir(self, camera_capture, temp_dir):
        """Test that the output directory is created correctly"""
        output_path = camera_capture.output_dir
        assert output_path.exists()
        assert output_path.is_dir()
        assert str(output_path).startswith(temp_dir)
    
    def test_get_rtsp_uri_from_config(self, camera_capture):
        """Test that RTSP URI is retrieved from config when ONVIF is not available"""
        camera = {
            'name': 'ConfigCamera',
            'rtsp_url': 'rtsp://example.com/stream'
        }
        
        uri = camera_capture.get_rtsp_uri(camera)
        assert uri == 'rtsp://example.com/stream'
    
    @patch('src.capture.ONVIFCamera')
    def test_get_rtsp_uri_from_onvif(self, mock_onvif, camera_capture):
        """Test that RTSP URI is retrieved via ONVIF when available"""
        # Mock ONVIF client and responses
        mock_cam = MagicMock()
        mock_onvif.return_value = mock_cam
        
        # Mock media service
        mock_media = MagicMock()
        mock_cam.create_media_service.return_value = mock_media
        
        # Mock profiles
        mock_profile = MagicMock()
        mock_profile._token = 'profile_token'
        mock_media.GetProfiles.return_value = [mock_profile]
        
        # Mock request and URI
        mock_request = MagicMock()
        mock_media.create_type.return_value = mock_request
        
        mock_uri = MagicMock()
        mock_uri.Uri = 'rtsp://onvif-discovery.com/stream'
        mock_media.GetStreamUri.return_value = mock_uri
        
        # Test camera with ONVIF parameters
        camera = {
            'name': 'OnvifCamera',
            'host': '192.168.1.100',
            'onvif_port': 80,
            'username': 'admin',
            'password': 'password'
        }
        
        uri = camera_capture.get_rtsp_uri(camera)
        
        # Assert that ONVIF discovery was attempted
        mock_onvif.assert_called_once_with(
            camera['host'], 
            camera['onvif_port'], 
            camera['username'], 
            camera['password']
        )
        
        # Assert that the URI was retrieved
        assert uri == 'rtsp://onvif-discovery.com/stream'
    
    @patch('src.capture.cv2.VideoCapture')
    def test_capture_frames_opencv(self, mock_video_capture, camera_capture, temp_dir):
        """Test that frames are captured correctly using OpenCV"""
        # Mock VideoCapture
        mock_cap = MagicMock()
        mock_video_capture.return_value = mock_cap
        
        # Configure mock to return valid frames
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0  # 30 fps
        
        # Create a test frame (simple 10x10 black image)
        test_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        
        # Configure read() to return 5 frames then stop
        mock_cap.read.side_effect = [
            (True, test_frame.copy()),  # Frame 1
            (True, test_frame.copy()),  # Frame 2
            (True, test_frame.copy()),  # Frame 3
            (True, test_frame.copy()),  # Frame 4
            (True, test_frame.copy()),  # Frame 5
            (False, None)               # End of stream
        ]
        
        # Patch cv2.imwrite to track saved files
        saved_frames = []
        
        def mock_imwrite(filename, img):
            saved_frames.append(filename)
            return True
        
        with patch('src.capture.cv2.imwrite', side_effect=mock_imwrite):
            # Run the capture
            result = camera_capture.capture_frames_opencv(
                'rtsp://test.stream/video', 
                'TestCamera'
            )
            
            # Check that the result is successful
            assert result is True
            
            # Check that VideoCapture was called with the right URI
            import cv2
            mock_video_capture.assert_called_once_with(
                'rtsp://test.stream/video', 
                cv2.CAP_FFMPEG
            )
            
            # Check that 5 frames were saved
            assert len(saved_frames) == 5
            
            # Check that the filenames have the expected format
            for i, filename in enumerate(saved_frames):
                expected_filename = os.path.join(
                    str(camera_capture.output_dir), 
                    f"TestCamera_img_{i:06d}.jpg"
                )
                assert filename == expected_filename
    
    @patch('src.capture.cv2.VideoCapture')
    def test_capture_failure_handling(self, mock_video_capture, camera_capture):
        """Test that capture failures are handled correctly"""
        # Mock VideoCapture
        mock_cap = MagicMock()
        mock_video_capture.return_value = mock_cap
        
        # Configure mock to fail to open
        mock_cap.isOpened.return_value = False
        
        # Run the capture
        result = camera_capture.capture_frames_opencv(
            'rtsp://test.stream/video', 
            'TestCamera'
        )
        
        # Check that the result is failure
        assert result is False
    
    @patch('src.capture.CameraCapture.capture_frames_opencv')
    @patch('src.capture.CameraCapture.capture_frames_ffmpeg')
    @patch('src.capture.CameraCapture.get_rtsp_uri')
    def test_capture_all_cameras(self, mock_get_rtsp_uri, mock_ffmpeg, mock_opencv, camera_capture):
        """Test the main capture_all_cameras method"""
        # Mock the RTSP URI retrieval
        mock_get_rtsp_uri.return_value = 'rtsp://test.stream/video'
        
        # Configure OpenCV capture to fail
        mock_opencv.return_value = False
        
        # Configure ffmpeg capture to succeed
        mock_ffmpeg.return_value = True
        
        # Run capture on all cameras
        camera_capture.capture_all_cameras()
        
        # Check that RTSP URI was retrieved
        mock_get_rtsp_uri.assert_called_once()
        
        # Check that OpenCV capture was attempted first
        mock_opencv.assert_called_once_with('rtsp://test.stream/video', 'TestCamera')
        
        # Check that ffmpeg was called as a fallback
        mock_ffmpeg.assert_called_once_with('rtsp://test.stream/video', 'TestCamera')
        
        # Now test successful OpenCV capture
        mock_opencv.reset_mock()
        mock_ffmpeg.reset_mock()
        
        # Configure OpenCV capture to succeed
        mock_opencv.return_value = True
        
        # Run capture again
        camera_capture.capture_all_cameras()
        
        # Check that OpenCV capture was attempted
        mock_opencv.assert_called_once_with('rtsp://test.stream/video', 'TestCamera')
        
        # Check that ffmpeg was NOT called
        mock_ffmpeg.assert_not_called()
    
    @patch('subprocess.Popen')
    def test_capture_frames_ffmpeg(self, mock_popen, camera_capture):
        """Test the ffmpeg fallback capture method"""
        # Mock the subprocess.Popen
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        # Configure the process to succeed
        mock_process.returncode = 0
        mock_process.communicate.return_value = ('stdout', 'stderr')
        
        # Run the ffmpeg capture
        result = camera_capture.capture_frames_ffmpeg(
            'rtsp://test.stream/video', 
            'TestCamera'
        )
        
        # Check that the result is successful
        assert result is True
        
        # Check that ffmpeg was called with the correct parameters
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        
        # Check that the command starts with ffmpeg
        assert args[0][0] == 'ffmpeg'
        
        # Check that the input URI is correct
        input_index = args[0].index('-i')
        assert args[0][input_index + 1] == 'rtsp://test.stream/video'
        
        # Check that stdout/stderr were captured
        assert kwargs['stdout'] == subprocess.PIPE
        assert kwargs['stderr'] == subprocess.PIPE


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])