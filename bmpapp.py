import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from BMPParser import BMPParser
from PIL import Image, ImageTk
import numpy as np
import os
from compression import save_cmpt365, load_cmpt365, format_size


class ImageProcessor:
    """Fast image‑processing helpers backed by NumPy vectorisation.

    All heavy pixel math (brightness, RGB masking, scaling) is now done with
    NumPy arrays instead of explicit Python loops, giving a *huge* speed‑up on
    large BMPs.
    """

    def __init__(self):
        self.original_pixels: np.ndarray | None = None  # (H, W, 4) uint8
        self.width: int = 0
        self.height: int = 0

    # ───────────────────────── IO helpers ────────────────────────── #
    def load_from_pil(self, pil_image: Image.Image) -> None:
        """Read a PIL image into a uint8 RGBA NumPy array."""
        pil_image = pil_image.convert("RGBA")  # force unified format
        self.width, self.height = pil_image.size
        # shape -> (H, W, 4)
        self.original_pixels = np.asarray(pil_image, dtype=np.uint8)

    @staticmethod
    def pixels_to_pil_image(pixels: np.ndarray, *_ignored) -> Image.Image:
        """Convert `(H, W, 4)` uint8 array back to a PIL Image."""
        if pixels is None:
            raise ValueError("pixels_to_pil_image received None")
        return Image.fromarray(pixels, mode="RGBA")

    # ──────────────────────── processors ─────────────────────────── #
    def apply_brightness(self, brightness_factor: float) -> np.ndarray:
        """Return a copy of the original image with brightness scaled.

        `brightness_factor` is in `[0, 1]` where 1 means *no* change (i.e. 100 %).
        """
        if self.original_pixels is None:
            raise ValueError("Image not loaded yet.")
        # Copy to avoid mutating the stored original
        arr = self.original_pixels.astype(np.float32)  # float for scaling
        arr[..., :3] *= brightness_factor  # scale RGB, leave alpha alone
        np.clip(arr, 0, 255, out=arr)
        return arr.astype(np.uint8)

    def apply_channel_filter(
        self,
        pixels: np.ndarray,
        show_red: bool = True,
        show_green: bool = True,
        show_blue: bool = True,
    ) -> np.ndarray:
        """Zero out selected RGB channels (alpha is untouched)."""
        filtered = pixels.copy()
        if not show_red:
            filtered[..., 0] = 0
        if not show_green:
            filtered[..., 1] = 0
        if not show_blue:
            filtered[..., 2] = 0
        return filtered

    def scale_image_manual(
        self,
        pixels: np.ndarray,
        original_width: int,
        original_height: int,
        scale_factor: float,
    ) -> tuple[np.ndarray, int, int]:
        """Nearest‑neighbour resize entirely in NumPy (★ **fast**).

        Returns `(scaled_pixels, new_width, new_height)`.
        """
        if scale_factor <= 0:
            raise ValueError("Scale factor must be positive.")
        new_width = max(1, int(original_width * scale_factor))
        new_height = max(1, int(original_height * scale_factor))

        # Build the coordinate look‑up tables (INT indices of original image)
        y_idx = (np.arange(new_height) / scale_factor).astype(np.int32)
        x_idx = (np.arange(new_width) / scale_factor).astype(np.int32)

        # Fancy indexing does the rest – broadcasting (H,1) × (W,) → (H,W)
        scaled = pixels[y_idx[:, None], x_idx, :]
        return scaled, new_width, new_height


