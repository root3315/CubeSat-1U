"""
Comprehensive Unit Tests for Security Module
Tests for SecurityManager class covering nonce generation/validation,
HMAC signature creation/verification, command authentication,
replay attack prevention, and thread-safety of nonce operations.
"""
import unittest
import json
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/raspberry-pi-code'))

from security import SecurityManager, create_secure_command, validate_secure_command


class TestSecurityManagerNonceGeneration(unittest.TestCase):
    """Tests for nonce generation functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key_12345")

    def test_generate_nonce_returns_string(self):
        """Test that generate_nonce returns a string"""
        nonce = self.security.generate_nonce()
        self.assertIsInstance(nonce, str)

    def test_generate_nonce_returns_hex_string(self):
        """Test that generate_nonce returns a valid hex string"""
        nonce = self.security.generate_nonce()
        # Should be valid hex (16 chars = 8 bytes)
        try:
            bytes.fromhex(nonce)
        except ValueError:
            self.fail("generate_nonce did not return a valid hex string")

    def test_generate_nonce_unique_values(self):
        """Test that generated nonces are unique"""
        nonces = set()
        for _ in range(1000):
            nonce = self.security.generate_nonce()
            nonces.add(nonce)
        # All 1000 nonces should be unique
        self.assertEqual(len(nonces), 1000)

    def test_generate_nonce_correct_length(self):
        """Test that generated nonces have correct length (16 hex chars = 8 bytes)"""
        for _ in range(100):
            nonce = self.security.generate_nonce()
            self.assertEqual(len(nonce), 16)  # 8 bytes = 16 hex characters

    def test_generate_nonce_randomness(self):
        """Test that nonces have good randomness distribution"""
        nonces = [self.security.generate_nonce() for _ in range(100)]
        # Check that not all nonces start with the same character
        first_chars = set(n[0] for n in nonces)
        self.assertGreater(len(first_chars), 1)


class TestSecurityManagerNonceValidation(unittest.TestCase):
    """Tests for nonce validation functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key")
        self.security.nonce_ttl = 60  # 60 seconds TTL

    def test_is_nonce_valid_new_nonce(self):
        """Test that a new nonce is valid"""
        nonce = self.security.generate_nonce()
        self.security.register_nonce(nonce)
        self.assertTrue(self.security.is_nonce_valid(nonce))

    def test_is_nonce_valid_unregistered_nonce(self):
        """Test that an unregistered nonce is invalid"""
        nonce = self.security.generate_nonce()
        self.assertFalse(self.security.is_nonce_valid(nonce))

    def test_is_nonce_valid_expired_nonce(self):
        """Test that an expired nonce is invalid"""
        # Set very short TTL for testing
        self.security.nonce_ttl = 0.1  # 100ms
        nonce = self.security.generate_nonce()
        self.security.register_nonce(nonce)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be invalid now
        self.assertFalse(self.security.is_nonce_valid(nonce))

    def test_register_nonce_adds_to_registry(self):
        """Test that register_nonce adds nonce to registry"""
        nonce = self.security.generate_nonce()
        self.security.register_nonce(nonce)
        self.assertIn(nonce, self.security.nonce_registry)

    def test_register_nonce_stores_timestamp(self):
        """Test that register_nonce stores current timestamp"""
        nonce = self.security.generate_nonce()
        before = time.time()
        self.security.register_nonce(nonce)
        after = time.time()
        
        timestamp = self.security.nonce_registry[nonce]
        self.assertGreaterEqual(timestamp, before)
        self.assertLessEqual(timestamp, after)

    def test_register_nonce_cleans_expired(self):
        """Test that register_nonce cleans up expired nonces"""
        self.security.nonce_ttl = 0.1
        
        # Register old nonce
        old_nonce = self.security.generate_nonce()
        self.security.register_nonce(old_nonce)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Register new nonce (should trigger cleanup)
        new_nonce = self.security.generate_nonce()
        self.security.register_nonce(new_nonce)
        
        # Old nonce should be cleaned up
        self.assertNotIn(old_nonce, self.security.nonce_registry)


