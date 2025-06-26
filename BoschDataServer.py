import asyncio
import time

import h5py
import numpy as np
from asyncua import Server

# Load HDF5 file
h5_file_path = "M01_Aug_2019_OP00_000.h5"
h5_file = h5py.File(h5_file_path, 'r')

# Global state
current_sample_index = 0
vibration_data = None
vibration_vars = {}  # dict to hold our OPC UA variables

BATCH_SIZE = 10  # number of samples per update


async def setup_vibration_streaming(parent_node, idx):
    """Setup OPC UA variables for streaming batched vibration data"""
    global vibration_data, vibration_vars

    vibration_data = h5_file['vibration_data']
    print(f"Loaded vibration data with shape: {vibration_data.shape}")

    vib_group = await parent_node.add_object(idx, "VibrationStreaming")

    # Metadata
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

    # Initial batch slice
    init_batch = vibration_data[0:BATCH_SIZE, :]  # shape (10,3)
    # 2D array
    vibration_vars['VibrationBatch'] = await vib_group.add_variable(
        idx,
        "VibrationBatch",
        [[float(x) for x in row] for row in init_batch]
    )
    await vibration_vars['VibrationBatch'].set_writable(False)

    # 1D arrays per axis
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
    global current_sample_index, vibration_data, vibration_vars

    if vibration_data is None or not vibration_vars:
        return

    total = vibration_data.shape[0]
    start = current_sample_index
    end = start + BATCH_SIZE

    # slice with wrap-around
    if end <= total:
        batch = vibration_data[start:end, :]
    else:
        wrap = end % total
        batch = np.vstack((vibration_data[start:, :], vibration_data[:wrap, :]))

    # prepare lists
    batch_2d = [[float(x) for x in row] for row in batch]
    x1d = [float(x) for x in batch[:, 0]]
    y1d = [float(x) for x in batch[:, 1]]
    z1d = [float(x) for x in batch[:, 2]]

    # write to OPC UA
    await vibration_vars['VibrationBatch'].write_value(batch_2d)
    await vibration_vars['VibrationXBatch'].write_value(x1d)
    await vibration_vars['VibrationYBatch'].write_value(y1d)
    await vibration_vars['VibrationZBatch'].write_value(z1d)

    # metadata
    await vibration_vars['CurrentSampleIndex'].write_value(current_sample_index)
    await vibration_vars['Timestamp'].write_value(time.time())

    print(f"Streaming batch starting at sample {current_sample_index}")

    current_sample_index = (current_sample_index + BATCH_SIZE) % total
    if current_sample_index == 0:
        print("Completed one full cycle of vibration data, restarting...")


async def streaming_task():
    """Background task to update vibration data every second"""
    while True:
        try:
            await update_vibration_data()
            await asyncio.sleep(1.0)
        except Exception as e:
            print(f"Error updating vibration data: {e}")
            await asyncio.sleep(1.0)


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("Bosch Vibration Data Streaming Server")

    uri = "http://bosch.vibration.streaming"
    idx = await server.register_namespace(uri)

    objects = server.nodes.objects
    bosch_node = await objects.add_object(idx, "BoschVibrationData")

    # Setup streaming nodes
    await setup_vibration_streaming(bosch_node, idx)

    async with server:
        print("Server running at opc.tcp://0.0.0.0:4840/")
        print(f"Total samples: {vibration_data.shape[0]}")
        print(f"Publishing {BATCH_SIZE}-sample batches every second...")
        task = asyncio.create_task(streaming_task())
        try:
            await task
        except asyncio.CancelledError:
            print("Streaming task cancelled")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        if h5_file:
            h5_file.close()
            print("HDF5 file closed")
