# Безопасность CubeSat 1U системы

## Обзор

CubeSat 1U система включает многоуровневую систему безопасности для защиты от несанкционированного доступа, подделки команд и компрометации данных.

## Уровни безопасности

### 1. Аутентификация команд

#### HMAC-подписи
Все команды, отправляемые на CubeSat, должны быть подписаны HMAC-SHA256 подписью с использованием общего секретного ключа.

**Процесс:**
1. Команда сериализуется в JSON
2. Добавляются временная метка и nonce
3. Создается HMAC-подпись
4. Команда отправляется вместе с подписью

**Пример:**
```python
import hmac
import hashlib
import json
import time

def create_secure_command(command_id, params, shared_secret):
    timestamp = time.time()
    nonce = generate_random_nonce()
    
    command = {
        'command_id': command_id,
        'params': params,
        'timestamp': timestamp,
        'nonce': nonce
    }
    
    # Создание сообщения для подписи
    message = json.dumps(command, sort_keys=True).encode('utf-8')
    
    # Создание HMAC-подписи
    signature = hmac.new(
        shared_secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    
    # Добавление подписи к команде
    command['signature'] = signature
    return command
```

### 2. Защита от повторного использования

#### Одноразовые числа (Nonce)
Каждая команда должна содержать уникальное одноразовое число (nonce), которое регистрируется и не может быть использовано повторно.

**Реализация:**
```python
class SecurityManager:
    def __init__(self, shared_secret):
        self.shared_secret = shared_secret
        self.nonce_registry = {}  # Словарь для отслеживания nonce
        self.nonce_ttl = 300  # Время жизни nonce (5 минут)
    
    def is_nonce_valid(self, nonce):
        """Проверка валидности nonce"""
        current_time = time.time()
        
        # Проверка существования nonce
        if nonce in self.nonce_registry:
            timestamp = self.nonce_registry[nonce]
            # Проверка времени жизни
            if current_time - timestamp > self.nonce_ttl:
                # Удаление просроченного nonce
                del self.nonce_registry[nonce]
                return False
            return True
        return False
    
    def register_nonce(self, nonce):
        """Регистрация nonce как использованного"""
        self.nonce_registry[nonce] = time.time()
        
        # Очистка просроченных nonce
        current_time = time.time()
        expired_nonces = [
            n for n, t in self.nonce_registry.items()
            if current_time - t > self.nonce_ttl
        ]
        for n in expired_nonces:
            del self.nonce_registry[n]
```

### 3. Валидация временных меток

Все команды должны иметь временную метку, и разница между текущим временем и временной меткой не должна превышать 15 секунд.

```python
def authenticate_command(self, command_data, signature, nonce, timestamp):
    """Аутентификация команды"""
    # Проверка времени - команда должна быть актуальной
    current_time = time.time()
    if abs(current_time - timestamp) > 15:  # 15 секунд
        return False, "Command too old"
    
    # Проверка nonce на уникальность
    if self.is_nonce_valid(nonce):
        return False, "Nonce already used"
    
    # Проверка подписи
    command_json = json.dumps(command_data, sort_keys=True).encode('utf-8')
    if not self.verify_signature(command_json, signature, timestamp):
        return False, "Invalid signature"
    
    # Регистрация nonce как использованного
    self.register_nonce(nonce)
    
    return True, "Authentication successful"
```

### 4. Управление ключами

#### Генерация ключей
Система включает автоматическую генерацию безопасных ключей:

```python
import secrets

def generate_security_keys():
    """Генерация безопасных ключей"""
    # Генерация сильного общего секрета
    shared_secret = secrets.token_urlsafe(32)  # 32 байта = 256 бит
    
    # Создание сертификатов (упрощенно)
    # В реальной системе использовались бы настоящие сертификаты
    return shared_secret
```

#### Обновление ключей
Система поддерживает обновление ключей безопасности без остановки работы.

### 5. Защита данных

#### Шифрование (опционально)
Данные могут быть зашифрованы при необходимости:

```python
def encrypt_telemetry(self, telemetry_data):
    """Шифрование данных телеметрии"""
    import base64
    
    json_str = json.dumps(telemetry_data)
    # Простое "шифрование" - XOR с частью секретного ключа
    encrypted = bytearray()
    secret_bytes = self.shared_secret.encode('utf-8')

    for i, char in enumerate(json_str.encode('utf-8')):
        encrypted.append(char ^ secret_bytes[i % len(secret_bytes)])

    return base64.b64encode(bytes(encrypted))
```

### 6. Защита от атак

#### Защита от атак переполнения
Ограничение размера входящих данных и очередей.

#### Защита от DoS-атак
Ограничение частоты команд от одного источника.

#### Защита от атак повторного использования
Строгая проверка nonce и временных меток.

## Проверка безопасности

### Тесты безопасности
Система включает автоматические тесты безопасности:

```python
def test_nonce_replay_protection():
    """Тест защиты от повторного использования nonce"""
    security = SecurityManager(shared_secret="replay_test")

    # Создание команды
    command = {"type": "TEST", "value": 123}
    secure_cmd = create_secure_command(1, command, security)

    # Первая валидация должна пройти
    is_valid1, msg1 = validate_secure_command(secure_cmd, security)
    assert is_valid1, f"Первая валидация провалилась: {msg1}"

    # Вторая валидация с тем же nonce должна провалиться
    is_valid2, msg2 = validate_secure_command(secure_cmd, security)
    assert not is_valid2, f"Защита от повторного использования не работает: {msg2}"
    assert "already used" in msg2.lower() or "nonce" in msg2.lower()
```

## Конфигурация безопасности

### Параметры безопасности в config.json
```json
{
  "security": {
    "shared_secret": "your_secure_shared_secret_here",
    "require_auth": true,
    "enable_signing": true,
    "ssl_enabled": false,
    "cert_file": "./certs/server.crt",
    "key_file": "./certs/server.key"
  },
  "monitoring": {
    "cpu_threshold": 85.0,
    "memory_threshold": 90.0,
    "disk_threshold": 95.0,
    "temp_threshold": 75.0,
    "battery_min": 3.4,
    "battery_max": 4.2
  }
}
```

## Аудит безопасности

### Логирование безопасности
Все события безопасности логируются:
- Попытки аутентификации
- Ошибки валидации
- Подозрительная активность
- Использование команд

### Мониторинг угроз
Система включает мониторинг подозрительной активности:
- Частые попытки команд
- Неверные подписи
- Повторное использование nonce
- Неправильные временные метки

## Рекомендации по безопасности

### Для разработчиков
- Использовать безопасные методы генерации случайных чисел
- Проверять все входящие данные
- Использовать строгую валидацию
- Регулярно обновлять зависимости

### Для операторов
- Регулярно обновлять ключи безопасности
- Мониторить логи безопасности
- Проводить регулярные аудиты
- Обучать персонал безопасности

## Совместимость

### Назад совместимость
Система поддерживает обратную совместимость с предыдущими версиями, но рекомендуется использовать последние безопасные методы.

## Лицензия
MIT License