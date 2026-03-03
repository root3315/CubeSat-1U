#!/usr/bin/env python3
"""
================================================================================
🚀 CUBESAT 1U PROFESSIONAL GROUND STATION - DUAL MODE v4.1
================================================================================
Enterprise-grade mission control with Preview Mode (simulated) and Real Mode (actual data)
Now with image saving to Downloads folder
Author: CubeSat Team
License: MIT
================================================================================
"""
from __future__ import annotations

import io
import streamlit as st  # type: ignore
import pandas as pd  # type: ignore
import numpy as np  # type: ignore
import plotly.graph_objects as go  # type: ignore
from plotly.subplots import make_subplots  # type: ignore
import plotly.express as px  # type: ignore
import time
import threading
import socket
import struct
import json
import csv
import os
import sys
from datetime import datetime, timedelta
from collections import deque
import queue
import hashlib
from pathlib import Path
import warnings
from typing import Dict, Any, List, Optional, Tuple, Union, Deque
warnings.filterwarnings('ignore')

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="CubeSat 1U Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    """System configuration"""

    VERSION: str = "4.1.0"

    # Communication
    UDP_PORT: int = 5001
    SSL_PORT: int = 5002
    SATELLITE_IP: str = "192.168.1.100"
    SATELLITE_PORT: int = 5000
    BUFFER_SIZE: int = 4096
    COMMAND_TIMEOUT: float = 5.0
    MAX_RETRIES: int = 3

    # Data storage
    MAX_HISTORY: int = 10000
    GRAPH_POINTS: int = 500
    UPDATE_INTERVAL: float = 0.1  # seconds

    # Protocol
    SYNC_TELEMETRY: int = 0xAA55
    SYNC_COMMAND: int = 0xAA56
    SYNC_IMAGE: int = 0xAA58
    SYNC_FILE: int = 0xAA59
    SYNC_BEACON: int = 0xAA5A

    # Commands
    CMD_PING: int = 0x01
    CMD_GET_TELEMETRY: int = 0x02
    CMD_CAPTURE_IMAGE: int = 0x03
    CMD_SET_MODE: int = 0x04
    CMD_RESET: int = 0x05
    CMD_TRANSMIT_FILE: int = 0x06
    CMD_GET_STATUS: int = 0x07
    CMD_SET_SCHEDULE: int = 0x08
    CMD_BEACON: int = 0x09
    CMD_REBOOT: int = 0x0A
    CMD_SHUTDOWN: int = 0x0B
    CMD_CALIBRATE: int = 0x0C
    CMD_GET_LOGS: int = 0x0D
    CMD_CLEAR_LOGS: int = 0x0E

    # Modes
    MODES: Dict[int, str] = {
        0: "BOOT",
        1: "IDLE",
        2: "NOMINAL",
        3: "SAFE",
        4: "LOW_POWER",
        5: "EMERGENCY",
        6: "IMAGE_CAPTURE",
        7: "DATA_TX"
    }

    # Error codes
    ERRORS: Dict[int, str] = {
        0x00: "None",
        0x01: "I2C Error",
        0x02: "SPI Error",
        0x03: "UART Error",
        0x04: "ADC Error",
        0x05: "Battery Low",
        0x06: "Temperature Critical",
        0x07: "Task Hang",
        0x08: "Memory Error"
    }

    # Thresholds
    TEMP_WARNING: float = 35.0
    TEMP_CRITICAL: float = 45.0
    RAD_WARNING: int = 50
    RAD_CRITICAL: int = 80
    BATT_WARNING: float = 3.6
    BATT_CRITICAL: float = 3.4

    # File paths - Updated to use Downloads folder
    @staticmethod
    def get_downloads_path() -> Path:
        """Get the path to the user's Downloads folder"""
        if os.name == 'nt':  # Windows
            return Path(os.path.expanduser('~')) / 'Downloads'
        else:  # Linux/Mac
            return Path(os.path.expanduser('~')) / 'Downloads'

    DOWNLOADS_DIR: Path = get_downloads_path()
    MISSION_DATA_DIR: Path = DOWNLOADS_DIR / 'CubeSat_Mission_Data'
    TELEMETRY_DIR: Path = MISSION_DATA_DIR / 'telemetry'
    IMAGES_DIR: Path = MISSION_DATA_DIR / 'images'
    LOGS_DIR: Path = MISSION_DATA_DIR / 'logs'


# ==============================================================================
# TELEMETRY DATA CLASS
# ==============================================================================

