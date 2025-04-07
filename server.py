import asyncio
from asyncua import Server
from asyncua.ua import VariantType
import pandas as pd
from datetime import datetime


async def main():
    try:
        # Load CSV data and exclude timestamp column
        df = pd.read_csv('sensor_data.csv')
        sensor_columns = df.columns.tolist()[1:]  # Skip first column (Timestamp)

        # Initialize OPC UA server
        server = Server()
        await server.init()
        server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")

        # Setup namespace
        uri = "iot_sensors"
        idx = await server.register_namespace(uri)

        # Create object node
        objects = server.get_objects_node()
        sensor_node = await objects.add_object(idx, "Sensors")

        # Create variables using sensor names from CSV headers
        variables = {}
        for col in sensor_columns:
            var = await sensor_node.add_variable(idx, col, 0.0)
            await var.set_writable()
            variables[col] = var
            print(f"Created variable: {col}")

        await server.start()
        print(f"Server started at {server.endpoint}")

        current_row = 0
        total_rows = len(df)

        while True:
            row_data = df.iloc[current_row]
            for col in sensor_columns:
                await variables[col].write_value(row_data[col], VariantType.Double)

            print(f"{datetime.now().isoformat()} - Published row {current_row + 1}/{total_rows}")
            current_row = (current_row + 1) % total_rows
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await server.stop()
        print("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())