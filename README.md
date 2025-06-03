# BMP-editor

A simple Python-based GUI application for inspecting and modifying BMP images.

## Setup

1. Run the provided `setup.sh` script to create a virtual environment and install dependencies:

```bash
./setup.sh
```

2. Activate the virtual environment:

```bash
source venv/bin/activate
```

## Running

After activating the virtual environment, launch the GUI with:

```bash
python bmpapp.py
```

The application requires Python 3.8 or newer. The dependencies include
[Pillow](https://python-pillow.org/) and [NumPy](https://numpy.org/).

## Key Functions

Below are excerpts of the main routines to give a quick idea of how the
application works.

### Parsing a BMP

`BMPParser.parse()` reads the file headers and stores them in dictionaries for
later use:

```python
def parse(self):
    with open(self.filepath, "rb") as f:
        file_header_data = f.read(14)
        signature = chr(file_header_data[0]) + chr(file_header_data[1])
        if signature != "BM":
            raise ValueError("Not a valid BMP file")
        file_size = self.bytes_to_uint32_le(file_header_data, 2)
        ...
        self.file_header = {
            "signature": signature,
            "file_size": file_size,
            # more fields here
        }
        # info header is parsed in the same fashion
        self.parsed = True
```

### Image Processing Helpers

`ImageProcessor` performs fast pixel operations using NumPy arrays. For example
the brightness function scales the RGB channels without loops:

```python
def apply_brightness(self, brightness_factor: float) -> np.ndarray:
    arr = self.original_pixels.astype(np.float32)
    arr[..., :3] *= brightness_factor
    np.clip(arr, 0, 255, out=arr)
    return arr.astype(np.uint8)
```

RGB channels can be toggled individually:

```python
def apply_channel_filter(self, pixels: np.ndarray,
                         show_red=True, show_green=True, show_blue=True):
    filtered = pixels.copy()
    if not show_red:
        filtered[..., 0] = 0
    if not show_green:
        filtered[..., 1] = 0
    if not show_blue:
        filtered[..., 2] = 0
    return filtered
```

A small nearest‑neighbour scaler is included as well:

```python
def scale_image_manual(self, pixels, original_width, original_height, scale):
    new_w = max(1, int(original_width * scale))
    new_h = max(1, int(original_height * scale))
    y_idx = (np.arange(new_h) / scale).astype(np.int32)
    x_idx = (np.arange(new_w) / scale).astype(np.int32)
    scaled = pixels[y_idx[:, None], x_idx, :]
    return scaled, new_w, new_h
```

### Updating the Display

Whenever a new file is opened or controls are changed, `BMPApp.update_image()`
applies the selected operations and refreshes the canvas:

```python
def update_image(self, *_):
    bright = self.processor.apply_brightness(self.brightness_var.get() / 100.0)
    masked = self.processor.apply_channel_filter(
        bright, self.show_red.get(), self.show_green.get(), self.show_blue.get()
    )
    scale = self.scale_var.get() / 100.0
    scaled_pixels, _, _ = self.processor.scale_image_manual(
        masked, self.processor.width, self.processor.height, scale
    )
    pil_img = self.processor.pixels_to_pil_image(scaled_pixels)
    ...
    self.image_label.configure(image=self.photo)
```

