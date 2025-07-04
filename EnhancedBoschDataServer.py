import asyncio
import time
import os
import logging
import glob
from typing import Dict, List, Optional

import h5py
import numpy as np
from asyncua import Server

# Enhanced global state
current_file_index = 0
current_sample_index = 0
vibration_data = None
vibration_vars = {}  # dict to hold our OPC UA variables
active_files = []

BATCH_SIZE = 10  # number of samples per update
SHARED_DATA_PATH = "/shared-data"
SIDECAR_READY_FILE = "/shared-data/.ready"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_sidecar_ready(timeout_seconds=300):
    """Wait for sidecar to signal completion by creating .ready file"""
    logger.info(f"Waiting for sidecar to complete data loading (timeout: {timeout_seconds}s)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if os.path.exists(SIDECAR_READY_FILE):
            logger.info("Sidecar has completed data loading!")
            return True
        
        # Log progress every 30 seconds
        elapsed = time.time() - start_time
        if elapsed > 0 and int(elapsed) % 30 == 0:
            logger.info(f"Still waiting for sidecar... ({elapsed:.0f}s elapsed)")
        
        time.sleep(5)  # Check every 5 seconds
    
    logger.error(f"Timeout waiting for sidecar to complete after {timeout_seconds}s")
    return False


def discover_files_from_shared_data() -> List[Dict]:
    """Discover HDF5 files directly from shared data directory with filtering"""
    file_list = []
    
    # Wait for sidecar to complete data loading
    if not wait_for_sidecar_ready():
        logger.error("Sidecar did not complete data loading within timeout")
        return file_list
    
    # Target machines (M01, M02, exclude M03)
    target_machines = ['M01', 'M02']
    # Operations to exclude
    excluded_operations = ['OP00', 'OP06', 'OP09', 'OP13']
    
    logger.info(f"Discovering files from {SHARED_DATA_PATH}")
    
    if not os.path.exists(SHARED_DATA_PATH):
        logger.error(f"Shared data path does not exist: {SHARED_DATA_PATH}")
        return file_list
    
    # Search for HDF5 files in the shared data directory
    pattern = os.path.join(SHARED_DATA_PATH, "**", "*.h5")
    h5_files = glob.glob(pattern, recursive=True)
    
    if not h5_files:
        logger.warning(f"No HDF5 files found in {SHARED_DATA_PATH}")
        return file_list
    
    logger.info(f"Found {len(h5_files)} HDF5 files")
    
    # Group files by machine and operation for sequential processing
    machine_operations = {}
    
    for h5_file_path in h5_files:
        try:
            # Parse filename to extract machine, operation, and quality
            filename = os.path.basename(h5_file_path)
            
            # Expected format: M01_Aug_2019_OP01_000.h5
            parts = filename.replace('.h5', '').split('_')
            if len(parts) < 4:
                logger.warning(f"Skipping file with unexpected format: {filename}")
                continue
                
            machine = parts[0]  # M01, M02, etc.
            operation = parts[3]  # OP01, OP02, etc.
            
            # Apply filtering
            if machine not in target_machines:
                logger.debug(f"Skipping excluded machine {machine}: {filename}")
                continue
                
            if operation in excluded_operations:
                logger.debug(f"Skipping excluded operation {operation}: {filename}")
                continue
            
            # Determine quality based on directory structure
            quality = 'unknown'
            if '/good/' in h5_file_path:
                quality = 'good'
            elif '/bad/' in h5_file_path:
                quality = 'bad'
            
            # Initialize nested structure
            if machine not in machine_operations:
                machine_operations[machine] = {}
            if operation not in machine_operations[machine]:
                machine_operations[machine][operation] = {'good': [], 'bad': []}
            
            # Add file info
            file_info = {
                'path': h5_file_path,
                'machine': machine,
                'operation': operation,
                'quality': quality,
                'filename': filename,
                'size': os.path.getsize(h5_file_path) if os.path.exists(h5_file_path) else 0
            }
            
            if quality in ['good', 'bad']:
                machine_operations[machine][operation][quality].append(file_info)
            else:
                # Default to good if quality can't be determined
                machine_operations[machine][operation]['good'].append(file_info)
                
        except Exception as e:
            logger.warning(f"Error processing file {h5_file_path}: {e}")
            continue
    
    # Sort files within each group for proper sequential ordering
    def sort_key(file_info):
        """Sort key function for proper file ordering"""
        filename = file_info['filename']
        try:
            # Extract date and sequence number for sorting
            # Format: M01_Aug_2019_OP01_000.h5 -> ['M01', 'Aug', '2019', 'OP01', '000']
            parts = filename.replace('.h5', '').split('_')
            if len(parts) >= 5:
                # Sort by: machine, date_year, operation, sequence_number
                machine = parts[0]
                date_month = parts[1]  # Aug, Feb, etc.
                date_year = parts[2]   # 2019, 2020, 2021
                operation = parts[3]   # OP01, OP02, etc.
                sequence = int(parts[4])  # 000, 001, 002, etc.
                
                # Create sortable tuple: (machine, year, month_priority, operation, sequence)
                month_priority = {'Feb': 1, 'Aug': 2}.get(date_month, 3)  # Feb before Aug
                
                return (machine, int(date_year), month_priority, operation, sequence)
            else:
                # Fallback to filename sorting if format is unexpected
                return (filename,)
        except (ValueError, IndexError):
            # Fallback to filename sorting if parsing fails
            logger.warning(f"Could not parse filename for sorting: {filename}, using filename sort")
            return (filename,)
    
    # Convert to sequential list with proper sorting
    for machine in sorted(machine_operations.keys()):
        for operation in sorted(machine_operations[machine].keys()):
            # Sort good files for this operation
            good_files = machine_operations[machine][operation]['good']
            good_files.sort(key=sort_key)
            file_list.extend(good_files)
            
            # Sort bad files for this operation  
            bad_files = machine_operations[machine][operation]['bad']
            bad_files.sort(key=sort_key)
            file_list.extend(bad_files)
    
    logger.info(f"Discovered {len(file_list)} files after filtering and sorting")
    if file_list:
        # Log summary
        machines = list(set(f['machine'] for f in file_list))
        operations = list(set(f['operation'] for f in file_list))
        good_count = len([f for f in file_list if f['quality'] == 'good'])
        bad_count = len([f for f in file_list if f['quality'] == 'bad'])
        
        logger.info(f"Files by machine: {machines}")
        logger.info(f"Files by operation: {operations}")
        logger.info(f"Files by quality - Good: {good_count}, Bad: {bad_count}")
        
        # Log first few files to verify sorting
        logger.info("First 10 files in sequence:")
        for i, file_info in enumerate(file_list[:10]):
            logger.info(f"  {i+1:2d}. {file_info['machine']}_{file_info['operation']} "
                       f"({file_info['quality']}) - {file_info['filename']}")
    
    return file_list


def load_current_file():
    """Load current HDF5 file based on index"""
    global vibration_data, current_file_index, active_files
    
    if not active_files or current_file_index >= len(active_files):
        logger.error("No files available or invalid file index")
        return False
        
    current_file = active_files[current_file_index]
    h5_file_path = current_file['path']
    
    try:
        # Close previous file if any
        if 'h5_file' in globals() and globals()['h5_file']:
            globals()['h5_file'].close()
            
        # Load new file
        globals()['h5_file'] = h5py.File(h5_file_path, 'r')
        vibration_data = globals()['h5_file']['vibration_data']
        
        logger.info(f"Loaded file {current_file_index + 1}/{len(active_files)}: "
                   f"{current_file['machine']}_{current_file['operation']} "
                   f"({current_file['quality']}) - {vibration_data.shape[0]} samples")
        return True
        
    except Exception as e:
        logger.error(f"Error loading file {h5_file_path}: {e}")
        return False


async def setup_vibration_streaming(parent_node, idx):
    """Setup OPC UA variables for streaming batched vibration data"""
    global vibration_data, vibration_vars, active_files

    # Discover files directly from shared data
    active_files = discover_files_from_shared_data()
    if not active_files:
        logger.error("No files found in shared data directory")
        return None
        
    # Load first file
    if not load_current_file():
        logger.error("Failed to load initial file")
        return None

    vib_group = await parent_node.add_object(idx, "VibrationStreaming")

    # Enhanced metadata
    vibration_vars['TotalFiles'] = await vib_group.add_variable(
        idx, "TotalFiles", len(active_files)
    )
    await vibration_vars['TotalFiles'].set_writable(False)

    vibration_vars['CurrentFileIndex'] = await vib_group.add_variable(
        idx, "CurrentFileIndex", current_file_index
    )
    await vibration_vars['CurrentFileIndex'].set_writable(False)

    current_file = active_files[current_file_index]
    vibration_vars['CurrentFileName'] = await vib_group.add_variable(
        idx, "CurrentFileName", current_file['filename']
    )
    await vibration_vars['CurrentFileName'].set_writable(False)

    vibration_vars['CurrentMachine'] = await vib_group.add_variable(
        idx, "CurrentMachine", current_file['machine']
    )
    await vibration_vars['CurrentMachine'].set_writable(False)

    vibration_vars['CurrentOperation'] = await vib_group.add_variable(
        idx, "CurrentOperation", current_file['operation']
    )
    await vibration_vars['CurrentOperation'].set_writable(False)

    vibration_vars['CurrentQuality'] = await vib_group.add_variable(
        idx, "CurrentQuality", current_file['quality']
    )
    await vibration_vars['CurrentQuality'].set_writable(False)

    # Original metadata (kept for compatibility)
    total_samples = vibration_data.shape[0]
    vibration_vars['TotalSamples'] = await vib_group.add_variable(
        idx, "TotalSamples", total_samples
    )
    await vibration_vars['TotalSamples'].set_writable(False)

    vibration_vars['CurrentSampleIndex'] = await vib_group.add_variable(
        idx, "CurrentSampleIndex", 0
    )
    await vibration_vars['CurrentSampleIndex'].set_writable(False)

    vibration_vars['Timestamp'] = await vib_group.add_variable(
        idx, "Timestamp", time.time()
    )
    await vibration_vars['Timestamp'].set_writable(False)

    init_batch = vibration_data[0 : BATCH_SIZE, :]

    # Original vibration variables (kept for compatibility)
    axes = ['X', 'Y', 'Z']
    for i, ax in enumerate(axes):
        vibration_vars[f'Vibration{ax}Batch'] = await vib_group.add_variable(
            idx,
            f"Vibration{ax}Batch",
            [float(x) for x in init_batch[:, i]]
        )
        await vibration_vars[f'Vibration{ax}Batch'].set_writable(False)

    return vib_group


async def update_vibration_data():
    """Update vibration data variables with next batch"""
    global current_sample_index, current_file_index, vibration_data, vibration_vars, active_files

    if vibration_data is None or not vibration_vars or not active_files:
        return

    total = vibration_data.shape[0]
    start = current_sample_index
    end = start + BATCH_SIZE

    # Check if we need to move to next file
    if start >= total:
        # Current file is done, move to next file
        logger.info(f"Completed file {current_file_index + 1}/{len(active_files)}, moving to next file...")
        
        current_file_index = (current_file_index + 1) % len(active_files)
        
        if current_file_index == 0:
            logger.info("Completed all files, restarting from first file...")
            
        # Load next file
        if load_current_file():
            current_sample_index = 0
            total = vibration_data.shape[0]
            start = 0
            end = BATCH_SIZE
            
            # Update file metadata
            current_file = active_files[current_file_index]
            await vibration_vars['CurrentFileIndex'].write_value(current_file_index)
            await vibration_vars['CurrentFileName'].write_value(current_file['filename'])
            await vibration_vars['CurrentMachine'].write_value(current_file['machine'])
            await vibration_vars['CurrentOperation'].write_value(current_file['operation'])
            await vibration_vars['CurrentQuality'].write_value(current_file['quality'])
            await vibration_vars['TotalSamples'].write_value(vibration_data.shape[0])
        else:
            # Failed to load next file, return without processing
            return

    # Read the batch (simple slice, no wrap-around needed)
    end = min(end, total)  # Don't go past end of file
    batch = vibration_data[start:end, :]

    # prepare lists
    x1d = [float(x) for x in batch[:, 0]]
    y1d = [float(x) for x in batch[:, 1]]
    z1d = [float(x) for x in batch[:, 2]]

    # write to OPC UA
    await vibration_vars['VibrationXBatch'].write_value(x1d)
    await vibration_vars['VibrationYBatch'].write_value(y1d)
    await vibration_vars['VibrationZBatch'].write_value(z1d)

    # metadata
    await vibration_vars['CurrentSampleIndex'].write_value(current_sample_index)
    await vibration_vars['Timestamp'].write_value(time.time())

    current_file = active_files[current_file_index]
    logger.info(f"Streaming records {start}-{end-1} from "
               f"{current_file['machine']}_{current_file['operation']} "
               f"({current_file['quality']}) - File {current_file_index + 1}/{len(active_files)}")

    # Move to next position
    current_sample_index += BATCH_SIZE


async def streaming_task():
    """Background task to update vibration data every 0.25 seconds (fast test mode)"""
    while True:
        try:
            await update_vibration_data()
            await asyncio.sleep(0.25)
        except Exception as e:
            logger.error(f"Error updating vibration data: {e}")
            await asyncio.sleep(0.25)


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("Enhanced Bosch Multi-File Vibration Data Streaming Server")

    uri = "http://bosch.vibration.streaming"
    idx = await server.register_namespace(uri)

    objects = server.nodes.objects
    bosch_node = await objects.add_object(idx, "BoschVibrationData")

    # Setup streaming nodes
    stream_group = await setup_vibration_streaming(bosch_node, idx)
    if not stream_group:
        logger.error("Failed to setup streaming, exiting...")
        return

    async with server:
        logger.info("Enhanced server running at opc.tcp://0.0.0.0:4840/")
        logger.info(f"Total files to stream: {len(active_files)}")
        logger.info(f"Publishing {BATCH_SIZE}-sample batches every 0.25 seconds (fast test mode)...")
        
        # Log summary
        machines = list(set(f['machine'] for f in active_files))
        operations = list(set(f['operation'] for f in active_files))
        good_count = len([f for f in active_files if f['quality'] == 'good'])
        bad_count = len([f for f in active_files if f['quality'] == 'bad'])
        
        logger.info(f"Streaming files from machines: {machines}")
        logger.info(f"Operations included: {operations}")
        logger.info(f"Files by quality - Good: {good_count}, Bad: {bad_count}")
        
        task = asyncio.create_task(streaming_task())
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Streaming task cancelled")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down enhanced server...")
    finally:
        if 'h5_file' in globals() and globals()['h5_file']:
            globals()['h5_file'].close()
            logger.info("HDF5 file closed") 