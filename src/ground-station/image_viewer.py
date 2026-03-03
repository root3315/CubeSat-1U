#!/usr/bin/env python3
"""
Image Viewer for Ground Station
Handles receiving and displaying images from satellite
"""

import io
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Dict, Any, TYPE_CHECKING

try:
    from PIL import Image, ImageTk  # type: ignore
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

if TYPE_CHECKING:
    from ground_station import GroundStation


class ImageViewer:
    """Image viewer for satellite images"""

    def __init__(self, parent: tk.Widget, ground_station: 'GroundStation') -> None:
        self.parent = parent
        self.gs = ground_station

        self.current_image: Optional[Image.Image] = None
        self.image_chunks: Dict[int, bytes] = {}
        self.expected_chunks = 0
        self.image_received = 0
        self.image_start_time: Optional[float] = None

        self.photo: Optional[ImageTk.PhotoImage] = None
        self.image_on_canvas: Optional[int] = None
        self.canvas: Optional[tk.Canvas] = None

        self.setup_gui()

    def setup_gui(self) -> None:
        """Setup the image viewer GUI"""
        control_frame = ttk.Frame(self.parent)
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

        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            control_frame,
            variable=self.progress_var,
            maximum=100,
            length=200
        )
        self.progress.pack(side=tk.LEFT, padx=5)

        self.status_label = ttk.Label(control_frame, text="No image")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.image_frame = ttk.Frame(self.parent)
        self.image_frame.pack(fill='both', expand=True, padx=5, pady=5)

        self.canvas = tk.Canvas(self.image_frame, bg='gray')
        v_scrollbar = ttk.Scrollbar(
            self.image_frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )
        h_scrollbar = ttk.Scrollbar(
            self.image_frame,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )

        self.canvas.configure(yscrollcommand=v_scrollbar.set,
                             xscrollcommand=h_scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        self.image_frame.grid_rowconfigure(0, weight=1)
        self.image_frame.grid_columnconfigure(0, weight=1)

        self.canvas.bind('<MouseWheel>', self.on_mousewheel)

    def request_image(self) -> None:
        """Request an image from the satellite"""
        self.gs.send_command(0x03)
        self.status_label.config(text="Image requested...")
        self.image_start_time = time.time()

    def add_image_chunk(self, chunk_num: int, data: bytes) -> None:
        """Add a chunk of image data"""
        self.image_chunks[chunk_num] = data
        self.image_received = len(self.image_chunks)

        if self.expected_chunks == 0:
            if chunk_num == 0:
                pass
        else:
            progress = (self.image_received / self.expected_chunks) * 100
            self.progress_var.set(progress)

        self.status_label.config(
            text=f"Receiving... {self.image_received}/{self.expected_chunks or '?'}"
        )

        if self.expected_chunks > 0 and self.image_received >= self.expected_chunks:
            self.assemble_image()

    def assemble_image(self) -> None:
        """Assemble image from chunks"""
        try:
            sorted_chunks = [self.image_chunks[i] for i in sorted(self.image_chunks.keys())]
            image_data = b''.join(sorted_chunks)

            self.current_image = Image.open(io.BytesIO(image_data))
            self.display_image(self.current_image)

            elapsed = 0
            if self.image_start_time:
                elapsed = time.time() - self.image_start_time

            if self.current_image:
                self.status_label.config(
                    text=f"Image received! {self.current_image.size[0]}x{self.current_image.size[1]} "
                         f"({elapsed:.1f}s)"
                )

            self.image_chunks = {}
            self.image_received = 0

        except Exception as e:
            self.status_label.config(text=f"Error assembling image: {e}")
            self.gs.log_message(f"Image assembly error: {e}")

    def display_image(self, image: Image.Image) -> None:
        """Display image on canvas"""
        if not self.canvas or not PIL_AVAILABLE:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 10 and canvas_height > 10:
            img_width, img_height = image.size
            scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)

            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            display_img = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            display_img = image

        self.photo = ImageTk.PhotoImage(display_img)

        self.canvas.delete("all")
        self.image_on_canvas = self.canvas.create_image(
            canvas_width//2, canvas_height//2,
            image=self.photo, anchor='center'
        )
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def save_image(self) -> None:
        """Save current image to file"""
        if not self.current_image or not PIL_AVAILABLE:
            return

        filename = filedialog.asksaveasfilename(
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
        if self.canvas:
            self.canvas.delete("all")
        self.current_image = None
        self.image_chunks = {}
        self.image_received = 0
        self.expected_chunks = 0
        self.progress_var.set(0)
        self.status_label.config(text="No image")

    def on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel for zoom"""
        scale = 1.1 if event.delta > 0 else 0.9

        if self.current_image and self.image_on_canvas and self.canvas:
            img_width, img_height = self.current_image.size
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)

            resized = self.current_image.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            self.display_image(resized)