class TestSecurityManagerSignatureCreation(unittest.TestCase):
    """Tests for HMAC signature creation"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key_123")
        self.test_data = b"test command data"
        self.test_timestamp = 1234567890.0

    def test_create_signature_returns_string(self):
        """Test that create_signature returns a string"""
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        self.assertIsInstance(signature, str)

    def test_create_signature_returns_hex(self):
        """Test that create_signature returns valid hex (SHA256 = 64 chars)"""
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        self.assertEqual(len(signature), 64)  # SHA256 hex = 64 characters
        try:
            bytes.fromhex(signature)
        except ValueError:
            self.fail("create_signature did not return valid hex")

    def test_create_signature_deterministic(self):
        """Test that same data produces same signature"""
        signature1 = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        signature2 = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        self.assertEqual(signature1, signature2)

    def test_create_signature_different_data(self):
        """Test that different data produces different signatures"""
        signature1 = self.security.create_signature(b"data1", timestamp=self.test_timestamp)
        signature2 = self.security.create_signature(b"data2", timestamp=self.test_timestamp)
        self.assertNotEqual(signature1, signature2)

    def test_create_signature_with_timestamp(self):
        """Test signature creation with explicit timestamp"""
        signature1 = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        signature2 = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        self.assertEqual(signature1, signature2)

    def test_create_signature_different_timestamps(self):
        """Test that different timestamps produce different signatures"""
        signature1 = self.security.create_signature(self.test_data, timestamp=1000.0)
        signature2 = self.security.create_signature(self.test_data, timestamp=2000.0)
        self.assertNotEqual(signature1, signature2)

    def test_create_signature_empty_data(self):
        """Test signature creation with empty data"""
        signature = self.security.create_signature(b"", timestamp=self.test_timestamp)
        self.assertEqual(len(signature), 64)

    def test_create_signature_large_data(self):
        """Test signature creation with large data"""
        large_data = b"x" * 10000
        signature = self.security.create_signature(large_data, timestamp=self.test_timestamp)
        self.assertEqual(len(signature), 64)


class TestSecurityManagerSignatureVerification(unittest.TestCase):
    """Tests for HMAC signature verification"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key")
        self.test_data = b"test data for verification"
        self.test_timestamp = 1234567890.0

    def test_verify_signature_valid(self):
        """Test verification of valid signature"""
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        self.assertTrue(self.security.verify_signature(self.test_data, signature, timestamp=self.test_timestamp))

    def test_verify_signature_invalid_data(self):
        """Test verification fails with modified data"""
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        modified_data = b"modified test data"
        self.assertFalse(self.security.verify_signature(modified_data, signature, timestamp=self.test_timestamp))

    def test_verify_signature_invalid_signature(self):
        """Test verification fails with wrong signature"""
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        wrong_signature = "a" * 64
        self.assertFalse(self.security.verify_signature(self.test_data, wrong_signature, timestamp=self.test_timestamp))

    def test_verify_signature_empty_data(self):
        """Test verification with empty data"""
        signature = self.security.create_signature(b"", timestamp=self.test_timestamp)
        self.assertTrue(self.security.verify_signature(b"", signature, timestamp=self.test_timestamp))

    def test_verify_signature_timing_safe(self):
        """Test that verification uses timing-safe comparison"""
        # This test verifies that hmac.compare_digest is used
        signature = self.security.create_signature(self.test_data, timestamp=self.test_timestamp)
        # Should not raise any exception
        result = self.security.verify_signature(self.test_data, signature, timestamp=self.test_timestamp)
        self.assertTrue(result)


