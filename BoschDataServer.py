import asyncio
from asyncua import Server
import h5py
import time

# Load HDF5 file
h5_file_path = "M01_Aug_2019_OP00_000.h5"
h5_file = h5py.File(h5_file_path, 'r')

# Global variables for streaming
current_sample_index = 0
vibration_data = None
vibration_vars = []


async def setup_vibration_streaming(parent_node, idx):
    """Setup OPC UA variables for streaming vibration data"""
    global vibration_data, vibration_vars

    # Get vibration data from HDF5 file
    vibration_data = h5_file['vibration_data']
    print(f"Loaded vibration data with shape: {vibration_data.shape}")

    # Create OPC UA variables for each vibration channel
    vibration_vars = []

    # Create a vibration group
    vib_group = await parent_node.add_object(idx, "VibrationStreaming")

    # Add metadata variables
    total_samples_var = await vib_group.add_variable(idx, "TotalSamples", vibration_data.shape[0])
    await total_samples_var.set_writable(False)

    current_index_var = await vib_group.add_variable(idx, "CurrentSampleIndex", 0)
    await current_index_var.set_writable(False)

    timestamp_var = await vib_group.add_variable(idx, "Timestamp", time.time())
    await timestamp_var.set_writable(False)

    # Add individual channel variables
    channel_names = ["VibrationX", "VibrationY", "VibrationZ"]
    for i, channel_name in enumerate(channel_names):
        var = await vib_group.add_variable(idx, channel_name, float(vibration_data[0, i]))
        await var.set_writable(False)
        vibration_vars.append(var)

    # Add a combined array variable for all 3 channels
    combined_var = await vib_group.add_variable(idx, "VibrationXYZ", [float(x) for x in vibration_data[0, :]])
    await combined_var.set_writable(False)
    vibration_vars.append(combined_var)

    # Add index and timestamp to the vars list for updating
    vibration_vars.extend([current_index_var, timestamp_var])

    return vib_group


async def update_vibration_data():
    """Update vibration data variables with next sample"""
    global current_sample_index, vibration_data, vibration_vars

    if vibration_data is None or len(vibration_vars) == 0:
        return

    # Get current sample
    current_sample = vibration_data[current_sample_index, :]
    current_time = time.time()

    # Update individual channel variables (first 3 variables)
    for i in range(3):
        await vibration_vars[i].write_value(float(current_sample[i]))

    # Update combined array variable (4th variable)
    await vibration_vars[3].write_value([float(x) for x in current_sample])

    # Update metadata variables (5th and 6th variables)
    await vibration_vars[4].write_value(current_sample_index)  # Current index
    await vibration_vars[5].write_value(current_time)  # Timestamp

    # Print progress every 10 seconds
    if current_sample_index % 10 == 0:
        print(
            f"Streaming sample {current_sample_index}/{vibration_data.shape[0]}: X={current_sample[0]:.2f}, Y={current_sample[1]:.2f}, Z={current_sample[2]:.2f}")

    # Move to next sample (loop back to start when finished)
    current_sample_index = (current_sample_index + 1) % vibration_data.shape[0]

    if current_sample_index == 0:
        print("Completed one full cycle of vibration data, restarting from beginning...")


async def streaming_task():
    """Background task to update vibration data every second"""
    while True:
        try:
            await update_vibration_data()
            await asyncio.sleep(1.0)  # Wait 1 second between updates
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

    # Setup vibration streaming
    await setup_vibration_streaming(bosch_node, idx)

    async with server:
        print("Bosch Vibration Streaming Server is running...")
        print(f"Endpoint: opc.tcp://0.0.0.0:4840/")
        print(f"Total vibration samples: {vibration_data.shape[0]}")
        print("Starting vibration data streaming (1 sample per second)...")

        # Start the streaming task
        streaming_task_handle = asyncio.create_task(streaming_task())

        try:
            await streaming_task_handle
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