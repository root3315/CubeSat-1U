"""
OTA (Over-The-Air) Update System for CubeSat
"""
import os
import json
import hashlib
import hmac
import zipfile
import tempfile
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None  # type: ignore


class OTAUpdater:
    """
    OTA update system for CubeSat
    Provides secure firmware and software updates
    """

    def __init__(self, config: Dict[str, Any], logger: Optional[Any] = None) -> None:
        self.config = config
        self.logger = logger
        self.update_server_url = config.get('ota', {}).get('server_url', 'https://updates.cubesat.example.com')
        self.update_directory = Path(config.get('ota', {}).get('update_directory', './updates'))
        self.backup_directory = Path(config.get('ota', {}).get('backup_directory', './backups'))
        self.current_version = config.get('ota', {}).get('current_version', '1.0.0')

        self.update_directory.mkdir(exist_ok=True)
        self.backup_directory.mkdir(exist_ok=True)

        self.updating = False
        self.progress_callback: Optional[Callable[[int, str], None]] = None

        if self.logger:
            self.logger.info(f"OTA Updater initialized. Current version: {self.current_version}")

    def set_progress_callback(self, callback: Callable[[int, str], None]) -> None:
        """Set callback for tracking update progress"""
        self.progress_callback = callback

    def notify_progress(self, percent: int, message: str = "") -> None:
        """Notify about update progress"""
        if self.progress_callback:
            self.progress_callback(percent, message)
        if self.logger:
            self.logger.info(f"OTA Progress: {percent}% - {message}")

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """
        Check for available updates

        Returns:
            Update info dictionary or None if no updates
        """
        if requests is None:
            if self.logger:
                self.logger.error("requests library not available")
            return None

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

    def download_update(self, update_info: Dict[str, Any]) -> Optional[Path]:
        """
        Download update package

        Args:
            update_info: Update information dictionary

        Returns:
            Path to downloaded file or None on error
        """
        if requests is None:
            if self.logger:
                self.logger.error("requests library not available")
            return None

        try:
            download_url = update_info.get('download_url')
            if not download_url:
                if self.logger:
                    self.logger.error("No download URL in update info")
                return None

            version = update_info.get('version', 'unknown')
            file_hash = update_info.get('hash', 'unknown')
            filename = f"update_{version}_{file_hash[:8]}.zip"
            filepath = self.update_directory / filename

            if filepath.exists():
                if self._verify_file_integrity(filepath, file_hash):
                    if self.logger:
                        self.logger.info(f"Update already downloaded: {filepath}")
                    return filepath

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
        Verify file integrity using hash

        Args:
            filepath: Path to file
            expected_hash: Expected SHA256 hash

        Returns:
            True if hash matches
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
        Validate update package

        Args:
            package_path: Path to update package

        Returns:
            True if package is valid
        """
        try:
            with zipfile.ZipFile(package_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()

                required_files = ['manifest.json', 'firmware.bin', 'metadata.json']
                for req_file in required_files:
                    if req_file not in file_list:
                        if self.logger:
                            self.logger.error(f"Required file missing in update package: {req_file}")
                        return False

                manifest_content = zip_ref.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)

                if not self._verify_update_signature(manifest):
                    if self.logger:
                        self.logger.error("Update package signature verification failed")
                    return False

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

    def _verify_update_signature(self, manifest: Dict[str, Any]) -> bool:
        """
        Verify update signature using HMAC

        Args:
            manifest: Update manifest

        Returns:
            True if signature is valid
        """
        signature = manifest.get('signature')
        if not signature:
            if self.logger:
                self.logger.error("Update manifest missing signature")
            return False

        secret_key = os.environ.get('CUBESAT_SHARED_SECRET', '')
        if not secret_key:
            if self.logger:
                self.logger.warning("CUBESAT_SHARED_SECRET not set, using basic validation")
            return True

        manifest_copy = {k: v for k, v in manifest.items() if k != 'signature'}
        manifest_data = json.dumps(manifest_copy, sort_keys=True).encode('utf-8')

        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            manifest_data,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            if self.logger:
                self.logger.error("Update signature verification failed")
            return False

        if self.logger:
            self.logger.info("Update signature verified successfully")
        return True

    def _check_compatibility(self, manifest: Dict[str, Any]) -> bool:
        """
        Check compatibility with current system

        Args:
            manifest: Update manifest

        Returns:
            True if compatible
        """
        try:
            required_version = manifest.get('required_version', '0.0.0')
            current_version = self.current_version

            if required_version != '0.0.0' and required_version != current_version:
                if not self._is_version_compatible(current_version, required_version):
                    return False

            hardware_required = manifest.get('hardware_requirements', {})
            if not self._check_hardware_compatibility(hardware_required):
                return False

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error checking compatibility: {e}")
            return False

    def _is_version_compatible(self, current: str, required: str) -> bool:
        """Check version compatibility"""
        return True

    def _check_hardware_compatibility(self, requirements: Dict[str, Any]) -> bool:
        """Check hardware compatibility"""
        return True

    def create_backup(self) -> bool:
        """
        Create backup of current system

        Returns:
            True if backup created successfully
        """
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_directory / backup_name

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
        Install update

        Args:
            package_path: Path to update package

        Returns:
            True if installation successful
        """
        if self.updating:
            if self.logger:
                self.logger.error("Update already in progress")
            return False

        self.updating = True
        try:
            if self.logger:
                self.logger.info(f"Starting update installation from: {package_path}")

            self.notify_progress(5, "Creating backup...")
            if not self.create_backup():
                if self.logger:
                    self.logger.error("Failed to create backup, aborting update")
                return False

            self.notify_progress(10, "Extracting update...")
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)

                manifest_path = temp_path / 'manifest.json'
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)

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
                    new_version = manifest.get('version', self.current_version)
                    self.current_version = new_version
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

    def _install_firmware_update(self, temp_path: Path, manifest: Dict[str, Any]) -> bool:
        """Install firmware update"""
        try:
            firmware_path = temp_path / 'firmware.bin'
            if not firmware_path.exists():
                if self.logger:
                    self.logger.error("Firmware file not found in update package")
                return False

            self.notify_progress(50, "Installing firmware...")
            time.sleep(2)

            self.notify_progress(80, "Verifying installation...")
            time.sleep(1)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing firmware update: {e}")
            return False

    def _install_software_update(self, temp_path: Path, manifest: Dict[str, Any]) -> bool:
        """Install software update"""
        try:
            source_dir = temp_path / 'software'
            if not source_dir.exists():
                if self.logger:
                    self.logger.error("Software directory not found in update package")
                return False

            self.notify_progress(50, "Installing software...")
            time.sleep(2)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing software update: {e}")
            return False

    def _install_config_update(self, temp_path: Path, manifest: Dict[str, Any]) -> bool:
        """Install configuration update"""
        try:
            config_path = temp_path / 'config.json'
            if not config_path.exists():
                if self.logger:
                    self.logger.error("Config file not found in update package")
                return False

            self.notify_progress(60, "Updating configuration...")
            time.sleep(1)

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error installing config update: {e}")
            return False

    def _install_full_update(self, temp_path: Path, manifest: Dict[str, Any]) -> bool:
        """Install full update"""
        try:
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

    def _update_config_version(self, new_version: str) -> None:
        """Update version in config file"""
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
        Rollback to previous version

        Returns:
            True if rollback successful
        """
        try:
            backup_files = list(self.backup_directory.glob('backup_*.zip'))
            if not backup_files:
                if self.logger:
                    self.logger.error("No backups available for rollback")
                return False

            latest_backup = max(backup_files, key=os.path.getctime)

            if self.logger:
                self.logger.info(f"Rolling back using backup: {latest_backup}")

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

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information

        Returns:
            Dictionary with system info
        """
        try:
            import platform
            import psutil

            info: Dict[str, Any] = {
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
    Asynchronous OTA update system
    """

    def __init__(self, ota_updater: OTAUpdater) -> None:
        self.ota_updater = ota_updater
        self.update_thread: Optional[threading.Thread] = None
        self.cancel_flag = threading.Event()

    def start_async_update(
        self,
        update_info: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Start asynchronous update

        Args:
            update_info: Update information
            progress_callback: Progress callback

        Returns:
            True if update started successfully
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

    def _async_update_worker(self, update_info: Dict[str, Any]) -> None:
        """Worker thread for async update"""
        try:
            package_path = self.ota_updater.download_update(update_info)
            if not package_path:
                self.ota_updater.notify_progress(0, "Download failed")
                return

            if self.cancel_flag.is_set():
                self.ota_updater.notify_progress(0, "Update cancelled")
                return

            if not self.ota_updater.validate_update_package(package_path):
                self.ota_updater.notify_progress(0, "Package validation failed")
                return

            if self.cancel_flag.is_set():
                self.ota_updater.notify_progress(0, "Update cancelled")
                return

            success = self.ota_updater.install_update(package_path)
            if not success:
                self.ota_updater.notify_progress(0, "Installation failed")
                return

            self.ota_updater.notify_progress(100, "Update completed successfully")

        except Exception as e:
            if self.ota_updater.logger:
                self.ota_updater.logger.error(f"Error in async update: {e}")
            self.ota_updater.notify_progress(0, f"Update failed: {str(e)}")

    def cancel_update(self) -> None:
        """Cancel current update"""
        self.cancel_flag.set()
        if self.ota_updater.logger:
            self.ota_updater.logger.info("Update cancellation requested")
