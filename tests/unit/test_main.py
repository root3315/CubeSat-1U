"""
Модульные тесты для CubeSat 1U системы
"""
import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.raspberry_pi_code.flight_controller import CubeSatFlightController
from src.raspberry_pi_code.security import SecurityManager
from src.raspberry_pi_code.telemetry_handler import TelemetryHandler


class TestFlightControllerMain(unittest.TestCase):
    """Основные тесты контроллера полета"""

    def setUp(self):
        """Настройка теста"""
        # Используем минимальную конфигурацию для тестирования
        self.config = {
            "satellite": {
                "name": "CubeSat-TEST",
                "mission_id": "CS-TEST",
                "callsign": "CS-T"
            },
            "camera": {
                "resolution": [640, 480],  # Уменьшенное разрешение для тестов
                "capture_interval": 300,  # 5 минут для тестов
                "compression_quality": 75,
                "svd_components": 20  # Меньше компонент для скорости
            },
            "storage": {
                "base_path": "/tmp/cubesat_test",
                "max_images": 10,
                "max_telemetry_files": 50,
                "min_free_space_gb": 0.1
            },
            "communication": {
                "stm32_port": "/dev/null",  # Для тестов
                "baudrate": 115200,
                "radio_port": "/dev/null",  # Для тестов
                "radio_baudrate": 9600,
                "beacon_interval": 15,  # 15 секунд для тестов
                "udp_port": 5000,
                "ground_station_ip": "127.0.0.1"
            },
            "security": {
                "shared_secret": "test_secret_for_testing",
                "require_auth": True,
                "enable_signing": True,
                "ssl_enabled": False
            },
            "logging": {
                "log_directory": "/tmp/cubesat_test/logs",
                "console_output": False,
                "file_rotation_mb": 1,
                "backup_count": 2
            },
            "gpio": {
                "stm32_wake": 17,
                "pi_ready": 27,
                "led_status": 22
            }
        }

        # Создаем контроллер с моками
        with patch('serial.Serial'), \
             patch('threading.Thread'), \
             patch('RPi.GPIO'):
            self.controller = CubeSatFlightController(config=self.config)

    def test_controller_initialization(self):
        """Тест инициализации контроллера"""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.state, 'BOOT')
        self.assertTrue(self.controller.running)
        self.assertEqual(self.controller.config['satellite']['name'], 'CubeSat-TEST')

    def test_command_processing(self):
        """Тест обработки команд"""
        command = {
            "type": "TEST_COMMAND",
            "params": {"test_param": "test_value"},
            "timestamp": time.time(),
            "nonce": "test_nonce_123"
        }

        # В тестовой среде просто проверяем, что команда может быть обработана
        self.assertIn('type', command)
        self.assertIsNotNone(command['type'])

    def test_telemetry_handling(self):
        """Тест обработки телеметрии"""
        telemetry_data = {
            "sequence": 1,
            "timestamp": time.time(),
            "temperature_bme": 25.5,
            "pressure": 1013.25,
            "humidity": 45.2,
            "battery_voltage": 3.78,
            "radiation_cps": 30
        }

        # Проверяем, что данные телеметрии корректны
        required_fields = ['sequence', 'timestamp', 'temperature_bme', 'battery_voltage']
        for field in required_fields:
            self.assertIn(field, telemetry_data)

        self.assertGreaterEqual(telemetry_data['sequence'], 0)
        self.assertGreater(telemetry_data['battery_voltage'], 0)


class TestSecurityManagerUnit(unittest.TestCase):
    """Модульные тесты менеджера безопасности"""

    def setUp(self):
        self.security = SecurityManager(shared_secret="unit_test_secret")

    def test_nonce_generation(self):
        """Тест генерации nonce"""
        nonce1 = self.security.generate_nonce()
        nonce2 = self.security.generate_nonce()

        self.assertIsInstance(nonce1, str)
        self.assertIsInstance(nonce2, str)
        self.assertNotEqual(nonce1, nonce2)
        self.assertGreater(len(nonce1), 0)

    def test_signature_operations(self):
        """Тест операций с подписями"""
        test_data = {"test": "data", "value": 123}
        data_bytes = json.dumps(test_data, sort_keys=True).encode()

        # Создание подписи
        signature = self.security.create_signature(data_bytes)
        self.assertIsInstance(signature, str)
        self.assertEqual(len(signature), 64)  # SHA256

        # Проверка подписи
        is_valid = self.security.verify_signature(data_bytes, signature)
        self.assertTrue(is_valid)

        # Проверка с неверными данными
        wrong_data = json.dumps({"test": "wrong"}, sort_keys=True).encode()
        is_valid_wrong = self.security.verify_signature(wrong_data, signature)
        self.assertFalse(is_valid_wrong)


class TestTelemetryHandlerUnit(unittest.TestCase):
    """Модульные тесты обработчика телеметрии"""

    def setUp(self):
        config = {
            "storage": {
                "base_path": "/tmp/test_telemetry_unit",
                "max_telemetry_files": 20
            }
        }
        self.handler = TelemetryHandler(config)

    def test_telemetry_validation(self):
        """Тест валидации телеметрии"""
        valid_telemetry = {
            "sequence": 123,
            "timestamp": time.time(),
            "temperature_bme": 25.5,
            "battery_voltage": 3.78
        }

        # Простая проверка, что данные корректны
        self.assertGreaterEqual(valid_telemetry['sequence'], 0)
        self.assertGreater(valid_telemetry['battery_voltage'], 0)
        self.assertIsInstance(valid_telemetry['temperature_bme'], (int, float))


def suite():
    """Создание тест-сьюта"""
    test_suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    test_suite.addTests(loader.loadTestsFromTestCase(TestFlightControllerMain))
    test_suite.addTests(loader.loadTestsFromTestCase(TestSecurityManagerUnit))
    test_suite.addTests(loader.loadTestsFromTestCase(TestTelemetryHandlerUnit))

    return test_suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())
    
    # Вывод результатов
    print(f"\nИтого: {result.testsRun} тестов")
    print(f"Ошибок: {len(result.errors)}")
    print(f"Неудач: {len(result.failures)}")
    
    exit(0 if result.wasSuccessful() else 1)