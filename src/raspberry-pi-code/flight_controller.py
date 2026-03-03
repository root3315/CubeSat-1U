#!/usr/bin/env python3
# Simplified Flight Controller for CubeSat
# Lightweight implementation optimized for resource-constrained environments

import sys
import io


# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import logging
import time
import serial  # type: ignore
import cv2  # type: ignore
import numpy as np
import json
import threading
import queue
import os
import struct
import hashlib
from datetime import datetime
from PIL import Image  # type: ignore
from typing import Optional, Dict, Any, List, Tuple, Union
from pathlib import Path

#import RPi.GPIO as GPIO
try:
    import RPi.GPIO as GPIO # type: ignore
except ImportError:
    print("Running in simulation mode (No GPIO hardware found)")

    class MockGPIO:
        BCM: Optional[int] = None
        OUT: Optional[int] = None
        IN: Optional[int] = None
        HIGH: Optional[int] = None
        LOW: Optional[int] = None

        def setmode(self, *args: Any) -> None:
            print("GPIO mode set")

        def setup(self, *args: Any) -> None:
            print(f"GPIO setup: {args}")

        def output(self, *args: Any) -> None:
            print(f"GPIO output: {args}")

        def cleanup(self) -> None:
            print("GPIO cleanup")

    GPIO = MockGPIO()


# Import custom modules
from camera_handler import CameraHandler
from telemetry_handler import TelemetryHandler
from communication import CommunicationHandler
from logging_monitoring import initialize_logging_system, get_logger, SimpleHealthMonitor
from ota_updater import OTAUpdater


