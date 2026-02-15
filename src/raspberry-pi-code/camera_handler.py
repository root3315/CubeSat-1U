#!/usr/bin/env python3
"""
Optimized Camera handler for Raspberry Pi Camera Module
Lightweight implementation optimized for resource-constrained environments
"""

import cv2
import numpy as np
from PIL import Image
import os
import time
import logging
import threading
from datetime import datetime
from pathlib import Path


class CameraHandler:
    """Optimized camera handler with reduced resource usage"""

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('CameraHandler')

        # Initialize camera
        self.camera = None
        self.init_camera()

        # Create storage directories
        self.setup_storage()

    def init_camera(self):
        """Initialize the camera with optimized settings"""
        try:
            # Use lower resolution initially for faster startup
            self.camera = cv2.VideoCapture(0)
            
            # Set properties for optimal performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 
                           self.config['camera']['resolution'][0] // 2)  # Lower res for speed
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 
                           self.config['camera']['resolution'][1] // 2)  # Lower res for speed
            self.camera.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS for efficiency
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer

            # Warm up camera with fewer frames
            for _ in range(3):  # Reduced warm-up
                self.camera.read()

            self.logger.info("Camera initialized successfully with optimized settings")
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            self.camera = None

    def setup_storage(self):
        """Setup image storage directories"""
        base_path = Path(self.config['storage']['base_path'])

        # Create directories
        dirs = ['images/raw', 'images/compressed', 'images/thumbnails']
        for dir_path in dirs:
            full_path = base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

    def capture_image(self, output_queue=None):
        """Capture an image from the camera with optimized performance"""
        if not self.camera:
            self.logger.error("Camera not initialized")
            return None

        try:
            self.logger.info("Capturing image...")

            # Capture frame
            ret, frame = self.camera.read()
            if not ret:
                self.logger.error("Failed to capture image")
                return None

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            base_path = Path(self.config['storage']['base_path'])
            filename = base_path / 'images' / 'raw' / f'raw_{timestamp}.jpg'

            # Save raw image with optimized quality
            cv2.imwrite(str(filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])  # Slightly lower quality for speed

            # Get file size
            file_size = os.path.getsize(filename) / 1024  # KB

            self.logger.info(f"Image captured: {filename} ({file_size:.1f} KB)")

            # Add metadata
            image_info = {
                'filename': str(filename),
                'timestamp': timestamp,
                'size': frame.shape,
                'file_size_kb': file_size,
                'capture_time': time.time()
            }

            # Send to output queue if provided
            if output_queue:
                try:
                    output_queue.put_nowait(image_info)  # Use put_nowait to avoid blocking
                except:
                    self.logger.warning("Output queue full, dropping image info")

            return image_info

        except Exception as e:
            self.logger.error(f"Image capture error: {e}")
            return None

    def compress_image(self, raw_path, n_components=30):  # Reduced components for speed
        """Optimized image compression using SVD with fewer components"""
        try:
            self.logger.info(f"Compressing image: {raw_path}")

            # Load image
            img = Image.open(raw_path)
            
            # Resize to smaller dimensions for faster processing
            img = img.resize((img.width // 2, img.height // 2), Image.Resampling.LANCZOS)
            
            img_array = np.array(img)

            # Convert to float for processing
            img_float = img_array.astype(float)

            # Apply optimized SVD compression
            if len(img_float.shape) == 3:
                # Color image - process each channel separately
                compressed = np.zeros_like(img_float)

                for channel in range(3):
                    U, s, Vt = np.linalg.svd(img_float[:, :, channel],
                                             full_matrices=False)

                    # Keep only top n_components (reduced for speed)
                    kept_components = min(n_components, len(s))  # Ensure we don't exceed available components
                    compressed[:, :, channel] = U[:, :kept_components] @ \
                                                np.diag(s[:kept_components]) @ \
                                                Vt[:kept_components, :]
            else:
                # Grayscale
                U, s, Vt = np.linalg.svd(img_float, full_matrices=False)
                kept_components = min(n_components, len(s))  # Ensure we don't exceed available components
                compressed = U[:, :kept_components] @ \
                            np.diag(s[:kept_components]) @ \
                            Vt[:kept_components, :]

            # Clip values and convert back to uint8
            compressed = np.clip(compressed, 0, 255).astype(np.uint8)

            # Generate compressed filename
            base_path = Path(self.config['storage']['base_path'])
            timestamp = Path(raw_path).stem.replace('raw_', '')
            compressed_path = base_path / 'images' / 'compressed' / f'compressed_{timestamp}.jpg'

            # Save compressed image
            compressed_img = Image.fromarray(compressed)
            compressed_img.save(str(compressed_path),
                              quality=self.config['camera']['compression_quality'])

            # Calculate compression ratio
            original_size = os.path.getsize(raw_path)
            compressed_size = os.path.getsize(compressed_path)
            ratio = original_size / compressed_size if compressed_size > 0 else 1

            self.logger.info(f"Compression complete: {ratio:.2f}x reduction "
                 f"({original_size/1024:.1f}KB -> {compressed_size/1024:.1f}KB)")

            return str(compressed_path)

        except Exception as e:
            self.logger.error(f"Image compression error: {e}")
            return None

    def create_thumbnail(self, raw_path, size=(160, 120)):  # Smaller thumbnails for speed
        """Create a lightweight thumbnail for quick preview"""
        try:
            # Load image
            img = Image.open(raw_path)

            # Create thumbnail with optimized resampling
            img.thumbnail(size, Image.Resampling.BILINEAR)  # Faster resampling method

            # Generate thumbnail filename
            base_path = Path(self.config['storage']['base_path'])
            timestamp = Path(raw_path).stem.replace('raw_', '')
            thumb_path = base_path / 'images' / 'thumbnails' / f'thumb_{timestamp}.jpg'

            # Save thumbnail with lower quality for speed
            img.save(str(thumb_path), quality=60)

            return str(thumb_path)

        except Exception as e:
            self.logger.error(f"Thumbnail creation error: {e}")
            return None

    def get_image_list(self, limit=50):  # Reduced limit for efficiency
        """Get list of captured images with optimized performance"""
        base_path = Path(self.config['storage']['base_path'])
        raw_path = base_path / 'images' / 'raw'

        if not raw_path.exists():
            return []

        images = sorted(raw_path.glob('raw_*.jpg'), reverse=True)
        return [str(img) for img in images[:limit]]

    def delete_image(self, filename):
        """Delete an image file with optimized performance"""
        try:
            if os.path.exists(filename):
                os.remove(filename)

                # Also delete associated compressed and thumbnail
                base = Path(filename)
                if 'raw_' in base.name:
                    timestamp = base.name.replace('raw_', '')
                    compressed = base.parent.parent / 'compressed' / f'compressed_{timestamp}'
                    thumb = base.parent.parent / 'thumbnails' / f'thumb_{timestamp}'

                    for f in [compressed, thumb]:
                        if f.exists():
                            try:
                                os.remove(f)
                            except:
                                pass  # Ignore errors when deleting associated files

                return True
        except Exception as e:
            self.logger.error(f"Error deleting {filename}: {e}")
        return False

    def cleanup(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            self.logger.info("Camera released")