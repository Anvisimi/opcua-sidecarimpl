# Project Purpose

This project implements an OPC UA (Open Platform Communications Unified Architecture) server that simulates industrial IoT sensor data. 

Key functionalities:
- Reads sensor measurements (temperature, vibration, pressure) for multiple machines from a CSV file
- Exposes each sensor as an OPC UA variable through standardized industrial protocol
- Updates sensor values at regular intervals (2 seconds) to simulate real-time data
- Supports multiple machines (Machine_1 to Machine_N) with three sensor types each
- Containerized for easy deployment using Docker

The server runs on port 4840 and provides endpoint: opc.tcp://0.0.0.0:4840/freeopcua/server/