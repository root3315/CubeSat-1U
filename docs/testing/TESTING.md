# Тестирование CubeSat 1U системы

## Обзор

CubeSat 1U система включает несколько уровней тестирования:
- Unit-тесты для отдельных компонентов
- Интеграционные тесты для взаимодействия компонентов
- Тесты производительности
- Тесты безопасности
- Тесты в режиме симуляции

## Структура тестов

```
tests/
├── simple_test_suite.py      # Упрощенный набор тестов
├── test_communication_simulated.py  # Тесты связи в симуляции
├── run_all_tests_simulated.py      # Запуск всех тестов в симуляции
├── comprehensive_test_suite.py     # Расширенный набор тестов
├── load_test_suite.py              # Тесты нагрузки
├── unit/                         # Unit-тесты
│   ├── test_main.py
│   └── test_detailed.py
└── launch.json                   # Конфигурация запуска тестов
```

## Unit-тесты

### Тестирование безопасности
```python
def test_signature_generation():
    """Проверка генерации подписей"""
    data = {"command": "test", "value": 123}
    security = SecurityManager(shared_secret="test_secret")
    signature = security.create_signature(json.dumps(data).encode())
    
    # Подпись должна быть 64 символа (SHA256)
    assert len(signature) == 64

def test_signature_verification():
    """Проверка валидации подписей"""
    data = {"command": "test", "value": 123}
    data_bytes = json.dumps(data).encode()
    security = SecurityManager(shared_secret="test_secret")
    
    signature = security.create_signature(data_bytes)
    is_valid = security.verify_signature(data_bytes, signature)
    
    assert is_valid == True

def test_nonce_replay_protection():
    """Проверка защиты от повторного использования nonce"""
    security = SecurityManager(shared_secret="replay_test")
    command = {"type": "TEST", "value": 123}
    secure_cmd = create_secure_command(1, command, security)
    
    # Первая валидация должна пройти
    is_valid1, msg1 = validate_secure_command(secure_cmd, security)
    assert is_valid1 == True
    
    # Вторая валидация с тем же nonce должна провалиться
    is_valid2, msg2 = validate_secure_command(secure_cmd, security)
    assert is_valid2 == False
```

### Тестирование телеметрии
```python
def test_telemetry_processing_performance():
    """Тест производительности обработки телеметрии"""
    import time
    from telemetry_handler import TelemetryHandler

    config = {"storage": {"base_path": "/tmp"}}
    handler = TelemetryHandler(config)

    # Генерация тестовых данных
    telemetry_data = []
    for i in range(100):
        data = {
            "timestamp": time.time(),
            "sequence": i,
            "temperature_bme": 20 + (i % 5),
            "pressure": 1013 + (i % 10),
            "humidity": 45 + (i % 15),
            "battery_voltage": 3.8 + (i % 2) * 0.1,
            "battery_level": 90 + (i % 10),
            "radiation_cps": 30 + (i % 20),
            "mag_x": 0.25 + (i % 5) * 0.01,
            "mag_y": -0.18 + (i % 5) * 0.01,
            "mag_z": 0.45 + (i % 5) * 0.01
        }
        telemetry_data.append(data)

    # Измерение времени обработки
    start_time = time.time()
    for data in telemetry_data:
        handler.save_telemetry(data)
    end_time = time.time()

    processing_time = end_time - start_time
    assert processing_time < 2.0  # Обработка 100 пакетов за менее чем 2 секунды
```

## Интеграционные тесты

### Тестирование полного цикла
```python
def test_end_to_end_workflow():
    """Тест полного цикла работы системы"""
    # Инициализация компонентов
    security = SecurityManager(shared_secret="integration_test")

    # Создание и валидация безопасной команды
    command = {"type": "TELEMETRY_REQUEST", "params": {"satellite": "TEST-001"}}
    secure_cmd = create_secure_command(2, command, security)

    is_valid, msg = validate_secure_command(secure_cmd, security)
    assert is_valid == True, f"Валидация команды провалена: {msg}"

    # Тест обработки телеметрии
    from telemetry_handler import TelemetryHandler
    config = {"storage": {"base_path": "/tmp"}}
    telemetry_handler = TelemetryHandler(config)
    
    telemetry = {
        "satellite_id": "TEST-001",
        "temperature": 25.5,
        "voltage": 3.75,
        "signal_strength": -65
    }

    # Сохранение телеметрии
    success = telemetry_handler.save_telemetry(telemetry)
    assert success == True, "Не удалось сохранить телеметрию"
```

## Тесты в режиме симуляции

Тесты в режиме симуляции позволяют проверить логику системы без реального оборудования:

```python
def test_flight_controller_simulation():
    """Тест контроллера полета в режиме симуляции"""
    import sys
    import os
    
    # Подмена GPIO для симуляции
    class MockGPIO:
        BCM = OUT = IN = HIGH = LOW = None
        def setmode(self, *args): pass
        def setup(self, *args): pass
        def output(self, *args): pass
        def cleanup(self): pass

    # Замена модуля
    sys.modules['RPi.GPIO'] = MockGPIO()

    # Импорт и тестирование
    from flight_controller import CubeSatFlightController
    controller = CubeSatFlightController()
    
    # Проверка инициализации
    assert controller is not None
    assert controller.state == 'BOOT'
    
    # Остановка контроллера
    controller.shutdown()
```

## Тесты производительности

### Тест загрузки CPU
```python
def test_cpu_load_under_normal_conditions():
    """Тест загрузки CPU при нормальных условиях"""
    import psutil
    import time
    
    initial_cpu = psutil.cpu_percent(interval=1)
    
    # Выполнение типичных операций
    for i in range(1000):
        # Симуляция обработки данных
        data = {"value": i, "timestamp": time.time()}
        # Обработка данных
        processed = {"processed_value": data["value"] * 2}
    
    final_cpu = psutil.cpu_percent(interval=1)
    
    # Загрузка CPU не должна превышать 80% при нормальных условиях
    assert final_cpu < 80
```

## Запуск тестов

### Запуск всех тестов
```bash
# Запуск упрощенного набора тестов
python3 tests/simple_test_suite.py

# Запуск всех тестов с помощью pytest
python3 -m pytest tests/ -v

# Запуск тестов в режиме симуляции
python3 tests/run_all_tests_simulated.py
```

### Запуск конкретных тестов
```bash
# Запуск unit-тестов
python3 -m pytest tests/unit/ -v

# Запуск тестов безопасности
python3 -m pytest -m security

# Запуск тестов производительности
python3 -m pytest -m performance
```

## Покрытие кода

Для проверки покрытия кода тестами:
```bash
python3 -m pytest --cov=. --cov-report=html
```

## Тестирование в Docker

Система также может быть протестирована в Docker-контейнерах:
```bash
# Сборка образа
docker build -f Dockerfile -t cubesat-pi .

# Запуск тестов в контейнере
docker run --rm cubesat-pi python3 -m pytest tests/
```

## CI/CD интеграция

Тесты интегрированы в CI/CD pipeline:
- Автоматический запуск при каждом коммите
- Проверка качества кода
- Проверка безопасности
- Тестирование совместимости

## Требования к тестам

### Покрытие
- Минимум 80% покрытия кода
- Все критические пути должны быть протестированы
- Тесты безопасности обязательны

### Производительность
- Тесты не должны занимать более 5 минут
- Память не должна превышать 512MB
- CPU не должен превышать 80%

### Надежность
- Тесты должны быть стабильными
- Не должно быть ложных срабатываний
- Тесты должны работать в разных окружениях

## Лицензия
MIT License