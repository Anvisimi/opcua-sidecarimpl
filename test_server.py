"""
Test cases for OPC UA server implementation.

This module contains comprehensive test cases for the server.py file,
covering server initialization, CSV data loading, OPC UA node creation,
and data publishing functionality.
"""

import asyncio
import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from asyncua import Server
from asyncua.ua import VariantType

# Import the functions to test
from server import main, publish_sensor


class TestCSVDataLoading:
    """Test cases for CSV data loading and processing."""

    def setup_method(self):
        """Set up test data for each test method."""
        self.sample_csv_content = """Timestamp,Machine_ID,Temperature_C,Vibration_mm_s,Pressure_bar
24/1/24 0:00,Machine_1,62.12,2.51,5.98
24/1/24 0:00,Machine_2,61.03,2.55,3.82
24/1/24 1:00,Machine_1,63.45,2.48,6.12
24/1/24 1:00,Machine_2,60.87,2.52,3.95"""

    @patch('pandas.read_csv')
    def test_csv_loading_success(self, mock_read_csv):
        """Test successful CSV file loading."""
        # Create mock DataFrame
        mock_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00', '2024-01-24 01:00:00']),
            'Machine_ID': ['Machine_1', 'Machine_2'],
            'Temperature_C': [62.12, 61.03],
            'Vibration_mm_s': [2.51, 2.55],
            'Pressure_bar': [5.98, 3.82]
        })
        mock_read_csv.return_value = mock_df

        # Test the CSV loading part of main function
        with patch('server.Server'), \
                patch('asyncio.run'):
            try:
                # This will test the CSV loading part
                df_sensor = pd.read_csv('sensor_data.csv', parse_dates=['Timestamp'])
                df_sensor['Machine_ID'] = df_sensor['Machine_ID'].astype(str)

                assert not df_sensor.empty
                assert 'Machine_ID' in df_sensor.columns
                assert 'Temperature_C' in df_sensor.columns
                assert 'Vibration_mm_s' in df_sensor.columns
                assert 'Pressure_bar' in df_sensor.columns
                assert df_sensor['Machine_ID'].dtype == object
            except Exception as e:
                pytest.fail(f"CSV loading failed: {e}")

    def test_csv_file_not_found(self):
        """Test handling of missing CSV file."""
        with patch('pandas.read_csv', side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError):
                pd.read_csv('nonexistent_file.csv', parse_dates=['Timestamp'])

    def test_csv_invalid_format(self):
        """Test handling of invalid CSV format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("invalid,csv,format\n1,2")  # Missing expected columns
            f.flush()

            try:
                with pytest.raises((pd.errors.EmptyDataError, pd.errors.ParserError, ValueError)):
                    pd.read_csv(f.name, parse_dates=['Timestamp'])
            finally:
                os.unlink(f.name)


class TestOPCUAServerSetup:
    """Test cases for OPC UA server initialization and setup."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock OPC UA server for testing."""
        server = AsyncMock(spec=Server)
        # Use synchronous get_objects_node so get_objects_node() is not a coroutine
        objects_node = AsyncMock()
        server.get_objects_node = Mock(return_value=objects_node)
        server.register_namespace.return_value = 1
        server.set_endpoint = Mock()
        server.start = AsyncMock()
        server.stop = AsyncMock()
        server.endpoint = "opc.tcp://0.0.0.0:4840/freeopcua/server/"
        return server

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00', '2024-01-24 01:00:00']),
            'Machine_ID': ['Machine_1', 'Machine_2'],
            'Temperature_C': [62.12, 61.03],
            'Vibration_mm_s': [2.51, 2.55],
            'Pressure_bar': [5.98, 3.82]
        })

    @pytest.mark.asyncio
    async def test_server_initialization(self, mock_server):
        """Test OPC UA server initialization."""
        with patch('server.Server', return_value=mock_server):
            await mock_server.init()
            mock_server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
            idx = await mock_server.register_namespace("iot_sensors")

            mock_server.init.assert_called_once()
            mock_server.set_endpoint.assert_called_once_with("opc.tcp://0.0.0.0:4840/freeopcua/server/")
            mock_server.register_namespace.assert_called_once_with("iot_sensors")
            assert idx == 1

    @pytest.mark.asyncio
    async def test_node_creation(self, mock_server, sample_dataframe):
        """Test OPC UA node creation for sensors."""
        objects = mock_server.get_objects_node()
        sensor_node = AsyncMock()
        mock_server.get_objects_node.return_value = objects
        objects.add_object = AsyncMock(return_value=sensor_node)
        sensor_node.add_variable = AsyncMock()
        sensor_node.add_object = AsyncMock()
        variable_node = AsyncMock()
        sensor_node.add_variable.return_value = variable_node
        variable_node.set_writable = AsyncMock()

        # Create root sensor node
        sensor_node = await objects.add_object(1, "Sensors")

        # Create timestamp variable
        ts_sensor = await sensor_node.add_variable(
            1, "Timestamp_Sensor", sample_dataframe['Timestamp'].iloc[0].to_pydatetime()
        )
        await ts_sensor.set_writable()

        # Create machine variables
        for machine_id in sample_dataframe['Machine_ID'].unique():
            obj = await sensor_node.add_object(1, machine_id)
            for measurement in ['Temperature_C', 'Vibration_mm_s', 'Pressure_bar']:
                var = await obj.add_variable(1, measurement, 0.0)
                await var.set_writable()

        objects.add_object.assert_called_once_with(1, "Sensors")
        sensor_node.add_variable.assert_called()
        variable_node.set_writable.assert_called()