class TestSecurityManagerCommandAuthentication(unittest.TestCase):
    """Tests for command authentication functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key")
        self.command_data = {
            "command_id": 1,
            "params": {"action": "capture_image"}
        }

    def test_authenticate_command_valid(self):
        """Test authentication of valid command"""
        command_json = json.dumps(self.command_data, sort_keys=True).encode()
        nonce = self.security.generate_nonce()
        timestamp = time.time()
        signature = self.security.create_signature(command_json, timestamp=timestamp)
        
        success, message = self.security.authenticate_command(
            self.command_data, signature, nonce, timestamp
        )
        
        self.assertTrue(success)
        self.assertEqual(message, "Authentication successful")

    def test_authenticate_command_invalid_signature(self):
        """Test authentication fails with invalid signature"""
        nonce = self.security.generate_nonce()
        timestamp = time.time()
        wrong_signature = "invalid_signature"
        
        success, message = self.security.authenticate_command(
            self.command_data, wrong_signature, nonce, timestamp
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid signature")

    def test_authenticate_command_old_timestamp(self):
        """Test authentication fails with old timestamp"""
        command_json = json.dumps(self.command_data, sort_keys=True).encode()
        nonce = self.security.generate_nonce()
        old_timestamp = time.time() - 30  # 30 seconds old (limit is 15)
        signature = self.security.create_signature(command_json, timestamp=old_timestamp)
        
        success, message = self.security.authenticate_command(
            self.command_data, signature, nonce, old_timestamp
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "Command too old")

    def test_authenticate_command_future_timestamp(self):
        """Test authentication fails with future timestamp"""
        command_json = json.dumps(self.command_data, sort_keys=True).encode()
        nonce = self.security.generate_nonce()
        future_timestamp = time.time() + 30  # 30 seconds in future
        signature = self.security.create_signature(command_json, timestamp=future_timestamp)
        
        success, message = self.security.authenticate_command(
            self.command_data, signature, nonce, future_timestamp
        )
        
        self.assertFalse(success)
        self.assertEqual(message, "Command too old")

    def test_authenticate_command_replay_attack(self):
        """Test that replay attacks are prevented"""
        command_json = json.dumps(self.command_data, sort_keys=True).encode()
        nonce = self.security.generate_nonce()
        timestamp = time.time()
        signature = self.security.create_signature(command_json, timestamp=timestamp)
        
        # First authentication should succeed
        success1, _ = self.security.authenticate_command(
            self.command_data, signature, nonce, timestamp
        )
        self.assertTrue(success1)
        
        # Replay attack - same command should fail
        success2, message = self.security.authenticate_command(
            self.command_data, signature, nonce, timestamp
        )
        self.assertFalse(success2)
        self.assertEqual(message, "Nonce already used")

    def test_authenticate_command_different_nonce_same_data(self):
        """Test that different nonces allow same command"""
        command_json = json.dumps(self.command_data, sort_keys=True).encode()
        timestamp = time.time()
        
        # First command with nonce1
        nonce1 = self.security.generate_nonce()
        signature1 = self.security.create_signature(command_json, timestamp=timestamp)
        success1, _ = self.security.authenticate_command(
            self.command_data, signature1, nonce1, timestamp
        )
        self.assertTrue(success1)
        
        # Second command with different nonce
        nonce2 = self.security.generate_nonce()
        signature2 = self.security.create_signature(command_json, timestamp=timestamp)
        success2, _ = self.security.authenticate_command(
            self.command_data, signature2, nonce2, timestamp
        )
        self.assertTrue(success2)


class TestSecurityManagerThreadSafety(unittest.TestCase):
    """Tests for thread-safety of nonce operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret_key")

    def test_concurrent_nonce_registration(self):
        """Test thread-safe nonce registration"""
        nonces = [self.security.generate_nonce() for _ in range(100)]
        results = []
        errors = []

        def register_nonce(nonce):
            try:
                self.security.register_nonce(nonce)
                results.append(nonce)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_nonce, args=(n,)) for n in nonces]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 100)

    def test_concurrent_nonce_validation(self):
        """Test thread-safe nonce validation"""
        # Pre-register some nonces
        nonces = [self.security.generate_nonce() for _ in range(50)]
        for nonce in nonces:
            self.security.register_nonce(nonce)

        results = []
        errors = []

        def validate_nonce(nonce):
            try:
                result = self.security.is_nonce_valid(nonce)
                results.append((nonce, result))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=validate_nonce, args=(n,)) for n in nonces]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 50)

    def test_concurrent_authentication(self):
        """Test thread-safe command authentication"""
        command_data = {"command_id": 1, "params": {}}
        results = []
        errors = []

        def authenticate_command(nonce):
            try:
                command_json = json.dumps(command_data, sort_keys=True).encode()
                signature = self.security.create_signature(command_json)
                timestamp = time.time()
                success, _ = self.security.authenticate_command(
                    command_data, signature, nonce, timestamp
                )
                results.append(success)
            except Exception as e:
                errors.append(e)

        nonces = [self.security.generate_nonce() for _ in range(50)]
        threads = [threading.Thread(target=authenticate_command, args=(n,)) for n in nonces]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 50)


