"""
SSL/TLS Handler for CubeSat Ground Station
Provides secure encrypted communication channels
"""

import ssl
import socket
import threading
import logging
from typing import Optional, Tuple, Dict, Any
import os
import tempfile

try:
    import subprocess
    import shutil
    SUBPROCESS_AVAILABLE = True
except ImportError:
    SUBPROCESS_AVAILABLE = False


class GroundStationSSLHandler:
    """
    SSL/TLS handler for secure communication between ground station and CubeSat
    Implements both client and server SSL/TLS functionality
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger('GroundStation_SSL_TLS_Handler')

        self.ssl_enabled = config.get('security', {}).get('ssl_enabled', False)
        self.cert_file = config.get('security', {}).get('cert_file', './certs/client.crt')
        self.key_file = config.get('security', {}).get('key_file', './certs/client.key')
        self.ca_cert_file = config.get('security', {}).get('ca_cert_file', './certs/ca.crt')

        certs_dir = os.path.dirname(self.cert_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        certs_dir = os.path.dirname(self.key_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        certs_dir = os.path.dirname(self.ca_cert_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        if self.ssl_enabled:
            self._ensure_certificates_exist()

        self.ssl_context: Optional[ssl.SSLContext] = None
        self._create_ssl_context()

    def _ensure_certificates_exist(self) -> None:
        """Generate self-signed certificates if they don't exist"""
        if not SUBPROCESS_AVAILABLE:
            self.logger.error("subprocess not available, cannot generate certificates")
            self.ssl_enabled = False
            return

        cert_exists = os.path.exists(self.cert_file)
        key_exists = os.path.exists(self.key_file)

        if not cert_exists or not key_exists:
            self.logger.info("Generating self-signed SSL certificates...")

            with tempfile.TemporaryDirectory() as temp_dir:
                subj = "/C=US/ST=CA/L=San Francisco/O=GroundStation/OU=Control/CN=groundstation.local"
                key_path = os.path.join(temp_dir, "temp.key")
                cert_path = os.path.join(temp_dir, "temp.crt")

                try:
                    subprocess.run([
                        "openssl", "genrsa", "-out", key_path, "2048"
                    ], check=True, capture_output=True)

                    subprocess.run([
                        "openssl", "req", "-new", "-x509", "-key", key_path,
                        "-out", cert_path, "-days", "365", "-subj", subj
                    ], check=True, capture_output=True)

                    shutil.copy(key_path, self.key_file)
                    shutil.copy(cert_path, self.cert_file)

                    self.logger.info(f"Certificates generated: {self.cert_file}, {self.key_file}")

                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to generate certificates: {e}")
                    raise RuntimeError(f"SSL certificate generation failed: {e}")
                except FileNotFoundError:
                    self.logger.error("OpenSSL not found. SSL cannot be enabled without OpenSSL.")
                    self.ssl_enabled = False
                    raise RuntimeError("OpenSSL is required for SSL/TLS functionality")

    def _create_ssl_context(self) -> None:
        """Create SSL context based on configuration"""
        if not self.ssl_enabled:
            self.ssl_context = None
            return

        try:
            self.ssl_context = ssl.create_default_context()

            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                self.ssl_context.load_cert_chain(self.cert_file, self.key_file)

            if os.path.exists(self.ca_cert_file):
                self.ssl_context.load_verify_locations(self.ca_cert_file)

            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED

            self.logger.info("SSL context created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create SSL context: {e}")
            self.ssl_context = None

    def wrap_socket(
        self,
        sock: socket.socket,
        server_side: bool = False
    ) -> ssl.SSLSocket:
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
            wrapped_sock = self.ssl_context.wrap_socket(
                sock,
                server_side=server_side,
                do_handshake_on_connect=True
            )
            self.logger.info(f"Socket wrapped with SSL/TLS (server_side={server_side})")
            return wrapped_sock
        except Exception as e:
            self.logger.error(f"Failed to wrap socket with SSL: {e}")
            return sock

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
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((host, port))
            return server_sock

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        ssl_sock = self.wrap_socket(server_sock, server_side=True)
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
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect((host, port))
            return client_sock

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = self.wrap_socket(client_sock, server_side=False)
        ssl_sock.connect((host, port))

        return ssl_sock

    def send_secure_data(self, ssl_socket: ssl.SSLSocket, data: bytes) -> bool:
        """
        Send data securely over SSL/TLS socket

        Args:
            ssl_socket: SSL-wrapped socket
            data: Data to send

        Returns:
            True if successful, False otherwise
        """
        try:
            data_len = len(data)
            ssl_socket.sendall(data_len.to_bytes(4, byteorder='big'))
            ssl_socket.sendall(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send secure data: {e}")
            return False

    def receive_secure_data(self, ssl_socket: ssl.SSLSocket) -> Optional[bytes]:
        """
        Receive data securely from SSL/TLS socket

        Args:
            ssl_socket: SSL-wrapped socket

        Returns:
            Received data or None if failed
        """
        try:
            len_bytes = ssl_socket.recv(4)
            if not len_bytes:
                return None

            data_len = int.from_bytes(len_bytes, byteorder='big')
            data = b''
            remaining = data_len

            while remaining > 0:
                chunk = ssl_socket.recv(min(remaining, 4096))
                if not chunk:
                    break
                data += chunk
                remaining -= len(chunk)

            return data
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
