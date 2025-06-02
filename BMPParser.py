#!/usr/bin/env python3
import struct
import sys
import os

class BMPParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.file_header = {}
        self.info_header = {}
        
    def parse(self):
        """Parse the BMP file and extract header information"""
        try:
            with open(self.filepath, 'rb') as f:
                # Read file header (14 bytes)
                file_header_data = f.read(14)
                if len(file_header_data) < 14:
                    raise ValueError("Invalid BMP file: too short")
                
                # Parse file header
                signature, file_size, reserved1, reserved2, data_offset = struct.unpack('<2sIHHI', file_header_data)
                
                if signature != b'BM':
                    raise ValueError("Not a valid BMP file")
                
                self.file_header = {
                    'signature': signature.decode('ascii'),
                    'file_size': file_size,
                    'reserved1': reserved1,
                    'reserved2': reserved2,
                    'data_offset': data_offset
                }
                
                # Read info header (first 4 bytes to determine size)
                info_size_data = f.read(4)
                if len(info_size_data) < 4:
                    raise ValueError("Invalid BMP file: incomplete info header")
                
                info_header_size = struct.unpack('<I', info_size_data)[0]
                
                # Read rest of info header
                remaining_info = f.read(info_header_size - 4)
                if len(remaining_info) < info_header_size - 4:
                    raise ValueError("Invalid BMP file: incomplete info header")
                
                # Parse basic info header (BITMAPINFOHEADER - 40 bytes minimum)
                if info_header_size >= 40:
                    info_data = info_size_data + remaining_info[:36]  # Total 40 bytes
                    header_values = struct.unpack('<IiiHHIIiiII', info_data)
                    
                    self.info_header = {
                        'header_size': header_values[0],
                        'width': header_values[1],
                        'height': header_values[2],
                        'planes': header_values[3],
                        'bits_per_pixel': header_values[4],
                        'compression': header_values[5],
                        'image_size': header_values[6],
                        'x_pixels_per_meter': header_values[7],
                        'y_pixels_per_meter': header_values[8],
                        'colors_used': header_values[9],
                        'colors_important': header_values[10]
                    }
                else:
                    raise ValueError("Unsupported BMP format: info header too small")
                    
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {self.filepath}")
        except Exception as e:
            raise Exception(f"Error parsing BMP file: {str(e)}")
    
    def get_summary(self) -> dict:
        """Return a dict with only the fields the GUI should display."""
        return {
            "File size":    f"{self.file_header['file_size']:,} bytes",
            "Dimensions":   f"{self.info_header['width']} × {abs(self.info_header['height'])}",
            "Bits/pixel":   self.info_header['bits_per_pixel'],
            "Compression":  self.get_compression_name(self.info_header['compression']),
            "Image size":   f"{self.info_header['image_size']:,} bytes",
        }

    def get_compression_name(self, compression_code):
        """Convert compression code to readable name"""
        compressions = {
            0: "BI_RGB (No compression)",
            1: "BI_RLE8 (8-bit RLE)",
            2: "BI_RLE4 (4-bit RLE)",
            3: "BI_BITFIELDS",
            4: "BI_JPEG",
            5: "BI_PNG"
        }
        return compressions.get(compression_code, f"Unknown ({compression_code})")
    
    def display_info(self):
        """Display parsed BMP information"""
        print(f"BMP File Analysis: {os.path.basename(self.filepath)}")
        print("=" * 50)
        
        print("\nFile Header:")
        print(f"  Signature: {self.file_header['signature']}")
        print(f"  File Size: {self.file_header['file_size']:,} bytes")
        print(f"  Data Offset: {self.file_header['data_offset']} bytes")
        
        print("\nImage Information:")
        print(f"  Dimensions: {self.info_header['width']} x {abs(self.info_header['height'])} pixels")
        print(f"  Bits per Pixel: {self.info_header['bits_per_pixel']}")
        print(f"  Compression: {self.get_compression_name(self.info_header['compression'])}")
        print(f"  Image Size: {self.info_header['image_size']:,} bytes")
        
        if self.info_header['colors_used'] > 0:
            print(f"  Colors Used: {self.info_header['colors_used']}")
        
        # Additional details
        print(f"\nTechnical Details:")
        print(f"  Color Planes: {self.info_header['planes']}")
        print(f"  Header Size: {self.info_header['header_size']} bytes")
        print(f"  Top-down image: {'Yes' if self.info_header['height'] < 0 else 'No'}")
        
        if self.info_header['x_pixels_per_meter'] > 0 or self.info_header['y_pixels_per_meter'] > 0:
            print(f"  Resolution: {self.info_header['x_pixels_per_meter']} x {self.info_header['y_pixels_per_meter']} pixels/meter")

def main():
    if len(sys.argv) != 2:
        print("Usage: python bmp_parser.py <bmp_file>")
        print("Example: python bmp_parser.py image.bmp")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        parser = BMPParser(filepath)
        parser.parse()
        parser.display_info()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()