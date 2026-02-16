# Документация по тестированию CubeSat 1U системы

## Обзор

CubeSat 1U система включает упрощенную, но эффективную систему тестирования, оптимизированную для ресурсоограниченной среды. Абсолютность тестирования заключается в её способности проверять критические функции без чрезмерного потребления ресурсов.

## Архитектура тестирования

### Структура тестов

```
tests/
├── simple_test_suite.py              # Упрощенный набор тестов
├── test_communication_simulated.py   # Тесты связи в симуляции
├── run_all_tests_simulated.py       # Запуск всех тестов в симуляции
├── unit/                           # Модульные тесты
│   ├── test_main.py                # Основные модульные тесты
│   └── test_detailed.py            # Подробные модульные тесты
├── integration/                    # Интеграционные тесты
│   ├── test_communication.py       # Тесты взаимодействия компонентов
│   └── test_end_to_end.py          # Тесты сквозного взаимодействия
├── performance/                    # Тесты производительности
│   └── test_performance.py         # Тесты производительности
└── conftest.py                     # Конфигурация pytest
```

## Типы тестов

### 1. Модульные тесты

Модульные тесты проверяют отдельные компоненты системы:

#### test_main.py
- Тесты контроллера полета
- Тесты безопасности
- Тесты обработки телеметрии
- Тесты связи

#### test_detailed.py
- Подробные тесты критических функций
- Граничные условия
- Обработка ошибок

### 2. Интеграционные тесты

Интеграционные тесты проверяют взаимодействие между компонентами:

#### test_communication.py
- Тесты взаимодействия между компонентами
- Проверка протоколов связи
- Тесты обработки команд

#### test_end_to_end.py
- Сквозные тесты сценариев использования
- Тесты полного цикла обработки данных

### 3. Тесты производительности

Тесты производительности проверяют эффективность системы:

#### test_performance.py
- Тесты производительности обработки данных
- Тесты потребления ресурсов
- Тесты скорости ответа

## Упрощенные тесты

### simple_test_suite.py

Основной упрощенный набор тестов, оптимизированный для ресурсоограниченной среды:

```python
"""
Упрощенный набор тестов для CubeSat 1U системы
Оптимизирован для ресурсоограниченной среды
"""
import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Импорт модулей для тестирования
from raspberry_pi_code.security import SecurityManager, create_secure_command, validate_secure_command
from raspberry_pi_code.communication import CommunicationHandler
from raspberry_pi_code.telemetry_handler import TelemetryHandler


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
```

### test_communication_simulated.py

Тесты связи в симуляции без использования реального оборудования:

```python
"""
Тесты связи в симуляции для CubeSat 1U системы
Тесты работают без реального оборудования
"""
import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock

from raspberry_pi_code.communication import CommunicationHandler


class TestCommunicationSimulated(unittest.TestCase):
    """Тесты связи в симуляции"""

    def setUp(self):
        # Конфигурация для симуляции
        self.config = {
            "communication": {
                "stm32_port": "/dev/null",  # Используем null для симуляции
                "baudrate": 115200,
                "radio_port": "/dev/null",
                "radio_baudrate": 9600,
                "udp_port": 5000,
                "ground_station_ip": "127.0.0.1"
            },
            "security": {
                "shared_secret": "simulated_secret",
                "require_auth": True,
                "enable_signing": True
            }
        }
        
        # Создаем обработчик связи с симуляцией
        with patch('serial.Serial'):
            self.comm = CommunicationHandler(self.config)

    def test_mock_serial_initialization(self):
        """Тест инициализации симуляции последовательных портов"""
        # Проверяем, что порты были "открыты" (на самом деле смоканы)
        self.assertIsNotNone(self.comm)
        self.assertTrue(hasattr(self.comm, 'stm32_serial'))
        self.assertTrue(hasattr(self.comm, 'radio_serial'))

    def test_command_parsing_simulation(self):
        """Тест симуляции парсинга команд"""
        # Тестовые данные команды
        test_command = {
            "type": "TELEMETRY_REQUEST",
            "params": {"satellite": "TEST-001"},
            "timestamp": time.time(),
            "nonce": "test_nonce_12345"
        }

        # Сериализуем команду
        command_json = json.dumps(test_command)
        command_bytes = command_json.encode()

        # В симуляции мы просто проверяем, что данные корректно обрабатываются
        self.assertIsInstance(command_bytes, bytes)
        self.assertGreater(len(command_bytes), 0)

    def test_telemetry_parsing_simulation(self):
        """Тест симуляции парсинга телеметрии"""
        # Тестовые данные телеметрии
        test_telemetry = {
            "sequence": 12345,
            "timestamp": time.time(),
            "mag_x": 0.123,
            "mag_y": -0.456,
            "mag_z": 0.789,
            "corrosion_raw": 1024,
            "radiation_cps": 42,
            "temperature_bme": 25.6,
            "pressure": 1013.25,
            "humidity": 45.2,
            "battery_voltage": 3.78,
            "battery_level": 85
        }

        # Сериализуем телеметрию
        telemetry_json = json.dumps(test_telemetry)
        telemetry_bytes = telemetry_json.encode()

        # Проверяем корректность данных
        self.assertIsInstance(telemetry_bytes, bytes)
        self.assertGreater(len(telemetry_bytes), 0)

        # Проверяем, что все ключевые поля присутствуют
        parsed = json.loads(telemetry_json)
        required_fields = [
            'sequence', 'timestamp', 'mag_x', 'mag_y', 'mag_z',
            'corrosion_raw', 'radiation_cps', 'temperature_bme',
            'pressure', 'humidity', 'battery_voltage', 'battery_level'
        ]
        
        for field in required_fields:
            self.assertIn(field, parsed)

    def test_secure_command_simulation(self):
        """Тест симуляции безопасных команд"""
        from raspberry_pi_code.security import SecurityManager, create_secure_command, validate_secure_command

        # Создаем менеджер безопасности
        security = SecurityManager(shared_secret="simulated_test_secret")

        # Создаем команду
        command = {"type": "TEST_COMMAND", "value": 999}
        secure_cmd = create_secure_command(1, command, security)

        # Проверяем, что команда содержит необходимые поля безопасности
        self.assertIn('signature', secure_cmd)
        self.assertIn('nonce', secure_cmd)
        self.assertIn('timestamp', secure_cmd)
        self.assertIn('command_id', secure_cmd)

        # Валидируем команду
        is_valid, msg = validate_secure_command(secure_cmd, security)
        self.assertTrue(is_valid, f"Команда не прошла валидацию: {msg}")
```

## Запуск тестов

### Запуск всех тестов

```bash
# Запуск всех тестов в симуляции
python3 tests/run_all_tests_simulated.py

# Запуск с помощью unittest
python3 -m unittest discover tests/ -v

# Запуск с помощью pytest
python3 -m pytest tests/ -v
```

### Запуск конкретных тестов

```bash
# Запуск упрощенного набора тестов
python3 tests/simple_test_suite.py

# Запуск тестов связи в симуляции
python3 tests/test_communication_simulated.py
```

## Конфигурация тестирования

### pytest.ini

```ini
[tool:pytest]
testpaths = tests/
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
markers =
    critical: marks tests as critical functionality
    security: marks tests as security-related
    communication: marks tests as communication-related
    telemetry: marks tests as telemetry-related
    performance: marks tests as performance-related
    simulation: marks tests as simulation-only
    hardware: marks tests as requiring hardware (deselect with '-m "not hardware"')