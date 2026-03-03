#!/usr/bin/env python3
"""
Optimized Camera handler for Raspberry Pi Camera Module
Lightweight implementation optimized for resource-constrained environments
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError:
    cv2 = None  # type: ignore
    np = None  # type: ignore
    Image = None  # type: ignore


class CameraHandler:
    """Optimized camera handler with reduced resource usage"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.logger = logging.getLogger('CameraHandler')

        self.camera_available = False
        self.camera: Optional[Any] = None

        self.init_camera()
        self.setup_storage()

    def init_camera(self) -> None:
        """Initialize the camera with optimized settings"""
        if cv2 is None:
            self.logger.warning("OpenCV not installed, camera unavailable")
            return

        try:
            self.camera = cv2.VideoCapture(0)

            if not self.camera.isOpened():
                self.logger.error("Camera failed to open - device not available")
                self.camera.release()
                self.camera = None
                self.camera_available = False
                return

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH,
                           self.config['camera']['resolution'][0] // 2)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT,
                           self.config['camera']['resolution'][1] // 2)
            self.camera.set(cv2.CAP_PROP_FPS, 15)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            for _ in range(3):
                ret, _ = self.camera.read()
                if not ret:
                    self.logger.warning("Camera warm-up frame capture failed")

            self.camera_available = True
            self.logger.info("Camera initialized successfully with optimized settings")

        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            if self.camera:
                self.camera.release()
            self.camera = None
            self.camera_available = False

    def setup_storage(self) -> None:
        """Setup image storage directories"""
        base_path = Path(self.config['storage']['base_path'])

        dirs = ['images/raw', 'images/compressed', 'images/thumbnails']
        for dir_path in dirs:
            full_path = base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

    def capture_image(self, output_queue: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Capture an image from the camera"""
        if not self.camera or not self.camera_available:
            self.logger.error("Camera not initialized or not available")
            return None

        if cv2 is None:
            self.logger.error("OpenCV not available")
            return None

        try:
            self.logger.info("Capturing image...")

            ret, frame = None, None
            for attempt in range(3):
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    break
                self.logger.warning(f"Capture attempt {attempt + 1} failed, retrying...")
                time.sleep(0.1)
            else:
                self.logger.error("Failed to capture image after 3 attempts")
                return None

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            base_path = Path(self.config['storage']['base_path'])
            filename = base_path / 'images' / 'raw' / f'raw_{timestamp}.jpg'

            cv2.imwrite(str(filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

            file_size = os.path.getsize(filename) / 1024

            self.logger.info(f"Image captured: {filename} ({file_size:.1f} KB)")

            image_info: Dict[str, Any] = {
                'filename': str(filename),
                'timestamp': timestamp,
                'size': frame.shape,
                'file_size_kb': file_size,
                'capture_time': time.time()
            }

            if output_queue:
                try:
                    output_queue.put_nowait(image_info)
                except Exception:
                    self.logger.warning("Output queue full, dropping image info")

            return image_info

        except Exception as e:
            self.logger.error(f"Image capture error: {e}")
            return None

    def compress_image(self, raw_path: str, n_components: int = 30) -> Optional[str]:
        """Optimized image compression using SVD"""
        if np is None or Image is None:
            self.logger.error("NumPy or PIL not available")
            return None

        try:
            self.logger.info(f"Compressing image: {raw_path}")

            img = Image.open(raw_path)
            img = img.resize((img.width // 2, img.height // 2), Image.Resampling.LANCZOS)

            img_array = np.array(img)
            img_float = img_array.astype(float)

            if len(img_float.shape) == 3:
                compressed = np.zeros_like(img_float)

                for channel in range(3):
                    U, s, Vt = np.linalg.svd(img_float[:, :, channel], full_matrices=False)
                    kept_components = min(n_components, len(s))
                    compressed[:, :, channel] = U[:, :kept_components] @ \
                                                np.diag(s[:kept_components]) @ \
                                                Vt[:kept_components, :]
            else:
                U, s, Vt = np.linalg.svd(img_float, full_matrices=False)
                kept_components = min(n_components, len(s))
                compressed = U[:, :kept_components] @ \
                            np.diag(s[:kept_components]) @ \
                            Vt[:kept_components, :]

            compressed = np.clip(compressed, 0, 255).astype(np.uint8)

            base_path = Path(self.config['storage']['base_path'])
            timestamp = Path(raw_path).stem.replace('raw_', '')
            compressed_path = base_path / 'images' / 'compressed' / f'compressed_{timestamp}.jpg'

            compressed_img = Image.fromarray(compressed)
            compressed_img.save(str(compressed_path),
                              quality=self.config['camera']['compression_quality'])

            original_size = os.path.getsize(raw_path)
            compressed_size = os.path.getsize(compressed_path)
            ratio = original_size / compressed_size if compressed_size > 0 else 1

            self.logger.info(f"Compression complete: {ratio:.2f}x reduction "
                 f"({original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB)")

            return str(compressed_path)

        except Exception as e:
            self.logger.error(f"Image compression error: {e}")
            return None

    def create_thumbnail(self, raw_path: str, size: Tuple[int, int] = (160, 120)) -> Optional[str]:
        """Create a lightweight thumbnail for quick preview"""
        if Image is None:
            self.logger.error("PIL not available")
            return None

        try:
            img = Image.open(raw_path)
            img.thumbnail(size, Image.Resampling.BILINEAR)

            base_path = Path(self.config['storage']['base_path'])
            timestamp = Path(raw_path).stem.replace('raw_', '')
            thumb_path = base_path / 'images' / 'thumbnails' / f'thumb_{timestamp}.jpg'

            img.save(str(thumb_path), quality=60)

            return str(thumb_path)

        except Exception as e:
            self.logger.error(f"Thumbnail creation error: {e}")
            return None

    def get_image_list(self, limit: int = 50) -> List[str]:
        """Get list of captured images"""
        base_path = Path(self.config['storage']['base_path'])
        raw_path = base_path / 'images' / 'raw'

        if not raw_path.exists():
            return []

        images = sorted(raw_path.glob('raw_*.jpg'), reverse=True)
        return [str(img) for img in images[:limit]]

    def delete_image(self, filename: str) -> bool:
        """Delete an image file"""
        try:
            if os.path.exists(filename):
                os.remove(filename)

                base = Path(filename)
                if 'raw_' in base.name:
                    timestamp = base.name.replace('raw_', '')
                    compressed = base.parent.parent / 'compressed' / f'compressed_{timestamp}'
                    thumb = base.parent.parent / 'thumbnails' / f'thumb_{timestamp}'

                    for f in [compressed, thumb]:
                        if f.exists():
                            try:
                                os.remove(f)
                            except Exception:
                                pass

                return True
        except Exception as e:
            self.logger.error(f"Error deleting {filename}: {e}")
        return False

    def cleanup(self) -> None:
        """Release camera resources"""
        if self.camera:
            try:
                self.camera.release()
            except Exception as e:
                self.logger.error(f"Error releasing camera: {e}")
            finally:
                self.camera = None
                self.camera_available = False
        self.logger.info("Camera released")
