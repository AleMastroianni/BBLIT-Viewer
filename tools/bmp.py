"""Converts the disc's .bmp files to PNG, to use them as visual reference."""

from __future__ import annotations

import os
import struct
import sys
import zlib


def read_bmp(file_path: str):
    d = open(file_path, "rb").read()
    if d[:2] != b"BM":
        raise ValueError("not a BMP")
    data_off = struct.unpack_from("<I", d, 10)[0]
    header = struct.unpack_from("<I", d, 14)[0]
    image_width, image_height = struct.unpack_from("<ii", d, 18)
    depth = struct.unpack_from("<H", d, 28)[0]
    bottom_up = image_height > 0
    image_height = abs(image_height)

    palette = []
    if depth <= 8:
        n = 1 << depth
        p = 14 + header
        for i in range(n):
            b, g, r, _ = d[p + 4 * i : p + 4 * i + 4]
            palette.append((r, g, b))

    step = ((image_width * depth + 31) // 32) * 4
    output = bytearray(image_width * image_height * 3)
    for y in range(image_height):
        row_no = image_height - 1 - y if bottom_up else y
        basis = data_off + row_no * step
        for x in range(image_width):
            if depth == 8:
                color_value = palette[d[basis + x]]
            elif depth == 24:
                b, g, r = d[basis + 3 * x : basis + 3 * x + 3]
                color_value = (r, g, b)
            elif depth == 4:
                byte = d[basis + x // 2]
                color_value = palette[(byte >> 4) if x % 2 == 0 else (byte & 0xF)]
            else:
                raise ValueError(f"bit depth {depth} not supported")
            o = (y * image_width + x) * 3
            output[o : o + 3] = bytes(color_value)
    return image_width, image_height, bytes(output)


def write_png(file_path, image_width, image_height, rgb):
    raw = bytearray()
    for y in range(image_height):
        raw.append(0)
        raw += rgb[y * image_width * 3 : (y + 1) * image_width * 3]

    def block(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(block(b"IHDR", struct.pack(">IIBBBBB", image_width, image_height, 8, 2, 0, 0, 0)))
        f.write(block(b"IDAT", zlib.compress(bytes(raw), 6)))
        f.write(block(b"IEND", b""))


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    b, h, rgb = read_bmp(source)
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    write_png(target, b, h, rgb)
    print(f"{os.path.basename(source)}: {b}x{h} -> {target}")
