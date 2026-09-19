"""The fast TIM reader (per-byte table) against the old one, pixel by pixel:
they must give the same bytes on every texture of the given levels.

    .venv/Scripts/python tools/diagnostics/check_tim.py [L03A L01A ...]

Without arguments it tests every level the menu opens. Exits with 1 if a
texture differs.
"""
import os
import struct
import sys
import time

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import levels  # noqa: E402
import loadscript  # noqa: E402
import paths  # noqa: E402
import tim  # noqa: E402
from viewer import sections  # noqa: E402


def read_tim_slow(data, offset):
    """The previous, slower version, unchanged."""
    magic, flag_bits = struct.unpack_from("<II", data, offset)
    if magic != 0x10:
        raise ValueError("magic")
    mode = flag_bits & 7
    pos = offset + 8
    palette = []
    if flag_bits & 8:
        block_len, _vx, _vy, colors, n_palettes = struct.unpack_from("<IHHHH", data, pos)
        for i in range(colors * n_palettes):
            palette.append(tim._bgr555(struct.unpack_from("<H", data, pos + 12 + 2 * i)[0]))
        pos += block_len
    _block_len, _vx, _vy, width_words, image_height = struct.unpack_from("<IHHHH", data, pos)
    pixels = pos + 12
    image_width = width_words * 4 if mode == 0 else (width_words * 2 if mode == 1 else width_words)
    rgba = bytearray(image_width * image_height * 4)
    for y in range(image_height):
        for x in range(image_width):
            if mode == 0:
                b = data[pixels + y * width_words * 2 + x // 2]
                index = (b & 0x0F) if x % 2 == 0 else (b >> 4)
                color_value = palette[index] if index < len(palette) else (255, 0, 255, 255)
            elif mode == 1:
                index = data[pixels + y * width_words * 2 + x]
                color_value = palette[index] if index < len(palette) else (255, 0, 255, 255)
            else:
                w = struct.unpack_from("<H", data, pixels + (y * width_words + x) * 2)[0]
                color_value = tim._bgr555(w)
            o = (y * image_width + x) * 4
            rgba[o: o + 4] = bytes(color_value)
    return image_width, image_height, bytes(rgba)


name_list = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
n_identical = n_mismatched = errors = 0
mode_counts = {}
t_slow = t_fast = 0.0
for entry_name in name_list:
    file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
    if not os.path.exists(file_path):
        continue
    sec = sections(file_path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    for t in lvl["textures"]:
        try:
            a0 = time.perf_counter()
            old = read_tim_slow(sec[3], t["offset"])
            a1 = time.perf_counter()
        except Exception:  # noqa: BLE001
            old = None
            a1 = time.perf_counter()
        try:
            new = tim.read_tim(sec[3], t["offset"])
        except Exception:  # noqa: BLE001
            new = None
        a2 = time.perf_counter()
        t_slow += a1 - a0
        t_fast += a2 - a1
        if old is None and new is None:
            errors += 1
        elif old == new:
            n_identical += 1
            tim_mode = struct.unpack_from("<I", sec[3], t["offset"] + 4)[0] & 7
            mode_counts[tim_mode] = mode_counts.get(tim_mode, 0) + 1
        else:
            n_mismatched += 1
            print(f"DIFFERENT: {entry_name} texture {t['id']} offset {t['offset']}")
print(f"{len(name_list)} levels: {n_identical} textures identical (per mode: {dict(sorted(mode_counts.items()))}), "
      f"{n_mismatched} different, {errors} unreadable by both")
print(f"time: old {t_slow:.2f} s, new {t_fast:.2f} s")
sys.exit(1 if n_mismatched else 0)
