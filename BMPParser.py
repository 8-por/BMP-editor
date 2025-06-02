#!/usr/bin/env python3
import struct
import sys
import os

class BMPParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.file_header = {}
        self.info_header = {}
        
    def bytes_to_uint16_le(self, data, offset=0):
        return data[offset] + (data[offset + 1] << 8)
    
    def bytes_to_uint32_le(self, data, offset=0):
        
        return (data[offset] + 
                (data[offset + 1] << 8) + 
                (data[offset + 2] << 16) + 
                (data[offset + 3] << 24))
    
    def bytes_to_int32_le(self, data, offset=0):
        """Convert 4 bytes to signed 32-bit integer (little-endian)"""
        value = self.bytes_to_uint32_le(data, offset)
        # Handle two's complement for negative numbers
        if value >= 2**31:
            value -= 2**32
        return value
    
    def parse(self):
        """Parse the BMP file and extract header information"""
        try:
            with open(self.filepath, 'rb') as f:
                # Read file header (14 bytes)
                file_header_data = f.read(14)
                if len(file_header_data) < 14:
                    raise ValueError("Invalid BMP file: too short")
                
                # Parse file header manually
                # Bytes 0-1: Signature
                signature = chr(file_header_data[0]) + chr(file_header_data[1])
                
                if signature != 'BM':
                    raise ValueError("Not a valid BMP file")
                
                # Bytes 2-5: File size (little-endian)
                file_size = self.bytes_to_uint32_le(file_header_data, 2)
                
                # Bytes 6-7: Reserved 1
                reserved1 = self.bytes_to_uint16_le(file_header_data, 6)
                
                # Bytes 8-9: Reserved 2
                reserved2 = self.bytes_to_uint16_le(file_header_data, 8)
                
                # Bytes 10-13: Data offset
                data_offset = self.bytes_to_uint32_le(file_header_data, 10)
                
                self.file_header = {
                    'signature': signature,
                    'file_size': file_size,
                    'reserved1': reserved1,
                    'reserved2': reserved2,
                    'data_offset': data_offset
                }
                
                # Read info header (first 4 bytes to determine size)
                info_size_data = f.read(4)
                if len(info_size_data) < 4:
                    raise ValueError("Invalid BMP file: incomplete info header")
                
                info_header_size = self.bytes_to_uint32_le(info_size_data)
                
                # Read rest of info header
                remaining_info = f.read(info_header_size - 4)
                if len(remaining_info) < info_header_size - 4:
                    raise ValueError("Invalid BMP file: incomplete info header")
                
                # Parse basic info header (BITMAPINFOHEADER - 40 bytes minimum)
                if info_header_size >= 40:
                    # Combine all info header data
                    full_info_data = info_size_data + remaining_info
                    
                    # Parse each field manually
                    header_size = self.bytes_to_uint32_le(full_info_data, 0)
                    width = self.bytes_to_int32_le(full_info_data, 4)
                    height = self.bytes_to_int32_le(full_info_data, 8)
                    planes = self.bytes_to_uint16_le(full_info_data, 12)
                    bits_per_pixel = self.bytes_to_uint16_le(full_info_data, 14)
                    compression = self.bytes_to_uint32_le(full_info_data, 16)
                    image_size = self.bytes_to_uint32_le(full_info_data, 20)
                    x_pixels_per_meter = self.bytes_to_int32_le(full_info_data, 24)
                    y_pixels_per_meter = self.bytes_to_int32_le(full_info_data, 28)
                    colors_used = self.bytes_to_uint32_le(full_info_data, 32)
                    colors_important = self.bytes_to_uint32_le(full_info_data, 36)
                    
                    self.info_header = {
                        'header_size': header_size,
                        'width': width,
                        'height': height,
                        'planes': planes,
                        'bits_per_pixel': bits_per_pixel,
                        'compression': compression,
                        'image_size': image_size,
                        'x_pixels_per_meter': x_pixels_per_meter,
                        'y_pixels_per_meter': y_pixels_per_meter,
                        'colors_used': colors_used,
                        'colors_important': colors_important
                    }
                else:
                    raise ValueError("Unsupported BMP format: info header too small")
                    
        except FileNotFoundError:
            raise FileNotFoundError("File not found: " + self.filepath)
        except Exception as e:
            raise Exception("Error parsing BMP file: " + str(e))

    
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