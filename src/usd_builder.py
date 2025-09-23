#!/usr/bin/env python3
"""
USD Scene Builder

Creates a USD stage with a plane geometry and applies a UsdPreviewSurface material
with the latest image from ./images/ as a texture.
"""

import os
import sys
import logging
import glob
import argparse
from pathlib import Path
from typing import Optional, Tuple, Any

# Import USD modules
try:
    from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf, Vt
    HAS_USD = True
except ImportError:
    HAS_USD = False
    logging.warning("pxr (OpenUSD) package not found. Will create a placeholder USD file instead.")
    # We'll just use Any for type hints when pxr is not available
    Usd = UsdGeom = UsdShade = Sdf = Gf = Vt = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('usd_builder.log')
    ]
)

logger = logging.getLogger('usd_builder')

class UsdSceneBuilder:
    """Creates USD scenes with photogrammetry data and textures"""
    
    def __init__(self, image_dir: str = './images', output_file: str = 'photoreal_scene.usda', point_cloud: str = None):
        """
        Initialize the USD Scene Builder
        
        Args:
            image_dir: Directory containing captured images
            output_file: Path to save the USD scene
            point_cloud: Optional path to a point cloud file (.ply) from photogrammetry
        """
        self.image_dir = Path(image_dir)
        self.output_file = Path(output_file)
        self.point_cloud = Path(point_cloud) if point_cloud else None
        
        # Create output directory if needed
        if not self.output_file.parent.exists():
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"USD Scene Builder initialized. Output will be saved to {self.output_file}")
        if self.point_cloud:
            logger.info(f"Using point cloud from: {self.point_cloud}")
    
    def find_latest_image(self) -> Optional[Path]:
        """
        Find the most recent image in the images directory
        
        Returns:
            Path to the latest image or None if no images found
        """
        try:
            # Get all jpg files in the directory
            image_files = list(self.image_dir.glob('*.jpg'))
            
            if not image_files:
                # Try subdirectories if no images found in main directory
                image_files = list(self.image_dir.glob('**/*.jpg'))
                
            if not image_files:
                logger.error(f"No images found in {self.image_dir}")
                return None
                
            # Sort by modification time (newest first)
            latest_image = max(image_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"Latest image found: {latest_image}")
            return latest_image
            
        except Exception as e:
            logger.error(f"Error finding latest image: {e}")
            return None
    
    def create_stage(self):
        """
        Create a new USD stage
        
        Returns:
            A new USD stage
        """
        try:
            stage = Usd.Stage.CreateNew(str(self.output_file))
            
            # Set up axis conventions (Y-up)
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
            
            # Set stage metadata
            stage.SetStartTimeCode(1)
            stage.SetEndTimeCode(1)
            stage.SetTimeCodesPerSecond(24)
            
            # Add default prim
            root_prim = UsdGeom.Xform.Define(stage, '/World')
            stage.SetDefaultPrim(root_prim.GetPrim())
            
            logger.info("Created new USD stage")
            return stage
            
        except Exception as e:
            logger.error(f"Failed to create USD stage: {e}")
            raise
    
    def add_plane(self, stage, size: Tuple[float, float] = (10.0, 10.0)):
        """
        Add a plane geometry to the USD stage
        
        Args:
            stage: USD stage to add the plane to
            size: Width and height of the plane
            
        Returns:
            The created mesh
        """
        try:
            # Create a plane mesh
            plane_path = '/World/plane'
            plane = UsdGeom.Mesh.Define(stage, plane_path)
            
            # Set mesh attributes (create a simple quad)
            width, height = size
            half_width = width / 2.0
            half_height = height / 2.0
            
            # Define vertices (counter-clockwise, Y-up)
            points = Vt.Vec3fArray([
                Gf.Vec3f(-half_width, 0, -half_height),  # bottom-left
                Gf.Vec3f(half_width, 0, -half_height),   # bottom-right
                Gf.Vec3f(half_width, 0, half_height),    # top-right
                Gf.Vec3f(-half_width, 0, half_height)    # top-left
            ])
            
            # Define UVs
            texCoords = Vt.Vec2fArray([
                Gf.Vec2f(0, 0),  # bottom-left
                Gf.Vec2f(1, 0),  # bottom-right
                Gf.Vec2f(1, 1),  # top-right
                Gf.Vec2f(0, 1)   # top-left
            ])
            
            # Define face
            faceVertexCounts = Vt.IntArray([4])  # One quad with 4 vertices
            faceVertexIndices = Vt.IntArray([0, 1, 2, 3])  # Counter-clockwise order
            
            # Set mesh attributes
            plane.CreatePointsAttr(points)
            plane.CreateFaceVertexCountsAttr(faceVertexCounts)
            plane.CreateFaceVertexIndicesAttr(faceVertexIndices)
            
            # Set UVs
            primvarsAPI = UsdGeom.PrimvarsAPI(plane)
            texCoordsAttr = primvarsAPI.CreatePrimvar(
                "st", 
                Sdf.ValueTypeNames.Float2Array,
                UsdGeom.Tokens.vertex
            )
            texCoordsAttr.Set(texCoords)
            
            # Set normals (all facing up)
            normals = Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)] * 4)  # Same normal for all vertices
            plane.CreateNormalsAttr(normals)
            
            logger.info(f"Added plane with dimensions {width}x{height}")
            return plane
            
        except Exception as e:
            logger.error(f"Failed to create plane geometry: {e}")
            raise
    
    def create_material(self, stage, texture_path: str):
        """
        Create a USD Preview Surface material with the provided texture
        
        Args:
            stage: USD stage to add the material to
            texture_path: Path to the texture image
            
        Returns:
            The created material
        """
        try:
            # Create material
            material_path = '/World/Materials/TexturedMaterial'
            material = UsdShade.Material.Define(stage, material_path)
            
            # Create shader
            shader = UsdShade.Shader.Define(stage, f"{material_path}/PBRShader")
            shader.CreateIdAttr("UsdPreviewSurface")
            
            # Set basic PBR parameters
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
            
            # Create texture sampler shader
            texture_sampler = UsdShade.Shader.Define(stage, f"{material_path}/diffuseTexture")
            texture_sampler.CreateIdAttr("UsdUVTexture")
            
            # Set texture file
            texture_sampler.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_path)
            
            # Set texture wrap mode to repeat
            texture_sampler.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
            texture_sampler.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
            
            # Connect texture to shader
            texture_sampler.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                texture_sampler, "rgb"
            )
            
            # Connect shader to material outputs
            material.CreateSurfaceOutput().ConnectToSource(shader, "surface")
            
            logger.info(f"Created material with texture: {texture_path}")
            return material
            
        except Exception as e:
            logger.error(f"Failed to create material: {e}")
            raise
    
    def apply_material_to_mesh(self, material, mesh):
        """
        Apply the material to the mesh
        
        Args:
            material: Material to apply
            mesh: Target mesh
        """
        try:
            # Bind material to mesh
            UsdShade.MaterialBindingAPI(mesh).Bind(material)
            logger.info(f"Applied material to mesh: {mesh.GetPath()}")
            
        except Exception as e:
            logger.error(f"Failed to apply material to mesh: {e}")
            raise
    
    def add_point_cloud(self, stage, point_cloud_path: str):
        """
        Add a point cloud to the USD stage
        
        Args:
            stage: USD stage to add the point cloud to
            point_cloud_path: Path to the point cloud file (.ply)
            
        Returns:
            The created Points prim
        """
        try:
            # Create a points prim
            points_path = '/World/PointCloud'
            points_prim = UsdGeom.Points.Define(stage, points_path)
            
            # For a basic integration we'll just reference the .ply file
            # In a real application, you would parse the PLY and set point attributes
            points_prim.GetPrim().GetReferences().AddReference(point_cloud_path)
            
            logger.info(f"Added point cloud from {point_cloud_path}")
            return points_prim
            
        except Exception as e:
            logger.error(f"Failed to add point cloud: {e}")
            logger.info("Falling back to simple plane geometry")
            return None
    
    def build_scene(self):
        """
        Build the complete USD scene
        """
        try:
            # Find latest image
            latest_image = self.find_latest_image()
            
            if not latest_image:
                logger.error("No images found. Cannot create textured scene.")
                return False
                
            # Check if USD is available
            if not HAS_USD:
                # Find all image files
                image_files = []
                try:
                    # Get all jpg files in the directory
                    image_files = sorted(list(Path(self.image_dir).glob('*.jpg')))
                    if not image_files:
                        # Try subdirectories if no images found in main directory
                        image_files = sorted(list(Path(self.image_dir).glob('**/*.jpg')))
                        
                    if not image_files:
                        logger.error(f"No images found in {self.image_dir} and pxr (OpenUSD) not available. Cannot generate USD scene.")
                        return False
                
                except Exception as e:
                    logger.error(f"Error finding images: {e}")
                    return False
                
                # Start building an enhanced placeholder USD file
                logger.info(f"Creating enhanced placeholder USD file with {len(image_files)} frames")
                
                # Create a placeholder USD file that references all images
                with open(self.output_file, 'w') as f:
                    # Write header
                    f.write(f"""#usda 1.0
(
    defaultPrim = "World"
    upAxis = "Y"
    timeCodesPerSecond = 24
    startTimeCode = 0
    endTimeCode = {len(image_files) - 1}
)

def Xform "World"
{{
    # This is an enhanced placeholder USD file
    # Point cloud reference would have been: {self.point_cloud if self.point_cloud else 'None'}
    # Total images available: {len(image_files)}
    
    def Camera "Camera"
    {{
        float3 xformOp:translate = (0, 1.5, 5)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        float focalLength = 35
        float horizontalAperture = 36
        float verticalAperture = 24
        
        # Camera animation around Y axis
        float3 xformOp:rotateXYZ.timeSamples = {{
            0: (0, 0, 0),
            {len(image_files) - 1}: (0, 360, 0),
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
            rel material:binding.timeSamples = {{""")
                    # Add material bindings for each frame
                    for i, image_path in enumerate(image_files):
                        f.write(f"                {i}: </World/Materials/FrameMaterial_{i}>,\n")
                    
                    f.write("""            }
        }
    }
    
    def Scope "Materials"
    {
""")
                    
                    # Add material definitions for each frame
                    for i, image_path in enumerate(image_files):
                        rel_path = str(image_path).replace(str(Path(self.image_dir).parent) + "/", "./")
                        f.write(f"""        def Material "FrameMaterial_{i}"
        {{
            token outputs:surface.connect = </World/Materials/FrameMaterial_{i}/PBRShader.outputs:surface>
            
            def Shader "PBRShader"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (1, 1, 1)
                float inputs:roughness = 0.4
                float inputs:metallic = 0
                token outputs:surface
                
                # Connect texture to diffuseColor
                color3f inputs:diffuseColor.connect = </World/Materials/FrameMaterial_{i}/TextureReader.outputs:rgb>
            }}
            
            def Shader "TextureReader"
            {{
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @{rel_path}@
                float2 inputs:st.connect = </World/ImageSequence/ImagePlane.inputs:st>
                token inputs:wrapS = "repeat"
                token inputs:wrapT = "repeat"
                float3 outputs:rgb
            }}
        }}
""")
                    
                    # Add a representation of the 3D geometry
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
                {len(image_files) - 1}: (0, 360, 0),
            }}
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            color3f[] primvars:displayColor = [(0, 255, 255)]
        }}
        
        # A pyramid 
        def Cone "Pyramid" (
            kind = "component"
        )
        {{
            float3 xformOp:translate = (0, -2, 0)
            float3 xformOp:scale = (1, 2, 1)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            color3f[] primvars:displayColor = [(255, 0, 0)]
        }}
        
        # A sphere
        def Sphere "Sphere" (
            kind = "component"
        )
        {{
            float3 xformOp:translate = (-2, 0.5, 0)
            float3 xformOp:scale = (0.5, 0.5, 0.5)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            color3f[] primvars:displayColor = [(0, 0, 255)]
        }}
    }}
    
    # This would typically come from photogrammetry point cloud
    def PointInstancer "SyntheticPointCloud" (
        kind = "component"
    )
    {{
        point3f[] positions = [
            # Synthetic points representing what would come from photogrammetry
            (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (-1, 0, 0), (0, -1, 0), (0, 0, -1),
            (1, 1, 1), (-1, -1, -1), (1, -1, 1), (-1, 1, -1),
            # Many more points would be included here
        ]
        
        int[] protoIndices = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        
        def Sphere "PointPrototype"
        {{
            double radius = 0.01
            color3f[] primvars:displayColor = [(1, 1, 1)]
        }}
    }}
}}
""")
                    logger.info(f"Created enhanced placeholder USD file at {self.output_file} with {len(image_files)} frames (pxr not available)")
                    return True
            
            # If USD is available, create proper USD stage
            stage = self.create_stage()
            
            # If we have a point cloud from photogrammetry, use it
            if self.point_cloud and self.point_cloud.exists():
                logger.info(f"Adding point cloud from {self.point_cloud}")
                self.add_point_cloud(stage, str(self.point_cloud))
            else:
                logger.info("No point cloud provided. Creating simple plane geometry.")
                # Add plane geometry as fallback
                plane = self.add_plane(stage)
                
                # Create material with texture
                material = self.create_material(stage, str(latest_image))
                
                # Apply material to plane
                self.apply_material_to_mesh(material, plane)
            
            # Save the USD stage
            stage.Save()
            
            logger.info(f"Successfully saved USD scene to {self.output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build USD scene: {e}")
            return False

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='USD Scene Builder')
    
    parser.add_argument(
        '--image-dir', 
        type=str, 
        default='./images',
        help='Directory containing input images (default: ./images)'
    )
    
    parser.add_argument(
        '--output', 
        type=str, 
        default='photoreal_scene.usda',
        help='Output USD file path (default: photoreal_scene.usda)'
    )
    
    parser.add_argument(
        '--point-cloud', 
        type=str, 
        default=None,
        help='Path to point cloud file from photogrammetry (.ply)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point"""
    try:
        # Parse arguments
        args = parse_args()
        
        logger.info("Starting USD scene builder")
        builder = UsdSceneBuilder(args.image_dir, args.output, args.point_cloud)
        builder.build_scene()
        logger.info("USD scene building complete")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)

if __name__ == "__main__":
    main()