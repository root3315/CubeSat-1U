# API документация CubeSat 1U

## Обзор

CubeSat 1U система предоставляет несколько уровней API для взаимодействия:
- UART API (для связи с STM32)
- UDP API (для связи с наземной станцией)
- Web API (для веб-интерфейса)
- Internal API (для внутреннего взаимодействия компонентов)

## UART API (STM32 ↔ Raspberry Pi)

### Телеметрия (STM32 → Raspberry Pi)
**Формат пакета (40 байт):**
```
Offset | Size | Type    | Description
-------|------|---------|------------------
0      | 1    | uint8   | Sync byte 1 (0xAA)
1      | 1    | uint8   | Sync byte 2 (0x55)
2      | 1    | uint8   | Packet type (0x01)
3-4    | 2    | uint16  | Sequence number
5-8    | 4    | uint32  | Timestamp
9-12   | 4    | float   | Magnetometer X
13-16  | 4    | float   | Magnetometer Y
17-20  | 4    | float   | Magnetometer Z
21-22  | 2    | uint16  | Corrosion raw
23-26  | 4    | uint32  | Radiation CPS
27-30  | 4    | float   | Temperature BME
31-34  | 4    | float   | Pressure
35-38  | 4    | float   | Humidity
39-40  | 2    | uint16  | Battery voltage (mV)
```

### Команды (Raspberry Pi → STM32)
**Формат пакета:**
```
Offset | Size | Type    | Description
-------|------|---------|------------------
0      | 1    | uint8   | Sync byte 1 (0xAA)
1      | 1    | uint8   | Sync byte 2 (0x56)
2      | 1    | uint8   | Command ID
3-4    | 2    | uint16  | Sequence
5-6    | 2    | uint16  | Parameter length
7...   | n    | bytes   | Parameters (JSON)
last-1 | 2    | uint16  | Checksum
```

**Поддерживаемые команды:**
- 0x01: PING - Проверка соединения
- 0x02: GET_TELEMETRY - Запрос телеметрии
- 0x03: CAPTURE_IMAGE - Сделать фото
- 0x04: SET_MODE - Установить режим
- 0x05: RESET - Сброс системы
- 0x06: CHECK_UPDATES - Проверить обновления
- 0x07: START_UPDATE - Начать обновление
- 0x08: CANCEL_UPDATE - Отменить обновление
- 0x09: BEACON - Отправить статус
- 0x0A: GET_SYSTEM_INFO - Получить информацию о системе

## UDP API (Raspberry Pi ↔ Ground Station)

### Формат сообщений
Все сообщения передаются в формате JSON через UDP на порт 5000.

### Типы сообщений

#### Телеметрия (от Raspberry Pi)
```json
{
  "type": "TELEMETRY",
  "data": {
    "sequence": 1234,
    "timestamp": 1234567890.123,
    "mag_x": 0.123,
    "mag_y": -0.456,
    "mag_z": 0.789,
    "corrosion_raw": 1024,
    "radiation_cps": 42,
    "temperature_bme": 25.6,
    "pressure": 1013.25,
    "humidity": 45.2,
    "battery_voltage": 3.78,
    "power_mode": "NORMAL"
  }
}
```

#### Команды (от Ground Station)
```json
{
  "type": "COMMAND",
  "command_id": 1,
  "params": {
    "action": "capture_image"
  },
  "timestamp": 1234567890.123,
  "nonce": "random_nonce_string",
  "signature": "hmac_signature"
}
```

#### Статус (от Raspberry Pi)
```json
{
  "type": "STATUS",
  "data": {
    "state": "NOMINAL",
    "uptime": 3600,
    "free_space": 2.5,
    "temp": 35.2,
    "images": 42,
    "power_mode": "NORMAL"
  }
}
```

## Web API (Ground Station)

### Веб-интерфейс
Веб-интерфейс построен на Streamlit и предоставляет:
- Визуализацию телеметрии
- Интерфейс отправки команд
- Просмотр изображений
- Экспорт данных

### REST API (планируется)
В будущем планируется добавить полноценный REST API для интеграции.

## Internal API (внутреннее взаимодействие)

### Flight Controller API
```python
class CubeSatFlightController:
    def execute_command(self, cmd: dict) -> bool:
        """Выполнить команду"""
    
    def get_priority_telemetry(self) -> dict:
        """Получить приоритетную телеметрию"""
    
    def update_power_mode(self):
        """Обновить режим питания"""
```

### Security API
```python
class SecurityManager:
    def create_signature(self, data: bytes, timestamp: float = None) -> str:
        """Создать подпись для данных"""
    
    def verify_signature(self, data: bytes, signature: str, timestamp: float = None) -> bool:
        """Проверить подпись"""
    
    def authenticate_command(self, command_data: dict, signature: str, nonce: str, timestamp: float) -> tuple[bool, str]:
        """Аутентифицировать команду"""
```

### Communication API
```python
class CommunicationHandler:
    def send_to_stm32(self, data: dict) -> bool:
        """Отправить данные в STM32"""
    
    def send_to_radio(self, data: dict) -> bool:
        """Отправить данные по радио"""
    
    def send_to_ground_station(self, data: dict) -> bool:
        """Отправить данные на наземную станцию"""
```

## Безопасность API

### Аутентификация
Все команды должны быть подписаны HMAC-SHA256 подписью с использованием общего секретного ключа.

### Защита от повторного использования
Каждая команда должна содержать одноразовое число (nonce), которое регистрируется и не может быть использовано повторно.

### Валидация времени
Команды должны иметь временную метку, и разница между текущим временем и временной меткой не должна превышать 15 секунд.

## Ошибки и исключения

### Коды ошибок
- 200: OK - Успешное выполнение
- 400: BAD_REQUEST - Неправильный формат запроса
- 401: UNAUTHORIZED - Не пройдена аутентификация
- 403: FORBIDDEN - Команда не разрешена
- 408: REQUEST_TIMEOUT - Таймаут запроса
- 500: INTERNAL_ERROR - Внутренняя ошибка системы

## Примеры использования

### Отправка команды
```python
from security import create_secure_command

# Создание безопасной команды
secure_cmd = create_secure_command(
    command_id=3,  # CAPTURE_IMAGE
    params={"resolution": "high"},
    security_manager=security
)

# Отправка команды
comm.send_to_stm32(secure_cmd)
```

### Обработка телеметрии
```python
def process_telemetry(telemetry_data):
    # Проверка целостности данных
    if validate_telemetry(telemetry_data):
        # Обработка данных
        handle_telemetry(telemetry_data)
        # Логирование
        log_telemetry(telemetry_data)
```

## Лицензия
MIT License