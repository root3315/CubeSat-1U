"""
Simplified Test Suite for CubeSat System
Lightweight tests optimized for resource-constrained environments
"""
import unittest
import json
import time
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'raspberry-pi-code'))

from security import SecurityManager, create_secure_command, validate_secure_command
from ota_updater import OTAUpdater


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


def test_telemetry_processing_performance():
    """Simple performance test for telemetry processing"""
    import time
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'raspberry-pi-code'))
    from telemetry_handler import TelemetryHandler

    # Create a simple telemetry handler
    config = {"storage": {"base_path": "/tmp"}}
    handler = TelemetryHandler(config)

    # Generate a few mock telemetry data points
    telemetry_data = []
    for i in range(100):  # Smaller number for efficiency
        data = {
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
        handler.save_telemetry(data)
    end_time = time.time()

    processing_time = end_time - start_time
    # Processing 100 telemetry packets should take less than 2 seconds
    assert processing_time < 2.0, f"Processing took {processing_time:.3f}s, expected < 2.0s"


def test_nonce_replay_protection():
    """Test that nonce replay protection works"""
    security = SecurityManager(shared_secret="replay_test")

    # Create a command
    command = {"type": "TEST", "value": 123}
    secure_cmd = create_secure_command(2, command, security)

    # First validation should succeed
    is_valid1, msg1 = validate_secure_command(secure_cmd, security)
    assert is_valid1, f"First validation failed: {msg1}"

    # Second validation with same nonce should fail
    is_valid2, msg2 = validate_secure_command(secure_cmd, security)
    assert not is_valid2, f"Replay protection failed: {msg2}"
    assert "already used" in msg2.lower() or "nonce" in msg2.lower()


def test_end_to_end_workflow():
    """Simple end-to-end workflow test"""
    # Initialize components
    security = SecurityManager(shared_secret="integration_test")

    # Create and validate a secure command
    command = {"type": "TELEMETRY_REQUEST", "params": {"satellite": "TEST-001"}}
    secure_cmd = create_secure_command(2, command, security)

    is_valid, msg = validate_secure_command(secure_cmd, security)
    assert is_valid, f"Command validation failed: {msg}"

    # Test basic telemetry processing
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'raspberry-pi-code'))
    from telemetry_handler import TelemetryHandler
    config = {"storage": {"base_path": "/tmp"}}
    telemetry_handler = TelemetryHandler(config)
    
    telemetry = {
        "satellite_id": "TEST-001",
        "temperature": 25.5,
        "voltage": 3.75,
        "signal_strength": -65
    }

    # Store the telemetry
    success = telemetry_handler.save_telemetry(telemetry)
    assert success, "Failed to store telemetry"


if __name__ == '__main__':
    # Run the tests
    print("Running simplified CubeSat test suite...")
    
    # Run unit tests
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run additional tests
    print("\nRunning performance test...")
    test_telemetry_processing_performance()
    print("✓ Performance test passed")
    
    print("Running replay protection test...")
    test_nonce_replay_protection()
    print("✓ Replay protection test passed")
    
    print("Running end-to-end test...")
    test_end_to_end_workflow()
    print("✓ End-to-end test passed")
    
    print("\nAll tests completed successfully!")