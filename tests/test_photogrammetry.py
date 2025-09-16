#!/usr/bin/env python3
"""
Unit tests for the photogrammetry module
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock, call

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the module to test
from src.photogrammetry import ColmapWrapper


class TestColmapWrapper(unittest.TestCase):
    """Test cases for the COLMAP wrapper module"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create temporary directories for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.image_dir = self.test_dir / "images"
        self.output_dir = self.test_dir / "colmap_out"
        
        # Create the directories
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test images
        self.create_test_images()
        
        # Path for COLMAP database and output
        self.database_path = self.output_dir / "database.db"
        self.sparse_dir = self.output_dir / "sparse"
        self.dense_dir = self.output_dir / "dense"
        
        # Create the COLMAP wrapper with mocked COLMAP path
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            self.colmap_wrapper = ColmapWrapper(
                image_dir=str(self.image_dir),
                output_dir=str(self.output_dir),
                colmap_path="mock_colmap"
            )
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_images(self):
        """Create test images for photogrammetry"""
        for i in range(5):
            image_path = self.image_dir / f"image_{i:06d}.jpg"
            try:
                import cv2
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                # Add some variation to the images
                cv2.putText(
                    img, f"Frame {i}", (10, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
                )
                cv2.imwrite(str(image_path), img)
            except ImportError:
                # If cv2 is not available, create empty files
                with open(image_path, 'wb') as f:
                    f.write(b'\x00' * 100)
    
    def test_initialization(self):
        """Test that the COLMAP wrapper initializes correctly"""
        # Check that directories are set correctly
        assert self.colmap_wrapper.image_dir == self.image_dir
        assert self.colmap_wrapper.output_dir == self.output_dir
        assert self.colmap_wrapper.colmap_path == "mock_colmap"
        
        # Check that derived paths are set correctly
        assert self.colmap_wrapper.database_path == self.database_path
        assert self.colmap_wrapper.sparse_dir == self.sparse_dir
        assert self.colmap_wrapper.dense_dir == self.dense_dir
    
    def test_create_directories(self):
        """Test that output directories are created"""
        # Check that the directories exist
        assert self.colmap_wrapper.output_dir.exists()
        assert self.colmap_wrapper.sparse_dir.exists()
        assert self.colmap_wrapper.dense_dir.exists()
    
    @patch('subprocess.run')
    def test_check_colmap_availability(self, mock_run):
        """Test checking if COLMAP is available"""
        # Configure the mock to succeed
        mock_run.return_value = MagicMock(returncode=0)
        
        # Create a new wrapper to test the check
        colmap_wrapper = ColmapWrapper(
            image_dir=str(self.image_dir),
            output_dir=str(self.output_dir),
            colmap_path="mock_colmap"
        )
        
        # Check that the command was run correctly
        mock_run.assert_any_call(
            ["mock_colmap", "help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Now test with a failing command
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=1, stderr="Command not found")
        
        # Check that an exception is raised
        with pytest.raises(RuntimeError):
            colmap_wrapper = ColmapWrapper(
                image_dir=str(self.image_dir),
                output_dir=str(self.output_dir),
                colmap_path="invalid_colmap"
            )
    
    @patch('subprocess.run')
    def test_run_command(self, mock_run):
        """Test running a COLMAP command"""
        # Configure the mock to succeed
        mock_run.return_value = MagicMock(returncode=0)
        
        # Run a test command
        result = self.colmap_wrapper.run_command(
            ["mock_colmap", "test_command"],
            "Test command"
        )
        
        # Check that the command was run
        mock_run.assert_called_once_with(
            ["mock_colmap", "test_command"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        # Check that the result is success
        assert result is True
        
        # Now test with a failing command
        mock_run.reset_mock()
        mock_run.return_value = MagicMock(returncode=1, stderr="Command failed")
        
        # Run a test command that fails
        result = self.colmap_wrapper.run_command(
            ["mock_colmap", "failing_command"],
            "Failing command"
        )
        
        # Check that the command was run
        mock_run.assert_called_once()
        
        # Check that the result is failure
        assert result is False
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_feature_extraction(self, mock_run_command):
        """Test running COLMAP feature extraction"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run feature extraction
        result = self.colmap_wrapper.feature_extraction()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "feature_extractor"
        assert command[3] == str(self.database_path)
        assert command[5] == str(self.image_dir)
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_feature_matching(self, mock_run_command):
        """Test running COLMAP feature matching"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run feature matching
        result = self.colmap_wrapper.feature_matching()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "exhaustive_matcher"
        assert command[3] == str(self.database_path)
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_sparse_reconstruction(self, mock_run_command):
        """Test running COLMAP mapper for sparse reconstruction"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run sparse reconstruction
        result = self.colmap_wrapper.sparse_reconstruction()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "mapper"
        assert command[3] == str(self.database_path)
        assert command[5] == str(self.image_dir)
        assert command[7] == str(self.sparse_dir)
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_image_undistortion(self, mock_run_command):
        """Test running COLMAP image undistorter"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run image undistortion
        result = self.colmap_wrapper.image_undistortion()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "image_undistorter"
        assert command[3] == str(self.image_dir)
        assert command[5] == str(self.colmap_wrapper.sparse_model_dir)
        assert command[7] == str(self.dense_dir)
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_stereo_matching(self, mock_run_command):
        """Test running COLMAP patch match stereo"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run stereo matching
        result = self.colmap_wrapper.stereo_matching()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "patch_match_stereo"
        assert command[3] == str(self.dense_dir)
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.run_command')
    def test_stereo_fusion(self, mock_run_command):
        """Test running COLMAP stereo fusion"""
        # Configure the mock to succeed
        mock_run_command.return_value = True
        
        # Run stereo fusion
        result = self.colmap_wrapper.stereo_fusion()
        
        # Check that the command was run correctly
        mock_run_command.assert_called_once()
        args, kwargs = mock_run_command.call_args
        command, desc = args
        
        # Check command format
        assert command[0] == "mock_colmap"
        assert command[1] == "stereo_fusion"
        assert command[3] == str(self.dense_dir)
        assert command[9] == str(self.dense_dir / "fused.ply")
        
        # Check that the result is success
        assert result is True
    
    @patch('src.photogrammetry.ColmapWrapper.feature_extraction')
    @patch('src.photogrammetry.ColmapWrapper.feature_matching')
    @patch('src.photogrammetry.ColmapWrapper.sparse_reconstruction')
    @patch('src.photogrammetry.ColmapWrapper.image_undistortion')
    @patch('src.photogrammetry.ColmapWrapper.stereo_matching')
    @patch('src.photogrammetry.ColmapWrapper.stereo_fusion')
    def test_run_pipeline(
        self, mock_fusion, mock_matching, mock_undistortion,
        mock_reconstruction, mock_feature_matching, mock_feature_extraction
    ):
        """Test running the complete COLMAP pipeline"""
        # Configure all mocks to succeed
        mock_feature_extraction.return_value = True
        mock_feature_matching.return_value = True
        mock_reconstruction.return_value = True
        mock_undistortion.return_value = True
        mock_matching.return_value = True
        mock_fusion.return_value = True
        
        # Create a mock output file
        output_ply = self.dense_dir / "fused.ply"
        output_ply.parent.mkdir(parents=True, exist_ok=True)
        with open(output_ply, 'w') as f:
            f.write("mock ply data")
        
        # Run the pipeline
        result = self.colmap_wrapper.run_pipeline()
        
        # Check that all steps were called in the right order
        mock_feature_extraction.assert_called_once()
        mock_feature_matching.assert_called_once()
        mock_reconstruction.assert_called_once()
        mock_undistortion.assert_called_once()
        mock_matching.assert_called_once()
        mock_fusion.assert_called_once()
        
        # Check that the result is success
        assert result is True
        
        # Now test with a step failing
        mock_feature_extraction.reset_mock()
        mock_feature_matching.reset_mock()
        mock_reconstruction.reset_mock()
        mock_undistortion.reset_mock()
        mock_matching.reset_mock()
        mock_fusion.reset_mock()
        
        # Make one step fail
        mock_matching.return_value = False
        
        # Run the pipeline
        result = self.colmap_wrapper.run_pipeline()
        
        # Check that steps were called up to the failing step
        mock_feature_extraction.assert_called_once()
        mock_feature_matching.assert_called_once()
        mock_reconstruction.assert_called_once()
        mock_undistortion.assert_called_once()
        mock_matching.assert_called_once()
        
        # Check that later steps were not called
        mock_fusion.assert_not_called()
        
        # Check that the result is failure
        assert result is False
    
    def test_run_pipeline_output_verification(self):
        """Test verification of output files in run_pipeline"""
        # Mock all the steps to succeed
        with patch.multiple(
            'src.photogrammetry.ColmapWrapper',
            feature_extraction=MagicMock(return_value=True),
            feature_matching=MagicMock(return_value=True),
            sparse_reconstruction=MagicMock(return_value=True),
            image_undistortion=MagicMock(return_value=True),
            stereo_matching=MagicMock(return_value=True),
            stereo_fusion=MagicMock(return_value=True)
        ):
            # Run the pipeline without creating the output file
            result = self.colmap_wrapper.run_pipeline()
            
            # Check that the result is failure due to missing output
            assert result is False
            
            # Now create the output file and try again
            output_ply = self.dense_dir / "fused.ply"
            with open(output_ply, 'w') as f:
                f.write("mock ply data")
                
            # Run the pipeline again
            result = self.colmap_wrapper.run_pipeline()
            
            # Check that the result is success now
            assert result is True


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])