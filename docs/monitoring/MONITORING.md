# Мониторинг и логирование CubeSat 1U системы

## Обзор

CubeSat 1U система включает упрощенную, но эффективную систему мониторинга и логирования, оптимизированную для ресурсоограниченной среды.

## Система логирования

### Упрощенный логгер

Система использует упрощенный логгер, оптимизированный для CubeSat:

```python
class SimpleLogger:
    """
    Упрощенный логгер, оптимизированный для ресурсоограниченной среды
    """
    def __init__(self, name: str = "CubeSat", log_dir: str = "./logs"):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Настройка основного логгера
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)  # Уровень INFO для эффективности

        # Очистка существующих хендлеров
        self.logger.handlers.clear()

        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        # Файловый хендлер с ротацией
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{name.lower()}.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3  # Уменьшенное количество резервных копий
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Условный консольный хендлер
        if os.environ.get('CUBESAT_DEBUG', '').lower() == 'true':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        self.logger.info(f"Simple logger initialized for {name}")
```

### Уровни логирования

- **DEBUG**: Подробная информация для диагностики (включается только при отладке)
- **INFO**: Общая информация о работе системы
- **WARNING**: Предупреждения о потенциально проблемных ситуациях
- **ERROR**: Ошибки, не приводящие к остановке системы
- **CRITICAL**: Критические ошибки, требующие немедленного внимания

### Формат логов

Формат записи в логах:
```
TIMESTAMP - LEVEL - MESSAGE
```

Пример:
```
2026-02-15 12:00:00 - INFO - CubeSat 1U Flight Controller v1.0 - Simplified
2026-02-15 12:00:05 - WARNING - Low disk space: 0.3 GB
2026-02-15 12:00:10 - ALERT-HIGH - Battery voltage critically low: 3.5V
```

## Система мониторинга

### Упрощенный мониторинг здоровья

Система включает упрощенный мониторинг здоровья:

```python
class SimpleHealthMonitor:
    """
    Упрощенный монитор здоровья системы
    """
    def __init__(self, logger: SimpleLogger, config: Dict[str, Any]):
        self.logger = logger
        self.config = config
        self.running = False
        self.monitor_thread = None

        # Пороги для алертов
        self.thresholds = {
            'cpu_percent': config.get('monitoring', {}).get('cpu_threshold', 85.0),
            'memory_percent': config.get('monitoring', {}).get('memory_threshold', 90.0),
            'disk_percent': config.get('monitoring', {}).get('disk_threshold', 95.0),
            'temperature': config.get('monitoring', {}).get('temp_threshold', 75.0),
            'battery_voltage_min': config.get('monitoring', {}).get('battery_min', 3.4),
            'battery_voltage_max': config.get('monitoring', {}).get('battery_max', 4.2)
        }
```

### Проверяемые параметры

#### Системные параметры
- **Загрузка CPU**: Проверка использования процессора
- **Использование памяти**: Проверка использования RAM
- **Доступное место**: Проверка свободного места на диске
- **Температура CPU**: Проверка температуры процессора

#### Параметры CubeSat
- **Напряжение батареи**: Проверка уровня заряда
- **Радиационный фон**: Проверка уровня радиации
- **Температура датчиков**: Проверка температурных датчиков
- **Состояние оборудования**: Проверка состояния датчиков и оборудования

### Частота проверок

Частота проверок оптимизирована для экономии ресурсов:
- **Системные параметры**: Каждые 60 секунд
- **Параметры телеметрии**: При получении новых данных
- **Параметры питания**: Каждые 30 секунд
- **Состояние оборудования**: При обращении к оборудованию

## Алерты и уведомления

### Уровни алертов

- **LOW**: Низкий приоритет, информационные сообщения
- **MEDIUM**: Средний приоритет, требует внимания
- **HIGH**: Высокий приоритет, требует реакции
- **CRITICAL**: Критический уровень, требует немедленного вмешательства

### Примеры алертов

```python
def alert(self, message: str, severity: str = "HIGH"):
    """Специальное логирование алертов"""
    alert_msg = f"[ALERT-{severity}] {message}"
    self.logger.warning(alert_msg)
```

Примеры алертов:
- `[ALERT-CRITICAL] Battery voltage critically low: 3.2V`
- `[ALERT-HIGH] Disk usage high: 96.5%`
- `[ALERT-MEDIUM] High CPU temperature: 78°C`
- `[ALERT-HIGH] Radiation level high: 150 CPS`

## Управление питанием

### Мониторинг питания

Система включает специальный мониторинг питания:

```python
def update_power_mode(self):
    """Обновление режима питания на основе уровня заряда батареи"""
    try:
        # Получение последних данных телеметрии
        latest_telemetry = self.telemetry.get_latest()
        battery_voltage = latest_telemetry.get('battery_voltage', 4.2)

        # Обновление режима питания на основе уровня заряда
        if battery_voltage < self.config['power_management']['low_battery_threshold']:
            if self.power_mode != 'LOW_POWER':
                self.power_mode = 'LOW_POWER'
                self.logger.info(f"Switched to LOW_POWER mode (battery: {battery_voltage:.2f}V)")
        elif battery_voltage < 3.4:  # Критический уровень
            if self.power_mode != 'CRITICAL':
                self.power_mode = 'CRITICAL'
                self.logger.warning(f"Switched to CRITICAL power mode (battery: {battery_voltage:.2f}V)")
        else:
            if self.power_mode != 'NORMAL':
                self.power_mode = 'NORMAL'
                self.logger.info(f"Switched to NORMAL power mode (battery: {battery_voltage:.2f}V)")

    except Exception as e:
        self.logger.error(f"Error updating power mode: {e}")
```

