# Code Style and Conventions

## Python Conventions
- Uses async/await pattern throughout
- Snake_case for variable names (Temperature_C, Vibration_mm_s, Pressure_bar)
- String machine IDs (Machine_1, Machine_2, etc.)
- No type hints used in current implementation
- No docstrings in current implementation
- Simple print statements for logging
- Basic error handling with try/except

## Structure Patterns
- Single main.py file approach
- Async functions for all OPC UA operations
- CSV data loaded once at startup
- Infinite loop for continuous data publishing
- Pandas for data manipulation

## Naming Conventions
- Machine IDs: Machine_1, Machine_2, etc.
- Sensor measurements: Temperature_C, Vibration_mm_s, Pressure_bar
- OPC UA namespace: "iot_sensors"
- CSV file: sensor_data.csv