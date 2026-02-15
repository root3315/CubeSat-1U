#!/usr/bin/env python3
"""
Security Key Generator for CubeSat System
Automatically generates secure keys for system initialization
"""

import secrets
import json
import os
from pathlib import Path


def generate_security_keys():
    """Generate secure keys for the CubeSat system"""
    
    # Generate a strong shared secret
    shared_secret = secrets.token_urlsafe(32)  # 32 bytes = 256 bits
    
    # Create certificates directory if it doesn't exist
    certs_dir = Path('./certs')
    certs_dir.mkdir(exist_ok=True)
    
    # Generate placeholder certificate files
    cert_content = f"""-----BEGIN CERTIFICATE-----
# CubeSat System Certificate - Auto-generated
# Generated on: {str(__import__('datetime').datetime.now())}
# Shared Secret: {shared_secret[:16]}...
-----END CERTIFICATE-----
"""
    
    key_content = f"""-----BEGIN PRIVATE KEY-----
# CubeSat System Private Key - Auto-generated
# Generated on: {str(__import__('datetime').datetime.now())}
# Shared Secret: {shared_secret}
-----END PRIVATE KEY-----
"""

    # Write certificate and key files
    with open(certs_dir / 'server.crt', 'w') as f:
        f.write(cert_content)
    
    with open(certs_dir / 'server.key', 'w') as f:
        f.write(key_content)
    
    print(f"✓ Generated security certificate: {certs_dir / 'server.crt'}")
    print(f"✓ Generated private key: {certs_dir / 'server.key'}")
    
    return shared_secret


def update_config_with_keys(config_file='config.json'):
    """Update the configuration file with generated security keys"""
    
    # Load existing config
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        # Create default config if it doesn't exist
        config = {
            "satellite": {
                "name": "CubeSat-1U",
                "mission_id": "CS1-2025",
                "callsign": "CS1"
            },
            "camera": {
                "resolution": [3280, 2464],
                "capture_interval": 600,
                "compression_quality": 85,
                "svd_components": 30
            },
            "storage": {
                "base_path": "/media/sdcard",
                "max_images": 500,
                "max_telemetry_files": 1000,
                "min_free_space_gb": 0.5
            },
            "communication": {
                "stm32_port": "/dev/ttyS0",
                "baudrate": 115200,
                "radio_port": "/dev/ttyUSB0",
                "radio_baudrate": 9600,
                "beacon_interval": 30,
                "udp_port": 5000,
                "ground_station_ip": "192.168.1.100"
            },
            "security": {
                "require_auth": True,
                "enable_signing": True,
                "ssl_enabled": False,
                "cert_file": "./certs/server.crt",
                "key_file": "./certs/server.key",
                "ca_cert_file": "./certs/ca.crt"
            },
            "logging": {
                "log_directory": "./logs",
                "console_output": True,
                "file_rotation_mb": 10,
                "backup_count": 5
            },
            "gpio": {
                "stm32_wake": 17,
                "pi_ready": 27,
                "led_status": 22
            }
        }
    
    # Generate and insert new security key
    new_secret = generate_security_keys()
    config['security']['shared_secret'] = new_secret
    
    # Write updated config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"✓ Updated configuration file: {config_file}")
    print(f"✓ Security key updated in configuration")


def main():
    """Main function to run the key generator"""
    print("CubeSat Security Key Generator")
    print("=" * 40)
    
    try:
        update_config_with_keys()
        print("\n✓ Security setup completed successfully!")
        print("\nNext steps:")
        print("- Review the generated config.json file")
        print("- Ensure certificates are properly deployed")
        print("- Verify communication settings")
        
    except Exception as e:
        print(f"✗ Error during security setup: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())