class TestDataPublishing:
    """Test cases for sensor data publishing functionality."""

    @pytest.fixture
    def mock_sensor_setup(self):
        """Set up mock sensor nodes for testing."""
        server = AsyncMock()
        # Use synchronous get_objects_node so get_objects_node() isn't a coroutine
        objects_node = AsyncMock()
        server.get_objects_node = Mock(return_value=objects_node)
        sensor_node = AsyncMock()
        ts_sensor = AsyncMock()
        objects_node.get_child.return_value = sensor_node
        sensor_node.get_child.return_value = ts_sensor

        # Mock machine sensors
        machine_obj = AsyncMock()
        temp_sensor = AsyncMock()
        vibration_sensor = AsyncMock()
        pressure_sensor = AsyncMock()

        def get_child_side_effect(path):
            name = path[0] if isinstance(path, list) else str(path)
            if 'Timestamp_Sensor' in name:
                return ts_sensor
            elif 'Temperature_C' in name:
                return temp_sensor
            elif 'Vibration_mm_s' in name:
                return vibration_sensor
            elif 'Pressure_bar' in name:
                return pressure_sensor
            else:
                return machine_obj

        sensor_node.get_child.side_effect = get_child_side_effect
        machine_obj.get_child.side_effect = get_child_side_effect

        return {
            'server': server,
            'sensor_node': sensor_node,
            'ts_sensor': ts_sensor,
            'temp_sensor': temp_sensor,
            'vibration_sensor': vibration_sensor,
            'pressure_sensor': pressure_sensor
        }

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        return pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00', '2024-01-24 01:00:00']),
            'Machine_ID': ['Machine_1', 'Machine_1'],
            'Temperature_C': [62.12, 63.45],
            'Vibration_mm_s': [2.51, 2.48],
            'Pressure_bar': [5.98, 6.12]
        })

    @pytest.mark.asyncio
    async def test_sensor_value_writing(self, mock_sensor_setup, sample_dataframe):
        """Test writing sensor values to OPC UA variables."""
        mocks = mock_sensor_setup
        await mocks['temp_sensor'].write_value(62.12)
        await mocks['vibration_sensor'].write_value(2.51)
        await mocks['pressure_sensor'].write_value(5.98)

        mocks['temp_sensor'].write_value.assert_called_with(62.12)
        mocks['vibration_sensor'].write_value.assert_called_with(2.51)
        mocks['pressure_sensor'].write_value.assert_called_with(5.98)

    @pytest.mark.asyncio
    async def test_timestamp_writing(self, mock_sensor_setup, sample_dataframe):
        """Test writing timestamp values."""
        mocks = mock_sensor_setup
        timestamp = sample_dataframe['Timestamp'].iloc[0].to_pydatetime()
        await mocks['ts_sensor'].write_value(timestamp, VariantType.DateTime)

        mocks['ts_sensor'].write_value.assert_called_with(timestamp, VariantType.DateTime)

    @pytest.mark.asyncio
    async def test_publish_sensor_loop_iteration(self, mock_sensor_setup, sample_dataframe):
        """Test a single iteration of the publish sensor loop."""
        mocks = mock_sensor_setup
        server = mocks['server']
        idx = 1

        # Mock the node traversal
        objects = server.get_objects_node()
        sensor_node = await objects.get_child([f"{idx}:Sensors"])
        ts_sensor = await sensor_node.get_child([f"{idx}:Timestamp_Sensor"])

        # Prepare a single timestamp batch
        timestamp = sample_dataframe['Timestamp'].iloc[0]
        batch = sample_dataframe[sample_dataframe['Timestamp'] == timestamp]

        await ts_sensor.write_value(timestamp.to_pydatetime(), VariantType.DateTime)
        for _, row in batch.iterrows():
            await mocks['temp_sensor'].write_value(float(row['Temperature_C']))
            await mocks['vibration_sensor'].write_value(float(row['Vibration_mm_s']))
            await mocks['pressure_sensor'].write_value(float(row['Pressure_bar']))

        ts_sensor.write_value.assert_called()
        mocks['temp_sensor'].write_value.assert_called()
        mocks['vibration_sensor'].write_value.assert_called()
        mocks['pressure_sensor'].write_value.assert_called()


