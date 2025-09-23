#!/bin/bash
#
# Simplified Pipeline Script for USD Generation with Synthetic Images
# 
# This script skips the full photogrammetry process and uses the fallback method
# to generate a USD scene from synthetic test frames
#

# Exit immediately if a command exits with a non-zero status
set -e

# Project root directory
PROJECT_ROOT="$(pwd)"

# Configuration
IMAGES_DIR="${PROJECT_ROOT}/test_frames"
USD_OUTPUT="${PROJECT_ROOT}/test_scene.usda"

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

# Create directories if they don't exist
mkdir -p "$(dirname "$USD_OUTPUT")"

# Check if we have test frames
image_count=$(find "$IMAGES_DIR" -name "*.jpg" | wc -l)
if [ "$image_count" -eq 0 ]; then
    handle_error "No images found in $IMAGES_DIR. Please run the generate_test_frames.py script first."
fi
echo "Found $image_count images for processing."

# Generate USD scene directly from images
print_header "Generating USD scene from images"
echo "Input images: $IMAGES_DIR"
echo "Output USD file: $USD_OUTPUT"
echo ""

if python -m src.usd_builder --image-dir "$IMAGES_DIR" --output "$USD_OUTPUT"; then
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

# Display the contents of the USD file
echo "Contents of the generated USD file:"
echo "----------------------------------------"
head -n 20 "$USD_OUTPUT"
echo "... (truncated) ..."
echo "----------------------------------------"

exit 0