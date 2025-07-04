#!/usr/bin/env python3
"""
Simplified Data Sidecar Container
- Copies real data from source to persistent shared volume
- Filters M01, M02 data excluding specified operations
- No manifest needed - main container discovers files directly
"""

import os
import shutil
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimplifiedDataSidecar:
    def __init__(self, shared_data_path: str = "/shared-data"):
        self.shared_data_path = shared_data_path
        
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
    
    def wait_for_source_data(self, timeout: int = 600) -> bool:
        """Wait for real data to be copied to a source location"""
        logger.info("Waiting for real data to be provided...")
        logger.info("Please copy your data using: kubectl cp data/ <pod-name>:/tmp/source-data/ -c data-sidecar")
        
        source_path = "/tmp/source-data"
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if os.path.exists(source_path):
                # Check if we have M01 and M02 directories with H5 files
                for machine in self.included_machines:
                    machine_path = os.path.join(source_path, machine)
                    if os.path.exists(machine_path):
                        # Look for H5 files
                        for root, dirs, files in os.walk(machine_path):
                            if any(f.endswith('.h5') for f in files):
                                logger.info(f"Found source data for {machine}")
                                return True
            
            logger.info(f"Waiting for source data... ({int(time.time() - start_time)}s)")
            time.sleep(10)
            
        logger.warning(f"Timeout waiting for source data after {timeout}s")
        return False
    
    def copy_real_data_to_shared(self, source_path: str = "/tmp/source-data"):
        """Copy real data from source to shared volume with filtering"""
        logger.info("Copying real data to shared volume...")
        
        total_files = 0
        
        for machine in self.included_machines:
            source_machine_path = os.path.join(source_path, machine)
            target_machine_path = os.path.join(self.shared_data_path, machine)
            
            if not os.path.exists(source_machine_path):
                logger.warning(f"Source machine directory not found: {source_machine_path}")
                continue
                
            logger.info(f"Processing {machine}...")
            
            # Get operation directories, excluding specified ones
            try:
                operations = [d for d in os.listdir(source_machine_path) 
                             if d.startswith("OP") and d not in self.excluded_operations and 
                             os.path.isdir(os.path.join(source_machine_path, d))]
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
                        h5_files = [f for f in os.listdir(source_quality_path) if f.endswith('.h5')]
                        for h5_file in h5_files:
                            source_file = os.path.join(source_quality_path, h5_file)
                            target_file = os.path.join(target_quality_path, h5_file)
                            
                            try:
                                shutil.copy2(source_file, target_file)
                                total_files += 1
                            except Exception as e:
                                logger.error(f"Failed to copy {source_file}: {e}")
                        
                        logger.info(f"Copied {len(h5_files)} files from {machine}/{operation}/{quality}")
                        
        logger.info(f"Real data copy complete - total files: {total_files}")
        
    def count_files_in_shared(self) -> int:
        """Count total files in shared volume for reporting"""
        total_files = 0
        
        for machine in self.included_machines:
            machine_path = os.path.join(self.shared_data_path, machine)
            if os.path.exists(machine_path):
                for root, dirs, files in os.walk(machine_path):
                    total_files += len([f for f in files if f.endswith('.h5')])
        
        return total_files

    def run_setup_and_monitor(self):
        """Run setup and then monitor for health"""
        logger.info("Starting Simplified Data Sidecar")
        
        # Check if data already exists
        has_existing_data = self.check_existing_data()
        
        if not has_existing_data:
            # Wait for real data to be provided
            if self.wait_for_source_data():
                # Copy the real data to shared volume
                self.copy_real_data_to_shared()
            else:
                logger.error("No source data provided - cannot proceed without real data")
                return
        
        # Report current status
        total_files = self.count_files_in_shared()
        logger.info(f"Data setup complete! {total_files} files ready in shared volume")
        logger.info("Main container can now discover and stream files directly")
        
        # Simple monitoring loop - just stay alive and report status
        while True:
            try:
                current_files = self.count_files_in_shared()
                logger.info(f"Health check: {current_files} files available in shared volume")
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error during health check: {e}")
                time.sleep(60)  # Wait 1 minute before retrying


def main():
    """Main sidecar function"""
    sidecar = SimplifiedDataSidecar()
    
    # Run setup and monitoring
    sidecar.run_setup_and_monitor()


if __name__ == "__main__":
    main() 