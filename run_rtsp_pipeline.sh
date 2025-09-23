#!/bin/bash
#
# Run the full ONVIF to USD pipeline using the public test RTSP stream
#

# Exit on error
set -e

# Project root
PROJECT_ROOT="$(pwd)"

# Configuration
CONFIG_FILE="test_config.yaml"
OUTPUT_DIR="${PROJECT_ROOT}/captured_frames"
COLMAP_OUT_DIR="${PROJECT_ROOT}/test_colmap"

# Function for printing section headers
print_header() {
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
}

# Function for error handling
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    handle_error "Config file not found: $CONFIG_FILE"
fi

# Create necessary directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$COLMAP_OUT_DIR"

# Step 1: Capture frames from RTSP stream
print_header "STEP 1: CAPTURING FRAMES FROM RTSP STREAM"
echo "Using config: $CONFIG_FILE"
echo "Output directory: $OUTPUT_DIR"

if python -m src.capture --config "$CONFIG_FILE"; then
    echo "Successfully captured frames from RTSP stream"
    
    # Check if any frames were captured
    frame_count=$(find "$OUTPUT_DIR" -name "*.jpg" | wc -l)
    echo "Captured $frame_count frames"
    
    if [ "$frame_count" -eq 0 ]; then
        echo "Warning: No frames were captured. Will use test frames instead."
        
        # Use test frames if no frames were captured
        if [ -d "test_frames" ] && [ -n "$(ls -A test_frames)" ]; then
            echo "Using existing test frames for photogrammetry"
            OUTPUT_DIR="${PROJECT_ROOT}/test_frames"
        else
            echo "Generating synthetic test frames"
            python -m scripts.generate_test_frames --output-dir "test_frames"
            OUTPUT_DIR="${PROJECT_ROOT}/test_frames"
        fi
    fi
else
    echo "Warning: Failed to capture frames from RTSP stream. Using test frames instead."
    
    # Generate synthetic test frames as a fallback
    python -m scripts.generate_test_frames --output-dir "test_frames"
    OUTPUT_DIR="${PROJECT_ROOT}/test_frames"
fi

# Step 2: Run photogrammetry
print_header "STEP 2: RUNNING PHOTOGRAMMETRY"
echo "Input frames: $OUTPUT_DIR"
echo "COLMAP output: $COLMAP_OUT_DIR"

if python -m src.photogrammetry --image-dir "$OUTPUT_DIR" --output-dir "$COLMAP_OUT_DIR"; then
    echo "Photogrammetry processing completed successfully"
    
    # Check if point cloud was generated
    if [ -f "$COLMAP_OUT_DIR/dense/fused.ply" ]; then
        POINT_CLOUD="$COLMAP_OUT_DIR/dense/fused.ply"
        echo "Point cloud generated: $POINT_CLOUD"
    else
        echo "Warning: Dense point cloud was not generated. Will generate USD scene without point cloud."
        POINT_CLOUD=""
    fi
else
    echo "Warning: Photogrammetry processing failed. Will generate USD scene without point cloud."
    POINT_CLOUD=""
fi

# Step 3: Generate USD scene
print_header "STEP 3: GENERATING USD SCENE"
echo "Input frames: $OUTPUT_DIR"

# Set USD output path
USD_OUTPUT="${PROJECT_ROOT}/output_rtsp_scene.usda"
echo "Output USD file: $USD_OUTPUT"

if [ -n "$POINT_CLOUD" ]; then
    # Generate USD scene with point cloud
    if python -m src.usd_builder --image-dir "$OUTPUT_DIR" --output "$USD_OUTPUT" --point-cloud "$POINT_CLOUD"; then
        echo "USD scene generation completed successfully with point cloud"
    else
        echo "Warning: USD scene generation with point cloud failed. Trying without point cloud..."
        python -m src.usd_builder --image-dir "$OUTPUT_DIR" --output "$USD_OUTPUT"
    fi
else
    # Generate USD scene without point cloud
    if python -m src.usd_builder --image-dir "$OUTPUT_DIR" --output "$USD_OUTPUT"; then
        echo "USD scene generation completed successfully without point cloud"
    else
        handle_error "USD scene generation failed"
    fi
fi

# Check if USD file was created
if [ ! -f "$USD_OUTPUT" ]; then
    handle_error "USD file was not created: $USD_OUTPUT"
fi

print_header "PIPELINE COMPLETED SUCCESSFULLY"
echo "USD scene saved to: $USD_OUTPUT"
echo ""
echo "To view the scene, use usdview:"
echo "  usdview $USD_OUTPUT"

exit 0