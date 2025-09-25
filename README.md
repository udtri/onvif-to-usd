# ONVIF Camera to OpenUSD Scene Builder

A Python project that captures frames from ONVIF cameras via RTSP, processes them through photogrammetry (optional), and generates a 3D scene in OpenUSD format.

## Overview

This project allows you to:
- Connect to ONVIF-compatible cameras
- Stream and capture frames via RTSP
- Optionally process captured frames using COLMAP for 3D reconstruction
- Generate an OpenUSD (.usda) scene representing the captured environment

## Prerequisites

- Python 3.10+
- Dependencies:
  - opencv-python-headless (for frame capture)
  - onvif-zeep (for ONVIF camera discovery)
  - numpy (for image processing)
  - pyyaml (for configuration parsing)
  - pytest (for testing)
  - ffmpeg (optional, fallback for frame capture)
  - pxr (OpenUSD, optional with graceful fallback)
- COLMAP (optional, for photogrammetry processing)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/udtri/onvif-to-usd.git
cd onvif-to-usd
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Install COLMAP (if using photogrammetry):
   - **Ubuntu/Debian**: `sudo apt-get install colmap`
   - **macOS**: `brew install colmap`
   - **Windows**: Download from [COLMAP website](https://colmap.github.io/)
   - For more detailed installation instructions, visit the [COLMAP documentation](https://colmap.github.io/install.html)

5. Install OpenUSD:
   - Follow the official installation guide at [OpenUSD Getting Started](https://openusd.org/release/getting_started.html)

## Configuration

Create a `config.yaml` file in the project root with your camera settings:

```yaml
cameras:
  - name: "FrontDoorCamera"
    host: "192.168.1.100"
    onvif_port: 80
    username: "admin"
    password: "password"
    rtsp_url: "rtsp://192.168.1.100:554/live/main"  # Optional: direct RTSP URL
  - name: "BackyardCamera"
    host: "192.168.1.101"
    onvif_port: 80
    username: "admin"
    password: "password"
    # rtsp_url is optional - if not provided, will be discovered via ONVIF

settings:
  capture:
    frame_interval: 5  # Seconds between frame captures
    total_frames: 20   # Total number of frames to capture per camera
    output_dir: "./captured_frames"
  
  photogrammetry:
    enabled: true
    colmap_path: "colmap"  # Path to COLMAP executable
    output_dir: "./colmap_out"
    feature_extractor_method: "sift"  # Options: sift, surf, etc.
    matching_strategy: "exhaustive"   # Options: exhaustive, sequential, vocab_tree
  
  usd:
    scene_name: "camera_scene"
    output_path: "./output/scene.usda"
```

### Example Configuration File

The repository includes a sample configuration file (`config.yaml`) that you can modify:

```yaml
# ONVIF Camera Configuration
cameras:
  - name: "FrontDoorCamera"
    host: "192.168.1.100"
    onvif_port: 80
    username: "admin"
    password: "password"
    rtsp_url: "rtsp://192.168.1.100:554/live/main"
  - name: "BackyardCamera"
    host: "192.168.1.101" 
    onvif_port: 80
    username: "admin"
    password: "password"

# Processing Settings
settings:
  capture:
    frame_interval: 2
    total_frames: 20
    output_dir: "./captured_frames"
  
  photogrammetry:
    enabled: true
    colmap_path: "colmap"
    output_dir: "./colmap_out"
  
  usd:
    scene_name: "camera_scene"
    output_path: "./scene.usda"
```

## Usage

### Basic Frame Capture

To capture frames from configured cameras:

```bash
python -m src.capture --config config.yaml
```

This will connect to each camera defined in your config file and save frames to the specified output directory.

### Run Photogrammetry Only

To run just the photogrammetry processing on previously captured images:

```bash
python -m src.photogrammetry --image-dir ./captured_frames --output-dir ./colmap_out
```

### Generate USD Scene Only

To create a USD scene from existing images and/or point cloud:

```bash
python -m src.usd_builder --image-dir ./captured_frames --output ./scene.usda --point-cloud ./colmap_out/dense/fused.ply
```

### Run Full Pipeline

To run the complete pipeline (capture, photogrammetry, USD generation):

```bash
python -m src.main --config config.yaml
```

### Run with Custom Options

```bash
python -m src.main --config config.yaml --no-photogrammetry --output ./custom_output.usda --image-dir ./my_images
```

### Using the Convenience Script

The repository includes a convenience script to run the full pipeline:

```bash
./scripts/run_full_pipeline.sh
```

Additional options:
```bash
# Skip capture step (use existing images)
./scripts/run_full_pipeline.sh --no-capture

# Skip photogrammetry step
./scripts/run_full_pipeline.sh --no-photogrammetry 

# Skip USD generation step
./scripts/run_full_pipeline.sh --no-usd

# Use mock photogrammetry data for testing
./scripts/run_full_pipeline.sh --mock-photogrammetry
```

### Run Tests

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_capture.py
pytest tests/test_photogrammetry.py
pytest tests/test_usd_builder.py

# Run tests with verbose output
pytest -v
```

## Testing

The project includes comprehensive unit tests for all components:

### Camera Capture Tests (8 tests)
Tests cover:
- ONVIF discovery and authentication
- RTSP URL construction
- Frame capture through OpenCV and ffmpeg
- Multiple camera handling
- Error handling for unavailable cameras

### Photogrammetry Tests (12 tests)
Tests cover:
- COLMAP availability checking
- Directory creation and management
- All pipeline stages:
  - Feature extraction
  - Feature matching
  - Sparse reconstruction
  - Stereo matching and fusion
- Pipeline integration and error handling

### USD Builder Tests (10 tests)
Tests cover:
- USD stage creation and setup
- Point cloud importing
- Plane geometry creation
- Material creation and binding
- Texture handling
- Fallback mechanisms
- Full pipeline integration

All tests use mock objects to simulate external dependencies, making them runnable without actual cameras, COLMAP, or OpenUSD installations.

## Project Structure

```
.
├── src/
│   ├── __init__.py
│   ├── main.py                  # Main entry point and pipeline integration
│   ├── capture.py               # ONVIF camera discovery and frame capture 
│   ├── photogrammetry.py        # COLMAP photogrammetry wrapper
│   └── usd_builder.py           # OpenUSD scene construction
├── scripts/
│   └── run_full_pipeline.sh     # Convenience script for running the full pipeline
├── tests/
│   ├── test_capture.py          # Unit tests for camera capture
│   ├── test_photogrammetry.py   # Unit tests for photogrammetry
│   └── test_usd_builder.py      # Unit tests for USD builder
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
├── scene.usda                   # Generated USD scene
├── captured_frames/             # Directory for captured images
├── colmap_out/                  # Directory for COLMAP output
│   └── dense/                   
│       └── fused.ply            # Generated point cloud
└── README.md                    # This file
```

## Features

- **ONVIF Camera Support**: Connect to any ONVIF-compatible IP camera
- **RTSP Streaming**: Efficient streaming and frame capture with both OpenCV and ffmpeg fallback
- **Automatic RTSP URL Discovery**: Uses ONVIF to automatically discover stream URLs
- **Photogrammetry Pipeline**: Complete COLMAP integration with all reconstruction stages:
  - Feature extraction
  - Feature matching
  - Sparse reconstruction
  - Dense reconstruction
  - Stereo matching and fusion
- **OpenUSD Integration**: Generate industry-standard USD files with:
  - Direct point cloud import
  - Textured plane fallback
  - PBR materials
  - USD preview surface materials
- **Graceful Fallbacks**: 
  - Multiple capture methods (OpenCV → ffmpeg)
  - Multiple 3D representation options (point cloud → textured plane)
  - Works even without OpenUSD by creating placeholder files

## Implementation Details

### Camera Capture Module

The `capture.py` module provides:
- ONVIF camera discovery using the onvif-zeep library
- Media profile enumeration to find available streams
- RTSP URL construction based on ONVIF capabilities
- Frame capture using OpenCV with ffmpeg fallback
- Configurable capture intervals and frame counts

### Photogrammetry Module

The `photogrammetry.py` module wraps COLMAP with:
- Full pipeline automation with appropriate parameter handling
- Feature extraction with SIFT by default
- Exhaustive or sequential matching strategies
- Support for both sparse and dense reconstruction
- Automatic management of intermediate files
- Configurable quality settings

### USD Builder Module

The `usd_builder.py` module handles:
- USD scene creation with proper metadata
- Direct import of point cloud data from COLMAP
- Fallback to textured plane when point cloud isn't available
- PBR material creation with textures from captured images
- Fallback to plain text USD when OpenUSD isn't available

## Examples

### Captured Frame Sample

After running the frame capture, check the `./captured_frames` directory for the saved images. Images are named with camera name and timestamp, for example:
```
FrontDoorCamera_20250916_145323.jpg
FrontDoorCamera_20250916_145325.jpg
BackyardCamera_20250916_145323.jpg
```

### Photogrammetry Output

COLMAP generates several outputs in the `./colmap_out` directory:
- `colmap_out/database.db`: Feature database
- `colmap_out/sparse/`: Sparse reconstruction
- `colmap_out/dense/`: Dense reconstruction
- `colmap_out/dense/fused.ply`: Final point cloud used for USD scene

### Generated USD Scene

The resulting USD scene will be available at the configured output path (default: `./scene.usda`).
You can view it with USD viewers like usdview:

```bash
usdview ./scene.usda
```

Without OpenUSD installed, a placeholder USD file is created with the following structure:
```
#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Y"
)

def Xform "World"
{
    # This is a placeholder USD file
    # Point cloud reference would have been: colmap_out/dense/fused.ply
    # Texture image used would have been: images/image_3.jpg
    
    def Mesh "PlaceholderPlane"
    {
        # A placeholder for actual geometry
    }
}
```

## Troubleshooting

### Common Issues

1. **Camera Connection Failures**:
   - Verify IP address, port, and credentials
   - Ensure camera is ONVIF-compatible
   - Check network connectivity
   - Look for errors in `camera_capture.log`
   - Try specifying an explicit RTSP URL in the config file
   - Ensure you have permissions to run ffmpeg if OpenCV fails

2. **COLMAP Errors**:
   - Verify COLMAP installation with `colmap -h`
   - Ensure sufficient image quality and overlap (minimum 10-20 images)
   - Check `photogrammetry.log` for detailed error messages
   - Try running individual COLMAP steps manually to isolate issues
   - Ensure you have enough disk space for dense reconstruction
   - Use the `--mock-photogrammetry` flag for testing when COLMAP isn't available

3. **USD Generation Issues**:
   - Confirm OpenUSD installation (`python -c "from pxr import Usd"`)
   - Check `usd_builder.log` for detailed error messages
   - Ensure point cloud file exists and is valid
   - Without OpenUSD, the system creates placeholder files
   - Check file permissions in output directories

### Running with Limited Dependencies

The system is designed to gracefully handle missing dependencies:

1. **Without OpenCV**:
   - Falls back to ffmpeg for frame capture

2. **Without ffmpeg**:
   - Will still attempt OpenCV capture

3. **Without COLMAP**:
   - Use `--no-photogrammetry` flag
   - Provide pre-existing point cloud data
   - Or use the textured plane fallback

4. **Without OpenUSD**:
   - Creates placeholder USD files with valid USDA syntax
   - Run with `--no-usd` to skip USD generation entirely

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.