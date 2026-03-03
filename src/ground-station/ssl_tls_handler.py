"""
SSL/TLS Handler for CubeSat Ground Station
Provides secure encrypted communication channels
"""
import ssl
import socket
import threading
import logging
from typing import Optional, Tuple, Any
import os
import tempfile
import secrets


class GroundStationSSLHandler:
    """
    SSL/TLS handler for secure communication between ground station and CubeSat
    Implements both client and server SSL/TLS functionality
    """

    def __init__(self, config: dict) -> None:
        self.config: dict = config
        self.logger: logging.Logger = logging.getLogger('GroundStation_SSL_TLS_Handler')

        # SSL/TLS configuration
        self.ssl_enabled: bool = config.get('security', {}).get('ssl_enabled', False)
        self.cert_file: str = config.get('security', {}).get('cert_file', './certs/client.crt')
        self.key_file: str = config.get('security', {}).get('key_file', './certs/client.key')
        self.ca_cert_file: str = config.get('security', {}).get('ca_cert_file', './certs/ca.crt')

        # Create certificates directory if it doesn't exist
        certs_dir: str = os.path.dirname(self.cert_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        certs_dir = os.path.dirname(self.key_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        certs_dir = os.path.dirname(self.ca_cert_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        # Generate self-signed certificates if they don't exist
        if self.ssl_enabled:
            self._ensure_certificates_exist()

        # SSL context
        self.ssl_context: Optional[ssl.SSLContext] = None
        self._create_ssl_context()

    def _ensure_certificates_exist(self) -> None:
        """Generate self-signed certificates if they don't exist"""
        import subprocess
        import platform

        # Check if certificate files exist
        cert_exists: bool = os.path.exists(self.cert_file)
        key_exists: bool = os.path.exists(self.key_file)

        if not cert_exists or not key_exists:
            self.logger.info("Generating self-signed SSL certificates...")

            # Create a temporary directory for openssl operations
            with tempfile.TemporaryDirectory() as temp_dir:
                # Certificate details
                subj: str = "/C=US/ST=CA/L=San Francisco/O=GroundStation/OU=Control/CN=groundstation.local"

                # Generate private key
                key_path: str = os.path.join(temp_dir, "temp.key")
                cert_path: str = os.path.join(temp_dir, "temp.crt")

                try:
                    # Generate private key
                    subprocess.run([
                        "openssl", "genrsa", "-out", key_path, "2048"
                    ], check=True, capture_output=True)

                    # Generate certificate
                    subprocess.run([
                        "openssl", "req", "-new", "-x509", "-key", key_path,
                        "-out", cert_path, "-days", "365", "-subj", subj
                    ], check=True, capture_output=True)

                    # Copy to final location
                    import shutil
                    shutil.copy(key_path, self.key_file)
                    shutil.copy(cert_path, self.cert_file)

                    self.logger.info(f"Certificates generated: {self.cert_file}, {self.key_file}")

                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to generate certificates: {e}")
                    # CRITICAL FIX #106: Don't create dummy files - fail properly
                    raise RuntimeError(f"SSL certificate generation failed: {e}")
                except FileNotFoundError:
                    self.logger.error("OpenSSL not found. SSL cannot be enabled without OpenSSL.")
                    # CRITICAL FIX #106: Don't create dummy files - fail properly
                    self.ssl_enabled = False
                    raise RuntimeError("OpenSSL is required for SSL/TLS functionality")

    def _create_ssl_context(self) -> None:
        """Create SSL context based on configuration"""
        if not self.ssl_enabled:
            self.ssl_context = None
            return

        try:
            # Create SSL context
            self.ssl_context = ssl.create_default_context()

            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                self.ssl_context.load_cert_chain(self.cert_file, self.key_file)

            if os.path.exists(self.ca_cert_file):
                self.ssl_context.load_verify_locations(self.ca_cert_file)

            # Set security options
            self.ssl_context.check_hostname = False  # For self-signed certificates
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED  # Require certificate verification

            self.logger.info("SSL context created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            self.ssl_context = None

    def wrap_socket(self, sock: socket.socket, server_side: bool = False) -> socket.socket:
        """
        Wrap a socket with SSL/TLS

        Args:
            sock: The socket to wrap
            server_side: True if this is a server socket, False for client

        Returns:
            SSL-wrapped socket
        """
        if not self.ssl_enabled or self.ssl_context is None:
            return sock

        try:
            wrapped_sock: ssl.SSLSocket = self.ssl_context.wrap_socket(  # type: ignore
                sock,
                server_side=server_side,
                do_handshake_on_connect=True
            )
            self.logger.info(f"Socket wrapped with SSL/TLS (server_side={server_side})")
            return wrapped_sock
        except Exception as e:
            self.logger.error(f"Failed to wrap socket with SSL: {e}")
            return sock  # Return original socket if SSL fails

    def create_secure_server_socket(self, host: str, port: int) -> socket.socket:
        """
        Create a secure server socket with SSL/TLS

        Args:
            host: Host address to bind to
            port: Port to bind to

        Returns:
            SSL-wrapped server socket
        """
        if not self.ssl_enabled:
            # Fallback to regular socket if SSL is disabled
            server_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((host, port))
            return server_sock

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Wrap with SSL
        ssl_sock: socket.socket = self.wrap_socket(server_sock, server_side=True)
        ssl_sock.bind((host, port))

        return ssl_sock

    def create_secure_client_socket(self, host: str, port: int) -> socket.socket:
        """
        Create a secure client socket with SSL/TLS

        Args:
            host: Host to connect to
            port: Port to connect to

        Returns:
            SSL-wrapped client socket
        """
        if not self.ssl_enabled:
            # Fallback to regular socket if SSL is disabled
            client_sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect((host, port))
            return client_sock

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Wrap with SSL
        ssl_sock: socket.socket = self.wrap_socket(client_sock, server_side=False)
        ssl_sock.connect((host, port))

        return ssl_sock

    def send_secure_data(self, ssl_socket: ssl.SSLSocket, data: bytes) -> bool:  # type: ignore
        """
        Send data securely over SSL/TLS socket

        Args:
            ssl_socket: SSL-wrapped socket
            data: Data to send

        Returns:
            True if successful, False otherwise
        """
        try:
            # Send data length first, then data
            data_len: int = len(data)
            ssl_socket.sendall(data_len.to_bytes(4, byteorder='big'))
            ssl_socket.sendall(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send secure data: {e}")
            return False

    def receive_secure_data(self, ssl_socket: ssl.SSLSocket) -> Optional[bytes]:  # type: ignore
        """
        Receive data securely from SSL/TLS socket

        Args:
            ssl_socket: SSL-wrapped socket

        Returns:
            Received data or None if failed
        """
        try:
            # Receive data length first
            len_bytes: bytes = ssl_socket.recv(4)
            if not len_bytes:
                return None

            data_len: int = int.from_bytes(len_bytes, byteorder='big')

            # Receive data
            recv_data: bytes = b''
            remaining: int = data_len

            while remaining > 0:
                chunk: bytes = ssl_socket.recv(min(remaining, 4096))
                if not chunk:
                    break
                recv_data += chunk
                remaining -= len(chunk)

            return recv_data
        except Exception as e:
            self.logger.error(f"Failed to receive secure data: {e}")
            return None

    def enable_ssl(self) -> None:
        """Enable SSL/TLS functionality"""
        self.ssl_enabled = True
        self._create_ssl_context()
        self.logger.info("SSL/TLS enabled")

    def disable_ssl(self) -> None:
        """Disable SSL/TLS functionality"""
        self.ssl_enabled = False
        self.ssl_context = None
        self.logger.info("SSL/TLS disabled")


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    config: dict = {
        "security": {
            "ssl_enabled": True,
            "cert_file": "./certs/client.crt",
            "key_file": "./certs/client.key",
            "ca_cert_file": "./certs/ca.crt"
        }
    }

    # Create SSL handler
    ssl_handler: GroundStationSSLHandler = GroundStationSSLHandler(config)

    print("Ground Station SSL/TLS Handler initialized")
    print(f"SSL Enabled: {ssl_handler.ssl_enabled}")
    print(f"SSL Context: {ssl_handler.ssl_context is not None}")