### Режимы питания

- **NORMAL**: Полная функциональность, стандартная частота опроса
- **LOW_POWER**: Сниженная активность, увеличенные интервалы опроса
- **CRITICAL**: Минимальная активность, только критические функции

## Логирование телеметрии

### Обработка телеметрии

Система логирует важные параметры телеметрии:

```python
def log_telemetry_health(self, telemetry_data: Dict[str, Any]):
    """Логирование данных телеметрии для мониторинга"""
    try:
        # Проверка напряжения батареи
        battery_voltage = telemetry_data.get('battery_voltage', 0)
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

        # Проверка других параметров телеметрии
        radiation_cps = telemetry_data.get('radiation_cps', 0)
        if radiation_cps > 100:  # Пример порога
            self.logger.alert(
                f"High radiation detected: {radiation_cps} CPS",
                severity="MEDIUM"
            )

        # Логирование нормальных значений для анализа
        self.logger.info(
            f"Telemetry: batt={battery_voltage}V, temp={telemetry_data.get('temperature_bme', 0)}°C"
        )

    except Exception as e:
        self.logger.exception(f"Error checking telemetry health: {e}")
```

## Управление файлами логов

### Ротация логов

Система использует ротацию логов для экономии места:

- **Максимальный размер файла**: 5MB
- **Количество резервных копий**: 3
- **Общий объем логов**: ~20MB

### Очистка старых файлов

Система автоматически очищает старые файлы и данные:

```python
def cleanup_old_files(self):
    """Удаление старых файлов при нехватке места"""
    try:
        self.logger.info("Cleaning up old files")

        # Очистка старых файлов телеметрии
        self.telemetry.cleanup_old_files(days=30)

        # Очистка старых изображений
        image_path = os.path.join(self.config['storage']['base_path'], 'images')
        if os.path.exists(image_path):
            images = sorted([os.path.join(image_path, f) for f in os.listdir(image_path)
                           if f.startswith('raw_')])

            # Удаление старейших 20%
            delete_count = max(1, len(images) // 5)
            for f in images[:delete_count]:
                try:
                    os.remove(f)
                    self.logger.info(f"Deleted old file: {f}")
                except Exception as e:
                    self.logger.error(f"Error deleting {f}: {e}")

    except Exception as e:
        self.logger.error(f"Error during file cleanup: {e}")
```

## Мониторинг ресурсов

### Экономия ресурсов

Система оптимизирована для экономии ресурсов:

- **Минимизация частоты проверок**
- **Использование эффективных структур данных**
- **Ограничение размера очередей**
- **Асинхронная обработка**

### Параметры мониторинга

| Параметр | Норма | Порог предупреждения | Порог алерта |
|----------|-------|---------------------|--------------|
| CPU % | < 50% | 70% | 85% |
| Память % | < 60% | 80% | 90% |
| Диск % | < 70% | 85% | 95% |
| Температура | < 60°C | 70°C | 75°C |
| Напряжение батареи | 4.2V | 3.6V | 3.4V |

## Визуализация в веб-интерфейсе

### Отображение статуса

Веб-интерфейс наземной станции отображает:

- **Текущий статус системы**
- **Уровень заряда батареи**
- **Температуру компонентов**
- **Свободное место**
- **Активные алерты**

### Графики телеметрии

- **История изменения параметров**
- **Тренды и аномалии**
- **Сравнение с пороговыми значениями**

## Тестирование мониторинга

### Тесты мониторинга

Система включает тесты для проверки мониторинга:

```python
def test_system_monitoring():
    """Тест системы мониторинга"""
    from logging_monitoring import SimpleLogger, SimpleHealthMonitor
    
    # Создание логгера
    logger = SimpleLogger("TestLogger", "./test_logs")
    
    # Создание конфигурации для теста
    config = {
        "monitoring": {
            "cpu_threshold": 85.0,
            "memory_threshold": 90.0,
            "disk_threshold": 95.0,
            "temp_threshold": 75.0,
            "battery_min": 3.4,
            "battery_max": 4.2,
            "check_interval": 60
        }
    }
    
    # Создание монитора
    monitor = SimpleHealthMonitor(logger, config)
    
    # Проверка инициализации
    assert monitor is not None
    assert monitor.thresholds['cpu_percent'] == 85.0
    
    print("✓ Тест мониторинга пройден")
```

## Аварийные процедуры

### Действия при алертах

- **CRITICAL алерты**: Немедленное уведомление оператора
- **HIGH алерты**: Запись в специальный журнал
- **MEDIUM алерты**: Регулярный мониторинг
- **LOW алерты**: Архивирование для анализа

### Восстановление после сбоев

Система включает механизмы автоматического восстановления:

```python
def restart_dead_threads(self, dead_thread_names):
    """Перезапуск умерших потоков"""
    thread_map = {
        "STM32 Reader": self.stm32_reader_thread,
        "STM32 Writer": self.stm32_writer_thread,
        "Command Processor": self.command_processor_thread,
        # ... другие потоки
    }

    for thread_name in dead_thread_names:
        if thread_name in thread_map:
            try:
                new_thread = threading.Thread(target=thread_map[thread_name], name=thread_name, daemon=True)
                new_thread.start()
                # Заменяем умерший поток новым
                for i, t in enumerate(self.threads):
                    if t.name == thread_name:
                        self.threads[i] = new_thread
                        break
                self.logger.info(f"Restarted thread: {thread_name}")
            except Exception as e:
                self.logger.error(f"Failed to restart thread {thread_name}: {e}")
```

## Лицензия
MIT License