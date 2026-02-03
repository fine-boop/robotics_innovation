"""
Photogrammetry processing module for Flask integration
Processes uploaded zip files containing photos and generates 3D models
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
import tempfile


class PhotogrammetryProcessor:
    """
    Handles photogrammetry processing for uploaded photo archives.
    Extracts photos, runs COLMAP pipeline, and creates downloadable model archive.
    """
    
    def __init__(self, uploads_dir='uploads', downloads_dir='downloads'):
        self.uploads_dir = Path(uploads_dir)
        self.downloads_dir = Path(downloads_dir)
        self.workspace_dir = Path('workspace')
        
        # Ensure directories exist
        self.uploads_dir.mkdir(exist_ok=True)
        self.downloads_dir.mkdir(exist_ok=True)
        self.workspace_dir.mkdir(exist_ok=True)
    
    def extract_photos(self, zip_filename):
        """
        Extract photos from uploaded zip file
        Returns path to extracted photos directory
        """
        zip_path = self.uploads_dir / zip_filename
        base_name = zip_filename.rsplit('.', 1)[0]
        extract_path = self.uploads_dir / base_name
        
        # Remove existing extraction directory if present
        if extract_path.exists():
            shutil.rmtree(extract_path)
        
        extract_path.mkdir(exist_ok=True)
        
        # Extract zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Find the actual photos directory (handle nested folders)
        photo_dir = self._find_photo_directory(extract_path)
        
        return photo_dir, base_name
    
    def _find_photo_directory(self, extract_path):
        """
        Find directory containing photos (handles nested zip structures)
        """
        # Look for common image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        
        # Check if photos are directly in extract_path
        images_in_root = [f for f in extract_path.iterdir() 
                         if f.suffix in image_extensions]
        
        if images_in_root:
            return extract_path
        
        # Check one level deep
        for subdir in extract_path.iterdir():
            if subdir.is_dir():
                images_in_subdir = [f for f in subdir.iterdir() 
                                   if f.suffix in image_extensions]
                if images_in_subdir:
                    return subdir
        
        # Default to extract_path if no images found
        return extract_path
    
    def count_photos(self, photo_dir):
        """Count number of valid photo files"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG'}
        return len([f for f in photo_dir.iterdir() if f.suffix in image_extensions])
    
    def run_colmap_pipeline(self, photo_dir, output_name):
        """
        Run COLMAP photogrammetry pipeline
        Returns True if successful, False otherwise
        """
        # Create workspace for this specific project
        project_workspace = self.workspace_dir / output_name
        if project_workspace.exists():
            shutil.rmtree(project_workspace)
        project_workspace.mkdir(parents=True)
        
        database_path = project_workspace / "database.db"
        sparse_dir = project_workspace / "sparse"
        dense_dir = project_workspace / "dense"
        sparse_dir.mkdir(exist_ok=True)
        dense_dir.mkdir(exist_ok=True)
        
        try:
            # Step 1: Feature extraction
            print(f"[{output_name}] Running feature extraction...")
            subprocess.run([
                "colmap", "feature_extractor",
                "--database_path", str(database_path),
                "--image_path", str(photo_dir),
                "--ImageReader.single_camera", "1"
            ], check=True, capture_output=True)
            
            # Step 2: Feature matching
            print(f"[{output_name}] Running feature matching...")
            subprocess.run([
                "colmap", "exhaustive_matcher",
                "--database_path", str(database_path)
            ], check=True, capture_output=True)
            
            # Step 3: Sparse reconstruction
            print(f"[{output_name}] Running sparse reconstruction...")
            subprocess.run([
                "colmap", "mapper",
                "--database_path", str(database_path),
                "--image_path", str(photo_dir),
                "--output_path", str(sparse_dir)
            ], check=True, capture_output=True)
            
            # Check if reconstruction succeeded
            reconstruction_dir = sparse_dir / "0"
            if not reconstruction_dir.exists():
                print(f"[{output_name}] ERROR: Sparse reconstruction failed")
                return False
            
            # Step 4: Image undistortion
            print(f"[{output_name}] Running image undistortion...")
            subprocess.run([
                "colmap", "image_undistorter",
                "--image_path", str(photo_dir),
                "--input_path", str(reconstruction_dir),
                "--output_path", str(dense_dir),
                "--output_type", "COLMAP"
            ], check=True, capture_output=True)
            
            # Step 5: Stereo matching (patch match)
            print(f"[{output_name}] Running stereo matching...")
            subprocess.run([
                "colmap", "patch_match_stereo",
                "--workspace_path", str(dense_dir),
                "--workspace_format", "COLMAP",
                "--PatchMatchStereo.geom_consistency", "true"
            ], check=True, capture_output=True)
            
            # Step 6: Stereo fusion
            print(f"[{output_name}] Running stereo fusion...")
            fused_ply = dense_dir / "fused.ply"
            subprocess.run([
                "colmap", "stereo_fusion",
                "--workspace_path", str(dense_dir),
                "--workspace_format", "COLMAP",
                "--input_type", "geometric",
                "--output_path", str(fused_ply)
            ], check=True, capture_output=True)
            
            # Step 7: Poisson meshing (final mesh)
            print(f"[{output_name}] Running Poisson meshing...")
            meshed_ply = dense_dir / "meshed-poisson.ply"
            subprocess.run([
                "colmap", "poisson_mesher",
                "--input_path", str(fused_ply),
                "--output_path", str(meshed_ply)
            ], check=True, capture_output=True)
            
            # Verify final model exists
            if not meshed_ply.exists():
                print(f"[{output_name}] ERROR: Final mesh not created")
                return False
            
            print(f"[{output_name}] ✓ Pipeline completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[{output_name}] ERROR in COLMAP pipeline: {e}")
            print(f"stderr: {e.stderr.decode() if e.stderr else 'none'}")
            return False
        except Exception as e:
            print(f"[{output_name}] ERROR: {e}")
            return False
    
    def create_output_archive(self, output_name):
        """
        Create downloadable zip archive with the 3D model
        Returns path to created archive
        """
        project_workspace = self.workspace_dir / output_name
        dense_dir = project_workspace / "dense"
        
        # Files to include in output
        model_file = dense_dir / "meshed-poisson.ply"
        point_cloud = dense_dir / "fused.ply"
        
        # Create output zip
        output_zip = self.downloads_dir / f"{output_name}.zip"
        
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add main mesh
            if model_file.exists():
                zipf.write(model_file, f"{output_name}_model.ply")
            
            # Add point cloud
            if point_cloud.exists():
                zipf.write(point_cloud, f"{output_name}_pointcloud.ply")
            
            # Add README
            readme_content = f"""3D Model: {output_name}
Generated using COLMAP photogrammetry

Files included:
- {output_name}_model.ply: Final 3D mesh (Poisson reconstruction)
- {output_name}_pointcloud.ply: Dense point cloud

Viewing instructions:
1. Open .ply files in MeshLab, Blender, or CloudCompare
2. In Blender: File > Import > Stanford (.ply)
3. In MeshLab: File > Import Mesh

The model file is the final mesh suitable for editing and export.
The point cloud shows the raw reconstructed points before meshing.
"""
            zipf.writestr(f"{output_name}_README.txt", readme_content)
        
        return output_zip
    
    def cleanup_workspace(self, output_name):
        """Clean up temporary workspace files"""
        project_workspace = self.workspace_dir / output_name
        if project_workspace.exists():
            shutil.rmtree(project_workspace)
    
    def cleanup_uploads(self, zip_filename, base_name):
        """Clean up uploaded files after processing"""
        # Remove zip file
        zip_path = self.uploads_dir / zip_filename
        if zip_path.exists():
            os.remove(zip_path)
        
        # Remove extracted directory
        extract_path = self.uploads_dir / base_name
        if extract_path.exists():
            shutil.rmtree(extract_path)


