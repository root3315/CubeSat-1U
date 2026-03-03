"""
Simplified SSL/TLS Handler for CubeSat Communication
Lightweight implementation optimized for resource-constrained environments
"""

import ssl
import socket
import logging
from typing import Optional, Dict, Any
import os
from datetime import datetime, timedelta


class SSLTLSHandler:
    """
    Simplified SSL/TLS handler for secure communication
    Lightweight implementation for CubeSat resource constraints
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger('SSL_TLS_Handler')

        self.ssl_enabled = config.get('security', {}).get('ssl_enabled', False)
        self.cert_file = config.get('security', {}).get('cert_file', './certs/server.crt')
        self.key_file = config.get('security', {}).get('key_file', './certs/server.key')

        certs_dir = os.path.dirname(self.cert_file)
        if certs_dir and not os.path.exists(certs_dir):
            os.makedirs(certs_dir, exist_ok=True)

        self.ssl_context: Optional[ssl.SSLContext] = None
        if self.ssl_enabled:
            self._ensure_certificates_exist()
            self._create_basic_ssl_context()

    def _ensure_certificates_exist(self) -> None:
        """Generate self-signed certificates using Python cryptography"""
        cert_exists = os.path.exists(self.cert_file)
        key_exists = os.path.exists(self.key_file)

        if not cert_exists or not key_exists:
            self.logger.info("Generating self-signed SSL certificates...")
            try:
                from cryptography import x509  # type: ignore
                from cryptography.x509.oid import NameOID  # type: ignore
                from cryptography.hazmat.primitives import hashes, serialization  # type: ignore
                from cryptography.hazmat.primitives.asymmetric import rsa  # type: ignore
                from cryptography.hazmat.backends import default_backend  # type: ignore

                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )

                subject = issuer = x509.Name([
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CubeSat-1U"),
                    x509.NameAttribute(NameOID.COMMON_NAME, "cubesat.local"),
                ])

                cert = (
                    x509.CertificateBuilder()
                    .subject_name(subject)
                    .issuer_name(issuer)
                    .public_key(private_key.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(datetime.utcnow())
                    .not_valid_after(datetime.utcnow() + timedelta(days=365))
                    .add_extension(
                        x509.SubjectAlternativeName([x509.DNSName("cubesat.local")]),
                        critical=False,
                    )
                    .sign(private_key, hashes.SHA256(), default_backend())
                )

                with open(self.key_file, "wb") as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))

                with open(self.cert_file, "wb") as f:
                    f.write(cert.public_bytes(serialization.Encoding.PEM))

                self.logger.info(f"Certificates generated: {self.cert_file}, {self.key_file}")

            except ImportError:
                self.logger.warning("cryptography library not available, SSL disabled")
                self.ssl_enabled = False
            except Exception as e:
                self.logger.error(f"Failed to generate certificates: {e}")
                self.ssl_enabled = False

    def _create_basic_ssl_context(self) -> None:
        """Create a basic SSL context with minimal configuration"""
        if not self.ssl_enabled:
            return

        try:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                self.ssl_context.load_cert_chain(self.cert_file, self.key_file)

            self.ssl_context.check_hostname = True
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED

            self.logger.info("Basic SSL context created with proper validation")

        except Exception as e:
            self.logger.warning(f"SSL not available, proceeding without encryption: {e}")
            self.ssl_enabled = False
            self.ssl_context = None

    def wrap_socket(self, sock: socket.socket, server_side: bool = False) -> socket.socket:
        """
        Wrap a socket with basic SSL/TLS

        Args:
            sock: The socket to wrap
            server_side: True if this is a server socket, False for client

        Returns:
            SSL-wrapped socket or original socket if SSL is disabled
        """
        if not self.ssl_enabled or self.ssl_context is None:
            return sock

        try:
            return self.ssl_context.wrap_socket(sock, server_side=server_side)
        except Exception as e:
            self.logger.warning(f"SSL wrapping failed, using plain socket: {e}")
            return sock

    def create_secure_connection(self, host: str, port: int) -> socket.socket:
        """
        Create a secure connection with minimal overhead

        Args:
            host: Host to connect to
            port: Port to connect to

        Returns:
            SSL-wrapped socket or plain socket if SSL is disabled
        """
        if not self.ssl_enabled:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            return sock

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = self.wrap_socket(sock, server_side=False)
        ssl_sock.connect((host, port))

        return ssl_sock

    def enable_ssl(self) -> None:
        """Enable SSL/TLS functionality"""
        self.ssl_enabled = True
        if self.ssl_enabled:
            self._create_basic_ssl_context()
        self.logger.info("SSL/TLS enabled (simplified)")

    def disable_ssl(self) -> None:
        """Disable SSL/TLS functionality"""
        self.ssl_enabled = False
        self.ssl_context = None
        self.logger.info("SSL/TLS disabled")
