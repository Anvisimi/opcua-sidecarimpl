import asyncio
from asyncua import Server
import h5py

# Load HDF5 file
h5_file_path = "M01_Aug_2019_OP00_000.h5"
h5_file = h5py.File(h5_file_path, 'r')

# Recursively expose HDF5 structure
async def expose_h5_group(h5group, parent_node, idx):
    for name, item in h5group.items():
        if isinstance(item, h5py.Group):
            sub_node = await parent_node.add_object(idx, name)
            await expose_h5_group(item, sub_node, idx)
        elif isinstance(item, h5py.Dataset):
            try:
                data = item[()]
                value = data.tolist() if hasattr(data, 'tolist') else data
                if isinstance(value, list):
                    value = value[0] if value else 0
                var = await parent_node.add_variable(idx, name, value)
                await var.set_writable()
            except Exception as e:
                print(f"Failed to expose {name}: {e}")

async def main():
    server = Server()
    await server.init()  # Required in asyncua ≥ 1.0.0
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("HDF5 OPC UA AsyncUA Server")

    uri = "http://examples.asyncua.hdf5"
    idx = server.register_namespace(uri)

    objects = server.nodes.objects
    hdf5_node = await objects.add_object(idx, "HDF5Data")

    await expose_h5_group(h5_file, hdf5_node, idx)

    async with server:
        print("OPC UA server running with asyncua ≥ 1.0.0...")
        while True:
            await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    h5_file.close()