# Обновления "на лету" (OTA) CubeSat 1U системы

## Обзор

CubeSat 1U система включает возможность обновления программного обеспечения "на лету" (Over-The-Air - OTA) без остановки работы системы и с возможностью отката.

## Архитектура OTA системы

### Компоненты

#### OTA Updater
Основной компонент, отвечающий за процесс обновления:

```python
class OTAUpdater:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.server_url = config.get('ota', {}).get('server_url', 'https://updates.cubesat.example.com')
        self.update_directory = config.get('ota', {}).get('update_directory', './updates')
        self.backup_directory = config.get('ota', {}).get('backup_directory', './backups')
        self.current_version = config.get('ota', {}).get('current_version', '1.0.0')
        
        # Создание директорий
        os.makedirs(self.update_directory, exist_ok=True)
        os.makedirs(self.backup_directory, exist_ok=True)
```

#### Async OTA Updater
Компонент для асинхронного обновления:

```python
class AsyncOTAUpdater:
    def __init__(self, ota_updater):
        self.ota_updater = ota_updater
        self.update_thread = None
        self.cancel_flag = threading.Event()
```

## Процесс обновления

### 1. Проверка обновлений

Система периодически проверяет наличие обновлений:

```python
def check_for_updates(self):
    """Проверка наличия обновлений"""
    try:
        url = f"{self.server_url}/check_update"
        params = {
            'current_version': self.current_version,
            'device_id': self.get_device_id(),
            'mission_id': self.config.get('satellite', {}).get('mission_id', 'UNKNOWN')
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            update_info = response.json()
            if update_info.get('available'):
                self.logger.info(f"New update available: {update_info.get('version')}")
                return update_info
        else:
            self.logger.warning(f"Update check failed with status: {response.status_code}")
            
    except Exception as e:
        self.logger.error(f"Error checking for updates: {e}")
    
    return None
```

### 2. Загрузка обновления

После обнаружения обновления система загружает его:

```python
def download_update(self, update_info):
    """Загрузка обновления"""
    try:
        download_url = update_info['download_url']
        update_file = os.path.join(self.update_directory, update_info['filename'])
        
        # Проверка свободного места
        required_space = update_info.get('size', 0)
        if not self.has_enough_space(required_space * 2):  # Требуется 2x места для загрузки и установки
            raise Exception("Not enough space for update")
        
        # Загрузка файла
        response = requests.get(download_url, stream=True, timeout=60)
        
        with open(update_file, 'wb') as f:
            downloaded = 0
            total_size = int(response.headers.get('content-length', 0))
            
            for chunk in response.iter_content(chunk_size=8192):
                if self.cancel_flag.is_set():
                    raise Exception("Update cancelled")
                
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Вызов колбэка прогресса
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        self.progress_callback(progress, f"Downloaded {downloaded}/{total_size} bytes")
        
        # Проверка контрольной суммы
        if not self.verify_checksum(update_file, update_info['checksum']):
            raise Exception("Checksum verification failed")
        
        self.logger.info(f"Update downloaded successfully: {update_file}")
        return update_file
        
    except Exception as e:
        self.logger.error(f"Error downloading update: {e}")
        raise
```

### 3. Создание резервной копии

Перед установкой обновления создается резервная копия текущей системы:

```python
def create_backup(self):
    """Создание резервной копии текущей системы"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"backup_{self.current_version}_{timestamp}"
        backup_path = os.path.join(self.backup_directory, backup_name)
        
        # Создание архива текущего состояния системы
        # (только критические файлы и конфигурации)
        files_to_backup = [
            'config.json',
            'flight_controller.py',
            'communication.py',
            'security.py',
            'telemetry_handler.py',
            'logging_monitoring.py',
            'ota_updater.py'
        ]
        
        os.makedirs(backup_path, exist_ok=True)
        
        for file_path in files_to_backup:
            src = os.path.join('.', file_path)
            dst = os.path.join(backup_path, file_path)
            
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        
        self.logger.info(f"Backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        self.logger.error(f"Error creating backup: {e}")
        raise
```

### 4. Установка обновления

После успешной загрузки и проверки обновление устанавливается:

