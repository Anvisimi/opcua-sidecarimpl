import asyncio
from asyncua import Server
from asyncua.ua import VariantType
import pandas as pd
from datetime import datetime

async def publish_sensor(server, idx, df_sensor):
    objects = server.get_objects_node()
    sensor_node = await objects.get_child([f"{idx}:Sensors"])
    ts_sensor = await sensor_node.get_child([f"{idx}:Timestamp_Sensor"])
    sensors = {}
    for m in df_sensor['Machine_ID'].unique():
        obj = await sensor_node.get_child([f"{idx}:{m}"])
        sensors[m] = {
            'Temperature_C': await obj.get_child([f"{idx}:Temperature_C"]),
            'Vibration_mm_s': await obj.get_child([f"{idx}:Vibration_mm_s"]),
            'Pressure_bar': await obj.get_child([f"{idx}:Pressure_bar"]),
        }

    # Loop indefinitely over sensor data
    timestamps = sorted(df_sensor['Timestamp'].unique())
    while True:
        for ts in timestamps:
            await ts_sensor.write_value(ts.to_pydatetime(), VariantType.DateTime)
            batch = df_sensor[df_sensor['Timestamp'] == ts]
            for _, row in batch.iterrows():
                m = row['Machine_ID']
                await sensors[m]['Temperature_C'].write_value(float(row['Temperature_C']))
                await sensors[m]['Vibration_mm_s'].write_value(float(row['Vibration_mm_s']))
                await sensors[m]['Pressure_bar'].write_value(float(row['Pressure_bar']))
            print(f"{datetime.now().isoformat()} – Sensor published {len(batch)} records @ {ts}")
            await asyncio.sleep(2)

async def main():
    # Load sensor CSV
    df_sensor = pd.read_csv('sensor_data.csv', parse_dates=['Timestamp'])
    df_sensor['Machine_ID'] = df_sensor['Machine_ID'].astype(str)

    # OPC UA server setup
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    idx = await server.register_namespace("iot_sensors")
    objects = server.get_objects_node()

    # Create root node and timestamp variable
    sensor_node = await objects.add_object(idx, "Sensors")
    ts_sensor = await sensor_node.add_variable(
        idx, "Timestamp_Sensor", df_sensor['Timestamp'].iloc[0].to_pydatetime()
    )
    await ts_sensor.set_writable()

    # Create machine variables
    for m in df_sensor['Machine_ID'].unique():
        obj = await sensor_node.add_object(idx, m)
        for meas in ['Temperature_C', 'Vibration_mm_s', 'Pressure_bar']:
            var = await obj.add_variable(idx, meas, 0.0)
            await var.set_writable()

    # Start server and publishing
    await server.start()
    print(f"Server started at {server.endpoint}")

    try:
        await publish_sensor(server, idx, df_sensor)
    except Exception as e:
        print("Error:", e)
    finally:
        await server.stop()
        print("Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
