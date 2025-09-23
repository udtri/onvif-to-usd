#!/usr/bin/env python3
"""
Enhanced USD Scene Generator

Creates a more comprehensive USD scene from synthetic frames with proper references
to all frames and animation timing.
"""

import os
import sys
import glob
import argparse
from pathlib import Path

def create_enhanced_usd_scene(images_dir, output_file):
    """
    Create an enhanced USD scene from a directory of image frames
    
    Args:
        images_dir: Directory containing the image frames
        output_file: Path to save the USD scene file
    """
    # Find all jpg images in the directory
    images = sorted(glob.glob(os.path.join(images_dir, "*.jpg")))
    if not images:
        print(f"No images found in {images_dir}")
        return False
        
    print(f"Found {len(images)} frames for USD scene")
    
    # Create parent directory for output file if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Start building USD scene
    with open(output_file, 'w') as f:
        # Write USD header
        f.write(f"""#usda 1.0
(
    defaultPrim = "Scene"
    upAxis = "Y"
    metersPerUnit = 1
    timeCodesPerSecond = 24
    startTimeCode = 0
    endTimeCode = {len(images) - 1}
)

def Xform "Scene" (
    kind = "assembly"
)
{{
    # Scene generated from synthetic frames

    def Camera "Camera" (
        kind = "component"
    )
    {{
        float3 xformOp:translate = (0, 0, 5)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        float focalLength = 35
        float horizontalAperture = 36
        float verticalAperture = 24
        
        # Camera animation with rotation around Y axis
        float3 xformOp:rotateXYZ.timeSamples = {{
            0: (0, 0, 0),
            {len(images) - 1}: (0, 360, 0),
        }}
    }}
    
    def Scope "ImageSequence" 
    {{
        def Plane "ImagePlane"
        {{
            float3[] extent = [(-2, -2, 0), (2, 2, 0)]
            int[] faceVertexIndices = [0, 1, 2, 0, 2, 3]
            point3f[] points = [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0)]
            texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
                interpolation = "vertex"
            )
            
            # Material binding with timeSamples for each frame
            rel material:binding.timeSamples = {{
""")

        # Add material bindings for each frame
        for i, image_path in enumerate(images):
            f.write(f"                {i}: </Scene/Materials/FrameMaterial_{i}>,\n")
            
        f.write("""            }
        }
    }
    
    def Scope "Materials"
    {
""")

        # Add material definitions for each frame
        for i, image_path in enumerate(images):
            image_name = os.path.basename(image_path)
            rel_path = f"./test_frames/{image_name}"
            
            f.write(f"""        def Material "FrameMaterial_{i}"
        {{
            token outputs:surface.connect = </Scene/Materials/FrameMaterial_{i}/PBRShader.outputs:surface>
            
            def Shader "PBRShader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (1, 1, 1)
                float inputs:roughness = 0.4
                float inputs:metallic = 0
                token outputs:surface
                
                # Connect texture to diffuseColor
                color3f inputs:diffuseColor.connect = </Scene/Materials/FrameMaterial_{i}/TextureReader.outputs:rgb>
            }}
            
            def Shader "TextureReader"
            {{
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @{rel_path}@
                float2 inputs:st.connect = </Scene/ImageSequence/ImagePlane.inputs:st>
                token inputs:wrapS = "repeat"
                token inputs:wrapT = "repeat"
                float3 outputs:rgb
            }}
        }}
""")

        # Add 3D geometry
        f.write(f"""    }}
    
    # Representation of the 3D geometry from synthetic frames
    def Xform "Geometry"
    {{
        # A cube as seen in our synthetic frames
        def Cube "Cube" (
            kind = "component"
        )
        {{
            float3 xformOp:translate = (0, 0, 0)
            float3 xformOp:scale = (1, 1, 1)
            float3 xformOp:rotateXYZ.timeSamples = {{
                0: (0, 0, 0),
                {len(images) - 1}: (0, 360, 0),
            }}
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            color3f[] primvars:displayColor = [(0, 1, 1)]
        }}
        
        # A pyramid 
        def Cone "Pyramid" (
            kind = "component"
        )
        {{
            float3 xformOp:translate = (0, -2, 0)
            float3 xformOp:scale = (1, 2, 1)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            color3f[] primvars:displayColor = [(1, 0, 0)]
        }}
        
        # A sphere
        def Sphere "Sphere" (
            kind = "component"
        )
        {{
            float3 xformOp:translate = (-2, 0.5, 0)
            float3 xformOp:scale = (0.5, 0.5, 0.5)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            color3f[] primvars:displayColor = [(0, 0, 1)]
        }}
    }}
}}
""")

    print(f"Successfully created enhanced USD scene at {output_file}")
    return True

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Enhanced USD Scene Generator')
    
    parser.add_argument(
        '--image-dir', 
        type=str, 
        default='./test_frames',
        help='Directory containing input images (default: ./test_frames)'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='enhanced_scene.usda',
        help='Output USD file path (default: enhanced_scene.usda)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_args()
        
        # Create enhanced USD scene
        success = create_enhanced_usd_scene(args.image_dir, args.output)
        
        if success:
            print("USD scene creation completed successfully")
            print(f"To view the scene, use usdview: usdview {args.output}")
        else:
            print("Failed to create USD scene")
            return 1
            
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())