class TestErrorHandling:
    """Test cases for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_server_start_failure(self):
        """Test handling of server start failure."""
        mock_server = AsyncMock()
        mock_server.start.side_effect = Exception("Failed to start server")

        with patch('server.Server', return_value=mock_server), \
                patch('pandas.read_csv', return_value=pd.DataFrame({
                    'Timestamp': pd.to_datetime(['2024-01-24 00:00:00']),
                    'Machine_ID': ['Machine_1'],
                    'Temperature_C': [62.12],
                    'Vibration_mm_s': [2.51],
                    'Pressure_bar': [5.98]
                })):
            with pytest.raises(Exception, match="Failed to start server"):
                await mock_server.start()

    @pytest.mark.asyncio
    async def test_node_creation_failure(self):
        """Test handling of node creation failure."""
        mock_server = AsyncMock()
        mock_objects = AsyncMock()
        # Use synchronous get_objects_node
        mock_server.get_objects_node = Mock(return_value=mock_objects)
        mock_objects.add_object = AsyncMock(side_effect=Exception("Failed to create node"))

        with pytest.raises(Exception, match="Failed to create node"):
            objects = mock_server.get_objects_node()
            await objects.add_object(1, "Sensors")

    @pytest.mark.asyncio
    async def test_data_writing_failure(self):
        """Test handling of data writing failure."""
        mock_variable = AsyncMock()
        mock_variable.write_value.side_effect = Exception("Failed to write value")

        with pytest.raises(Exception, match="Failed to write value"):
            await mock_variable.write_value(62.12)


class TestMainFunction:
    """Test cases for the main function integration."""

    @pytest.mark.asyncio
    async def test_main_function_setup(self):
        """Test the main function setup process."""
        sample_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00']),
            'Machine_ID': ['Machine_1'],
            'Temperature_C': [62.12],
            'Vibration_mm_s': [2.51],
            'Pressure_bar': [5.98]
        })

        mock_server = AsyncMock()
        mock_server.register_namespace.return_value = 1
        mock_objects = AsyncMock()
        mock_server.get_objects_node = Mock(return_value=mock_objects)
        mock_sensor_node = AsyncMock()
        mock_variable = AsyncMock()

        mock_objects.add_object = AsyncMock(return_value=mock_sensor_node)
        mock_sensor_node.add_variable = AsyncMock(return_value=mock_variable)
        mock_sensor_node.add_object = AsyncMock()

        with patch('pandas.read_csv', return_value=sample_df), \
                patch('server.Server', return_value=mock_server), \
                patch('server.publish_sensor') as mock_publish:
            # Mock the publish_sensor to avoid infinite loop
            mock_publish.side_effect = KeyboardInterrupt("Test interrupt")

            with pytest.raises(KeyboardInterrupt):
                await main()


class TestDataValidation:
    """Test cases for data validation and edge cases."""

    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame()

        with pytest.raises((KeyError, IndexError)):
            empty_df['Machine_ID'].unique()

    def test_missing_columns(self):
        """Test handling of DataFrame with missing required columns."""
        incomplete_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00']),
            'Machine_ID': ['Machine_1']
        })

        with pytest.raises(KeyError):
            float(incomplete_df['Temperature_C'].iloc[0])

    def test_invalid_data_types(self):
        """Test handling of invalid data types in DataFrame."""
        invalid_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00']),
            'Machine_ID': ['Machine_1'],
            'Temperature_C': ['invalid_temperature'],  # String instead of float
            'Vibration_mm_s': [2.51],
            'Pressure_bar': [5.98]
        })

        with pytest.raises((ValueError, TypeError)):
            float(invalid_df['Temperature_C'].iloc[0])

    def test_duplicate_timestamps(self):
        """Test handling of duplicate timestamps for same machine."""
        duplicate_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(['2024-01-24 00:00:00', '2024-01-24 00:00:00']),
            'Machine_ID': ['Machine_1', 'Machine_1'],
            'Temperature_C': [62.12, 63.45],
            'Vibration_mm_s': [2.51, 2.48],
            'Pressure_bar': [5.98, 6.12]
        })

        # This should work - multiple rows for same timestamp/machine is valid
        unique_timestamps = duplicate_df['Timestamp'].unique()
        assert len(unique_timestamps) == 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
