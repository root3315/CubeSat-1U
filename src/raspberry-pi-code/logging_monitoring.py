"""
Simplified Logging and Monitoring Module for CubeSat System
Lightweight implementation optimized for resource-constrained environments
"""
from __future__ import annotations

import logging
import logging.handlers
import time
import threading
from datetime import datetime
from pathlib import Path
import os
import sys
from typing import Dict, Any, Optional, List, Tuple


class SimpleLogger:
    """
    Simplified logger optimized for CubeSat resource constraints
    """

    def __init__(self, name: str = "CubeSat", log_dir: str = "./logs") -> None:
        self.name: str = name
        self.log_dir: Path = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Setup main logger
        self.logger: logging.Logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)  # Reduced default level for efficiency

        # Clear existing handlers
        self.logger.handlers.clear()

        # Formatter
        formatter: logging.Formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # File handler with smaller rotation
        file_handler: logging.handlers.RotatingFileHandler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{name.lower()}.log",
            maxBytes=5*1024*1024,  # Reduced to 5MB
            backupCount=3  # Reduced backup count
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Conditional console handler based on config
        if os.environ.get('CUBESAT_DEBUG', '').lower() == 'true':
            console_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self.logger.info(f"Simple logger initialized for {name}")

    def debug(self, message: str) -> None:
        """DEBUG level logging"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """INFO level logging"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """WARNING level logging"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """ERROR level logging"""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """CRITICAL level logging"""
        self.logger.critical(message)

    def alert(self, message: str, severity: str = "HIGH") -> None:
        """Special alert logging"""
        alert_msg: str = f"[ALERT-{severity}] {message}"
        self.logger.warning(alert_msg)

    def exception(self, message: str) -> None:
        """Exception logging"""
        self.logger.exception(message)


class SimpleHealthMonitor:
    """
    Simplified system health monitor
    """

    def __init__(self, logger: SimpleLogger, config: Dict[str, Any]) -> None:
        self.logger: SimpleLogger = logger
        self.config: Dict[str, Any] = config
        self.running: bool = False
        self.monitor_thread: Optional[threading.Thread] = None

        # Thresholds for alerts
        monitoring_config: Dict[str, Any] = config.get('monitoring', {})
        self.thresholds: Dict[str, Any] = {
            'cpu_percent': monitoring_config.get('cpu_threshold', 85.0),
            'memory_percent': monitoring_config.get('memory_threshold', 90.0),
            'disk_percent': monitoring_config.get('disk_threshold', 95.0),
            'temperature': monitoring_config.get('temp_threshold', 75.0),
            'battery_voltage_min': monitoring_config.get('battery_min', 3.4),
            'battery_voltage_max': monitoring_config.get('battery_max', 4.2)
        }

    def start_monitoring(self) -> None:
        """Start monitoring"""
        if self.running:
            return

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Simple health monitoring started")

    def stop_monitoring(self) -> None:
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)  # Shorter timeout
        self.logger.info("Health monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop with reduced frequency"""
        check_interval: int = self.config.get('monitoring', {}).get('check_interval', 60)  # Increased interval

        while self.running:
            try:
                # Check thresholds
                self._check_simple_thresholds()

                # Wait before next check
                for _ in range(check_interval):  # Break down sleep for responsiveness
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.logger.exception(f"Error in health monitor: {e}")
                time.sleep(10)  # Pause before retry

    def _check_simple_thresholds(self) -> None:
        """Check simplified thresholds using basic system calls"""
        try:
            # Import only when needed to reduce memory usage
            import os

            # Check memory usage (simplified)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo: str = f.read()
                    mem_total_line: str = [line for line in meminfo.split('\n') if 'MemTotal:' in line][0]
                    mem_free_line: str = [line for line in meminfo.split('\n') if 'MemFree:' in line][0]

                    mem_total: int = int(mem_total_line.split()[1])  # KB
                    mem_free: int = int(mem_free_line.split()[1])    # KB
                    memory_percent: float = 100 - (mem_free / mem_total * 100)

                    if memory_percent > self.thresholds['memory_percent']:
                        self.logger.alert(
                            f"Memory usage high: {memory_percent:.1f}%",
                            severity="HIGH"
                        )
            except Exception:
                pass  # Ignore errors in memory check

            # Check disk usage (simplified)
            try:
                statvfs = os.statvfs('/')
                disk_percent: float = (statvfs.f_blocks - statvfs.f_bavail) / statvfs.f_blocks * 100

                if disk_percent > self.thresholds['disk_percent']:
                    self.logger.alert(
                        f"Disk usage high: {disk_percent:.1f}%",
                        severity="CRITICAL"
                    )
            except Exception:
                pass  # Ignore errors in disk check

            # Check temperature
            try:
                temp: float = self._get_cpu_temperature()
                if temp > self.thresholds['temperature']:
                    self.logger.alert(
                        f"High CPU temperature: {temp}°C",
                        severity="MEDIUM"
                    )
            except Exception:
                pass  # Ignore errors in temperature check

        except Exception as e:
            self.logger.exception(f"Error in threshold check: {e}")

    def _get_cpu_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp: int = int(f.read())
            return temp / 1000
        except Exception:
            return 0.0

    def log_telemetry_health(self, telemetry_data: Dict[str, Any]) -> None:
        """Log telemetry data for monitoring"""
        try:
            # Check battery voltage
            battery_voltage: float = telemetry_data.get('battery_voltage', 0)
            if battery_voltage < self.thresholds['battery_voltage_min']:
                self.logger.alert(
                    f"Battery voltage critically low: {battery_voltage}V",
                    severity="CRITICAL"
                )
            elif battery_voltage > self.thresholds['battery_voltage_max']:
                self.logger.alert(
                    f"Battery voltage high: {battery_voltage}V",
                    severity="WARNING"
                )

            # Log basic telemetry info
            self.logger.info(
                f"Telemetry: batt={battery_voltage}V, temp={telemetry_data.get('temperature_bme', 0)}°C"
            )

        except Exception as e:
            self.logger.exception(f"Error checking telemetry health: {e}")


# Global instance for use in other modules
_simple_logger: Optional[SimpleLogger] = None
_simple_health_monitor: Optional[SimpleHealthMonitor] = None


def initialize_logging_system(config: Dict[str, Any]) -> Tuple[SimpleLogger, SimpleHealthMonitor]:
    """
    Initialize simplified logging system

    Returns:
        Tuple (logger, monitor)
    """
    global _simple_logger, _simple_health_monitor

    # Create logger
    log_dir: str = config.get('logging', {}).get('log_directory', './logs')
    _simple_logger = SimpleLogger("CubeSat", log_dir)

    # Create monitor
    _simple_health_monitor = SimpleHealthMonitor(_simple_logger, config)

    return _simple_logger, _simple_health_monitor


def get_logger() -> Optional[SimpleLogger]:
    """Get global logger instance"""
    return _simple_logger