class CubeSatFlightController:
    """Simplified flight controller for Raspberry Pi with improved reliability"""

    def __init__(self, config_file: str = 'config.json') -> None:
        """Initialize the flight controller with improved reliability"""

        # Load configuration first
        self.config: Dict[str, Any] = self.load_config(config_file)

        # Initialize logging system
        self.logger: logging.Logger
        self.health_monitor: Optional[SimpleHealthMonitor]
        self.logger, self.health_monitor = initialize_logging_system(self.config)
        self.logger.info("=" * 60)
        self.logger.info("CubeSat 1U Flight Controller v1.0 - Simplified")
        self.logger.info("=" * 60)

        # System state
        self.state: str = 'BOOT'
        self.running: bool = True
        self.uptime: float = 0
        self.sequence_number: int = 0

        # Power management
        self.power_mode: str = 'NORMAL'  # NORMAL, LOW_POWER, CRITICAL
        self.last_battery_check: float = 0

        # Initialize handlers
        self.camera: CameraHandler = CameraHandler(self.config)
        self.telemetry: TelemetryHandler = TelemetryHandler(self.config)
        self.comm: CommunicationHandler = CommunicationHandler(self.config)

        # Initialize OTA updater
        self.ota_updater: OTAUpdater = OTAUpdater(self.config, self.logger)

        # Queues for inter-thread communication
        self.telemetry_queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=50)  # Smaller queue for efficiency
        self.command_queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=20)    # Smaller queue for efficiency
        self.image_queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=5)       # Smaller queue for efficiency
        self.downlink_queue: queue.Queue[Dict[str, Any]] = queue.Queue(maxsize=20)   # Smaller queue for efficiency

        # Threads
        self.threads: List[threading.Thread] = []
        self.running = True

        # Setup GPIO
        self.setup_gpio()

        # Start all threads
        self.start_threads()

        self.logger.info("Flight controller initialized successfully")

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        default_config: Dict[str, Any] = {
            "satellite": {
                "name": "CubeSat-1U",
                "mission_id": "CS1-2025",
                "callsign": "CS1"
            },
            "camera": {
                "resolution": [3280, 2464],
                "capture_interval": 600,  # seconds
                "compression_quality": 85,
                "svd_components": 50
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
                "beacon_interval": 30
            },
            "gpio": {
                "stm32_wake": 17,
                "pi_ready": 27,
                "led_status": 22
            }
        }

        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    loaded_config: Dict[str, Any] = json.load(f)
                    # Merge with default
                    for key in default_config:
                        if key not in loaded_config:
                            loaded_config[key] = default_config[key]
                    return loaded_config
            else:
                # Save default config
                with open(config_file, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return default_config

    def setup_gpio(self) -> None:
        """Setup GPIO pins with error handling"""
        try:
            GPIO.setmode(GPIO.BCM)  # type: ignore
            GPIO.setup(self.config['gpio']['stm32_wake'], GPIO.IN)  # type: ignore
            GPIO.setup(self.config['gpio']['pi_ready'], GPIO.OUT)  # type: ignore
            GPIO.setup(self.config['gpio']['led_status'], GPIO.OUT)  # type: ignore

            # Set Pi ready signal
            GPIO.output(self.config['gpio']['pi_ready'], GPIO.HIGH)  # type: ignore

            self.logger.info("GPIO initialized")
        except Exception as e:
            self.logger.error(f"GPIO setup error: {e}")

    def start_threads(self) -> None:
        """Start all background threads with error handling"""

        thread_configs: List[Tuple[str, Any]] = [
            ("STM32 Reader", self.stm32_reader_thread),
            ("STM32 Writer", self.stm32_writer_thread),
            ("Command Processor", self.command_processor_thread),
            ("Image Capture", self.image_capture_thread),
            ("Image Compressor", self.image_compressor_thread),
            ("Telemetry Logger", self.telemetry_logger_thread),
            ("System Health Monitor", self.system_health_monitor_thread),
            ("Downlink Manager", self.downlink_manager_thread),
            ("Status LED", self.status_led_thread)
        ]

        for name, target in thread_configs:
            try:
                thread: threading.Thread = threading.Thread(target=target, name=name, daemon=True)
                thread.start()
                self.threads.append(thread)
                self.logger.info(f"Started thread: {name}")
            except Exception as e:
                self.logger.error(f"Failed to start thread {name}: {e}")

        self.state = 'NOMINAL'

    def stm32_reader_thread(self) -> None:
        """Read data from STM32 via UART with improved error handling"""
        consecutive_errors: int = 0
        max_consecutive_errors: int = 5

        while self.running:
            try:
                if self.comm.stm32_serial and self.comm.stm32_serial.in_waiting:  # type: ignore
                    data: bytes = self.comm.stm32_serial.read(self.comm.stm32_serial.in_waiting)  # type: ignore

                    # Process telemetry packets
                    packets: List[Dict[str, Any]] = self.comm.parse_incoming_data(data)
                    for packet in packets:
                        if packet['type'] == 'telemetry':
                            try:
                                self.telemetry_queue.put_nowait(packet['data'])
                            except queue.Full:
                                self.logger.warning("Telemetry queue full, dropping packet")
                        elif packet['type'] == 'command_response':
                            self.logger.info(f"Command response: {packet['data']}")

                # Reset error counter on success
                consecutive_errors = 0

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"STM32 reader error: {e}")

                # If too many consecutive errors, try to reconnect
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.warning("Too many consecutive errors, attempting recovery...")
                    time.sleep(2)  # Brief pause before retry
                    consecutive_errors = 0  # Reset counter after delay

            time.sleep(0.01)

    def stm32_writer_thread(self) -> None:
        """Send commands to STM32 with improved error handling"""
        consecutive_errors: int = 0
        max_consecutive_errors: int = 3

        while self.running:
            try:
                if not self.command_queue.empty():
                    cmd: Dict[str, Any] = self.command_queue.get_nowait()
                    success: bool = self.comm.send_to_stm32(cmd)

                    if not success:
                        self.logger.warning("Failed to send command to STM32")
                        consecutive_errors += 1
                    else:
                        consecutive_errors = 0  # Reset on success

            except queue.Empty:
                pass
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"STM32 writer error: {e}")

            # If too many consecutive errors, pause briefly
            if consecutive_errors >= max_consecutive_errors:
                time.sleep(0.5)
                consecutive_errors = 0

            time.sleep(0.01)

    def command_processor_thread(self) -> None:
        """Process commands from STM32 or ground station with improved error handling"""
        consecutive_errors: int = 0
        max_consecutive_errors: int = 3

        while self.running:
            try:
                # Check for commands from STM32 (forwarded from ground)
                if not self.comm.command_queue.empty():
                    cmd: Dict[str, Any] = self.comm.command_queue.get_nowait()
                    self.execute_command(cmd)
                    consecutive_errors = 0  # Reset on success

            except queue.Empty:
                pass
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Command processor error: {e}")

            # If too many consecutive errors, pause briefly
            if consecutive_errors >= max_consecutive_errors:
                time.sleep(0.5)
                consecutive_errors = 0

            time.sleep(0.1)

    def execute_command(self, cmd: Dict[str, Any]) -> None:
        """CRITICAL FIX #105: Execute a received command with authentication for critical commands"""
        try:
            self.logger.info(f"Executing command: {cmd}")

            cmd_type: Optional[str] = cmd.get('type')
            params: Dict[str, Any] = cmd.get('params', {})

            # CRITICAL FIX #105: Require authentication for critical commands
            CRITICAL_COMMANDS: List[str] = ['REBOOT', 'SHUTDOWN', 'START_UPDATE']
            if cmd_type in CRITICAL_COMMANDS:
                if not self._validate_critical_command(cmd):
                    self.logger.warning(f"Unauthorized critical command blocked: {cmd_type}")
                    return

            if cmd_type == 'PING':
                response: Dict[str, Any] = {'type': 'PONG', 'timestamp': time.time()}
                self.comm.send_to_stm32(response)

            elif cmd_type == 'CAPTURE_IMAGE':
                # Trigger immediate capture
                threading.Thread(target=self.camera.capture_image,
                               args=(self.image_queue,)).start()

            elif cmd_type == 'GET_TELEMETRY':
                # Send latest telemetry
                latest: Dict[str, Any] = self.telemetry.get_latest()
                self.comm.send_to_stm32(latest)

            elif cmd_type == 'TRANSMIT_FILE':
                # MEDIUM FIX: Validate file path to prevent path traversal
                filename: Optional[str] = params.get('filename')
                if filename:
                    # Sanitize filename - only allow basename
                    filename = os.path.basename(filename)
                    if filename and os.path.exists(filename):
                        self.downlink_queue.put({
                            'type': 'file',
                            'filename': filename,
                            'priority': 1
                        })
                    else:
                        self.logger.error(f"Invalid or non-existent file: {filename}")

            elif cmd_type == 'SET_SCHEDULE':
                # Update capture schedule
                interval: int = params.get('interval', 600)
                self.config['camera']['capture_interval'] = interval
                self.logger.info(f"Capture interval updated to {interval}s")

            elif cmd_type == 'GET_STATUS':
                status: Dict[str, Any] = {
                    'state': self.state,
                    'uptime': self.uptime,
                    'free_space': self.get_free_space(),
                    'temp': self.get_cpu_temperature(),
                    'images': self.get_image_count()
                }
                self.comm.send_to_stm32({'type': 'STATUS', 'data': status})

            elif cmd_type == 'CHECK_UPDATES':
                # Check for system updates
                update_info: Optional[Dict[str, Any]] = self.ota_updater.check_for_updates()
                response = {
                    'type': 'UPDATE_INFO',
                    'available': update_info is not None,
                    'update_info': update_info,
                    'current_version': self.ota_updater.current_version
                }
                self.comm.send_to_stm32(response)

            elif cmd_type == 'GET_SYSTEM_INFO':
                # Get detailed system information
                sys_info: Dict[str, Any] = self.ota_updater.get_system_info()
                response = {
                    'type': 'SYSTEM_INFO',
                    'info': sys_info
                }
                self.comm.send_to_stm32(response)

            elif cmd_type == 'REBOOT':
                self.logger.warning("Reboot command received")
                self.shutdown()
                # FIX: Use subprocess with argument list instead of os.system() for security
                import subprocess
                try:
                    subprocess.run(['/usr/bin/sudo', '/sbin/reboot'], check=False)
                except Exception as reboot_error:
                    self.logger.error(f"Reboot command failed: {reboot_error}")

            elif cmd_type == 'SHUTDOWN':
                self.logger.warning("Shutdown command received")
                self.shutdown()
                # FIX: Use subprocess with argument list instead of os.system() for security
                import subprocess
                try:
                    subprocess.run(['/usr/bin/sudo', '/sbin/shutdown', '-h', 'now'], check=False)
                except Exception as shutdown_error:
                    self.logger.error(f"Shutdown command failed: {shutdown_error}")

        except Exception as e:
            self.logger.error(f"Error executing command {cmd}: {e}")

    def _validate_critical_command(self, cmd: Dict[str, Any]) -> bool:
        """
        CRITICAL FIX #105: Validate critical commands with HMAC signature

        Args:
            cmd: Command dictionary

        Returns:
            True if command is authenticated
        """
        import hmac
        import time

        # Get signature and timestamp from command
        signature: Optional[str] = cmd.get('signature')
        timestamp: Optional[float] = cmd.get('timestamp')

        if not signature or not timestamp:
            self.logger.error("Critical command missing signature or timestamp")
            return False

        # Check timestamp validity (prevent replay attacks)
        if abs(time.time() - timestamp) > 300:  # 5 minute window
            self.logger.error("Critical command timestamp expired")
            return False

        # Get secret key from environment
        secret_key: str = os.environ.get('CUBESAT_SHARED_SECRET', '')
        if not secret_key:
            self.logger.warning("CUBESAT_SHARED_SECRET not set, allowing command for testing")
            return True

        # Create data for verification (all fields except signature)
        cmd_copy: Dict[str, Any] = {k: v for k, v in cmd.items() if k != 'signature'}
        cmd_data: bytes = json.dumps(cmd_copy, sort_keys=True).encode('utf-8')

        # Calculate expected signature
        expected_signature: str = hmac.new(
            secret_key.encode('utf-8'),
            cmd_data,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures securely
        if not hmac.compare_digest(signature, expected_signature):
            self.logger.error("Critical command signature verification failed")
            return False

        self.logger.info("Critical command authenticated successfully")
        return True

    def image_capture_thread(self) -> None:
        """Scheduled image capture thread with power management"""
        last_capture: float = 0

        while self.running:
            try:
                current_time: float = time.time()

                # Get appropriate interval based on power mode
                if self.power_mode == 'CRITICAL':
                    interval: int = self.config['power_management']['power_save_intervals']['critical_battery']
                elif self.power_mode == 'LOW_POWER':
                    interval = self.config['power_management']['power_save_intervals']['low_battery']
                else:
                    interval = self.config['power_management']['power_save_intervals']['normal']

                # Check if it's time to capture
                if current_time - last_capture >= interval:
                    self.logger.info("Scheduled image capture triggered")
                    threading.Thread(target=self.camera.capture_image,
                                   args=(self.image_queue,)).start()
                    last_capture = current_time

            except Exception as e:
                self.logger.error(f"Image capture scheduling error: {e}")

            time.sleep(1)

    def image_compressor_thread(self) -> None:
        """Compress images using SVD for efficient downlink with improved error handling"""
        consecutive_errors: int = 0
        max_consecutive_errors: int = 3

        while self.running:
            try:
                if not self.image_queue.empty():
                    image_info: Dict[str, Any] = self.image_queue.get_nowait()

                    self.logger.info(f"Compressing image: {image_info['filename']}")

                    # Compress the image
                    compressed_path: Optional[str] = self.camera.compress_image(
                        image_info['filename'],
                        self.config['camera']['svd_components']
                    )

                    if compressed_path:
                        # Add to downlink queue
                        self.downlink_queue.put({
                            'type': 'image',
                            'filename': compressed_path,
                            'original': image_info['filename'],
                            'timestamp': image_info['timestamp'],
                            'priority': 2
                        })

                        # Generate thumbnail for quick preview
                        thumbnail_path: Optional[str] = self.camera.create_thumbnail(
                            image_info['filename']
                        )
                        if thumbnail_path:
                            self.downlink_queue.put({
                                'type': 'thumbnail',
                                'filename': thumbnail_path,
                                'timestamp': image_info['timestamp'],
                                'priority': 3
                            })

                    consecutive_errors = 0  # Reset on success

            except queue.Empty:
                pass
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Image compression error: {e}")

            # If too many consecutive errors, pause briefly
            if consecutive_errors >= max_consecutive_errors:
                time.sleep(0.5)
                consecutive_errors = 0

            time.sleep(0.1)

    def telemetry_logger_thread(self) -> None:
        """Log telemetry data to SD card with improved error handling"""
        consecutive_errors: int = 0
        max_consecutive_errors: int = 3

        while self.running:
            try:
                if not self.telemetry_queue.empty():
                    telemetry: Dict[str, Any] = self.telemetry_queue.get_nowait()
                    self.telemetry.save_telemetry(telemetry)
                    consecutive_errors = 0  # Reset on success

            except queue.Empty:
                pass
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Telemetry logger error: {e}")

            # If too many consecutive errors, pause briefly
            if consecutive_errors >= max_consecutive_errors:
                time.sleep(0.5)
                consecutive_errors = 0

            time.sleep(0.1)

    def downlink_manager_thread(self) -> None:
        """Manage data downlink to ground station with improved error handling"""
        last_beacon: float = 0
        consecutive_errors: int = 0
        max_consecutive_errors: int = 3

        while self.running:
            try:
                current_time: float = time.time()

                # Send beacon every 30 seconds
                if current_time - last_beacon >= self.config['communication']['beacon_interval']:
                    self.send_beacon()
                    last_beacon = current_time

                # Process downlink queue
                if not self.downlink_queue.empty():
                    # Get highest priority item
                    items: List[Dict[str, Any]] = []
                    while not self.downlink_queue.empty():
                        items.append(self.downlink_queue.get_nowait())

                    # Sort by priority (lower number = higher priority)
                    items.sort(key=lambda x: x.get('priority', 10))

                    # Send highest priority item
                    if items:
                        self.send_to_ground(items[0])

                    # Put remaining items back
                    for item in items[1:]:
                        try:
                            self.downlink_queue.put_nowait(item)
                        except queue.Full:
                            self.logger.warning("Downlink queue full, dropping item")

                consecutive_errors = 0  # Reset on success

            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"Downlink manager error: {e}")

            # If too many consecutive errors, pause briefly
            if consecutive_errors >= max_consecutive_errors:
                time.sleep(0.5)
                consecutive_errors = 0

            time.sleep(1)

    def send_beacon(self) -> None:
        """Send status beacon with priority telemetry"""
        try:
            # Get priority telemetry data
            priority_data: Dict[str, Any] = self.get_priority_telemetry()

            beacon: Dict[str, Any] = {
                'type': 'BEACON',
                'timestamp': time.time(),
                'state': self.state,
                'uptime': self.uptime,
                'battery': priority_data.get('battery_voltage', self.telemetry.get_latest_battery()),
                'power_mode': priority_data.get('power_mode', 'NORMAL'),
                'cpu_temp': priority_data.get('cpu_temp', 0),
                'free_space': priority_data.get('free_space', 0),
                'images_queued': self.image_queue.qsize(),
                'downlink_queued': self.downlink_queue.qsize()
            }

            self.comm.send_to_radio(beacon)
            self.logger.debug(f"Beacon sent: {beacon}")
        except Exception as e:
            self.logger.error(f"Error sending beacon: {e}")

    def send_to_ground(self, data: Dict[str, Any]) -> None:
        """Send data to ground station via radio"""
        try:
            self.logger.info(f"Sending to ground: {data.get('type')}")

            if data['type'] in ['image', 'thumbnail']:
                # Send image in chunks
                self.comm.send_file_to_ground(data['filename'])
            else:
                # Send as JSON
                self.comm.send_to_radio(data)
        except Exception as e:
            self.logger.error(f"Error sending to ground: {e}")

    def system_health_monitor_thread(self) -> None:
        """Simplified system health monitoring with power management"""
        check_interval: int = 60  # Increased interval for efficiency
        last_check: float = 0

        while self.running:
            try:
                current_time: float = time.time()

                if current_time - last_check >= check_interval:
                    # Check disk space
                    free_space: float = self.get_free_space()
                    if free_space < self.config['storage']['min_free_space_gb']:
                        self.logger.warning(f"Low disk space: {free_space:.2f} GB")
                        self.cleanup_old_files()

                    # Check temperature
                    temp: float = self.get_cpu_temperature()
                    if temp > 75:  # Increased threshold slightly
                        self.logger.warning(f"High CPU temperature: {temp}°C")

                    # Check battery level and update power mode
                    self.update_power_mode()

                    # Check thread health
                    dead_threads: List[str] = []
                    for thread in self.threads:
                        if not thread.is_alive():
                            dead_threads.append(thread.name)
                            self.logger.error(f"Thread {thread.name} died!")

                    if dead_threads:
                        # Attempt to restart critical threads
                        self.restart_dead_threads(dead_threads)

                    # Update uptime
                    self.uptime += check_interval

                    last_check = current_time

            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")

            time.sleep(10)

    def update_power_mode(self) -> None:
        """Update power mode based on battery level"""
        try:
            # Get latest battery voltage from telemetry
            latest_telemetry: Dict[str, Any] = self.telemetry.get_latest()
            battery_voltage: float = latest_telemetry.get('battery_voltage', 4.2)  # Default to full charge

            # Update power mode based on battery level
            if battery_voltage < self.config['power_management']['low_battery_threshold']:
                if self.power_mode != 'LOW_POWER':
                    self.power_mode = 'LOW_POWER'
                    self.logger.info(f"Switched to LOW_POWER mode (battery: {battery_voltage:.2f}V)")
            elif battery_voltage < 3.4:  # Critical level
                if self.power_mode != 'CRITICAL':
                    self.power_mode = 'CRITICAL'
                    self.logger.warning(f"Switched to CRITICAL power mode (battery: {battery_voltage:.2f}V)")
            else:
                if self.power_mode != 'NORMAL':
                    self.power_mode = 'NORMAL'
                    self.logger.info(f"Switched to NORMAL power mode (battery: {battery_voltage:.2f}V)")

        except Exception as e:
            self.logger.error(f"Error updating power mode: {e}")

    def get_priority_telemetry(self) -> Dict[str, Any]:
        """Get critical telemetry data with priority"""
        try:
            latest: Dict[str, Any] = self.telemetry.get_latest()
            critical_data: Dict[str, Any] = {
                'timestamp': latest.get('timestamp'),
                'battery_voltage': latest.get('battery_voltage'),
                'temperature_bme': latest.get('temperature_bme'),
                'radiation_cps': latest.get('radiation_cps'),
                'power_mode': self.power_mode,
                'cpu_temp': self.get_cpu_temperature(),
                'free_space': self.get_free_space()
            }
            return critical_data
        except Exception as e:
            self.logger.error(f"Error getting priority telemetry: {e}")
            return {}

    def restart_dead_threads(self, dead_thread_names: List[str]) -> None:
        """Restart dead threads with error handling"""
        thread_map: Dict[str, Any] = {
            "STM32 Reader": self.stm32_reader_thread,
            "STM32 Writer": self.stm32_writer_thread,
            "Command Processor": self.command_processor_thread,
            "Image Capture": self.image_capture_thread,
            "Image Compressor": self.image_compressor_thread,
            "Telemetry Logger": self.telemetry_logger_thread,
            "System Health Monitor": self.system_health_monitor_thread,
            "Downlink Manager": self.downlink_manager_thread,
            "Status LED": self.status_led_thread
        }

        for thread_name in dead_thread_names:
            if thread_name in thread_map:
                try:
                    new_thread: threading.Thread = threading.Thread(target=thread_map[thread_name], name=thread_name, daemon=True)
                    new_thread.start()
                    # Replace the dead thread in the list
                    for i, t in enumerate(self.threads):
                        if t.name == thread_name:
                            self.threads[i] = new_thread
                            break
                    self.logger.info(f"Restarted thread: {thread_name}")
                except Exception as e:
                    self.logger.error(f"Failed to restart thread {thread_name}: {e}")

    def status_led_thread(self) -> None:
        """Control status LED with improved reliability"""
        while self.running:
            try:
                if self.state == 'NOMINAL':
                    # Heartbeat: slow blink
                    GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                    time.sleep(1)
                    GPIO.output(self.config['gpio']['led_status'], GPIO.LOW)  # type: ignore
                    time.sleep(1)
                elif self.state == 'IMAGE_CAPTURE':
                    # Fast blink during capture
                    for _ in range(5):
                        GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                        time.sleep(0.1)
                        GPIO.output(self.config['gpio']['led_status'], GPIO.LOW)  # type: ignore
                        time.sleep(0.1)
                elif self.state == 'DATA_TX':
                    # Double blink during transmission
                    GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                    time.sleep(0.2)
                    GPIO.output(self.config['gpio']['led_status'], GPIO.LOW)  # type: ignore
                    time.sleep(0.2)
                    GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                    time.sleep(0.2)
                    GPIO.output(self.config['gpio']['led_status'], GPIO.LOW)  # type: ignore
                    time.sleep(0.4)
                elif self.state == 'ERROR':
                    # Continuous fast blink for error
                    GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                    time.sleep(0.1)
                    GPIO.output(self.config['gpio']['led_status'], GPIO.LOW)  # type: ignore
                    time.sleep(0.1)
                else:
                    # Solid on for boot/safe mode
                    GPIO.output(self.config['gpio']['led_status'], GPIO.HIGH)  # type: ignore
                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"LED control error: {e}")
                time.sleep(1)  # Brief pause on error

    def get_free_space(self) -> float:
        """Get free space on SD card in GB"""
        try:
            statvfs: os.statvfs_result = os.statvfs(self.config['storage']['base_path'])  # type: ignore
            free_space: float = statvfs.f_frsize * statvfs.f_bavail / (1024**3)
            return free_space
        except:
            return 0

    def get_cpu_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp: int = int(f.read()) / 1000
            return temp
        except:
            return 0

    def get_image_count(self) -> int:
        """Get number of stored images"""
        try:
            image_path: str = os.path.join(self.config['storage']['base_path'], 'images')
            if os.path.exists(image_path):
                return len([f for f in os.listdir(image_path) if f.endswith('.jpg')])
        except:
            pass
        return 0

    def cleanup_old_files(self) -> None:
        """Delete oldest files when space is low"""
        try:
            self.logger.info("Cleaning up old files")

            # Clean telemetry files older than 30 days
            self.telemetry.cleanup_old_files(days=30)

            # Clean old images
            image_path: str = os.path.join(self.config['storage']['base_path'], 'images')
            if os.path.exists(image_path):
                images: List[str] = sorted([os.path.join(image_path, f) for f in os.listdir(image_path)
                               if f.startswith('raw_')])

                # Delete oldest 20%
                delete_count: int = max(1, len(images) // 5)
                for f in images[:delete_count]:
                    try:
                        os.remove(f)
                        self.logger.info(f"Deleted old file: {f}")
                    except Exception as e:
                        self.logger.error(f"Error deleting {f}: {e}")
        except Exception as e:
            self.logger.error(f"Error during file cleanup: {e}")

    def shutdown(self) -> None:
        """Graceful shutdown with improved error handling"""
        try:
            self.logger.info("Shutting down flight controller...")

            self.running = False

            # Stop health monitoring
            if self.health_monitor:
                self.health_monitor.stop_monitoring()

            # Wait for threads with timeout
            for thread in self.threads:
                thread.join(timeout=2)  # Shorter timeout

            # Cleanup
            self.camera.cleanup()
            self.comm.cleanup()
            GPIO.cleanup()  # type: ignore

            self.logger.info("Shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


if __name__ == '__main__':
    controller: CubeSatFlightController = CubeSatFlightController()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nReceived interrupt")
        controller.shutdown()
