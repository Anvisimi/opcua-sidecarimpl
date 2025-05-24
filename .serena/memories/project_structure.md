# Project Structure

## File Organization
```
opcua-server/
├── server.py              # Main OPC UA server implementation
├── sensor_data.csv         # Sensor data source file
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker container configuration
├── docker-compose.yml     # Docker Compose orchestration
└── README.md              # Project documentation
```

## Code Structure
- **server.py**: Single file containing all functionality
  - `main()`: Server setup, initialization, and startup
  - `publish_sensor()`: Continuous data publishing loop
  - Uses asyncio for asynchronous operations
  - CSV data loaded at startup and cycled through

## Data Structure
- **sensor_data.csv**: Contains timestamped sensor readings
  - Columns: Timestamp, Machine_ID, Temperature_C, Vibration_mm_s, Pressure_bar
  - Multiple machines with multiple timestamps
  - Date format: DD/MM/YY H:MM

## OPC UA Node Structure
- Root: Objects/Sensors
- Timestamp_Sensor: Global timestamp variable
- Per machine: Machine_ID object containing three variables
  - Temperature_C
  - Vibration_mm_s  
  - Pressure_bar