#!/usr/bin/env python3
"""
Image Viewer for Ground Station
Handles receiving and displaying images from satellite
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk  # type: ignore
import io
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ground_station import CommunicationHandler


class ImageViewer:
    """Image viewer for satellite images"""

    def __init__(self, parent: tk.Widget, ground_station: Any) -> None:
        self.parent: tk.Widget = parent
        self.gs: Any = ground_station

        # Image data
        self.current_image: Optional[Image.Image] = None
        self.image_chunks: Dict[int, bytes] = {}
        self.expected_chunks: int = 0
        self.image_received: int = 0
        self.image_start_time: Optional[float] = None

        # Setup GUI
        self.setup_gui()

    def setup_gui(self) -> None:
        """Setup the image viewer GUI"""
        # Control panel
        control_frame: ttk.Frame = ttk.Frame(self.parent)
        control_frame.pack(fill='x', padx=5, pady=5)

        ttk.Button(
            control_frame, 
            text="Request Image",
            command=self.request_image
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, 
            text="Save Image",
            command=self.save_image
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            control_frame, 
            text="Clear",
            command=self.clear_image
        ).pack(side=tk.LEFT, padx=5)

        # Progress bar
        self.progress_var: tk.DoubleVar = tk.DoubleVar()
        self.progress: ttk.Progressbar = ttk.Progressbar(
            control_frame, 
            variable=self.progress_var,
            maximum=100, 
            length=200
        )
        self.progress.pack(side=tk.LEFT, padx=5)

        self.status_label: ttk.Label = ttk.Label(control_frame, text="No image")
        self.status_label.pack(side=tk.LEFT, padx=5)

        # Image display area
        self.image_frame: ttk.Frame = ttk.Frame(self.parent)
        self.image_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create canvas with scrollbars
        self.canvas: tk.Canvas = tk.Canvas(self.image_frame, bg='gray')
        v_scrollbar: ttk.Scrollbar = ttk.Scrollbar(
            self.image_frame, 
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )
        h_scrollbar: ttk.Scrollbar = ttk.Scrollbar(
            self.image_frame, 
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )

        self.canvas.configure(yscrollcommand=v_scrollbar.set,
                             xscrollcommand=h_scrollbar.set)

        # Grid layout
        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        self.image_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)

        # Image placeholder
        self.image_on_canvas: Optional[int] = None

        # Bind mouse wheel for zoom
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)

    def request_image(self) -> None:
        """Request an image from the satellite"""
        self.gs.send_command(0x03)  # CAPTURE_IMAGE command
        self.status_label.config(text="Image requested...")
        self.image_start_time = time.time()

    def add_image_chunk(self, chunk_num: int, data: bytes) -> None:
        """Add a chunk of image data"""
        self.image_chunks[chunk_num] = data
        self.image_received = len(self.image_chunks)

        # Update progress
        if self.expected_chunks == 0:
            # First chunk - try to determine total chunks
            if chunk_num == 0:
                # Assume total from first chunk? In real protocol, would have header
                pass
        else:
            progress: float = (self.image_received / self.expected_chunks) * 100
            self.progress_var.set(progress)

        self.status_label.config(
            text=f"Receiving... {self.image_received}/{self.expected_chunks or '?'}"
        )

        # Check if we have all chunks
        if self.expected_chunks > 0 and self.image_received >= self.expected_chunks:
            self.assemble_image()

    def assemble_image(self) -> None:
        """Assemble image from chunks"""
        try:
            # Sort chunks by number
            sorted_chunks: List[bytes] = [
                self.image_chunks[i] 
                for i in sorted(self.image_chunks.keys())
            ]

            # Combine all data
            image_data: bytes = b''.join(sorted_chunks)

            # Open image
            self.current_image = Image.open(io.BytesIO(image_data))

            # Display image
            self.display_image(self.current_image)

            # Update status
            elapsed: float = 0.0
            if self.image_start_time:
                elapsed = time.time() - self.image_start_time
            
            self.status_label.config(
                text=f"Image received! {self.current_image.size[0]}x{self.current_image.size[1]} "
                     f"({elapsed:.1f}s)"
            )

            # Clear chunks
            self.image_chunks = {}
            self.image_received = 0

        except Exception as e:
            self.status_label.config(text=f"Error assembling image: {e}")
            self.gs.log_message(f"Image assembly error: {e}")

    def display_image(self, image: Image.Image) -> None:
        """Display image on canvas"""
        # Resize to fit canvas initially
        canvas_width: int = self.canvas.winfo_width()
        canvas_height: int = self.canvas.winfo_height()

        if canvas_width > 10 and canvas_height > 10:
            # Calculate scaling factor
            img_width: int
            img_height: int
            img_width, img_height = image.size
            scale: float = min(canvas_width / img_width, canvas_height / img_height, 1.0)

            new_width: int = int(img_width * scale)
            new_height: int = int(img_height * scale)

            display_img: Image.Image = image.resize(
                (new_width, new_height), 
                Image.Resampling.LANCZOS
            )
        else:
            display_img = image

        # Convert to PhotoImage
        self.photo: ImageTk.PhotoImage = ImageTk.PhotoImage(display_img)

        # Update canvas
        self.canvas.delete("all")
        self.image_on_canvas = self.canvas.create_image(
            canvas_width//2, 
            canvas_height//2,
            image=self.photo, 
            anchor='center'
        )
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_image(self) -> None:
        """Save current image to file"""
        if not self.current_image:
            return

        filename: str = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[
                ("JPEG files", "*.jpg"), 
                ("PNG files", "*.png"),
                ("All files", "*.*")
            ],
            initialfile=f"satellite_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        )

        if filename:
            self.current_image.save(filename)
            self.gs.log_message(f"Image saved to {filename}")

    def clear_image(self) -> None:
        """Clear current image"""
        self.canvas.delete("all")
        self.current_image = None
        self.image_chunks = {}
        self.image_received = 0
        self.expected_chunks = 0
        self.progress_var.set(0)
        self.status_label.config(text="No image")

    def on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel for zoom"""
        # Simple zoom implementation
        scale: float = 1.1 if event.delta > 0 else 0.9

        if self.current_image and self.image_on_canvas:
            # Get current image size
            img_width: int
            img_height: int
            img_width, img_height = self.current_image.size

            # Calculate new size
            new_width: int = int(img_width * scale)
            new_height: int = int(img_height * scale)

            # Resize and display
            resized: Image.Image = self.current_image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            self.display_image(resized)
