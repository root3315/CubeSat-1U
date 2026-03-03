"""Test Raspberry Pi code without any hardware"""
from __future__ import annotations

import sys
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock all hardware imports automatically
import builtins
import importlib


class MockGPIO:
    """Mock GPIO class for testing without hardware"""
    BCM: str = 'BCM'
    OUT: str = 'OUT'
    HIGH: int = 1
    LOW: int = 0

    def setmode(self, mode: Any) -> None:
        print(f"📌 Mock: GPIO mode={mode}")

    def setup(self, pin: int, mode: Any) -> None:
        print(f"📌 Mock: Pin {pin} setup as {mode}")

    def output(self, pin: int, state: Any) -> None:
        print(f"📌 Mock: Pin {pin} = {state}")

    def cleanup(self) -> None:
        print("📌 Mock: GPIO cleaned up")


# Replace RPi.GPIO with mock
sys.modules['RPi'] = type('RPi', (), {})
sys.modules['RPi.GPIO'] = MockGPIO()

# Now import your actual code
from flight_controller import CubeSatFlightController


def run_simulation() -> None:
    """Run the simulation loop"""
    print("="*60)
    print("🚀 RUNNING IN SIMULATION MODE - NO HARDWARE NEEDED")
    print("="*60)

    # Create controller but don't try real hardware
    controller: CubeSatFlightController = CubeSatFlightController()

    # Manually override to use mock
    controller.comm.stm32_serial = None  # No real serial
    print("\n✅ Controller initialized in simulation mode")
    print("\nAvailable commands you can test:")
    print("  - Telemetry logging")
    print("  - Image capture simulation")
    print("  - Data compression algorithms")
    print("  - State machine logic")
    print("\nPress Ctrl+C to exit")

    try:
        while True:
            # Generate mock telemetry
            mock_telemetry: Dict[str, Any] = {
                'timestamp': time.time(),
                'temperature_bme': 23.5,
                'radiation_cps': 42,
                'battery_voltage': 3850
            }
            controller.telemetry.save_telemetry(mock_telemetry)
            print(f"📊 Mock telemetry saved: {mock_telemetry['temperature_bme']}°C")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n✅ Test complete!")


if __name__ == '__main__':
    run_simulation()