# Main processing function for Flask integration
def process_photogrammetry(filename):
    """
    Main entry point for photogrammetry processing
    Called from Flask app with uploaded zip filename
    """
    print(f"\n{'='*60}")
    print(f"Starting photogrammetry processing: {filename}")
    print(f"{'='*60}\n")
    
    processor = PhotogrammetryProcessor()
    
    try:
        # Extract photos from zip
        print(f"Extracting photos from {filename}...")
        photo_dir, base_name = processor.extract_photos(filename)
        
        # Count photos
        photo_count = processor.count_photos(photo_dir)
        print(f"Found {photo_count} photos")
        
        if photo_count < 8:
            print(f"WARNING: Only {photo_count} photos. Recommend 20+ for good results.")
        
        # Run COLMAP pipeline
        print(f"\nRunning COLMAP photogrammetry pipeline...")
        print(f"This may take 30 minutes to several hours depending on:")
        print(f"  - Number of photos ({photo_count})")
        print(f"  - Image resolution")
        print(f"  - Available hardware (CPU/GPU)")
        print()
        
        success = processor.run_colmap_pipeline(photo_dir, base_name)
        
        if not success:
            print(f"\nERROR: Photogrammetry pipeline failed for {filename}")
            print(f"Common causes:")
            print(f"  - Not enough overlapping photos")
            print(f"  - Photos lack distinctive features")
            print(f"  - Object moved between shots")
            print(f"  - Insufficient lighting/focus")
            processor.cleanup_uploads(filename, base_name)
            return
        
        # Create output archive
        print(f"\nCreating output archive...")
        output_zip = processor.create_output_archive(base_name)
        print(f"✓ Created: {output_zip}")
        
        # Cleanup
        print(f"\nCleaning up temporary files...")
        processor.cleanup_workspace(base_name)
        processor.cleanup_uploads(filename, base_name)
        
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS: {base_name}.zip ready for download")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR processing {filename}: {e}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