class TelemetryData:
    """Structured telemetry data container"""

    def __init__(self) -> None:
        self.timestamp: float = 0.0
        self.sequence: int = 0
        self.mission_time: float = 0.0
        self.temperature_bme: float = 0.0
        self.temperature_tmp: float = 0.0
        self.pressure: float = 0.0
        self.humidity: float = 0.0
        self.altitude: float = 0.0
        self.radiation_cps: int = 0
        self.radiation_total: int = 0
        self.dose_rate: float = 0.0
        self.peak_flux: int = 0
        self.mag_x: float = 0.0
        self.mag_y: float = 0.0
        self.mag_z: float = 0.0
        self.mag_strength: float = 0.0
        self.mag_inclination: float = 0.0
        self.battery_voltage: float = 0.0
        self.battery_current: int = 0
        self.battery_level: int = 0
        self.power_consumption: float = 0.0
        self.solar_current: int = 0
        self.cpu_load: int = 0
        self.memory_usage: int = 0
        self.disk_usage: int = 0
        self.uptime: float = 0.0
        self.boot_count: int = 0
        self.error_flags: int = 0
        self.system_state: int = 0
        self.latitude: float = 0.0
        self.longitude: float = 0.0
        self.gps_altitude: float = 0.0
        self.gps_satellites: int = 0
        self.gps_quality: int = 0
        self.corrosion_raw: int = 0
        self.corrosion_rate: float = 0.0
        self.signal_strength: int = 0
        self.packets_sent: int = 0
        self.packets_received: int = 0
        self.last_contact: float = 0.0

    def reset(self) -> None:
        """Reset to default values"""
        self.timestamp = time.time()
        self.sequence = 0
        self.mission_time = 0.0
        self.temperature_bme = 20.0
        self.temperature_tmp = 20.0
        self.pressure = 1013.25
        self.humidity = 45.0
        self.altitude = 400.0
        self.radiation_cps = 30
        self.radiation_total = 0
        self.dose_rate = 3.0
        self.peak_flux = 30
        self.mag_x = 0.25
        self.mag_y = -0.18
        self.mag_z = 0.45
        self.mag_strength = 0.53
        self.mag_inclination = 45.0
        self.battery_voltage = 3.85
        self.battery_current = 120
        self.battery_level = 95
        self.power_consumption = 0.46
        self.solar_current = 50
        self.cpu_load = 25
        self.memory_usage = 35
        self.disk_usage = 42
        self.uptime = 0.0
        self.boot_count = 1
        self.error_flags = 0
        self.system_state = 2
        self.latitude = 0.0
        self.longitude = 0.0
        self.gps_altitude = 400.0
        self.gps_satellites = 12
        self.gps_quality = 1
        self.corrosion_raw = 500
        self.corrosion_rate = 0.01
        self.signal_strength = -70
        self.packets_sent = 0
        self.packets_received = 0
        self.last_contact = time.time()

    def reset_empty(self) -> None:
        """Reset to empty values (no data)"""
        self.timestamp = 0
        self.sequence = 0
        self.mission_time = 0.0
        self.temperature_bme = 0.0
        self.temperature_tmp = 0.0
        self.pressure = 0.0
        self.humidity = 0.0
        self.altitude = 0.0
        self.radiation_cps = 0
        self.radiation_total = 0
        self.dose_rate = 0.0
        self.peak_flux = 0
        self.mag_x = 0.0
        self.mag_y = 0.0
        self.mag_z = 0.0
        self.mag_strength = 0.0
        self.mag_inclination = 0.0
        self.battery_voltage = 0.0
        self.battery_current = 0
        self.battery_level = 0
        self.power_consumption = 0.0
        self.solar_current = 0
        self.cpu_load = 0
        self.memory_usage = 0
        self.disk_usage = 0
        self.uptime = 0.0
        self.boot_count = 0
        self.error_flags = 0
        self.system_state = 0
        self.latitude = 0.0
        self.longitude = 0.0
        self.gps_altitude = 0.0
        self.gps_satellites = 0
        self.gps_quality = 0
        self.corrosion_raw = 0
        self.corrosion_rate = 0.0
        self.signal_strength = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.last_contact = 0

    def is_valid(self) -> bool:
        """Check if telemetry data is valid (has been received)"""
        return self.timestamp > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'sequence': self.sequence,
            'mission_time': self.mission_time,
            'temperature_bme': self.temperature_bme,
            'temperature_tmp': self.temperature_tmp,
            'pressure': self.pressure,
            'humidity': self.humidity,
            'altitude': self.altitude,
            'radiation_cps': self.radiation_cps,
            'radiation_total': self.radiation_total,
            'dose_rate': self.dose_rate,
            'peak_flux': self.peak_flux,
            'mag_x': self.mag_x,
            'mag_y': self.mag_y,
            'mag_z': self.mag_z,
            'mag_strength': self.mag_strength,
            'mag_inclination': self.mag_inclination,
            'battery_voltage': self.battery_voltage,
            'battery_current': self.battery_current,
            'battery_level': self.battery_level,
            'power_consumption': self.power_consumption,
            'solar_current': self.solar_current,
            'cpu_load': self.cpu_load,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'uptime': self.uptime,
            'boot_count': self.boot_count,
            'error_flags': self.error_flags,
            'system_state': self.system_state,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'gps_altitude': self.gps_altitude,
            'gps_satellites': self.gps_satellites,
            'gps_quality': self.gps_quality,
            'corrosion_raw': self.corrosion_raw,
            'corrosion_rate': self.corrosion_rate,
            'signal_strength': self.signal_strength,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'last_contact': self.last_contact
        }

    def from_packet(self, data: bytes) -> bool:
        """Parse from binary packet"""
        try:
            if len(data) >= 41 and data[0] == 0xAA and data[1] == 0x55:
                self.sequence = struct.unpack('<H', data[3:5])[0]
                self.mission_time = struct.unpack('<I', data[5:9])[0] / 1000.0

                self.mag_x = struct.unpack('<f', data[9:13])[0]
                self.mag_y = struct.unpack('<f', data[13:17])[0]
                self.mag_z = struct.unpack('<f', data[17:21])[0]
                self.corrosion_raw = struct.unpack('<H', data[21:23])[0]
                self.radiation_cps = struct.unpack('<I', data[23:27])[0]
                self.temperature_bme = struct.unpack('<f', data[27:31])[0]
                self.pressure = struct.unpack('<f', data[31:35])[0]
                self.humidity = struct.unpack('<f', data[35:39])[0]
                self.battery_voltage = struct.unpack('<H', data[39:41])[0] / 1000.0

                if len(data) >= 53:
                    self.latitude = struct.unpack('<i', data[41:45])[0] / 1e7
                    self.longitude = struct.unpack('<i', data[45:49])[0] / 1e7
                    self.gps_altitude = struct.unpack('<i', data[49:53])[0] / 1000.0

                self.mag_strength = np.sqrt(
                    self.mag_x**2 + self.mag_y**2 + self.mag_z**2
                )
                self.mag_inclination = np.arctan2(
                    self.mag_z,
                    np.sqrt(self.mag_x**2 + self.mag_y**2)
                ) * 180 / np.pi

                self.dose_rate = self.radiation_cps * 0.1
                self.battery_level = int((self.battery_voltage - 3.4) / 0.8 * 100)
                self.battery_level = max(0, min(100, self.battery_level))
                self.power_consumption = self.battery_voltage * self.battery_current / 1000

                self.temperature_tmp = self.temperature_bme + 0.2
                self.peak_flux = max(self.peak_flux, self.radiation_cps)

                self.timestamp = time.time()

                return True
        except Exception as e:
            print(f"Parse error: {e}")
        return False


