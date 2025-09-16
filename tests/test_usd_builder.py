#!/usr/bin/env python3
"""
Unit tests for the USD builder module
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
from unittest.mock import patch, MagicMock, Mock

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock the pxr import since it might not be available in the test environment
sys.modules['pxr'] = MagicMock()
sys.modules['pxr.Usd'] = MagicMock()
sys.modules['pxr.UsdGeom'] = MagicMock()
sys.modules['pxr.UsdShade'] = MagicMock()
sys.modules['pxr.Sdf'] = MagicMock()
sys.modules['pxr.Gf'] = MagicMock()
sys.modules['pxr.Vt'] = MagicMock()

# After mocking the modules, import the module under test
from src.usd_builder import UsdSceneBuilder


class TestUsdBuilder(unittest.TestCase):
    """Test cases for the USD builder module"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create temporary directories for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.image_dir = self.test_dir / "images"
        self.output_dir = self.test_dir / "output"
        
        # Create the directories
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test image in the image directory
        self.test_image_path = self.image_dir / "test_image.jpg"
        self.create_test_image(self.test_image_path)
        
        # Create a dummy point cloud file
        self.test_pointcloud_path = self.test_dir / "test_pointcloud.ply"
        self.create_test_pointcloud(self.test_pointcloud_path)
        
        # Path for output USD file
        self.usd_output_path = self.output_dir / "test_scene.usda"
        
        # Create the USD builder instance
        self.usd_builder = UsdSceneBuilder(
            image_dir=str(self.image_dir),
            output_file=str(self.usd_output_path),
            point_cloud=str(self.test_pointcloud_path)
        )
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_image(self, path):
        """Create a test image file for testing"""
        # Create a simple test image (black 10x10 image)
        try:
            import cv2
            img = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.imwrite(str(path), img)
        except ImportError:
            # If cv2 is not available, create an empty file
            with open(path, 'wb') as f:
                f.write(b'\x00' * 100)  # Just some dummy content
    
    def create_test_pointcloud(self, path):
        """Create a test PLY file for testing"""
        # Create a minimal valid PLY file
        with open(path, 'w') as f:
            f.write("""ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
end_header
0.0 0.0 0.0
1.0 0.0 0.0
0.0 1.0 0.0
""")
    
    def test_initialization(self):
        """Test that the USD builder initializes correctly"""
        # Check that the directories and paths are set correctly
        assert self.usd_builder.image_dir == self.image_dir
        assert self.usd_builder.output_file == self.usd_output_path
        assert self.usd_builder.point_cloud == self.test_pointcloud_path
    
    def test_find_latest_image(self):
        """Test finding the latest image in the images directory"""
        # Create a few images with different timestamps
        image1 = self.image_dir / "image1.jpg"
        image2 = self.image_dir / "image2.jpg"
        image3 = self.image_dir / "image3.jpg"
        
        # First remove any existing test image that might be there
        if self.test_image_path.exists():
            self.test_image_path.unlink()
        
        # Create the images with increasing timestamps
        self.create_test_image(image1)
        self.create_test_image(image2)
        self.create_test_image(image3)
        
        # Set modification times to different values
        # Use different timestamps to ensure proper ordering
        os.utime(image1, (1000000, 1000000))
        os.utime(image2, (2000000, 2000000))
        os.utime(image3, (3000000, 3000000))
        
        # Find the latest image
        latest_image = self.usd_builder.find_latest_image()
        
        # Check that the latest image is image3
        assert latest_image == image3
    
    def test_create_stage(self):
        """Test creating a USD stage"""
        # Mock the Stage.CreateNew method
        pxr_mock = sys.modules['pxr']
        usd_mock = pxr_mock.Usd
        usd_geom_mock = pxr_mock.UsdGeom
        
        # Create mocks for the stage and related objects
        mock_stage = MagicMock()
        usd_mock.Stage.CreateNew = MagicMock(return_value=mock_stage)
        
        mock_xform = MagicMock()
        usd_geom_mock.Xform.Define = MagicMock(return_value=mock_xform)
        
        mock_prim = MagicMock()
        mock_xform.GetPrim.return_value = mock_prim
        
        # Create the stage
        stage = self.usd_builder.create_stage()
        
        # Check that the stage was created with the right file path
        usd_mock.Stage.CreateNew.assert_called_once_with(str(self.usd_output_path))
        
        # Check that stage setup was done
        usd_geom_mock.SetStageUpAxis.assert_called_once()
        mock_stage.SetStartTimeCode.assert_called_once()
        mock_stage.SetEndTimeCode.assert_called_once()
        mock_stage.SetTimeCodesPerSecond.assert_called_once()
        
        # Check that the default prim was set
        mock_stage.SetDefaultPrim.assert_called_once_with(mock_prim)
    
    def test_add_plane(self):
        """Test adding a plane geometry to the USD stage"""
        # Mock the stage and related USD objects
        mock_stage = MagicMock()
        pxr_mock = sys.modules['pxr']
        
        # Set up the UsdGeom.Mesh.Define mock
        mock_mesh = MagicMock()
        pxr_mock.UsdGeom.Mesh.Define = MagicMock(return_value=mock_mesh)
        
        # Mock Vt arrays
        pxr_mock.Vt.Vec3fArray = MagicMock(return_value="MockVec3fArray")
        pxr_mock.Vt.Vec2fArray = MagicMock(return_value="MockVec2fArray")
        pxr_mock.Vt.IntArray = MagicMock(return_value="MockIntArray")
        
        # Mock UsdGeom.PrimvarsAPI
        mock_primvars_api = MagicMock()
        pxr_mock.UsdGeom.PrimvarsAPI = MagicMock(return_value=mock_primvars_api)
        mock_texcoords_attr = MagicMock()
        mock_primvars_api.CreatePrimvar.return_value = mock_texcoords_attr
        
        # Add the plane
        plane = self.usd_builder.add_plane(mock_stage)
        
        # Check that the mesh was created with the right path
        pxr_mock.UsdGeom.Mesh.Define.assert_called_once_with(mock_stage, '/World/plane')
        
        # Check that points, indices, and UVs were set
        mock_mesh.CreatePointsAttr.assert_called_once()
        mock_mesh.CreateFaceVertexCountsAttr.assert_called_once()
        mock_mesh.CreateFaceVertexIndicesAttr.assert_called_once()
        mock_mesh.CreateNormalsAttr.assert_called_once()
        
        # Check that primvar for UVs was created
        pxr_mock.UsdGeom.PrimvarsAPI.assert_called_once_with(mock_mesh)
        mock_primvars_api.CreatePrimvar.assert_called_once()
        mock_texcoords_attr.Set.assert_called_once()
    
    def test_create_material(self):
        """Test creating a USD Preview Surface material"""
        # Mock the stage and USD objects
        mock_stage = MagicMock()
        pxr_mock = sys.modules['pxr']
        
        # Mock material
        mock_material = MagicMock()
        pxr_mock.UsdShade.Material.Define = MagicMock(return_value=mock_material)
        
        # Mock shaders
        mock_shader = MagicMock()
        mock_texture_sampler = MagicMock()
        pxr_mock.UsdShade.Shader.Define = MagicMock(side_effect=[mock_shader, mock_texture_sampler])
        
        # Mock material outputs and shader outputs
        mock_surface_output = MagicMock()
        mock_material.CreateSurfaceOutput.return_value = mock_surface_output
        mock_texture_output = MagicMock()
        mock_texture_sampler.CreateOutput.return_value = mock_texture_output
        
        # Create the material
        material = self.usd_builder.create_material(mock_stage, "test_texture.jpg")
        
        # Check that the material was created with the right path
        pxr_mock.UsdShade.Material.Define.assert_called_once_with(mock_stage, '/World/Materials/TexturedMaterial')
        
        # Check that shaders were created
        assert pxr_mock.UsdShade.Shader.Define.call_count == 2
        
        # Check that shader inputs were set
        assert mock_shader.CreateInput.call_count >= 2  # roughness and metallic
        assert mock_texture_sampler.CreateInput.call_count >= 3  # file, wrapS, wrapT
        
        # Check that outputs were created and connected
        mock_texture_sampler.CreateOutput.assert_called_once()
        mock_material.CreateSurfaceOutput.assert_called_once()
        mock_surface_output.ConnectToSource.assert_called_once()
    
    def test_add_point_cloud(self):
        """Test adding a point cloud to the USD stage"""
        # Mock the stage and USD objects
        mock_stage = MagicMock()
        pxr_mock = sys.modules['pxr']
        
        # Mock points
        mock_points = MagicMock()
        pxr_mock.UsdGeom.Points.Define = MagicMock(return_value=mock_points)
        
        # Mock the prim and references
        mock_prim = MagicMock()
        mock_points.GetPrim.return_value = mock_prim
        mock_references = MagicMock()
        mock_prim.GetReferences.return_value = mock_references
        
        # Add the point cloud
        points = self.usd_builder.add_point_cloud(mock_stage, str(self.test_pointcloud_path))
        
        # Check that the points were created with the right path
        pxr_mock.UsdGeom.Points.Define.assert_called_once_with(mock_stage, '/World/PointCloud')
        
        # Check that the reference was added
        mock_prim.GetReferences.assert_called_once()
        mock_references.AddReference.assert_called_once_with(str(self.test_pointcloud_path))
    
    def test_apply_material_to_mesh(self):
        """Test applying a material to a mesh"""
        # Mock the material, mesh, and binding API
        mock_material = MagicMock()
        mock_mesh = MagicMock()
        mock_binding_api = MagicMock()
        
        # Mock the MaterialBindingAPI constructor
        pxr_mock = sys.modules['pxr']
        pxr_mock.UsdShade.MaterialBindingAPI = MagicMock(return_value=mock_binding_api)
        
        # Apply the material
        self.usd_builder.apply_material_to_mesh(mock_material, mock_mesh)
        
        # Check that the binding API was created and used
        pxr_mock.UsdShade.MaterialBindingAPI.assert_called_once_with(mock_mesh)
        mock_binding_api.Bind.assert_called_once_with(mock_material)
    
    @patch('src.usd_builder.UsdSceneBuilder.find_latest_image')
    @patch('src.usd_builder.UsdSceneBuilder.create_stage')
    @patch('src.usd_builder.UsdSceneBuilder.add_point_cloud')
    @patch('src.usd_builder.UsdSceneBuilder.add_plane')
    @patch('src.usd_builder.UsdSceneBuilder.create_material')
    @patch('src.usd_builder.UsdSceneBuilder.apply_material_to_mesh')
    def test_build_scene_with_point_cloud(
        self, mock_apply_material, mock_create_material, mock_add_plane,
        mock_add_point_cloud, mock_create_stage, mock_find_latest_image
    ):
        """Test building a scene with a point cloud"""
        # Mock dependencies
        mock_stage = MagicMock()
        mock_create_stage.return_value = mock_stage
        mock_latest_image = self.image_dir / "latest.jpg"
        mock_find_latest_image.return_value = mock_latest_image
        mock_point_cloud = MagicMock()
        mock_add_point_cloud.return_value = mock_point_cloud
        
        # Build the scene
        result = self.usd_builder.build_scene()
        
        # Check the result
        assert result is True
        
        # Check that the methods were called in the right order
        mock_find_latest_image.assert_called_once()
        mock_create_stage.assert_called_once()
        mock_add_point_cloud.assert_called_once_with(mock_stage, str(self.test_pointcloud_path))
        
        # When using a point cloud, we don't expect to create a plane or material
        mock_add_plane.assert_not_called()
        mock_create_material.assert_not_called()
        mock_apply_material.assert_not_called()
        
        # Check that the stage was saved
        mock_stage.Save.assert_called_once()
    
    @patch('src.usd_builder.UsdSceneBuilder.find_latest_image')
    @patch('src.usd_builder.UsdSceneBuilder.create_stage')
    @patch('src.usd_builder.UsdSceneBuilder.add_point_cloud')
    @patch('src.usd_builder.UsdSceneBuilder.add_plane')
    @patch('src.usd_builder.UsdSceneBuilder.create_material')
    @patch('src.usd_builder.UsdSceneBuilder.apply_material_to_mesh')
    def test_build_scene_with_plane_fallback(
        self, mock_apply_material, mock_create_material, mock_add_plane,
        mock_add_point_cloud, mock_create_stage, mock_find_latest_image
    ):
        """Test building a scene with a plane (no point cloud)"""
        # Mock dependencies
        mock_stage = MagicMock()
        mock_create_stage.return_value = mock_stage
        mock_latest_image = self.image_dir / "latest.jpg"
        mock_find_latest_image.return_value = mock_latest_image
        
        # Set up point cloud to be None
        self.usd_builder.point_cloud = None
        
        # Mock plane and material
        mock_plane = MagicMock()
        mock_add_plane.return_value = mock_plane
        mock_material = MagicMock()
        mock_create_material.return_value = mock_material
        
        # Build the scene
        result = self.usd_builder.build_scene()
        
        # Check the result
        assert result is True
        
        # Check that the methods were called in the right order
        mock_find_latest_image.assert_called_once()
        mock_create_stage.assert_called_once()
        mock_add_plane.assert_called_once_with(mock_stage)
        mock_create_material.assert_called_once_with(mock_stage, str(mock_latest_image))
        mock_apply_material.assert_called_once_with(mock_material, mock_plane)
        
        # When not using a point cloud, we don't expect to add one
        mock_add_point_cloud.assert_not_called()
        
        # Check that the stage was saved
        mock_stage.Save.assert_called_once()


