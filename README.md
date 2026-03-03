# CubeSat 1U (root3315-ui) - Техническая Документация

## 📋 Обзор Проекта

**CubeSat 1U** - это система управления миниатюрным спутником формата CubeSat с веб-интерфейсом наземной станции.

### Статус Проекта
- ✅ **Все модули работают корректно**
- ✅ **14 критических исправлений безопасности применено**
- ✅ **Код прошел тестирование**
- ✅ **Документация обновлена**

---

## 🏗️ Архитектура Проекта

```
CubeSat-1U-root3315-ui/
├── src/
│   ├── raspberry-pi-code/        # Код для Raspberry Pi (бортовой компьютер)
│   │   ├── flight_controller.py    # Основной контроллер полета
│   │   ├── communication.py        # Обработка связи (UART, UDP)
│   │   ├── security.py             # HMAC аутентификация
│   │   ├── camera_handler.py       # Обработка камеры
│   │   ├── telemetry_handler.py    # Обработка телеметрии (SQLite)
│   │   ├── logging_monitoring.py   # Логирование и мониторинг
│   │   └── ota_updater.py          # OTA обновления
│   │
│   ├── ground-station/           # Веб-интерфейс наземной станции
│   │   ├── ground_station.py       # Streamlit веб-интерфейс
│   │   ├── command_sender.py       # Отправка команд
│   │   ├── telemetry_viewer.py     # Просмотр телеметрии
│   │   ├── image_viewer.py         # Просмотр изображений
│   │   └── ssl_tls_handler.py      # SSL/TLS для наземной станции
│   │
│   └── stm32-firmware/           # Прошивка для STM32 (микроконтроллер)
│
├── config/                       # Конфигурация
│   ├── config.json               # Основная конфигурация
│   ├── ground_config.json        # Конфигурация наземной станции
│   └── docker-compose.yml        # Docker композиция
│
├── scripts/                      # Скрипты
│   ├── deploy.sh                 # Развертывание
│   └── generate_keys.py          # Генерация ключей
│
├── docs/                         # Документация
│   └── ...
│
└── tests/                        # Тесты
    └── ...
```

---

## 🚀 Быстрый Старт

### Требования

#### Для Raspberry Pi (бортовой компьютер):
- Raspberry Pi Zero 2 W или выше
- Python 3.9+
- Камера Raspberry Pi (опционально)
- STM32 микроконтроллер (опционально)

#### Для наземной станции:
- Python 3.9+
- Веб-браузер

### Установка

#### 1. Установка зависимостей

```bash
# Для Raspberry Pi
cd src/raspberry-pi-code
pip3 install -r requirements.txt

# Для наземной станции
cd src/ground-station
pip3 install -r requirements.txt
```

#### 2. Генерация ключей безопасности

```bash
# На Raspberry Pi
cd /path/to/CubeSat-1U-root3315-ui
export CUBESAT_SHARED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Или используйте скрипт генерации
python3 scripts/generate_keys.py
```

#### 3. Настройка конфигурации

Отредактируйте `config/config.json`:
```json
{
    "security": {
        "shared_secret": "${CUBESAT_SHARED_SECRET}",
        "require_auth": true,
        "enable_signing": true
    }
}
```

#### 4. Запуск

```bash
# Запуск бортового контроллера (на Raspberry Pi)
cd src/raspberry-pi-code
python3 flight_controller.py

# В отдельном терминале - запуск наземной станции
cd src/ground-station
streamlit run ground_station.py
```

Наземная станция будет доступна по адресу: **http://localhost:8501**

---

## 🔧 Компоненты Системы

### 1. Flight Controller (`flight_controller.py`)

<<<<<<< HEAD

## Благодарности

