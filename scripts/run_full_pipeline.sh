#!/bin/bash
#
# Full ONVIF to USD Pipeline Script
# 
# This script runs the complete pipeline:
# 1. Capture frames from ONVIF cameras
# 2. Process images with COLMAP photogrammetry
# 3. Generate a USD scene with textures
#

# Exit immediately if a command exits with a non-zero status
set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root directory (parent of script directory)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
CONFIG_FILE="${PROJECT_ROOT}/config.yaml"
IMAGES_DIR="${PROJECT_ROOT}/images"
COLMAP_OUT_DIR="${PROJECT_ROOT}/colmap_out"
USD_OUTPUT="${PROJECT_ROOT}/photoreal_scene.usda"

# Function for printing section headers
print_header() {
    echo "========================================================="
    echo "  $1"
    echo "========================================================="
}

# Function for error handling
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    handle_error "Python 3 is required but not installed."
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    handle_error "Configuration file $CONFIG_FILE not found."
fi

# Create directories if they don't exist
mkdir -p "$IMAGES_DIR"
mkdir -p "$COLMAP_OUT_DIR"

# Check if the source files exist
if [ ! -f "${PROJECT_ROOT}/src/capture.py" ]; then
    handle_error "capture.py not found in ${PROJECT_ROOT}/src/"
fi

if [ ! -f "${PROJECT_ROOT}/src/photogrammetry.py" ]; then
    handle_error "photogrammetry.py not found in ${PROJECT_ROOT}/src/"
fi

if [ ! -f "${PROJECT_ROOT}/src/usd_builder.py" ]; then
    handle_error "usd_builder.py not found in ${PROJECT_ROOT}/src/"
fi

# Change to the project root directory
cd "$PROJECT_ROOT"

# Step 1: Capture frames from ONVIF cameras
print_header "STEP 1: Capturing frames from ONVIF cameras"
echo "Saving images to: $IMAGES_DIR"
echo "Using config: $CONFIG_FILE"
echo ""

if python3 src/capture.py --config "$CONFIG_FILE"; then
    echo "Frame capture completed successfully."
else
    handle_error "Frame capture failed."
fi

# Check if any images were captured
image_count=$(find "$IMAGES_DIR" -name "*.jpg" | wc -l)
if [ "$image_count" -eq 0 ]; then
    handle_error "No images were captured. Cannot continue."
fi
echo "Found $image_count images for processing."

# Step 2: Run photogrammetry
print_header "STEP 2: Running COLMAP photogrammetry"
echo "Input images: $IMAGES_DIR"
echo "Output directory: $COLMAP_OUT_DIR"
echo ""

if python3 src/photogrammetry.py --image-dir "$IMAGES_DIR" --output-dir "$COLMAP_OUT_DIR"; then
    echo "Photogrammetry completed successfully."
else
    handle_error "Photogrammetry processing failed."
fi

# Check if the point cloud was generated
if [ ! -f "${COLMAP_OUT_DIR}/dense/fused.ply" ]; then
    handle_error "Photogrammetry did not produce the expected output file: ${COLMAP_OUT_DIR}/dense/fused.ply"
fi

# Step 3: Generate USD scene
print_header "STEP 3: Generating USD scene"
echo "Using point cloud: ${COLMAP_OUT_DIR}/dense/fused.ply"
echo "Output USD file: $USD_OUTPUT"
echo ""

if python3 src/usd_builder.py --image-dir "$IMAGES_DIR" --output "$USD_OUTPUT" --point-cloud "${COLMAP_OUT_DIR}/dense/fused.ply"; then
    echo "USD scene generation completed successfully."
else
    handle_error "USD scene generation failed."
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
echo ""

exit 0