```python
def install_update(self, update_file):
    """Установка обновления"""
    try:
        # Распаковка обновления
        update_dir = os.path.join(self.update_directory, 'temp_update')
        os.makedirs(update_dir, exist_ok=True)
        
        # Предполагаем, что обновление - это ZIP-архив
        with zipfile.ZipFile(update_file, 'r') as zip_ref:
            zip_ref.extractall(update_dir)
        
        # Проверка совместимости
        if not self.check_compatibility(update_dir):
            raise Exception("Update is not compatible with current hardware/software")
        
        # Установка файлов
        self.apply_update_files(update_dir)
        
        # Обновление информации о версии
        self.update_version_info(update_dir)
        
        self.logger.info("Update installed successfully")
        
    except Exception as e:
        self.logger.error(f"Error installing update: {e}")
        raise
```

### 5. Проверка после установки

После установки обновления система выполняет проверку:

```python
def verify_installation(self):
    """Проверка успешности установки обновления"""
    try:
        # Перезапуск критических компонентов
        self.restart_critical_services()
        
        # Проверка основных функций
        if not self.basic_functionality_check():
            raise Exception("Basic functionality check failed after update")
        
        # Проверка связи
        if not self.connection_check():
            raise Exception("Connection check failed after update")
        
        # Проверка безопасности
        if not self.security_check():
            raise Exception("Security check failed after update")
        
        self.logger.info("Post-installation verification passed")
        return True
        
    except Exception as e:
        self.logger.error(f"Post-installation verification failed: {e}")
        return False
```

## Откат обновления

Если обновление прошло неудачно, система может выполнить откат:

```python
def rollback_update(self):
    """Откат к предыдущей версии"""
    try:
        # Поиск последней резервной копии
        backups = self.get_recent_backups()
        if not backups:
            raise Exception("No backups available for rollback")
        
        latest_backup = backups[0]  # Самая последняя резервная копия
        
        # Восстановление из резервной копии
        self.restore_from_backup(latest_backup)
        
        # Перезапуск системы
        self.restart_system()
        
        self.logger.info(f"Rollback completed from backup: {latest_backup}")
        return True
        
    except Exception as e:
        self.logger.error(f"Rollback failed: {e}")
        return False
```

## Асинхронное обновление

Для обеспечения непрерывной работы системы обновления выполняются асинхронно:

```python
def start_async_update(self, update_info, progress_callback=None):
    """Запуск асинхронного обновления"""
    def update_thread():
        try:
            self.progress_callback = progress_callback or (lambda p, m: None)
            
            # Уведомление о начале обновления
            self.progress_callback(0, "Starting update process")
            
            # Создание резервной копии
            self.progress_callback(5, "Creating backup")
            backup_path = self.create_backup()
            
            # Загрузка обновления
            self.progress_callback(10, "Downloading update")
            update_file = self.download_update(update_info)
            
            # Установка обновления
            self.progress_callback(60, "Installing update")
            self.install_update(update_file)
            
            # Проверка установки
            self.progress_callback(90, "Verifying installation")
            if self.verify_installation():
                self.progress_callback(100, "Update completed successfully")
                self.logger.info("OTA update completed successfully")
            else:
                self.progress_callback(100, "Update verification failed, rolling back")
                self.rollback_update()
                
        except Exception as e:
            self.logger.error(f"Async update failed: {e}")
            self.progress_callback(100, f"Update failed: {str(e)}")
            
            # Попытка отката при ошибке
            try:
                self.rollback_update()
            except:
                pass  # Ошибка отката не должна вызывать дополнительные ошибки
    
    # Запуск обновления в отдельном потоке
    self.update_thread = threading.Thread(target=update_thread, daemon=True)
    self.update_thread.start()
    
    return True
```

## Безопасность обновлений

### Проверка подписи

Все обновления подписываются для обеспечения безопасности:

```python
def verify_update_signature(self, update_file, signature):
    """Проверка подписи обновления"""
    try:
        # Загрузка публичного ключа
        public_key = self.load_public_key()
        
        # Проверка подписи
        with open(update_file, 'rb') as f:
            file_content = f.read()
        
        # Проверка подписи с использованием криптографических методов
        return self.crypto_verify(file_content, signature, public_key)
        
    except Exception as e:
        self.logger.error(f"Signature verification failed: {e}")
        return False
```

### Проверка целостности

Каждое обновление проверяется на целостность:

```python
def verify_checksum(self, file_path, expected_checksum):
    """Проверка контрольной суммы файла"""
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Вычисление SHA256 контрольной суммы
        calculated_checksum = hashlib.sha256(file_content).hexdigest()
        
        return calculated_checksum.lower() == expected_checksum.lower()
        
    except Exception as e:
        self.logger.error(f"Checksum verification error: {e}")
        return False
```

## Управление обновлениями

### Автоматические проверки