Проект основан на оригинальной разработке [oliya09/CubeSat_1u](https://github.com/oliya09/CubeSat_1u) и представляет собой её модернизированную версию с улучшенной архитектурой, производительностью, документацией и другими функциями.

## Лицензия
MIT License
=======
Основной контроллер полета управляет всеми системами спутника:

**Функции:**
- Управление камерой (захват, сжатие SVD)
- Обработка телеметрии (датчики, батарея)
- Связь с STM32 и наземной станцией
- OTA обновления
- Управление питанием

**Потоки:**
- STM32 Reader - чтение телеметрии
- STM32 Writer - отправка команд
- Command Processor - обработка команд
- Image Capture - захват изображений
- Image Compressor - сжатие изображений
- Telemetry Logger - логирование
- System Health Monitor - мониторинг
- Downlink Manager - передача данных

### 2. Communication Handler (`communication.py`)

Обработка всех коммуникационных интерфейсов:

**Интерфейсы:**
- UART (STM32)
- UART (Радио)
- UDP (Наземная станция)

**Функции безопасности:**
- HMAC-SHA256 аутентификация
- Rate limiting (100 команд/мин)
- Валидация входящих пакетов

### 3. Security Module (`security.py`)

Система безопасности обеспечивает:

- HMAC-SHA256 подписи команд
- Nonce защита от replay атак
- Thread-safe операции

### 4. Telemetry Handler (`telemetry_handler.py`)

Хранение и обработка телеметрии:

- SQLite база данных
- Thread-safe доступ
- Экспорт в JSON
- Автоматическая очистка старых данных

### 5. OTA Updater (`ota_updater.py`)

Система обновлений "на лету":

- Проверка обновлений
- HMAC подпись пакетов
- Резервное копирование
- Откат при неудаче

### 6. Ground Station (`ground_station.py`)

Веб-интерфейс на Streamlit:

- Просмотр телеметрии в реальном времени
- Отправка команд
- Просмотр изображений
- Графики и статистика

---

## 🔐 Безопасность

### Примененные Исправления

| Функция | Описание |
|---------|----------|
| **HMAC Аутентификация** | Все команды подписываются HMAC-SHA256 |
| **Nonce Защита** | Защита от replay атак |
| **Rate Limiting** | 100 команд в минуту |
| **Валидация Входа** | Проверка размеров пакетов |
| **SSL/TLS** | Шифрование соединений |
| **CSRF Защита** | Включена в наземной станции |

### Настройка Безопасности

```bash
# 1. Установите секретный ключ
export CUBESAT_SHARED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 2. Сгенерируйте SSL сертификаты
openssl req -x509 -newkey rsa:2048 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -days 365 -nodes

# 3. Включите SSL в config.json
{
    "security": {
        "ssl_enabled": true,
        "require_auth": true
    }
}
```

---

## 📊 Телеметрия

### Параметры

| Параметр | Описание | Датчик |
|----------|----------|--------|
| `battery_voltage` | Напряжение батареи | ADC |
| `battery_current` | Ток потребления | ADC |
| `temperature_bme` | Температура | BME280 |
| `pressure` | Давление | BME280 |
| `humidity` | Влажность | BME280 |
| `mag_x/y/z` | Магнитное поле | LIS3MDL |
| `radiation_cps` | Радиация | Geiger counter |
| `corrosion_raw` | Коррозия | Sensor |

---

## 🧪 Тестирование

### Запуск Тестов

```bash
# Все тесты
cd tests
python3 run_all_tests_simulated.py

# Отдельные модули
python3 -m pytest tests/unit/

# Запуск конкретных тестовых модулей
python3 tests/unit/test_security.py
python3 tests/unit/test_communication.py
python3 tests/unit/test_main.py
```

### Модульные Тесты

#### Security Module (`tests/unit/test_security.py`)

Комплексные тесты для модуля безопасности `SecurityManager`:

| Категория Тестов | Описание | Кол-во Тестов |
|-----------------|----------|---------------|
| **Nonce Generation** | Генерация уникальных случайных nonce | 5 |
| **Nonce Validation** | Валидация и TTL nonce, очистка expired | 6 |
| **Signature Creation** | Создание HMAC-SHA256 подписей | 8 |
| **Signature Verification** | Проверка подписей, timing-safe comparison | 5 |
| **Command Authentication** | Аутентификация команд, проверка timestamp | 6 |
| **Replay Attack Prevention** | Предотвращение replay атак | 1 |
| **Thread Safety** | Thread-safe операции с nonce | 3 |
| **Helper Functions** | `create_secure_command`, `validate_secure_command` | 11 |
| **Edge Cases** | Unicode, binary data, empty data | 7 |

**Ключевые тестируемые функции:**
- `SecurityManager.generate_nonce()` - генерация криптографически стойких nonce
- `SecurityManager.is_nonce_valid()` / `register_nonce()` - валидация и регистрация
- `SecurityManager.create_signature()` / `verify_signature()` - HMAC подписи
- `SecurityManager.authenticate_command()` - полная аутентификация команд
- `create_secure_command()` / `validate_secure_command()` - helper функции

#### Communication Module (`tests/unit/test_communication.py`)

Комплексные тесты для модуля связи `CommunicationHandler`:

| Категория Тестов | Описание | Кол-во Тестов |
|-----------------|----------|---------------|
| **Initialization** | Инициализация handler, protocol constants | 5 |
| **Packet Parsing** | Парсинг telemetry/command/image пакетов | 9 |
| **Rate Limiting** | Rate limiting (100 команд/мин), window expiration | 4 |
| **UDP Operations** | Отправка/получение UDP, error handling | 5 |
| **Secure Command Validation** | Валидация secure команд через security manager | 4 |
| **Serial Operations** | Отправка через UART (STM32, Radio) | 5 |
| **Cleanup** | Закрытие соединений, остановка threads | 4 |
| **Edge Cases** | Malformed packets, truncated data, concurrent parsing | 5 |

**Ключевые тестируемые функции:**
- `CommunicationHandler.parse_incoming_data()` - парсинг бинарных пакетов
- `CommunicationHandler.process_udp_data()` / `process_radio_data()` - обработка
- `CommunicationHandler._check_rate_limit()` - rate limiting
- `CommunicationHandler.send_to_stm32()` / `send_to_radio()` / `send_to_ground_station()`
- `CommunicationHandler.build_command_packet()` - построение командных пакетов
- `CommunicationHandler.cleanup()` - корректная очистка ресурсов

### Проверка Модулей

```bash
# Проверка Raspberry Pi модулей
cd src/raspberry-pi-code
python3 -c "
from security import SecurityManager
from telemetry_handler import TelemetryHandler
from communication import CommunicationHandler
print('✓ Все модули импортируются успешно')
"
```

### Покрытие Тестами

| Модуль | Файл Тестов | Статус |
|--------|-------------|--------|
| `security.py` | `tests/unit/test_security.py` | ✅ 52 теста |
| `communication.py` | `tests/unit/test_communication.py` | ✅ 41 тест |
| `flight_controller.py` | `tests/unit/test_main.py` | ✅ 3 теста |
| `telemetry_handler.py` | `tests/unit/test_main.py` | ✅ 1 тест |

---

## 📝 API Документация

### Команды Наземной Станции

| Команда | Описание | Параметры |
|---------|----------|-----------|
| `PING` | Проверка связи | - |
| `GET_TELEMETRY` | Получить телеметрию | - |
| `CAPTURE_IMAGE` | Сделать снимок | - |
| `SET_SCHEDULE` | Установить интервал | `interval` (сек) |
| `TRANSMIT_FILE` | Передать файл | `filename` |
| `GET_STATUS` | Статус системы | - |
| `REBOOT` | Перезагрузка | - |
| `SHUTDOWN` | Выключение | - |

### Формат Команды

```json
{
    "type": "CAPTURE_IMAGE",
    "params": {},
    "signature": "hmac_signature",
    "timestamp": 1234567890,
    "nonce": "random_nonce"
}
```

---

## 🐳 Docker

### Запуск в Docker

```bash
cd config
docker-compose up -d
```

### Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| `cubesat-pi` | 5000/udp, 5001 | Бортовой компьютер |
| `ground-station` | 8501 | Веб-интерфейс |
| `influxdb` | 8086 | База данных (опционально) |
| `grafana` | 3000 | Визуализация (опционально) |

---

## 🔧 Устранение Неисправностей

### Проблема: Не подключается STM32

**Решение:**
```bash
# Проверьте права доступа
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyS0
```

### Проблема: Ошибка аутентификации

**Решение:**
```bash
# Проверьте секретный ключ
echo $CUBESAT_SHARED_SECRET

# Перегенерируйте ключи
python3 scripts/generate_keys.py
```

### Проблема: Камера не работает

**Решение:**
```bash
# Включите камеру
sudo raspi-config
# Interface Options -> Camera -> Enable

# Проверьте подключение
vcgencmd get_camera
```

---

## 📚 Дополнительные Ресурсы

- [API Документация](docs/api/API.md)
- [Архитектура](docs/architecture/ARCHITECTURE.md)
- [Безопасность](docs/security/SECURITY.md)
- [Развертывание](docs/deployment/DEPLOYMENT.md)
- [Docker](docs/docker/DOCKER.md)

---

## 📄 Лицензия

MIT License

---

## 👥 Контакты

По вопросам обращайтесь к документации в `docs/` или создайте issue в репозитории.
>>>>>>> 9626d9f (root3315-ui: Security fixes (14 vulnerabilities) and code improvements)
