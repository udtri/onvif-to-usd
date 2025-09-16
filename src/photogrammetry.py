#!/usr/bin/env python3
"""
Photogrammetry Module

Python wrapper for COLMAP photogrammetry pipeline.
Processes images and generates a 3D point cloud model.
"""

import os
import sys
import subprocess
import shutil
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('photogrammetry.log')
    ]
)

logger = logging.getLogger('photogrammetry')

class ColmapWrapper:
    """COLMAP photogrammetry pipeline wrapper"""
    
    def __init__(
        self,
        image_dir: str = './images',
        output_dir: str = './colmap_out',
        colmap_path: str = 'colmap',
        gpu_index: int = 0
    ):
        """
        Initialize COLMAP wrapper
        
        Args:
            image_dir: Directory containing input images
            output_dir: Directory for COLMAP output
            colmap_path: Path to COLMAP executable
            gpu_index: GPU index to use (0-based)
        """
        self.image_dir = Path(image_dir)
        self.output_dir = Path(output_dir)
        self.colmap_path = colmap_path
        self.gpu_index = gpu_index
        
        # Derived paths for COLMAP workspace
        self.database_path = self.output_dir / "database.db"
        self.sparse_dir = self.output_dir / "sparse"
        self.sparse_model_dir = self.sparse_dir / "0"
        self.dense_dir = self.output_dir / "dense"
        
        # Create output directories
        self._create_directories()
        
        # Check if COLMAP is available
        self._check_colmap_availability()
        
        logger.info(f"COLMAP wrapper initialized with image_dir={image_dir}, output_dir={output_dir}")
    
    def _create_directories(self):
        """Create necessary directories for COLMAP pipeline"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.sparse_dir.mkdir(parents=True, exist_ok=True)
            self.dense_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created output directories in {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise
    
    def _check_colmap_availability(self):
        """Check if COLMAP is available"""
        try:
            cmd = [self.colmap_path, "help"]
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"COLMAP not found at {self.colmap_path}. Error: {result.stderr}")
                raise RuntimeError(f"COLMAP not found at {self.colmap_path}")
                
            logger.info(f"COLMAP found at {self.colmap_path}")
            
        except FileNotFoundError:
            logger.error(f"COLMAP executable not found at {self.colmap_path}")
            raise
    
    def run_command(self, command: List[str], desc: str) -> bool:
        """
        Run a COLMAP command with error handling
        
        Args:
            command: Command list to run
            desc: Description of the command for logging
            
        Returns:
            True if command succeeds, False otherwise
        """
        start_time = time.time()
        logger.info(f"Starting {desc}")
        
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Check return code
            if result.returncode != 0:
                logger.error(f"{desc} failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                return False
            
            elapsed = time.time() - start_time
            logger.info(f"{desc} completed successfully in {elapsed:.2f} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Exception while running {desc}: {e}")
            return False
    
    def feature_extraction(self) -> bool:
        """
        Run COLMAP feature extraction step
        
        Returns:
            True if successful, False otherwise
        """
        command = [
            self.colmap_path, "feature_extractor",
            "--database_path", str(self.database_path),
            "--image_path", str(self.image_dir),
            "--ImageReader.camera_model", "SIMPLE_RADIAL",
            "--ImageReader.single_camera", "1",
            "--SiftExtraction.use_gpu", "1",
            "--SiftExtraction.gpu_index", str(self.gpu_index)
        ]
        
        return self.run_command(command, "Feature extraction")
    
    def feature_matching(self) -> bool:
        """
        Run COLMAP exhaustive matcher step
        
        Returns:
            True if successful, False otherwise
        """
        command = [
            self.colmap_path, "exhaustive_matcher",
            "--database_path", str(self.database_path),
            "--SiftMatching.use_gpu", "1",
            "--SiftMatching.gpu_index", str(self.gpu_index)
        ]
        
        return self.run_command(command, "Exhaustive matching")
    
    def sparse_reconstruction(self) -> bool:
        """
        Run COLMAP mapper step for sparse reconstruction
        
        Returns:
            True if successful, False otherwise
        """
        command = [
            self.colmap_path, "mapper",
            "--database_path", str(self.database_path),
            "--image_path", str(self.image_dir),
            "--output_path", str(self.sparse_dir)
        ]
        
        return self.run_command(command, "Sparse reconstruction")
    
    def image_undistortion(self) -> bool:
        """
        Run COLMAP image undistorter step
        
        Returns:
            True if successful, False otherwise
        """
        command = [
            self.colmap_path, "image_undistorter",
            "--image_path", str(self.image_dir),
            "--input_path", str(self.sparse_model_dir),
            "--output_path", str(self.dense_dir),
            "--output_type", "COLMAP"
        ]
        
        return self.run_command(command, "Image undistortion")
    
    def stereo_matching(self) -> bool:
        """
        Run COLMAP patch match stereo step
        
        Returns:
            True if successful, False otherwise
        """
        command = [
            self.colmap_path, "patch_match_stereo",
            "--workspace_path", str(self.dense_dir),
            "--workspace_format", "COLMAP",
            "--PatchMatchStereo.gpu_index", str(self.gpu_index)
        ]
        
        return self.run_command(command, "Patch match stereo")
    
    def stereo_fusion(self) -> bool:
        """
        Run COLMAP stereo fusion step
        
        Returns:
            True if successful, False otherwise
        """
        # Ensure the fused directory exists
        fused_dir = self.dense_dir / "fused"
        fused_dir.mkdir(parents=True, exist_ok=True)
        
        command = [
            self.colmap_path, "stereo_fusion",
            "--workspace_path", str(self.dense_dir),
            "--workspace_format", "COLMAP",
            "--input_type", "geometric",
            "--output_path", str(self.dense_dir / "fused.ply")
        ]
        
        return self.run_command(command, "Stereo fusion")
    
    def run_pipeline(self) -> bool:
        """
        Run the complete COLMAP pipeline
        
        Returns:
            True if all steps succeed, False otherwise
        """
        steps = [
            ("Feature extraction", self.feature_extraction),
            ("Feature matching", self.feature_matching),
            ("Sparse reconstruction", self.sparse_reconstruction),
            ("Image undistortion", self.image_undistortion),
            ("Stereo matching", self.stereo_matching),
            ("Stereo fusion", self.stereo_fusion)
        ]
        
        logger.info("Starting COLMAP photogrammetry pipeline")
        
        # Run each step
        for step_name, step_func in steps:
            if not step_func():
                logger.error(f"Pipeline failed at {step_name}")
                return False
        
        # Verify output exists
        output_ply = self.dense_dir / "fused.ply"
        if not output_ply.exists():
            logger.error(f"Pipeline completed but output file {output_ply} not found")
            return False
        
        logger.info(f"COLMAP pipeline completed successfully. Output: {output_ply}")
        return True

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='COLMAP Photogrammetry Wrapper')
    
    parser.add_argument(
        '--image-dir', 
        type=str, 
        default='./images',
        help='Directory containing input images (default: ./images)'
    )
    
    parser.add_argument(
        '--output-dir', 
        type=str, 
        default='./colmap_out',
        help='Directory for COLMAP output (default: ./colmap_out)'
    )
    
    parser.add_argument(
        '--colmap-path', 
        type=str, 
        default='colmap',
        help='Path to COLMAP executable (default: colmap)'
    )
    
    parser.add_argument(
        '--gpu', 
        type=int, 
        default=0,
        help='GPU index to use (default: 0)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_args()
        
        # Initialize COLMAP wrapper
        colmap = ColmapWrapper(
            image_dir=args.image_dir,
            output_dir=args.output_dir,
            colmap_path=args.colmap_path,
            gpu_index=args.gpu
        )
        
        # Run the pipeline
        success = colmap.run_pipeline()
        
        if success:
            logger.info("Photogrammetry processing completed successfully!")
            return 0
        else:
            logger.error("Photogrammetry processing failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())