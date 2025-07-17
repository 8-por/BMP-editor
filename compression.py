"""Simple LZW compression utilities for CMPT365 files."""

from __future__ import annotations

import time


class LZW:
    @staticmethod
    def compress(data: bytes) -> tuple[bytes, int]:
        """Compress bytes using a basic LZW algorithm.

        Returns a tuple of (compressed_bytes, bytes_per_code)."""
        # Initialize dictionary with single-byte entries
        dictionary: dict[bytes, int] = {bytes([i]): i for i in range(256)}
        next_code = 256
        w = b""
        codes: list[int] = []
        max_code = 255
        for byte in data:
            k = bytes([byte])
            wk = w + k
            if wk in dictionary:
                w = wk
            else:
                codes.append(dictionary[w])
                dictionary[wk] = next_code
                max_code = max(max_code, next_code)
                next_code += 1
                w = k
        if w:
            codes.append(dictionary[w])
            max_code = max(max_code, dictionary[w])

        if max_code <= 0xFFFF:
            width = 2
        elif max_code <= 0xFFFFFF:
            width = 3
        else:
            width = 4

        out = bytearray()
        for code in codes:
            out.extend(code.to_bytes(width, "big"))
        return bytes(out), width

    @staticmethod
    def decompress(data: bytes, width: int) -> bytes:
        """Decompress bytes produced by `compress` using ``width`` bytes per code."""
        if width not in (2, 3, 4):
            raise ValueError("Invalid code width")
        if len(data) % width != 0:
            raise ValueError("Corrupted LZW data length")
        codes = [int.from_bytes(data[i:i+width], "big") for i in range(0, len(data), width)]
        if not codes:
            return b""
        dictionary: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
        next_code = 256

        w = dictionary[codes[0]]
        result = bytearray(w)
        for code in codes[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = w + w[:1]
            else:
                raise ValueError("Bad compressed code")
            result.extend(entry)
            dictionary[next_code] = w + entry[:1]
            next_code += 1
            w = entry
        return bytes(result)


def save_cmpt365(path: str, width: int, height: int, pixels: bytes) -> tuple[int, int, int]:
    """Compress and save raw RGBA pixel bytes to a .cmpt365 file.

    Returns (original_size, compressed_size, elapsed_ms).
    """
    start = time.perf_counter()
    compressed, code_width = LZW.compress(pixels)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    header = bytearray()
    header.extend(b"CMPT")  # magic
    header.append(1)  # version
    header.append(1)  # algorithm id for LZW
    header.append(code_width)  # bytes per code
    header.append(0)  # reserved
    header.extend(width.to_bytes(4, "little"))
    header.extend(height.to_bytes(4, "little"))
    header.extend(len(compressed).to_bytes(4, "little"))

    with open(path, "wb") as f:
        f.write(header)
        f.write(compressed)

    return len(pixels), len(header) + len(compressed), elapsed_ms


def load_cmpt365(path: str) -> tuple[int, int, bytes]:
    """Load a .cmpt365 file and return (width, height, pixel_bytes)."""
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"CMPT":
            raise ValueError("Invalid CMPT file")
        version = int.from_bytes(f.read(1), "little")
        alg = int.from_bytes(f.read(1), "little")
        code_width = int.from_bytes(f.read(1), "little")
        f.read(1)  # reserved
        width = int.from_bytes(f.read(4), "little")
        height = int.from_bytes(f.read(4), "little")
        data_len = int.from_bytes(f.read(4), "little")
        data = f.read(data_len)
        if len(data) < data_len:
            raise ValueError("Truncated CMPT file")

    if alg != 1:
        raise ValueError("Unsupported compression algorithm")

    pixels = LZW.decompress(data, code_width)
    expected = width * height * 4
    if len(pixels) != expected:
        raise ValueError("Decompressed data size mismatch")
    return width, height, pixels


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"
    if size < 1024 * 1024:
        return f"{size} bytes ({size/1024:.1f} KB)"
    return f"{size} bytes ({size/1024/1024:.1f} MB)"
