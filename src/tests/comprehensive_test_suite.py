"""
Comprehensive Test Suite for CubeSat System
Includes unit, integration, performance, and security tests
"""
import unittest
import pytest
import json
import time
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import modules to test
from raspberry_pi_code.security import SecurityManager, create_secure_command, validate_secure_command
from distributed_system import SimpleSystemManager, TelemetryProcessor, DataStorageNode  # Simplified imports
from raspberry_pi_code.ota_updater import OTAUpdater


class TestSecurityModule(unittest.TestCase):
    """Test the security module functionality"""
    
    def setUp(self):
        self.security = SecurityManager(shared_secret="test_secret")
    
    def test_signature_generation(self):
        """Test that signatures are generated correctly"""
        data = {"command": "test", "value": 123}
        signature = self.security.create_signature(json.dumps(data).encode())
        
        # Signature should be a hex string of appropriate length
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256 produces 64 hex chars
    
    def test_signature_verification(self):
        """Test that signatures can be verified"""
        data = {"command": "test", "value": 123}
        data_bytes = json.dumps(data).encode()
        signature = self.security.create_signature(data_bytes)
        
        is_valid = self.security.verify_signature(data_bytes, signature)
        self.assertTrue(is_valid)
    
    def test_signature_invalid_data(self):
        """Test that invalid signatures are rejected"""
        data = {"command": "test", "value": 123}
        wrong_data = {"command": "different", "value": 456}
        
        data_bytes = json.dumps(data).encode()
        wrong_data_bytes = json.dumps(wrong_data).encode()
        
        signature = self.security.create_signature(data_bytes)
        is_valid = self.security.verify_signature(wrong_data_bytes, signature)
        
        self.assertFalse(is_valid)
    
    def test_nonce_generation_and_validation(self):
        """Test nonce generation and validation"""
        nonce = self.security.generate_nonce()
        
        # Initially nonce should not be valid (not registered)
        self.assertFalse(self.security.is_nonce_valid(nonce))
        
        # Register the nonce
        self.security.register_nonce(nonce)
        
        # Now it should be invalid (already used)
        self.assertFalse(self.security.is_nonce_valid(nonce))
    
    def test_secure_command_creation_and_validation(self):
        """Test creation and validation of secure commands"""
        command = create_secure_command(1, {"test": "value"}, self.security)
        
        self.assertIn('signature', command)
        self.assertIn('nonce', command)
        self.assertIn('timestamp', command)
        
        # Validate the command
        is_valid, msg = validate_secure_command(command, self.security)
        self.assertTrue(is_valid)


