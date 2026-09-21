"""Exports PlayStation TIM textures to PNG (Ombelll's FORMATS.md §5b).

    u32 magic = 0x10
    u32 flags      bit 0-2 = pixel mode (0 = 4 bit, 1 = 8 bit, 2 = 16 bit)
                   bit 3   = palette present
    if palette:
        u32 block length (including this field)
        u16 vram_x, vram_y, colors, palettes
        then colors*palettes 16-bit words
    image block:
        u32 block length, u16 vram_x, vram_y, width_in_words, height
        then the pixels

At 4 bits four pixels fit in a word, at 8 bits two. The colors are
BGR555; 0x0000 is fully transparent.

The PNG is written by hand with zlib, with no external dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import zlib
import sys as _sys  # noqa: E402
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from support import paths  # noqa: E402


def _png(file_path: str, image_width: int, image_height: int, rgba: bytes) -> None:
    raw = bytearray()
    for y in range(image_height):
        raw.append(0)  # filter "none"
        raw += rgba[y * image_width * 4 : (y + 1) * image_width * 4]

    def block(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(block(b"IHDR", struct.pack(">IIBBBBB", image_width, image_height, 8, 6, 0, 0, 0)))
        f.write(block(b"IDAT", zlib.compress(bytes(raw), 9)))
        f.write(block(b"IEND", b""))


def _bgr555(w: int) -> tuple[int, int, int, int]:
    if w == 0:
        return (0, 0, 0, 0)  # transparent
    r = (w & 0x1F) << 3
    g = ((w >> 5) & 0x1F) << 3
    b = ((w >> 10) & 0x1F) << 3
    return (r | r >> 5, g | g >> 5, b | b >> 5, 255)


def read_tim(data: bytes, offset: int, convert=None) -> tuple[int, int, bytes]:
    """The texture as RGBA. `convert` (r, g, b, a) -> (r, g, b, a) is applied
    to every PALETTE ENTRY, not to every texel: that is where the game does
    it too, and a paletted texture has at most 256 of them, so it costs
    nothing (`pc_colour`)."""
    magic, flag_bits = struct.unpack_from("<II", data, offset)
    if magic != 0x10:
        raise ValueError(f"no TIM at offset {offset}: magic 0x{magic:X}")
    mode = flag_bits & 7
    pos = offset + 8

    palette: list[tuple[int, int, int, int]] = []
    if flag_bits & 8:
        block_len, _vx, _vy, colors, n_palettes = struct.unpack_from("<IHHHH", data, pos)
        for i in range(colors * n_palettes):
            entry = _bgr555(struct.unpack_from("<H", data, pos + 12 + 2 * i)[0])
            palette.append(convert(*entry) if convert else entry)
        pos += block_len

    _block_len, _vx, _vy, width_words, image_height = struct.unpack_from("<IHHHH", data, pos)
    pixels = pos + 12

    if mode == 0:      # 4 bit, four pixels per word
        image_width = width_words * 4
    elif mode == 1:    # 8 bit, two per word
        image_width = width_words * 2
    else:               # 16 bit direct
        image_width = width_words

    # the rows are contiguous: all pixels in a single block, translated with a
    # per-byte table instead of pixel by pixel (from 1.5 ms to a few tenths
    # per texture; same result byte for byte, tools/diagnostics/check_tim.py)
    pixel_data = data[pixels : pixels + image_height * width_words * 2]
    if len(pixel_data) < image_height * width_words * 2:
        raise IndexError(f"TIM truncated at offset {offset}")
    outside = bytes((255, 0, 255, 255))
    palette_colors = [bytes(k) for k in palette]
    if mode in (0, 1):
        draw_color = [palette_colors[i] if i < len(palette_colors) else outside for i in range(256)]
        if mode == 0:  # 4 bit: low nibble first, then the high one
            lookup_table = [draw_color[b & 0x0F] + draw_color[b >> 4] for b in range(256)]
        else:           # 8 bit: one index per byte
            lookup_table = draw_color
        return image_width, image_height, b"".join([lookup_table[b] for b in pixel_data])
    seen_colors: dict[int, bytes] = {}
    output = []
    for (w,) in struct.iter_unpack("<H", pixel_data):
        k = seen_colors.get(w)
        if k is None:
            entry = _bgr555(w)
            k = seen_colors[w] = bytes(convert(*entry) if convert else entry)
        output.append(k)
    return image_width, image_height, b"".join(output)


# The PC's OpenGL renderer puts every colour of every texture through
# c' = int(256 * (c/256) ** (1/1.2)) when it loads it, opaque ones included,
# and then through a contrast and brightness table that with the default
# settings is the identity (finding 306; the software renderer uses 1/1.7 at
# 24 bit instead). The vertex colours are NOT touched: the 255 of a vertex
# byte stays the neutral one (finding 268).
#
# Dark and middling texels come out lighter than the file has them:
# 32 -> 45, 64 -> 80, 128 -> 143, 200 -> 208. Measured on screenshots
# of the PC game (finding 310): on the galleon's hull of Hey... What's up,
# Dock? part 1 the exponent comes out 0.856 against the 0.833 read in the
# code, and 1.011 on the same measurement of the viewer without it.
GAMMA_EXPONENT = 1.0 / 1.2
GAMMA_TABLE = bytes(min(255, int(256.0 * (c / 256.0) ** GAMMA_EXPONENT)) for c in range(256))


def with_gamma(rgba: bytes) -> bytes:
    """The RGBA of a texture with the renderer's gamma on R, G and B, the
    alpha left alone. Kept for what works on an RGBA buffer instead of on a
    palette (`checks/check_texture_gamma.py`); the viewer itself converts the
    palette entries, with `pc_colour`."""
    buffer = bytearray(rgba)
    for channel in range(3):
        buffer[channel::4] = bytes(buffer[channel::4]).translate(GAMMA_TABLE)
    return bytes(buffer)


# The four PlayStation blend modes do not exist as blend functions on the
# PC's OpenGL renderer: there is ONE glBlendFunc(GL_SRC_ALPHA,
# GL_ONE_MINUS_SRC_ALPHA) for every semi-transparent polygon, and the modes
# differ only in the alpha built into a copy of the texture when it is
# loaded, one copy per mode the texture is used with (finding 305). Per
# palette entry, with m the largest of R, G and B:
#
#   the transparent entry (palette word 0)   alpha 0
#   mode 0 (B/2 + F/2)   alpha m/2         colour + (255 - m) on each channel
#   mode 1 (B + F)       alpha m - m/4     colour + (255 - m)
#   mode 2 (B - F)       alpha luminance   colour unchanged
#   mode 3 (B + F/4)     alpha m/4         colour + (255 - m)
#   opaque               alpha 255
#
# A grey entry comes out white: 255 - m lifts every channel to 255. So an
# "additive" texel is faded towards its brightened colour, not summed, and
# over a background lighter than itself it DARKENS it. The gamma above comes
# after, on the colour the conversion left (finding 306).
BLEND_ALPHA = {0: lambda m: m // 2, 1: lambda m: m - m // 4, 3: lambda m: m // 4}


def pc_colour(blend=None):
    """The function the PC's renderer applies to every palette entry of a
    texture used with this blend mode (None: opaque), gamma included. Pass
    it to `read_tim`."""

    def convert(r, g, b, a):
        if a == 0:
            return r, g, b, 0          # the transparent entry stays transparent
        if blend is None:
            alpha = 255
        elif blend == 2:
            alpha = int(0.299 * r + 0.587 * g + 0.114 * b)
        else:
            m = max(r, g, b)
            alpha = BLEND_ALPHA[blend](m)
            push = 255 - m             # r, g and b are all <= m: never over 255
            r, g, b = r + push, g + push, b + push
        return GAMMA_TABLE[r], GAMMA_TABLE[g], GAMMA_TABLE[b], alpha

    return convert


def cut_outs(data: bytes, textures: list[dict]) -> set:
    """The ids of the textures that have a transparent entry: a word 0 in the
    palette, or a 0 among the pixels of a 16-bit one.

    The PC draws those faces NOT with the opaque ones but in the same sorted
    list as the semi-transparent ones, blended and with no alpha test
    (finding 306): leaves, grilles, the torch's flame. Reads only the palette
    where there is one."""
    output = set()
    for t in textures:
        try:
            magic, flag_bits = struct.unpack_from("<II", data, t["offset"])
            if magic != 0x10:
                continue
            pos = t["offset"] + 8
            if flag_bits & 8:
                block_len, _vx, _vy, colors, n_palettes = struct.unpack_from("<IHHHH", data, pos)
                entries = data[pos + 12: pos + 12 + 2 * colors * n_palettes]
                if any(w == 0 for (w,) in struct.iter_unpack("<H", entries)):
                    output.add(t["id"])
                continue
            # 16 bit, no palette: the pixels themselves have to be looked at
            _len, _vx, _vy, width_words, image_height = struct.unpack_from("<IHHHH", data, pos)
            pixels = data[pos + 12: pos + 12 + image_height * width_words * 2]
            if any(w == 0 for (w,) in struct.iter_unpack("<H", pixels)):
                output.add(t["id"])
        except struct.error:
            continue
    return output


def sizes(data: bytes, textures: list[dict]) -> dict[int, tuple[int, int]]:
    """texture id -> (width, height), reading only the headers."""
    output = {}
    for t in textures:
        try:
            magic, flag_bits = struct.unpack_from("<II", data, t["offset"])
            if magic != 0x10:
                continue
            pos = t["offset"] + 8
            if flag_bits & 8:
                pos += struct.unpack_from("<I", data, pos)[0]
            _len, _vx, _vy, width_words, image_height = struct.unpack_from("<IHHHH", data, pos)
            mode = flag_bits & 7
            image_width = width_words * 4 if mode == 0 else (width_words * 2 if mode == 1 else width_words)
            output[t["id"]] = (image_width, image_height)
        except struct.error:
            continue
    return output


def main() -> None:
    p = argparse.ArgumentParser(description="TIM -> PNG for a level")
    p.add_argument("section3", help="section id 3, decompressed (asset block)")
    p.add_argument("json", help="load script extract, for the texture offsets")
    p.add_argument("--chain", metavar="LEVEL",
                   help="use the cumulative table: also export the textures "
                        "registered by the companion files (see textures.py)")
    p.add_argument("--data", default=paths.DATA_BZE)
    p.add_argument("--cache", default="extracted")
    p.add_argument("-o", "--output", required=True, help="destination folder")
    p.add_argument("--scale-factor", type=int, default=1,
                   help="upscale with scale2x/scale3x: 1, 2, 3, 4, 6 or 8")
    p.add_argument("--soft", action="store_true", help="apply a light blur after upscaling")
    args = p.parse_args()

    with open(args.section3, "rb") as f:
        assets = f.read()
    with open(args.json, encoding="utf-8") as f:
        textures = json.load(f)["textures"]

    sources = [(t["id"], assets, t["offset"]) for t in textures]
    if args.chain:
        from game import textures as texmod
        table = texmod.construct(args.data, args.chain, args.cache)
        sources = [(tid, block, off) for tid, (block, off) in sorted(table.slots.items())]

    os.makedirs(args.output, exist_ok=True)
    size_counts: dict[str, int] = {}
    failure = 0
    if args.scale_factor != 1:
        from support import upscale

    for tid, block, offset in sources:
        try:
            b, h, rgba = read_tim(block, offset)
        except Exception as e:  # noqa: BLE001
            failure += 1
            print(f"  texture {tid}: {e}")
            continue
        if args.scale_factor != 1:
            b, h, rgba = upscale.enlarge((b, h, rgba), args.scale_factor, soft=args.soft)
        _png(os.path.join(args.output, f"{tid}.png"), b, h, rgba)
        size_counts[f"{b}x{h}"] = size_counts.get(f"{b}x{h}", 0) + 1

    print(f"{len(sources) - failure}/{len(sources)} textures written to {args.output}")
    for measure, n in sorted(size_counts.items(), key=lambda x: -x[1]):
        print(f"  {measure:>10s}  {n}")


if __name__ == "__main__":
    main()
