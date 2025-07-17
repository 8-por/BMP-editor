"""Simple LZW compression utilities for CMPT365 files."""

from __future__ import annotations

import time


class LZMA:
    """Very small LZMA-like compressor using a simple LZ77 scheme.

    This is **not** a full LZMA implementation but provides a minimal
    dictionary based compressor so the application can operate without
    external libraries.
    """

    WINDOW_SIZE = 4096
    MIN_MATCH = 3
    MAX_MATCH = 255

    @staticmethod
    def compress(data: bytes) -> bytes:
        out = bytearray()
        i = 0
        length = len(data)
        while i < length:
            window_start = max(0, i - LZMA.WINDOW_SIZE)
            match_len = 0
            match_dist = 0
            # Search for longest match in window
            for dist in range(1, i - window_start + 1):
                j = 0
                while (
                    j < LZMA.MAX_MATCH
                    and i + j < length
                    and data[i - dist + j] == data[i + j]
                ):
                    j += 1
                if j > match_len:
                    match_len = j
                    match_dist = dist
            if match_len >= LZMA.MIN_MATCH:
                out.append(1)
                out.extend(match_dist.to_bytes(2, "big"))
                out.append(match_len)
                i += match_len
            else:
                out.append(0)
                out.append(data[i])
                i += 1
        return bytes(out)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        out = bytearray()
        i = 0
        length = len(data)
        while i < length:
            flag = data[i]
            i += 1
            if flag == 0:
                if i >= length:
                    raise ValueError("Corrupted LZMA data")
                out.append(data[i])
                i += 1
            elif flag == 1:
                if i + 2 >= length:
                    raise ValueError("Corrupted LZMA data")
                dist = int.from_bytes(data[i : i + 2], "big")
                i += 2
                match_len = data[i]
                i += 1
                if dist == 0 or match_len == 0 or dist > len(out):
                    raise ValueError("Corrupted LZMA data")
                start = len(out) - dist
                for j in range(match_len):
                    out.append(out[start + j])
            else:
                raise ValueError("Invalid LZMA flag")
        return bytes(out)


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


def save_cmpt365(
    path: str,
    width: int,
    height: int,
    bits_per_pixel: int,
    pixels: bytes,
) -> tuple[int, int, int]:
    """Compress and save raw pixel bytes to a ``.cmpt365`` file.

    ``bits_per_pixel`` records the original colour depth so the viewer can
    display accurate metadata.  The pixel data itself is always stored as
    bytes and compressed using a simplified LZMA implementation.

    Returns ``(original_size, compressed_size, elapsed_ms)``.
    """
    start = time.perf_counter()
    compressed = LZMA.compress(pixels)
    code_width = 0  # not used by this implementation
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    header = bytearray()
    header.extend(b"CMPT")  # magic
    header.append(1)  # version
    header.append(2)  # algorithm id for LZMA
    header.append(code_width)  # unused for LZMA
    header.append(bits_per_pixel & 0xFF)  # original colour depth
    header.extend(width.to_bytes(4, "little"))
    header.extend(height.to_bytes(4, "little"))
    header.extend(len(compressed).to_bytes(4, "little"))

    with open(path, "wb") as f:
        f.write(header)
        f.write(compressed)

    return len(pixels), len(header) + len(compressed), elapsed_ms


def load_cmpt365(path: str) -> tuple[int, int, int, bytes]:
    """Load a ``.cmpt365`` file.

    Returns ``(width, height, bits_per_pixel, pixel_bytes)``.
    """
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"CMPT":
            raise ValueError("Invalid CMPT file")
        version = int.from_bytes(f.read(1), "little")
        alg = int.from_bytes(f.read(1), "little")
        code_width = int.from_bytes(f.read(1), "little")
        bits_per_pixel = int.from_bytes(f.read(1), "little")
        width = int.from_bytes(f.read(4), "little")
        height = int.from_bytes(f.read(4), "little")
        data_len = int.from_bytes(f.read(4), "little")
        data = f.read(data_len)
        if len(data) < data_len:
            raise ValueError("Truncated CMPT file")

    if alg == 1:
        pixels = LZW.decompress(data, code_width)
    elif alg == 2:
        pixels = LZMA.decompress(data)
    else:
        raise ValueError("Unsupported compression algorithm")

    bytes_per_pixel = (bits_per_pixel + 7) // 8
    expected = width * height * bytes_per_pixel
    if len(pixels) != expected:
        raise ValueError("Decompressed data size mismatch")

    return width, height, bits_per_pixel, pixels

def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} bytes"
    if size < 1024 * 1024:
        return f"{size} bytes ({size/1024:.1f} KB)"
    return f"{size} bytes ({size/1024/1024:.1f} MB)"
