"""
Simplified Security Module for CubeSat System
Lightweight implementation optimized for resource-constrained environments
"""
from __future__ import annotations

import hashlib
import hmac
import time
import secrets
from typing import Dict, Optional, Tuple, Any
import json
import struct
import threading


class SecurityManager:
    """
    Simplified security manager for CubeSat system
    Lightweight implementation for resource constraints
    """

    def __init__(self, shared_secret: Optional[str] = None) -> None:
        """
        Initialize security manager

        Args:
            shared_secret: Shared secret key for HMAC signatures
        """
        if shared_secret is None:
            # Generate a random secret key
            self.shared_secret: str = secrets.token_hex(16)  # Smaller key for efficiency
        else:
            self.shared_secret = shared_secret

        # Dictionary to track nonces (one-time numbers)
        self.nonce_registry: Dict[str, float] = {}
        # Nonce time-to-live in seconds
        self.nonce_ttl: float = 60  # Reduced TTL for CubeSat (1 minute)
        # FIX: Add thread lock for thread-safe nonce operations
        self._nonce_lock: threading.Lock = threading.Lock()

    def generate_nonce(self) -> str:
        """
        Generate a one-time number (nonce)

        Returns:
            Random one-time number
        """
        return secrets.token_hex(8)  # Smaller nonce for efficiency

    def is_nonce_valid(self, nonce: str) -> bool:
        """
        Check validity of nonce (not previously used and not expired)

        Args:
            nonce: One-time number to check

        Returns:
            True if nonce is valid, otherwise False
        """
        current_time: float = time.time()

        # FIX: Thread-safe nonce check
        with self._nonce_lock:
            # Check if nonce exists
            if nonce in self.nonce_registry:
                # Check lifetime
                timestamp: float = self.nonce_registry[nonce]
                if current_time - timestamp > self.nonce_ttl:
                    # Remove expired nonce
                    del self.nonce_registry[nonce]
                    return False
                return True
        return False

    def register_nonce(self, nonce: str) -> None:
        """
        Register nonce as used

        Args:
            nonce: One-time number to register
        """
        # FIX: Thread-safe nonce registration
        with self._nonce_lock:
            self.nonce_registry[nonce] = time.time()

            # Clean up expired nonces periodically
            current_time: float = time.time()
            expired_nonces: List[str] = [
                n for n, t in self.nonce_registry.items()
                if current_time - t > self.nonce_ttl
            ]
            for n in expired_nonces:
                del self.nonce_registry[n]

    def create_signature(self, data: bytes, timestamp: Optional[float] = None) -> str:
        """
        Create digital signature for data

        Args:
            data: Data to sign
            timestamp: Timestamp (if None, current time is used)

        Returns:
            Hex representation of HMAC signature
        """
        if timestamp is None:
            timestamp = time.time()

        # Create message for signing: data + timestamp
        message: bytes = data + str(timestamp).encode('utf-8')

        # Create HMAC signature
        signature: str = hmac.new(
            self.shared_secret.encode('utf-8'),
            message,
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, data: bytes, signature: str, timestamp: Optional[float] = None) -> bool:
        """
        Verify digital signature

        Args:
            data: Original data
            signature: Signature to verify
            timestamp: Timestamp

        Returns:
            True if signature is valid, otherwise False
        """
        if timestamp is None:
            timestamp = time.time()

        expected_signature: str = self.create_signature(data, timestamp)
        return hmac.compare_digest(expected_signature, signature)

    def authenticate_command(
        self, 
        command_data: Dict[str, Any], 
        signature: str, 
        nonce: str,
        timestamp: float
    ) -> Tuple[bool, str]:
        """
        Authenticate command from ground station

        Args:
            command_data: Command data
            signature: Digital signature
            nonce: One-time number
            timestamp: Timestamp

        Returns:
            Tuple (success, error message)
        """
        # Check time - command should be recent (not older than 15 sec)
        current_time: float = time.time()
        if abs(current_time - timestamp) > 15:  # Reduced from 30 to 15 seconds
            return False, "Command too old"

        # Check nonce uniqueness
        if self.is_nonce_valid(nonce):
            return False, "Nonce already used"

        # Verify signature
        command_json: bytes = json.dumps(command_data, sort_keys=True).encode('utf-8')
        if not self.verify_signature(command_json, signature, timestamp):
            return False, "Invalid signature"

        # Register nonce as used
        self.register_nonce(nonce)

        return True, "Authentication successful"


def create_secure_command(
    command_id: int, 
    params: Optional[Dict[str, Any]] = None, 
    security_manager: Optional[SecurityManager] = None
) -> Dict[str, Any]:
    """
    Create a secure authenticated command

    Args:
        command_id: Command ID
        params: Command parameters
        security_manager: Security manager

    Returns:
        Dictionary with secure command
    """
    if security_manager is None:
        security_manager = SecurityManager()

    if params is None:
        params = {}

    # Create command
    command: Dict[str, Any] = {
        'command_id': command_id,
        'params': params,
        'timestamp': time.time(),
        'nonce': security_manager.generate_nonce()
    }

    # Create signature
    command_json: bytes = json.dumps(command, sort_keys=True).encode('utf-8')
    signature: str = security_manager.create_signature(command_json, command['timestamp'])

    # Add signature to command
    command['signature'] = signature

    return command


def validate_secure_command(
    command: Dict[str, Any], 
    security_manager: SecurityManager
) -> Tuple[bool, str]:
    """
    Validate a secure command

    Args:
        command: Command to validate
        security_manager: Security manager

    Returns:
        Tuple (success, message)
    """
    if 'signature' not in command or 'nonce' not in command or 'timestamp' not in command:
        return False, "Missing security fields"

    # Extract data for verification
    signature: str = command['signature']
    nonce: str = command['nonce']
    timestamp: float = command['timestamp']

    # Remove security fields for signature verification
    cmd_copy: Dict[str, Any] = command.copy()
    del cmd_copy['signature']

    # Authenticate command
    success: bool
    msg: str
    success, msg = security_manager.authenticate_command(cmd_copy, signature, nonce, timestamp)

    return success, msg