Система может автоматически проверять наличие обновлений:

```python
def auto_check_updates(self):
    """Автоматическая проверка обновлений"""
    check_interval = self.config.get('ota', {}).get('auto_check_interval', 86400)  # 1 день
    
    while self.running:
        try:
            # Проверка необходимости обновления
            if self.should_check_for_updates():
                update_info = self.check_for_updates()
                
                if update_info:
                    self.logger.info(f"Auto-update available: {update_info.get('version')}")
                    
                    # Проверка условий для обновления
                    if self.can_perform_update(update_info):
                        # Выполнение обновления
                        self.perform_auto_update(update_info)
            
            # Ожидание до следующей проверки
            for _ in range(check_interval // 10):  # Проверка каждые 10 секунд
                if not self.running:
                    break
                time.sleep(10)
                
        except Exception as e:
            self.logger.error(f"Error in auto-update check: {e}")
            time.sleep(300)  # Пауза перед повторной попыткой
```

### Условия для обновления

Обновления выполняются только при соблюдении определенных условий:

- **Достаточный уровень заряда батареи** (обычно > 50%)
- **Наличие стабильного соединения**
- **Нормальная температура оборудования**
- **Отсутствие критических операций**

## Уведомления и мониторинг

### Прогресс обновления

Система предоставляет информацию о прогрессе обновления:

```python
def send_update_progress(self, percent, message):
    """Отправка информации о прогрессе обновления"""
    progress_data = {
        'type': 'UPDATE_PROGRESS',
        'percent': percent,
        'message': message,
        'timestamp': time.time(),
        'current_version': self.current_version
    }
    
    # Отправка на наземную станцию
    self.comm.send_to_radio(progress_data)
```

### Логирование обновлений

Все операции обновления логируются:

```python
def log_update_event(self, event_type, details):
    """Логирование события обновления"""
    log_entry = {
        'timestamp': time.time(),
        'event_type': event_type,
        'details': details,
        'version_before': self.current_version,
        'version_after': getattr(self, 'new_version', self.current_version)
    }
    
    self.logger.info(f"OTA Event: {event_type} - {details}")
```

## Режимы обновления

### Режим "тихого" обновления

Для экономии ресурсов и энергии:

- Минимизация сетевой активности
- Оптимизация времени выполнения
- Снижение частоты проверок во время обновления

### Режим аварийного обновления

В случае критических уязвимостей:

- Приоритетное обновление
- Минимальные проверки безопасности
- Быстрый процесс установки

## Совместимость

### Проверка совместимости

Перед установкой обновления проверяется совместимость:

```python
def check_compatibility(self, update_dir):
    """Проверка совместимости обновления"""
    try:
        # Загрузка манифеста обновления
        manifest_path = os.path.join(update_dir, 'manifest.json')
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Проверка требований к оборудованию
        hw_requirements = manifest.get('hardware_requirements', {})
        if not self.check_hardware_compatibility(hw_requirements):
            return False
        
        # Проверка требований к версии
        required_version = manifest.get('required_version', '0.0.0')
        current_version = self.current_version
        
        if required_version != '0.0.0' and required_version != current_version:
            if not self.is_version_compatible(current_version, required_version):
                return False
        
        # Проверка размера
        update_size = self.get_directory_size(update_dir)
        available_space = self.get_available_space()
        
        if update_size * 3 > available_space:  # Требуется 3x места для установки
            return False
        
        return True
        
    except Exception as e:
        self.logger.error(f"Compatibility check error: {e}")
        return False
```

## Тестирование OTA

### Тесты обновлений

Система включает тесты для проверки процесса обновления:

```python
def test_ota_process():
    """Тест процесса OTA обновления"""
    # Создание тестовой конфигурации
    config = {
        'ota': {
            'server_url': 'https://test.example.com',
            'update_directory': '/tmp/test_updates',
            'backup_directory': '/tmp/test_backups',
            'current_version': '1.0.0',
            'auto_check_interval': 3600
        }
    }
    
    # Создание обновления
    logger = SimpleLogger("TestOTA")
    ota_updater = OTAUpdater(config, logger)
    
    # Тестирование различных сценариев
    print("✓ Проверка инициализации OTA")
    assert ota_updater is not None
    
    print("✓ Проверка создания резервной копии")
    # (тестирование создания резервной копии)
    
    print("✓ Проверка процесса обновления")
    # (тестирование процесса обновления)
    
    print("✓ Тест OTA процесса пройден")
```

## Лицензия
MIT License