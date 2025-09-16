#!/usr/bin/env python3
"""
ONVIF to USD Main Script

This script captures frames from ONVIF cameras, performs photogrammetry,
and builds a USD scene from them.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Local imports
from src.capture import CameraCapture
from src.photogrammetry import ColmapWrapper
from src.usd_builder import UsdSceneBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('onvif_to_usd.log')
    ]
)

logger = logging.getLogger('onvif_to_usd')

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='ONVIF to USD Converter')
    
    parser.add_argument(
        '--config', 
        type=str, 
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    
    parser.add_argument(
        '--no-capture', 
        action='store_true',
        help='Skip frame capture and use existing images'
    )
    
    parser.add_argument(
        '--no-photogrammetry', 
        action='store_true',
        help='Skip photogrammetry processing'
    )
    
    parser.add_argument(
        '--no-usd', 
        action='store_true',
        help='Skip USD generation'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='photoreal_scene.usda',
        help='Output USD file path (default: photoreal_scene.usda)'
    )
    
    parser.add_argument(
        '--image-dir', 
        type=str, 
        default='./images',
        help='Directory for captured images (default: ./images)'
    )
    
    parser.add_argument(
        '--colmap-dir', 
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
    
    return parser.parse_args()

def main():
    """Main entry point"""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Create output directories if needed
        image_dir = Path(args.image_dir)
        image_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Capture frames (if not skipped)
        if not args.no_capture:
            logger.info("Starting frame capture from ONVIF cameras")
            capture = CameraCapture(args.config)
            capture.capture_all_cameras()
            logger.info("Frame capture complete")
        else:
            logger.info("Skipping frame capture")
        
        # Step 2: Run photogrammetry (if not skipped)
        if not args.no_photogrammetry:
            logger.info("Starting photogrammetry processing with COLMAP")
            colmap = ColmapWrapper(
                image_dir=args.image_dir,
                output_dir=args.colmap_dir,
                colmap_path=args.colmap_path
            )
            
            success = colmap.run_pipeline()
            if not success:
                logger.error("Photogrammetry processing failed")
                return 1
                
            logger.info("Photogrammetry processing complete")
        else:
            logger.info("Skipping photogrammetry processing")
        
        # Step 3: Generate USD scene (if not skipped)
        if not args.no_usd:
            logger.info("Starting USD scene generation")
            builder = UsdSceneBuilder(args.image_dir, args.output)
            success = builder.build_scene()
            
            if success:
                logger.info(f"USD scene successfully generated at {args.output}")
            else:
                logger.error("Failed to generate USD scene")
                return 1
        else:
            logger.info("Skipping USD scene generation")
            
        logger.info("ONVIF to USD processing complete")
        return 0
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())