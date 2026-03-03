#!/usr/bin/env python3
"""
Simplified Communication handler for CubeSat
Lightweight implementation optimized for resource-constrained environments
"""
import os
import json
import time
import struct
import logging
import threading
import queue
import socket
from typing import Optional, Dict, Any, List, Tuple

try:
    import serial  # type: ignore
except ImportError:
    serial = None  # type: ignore

from security import SecurityManager, validate_secure_command, create_secure_command


class CommunicationHandler:
    """Handles communication interfaces with minimal overhead"""

    SYNC_TELEMETRY = 0xAA55
    SYNC_COMMAND = 0xAA56
    SYNC_IMAGE = 0xAA58
    SYNC_FILE = 0xAA59

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger('Communication')

        self.stm32_serial: Optional[Any] = None
        self.radio_serial: Optional[Any] = None
        self.udp_socket: Optional[socket.socket] = None

        self.command_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.telemetry_queue: queue.Queue[Dict[str, Any]] = queue.Queue()

        self.rate_limit_window = 60
        self.rate_limit_max_commands = 100
        self.command_timestamps: List[float] = []
        self.rate_limit_lock = threading.Lock()

        self.security_manager = SecurityManager(
            shared_secret=config.get('security', {}).get('shared_secret', 'default_secret_key')
        )

        self.init_serial_ports()
        self.init_network_socket()

        self.running = True
        self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
        self.reader_thread.start()

    def init_serial_ports(self) -> None:
        """Initialize serial connections"""
        if serial is None:
            self.logger.warning("pyserial not installed, serial ports unavailable")
            return

        try:
            self.stm32_serial = serial.Serial(
                port=self.config['communication']['stm32_port'],
                baudrate=self.config['communication']['baudrate'],
                timeout=0.1
            )
            self.logger.info(f"STM32 serial connected on {self.config['communication']['stm32_port']}")
        except Exception as e:
            self.logger.error(f"Failed to connect to STM32: {e}")
            self.stm32_serial = None

        try:
            self.radio_serial = serial.Serial(
                port=self.config['communication']['radio_port'],
                baudrate=self.config['communication']['radio_baudrate'],
                timeout=0.1
            )
            self.logger.info(f"Radio serial connected on {self.config['communication']['radio_port']}")
        except Exception as e:
            self.logger.warning(f"Radio not connected: {e}")
            self.radio_serial = None

    def init_network_socket(self) -> None:
        """Initialize network socket for UDP communication"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_port = self.config.get('communication', {}).get('udp_port', 5000)
            self.udp_socket.bind(('', udp_port))
            self.udp_socket.settimeout(0.1)
            self.logger.info(f"UDP socket bound to port {udp_port}")
        except Exception as e:
            self.logger.error(f"Failed to initialize UDP socket: {e}")
            self.udp_socket = None

    def reader_loop(self) -> None:
        """Read from all communication interfaces"""
        while self.running:
            if self.stm32_serial and self.stm32_serial.in_waiting:
                data = self.stm32_serial.read(self.stm32_serial.in_waiting)
                self.process_stm32_data(data)

            if self.radio_serial and self.radio_serial.in_waiting:
                data = self.radio_serial.read(self.radio_serial.in_waiting)
                self.process_radio_data(data)

            if self.udp_socket:
                try:
                    data, addr = self.udp_socket.recvfrom(4096)
                    self.process_udp_data(data, addr)
                except socket.timeout:
                    pass
                except Exception as e:
                    if "Resource temporarily unavailable" not in str(e):
                        self.logger.error(f"UDP receive error: {e}")

            time.sleep(0.01)

    def process_udp_data(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Process data received via UDP"""
        try:
            packets = self.parse_incoming_data(data)

            for packet in packets:
                if packet['type'] == 'telemetry':
                    self.telemetry_queue.put(packet['data'])
                elif packet['type'] == 'command':
                    if 'signature' in packet['data'] and 'nonce' in packet['data']:
                        success, msg = validate_secure_command(packet['data'], self.security_manager)
                        if success:
                            self.command_queue.put(packet['data'])
                            self.logger.info(f"Secure command validated: {msg}")
                        else:
                            self.logger.error(f"Command validation failed: {msg}")
                    else:
                        if self.config.get('security', {}).get('require_auth', False):
                            self.logger.warning("Unsigned command rejected due to security policy")
                        else:
                            self.command_queue.put(packet['data'])
        except Exception as e:
            self.logger.error(f"Error processing UDP data: {e}")

    def process_stm32_data(self, data: bytes) -> None:
        """Process data from STM32"""
        packets = self.parse_incoming_data(data)

        for packet in packets:
            if packet['type'] == 'telemetry':
                self.telemetry_queue.put(packet['data'])
            elif packet['type'] == 'command':
                self.command_queue.put(packet['data'])

    def process_radio_data(self, data: bytes) -> None:
        """Process data from radio (ground station)"""
        try:
            text = data.decode('utf-8').strip()
            if text.startswith('{'):
                command = json.loads(text)

                if 'signature' in command and 'nonce' in command:
                    success, msg = validate_secure_command(command, self.security_manager)
                    if success:
                        self.command_queue.put(command)
                        self.logger.info(f"Secure command validated: {msg}")
                    else:
                        self.logger.error(f"Command validation failed: {msg}")
                else:
                    if self.config.get('security', {}).get('require_auth', False):
                        self.logger.warning("Unsigned command rejected due to security policy")
                    else:
                        self.command_queue.put(command)
            else:
                packets = self.parse_incoming_data(data)
                for packet in packets:
                    if packet['type'] == 'command':
                        command_data = packet['data']

                        if 'signature' in command_data and 'nonce' in command_data:
                            success, msg = validate_secure_command(command_data, self.security_manager)
                            if success:
                                self.command_queue.put(command_data)
                                self.logger.info(f"Binary command validated: {msg}")
                            else:
                                self.logger.error(f"Binary command validation failed: {msg}")
                        else:
                            if self.config.get('security', {}).get('require_auth', False):
                                self.logger.warning("Unsigned binary command rejected due to security policy")
                            else:
                                self.command_queue.put(command_data)

        except Exception as e:
            self.logger.error(f"Error processing radio data: {e}")

    def parse_incoming_data(self, data: bytes) -> List[Dict[str, Any]]:
        """Parse incoming binary data with input validation"""
        packets: List[Dict[str, Any]] = []
        i = 0

        MAX_PARAM_LENGTH = 256
        MAX_IMAGE_CHUNK_SIZE = 4096

        while i < len(data) - 1:
            if i + 2 > len(data):
                break
            sync = struct.unpack('<H', data[i:i+2])[0]

            if sync == self.SYNC_TELEMETRY:
                if i + 40 <= len(data):
                    packet = self.parse_telemetry(data[i:i+40])
                    packets.append({'type': 'telemetry', 'data': packet})
                    i += 40
                else:
                    break

            elif sync == self.SYNC_COMMAND:
                if i + 8 <= len(data):
                    cmd_id = data[i+2]
                    seq = struct.unpack('<H', data[i+3:i+5])[0]
                    param_len = struct.unpack('<H', data[i+5:i+7])[0]

                    if param_len > MAX_PARAM_LENGTH or param_len < 0:
                        self.logger.error(f"Invalid parameter length {param_len}")
                        i += 1
                        continue

                    if i + 8 + param_len <= len(data):
                        params = data[i+8:i+8+param_len]
                        try:
                            params_dict = json.loads(params.decode())
                        except Exception:
                            params_dict = {'raw': params.hex()}

                        packets.append({
                            'type': 'command',
                            'data': {
                                'id': cmd_id,
                                'sequence': seq,
                                'params': params_dict
                            }
                        })
                        i += 8 + param_len
                    else:
                        break
                else:
                    break

            elif sync == self.SYNC_IMAGE:
                if i + 7 <= len(data):
                    chunk_num = struct.unpack('<H', data[i+2:i+4])[0]
                    data_len = struct.unpack('<H', data[i+4:i+6])[0]

                    if data_len > MAX_IMAGE_CHUNK_SIZE or data_len < 0:
                        self.logger.error(f"Invalid image chunk size {data_len}")
                        i += 1
                        continue

                    if i + 7 + data_len <= len(data):
                        image_data = data[i+7:i+7+data_len]
                        packets.append({
                            'type': 'image_chunk',
                            'data': {
                                'chunk': chunk_num,
                                'data': image_data
                            }
                        })
                        i += 7 + data_len
                    else:
                        break
                else:
                    break
            else:
                i += 1

        return packets

    def parse_telemetry(self, data: bytes) -> Dict[str, Any]:
        """Parse telemetry packet"""
        try:
            result: Dict[str, Any] = {
                'sync1': data[0],
                'sync2': data[1],
                'packet_type': data[2],
                'sequence': struct.unpack('<H', data[3:5])[0],
                'timestamp': struct.unpack('<I', data[5:9])[0],
                'mag_x': struct.unpack('<f', data[9:13])[0],
                'mag_y': struct.unpack('<f', data[13:17])[0],
                'mag_z': struct.unpack('<f', data[17:21])[0],
                'corrosion_raw': struct.unpack('<H', data[21:23])[0],
                'radiation_cps': struct.unpack('<I', data[23:27])[0],
                'temperature_bme': struct.unpack('<f', data[27:31])[0],
                'pressure': struct.unpack('<f', data[31:35])[0],
                'humidity': struct.unpack('<f', data[35:39])[0],
            }
            if len(data) >= 41:
                result['checksum'] = struct.unpack('<H', data[39:41])[0]
            return result
        except Exception as e:
            self.logger.error(f"Telemetry parse error: {e}")
            return {}

    def send_to_stm32(self, data: Any) -> bool:
        """Send data to STM32"""
        if not self.stm32_serial:
            self.logger.error("STM32 serial not available")
            return False

        try:
            if isinstance(data, dict):
                if 'command_id' in data and self.config.get('security', {}).get('enable_signing', True):
                    secure_cmd = create_secure_command(
                        command_id=data.get('command_id'),
                        params=data.get('params', {}),
                        security_manager=self.security_manager
                    )
                    cmd_data = self.build_command_packet(secure_cmd)
                else:
                    cmd_data = self.build_command_packet(data)

                self.stm32_serial.write(cmd_data)
            else:
                self.stm32_serial.write(data)

            return True
        except Exception as e:
            self.logger.error(f"Error sending to STM32: {e}")
            return False

    def send_to_radio(self, data: Any) -> bool:
        """Send data to radio (ground station)"""
        if not self.radio_serial:
            self.logger.warning("Radio serial not available")
            return False

        try:
            if isinstance(data, dict):
                json_str = json.dumps(data) + '\n'
                self.radio_serial.write(json_str.encode())
            else:
                self.radio_serial.write(data)

            return True
        except Exception as e:
            self.logger.error(f"Error sending to radio: {e}")
            return False

    def send_to_ground_station(self, data: Any) -> bool:
        """Send data to ground station via UDP"""
        try:
            ground_ip = self.config.get('communication', {}).get('ground_station_ip', '127.0.0.1')
            udp_port = self.config.get('communication', {}).get('udp_port', 5001)

            if isinstance(data, dict):
                json_data = json.dumps(data).encode()
                self.udp_socket.sendto(json_data, (ground_ip, udp_port))
            else:
                self.udp_socket.sendto(data, (ground_ip, udp_port))
            return True
        except Exception as e:
            self.logger.error(f"Error sending via UDP: {e}")
            return False

    def send_file_to_ground(self, filename: str, chunk_size: int = 256) -> bool:
        """Send a file to ground station in chunks"""
        if not self.radio_serial:
            self.logger.error("Radio not available")
            return False

        try:
            file_size = os.path.getsize(filename)
            num_chunks = (file_size + chunk_size - 1) // chunk_size

            self.logger.info(f"Sending file {filename} ({num_chunks} chunks)")

            with open(filename, 'rb') as f:
                for chunk_num in range(num_chunks):
                    chunk_data = f.read(chunk_size)

                    packet = struct.pack('<HHH',
                                        self.SYNC_FILE,
                                        chunk_num,
                                        len(chunk_data))
                    packet += chunk_data

                    self.radio_serial.write(packet)
                    time.sleep(0.05)

            self.logger.info(f"File sent successfully: {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Error sending file: {e}")
            return False

    def build_command_packet(self, command: Dict[str, Any]) -> bytes:
        """Build a command packet for STM32"""
        packet = bytearray()
        packet.extend(struct.pack('<H', self.SYNC_COMMAND))
        packet.append(command.get('id', 0))
        packet.extend(struct.pack('<H', command.get('sequence', 0)))

        params = command.get('params', {})
        params_json = json.dumps(params).encode()
        packet.extend(struct.pack('<H', len(params_json)))
        packet.extend(params_json)

        return bytes(packet)

    def cleanup(self) -> None:
        """Close serial ports with proper error handling"""
        self.running = False

        if hasattr(self, 'reader_thread') and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=2.0)

        if self.stm32_serial:
            try:
                self.stm32_serial.cancel_read()
            except Exception:
                pass
            try:
                self.stm32_serial.close()
            except Exception as e:
                self.logger.error(f"Error closing STM32 serial: {e}")

        if self.radio_serial:
            try:
                self.radio_serial.cancel_read()
            except Exception:
                pass
            try:
                self.radio_serial.close()
            except Exception as e:
                self.logger.error(f"Error closing radio serial: {e}")

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing UDP socket: {e}")

        self.logger.info("Communication handler cleaned up")

    def _check_rate_limit(self) -> bool:
        """Check if command rate is within limits"""
        current_time = time.time()
        with self.rate_limit_lock:
            self.command_timestamps = [
                ts for ts in self.command_timestamps
                if current_time - ts < self.rate_limit_window
            ]

            if len(self.command_timestamps) >= self.rate_limit_max_commands:
                return False

            self.command_timestamps.append(current_time)
            return True
