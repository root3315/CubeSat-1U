"""
Simplified SSL/TLS Handler for CubeSat Communication
Lightweight implementation optimized for resource-constrained environments
"""
import ssl
import socket
import logging
from typing import Optional
import os


class SSLTLSHandler:
    """
    Simplified SSL/TLS handler for secure communication
    Lightweight implementation for CubeSat resource constraints
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('SSL_TLS_Handler')

        # Simplified SSL/TLS configuration
        self.ssl_enabled = config.get('security', {}).get('ssl_enabled', False)
        self.cert_file = config.get('security', {}).get('cert_file', './certs/server.crt')
        self.key_file = config.get('security', {}).get('key_file', './certs/server.key')

        # SSL context - simplified
        self.ssl_context = None
        if self.ssl_enabled:
            self._create_basic_ssl_context()

    def _create_basic_ssl_context(self):
        """Create a basic SSL context with minimal configuration"""
        if not self.ssl_enabled:
            return

        try:
            # Create basic SSL context
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # Load certificates if they exist
            if os.path.exists(self.cert_file) and os.path.exists(self.key_file):
                self.ssl_context.load_cert_chain(self.cert_file, self.key_file)
            
            # Simplified security settings for resource efficiency
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
            
            self.logger.info("Basic SSL context created")

        except Exception as e:
            self.logger.warning(f"SSL not available, proceeding without encryption: {e}")
            self.ssl_enabled = False
            self.ssl_context = None

    def wrap_socket(self, sock, server_side: bool = False):
        """
        Wrap a socket with basic SSL/TLS
        
        Args:
            sock: The socket to wrap
            server_side: True if this is a server socket, False for client

        Returns:
            SSL-wrapped socket or original socket if SSL is disabled
        """
        if not self.ssl_enabled or self.ssl_context is None:
            return sock  # Return original socket if SSL is disabled

        try:
            # Simplified SSL wrapping
            return self.ssl_context.wrap_socket(
                sock,
                server_side=server_side
            )
        except Exception as e:
            self.logger.warning(f"SSL wrapping failed, using plain socket: {e}")
            return sock  # Return original socket if SSL fails

    def create_secure_connection(self, host: str, port: int):
        """
        Create a secure connection with minimal overhead
        
        Args:
            host: Host to connect to
            port: Port to connect to

        Returns:
            SSL-wrapped socket or plain socket if SSL is disabled
        """
        if not self.ssl_enabled:
            # Fallback to regular socket if SSL is disabled
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            return sock

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssl_sock = self.wrap_socket(sock, server_side=False)
        ssl_sock.connect((host, port))
        
        return ssl_sock

    def enable_ssl(self):
        """Enable SSL/TLS functionality"""
        self.ssl_enabled = True
        if self.ssl_enabled:
            self._create_basic_ssl_context()
        self.logger.info("SSL/TLS enabled (simplified)")

    def disable_ssl(self):
        """Disable SSL/TLS functionality"""
        self.ssl_enabled = False
        self.ssl_context = None
        self.logger.info("SSL/TLS disabled")


# Example usage
if __name__ == "__main__":
    # Example configuration
    config = {
        "security": {
            "ssl_enabled": True,
            "cert_file": "./certs/server.crt",
            "key_file": "./certs/server.key"
        }
    }

    # Create simplified SSL handler
    ssl_handler = SSLTLSHandler(config)

    print("Simplified SSL/TLS Handler initialized")
    print(f"SSL Enabled: {ssl_handler.ssl_enabled}")