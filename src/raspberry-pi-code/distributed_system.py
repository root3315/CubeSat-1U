"""
Simplified Distributed Architecture Components for CubeSat System
Lightweight implementation optimized for single CubeSat with limited resources

Note: This is a simplified version that doesn't require aiohttp.
For the full async version with HTTP communication, use the distributed_system.py
from the main CubeSat_1u-main project and ensure aiohttp==3.9.1 is installed.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional
import uuid


class SimpleNode:
    """Simple node class for basic CubeSat operations"""

    def __init__(self, node_type: str, host: str = "localhost", port: int = 8000) -> None:
        self.node_id: str = str(uuid.uuid4())[:8]  # Shorter ID for efficiency
        self.node_type: str = node_type
        self.host: str = host
        self.port: int = port
        self.status: str = "online"
        self.last_heartbeat: float = time.time()
        self.capabilities: List[str] = []
        self.logger: logging.Logger = logging.getLogger(f"SimpleNode-{node_type}")

        # Simple message queue without size limits to reduce complexity
        self.message_queue: List[Dict[str, Any]] = []

    def heartbeat(self) -> None:
        """Simple heartbeat without resource monitoring"""
        self.last_heartbeat = time.time()
        self.logger.debug(f"Heartbeat from {self.node_type}: {self.node_id}")

    def send_message(self, message: Dict[str, Any]) -> bool:
        """Simple message sending without complex routing"""
        try:
            # Process message directly without network overhead
            self.process_message(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def process_message(self, message: Dict[str, Any]) -> None:
        """Process message directly"""
        # In a real implementation, this would handle the message appropriately
        pass


class TelemetryProcessor(SimpleNode):
    """Simplified telemetry processor for single CubeSat"""

    def __init__(self, host: str = "localhost", port: int = 8001) -> None:
        super().__init__("telemetry_processor", host, port)
        self.capabilities: List[str] = ["telemetry_processing", "simple_analysis"]

        # Simple buffer without complex data structures
        self.telemetry_buffer: List[Dict[str, Any]] = []
        self.processed_data: List[Dict[str, Any]] = []

        # Simple thresholds without caching
        self.thresholds: Dict[str, float] = {
            'battery_min': 3.4,
            'battery_max': 4.2,
            'temp_threshold': 45.0
        }

    def process_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Process incoming telemetry data efficiently"""
        try:
            # Perform simple analysis on telemetry data
            processed_item: Dict[str, Any] = self._analyze_telemetry(telemetry_data)

            # Add to processed data
            self.processed_data.append(processed_item)

            # Trigger processing if buffer is full
            if len(self.telemetry_buffer) >= 10:  # Small buffer for CubeSat
                self._simple_process()

            self.logger.info(f"Processed telemetry from {telemetry_data.get('source', 'unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Error processing telemetry: {e}")
            return False

    def _analyze_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simple analysis of telemetry data"""
        analysis: Dict[str, Any] = {
            "original_data": data,
            "analysis_timestamp": time.time(),
            "anomalies_detected": [],
            "derived_metrics": {}
        }

        # Simple anomaly detection
        if "battery_voltage" in data:
            voltage: float = data["battery_voltage"]
            if voltage < self.thresholds['battery_min']:
                analysis["anomalies_detected"].append("low_battery")
            elif voltage > self.thresholds['battery_max']:
                analysis["anomalies_detected"].append("high_battery")

        if "temperature_bme" in data:
            temp: float = data["temperature_bme"]
            if temp > self.thresholds['temp_threshold']:
                analysis["anomalies_detected"].append("high_temperature")

        # Calculate simple derived metrics
        mag_keys: List[str] = ["mag_x", "mag_y", "mag_z"]
        if all(key in data for key in mag_keys):
            mag_values: List[float] = [data[key] for key in mag_keys]
            mag_strength: float = sum(v**2 for v in mag_values)**0.5
            analysis["derived_metrics"]["magnetic_field_strength"] = mag_strength

        return analysis

    def _simple_process(self) -> None:
        """Simple processing without resource checks"""
        self.logger.info(f"Processing {len(self.telemetry_buffer)} telemetry items")
        self.telemetry_buffer.clear()


class CommandDispatcher(SimpleNode):
    """Simple command dispatcher for single CubeSat"""

    def __init__(self, host: str = "localhost", port: int = 8002) -> None:
        super().__init__("command_dispatcher", host, port)
        self.capabilities: List[str] = ["command_dispatch", "simple_routing"]
        self.pending_commands: Dict[str, Dict[str, Any]] = {}

    def dispatch_command(self, command: Dict[str, Any]) -> str:
        """Dispatch a command directly to CubeSat"""
        command_id: str = str(uuid.uuid4())[:8]  # Shorter ID
        command_with_id: Dict[str, Any] = {
            "command_id": command_id,
            "command": command,
            "timestamp": time.time()
        }

        # Store as pending
        self.pending_commands[command_id] = command_with_id

        # Send to CubeSat directly
        success: bool = self._send_to_cubeSat(command_with_id)

        if success:
            del self.pending_commands[command_id]
            self.logger.info(f"Command {command_id} dispatched successfully")
        else:
            self.logger.warning(f"Command {command_id} failed to dispatch")

        return command_id

    def _send_to_cubeSat(self, command: Dict[str, Any]) -> bool:
        """Send command directly to CubeSat"""
        # In a real implementation, this would use the actual CubeSat communication
        # For now, we'll just return success
        self.logger.info(f"Sending command to CubeSat")
        return True


class DataStorageNode(SimpleNode):
    """Simple data storage for single CubeSat with minimal overhead"""

    def __init__(self, host: str = "localhost", port: int = 8003) -> None:
        super().__init__("data_storage", host, port)
        self.capabilities: List[str] = ["data_storage", "simple_query"]

        # Simple storage without complex indexing
        self.storage_backend: List[Dict[str, Any]] = []
        self.max_storage_entries: int = 1000  # Reasonable limit for CubeSat

        self.logger = logging.getLogger("DataStorageNode")

    def store_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Store telemetry data with simple size management"""
        try:
            entry: Dict[str, Any] = {
                "timestamp": time.time(),
                "data": telemetry_data
            }

            # Store in simple list
            self.storage_backend.append(entry)

            # Manage size
            if len(self.storage_backend) > self.max_storage_entries:
                # Remove oldest entries
                excess: int = len(self.storage_backend) - self.max_storage_entries
                self.storage_backend = self.storage_backend[excess:]

            self.logger.info(f"Stored telemetry entry")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store telemetry: {e}")
            return False

    def store_command(self, command_data: Dict[str, Any]) -> bool:
        """Store command data with simple size management"""
        try:
            entry: Dict[str, Any] = {
                "timestamp": time.time(),
                "data": command_data
            }

            # Store in simple list
            self.storage_backend.append(entry)

            # Manage size
            if len(self.storage_backend) > self.max_storage_entries:
                # Remove oldest entries
                excess: int = len(self.storage_backend) - self.max_storage_entries
                self.storage_backend = self.storage_backend[excess:]

            self.logger.info(f"Stored command entry")
            return True
        except Exception as e:
            self.logger.error(f"Failed to store command: {e}")
            return False

    def query_data(self, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simple query without complex indexing"""
        results: List[Dict[str, Any]] = []
        for entry in self.storage_backend:
            # Apply simple filters
            matches: bool = True
            for key, value in query_params.items():
                if key in entry.get('data', {}):
                    if entry['data'][key] != value:
                        matches = False
                        break

            if matches:
                results.append(entry)

        self.logger.info(f"Query returned {len(results)} results")
        return results


class SimpleSystemManager:
    """Simple system manager for single CubeSat"""

    def __init__(self) -> None:
        self.nodes: Dict[str, SimpleNode] = {}
        self.logger: logging.Logger = logging.getLogger("SimpleSystemManager")

        # Initialize node attributes
        self.telemetry_processor: Optional[TelemetryProcessor] = None
        self.command_dispatcher: Optional[CommandDispatcher] = None
        self.data_storage: Optional[DataStorageNode] = None

    def initialize_system(self) -> None:
        """Initialize the simplified system"""
        # Create and start simple nodes
        self.telemetry_processor = TelemetryProcessor(host="localhost", port=8001)
        self.nodes[self.telemetry_processor.node_id] = self.telemetry_processor

        self.command_dispatcher = CommandDispatcher(host="localhost", port=8002)
        self.nodes[self.command_dispatcher.node_id] = self.command_dispatcher

        self.data_storage = DataStorageNode(host="localhost", port=8003)
        self.nodes[self.data_storage.node_id] = self.data_storage

        self.logger.info("Simple system initialized with 3 nodes")

    def process_telemetry(self, telemetry_data: Dict[str, Any]) -> bool:
        """Process telemetry through the system"""
        # Process through telemetry processor
        if self.telemetry_processor:
            success: bool = self.telemetry_processor.process_telemetry(telemetry_data)

            if success and self.data_storage:
                # Store processed data
                self.data_storage.store_telemetry(telemetry_data)

            return success
        return False

    def dispatch_command(self, command: Dict[str, Any]) -> Optional[str]:
        """Dispatch command through the system"""
        if self.command_dispatcher:
            return self.command_dispatcher.dispatch_command(command)
        return None