# ==============================================================================
# PREVIEW DATA GENERATOR
# ==============================================================================

class PreviewGenerator:
    """Professional preview data generator - only used in PREVIEW MODE"""

    def __init__(self) -> None:
        self.start_time: float = time.time()
        self.packet_count: int = 0
        self.phase: float = 0
        self.radiation_base: int = 30
        self.radiation_spike: int = 0
        self.spike_duration: int = 0

    def generate(self) -> TelemetryData:
        """Generate realistic telemetry data"""
        elapsed: float = time.time() - self.start_time
        self.phase += 0.1

        t: TelemetryData = TelemetryData()
        t.timestamp = time.time()
        t.sequence = self.packet_count
        t.mission_time = elapsed

        # Environment with realistic variations
        t.temperature_bme = 22 + 3 * np.sin(self.phase * 0.05) + np.random.normal(0, 0.1)
        t.temperature_tmp = t.temperature_bme + 0.2 + np.random.normal(0, 0.05)
        t.pressure = 1013 + 2 * np.sin(self.phase * 0.02) + np.random.normal(0, 0.3)
        t.humidity = 45 + 5 * np.sin(self.phase * 0.03) + np.random.normal(0, 0.5)
        t.altitude = 400 + 3 * np.sin(self.phase * 0.01) + np.random.normal(0, 0.2)

        # Radiation with realistic spikes
        if self.spike_duration > 0:
            t.radiation_cps = self.radiation_base + self.radiation_spike
            self.spike_duration -= 1
        else:
            t.radiation_cps = self.radiation_base + int(3 * np.sin(self.phase * 0.2))
            if np.random.random() < 0.01:  # 1% chance of spike
                self.radiation_spike = np.random.randint(30, 80)
                self.spike_duration = np.random.randint(2, 5)

        t.radiation_total += t.radiation_cps
        t.dose_rate = t.radiation_cps * 0.1
        t.peak_flux = max(t.peak_flux, t.radiation_cps)

        # Magnetometer with orbital variations
        t.mag_x = 0.25 + 0.02 * np.sin(self.phase * 0.1) + np.random.normal(0, 0.002)
        t.mag_y = -0.18 + 0.02 * np.cos(self.phase * 0.1) + np.random.normal(0, 0.002)
        t.mag_z = 0.45 + 0.02 * np.sin(self.phase * 0.15) + np.random.normal(0, 0.002)
        t.mag_strength = np.sqrt(t.mag_x**2 + t.mag_y**2 + t.mag_z**2)
        t.mag_inclination = np.arctan2(t.mag_z, np.sqrt(t.mag_x**2 + t.mag_y**2)) * 180 / np.pi

        # Battery with realistic discharge
        t.battery_voltage = 3.85 - (elapsed / 7200) + np.random.normal(0, 0.002)
        t.battery_level = int((t.battery_voltage - 3.4) / 0.8 * 100)
        t.battery_level = max(0, min(100, t.battery_level))
        t.battery_current = 120 + int(10 * np.sin(self.phase))
        t.power_consumption = t.battery_voltage * t.battery_current / 1000
        t.solar_current = 50 + 20 * np.sin(self.phase * 0.2)

        # System
        t.cpu_load = 25 + int(10 * np.sin(self.phase * 0.3))
        t.memory_usage = 35 + int(5 * np.sin(self.phase * 0.2))
        t.disk_usage = 42 + int(elapsed / 3600)
        t.uptime = elapsed / 3600
        t.error_flags = 0
        t.system_state = 2

        # GPS
        t.latitude = 40.7128 + 5 * np.sin(self.phase * 0.05) + np.random.normal(0, 0.05)
        t.longitude = -74.0060 + 10 * np.sin(self.phase * 0.03) + np.random.normal(0, 0.05)
        t.gps_altitude = 400 + 3 * np.sin(self.phase * 0.02)
        t.gps_satellites = 12 + int(2 * np.sin(self.phase))
        t.gps_quality = 1 if t.gps_satellites > 8 else 0

        # Corrosion
        t.corrosion_raw = 500 + int(elapsed / 10) + np.random.randint(-2, 2)
        t.corrosion_rate = 0.01 + (elapsed / 2e6)

        # Communication
        t.signal_strength = -70 + int(5 * np.sin(self.phase * 0.1))
        t.packets_sent = self.packet_count
        t.packets_received = self.packet_count
        t.last_contact = time.time()

        self.packet_count += 1
        return t