class BMPApp(tk.Tk):
    """GUI application"""

    def __init__(self):
        super().__init__()
        self.title("BMP Inspector (NumPy Edition)")
        self.geometry("800x700")

        self.processor = ImageProcessor()
        self.current_image_path: str | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.bits_per_pixel: int = 32

        # Control variables
        self.brightness_var = tk.DoubleVar(value=100.0)  # percent
        self.scale_var = tk.DoubleVar(value=100.0)       # percent
        self.show_red = tk.BooleanVar(value=True)
        self.show_green = tk.BooleanVar(value=True)
        self.show_blue = tk.BooleanVar(value=True)

        self._build_widgets()

    # ──────────────────────── GUI layout  ────────────────────────── #
    def _build_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # File chooser
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(file_frame, text="Open BMP…", command=self.open_file).pack(side="left")
        ttk.Button(file_frame, text="Open .cmpt365…", command=self.open_cmpt_file).pack(side="left", padx=(10, 0))
        ttk.Button(file_frame, text="Compress to .cmpt365", command=self.compress_current_image).pack(side="left", padx=(10, 0))

        # Split left (controls/info) and right (preview)
        paned = ttk.PanedWindow(main_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)
        right = ttk.Frame(paned)
        paned.add(right, weight=3)

        # Notebook on the left with a single tab
        notebook = ttk.Notebook(left)
        notebook.pack(fill="both", expand=True)

        info_tab = ttk.Frame(notebook)
        notebook.add(info_tab, text="Info & Controls")

        controls_frame = ttk.LabelFrame(info_tab, text="Image Controls", padding="10")
        controls_frame.pack(fill="x", pady=(0, 10))

        # Brightness slider
        self._add_slider(
            controls_frame,
            label="Brightness:",
            variable=self.brightness_var,
            from_=0,
            to=100,
            command=self.update_image,
        )

        # Scale slider
        self._add_slider(
            controls_frame,
            label="Scale:",
            variable=self.scale_var,
            from_=10,
            to=100,
            command=self.update_image,
        )

        # RGB toggle buttons
        rgb_frame = ttk.Frame(controls_frame)
        rgb_frame.pack(fill="x")
        ttk.Label(rgb_frame, text="RGB Channels:").pack(side="left")

        btn_frame = ttk.Frame(rgb_frame)
        btn_frame.pack(side="left", padx=(10, 0))
        self.red_button = tk.Button(btn_frame, text="R", width=3, command=lambda: self.toggle_channel("red"))
        self.green_button = tk.Button(btn_frame, text="G", width=3, command=lambda: self.toggle_channel("green"))
        self.blue_button = tk.Button(btn_frame, text="B", width=3, command=lambda: self.toggle_channel("blue"))
        for b in (self.red_button, self.green_button, self.blue_button):
            b.pack(side="left", padx=2)

        ttk.Button(controls_frame, text="Reset All", command=self.reset_controls).pack(pady=(10, 0))

        # Scrollable canvas for image on the right side
        image_display = ttk.Frame(right)
        image_display.pack(fill="both", expand=True)
        canvas = tk.Canvas(image_display, bg="white")
        vbar = ttk.Scrollbar(image_display, orient="vertical", command=canvas.yview)
        hbar = ttk.Scrollbar(image_display, orient="horizontal", command=canvas.xview)
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)

        self.image_canvas = canvas
        self.image_label = ttk.Label(canvas)
        canvas.create_window(0, 0, anchor="nw", window=self.image_label)

        # Metadata tree under the same tab
        props = ttk.LabelFrame(info_tab, text="Metadata", padding="10")
        props.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(props, columns=("field", "value"), show="headings")
        self.tree.heading("field", text="Field")
        self.tree.heading("value", text="Value")
        self.tree.column("field", width=200, anchor="w")
        self.tree.column("value", width=400, anchor="w")
        scroll = ttk.Scrollbar(props, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.update_channel_buttons()

    # Helper to build a labelled slider + live % display
    def _add_slider(self, parent, label, variable, from_, to, command):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=(0, 5))
        ttk.Label(frame, text=label).pack(side="left")
        ttk.Scale(frame, from_=from_, to=to, orient="horizontal", variable=variable, command=command).pack(
            side="left", fill="x", expand=True, padx=(10, 0)
        )
        lbl = ttk.Label(frame, width=6)
        lbl.pack(side="right")

        def _update(*_):
            lbl.config(text=f"{variable.get():.0f}%")
        variable.trace_add("write", _update)
        _update()

    # ───────────────────────── File handling ─────────────────────── #
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Choose a BMP",
            filetypes=[("Bitmap Images", "*.bmp;*.dib"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            parser = BMPParser(path)
            parser.parse()
            self._populate_table(parser.get_summary())
            self.bits_per_pixel = parser.info_header.get("bits_per_pixel", 32)

            img = Image.open(path)
            self.processor.load_from_pil(img)
            self.current_image_path = path
            self.reset_controls()
            self.update_image()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def open_cmpt_file(self):
        path = filedialog.askopenfilename(
            title="Open .cmpt365",
            filetypes=[("CMPT365 Image", "*.cmpt365"), ("All files", "*.*")],
        )
        if not path:
            return
        try:

            width, height, bpp, pixels = load_cmpt365(path)
            bytes_per_pixel = (bpp + 7) // 8
            arr = np.frombuffer(pixels, dtype=np.uint8)
            arr = arr.reshape((height, width, bytes_per_pixel))
            mode = "RGBA" if bytes_per_pixel == 4 else "RGB"
            pil_img = Image.fromarray(arr, mode=mode)
            if mode != "RGBA":
                pil_img = pil_img.convert("RGBA")
            self.processor.load_from_pil(pil_img)
            self.bits_per_pixel = bpp
            self.current_image_path = None
            summary = {
                "File Size": format_size(os.path.getsize(path)),
                "Image Dimensions": f"{width} × {height} pixels",

                "Bits per pixel": BMPParser("").get_color_depth_description(bpp),

            }
            self._populate_table(summary)
            self.reset_controls()
            self.update_image()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def compress_current_image(self):
        if self.processor.original_pixels is None:
            messagebox.showerror("Error", "No image loaded")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".cmpt365",
            filetypes=[("CMPT365 Image", "*.cmpt365"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            width = self.processor.width
            height = self.processor.height
            pixels = self.processor.original_pixels.tobytes()

            orig, comp, ms = save_cmpt365(
                path, width, height, self.bits_per_pixel, pixels
            )

            ratio = orig / comp if comp else 0
            messagebox.showinfo(
                "Compression Complete",
                f"Original size: {orig} bytes\n"
                f"Compressed size: {comp} bytes\n"
                f"Compression ratio: {ratio:.2f}\n"
                f"Time: {ms} ms",
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _populate_table(self, data: dict):
        self.tree.delete(*self.tree.get_children())
        for k, v in data.items():
            self.tree.insert("", "end", values=(k, v))

    # ───────────────────────── Image updates ─────────────────────── #
    def toggle_channel(self, channel: str):
        if channel == "red":
            self.show_red.set(not self.show_red.get())
        elif channel == "green":
            self.show_green.set(not self.show_green.get())
        elif channel == "blue":
            self.show_blue.set(not self.show_blue.get())
        self.update_channel_buttons()
        self.update_image()

    def update_channel_buttons(self):
        states = [self.show_red.get(), self.show_green.get(), self.show_blue.get()]
        buttons = [self.red_button, self.green_button, self.blue_button]
        colours = ["#ff6666", "#66ff66", "#6666ff"]
        for state, btn, col in zip(states, buttons, colours):
            btn.config(bg=col if state else "#cccccc", relief="raised" if state else "sunken")

    def reset_controls(self):
        self.brightness_var.set(100.0)
        self.scale_var.set(100.0)
        self.show_red.set(True)
        self.show_green.set(True)
        self.show_blue.set(True)
        self.update_channel_buttons()

    def update_image(self, *_):
        if self.processor.original_pixels is None:
            return
        try:
            # 1. brightness
            bright = self.processor.apply_brightness(self.brightness_var.get() / 100.0)
            # 2. RGB mask
            masked = self.processor.apply_channel_filter(
                bright,
                self.show_red.get(),
                self.show_green.get(),
                self.show_blue.get(),
            )
            # 3. scale
            scale = self.scale_var.get() / 100.0
            scaled_pixels, new_w, new_h = self.processor.scale_image_manual(
                masked, self.processor.width, self.processor.height, scale
            )
            # 4. display
            pil_img = self.processor.pixels_to_pil_image(scaled_pixels)
            # limit GUI thumbnail for performance
            display_img = pil_img.copy()
            if display_img.width > 800 or display_img.height > 600:
                display_img.thumbnail((800, 600), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(display_img)
            self.image_label.configure(image=self.photo)
            self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))
        except Exception as exc:
            print(f"Error updating image: {exc}")


if __name__ == "__main__":
    BMPApp().mainloop()
