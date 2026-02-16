"""
Упрощенный набор тестов для CubeSat 1U системы
Оптимизирован для ресурсоограниченной среды
"""
import unittest
import json
import time
import os
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Импорт модулей для тестирования
from src.raspberry_pi_code.security import SecurityManager, create_secure_command, validate_secure_command
from src.raspberry_pi_code.communication import CommunicationHandler
from src.raspberry_pi_code.telemetry_handler import TelemetryHandler


class TestSecurityModule(unittest.TestCase):
    """Тесты модуля безопасности"""

    def setUp(self):
        self.security = SecurityManager(shared_secret="test_secret")

    def test_signature_generation(self):
        """Тест генерации подписей"""
        data = {"command": "test", "value": 123}
        data_bytes = json.dumps(data, sort_keys=True).encode()
        signature = self.security.create_signature(data_bytes)

        # Подпись должна быть 64 символа (SHA256)
        self.assertEqual(len(signature), 64)
        self.assertIsInstance(signature, str)

    def test_signature_verification(self):
        """Тест проверки подписей"""
        data = {"command": "test", "value": 123}
        data_bytes = json.dumps(data, sort_keys=True).encode()
        signature = self.security.create_signature(data_bytes)

        is_valid = self.security.verify_signature(data_bytes, signature)
        self.assertTrue(is_valid)

    def test_signature_invalid_data(self):
        """Тест проверки подписей с неверными данными"""
        data = {"command": "test", "value": 123}
        wrong_data = {"command": "different", "value": 456}

        data_bytes = json.dumps(data, sort_keys=True).encode()
        wrong_data_bytes = json.dumps(wrong_data, sort_keys=True).encode()

        signature = self.security.create_signature(data_bytes)
        is_valid = self.security.verify_signature(wrong_data_bytes, signature)

        self.assertFalse(is_valid)

    def test_nonce_handling(self):
        """Тест обработки одноразовых чисел (nonce)"""
        nonce = self.security.generate_nonce()

        # Проверка, что nonce не используется повторно
        self.assertFalse(self.security.is_nonce_valid(nonce))
        
        # Регистрация nonce
        self.security.register_nonce(nonce)
        
        # Повторное использование должно быть отклонено
        self.assertFalse(self.security.is_nonce_valid(nonce))


class TestCommunicationHandler(unittest.TestCase):
    """Тесты обработчика связи"""

    def setUp(self):
        config = {
            "communication": {
                "stm32_port": "/dev/null",  # Используем null для симуляции
                "baudrate": 115200,
                "radio_port": "/dev/null",  # Используем null для симуляции
                "radio_baudrate": 9600,
                "udp_port": 5000,
                "ground_station_ip": "127.0.0.1"
            },
            "security": {
                "shared_secret": "test_secret",
                "require_auth": True,
                "enable_signing": True
            }
        }
        
        # Создаем обработчик связи с моками для симуляции
        with patch('serial.Serial'):
            self.comm = CommunicationHandler(config)

    def test_command_creation(self):
        """Тест создания команд"""
        command = {"type": "TEST", "value": 123}
        secure_cmd = create_secure_command(1, command, self.security)

        self.assertIn('signature', secure_cmd)
        self.assertIn('nonce', secure_cmd)
        self.assertIn('timestamp', secure_cmd)
        self.assertEqual(secure_cmd['command_id'], 1)

    def test_command_validation(self):
        """Тест валидации команд"""
        command = {"type": "TEST", "value": 123}
        secure_cmd = create_secure_command(2, command, self.security)

        is_valid, msg = validate_secure_command(secure_cmd, self.security)
        self.assertTrue(is_valid)


class TestTelemetryHandler(unittest.TestCase):
    """Тесты обработчика телеметрии"""

    def setUp(self):
        config = {
            "storage": {
                "base_path": "/tmp/test_telemetry",
                "max_telemetry_files": 100
            }
        }
        self.telemetry = TelemetryHandler(config)

    def test_telemetry_storage(self):
        """Тест сохранения телеметрии"""
        test_data = {
            "timestamp": time.time(),
            "sequence": 1,
            "temperature_bme": 25.5,
            "pressure": 1013.25,
            "humidity": 45.2,
            "battery_voltage": 3.78,
            "radiation_cps": 30
        }

        success = self.telemetry.save_telemetry(test_data)
        self.assertTrue(success)

    def test_telemetry_retrieval(self):
        """Тест получения телеметрии"""
        test_data = {
            "timestamp": time.time(),
            "sequence": 2,
            "temperature_bme": 26.0,
            "pressure": 1012.50,
            "humidity": 46.0,
            "battery_voltage": 3.80,
            "radiation_cps": 32
        }

        # Сохраняем данные
        self.telemetry.save_telemetry(test_data)

        # Получаем последние данные
        latest = self.telemetry.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest['sequence'], 2)


def run_tests():
    """Запуск всех тестов"""
    print("Запуск упрощенного набора тестов CubeSat 1U...")
    
    # Создание тест-раннера
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Добавление тестов
    suite.addTests(loader.loadTestsFromTestCase(TestSecurityModule))
    suite.addTests(loader.loadTestsFromTestCase(TestCommunicationHandler))
    suite.addTests(loader.loadTestsFromTestCase(TestTelemetryHandler))

    # Запуск тестов
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print(f"\nРезультаты тестирования:")
    print(f"Пройдено: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Неудач: {len(result.failures)}")
    print(f"Ошибок: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)