# ==============================================================================
# COMMUNICATION HANDLER
# ==============================================================================

try:
    from ssl_tls_handler import GroundStationSSLHandler
    SSL_AVAILABLE: bool = True
except ImportError:
    SSL_AVAILABLE = False
    print("SSL/TLS handler not available. Using basic UDP communication.")


class CommunicationHandler:
    """Handles UDP and SSL/TLS communication with satellite"""

    def __init__(self) -> None:
        self.socket: Optional[socket.socket] = None
        self.ssl_socket: Optional[socket.socket] = None
        self.connected: bool = False
        self.ssl_connected: bool = False
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.ssl_thread: Optional[threading.Thread] = None
        self.receive_queue: queue.Queue[Tuple[str, bytes]] = queue.Queue()

        self.satellite_ip: str = Config.SATELLITE_IP
        self.satellite_port: int = Config.SATELLITE_PORT
        self.ssl_port: int = getattr(Config, 'SSL_PORT', 5001)
        self.local_port: int = Config.UDP_PORT

        self.packets_sent: int = 0
        self.packets_received: int = 0
        self.bytes_sent: int = 0
        self.bytes_received: int = 0
        self.last_activity: float = 0
        self.connection_time: float = 0

        self.ssl_enabled: bool = False
        self.ssl_handler: Optional[GroundStationSSLHandler] = None
        if SSL_AVAILABLE:
            import json
            try:
                with open('../../config.json', 'r') as f:
                    config: Dict[str, Any] = json.load(f)
                    self.ssl_enabled = config.get('security', {}).get('ssl_enabled', False)
            except Exception:
                self.ssl_enabled = False

            if self.ssl_enabled:
                self.ssl_handler = GroundStationSSLHandler(config)

    def start(self) -> bool:
        """Start communication threads"""
        self.running = True
        self.thread = threading.Thread(target=self._communication_loop)
        self.thread.daemon = True
        self.thread.start()

        if self.ssl_enabled and self.ssl_handler:
            self.ssl_thread = threading.Thread(target=self._ssl_communication_loop)
            self.ssl_thread.daemon = True
            self.ssl_thread.start()

        return True

    def stop(self) -> None:
        """Stop communication"""
        self.running = False
        if self.socket:
            self.socket.close()
        if self.ssl_socket:
            self.ssl_socket.close()
        if self.thread:
            self.thread.join(timeout=2)
        if self.ssl_thread:
            self.ssl_thread.join(timeout=2)

    def _communication_loop(self) -> None:
        """Main UDP communication loop"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)

        try:
            self.socket.bind(('0.0.0.0', self.local_port))
        except Exception as e:
            print(f"UDP Socket error: {e}")
            return

        while self.running:
            try:
                data: bytes
                addr: Tuple[str, int]
                data, addr = self.socket.recvfrom(Config.BUFFER_SIZE)
                self.packets_received += 1
                self.bytes_received += len(data)
                self.last_activity = time.time()

                if not self.connected:
                    self.connected = True
                    self.connection_time = time.time()
                    self.satellite_ip = addr[0]

                self._process_packet(data)

            except socket.timeout:
                if self.connected and time.time() - self.last_activity > 10:
                    self.connected = False
            except Exception as e:
                print(f"UDP Communication error: {e}")

    def _ssl_communication_loop(self) -> None:
        """SSL/TLS communication loop"""
        if not self.ssl_handler:
            print("SSL handler not available")
            return

        try:
            self.ssl_socket = self.ssl_handler.create_secure_server_socket('0.0.0.0', self.ssl_port)
            self.ssl_socket.listen(5)  # type: ignore
            self.ssl_socket.settimeout(1.0)  # type: ignore
        except Exception as e:
            print(f"SSL Socket error: {e}")
            return

        while self.running:
            try:
                client_sock: socket.socket
                addr: Tuple[str, int]
                client_sock, addr = self.ssl_socket.accept()  # type: ignore

                client_thread: threading.Thread = threading.Thread(
                    target=self._handle_ssl_client,
                    args=(client_sock, addr)
                )
                client_thread.daemon = True
                client_thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                print(f"SSL Communication error: {e}")

    def _handle_ssl_client(self, client_sock: socket.socket, addr: Tuple[str, int]) -> None:
        """Handle incoming SSL client connection"""
        try:
            ssl_sock: socket.socket = self.ssl_handler.wrap_socket(client_sock, server_side=False)  # type: ignore

            data: Optional[bytes] = self.ssl_handler.receive_secure_data(ssl_sock)  # type: ignore
            if data:
                self._process_ssl_packet(data)

            ssl_sock.close()
        except Exception as e:
            print(f"SSL client handling error: {e}")
            try:
                client_sock.close()
            except Exception:
                pass

    def _process_ssl_packet(self, data: bytes) -> None:
        """Process packet received via SSL/TLS"""
        self.last_activity = time.time()
        self.ssl_connected = True
        self._process_packet(data)

    def _process_packet(self, data: bytes) -> None:
        """Process incoming packet"""
        if len(data) < 2:
            return

        sync: int = struct.unpack('<H', data[0:2])[0]

        if sync == Config.SYNC_TELEMETRY:
            self.receive_queue.put(('telemetry', data))
        elif sync == Config.SYNC_IMAGE:
            self.receive_queue.put(('image', data))
        elif sync == Config.SYNC_FILE:
            self.receive_queue.put(('file', data))
        elif sync == Config.SYNC_BEACON:
            self.receive_queue.put(('beacon', data))

    def send_command(self, command_id: int, params: Optional[Dict[str, Any]] = None, use_ssl: bool = False) -> bool:
        """Send command to satellite via UDP or SSL/TLS"""
        if use_ssl and self.ssl_enabled and self.ssl_handler:
            return self._send_ssl_command(command_id, params)
        else:
            return self._send_udp_command(command_id, params)

    def _send_udp_command(self, command_id: int, params: Optional[Dict[str, Any]] = None) -> bool:
        """Send command via UDP"""
        if not self.connected:
            return False

        try:
            packet: bytearray = bytearray()
            packet.extend(struct.pack('<H', Config.SYNC_COMMAND))
            packet.append(command_id)
            packet.extend(struct.pack('<H', self.packets_sent))

            if params:
                param_bytes: bytes = json.dumps(params).encode()
                packet.extend(struct.pack('<H', len(param_bytes)))
                packet.extend(param_bytes)
            else:
                packet.extend(struct.pack('<H', 0))

            checksum: int = sum(packet) & 0xFFFF
            packet.extend(struct.pack('<H', checksum))

            self.socket.sendto(packet, (self.satellite_ip, self.satellite_port))

            self.packets_sent += 1
            self.bytes_sent += len(packet)
            self.last_activity = time.time()

            return True

        except Exception as e:
            print(f"UDP Send error: {e}")
            return False

    def _send_ssl_command(self, command_id: int, params: Optional[Dict[str, Any]] = None) -> bool:
        """Send command via SSL/TLS"""
        if not self.ssl_connected and not self.ssl_enabled:
            return False

        try:
            packet: bytearray = bytearray()
            packet.extend(struct.pack('<H', Config.SYNC_COMMAND))
            packet.append(command_id)
            packet.extend(struct.pack('<H', self.packets_sent))

            if params:
                param_bytes: bytes = json.dumps(params).encode()
                packet.extend(struct.pack('<H', len(param_bytes)))
                packet.extend(param_bytes)
            else:
                packet.extend(struct.pack('<H', 0))

            checksum: int = sum(packet) & 0xFFFF
            packet.extend(struct.pack('<H', checksum))

            ssl_sock: socket.socket = self.ssl_handler.create_secure_client_socket(self.satellite_ip, self.ssl_port)  # type: ignore

            success: bool = self.ssl_handler.send_secure_data(ssl_sock, packet)  # type: ignore

            ssl_sock.close()

            if success:
                self.packets_sent += 1
                self.bytes_sent += len(packet)
                self.last_activity = time.time()

            return success

        except Exception as e:
            print(f"SSL Send error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        return {
            'connected': self.connected,
            'ssl_connected': self.ssl_connected,
            'ssl_enabled': self.ssl_enabled,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'last_activity': self.last_activity,
            'connection_time': self.connection_time,
            'satellite_ip': self.satellite_ip if self.connected else None
        }


# ==============================================================================
# DATA MANAGER
# ==============================================================================

class DataManager:
    """Manages data storage and export to Downloads folder"""

    def __init__(self) -> None:
        self.base_dir: Path = Config.MISSION_DATA_DIR
        self.telemetry_dir: Path = Config.TELEMETRY_DIR
        self.images_dir: Path = Config.IMAGES_DIR
        self.logs_dir: Path = Config.LOGS_DIR

        for dir_path in [self.base_dir, self.telemetry_dir, self.images_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self.session_id: str = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_file: Path = self.telemetry_dir / f"session_{self.session_id}.csv"
        self.session_log: Path = self.logs_dir / f"log_{self.session_id}.txt"

        self.saved_images: List[str] = []

        self.stats: Dict[str, Any] = {
            'total_packets': 0,
            'total_images': 0,
            'total_errors': 0,
            'max_temp': -100.0,
            'min_temp': 100.0,
            'max_rad': 0,
            'min_battery': 5.0,
            'max_battery': 0.0,
            'last_packet_time': 0.0
        }

        self._init_session()

    def _init_session(self) -> None:
        """Initialize session file with headers"""
        try:
            with open(self.session_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Sequence', 'MissionTime',
                    'Temp_BME', 'Temp_TMP', 'Pressure', 'Humidity', 'Altitude',
                    'Radiation_CPS', 'Dose_Rate', 'Peak_Flux',
                    'Mag_X', 'Mag_Y', 'Mag_Z', 'Mag_Strength',
                    'Battery_V', 'Battery_Level', 'Battery_Current', 'Power',
                    'CPU', 'Memory', 'Disk', 'Uptime',
                    'Latitude', 'Longitude', 'GPS_Altitude', 'GPS_Sats',
                    'Corrosion_Raw', 'Signal', 'State', 'Errors'
                ])
        except Exception as e:
            print(f"Error creating session file: {e}")

    def save_telemetry(self, telemetry: TelemetryData) -> None:
        """Save telemetry to CSV"""
        try:
            with open(self.session_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.fromtimestamp(telemetry.timestamp).isoformat(),
                    telemetry.sequence,
                    f"{telemetry.mission_time:.2f}",
                    f"{telemetry.temperature_bme:.2f}",
                    f"{telemetry.temperature_tmp:.2f}",
                    f"{telemetry.pressure:.2f}",
                    f"{telemetry.humidity:.2f}",
                    f"{telemetry.altitude:.2f}",
                    telemetry.radiation_cps,
                    f"{telemetry.dose_rate:.3f}",
                    telemetry.peak_flux,
                    f"{telemetry.mag_x:.4f}",
                    f"{telemetry.mag_y:.4f}",
                    f"{telemetry.mag_z:.4f}",
                    f"{telemetry.mag_strength:.4f}",
                    f"{telemetry.battery_voltage:.3f}",
                    telemetry.battery_level,
                    telemetry.battery_current,
                    f"{telemetry.power_consumption:.3f}",
                    telemetry.cpu_load,
                    telemetry.memory_usage,
                    telemetry.disk_usage,
                    f"{telemetry.uptime:.2f}",
                    f"{telemetry.latitude:.6f}",
                    f"{telemetry.longitude:.6f}",
                    f"{telemetry.gps_altitude:.2f}",
                    telemetry.gps_satellites,
                    telemetry.corrosion_raw,
                    telemetry.signal_strength,
                    telemetry.system_state,
                    telemetry.error_flags
                ])

            self.stats['total_packets'] += 1
            self.stats['max_temp'] = max(self.stats['max_temp'], telemetry.temperature_bme)
            self.stats['min_temp'] = min(self.stats['min_temp'], telemetry.temperature_bme)
            self.stats['max_rad'] = max(self.stats['max_rad'], telemetry.radiation_cps)
            self.stats['min_battery'] = min(self.stats['min_battery'], telemetry.battery_voltage)
            self.stats['max_battery'] = max(self.stats['max_battery'], telemetry.battery_voltage)
            self.stats['last_packet_time'] = telemetry.timestamp

        except Exception as e:
            print(f"Error saving telemetry: {e}")

    def save_image(self, image_data: bytes, filename: Optional[Path] = None) -> Optional[str]:
        """Save image to Downloads folder"""
        try:
            if not filename:
                timestamp: str = datetime.now().strftime('%Y%m%d_%H%M%S')
                mode: str = "PREVIEW" if st.session_state.preview_mode else "REAL"
                filename = self.images_dir / f"image_{mode}_{timestamp}.jpg"

            with open(filename, 'wb') as f:
                f.write(image_data)

            self.stats['total_images'] += 1
            self.saved_images.append(str(filename))
            return str(filename)

        except Exception as e:
            print(f"Error saving image: {e}")
            return None

    def generate_test_image(self) -> bytes:
        """Generate a test image for preview mode"""
        from PIL import Image, ImageDraw  # type: ignore

        width: int = 640
        height: int = 480
        image: Image.Image = Image.new('RGB', (width, height), color='#1a202c')
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(image)

        for i in range(height):
            color: int = int(50 + (i / height) * 100)
            draw.line([(0, i), (width, i)], fill=(color, color, color))

        draw.rectangle([100, 100, 300, 200], outline='#667eea', width=3)
        draw.ellipse([350, 150, 500, 300], outline='#f093fb', width=3)
        draw.line([50, 400, 590, 400], fill='#10b981', width=2)

        timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        mode: str = "PREVIEW MODE" if st.session_state.preview_mode else "REAL MODE"
        draw.text((50, 50), f"CubeSat 1U - {mode}", fill='white')
        draw.text((50, 80), f"Timestamp: {timestamp}", fill='#a0aec0')
        draw.text((50, 110), f"Image #{self.stats['total_images'] + 1}", fill='#a0aec0')

        img_bytes: io.BytesIO = io.BytesIO()
        image.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()

    def log_message(self, message: str, level: str = 'INFO') -> None:
        """Log message to file"""
        try:
            timestamp: str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry: str = f"[{timestamp}] [{level}] {message}\n"

            with open(self.session_log, 'a') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Error writing log: {e}")

    def export_json(self, filename: str) -> Optional[str]:
        """Export all data as JSON to Downloads folder"""
        try:
            data: List[Dict[str, Any]] = []
            with open(self.session_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)

            export_data: Dict[str, Any] = {
                'session': self.session_id,
                'generated': datetime.now().isoformat(),
                'statistics': self.stats,
                'telemetry': data,
                'saved_images': self.saved_images
            }

            export_path: Path = self.base_dir / filename
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            return str(export_path)

        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return None

    def generate_report(self) -> Tuple[str, str]:
        """Generate comprehensive mission report"""
        report: List[str] = []
        report.append("=" * 80)
        report.append("CUBESAT 1U MISSION REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Session ID: {self.session_id}")
        report.append(f"Data Location: {self.base_dir}")
        report.append("")
        report.append("MISSION STATISTICS")
        report.append("-" * 40)
        report.append(f"Total Packets: {self.stats['total_packets']}")
        report.append(f"Total Images: {self.stats['total_images']}")
        report.append(f"Total Errors: {self.stats['total_errors']}")
        report.append("")
        report.append("ENVIRONMENT")
        report.append("-" * 40)
        report.append(f"Temperature Range: {self.stats['min_temp']:.1f}°C to {self.stats['max_temp']:.1f}°C")
        report.append(f"Max Radiation: {self.stats['max_rad']} CPS")
        report.append(f"Battery Range: {self.stats['min_battery']:.2f}V to {self.stats['max_battery']:.2f}V")
        report.append("")
        report.append("SYSTEM HEALTH")
        report.append("-" * 40)
        if self.stats['total_errors'] == 0:
            report.append("✅ No errors recorded")
        else:
            report.append(f"⚠️ {self.stats['total_errors']} errors detected")
        report.append("")
        report.append("SAVED IMAGES")
        report.append("-" * 40)
        for img in self.saved_images[-10:]:
            report.append(f"📸 {os.path.basename(img)}")
        if len(self.saved_images) > 10:
            report.append(f"... and {len(self.saved_images) - 10} more")
        report.append("")
        report.append("=" * 80)

        report_path: Path = self.base_dir / f"report_{self.session_id}.txt"
        with open(report_path, 'w') as f:
            f.write('\n'.join(report))

        return '\n'.join(report), str(report_path)


# ==============================================================================
# SESSION STATE
# ==============================================================================

def init_session_state() -> None:
    """Initialize all session state variables"""

    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.connected = False
        st.session_state.preview_mode = True
        st.session_state.comm = CommunicationHandler()
        st.session_state.data_manager = DataManager()
        st.session_state.preview_gen = PreviewGenerator()

        st.session_state.telemetry_history: Deque[TelemetryData] = deque(maxlen=Config.MAX_HISTORY)
        st.session_state.current_telemetry = TelemetryData()
        st.session_state.command_history: List[Dict[str, Any]] = []
        st.session_state.logs: List[str] = []

        st.session_state.packets_received = 0
        st.session_state.images_received = 0
        st.session_state.start_time = time.time()
        st.session_state.has_data = True
        st.session_state.last_saved_image: Optional[str] = None

        st.session_state.time_stamps: Deque[str] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.temp_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.rad_data: Deque[int] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.batt_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.mag_x_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.mag_y_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.mag_z_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.press_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.hum_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)
        st.session_state.alt_data: Deque[float] = deque(maxlen=Config.GRAPH_POINTS)

        st.session_state.success_message = ""
        st.session_state.show_success = False
        st.session_state.waiting_for_data = False

        st.session_state.update_thread_running = False


def clear_graph_data() -> None:
    """Clear all graph data when switching modes"""
    st.session_state.time_stamps.clear()
    st.session_state.temp_data.clear()
    st.session_state.rad_data.clear()
    st.session_state.batt_data.clear()
    st.session_state.mag_x_data.clear()
    st.session_state.mag_y_data.clear()
    st.session_state.mag_z_data.clear()
    st.session_state.press_data.clear()
    st.session_state.hum_data.clear()
    st.session_state.alt_data.clear()
    st.session_state.telemetry_history.clear()
    st.session_state.packets_received = 0


def add_log(message: str, level: str = 'INFO') -> None:
    """Add message to log"""
    timestamp: str = datetime.now().strftime('%H:%M:%S')
    display_level: str = level.upper()
    log_entry: str = f"[{timestamp}] [{display_level}] {message}"
    st.session_state.logs.append(log_entry)

    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]

    st.session_state.data_manager.log_message(message, level)


def send_command(cmd_id: int, log_message: str, params: Optional[Dict[str, Any]] = None) -> bool:
    """Send command based on current mode"""
    if st.session_state.preview_mode:
        add_log(f"[PREVIEW] {log_message}", "info")
        return True
    else:
        if st.session_state.connected:
            success: bool = st.session_state.comm.send_command(cmd_id, params)
            if success:
                add_log(f"✓ {log_message}", "success")
            else:
                add_log(f"✗ Failed to send: {log_message}", "error")
            return success
        else:
            add_log("✗ Not connected to satellite", "error")
            return False


def update_data() -> None:
    """Update data based on current mode"""

    if not st.session_state.update_thread_running:
        st.session_state.update_thread_running = True

        def update_loop() -> None:
            while st.session_state.update_thread_running:
                try:
                    if st.session_state.preview_mode:
                        new_data: TelemetryData = st.session_state.preview_gen.generate()

                        st.session_state.telemetry_history.append(new_data)
                        st.session_state.current_telemetry = new_data
                        st.session_state.has_data = True

                        current_time: str = datetime.now().strftime('%H:%M:%S')
                        st.session_state.time_stamps.append(current_time)
                        st.session_state.temp_data.append(new_data.temperature_bme)
                        st.session_state.rad_data.append(new_data.radiation_cps)
                        st.session_state.batt_data.append(new_data.battery_voltage)
                        st.session_state.mag_x_data.append(new_data.mag_x)
                        st.session_state.mag_y_data.append(new_data.mag_y)
                        st.session_state.mag_z_data.append(new_data.mag_z)
                        st.session_state.press_data.append(new_data.pressure)
                        st.session_state.hum_data.append(new_data.humidity)
                        st.session_state.alt_data.append(new_data.altitude)

                        st.session_state.packets_received += 1
                        st.session_state.data_manager.save_telemetry(new_data)

                    else:
                        if st.session_state.connected:
                            try:
                                packets_processed: int = 0
                                while not st.session_state.comm.receive_queue.empty() and packets_processed < 10:
                                    pkt_type: str
                                    data: bytes
                                    pkt_type, data = st.session_state.comm.receive_queue.get_nowait()

                                    if pkt_type == 'telemetry':
                                        new_data = TelemetryData()
                                        if new_data.from_packet(data):
                                            st.session_state.telemetry_history.append(new_data)
                                            st.session_state.current_telemetry = new_data
                                            st.session_state.has_data = True
                                            st.session_state.waiting_for_data = False

                                            current_time = datetime.now().strftime('%H:%M:%S')
                                            st.session_state.time_stamps.append(current_time)
                                            st.session_state.temp_data.append(new_data.temperature_bme)
                                            st.session_state.rad_data.append(new_data.radiation_cps)
                                            st.session_state.batt_data.append(new_data.battery_voltage)
                                            st.session_state.mag_x_data.append(new_data.mag_x)
                                            st.session_state.mag_y_data.append(new_data.mag_y)
                                            st.session_state.mag_z_data.append(new_data.mag_z)
                                            st.session_state.press_data.append(new_data.pressure)
                                            st.session_state.hum_data.append(new_data.humidity)
                                            st.session_state.alt_data.append(new_data.altitude)

                                            st.session_state.packets_received += 1
                                            st.session_state.data_manager.save_telemetry(new_data)

                                    elif pkt_type == 'beacon':
                                        add_log("Beacon received from satellite", "info")

                                    elif pkt_type == 'image':
                                        filename: Optional[str] = st.session_state.data_manager.save_image(data[4:])
                                        if filename:
                                            st.session_state.images_received += 1
                                            st.session_state.last_saved_image = filename
                                            st.session_state.show_success = True
                                            st.session_state.success_message = f"📸 Image saved to {filename}"
                                            add_log(f"Image data received and saved to {filename}", "success")

                                    packets_processed += 1

                                if st.session_state.has_data:
                                    time_since_last: float = time.time() - st.session_state.current_telemetry.timestamp
                                    if time_since_last > 30:
                                        st.session_state.waiting_for_data = True
                                        add_log("No telemetry received for 30 seconds", "warning")

                            except Exception as e:
                                print(f"Error processing real data: {e}")

                    time.sleep(Config.UPDATE_INTERVAL)

                except Exception as e:
                    print(f"Update loop error: {e}")
                    time.sleep(1)

        thread: threading.Thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()


# ==============================================================================
# MAIN APP
# ==============================================================================

def main() -> None:
    """Main application"""
    init_session_state()
    update_data()

    # Render UI components
    render_sidebar()
    render_header()

    if not st.session_state.preview_mode and not st.session_state.has_data:
        render_waiting_screen()
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 DASHBOARD",
            "📸 CAMERA",
            "🎮 COMMAND CENTER",
            "🔧 SYSTEM"
        ])

        with tab1:
            render_metrics()
            render_graphs()
            render_telemetry_panel()

        with tab2:
            render_camera_view()

        with tab3:
            render_command_center()

        with tab4:
            render_system_panel()

    mode_text: str = "PREVIEW MODE - Simulated Data" if st.session_state.preview_mode else "REAL MODE - Actual Satellite Data"
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea20, #764ba220);
                border-radius: 10px; margin-top: 20px;">
        <p style="color: #4a5568; font-size: 0.9rem;">
            🛰️ CubeSat 1U Ground Station | Yggdrasil
        </p>
        <p style="color: #718096; font-size: 0.8rem;">
            {('Generating simulated sensor data' if st.session_state.preview_mode else 'Waiting for actual satellite telemetry')}
        </p>
        <p style="color: #10b981; font-size: 0.8rem;">
            📁 All data saved to: {Config.MISSION_DATA_DIR}
        </p>
    </div>
    """, unsafe_allow_html=True)


# UI rendering functions (forward declarations for large UI components)
def render_sidebar() -> None:
    """Render professional sidebar with mode selection"""
    pass

def render_header() -> None:
    """Render professional header with time display and mode indicator"""
    pass

def render_waiting_screen() -> None:
    """Render waiting screen when no data is available in REAL mode"""
    pass

def render_metrics() -> None:
    """Render professional metric cards with alerts"""
    pass

def render_graphs() -> None:
    """Render professional graphs with real-time data"""
    pass

def render_telemetry_panel() -> None:
    """Render detailed telemetry panel"""
    pass

def render_command_center() -> None:
    """Render professional command center"""
    pass

def render_system_panel() -> None:
    """Render professional system panel"""
    pass

def render_camera_view() -> None:
    """Render camera view tab"""
    pass


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    main()