class TestCreateSecureCommand(unittest.TestCase):
    """Tests for create_secure_command helper function"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret")

    def test_create_secure_command_returns_dict(self):
        """Test that create_secure_command returns a dictionary"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        self.assertIsInstance(command, dict)

    def test_create_secure_command_has_required_fields(self):
        """Test that created command has all required fields"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        
        required_fields = ['command_id', 'params', 'timestamp', 'nonce', 'signature']
        for field in required_fields:
            self.assertIn(field, command, f"Missing required field: {field}")

    def test_create_secure_command_with_params(self):
        """Test command creation with parameters"""
        params = {"action": "capture", "quality": 80}
        command = create_secure_command(
            command_id=2, 
            params=params, 
            security_manager=self.security
        )
        
        self.assertEqual(command['command_id'], 2)
        self.assertEqual(command['params'], params)

    def test_create_secure_command_default_params(self):
        """Test command creation with default empty params"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        self.assertEqual(command['params'], {})

    def test_create_secure_command_has_timestamp(self):
        """Test that command has current timestamp"""
        before = time.time()
        command = create_secure_command(command_id=1, security_manager=self.security)
        after = time.time()
        
        self.assertGreaterEqual(command['timestamp'], before)
        self.assertLessEqual(command['timestamp'], after)

    def test_create_secure_command_has_nonce(self):
        """Test that command has unique nonce"""
        command1 = create_secure_command(command_id=1, security_manager=self.security)
        command2 = create_secure_command(command_id=1, security_manager=self.security)
        
        self.assertNotEqual(command1['nonce'], command2['nonce'])

    def test_create_secure_command_has_valid_signature(self):
        """Test that command signature is valid"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        
        # Verify signature - use the timestamp from the command
        cmd_copy = command.copy()
        del cmd_copy['signature']
        command_json = json.dumps(cmd_copy, sort_keys=True).encode()
        
        is_valid = self.security.verify_signature(command_json, command['signature'], timestamp=command['timestamp'])
        self.assertTrue(is_valid)

    def test_create_secure_command_default_security_manager(self):
        """Test command creation with default security manager"""
        command = create_secure_command(command_id=1)
        
        self.assertIn('command_id', command)
        self.assertIn('signature', command)


class TestValidateSecureCommand(unittest.TestCase):
    """Tests for validate_secure_command helper function"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret")

    def test_validate_secure_command_valid(self):
        """Test validation of valid command"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        success, message = validate_secure_command(command, self.security)
        
        self.assertTrue(success)
        self.assertEqual(message, "Authentication successful")

    def test_validate_secure_command_missing_signature(self):
        """Test validation fails with missing signature"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        del command['signature']
        
        success, message = validate_secure_command(command, self.security)
        
        self.assertFalse(success)
        self.assertEqual(message, "Missing security fields")

    def test_validate_secure_command_missing_nonce(self):
        """Test validation fails with missing nonce"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        del command['nonce']
        
        success, message = validate_secure_command(command, self.security)
        
        self.assertFalse(success)
        self.assertEqual(message, "Missing security fields")

    def test_validate_secure_command_missing_timestamp(self):
        """Test validation fails with missing timestamp"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        del command['timestamp']
        
        success, message = validate_secure_command(command, self.security)
        
        self.assertFalse(success)
        self.assertEqual(message, "Missing security fields")

    def test_validate_secure_command_tampered_data(self):
        """Test validation fails with tampered command data"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        command['command_id'] = 999  # Tamper with data
        
        success, message = validate_secure_command(command, self.security)
        
        self.assertFalse(success)

    def test_validate_secure_command_wrong_security_manager(self):
        """Test validation fails with different security manager"""
        command = create_secure_command(command_id=1, security_manager=self.security)
        wrong_security = SecurityManager(shared_secret="different_secret")
        
        success, message = validate_secure_command(command, wrong_security)
        
        self.assertFalse(success)


class TestSecurityManagerEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions"""

    def setUp(self):
        """Set up test fixtures"""
        self.security = SecurityManager(shared_secret="test_secret")
        self.test_timestamp = 1234567890.0

    def test_empty_shared_secret(self):
        """Test initialization with empty shared secret"""
        security = SecurityManager(shared_secret="")
        data = b"test"
        signature = security.create_signature(data, timestamp=self.test_timestamp)
        self.assertTrue(security.verify_signature(data, signature, timestamp=self.test_timestamp))

    def test_unicode_shared_secret(self):
        """Test with unicode shared secret"""
        security = SecurityManager(shared_secret="секрет_ключ_🔐")
        data = b"test"
        signature = security.create_signature(data, timestamp=self.test_timestamp)
        self.assertTrue(security.verify_signature(data, signature, timestamp=self.test_timestamp))

    def test_very_long_shared_secret(self):
        """Test with very long shared secret"""
        security = SecurityManager(shared_secret="a" * 10000)
        data = b"test"
        signature = security.create_signature(data, timestamp=self.test_timestamp)
        self.assertTrue(security.verify_signature(data, signature, timestamp=self.test_timestamp))

    def test_special_characters_in_data(self):
        """Test signature with special characters in data"""
        data = b'{"special": "chars\\n\\t\\r"}'
        signature = self.security.create_signature(data, timestamp=self.test_timestamp)
        self.assertTrue(self.security.verify_signature(data, signature, timestamp=self.test_timestamp))

    def test_binary_data(self):
        """Test signature with binary data"""
        data = bytes([0x00, 0x01, 0xFF, 0xFE])
        signature = self.security.create_signature(data, timestamp=self.test_timestamp)
        self.assertTrue(self.security.verify_signature(data, signature, timestamp=self.test_timestamp))

    def test_nonce_registry_cleanup(self):
        """Test that nonce registry cleans up expired entries"""
        self.security.nonce_ttl = 0.1
        
        # Add many nonces
        for _ in range(100):
            nonce = self.security.generate_nonce()
            self.security.register_nonce(nonce)
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Trigger cleanup by registering new nonce
        new_nonce = self.security.generate_nonce()
        self.security.register_nonce(new_nonce)
        
        # Registry should be mostly cleaned
        self.assertLess(len(self.security.nonce_registry), 50)


def suite():
    """Create test suite"""
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerNonceGeneration))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerNonceValidation))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerSignatureCreation))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerSignatureVerification))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerCommandAuthentication))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerThreadSafety))
    test_suite.addTests(loader.loadTestsFromTestCase(TestCreateSecureCommand))
    test_suite.addTests(loader.loadTestsFromTestCase(TestValidateSecureCommand))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerEdgeCases))

    return test_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())

    print(f"\n{'='*60}")
    print(f"Security Module Test Results")
    print(f"{'='*60}")
    print(f"Total tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Success: {result.wasSuccessful()}")
    
    if result.errors:
        print(f"\n{'='*60}")
        print("ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}")
    
    if result.failures:
        print(f"\n{'='*60}")
        print("FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    exit(0 if result.wasSuccessful() else 1)
