import unittest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open

# Добавляем путь к основному коду
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../raspberry-pi-code'))

class TestTelemetryHandler(unittest.TestCase):
    """Тесты для обработчика телеметрии"""
    
    def setUp(self):
        """Подготовка тестового окружения"""
        from telemetry_handler import TelemetryHandler
        self.config = {
            'storage': {
                'base_path': '/tmp/test_storage',
                'max_telemetry_files': 100
            }
        }
        self.handler = TelemetryHandler(self.config)
    
    def test_save_telemetry(self):
        """Тест сохранения телеметрии"""
        telemetry_data = {
            'timestamp': 1234567890,
            'sequence': 1,
            'temperature': 25.0,
            'voltage': 3.7
        }
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('os.makedirs'):
                result = self.handler.save_telemetry(telemetry_data)
                self.assertTrue(result)
                mock_file.assert_called_once()


class TestCameraHandler(unittest.TestCase):
    """Тесты для обработчика камеры"""
    
    def setUp(self):
        """Подготовка тестового окружения"""
        from camera_handler import CameraHandler
        self.config = {
            'camera': {
                'resolution': [640, 480],
                'capture_interval': 60,
                'compression_quality': 85,
                'svd_components': 50
            },
            'storage': {
                'base_path': '/tmp/test_images'
            }
        }
        self.handler = CameraHandler(self.config)
    
    @patch('cv2.VideoCapture')
    def test_capture_image_success(self, mock_video_capture):
        """Тест успешного захвата изображения"""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, MagicMock())
        mock_video_capture.return_value = mock_cap
        
        with patch('cv2.imwrite', return_value=True):
            with patch('os.makedirs'):
                result = self.handler.capture_image(queue.Queue())
                self.assertIsNotNone(result)


class TestCommunicationHandler(unittest.TestCase):
    """Тесты для обработчика коммуникации"""
    
    def setUp(self):
        """Подготовка тестового окружения"""
        from communication import CommunicationHandler
        self.config = {
            'communication': {
                'stm32_port': '/dev/ttyUSB0',
                'baudrate': 115200,
                'radio_port': '/dev/ttyUSB1',
                'radio_baudrate': 9600
            }
        }
        self.handler = CommunicationHandler(self.config)
    
    def test_parse_incoming_data(self):
        """Тест парсинга входящих данных"""
        # Тест с валидными данными телеметрии
        valid_data = bytearray([0xAA, 0x55]) + b'\x00' * 38  # 40 байт, синхро-байты 0xAA 0x55
        result = self.handler.parse_incoming_data(valid_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'telemetry')
    
    def test_parse_invalid_data(self):
        """Тест парсинга невалидных данных"""
        invalid_data = b'\xFF\xFF'  # Неверные синхро-байты
        result = self.handler.parse_incoming_data(invalid_data)
        self.assertEqual(len(result), 0)


class TestGroundStation(unittest.TestCase):
    """Тесты для наземной станции"""
    
    def test_config_loading(self):
        """Тест загрузки конфигурации"""
        from ground_station import Config
        self.assertIsNotNone(Config.VERSION)
        self.assertEqual(Config.UPDATE_INTERVAL, 0.1)


class TestTelemetryData(unittest.TestCase):
    """Тесты для класса данных телеметрии"""
    
    def test_from_packet_valid(self):
        """Тест парсинга валидного пакета"""
        from ground_station import TelemetryData
        import struct
        
        # Создаем валидный пакет телеметрии (40 байт)
        packet = bytearray()
        packet.extend(struct.pack('<H', 0xAA55))  # sync
        packet.extend(struct.pack('<H', 123))     # sequence
        packet.extend(struct.pack('<I', 1000))    # timestamp
        packet.extend(struct.pack('<f', 0.1))    # mag_x
        packet.extend(struct.pack('<f', 0.2))    # mag_y
        packet.extend(struct.pack('<f', 0.3))    # mag_z
        packet.extend(struct.pack('<H', 500))    # corrosion_raw
        packet.extend(struct.pack('<I', 30))     # radiation_cps
        packet.extend(struct.pack('<f', 25.0))   # temperature_bme
        packet.extend(struct.pack('<f', 1013.25)) # pressure
        packet.extend(struct.pack('<f', 45.0))   # humidity
        packet.extend(struct.pack('<H', 3850))   # battery_voltage (3.85V * 1000)
        
        td = TelemetryData()
        result = td.from_packet(packet)
        self.assertTrue(result)
        self.assertEqual(td.sequence, 123)
        self.assertAlmostEqual(td.mag_x, 0.1)
        self.assertAlmostEqual(td.battery_voltage, 3.85)


if __name__ == '__main__':
    unittest.main()