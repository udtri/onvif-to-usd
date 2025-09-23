#!/bin/bash
#
# Repository Cleanup Script for ONVIF-to-USD
# This script will clean up the repository for GitHub push
#

echo "Starting repository cleanup..."

# Create backup directory just in case
echo "Creating backup directory..."
mkdir -p ../onvif-to-usd-backup-$(date +%Y%m%d)
cp -r . ../onvif-to-usd-backup-$(date +%Y%m%d)/

# 1. Remove log files
echo "Removing log files..."
rm -f camera_capture.log onvif_to_usd.log photogrammetry.log usd_builder.log

# 2. Remove redundant test files
echo "Removing redundant test files..."
rm -f direct_test_scene.usda test_scene.usda

# 3. Remove redundant test scripts
echo "Removing redundant test scripts..."
rm -f test_direct_code.py

# 4. Remove duplicate scripts from scripts directory
echo "Removing duplicate scripts..."
rm -f scripts/run_synthetic_pipeline.sh scripts/run_test_pipeline.sh scripts/create_enhanced_usd.sh

# 5. Create new directory structure
echo "Creating new directory structure..."
mkdir -p examples sample_data/test_frames demo

# 6. Move files to appropriate locations
echo "Moving files to new locations..."
# Examples directory
mv enhanced_scene.usda photoreal_scene.usda examples/

# Sample data
cp test_frames/frame_00{1,2,3}.jpg sample_data/test_frames/ 2>/dev/null || echo "Could not find sample frames, skipping..."

# Demo materials
mv demo_script.sh demo/

# 7. Create proper .gitignore
echo "Creating proper .gitignore file..."
cat > .gitignore << EOL
# Logs
*.log

# Generated directories
captured_frames/
colmap_out/
azure_iot_frames/
azure_iot_colmap/
__pycache__/
.pytest_cache/

# Python
*.pyc
*.pyo
*.egg-info/
venv/

# Environment
.env
EOL

echo "Repository cleanup complete!"
echo "Next steps:"
echo "  1. Review the changes to ensure nothing important was removed"
echo "  2. Update README.md with the new directory structure"
echo "  3. Run 'git status' to see what files will be tracked"
echo "  4. Run 'git add .' to stage all changes"
echo "  5. Run 'git commit -m \"Clean repository structure\"'"
echo "  6. Run 'git push' to push to GitHub"