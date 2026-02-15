"""
OTA (Over-The-Air) обновление для CubeSat системы
"""
import os
import json
import hashlib
import zipfile
import tempfile
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable
import requests
from datetime import datetime


class OTAUpdater:
    """
    Система OTA обновлений для CubeSat
    Обеспечивает безопасное обновление прошивки и программного обеспечения
    """
    
    def __init__(self, config: Dict, logger=None):
        self.config = config
        self.logger = logger
        self.update_server_url = config.get('ota', {}).get('server_url', 'https://updates.cubesat.example.com')
        self.update_directory = Path(config.get('ota', {}).get('update_directory', './updates'))
        self.backup_directory = Path(config.get('ota', {}).get('backup_directory', './backups'))
        self.current_version = config.get('ota', {}).get('current_version', '1.0.0')
        
        # Создаем необходимые директории
        self.update_directory.mkdir(exist_ok=True)
        self.backup_directory.mkdir(exist_ok=True)
        
        # Состояние обновления
        self.updating = False
        self.progress_callback = None
        
        if self.logger:
            self.logger.info(f"OTA Updater initialized. Current version: {self.current_version}")
    
    def set_progress_callback(self, callback: Callable[[int, str], None]):
        """Установить коллбэк для отслеживания прогресса обновления"""
        self.progress_callback = callback
    
    def notify_progress(self, percent: int, message: str = ""):
        """Уведомить о прогрессе обновления"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        if self.logger:
            self.logger.info(f"OTA Progress: {percent}% - {message}")
    
    def check_for_updates(self) -> Optional[Dict]:
        """
        Проверить наличие обновлений
        
        Returns:
            Информация об обновлении или None если нет обновлений
        """
        try:
            url = f"{self.update_server_url}/api/v1/check-update"
            payload = {
                'device_id': self.config.get('satellite', {}).get('mission_id', 'unknown'),
                'current_version': self.current_version,
                'platform': 'cubesat-1u',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                update_info = response.json()
                if update_info.get('update_available', False):
                    return update_info
            elif response.status_code == 204:
                # No updates available
                if self.logger:
                    self.logger.info("No updates available")
                return None
            else:
                if self.logger:
                    self.logger.error(f"Update check failed: {response.status_code}")
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking for updates: {e}")
        
        return None
    
    def download_update(self, update_info: Dict) -> Optional[Path]:
        """
        Скачать обновление
        
        Args:
            update_info: Информация об обновлении
            
        Returns:
            Путь к скачанному файлу или None при ошибке
        """
        try:
            download_url = update_info.get('download_url')
            if not download_url:
                if self.logger:
                    self.logger.error("No download URL in update info")
                return None
            
            # Создаем имя файла на основе версии и хэша
            version = update_info.get('version', 'unknown')
            file_hash = update_info.get('hash', 'unknown')
            filename = f"update_{version}_{file_hash[:8]}.zip"
            filepath = self.update_directory / filename
            
            # Проверяем, не скачан ли уже этот файл
            if filepath.exists():
                if self._verify_file_integrity(filepath, file_hash):
                    if self.logger:
                        self.logger.info(f"Update already downloaded: {filepath}")
                    return filepath
            
            # Скачиваем файл
            if self.logger:
                self.logger.info(f"Downloading update from {download_url}")
            
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            self.notify_progress(percent, "Downloading...")
            
            # Проверяем целостность файла
            if not self._verify_file_integrity(filepath, file_hash):
                if self.logger:
                    self.logger.error("Downloaded file integrity check failed")
                filepath.unlink(missing_ok=True)
                return None
            
            self.notify_progress(100, "Download complete")
            
            if self.logger:
                self.logger.info(f"Update downloaded successfully: {filepath}")
            
            return filepath
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error downloading update: {e}")
            return None
    
    def _verify_file_integrity(self, filepath: Path, expected_hash: str) -> bool:
        """
        Проверить целостность файла по хэшу
        
        Args:
            filepath: Путь к файлу
            expected_hash: Ожидаемый хэш
            
        Returns:
            True если хэши совпадают
        """
        try:
            with open(filepath, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash.lower() == expected_hash.lower()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error verifying file integrity: {e}")
            return False
    
    def validate_update_package(self, package_path: Path) -> bool:
        """
        Проверить валидность пакета обновления
        
        Args:
            package_path: Путь к пакету обновления
            
        Returns:
            True если пакет валиден
        """
        try:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                # Проверяем структуру пакета
                file_list = zip_ref.namelist()
                
                # Проверяем наличие обязательных файлов
                required_files = ['manifest.json', 'firmware.bin', 'metadata.json']
                for req_file in required_files:
                    if req_file not in file_list:
                        if self.logger:
                            self.logger.error(f"Required file missing in update package: {req_file}")
                        return False
                
                # Читаем манифест
                manifest_content = zip_ref.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)
                
                # Проверяем сигнатуру (в реальной системе - криптографическая проверка)
                if not self._verify_update_signature(manifest):
                    if self.logger:
                        self.logger.error("Update package signature verification failed")
                    return False
                
                # Проверяем совместимость
                if not self._check_compatibility(manifest):
                    if self.logger:
                        self.logger.error("Update package is not compatible with current system")
                    return False
                
                if self.logger:
                    self.logger.info("Update package validation successful")
                
                return True
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error validating update package: {e}")
            return False
    
    def _verify_update_signature(self, manifest: Dict) -> bool:
        """
        Проверить подпись обновления
        
        Args:
            manifest: Манифест обновления
            
        Returns:
            True если подпись действительна
        """
        # В реальной системе здесь будет криптографическая проверка подписи
        # Пока просто проверяем наличие поля signature
        return 'signature' in manifest
    
    def _check_compatibility(self, manifest: Dict) -> bool:
        """
        Проверить совместимость обновления с текущей системой
        
        Args:
            manifest: Манифест обновления
            
        Returns:
            True если обновление совместимо
        """
        try:
            # Проверяем совместимость версий
            required_version = manifest.get('required_version', '0.0.0')
            current_version = self.current_version
            
            # Простая проверка версии (в реальной системе - семантическое версионирование)
            if required_version != '0.0.0' and required_version != current_version:
                # Проверяем, является ли версия допустимой для обновления
                if not self._is_version_compatible(current_version, required_version):
                    return False
            
            # Проверяем аппаратную совместимость
            hardware_required = manifest.get('hardware_requirements', {})
            if not self._check_hardware_compatibility(hardware_required):
                return False
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking compatibility: {e}")
            return False
    
    def _is_version_compatible(self, current: str, required: str) -> bool:
        """Проверить совместимость версий"""
        # Простая реализация - в реальной системе использовать семантическое версионирование
        return True
    
    def _check_hardware_compatibility(self, requirements: Dict) -> bool:
        """Проверить совместимость с оборудованием"""
        # В реальной системе проверять спецификации оборудования
        return True
    
    def create_backup(self) -> bool:
        """
        Создать резервную копию текущей системы
        
        Returns:
            True если резервная копия создана успешно
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_directory / backup_name
            
            # Создаем резервную копию важных файлов
            important_dirs = [
                Path('./config'),
                Path('./logs'),
                Path('./scripts'),
                Path('./data')
            ]
            
            with zipfile.ZipFile(backup_path.with_suffix('.zip'), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for dir_path in important_dirs:
                    if dir_path.exists():
                        for file_path in dir_path.rglob('*'):
                            if file_path.is_file():
                                arc_path = file_path.relative_to(Path('.'))
                                zipf.write(file_path, arc_path)
            
            if self.logger:
                self.logger.info(f"Backup created: {backup_path.with_suffix('.zip')}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error creating backup: {e}")
            return False
    
    def install_update(self, package_path: Path) -> bool:
        """
        Установить обновление
        
        Args:
            package_path: Путь к пакету обновления
            
        Returns:
            True если обновление установлено успешно
        """
        if self.updating:
            if self.logger:
                self.logger.error("Update already in progress")
            return False
        
        self.updating = True
        try:
            if self.logger:
                self.logger.info(f"Starting update installation from: {package_path}")
            
            # Создаем резервную копию
            self.notify_progress(5, "Creating backup...")
            if not self.create_backup():
                if self.logger:
                    self.logger.error("Failed to create backup, aborting update")
                return False
            
            # Распаковываем обновление
            self.notify_progress(10, "Extracting update...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Читаем манифест
                manifest_path = temp_path / 'manifest.json'
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Выполняем установку в зависимости от типа обновления
                update_type = manifest.get('type', 'full')
                
                if update_type == 'firmware':
                    success = self._install_firmware_update(temp_path, manifest)
                elif update_type == 'software':
                    success = self._install_software_update(temp_path, manifest)
                elif update_type == 'configuration':
                    success = self._install_config_update(temp_path, manifest)
                else:
                    success = self._install_full_update(temp_path, manifest)
                
                if success:
                    # Обновляем информацию о версии
                    new_version = manifest.get('version', self.current_version)
                    self.current_version = new_version
                    
                    # Сохраняем новую версию в конфиг
                    self._update_config_version(new_version)
                    
                    self.notify_progress(95, "Update installed successfully")
                    if self.logger:
                        self.logger.info(f"Update installed successfully. New version: {new_version}")
                else:
                    self.notify_progress(0, "Update failed")
                    if self.logger:
                        self.logger.error("Update installation failed")
                
                return success
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing update: {e}")
            return False
        finally:
            self.updating = False
    
    def _install_firmware_update(self, temp_path: Path, manifest: Dict) -> bool:
        """Установить обновление прошивки"""
        try:
            firmware_path = temp_path / 'firmware.bin'
            if not firmware_path.exists():
                if self.logger:
                    self.logger.error("Firmware file not found in update package")
                return False
            
            # В реальной системе здесь будет загрузка прошивки в микроконтроллер
            # Пока просто имитируем процесс
            self.notify_progress(50, "Installing firmware...")
            time.sleep(2)  # Имитация процесса
            
            # Проверяем результат установки
            self.notify_progress(80, "Verifying installation...")
            time.sleep(1)  # Имитация проверки
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing firmware update: {e}")
            return False
    
    def _install_software_update(self, temp_path: Path, manifest: Dict) -> bool:
        """Установить обновление программного обеспечения"""
        try:
            # Копируем новые файлы в соответствующие директории
            source_dir = temp_path / 'software'
            if not source_dir.exists():
                if self.logger:
                    self.logger.error("Software directory not found in update package")
                return False
            
            # В реальной системе нужно аккуратно заменить файлы
            # с учетом зависимостей и прав доступа
            self.notify_progress(50, "Installing software...")
            
            # Имитация установки
            time.sleep(2)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing software update: {e}")
            return False
    
    def _install_config_update(self, temp_path: Path, manifest: Dict) -> bool:
        """Установить обновление конфигурации"""
        try:
            config_path = temp_path / 'config.json'
            if not config_path.exists():
                if self.logger:
                    self.logger.error("Config file not found in update package")
                return False
            
            # Обновляем конфигурацию
            self.notify_progress(60, "Updating configuration...")
            
            # В реальной системе нужно аккуратно обновить конфигурацию
            # с сохранением пользовательских настроек
            time.sleep(1)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing config update: {e}")
            return False
    
    def _install_full_update(self, temp_path: Path, manifest: Dict) -> bool:
        """Установить полное обновление"""
        try:
            # Полная замена системы (в реальной системе - осторожно!)
            self.notify_progress(40, "Preparing full update...")
            time.sleep(1)
            
            self.notify_progress(70, "Applying changes...")
            time.sleep(2)
            
            self.notify_progress(90, "Finalizing...")
            time.sleep(1)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing full update: {e}")
            return False
    
    def _update_config_version(self, new_version: str):
        """Обновить версию в конфигурационном файле"""
        try:
            config_path = Path('config.json')
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                config.setdefault('ota', {})['current_version'] = new_version
                
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                    
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating config version: {e}")
    
    def rollback_update(self) -> bool:
        """
        Откатить последнее обновление
        
        Returns:
            True если откат выполнен успешно
        """
        try:
            # Находим последнюю резервную копию
            backup_files = list(self.backup_directory.glob('backup_*.zip'))
            if not backup_files:
                if self.logger:
                    self.logger.error("No backups available for rollback")
                return False
            
            # Берем самую последнюю резервную копию
            latest_backup = max(backup_files, key=os.path.getctime)
            
            if self.logger:
                self.logger.info(f"Rolling back using backup: {latest_backup}")
            
            # В реальной системе - восстановление из резервной копии
            # Пока просто имитируем процесс
            self.notify_progress(50, "Restoring from backup...")
            time.sleep(2)
            
            self.notify_progress(100, "Rollback completed")
            
            if self.logger:
                self.logger.info("Rollback completed successfully")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during rollback: {e}")
            return False
    
    def get_system_info(self) -> Dict:
        """
        Получить информацию о системе
        
        Returns:
            Словарь с информацией о системе
        """
        try:
            import platform
            import psutil
            
            info = {
                'version': self.current_version,
                'platform': platform.platform(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'disk_total': psutil.disk_usage('/').total,
                'uptime': getattr(self, 'uptime', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return info
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error getting system info: {e}")
            return {}


class AsyncOTAUpdater:
    """
    Асинхронная система OTA обновлений
    """
    
    def __init__(self, ota_updater: OTAUpdater):
        self.ota_updater = ota_updater
        self.update_thread = None
        self.cancel_flag = threading.Event()
    
    def start_async_update(self, update_info: Dict, progress_callback: Callable = None) -> bool:
        """
        Запустить асинхронное обновление
        
        Args:
            update_info: Информация об обновлении
            progress_callback: Коллбэк для отслеживания прогресса
            
        Returns:
            True если обновление запущено успешно
        """
        if self.update_thread and self.update_thread.is_alive():
            if self.ota_updater.logger:
                self.ota_updater.logger.error("Update already in progress")
            return False
        
        if progress_callback:
            self.ota_updater.set_progress_callback(progress_callback)
        
        self.cancel_flag.clear()
        self.update_thread = threading.Thread(
            target=self._async_update_worker,
            args=(update_info,),
            daemon=True
        )
        self.update_thread.start()
        
        if self.ota_updater.logger:
            self.ota_updater.logger.info("Async update started")
        
        return True
    
    def _async_update_worker(self, update_info: Dict):
        """Рабочий поток для асинхронного обновления"""
        try:
            # Скачиваем обновление
            package_path = self.ota_updater.download_update(update_info)
            if not package_path:
                self.ota_updater.notify_progress(0, "Download failed")
                return
            
            if self.cancel_flag.is_set():
                self.ota_updater.notify_progress(0, "Update cancelled")
                return
            
            # Проверяем пакет
            if not self.ota_updater.validate_update_package(package_path):
                self.ota_updater.notify_progress(0, "Package validation failed")
                return
            
            if self.cancel_flag.is_set():
                self.ota_updater.notify_progress(0, "Update cancelled")
                return
            
            # Устанавливаем обновление
            success = self.ota_updater.install_update(package_path)
            if not success:
                self.ota_updater.notify_progress(0, "Installation failed")
                return
            
            self.ota_updater.notify_progress(100, "Update completed successfully")
            
        except Exception as e:
            if self.ota_updater.logger:
                self.ota_updater.logger.error(f"Error in async update: {e}")
            self.ota_updater.notify_progress(0, f"Update failed: {str(e)}")
    
    def cancel_update(self):
        """Отменить текущее обновление"""
        self.cancel_flag.set()
        if self.ota_updater.logger:
            self.ota_updater.logger.info("Update cancellation requested")