# Create a test for the integration points between modules
class TestIntegration(unittest.TestCase):
    """Test the integration points between the different modules"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create temporary directories for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / "config"
        self.image_dir = self.test_dir / "images"
        self.colmap_dir = self.test_dir / "colmap_out"
        self.output_dir = self.test_dir / "output"
        
        # Create the directories
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.colmap_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Path for output USD file
        self.usd_output_path = self.output_dir / "test_scene.usda"
        
        # Create a test config file
        self.config_file = self.config_dir / "test_config.yaml"
        self.create_test_config(self.config_file)
        
        # Create test images
        self.create_test_images()
        
        # Create a dummy colmap output
        self.create_colmap_output()
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove temporary directory
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_config(self, path):
        """Create a test configuration file"""
        config = {
            'cameras': [
                {
                    'name': 'TestCamera',
                    'host': '192.168.1.100',
                    'onvif_port': 80,
                    'username': 'admin',
                    'password': 'password',
                    'rtsp_url': 'rtsp://192.168.1.100:554/live/main'
                }
            ],
            'settings': {
                'capture': {
                    'frame_interval': 1,
                    'total_frames': 5,
                    'output_dir': str(self.image_dir)
                },
                'photogrammetry': {
                    'enabled': True,
                    'colmap_path': '/usr/bin/colmap',
                    'output_dir': str(self.colmap_dir)
                },
                'usd': {
                    'scene_name': 'test_scene',
                    'output_path': str(self.output_dir / "test_scene.usda")
                }
            }
        }
        
        import yaml
        with open(path, 'w') as f:
            yaml.dump(config, f)
    
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
    
    def create_colmap_output(self):
        """Create a dummy COLMAP output structure"""
        # Create dense directory
        dense_dir = self.colmap_dir / "dense"
        dense_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy point cloud
        ply_path = dense_dir / "fused.ply"
        with open(ply_path, 'w') as f:
            f.write("""ply
