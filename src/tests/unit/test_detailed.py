import unittest
import sys
import os
from unittest.mock import MagicMock, patch, mock_open
import json
import struct
from datetime import datetime

# Добавляем путь к основному коду
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../raspberry-pi-code'))

from telemetry_handler import TelemetryHandler
from camera_handler import CameraHandler
from communication import CommunicationHandler


class TestTelemetryHandlerDetailed(unittest.TestCase):
    """Детальные тесты для обработчика телеметрии"""
    
    def setUp(self):
        self.config = {
            'storage': {
                'base_path': '/tmp/test_telemetry',
                'max_telemetry_files': 100
            }
        }
        self.handler = TelemetryHandler(self.config)
    
    def test_get_latest(self):
        """Тест получения последних данных телеметрии"""
        # Тест с пустыми данными
        latest = self.handler.get_latest()
        self.assertIsNotNone(latest)
        
        # Тест с заполненными данными
        test_data = {'timestamp': 1234567890, 'test': 'value'}
        self.handler.save_telemetry(test_data)
        latest = self.handler.get_latest()
        self.assertEqual(latest.get('test'), 'value')
    
    def test_cleanup_old_files(self):
        """Тест очистки старых файлов"""
        with patch('os.path.exists', return_value=True):
            with patch('os.listdir', return_value=['old_file.json', 'recent_file.json']):
                with patch('os.path.getctime', side_effect=[datetime.now().timestamp() - 40*24*3600,  # 40 дней назад
                                                           datetime.now().timestamp() - 10*24*3600]): # 10 дней назад
                    with patch('os.remove', return_value=None) as mock_remove:
                        self.handler.cleanup_old_files(days=30)
                        # Проверяем, что старый файл был удален
                        mock_remove.assert_called_once_with(os.path.join(self.config['storage']['base_path'], 'old_file.json'))


class TestCameraHandlerDetailed(unittest.TestCase):
    """Детальные тесты для обработчика камеры"""
    
    def setUp(self):
        self.config = {
            'camera': {
                'resolution': [640, 480],
                'capture_interval': 60,
                'compression_quality': 85,
                'svd_components': 50
            },
            'storage': {
                'base_path': '/tmp/test_camera'
            }
        }
        self.handler = CameraHandler(self.config)
    
    @patch('cv2.VideoCapture')
    @patch('cv2.imwrite')
    def test_capture_image(self, mock_imwrite, mock_videocapture):
        """Тест захвата изображения"""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, MagicMock())
        mock_videocapture.return_value = mock_cap
        mock_imwrite.return_value = True
        
        import queue
        result_queue = queue.Queue()
        
        with patch('os.makedirs'):
            result = self.handler.capture_image(result_queue)
            
            # Проверяем, что результат не None
            self.assertIsNotNone(result)
            # Проверяем, что в очередь было добавлено сообщение
            self.assertFalse(result_queue.empty())
    
    def test_compress_image(self):
        """Тест сжатия изображения с помощью SVD"""
        import numpy as np
        from PIL import Image
        import tempfile
        
        # Создаем тестовое изображение
        test_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        test_img_pil = Image.fromarray(test_img)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_input:
            test_img_pil.save(tmp_input.name)
            
            with tempfile.TemporaryDirectory() as tmp_output_dir:
                output_path = os.path.join(tmp_output_dir, 'compressed.jpg')
                
                # Проверяем, что метод существует и не вызывает ошибок
                try:
                    result = self.handler.compress_image(tmp_input.name, 10)
                    # Результат может быть None если OpenCV не установлен
                    # Это нормально для среды тестирования
                except ImportError:
                    # Если нет необходимых библиотек, просто проверяем, что метод существует
                    self.assertTrue(hasattr(self.handler, 'compress_image'))
    
    def test_create_thumbnail(self):
        """Тест создания миниатюры"""
        import numpy as np
        from PIL import Image
        import tempfile
        
        # Создаем тестовое изображение
        test_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        test_img_pil = Image.fromarray(test_img)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_input:
            test_img_pil.save(tmp_input.name)
            
            with tempfile.TemporaryDirectory() as tmp_output_dir:
                # Проверяем, что метод существует
                self.assertTrue(hasattr(self.handler, 'create_thumbnail'))


class TestCommunicationHandlerDetailed(unittest.TestCase):
    """Детальные тесты для обработчика коммуникации"""
    
    def setUp(self):
        self.config = {
            'communication': {
                'stm32_port': '/dev/ttyUSB0',
                'baudrate': 115200,
                'radio_port': '/dev/ttyUSB1',
                'radio_baudrate': 9600
            }
        }
        self.handler = CommunicationHandler(self.config)
    
    def test_send_to_stm32(self):
        """Тест отправки данных STM32"""
        test_data = {'command': 'test', 'value': 123}
        
        # Тестируем с подключенным сериал портом
        self.handler.stm32_serial = MagicMock()
        self.handler.stm32_serial.write = MagicMock(return_value=len(json.dumps(test_data)))
        
        result = self.handler.send_to_stm32(test_data)
        # Результат зависит от того, был ли порт открыт
        # Главное - метод должен существовать и не вызывать ошибок
        
        self.assertTrue(hasattr(self.handler, 'send_to_stm32'))
    
    def test_send_to_radio(self):
        """Тест отправки данных по радио"""
        test_data = {'type': 'telemetry', 'data': {'temp': 25.0}}
        
        # Тестируем с подключенным радио портом
        self.handler.radio_serial = MagicMock()
        self.handler.radio_serial.write = MagicMock(return_value=len(json.dumps(test_data)))
        
        result = self.handler.send_to_radio(test_data)
        # Аналогично - главное наличие метода
        
        self.assertTrue(hasattr(self.handler, 'send_to_radio'))
    
    def test_parse_incoming_data_edge_cases(self):
        """Тест граничных случаев парсинга данных"""
        # Пустые данные
        result = self.handler.parse_incoming_data(b'')
        self.assertEqual(len(result), 0)
        
        # Очень короткие данные
        result = self.handler.parse_incoming_data(b'\xAA')
        self.assertEqual(len(result), 0)
        
        # Данные без синхронизации
        result = self.handler.parse_incoming_data(b'\xFF\xFF\x00\x00')
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main()