class TestDataStorageNode(unittest.TestCase):
    """Test the data storage node functionality"""
    
    def setUp(self):
        self.storage = DataStorageNode(host="localhost", port=8003)
    
    def test_store_and_query_telemetry(self):
        """Test storing and querying telemetry data"""
        telemetry_data = {
            "satellite_id": "TEST-001",
            "temperature": 25.0,
            "voltage": 3.7
        }
        
        # Store telemetry
        result = self.storage.store_telemetry(telemetry_data)
        self.assertTrue(result)
        
        # Query by satellite_id
        results = self.storage.query_data({"satellite_id": "TEST-001"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['data']['satellite_id'], "TEST-001")
    
    def test_storage_size_limit(self):
        """Test that storage respects size limits"""
        original_limit = self.storage.max_storage_entries
        self.storage.max_storage_entries = 5  # Small limit for testing
        
        # Add more entries than the limit
        for i in range(10):
            telemetry_data = {
                "satellite_id": f"TEST-{i:03d}",
                "value": i
            }
            self.storage.store_telemetry(telemetry_data)
        
        # Storage should not exceed the limit
        self.assertLessEqual(len(self.storage.storage_backend), 5)
        
        # Restore original limit
        self.storage.max_storage_entries = original_limit


# Removed LoadBalancer tests as it's no longer part of the simplified system


# Removed ResourceMonitor tests as it's no longer part of the simplified system


class TestOTAUpdater(unittest.TestCase):
    """Test the OTA updater functionality"""
    
    def setUp(self):
        config = {
            'ota': {
                'server_url': 'https://test.example.com',
                'update_directory': '/tmp/updates',
                'backup_directory': '/tmp/backups',
                'current_version': '1.0.0',
                'auto_check_interval': 3600
            }
        }
        self.ota = OTAUpdater(config)
    
    def test_initialization(self):
        """Test OTA updater initialization"""
        self.assertEqual(self.ota.current_version, '1.0.0')
        self.assertEqual(self.ota.server_url, 'https://test.example.com')


@pytest.mark.performance
def test_telemetry_processing_performance():
    """Performance test for telemetry processing"""
    import time
    from distributed_system import TelemetryProcessor

    processor = TelemetryProcessor()

    # Generate a bunch of mock telemetry data
    telemetry_data = []
    for i in range(1000):  # More data for better performance testing
        data = {
            "satellite_id": f"SAT-{i:03d}",
            "timestamp": time.time(),
            "sequence": i,
            "temperature_bme": 20 + (i % 5),
            "pressure": 1013 + (i % 10),
            "humidity": 45 + (i % 15),
            "battery_voltage": 3.8 + (i % 2) * 0.1,
            "battery_level": 90 + (i % 10),
            "radiation_cps": 30 + (i % 20),
            "mag_x": 0.25 + (i % 5) * 0.01,
            "mag_y": -0.18 + (i % 5) * 0.01,
            "mag_z": 0.45 + (i % 5) * 0.01
        }
        telemetry_data.append(data)

    # Measure processing time
    start_time = time.time()
    for data in telemetry_data:
        processor._analyze_telemetry(data)
    end_time = time.time()

    processing_time = end_time - start_time
    # Processing 1000 telemetry packets should take less than 3 seconds (improved performance)
    assert processing_time < 3.0, f"Processing took {processing_time:.3f}s, expected < 3.0s"


@pytest.mark.security
def test_nonce_replay_protection():
    """Test that nonce replay protection works"""
    security = SecurityManager(shared_secret="replay_test")
    
    # Create a command
    command = {"type": "TEST", "value": 123}
    secure_command = create_secure_command(1, command, security)
    
    # First validation should succeed
    is_valid1, msg1 = validate_secure_command(secure_command, security)
    assert is_valid1, f"First validation failed: {msg1}"
    
    # Second validation with same nonce should fail
    is_valid2, msg2 = validate_secure_command(secure_command, security)
    assert not is_valid2, f"Replay protection failed: {msg2}"
    assert "already used" in msg2.lower() or "nonce" in msg2.lower()


@pytest.mark.integration
def test_end_to_end_workflow():
    """Test an end-to-end workflow with multiple components"""
    # Initialize components
    security = SecurityManager(shared_secret="integration_test")
    storage = DataStorageNode(host="localhost", port=8003)
    processor = TelemetryProcessor(host="localhost", port=8001)

    # Create and validate a secure command
    command = {"type": "TELEMETRY_REQUEST", "params": {"satellite": "TEST-001"}}
    secure_cmd = create_secure_command(2, command, security)

    is_valid, msg = validate_secure_command(secure_cmd, security)
    assert is_valid, f"Command validation failed: {msg}"

    # Process some telemetry data
    telemetry = {
        "satellite_id": "TEST-001",
        "temperature": 25.5,
        "voltage": 3.75,
        "signal_strength": -65
    }

    # Store the telemetry
    success = storage.store_telemetry(telemetry)
    assert success, "Failed to store telemetry"

    # Process the telemetry
    success = processor.process_telemetry(telemetry)
    assert success, "Failed to process telemetry"

    # Query the stored telemetry
    results = storage.query_data({"satellite_id": "TEST-001"})
    assert len(results) >= 1, "No telemetry found after storage"

    # Test simplified system manager
    system_manager = SimpleSystemManager()
    system_manager.initialize_system()
    
    # Process telemetry through the system
    success = system_manager.process_telemetry(telemetry)
    assert success, "Failed to process telemetry through system manager"


if __name__ == '__main__':
    # Run the tests
    unittest.main()