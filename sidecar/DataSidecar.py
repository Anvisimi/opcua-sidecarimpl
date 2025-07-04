#!/usr/bin/env python3
"""
Git-Enhanced Data Sidecar Container
- Clones H5 data from git repository (much faster than kubectl cp)
- Filters M01, M02 data excluding specified operations
- Automatic data loading from remote git repository
"""

import os
import shutil
import time
import logging
import subprocess
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GitDataSidecar:
    def __init__(self, shared_data_path: str = "/shared-data", git_repo_url: str = None):
        self.shared_data_path = shared_data_path
        self.git_repo_url = git_repo_url or os.getenv("DATA_GIT_REPO_URL")
        self.git_clone_path = "/home/sidecar/git-data-repo"
        
        # Configuration based on TechSpikeDataPipeline.md requirements
        self.included_machines = ["M01", "M02"]  # Exclude M03
        self.excluded_operations = ["OP00", "OP06", "OP09", "OP13"]
        
        # Ensure shared directory exists
        os.makedirs(shared_data_path, exist_ok=True)
        
    def check_existing_data(self) -> bool:
        """Check if data already exists in shared volume"""
        try:
            # Check if we have machine directories with H5 files
            for machine in self.included_machines:
                machine_path = os.path.join(self.shared_data_path, machine)
                if os.path.exists(machine_path):
                    # Look for any .h5 files
                    for root, dirs, files in os.walk(machine_path):
                        if any(f.endswith('.h5') for f in files):
                            logger.info(f"Found existing data in {machine_path}")
                            return True
            
            logger.info("No existing data found in shared volume")
            return False
        except Exception as e:
            logger.error(f"Error checking existing data: {e}")
            return False
    
    def clone_data_repository(self) -> bool:
        """Clone data from git repository"""
        if not self.git_repo_url:
            logger.error("No git repository URL provided. Set DATA_GIT_REPO_URL environment variable.")
            return False
            
        logger.info(f"Cloning data from git repository: {self.git_repo_url}")
        
        try:
            # Remove existing clone if present
            if os.path.exists(self.git_clone_path):
                shutil.rmtree(self.git_clone_path)
            
            # Clone the repository
            result = subprocess.run([
                "git", "clone", "--depth", "1", self.git_repo_url, self.git_clone_path
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                return False
                
            logger.info(f"Successfully cloned data repository to {self.git_clone_path}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Git clone timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Error cloning repository: {e}")
            return False
    
    def copy_data_from_git(self) -> int:
        """Copy filtered data from git clone to shared volume"""
        try:
            # First clone the repository
            if not self.clone_data_repository():
                logger.error("Failed to clone git repository")
                return 0
            
            logger.info(f"Copying filtered data from git clone to shared volume...")
            
            total_files = 0
            
            for machine in self.included_machines:
                source_machine_path = os.path.join(self.git_clone_path, "data", machine)
                target_machine_path = os.path.join(self.shared_data_path, machine)
                
                if not os.path.exists(source_machine_path):
                    logger.warning(f"Source machine directory not found in git repo: {source_machine_path}")
                    continue
                    
                logger.info(f"Processing {machine} from git repository...")
                
                # Get operation directories, excluding specified ones
                try:
                    operations = [d for d in os.listdir(source_machine_path) 
                                 if d.startswith("OP") and d not in self.excluded_operations and 
                                 os.path.isdir(os.path.join(source_machine_path, d))]
                    logger.info(f"Found operations for {machine}: {operations}")
                except Exception as e:
                    logger.error(f"Error reading machine directory {source_machine_path}: {e}")
                    continue
                    
                for operation in operations:
                    source_op_path = os.path.join(source_machine_path, operation)
                    target_op_path = os.path.join(target_machine_path, operation)
                    
                    # Copy good and bad directories
                    for quality in ["good", "bad"]:
                        source_quality_path = os.path.join(source_op_path, quality)
                        target_quality_path = os.path.join(target_op_path, quality)
                        
                        if os.path.exists(source_quality_path):
                            os.makedirs(target_quality_path, exist_ok=True)
                            
                            # Copy all H5 files
                            try:
                                h5_files = [f for f in os.listdir(source_quality_path) if f.endswith('.h5')]
                                for h5_file in h5_files:
                                    source_file = os.path.join(source_quality_path, h5_file)
                                    target_file = os.path.join(target_quality_path, h5_file)
                                    
                                    try:
                                        shutil.copy2(source_file, target_file)
                                        total_files += 1
                                    except Exception as e:
                                        logger.error(f"Failed to copy {source_file}: {e}")
                                
                                if h5_files:
                                    logger.info(f"Copied {len(h5_files)} files from {machine}/{operation}/{quality}")
                            except Exception as e:
                                logger.error(f"Error processing quality directory {source_quality_path}: {e}")
                        else:
                            logger.debug(f"Quality directory does not exist: {source_quality_path}")
                            
            logger.info(f"Git data copy complete - total files copied: {total_files}")
            
            # Clean up git clone to save space
            self.cleanup_git_clone()
            
            return total_files

        except Exception as e:
            logger.error(f"Error during git data loading: {e}")
            return 0
    
    def cleanup_git_clone(self):
        """Clean up git clone to save space"""
        try:
            if os.path.exists(self.git_clone_path):
                shutil.rmtree(self.git_clone_path)
                logger.info("Cleaned up git clone directory")
        except Exception as e:
            logger.warning(f"Error cleaning up git clone: {e}")
        
    def count_files_in_shared(self) -> int:
        """Count total files in shared volume for reporting"""
        total_files = 0
        
        for machine in self.included_machines:
            machine_path = os.path.join(self.shared_data_path, machine)
            if os.path.exists(machine_path):
                for root, dirs, files in os.walk(machine_path):
                    total_files += len([f for f in files if f.endswith('.h5')])
        
        return total_files

    def signal_ready(self):
        """Create ready file to signal completion to main container"""
        try:
            ready_file = os.path.join(self.shared_data_path, '.ready')
            with open(ready_file, 'w') as f:
                f.write(f"Ready at {time.time()}\n")
            logger.info("Created .ready file to signal completion to main container")
        except Exception as e:
            logger.error(f"Error creating ready file: {e}")

    def run(self):
        """Main execution flow"""
        logger.info("Starting Git-Enhanced Data Sidecar")
        logger.info(f"Git repository URL: {self.git_repo_url}")
        logger.info(f"Shared data path: {self.shared_data_path}")
        
        # Check if data already exists
        if self.check_existing_data():
            logger.info("Data already exists in shared volume, skipping git clone")
            total_files = self.count_files_in_shared()
            logger.info(f"Found {total_files} existing files")
        else:
            logger.info("No existing data found in shared volume")
            logger.info("Loading data from git repository...")
            total_files = self.copy_data_from_git()
            
            if total_files > 0:
                logger.info(f"Successfully loaded {total_files} files from git repository")
            else:
                logger.error("Failed to load data from git repository")
                return

        # Signal completion to main container
        self.signal_ready()
        
        logger.info("Data setup complete! {} files ready in shared volume".format(total_files))
        logger.info("Main container can now discover and stream files directly")
        
        # Start monitoring loop
        logger.info("Starting monitoring loop...")
        self.monitor_loop()

    def monitor_loop(self):
        """Enhanced monitoring loop with periodic health checks"""
        while True:
            try:
                current_files = self.count_files_in_shared()
                logger.info(f"Health check: {current_files} files available in shared volume")
                
                # Check if source data has changed (could re-clone periodically)
                # This could trigger re-sync if needed
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error during health check: {e}")
                time.sleep(60)  # Wait 1 minute before retrying


def main():
    """Main sidecar function"""
    sidecar = GitDataSidecar()
    
    # Run setup and monitoring
    sidecar.run()


if __name__ == "__main__":
    main() 