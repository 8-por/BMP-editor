#!/usr/bin/env python3
# BMP Parser - Refactored for GUI integration

class BMPParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.file_header = {}
        self.info_header = {}
        self.parsed = False
    
    def bytes_to_uint16_le(self, data, offset=0):
        """Convert 2 bytes to unsigned 16-bit integer (little-endian)"""
        return data[offset] + (data[offset + 1] << 8)
    
    def bytes_to_uint32_le(self, data, offset=0):
        """Convert 4 bytes to unsigned 32-bit integer (little-endian)"""
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
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes:,} bytes ({size_bytes/1024:.1f} KB)"
        else:
            return f"{size_bytes:,} bytes ({size_bytes/1024/1024:.1f} MB)"
    
    def get_color_depth_description(self, bits_per_pixel):
        """Get description of color depth"""
        descriptions = {
            1: "1-bit (Monochrome)",
            4: "4-bit (16 colors)",
            8: "8-bit (256 colors)",
            16: "16-bit (High Color)",
            24: "24-bit (True Color)",
            32: "32-bit (True Color + Alpha)"
        }
        return descriptions.get(bits_per_pixel, f"{bits_per_pixel}-bit")
    
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
                
                self.parsed = True
                    
        except FileNotFoundError:
            raise FileNotFoundError("File not found: " + self.filepath)
        except Exception as e:
            raise Exception("Error parsing BMP file: " + str(e))
    
    def get_summary(self):
        """Return a dictionary of key-value pairs for GUI display"""
        if not self.parsed:
            raise ValueError("File not parsed yet. Call parse() first.")
        
        summary = {}
        
        # File information
        summary["File Size"] = self.format_file_size(self.file_header['file_size'])
        
        # Image dimensions and basic info
        height_abs = abs(self.info_header['height'])
        summary["Image Dimensions"] = f"{self.info_header['width']} × {height_abs} pixels"
        summary["Bits per pixel"] = self.get_color_depth_description(self.info_header['bits_per_pixel'])
        
        
        return summary
    
    def get_raw_data(self):
        """Return raw parsed data for advanced users"""
        if not self.parsed:
            raise ValueError("File not parsed yet. Call parse() first.")
        
        return {
            'file_header': self.file_header,
            'info_header': self.info_header
        }
    
    def display_info(self):
        """Display parsed BMP information (for CLI compatibility)"""
        if not self.parsed:
            print("Error: File not parsed yet. Call parse() first.")
            return
            
        # Get just the filename without path (manual implementation)
        filename = self.filepath
        if '/' in filename:
            filename = filename.split('/')[-1]
        if '\\' in filename:
            filename = filename.split('\\')[-1]
            
        print("BMP File Analysis: " + filename)
        print("=" * 50)
        
        # Use the summary data for consistent formatting
        summary = self.get_summary()
        for field, value in summary.items():
            print(f"  {field}: {value}")

def main():
    try:
        import sys
        if len(sys.argv) != 2:
            print("Usage: python bmp_parser.py <bmp_file>")
            print("Example: python bmp_parser.py image.bmp")
            return
        
        filepath = sys.argv[1]
        
        parser = BMPParser(filepath)
        parser.parse()
        parser.display_info()
        
    except Exception as e:
        print("Error: " + str(e))

if __name__ == "__main__":
    main()