format ascii 1.0
element vertex 3
property float x
property float y
property float z
end_header
0.0 0.0 0.0
1.0 0.0 0.0
0.0 1.0 0.0
""")
    
    @patch('src.capture.CameraCapture')
    @patch('src.photogrammetry.ColmapWrapper')
    @patch('src.usd_builder.UsdSceneBuilder')
    def test_full_pipeline_integration(self, mock_usd_builder_class, mock_colmap_class, mock_capture_class):
        """Test the full pipeline integration with mocked components"""
        # Import the main module here to avoid circular imports during testing
        from src import main
        
        # Mock the command line arguments
        test_args = [
            'main.py',
            '--config', str(self.config_file),
            '--image-dir', str(self.image_dir),
            '--colmap-dir', str(self.colmap_dir),
            '--output', str(self.usd_output_path)
        ]
        with patch('sys.argv', test_args):
            # Mock the instances
            mock_capture = MagicMock()
            mock_capture_class.return_value = mock_capture
            
            mock_colmap = MagicMock()
            mock_colmap_class.return_value = mock_colmap
            mock_colmap.run_pipeline.return_value = True
            
            mock_usd_builder = MagicMock()
            mock_usd_builder_class.return_value = mock_usd_builder
            mock_usd_builder.build_scene.return_value = True
            
            # Run the main function
            main_result = main.main()
            
            # Check that it completed successfully
            assert main_result == 0
            
            # Check that each component was initialized with the right parameters
            mock_capture_class.assert_called_once_with(str(self.config_file))
            mock_capture.capture_all_cameras.assert_called_once()
            
            mock_colmap_class.assert_called_once()
            call_args = mock_colmap_class.call_args[1]
            assert call_args['image_dir'] == str(self.image_dir)
            assert call_args['output_dir'] == str(self.colmap_dir)
            mock_colmap.run_pipeline.assert_called_once()
            
            mock_usd_builder_class.assert_called_once()
            # In main.py, UsdSceneBuilder is called with (args.image_dir, args.output)
            mock_usd_builder_class.assert_called_once_with(str(self.image_dir), str(self.usd_output_path))
            mock_usd_builder.build_scene.assert_called_once()

if __name__ == '__main__':
    pytest.main(['-xvs', __file__])