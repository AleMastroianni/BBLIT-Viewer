"""Upscaling of the original textures without inventing detail.

The Lost in Time textures are tiny: almost all 16x16 or 32x32, at 4 bits.
Upscaling them with linear interpolation smears them; an algorithm designed for
pixel art keeps the edges sharp and only rounds off the staircases.

This module has `scale2x` (also known as EPX/AdvMAME2x) and `scale3x`, composed to
reach 2x, 3x, 4x, 6x, 8x, plus a soft mode that applies a weighted average
after upscaling, for those who prefer a less jagged result.

No detail is invented: both are deterministic filters that
look only at the eight neighbouring pixels.
"""

from __future__ import annotations

Bitmap = tuple[int, int, bytes]  # (width, height, rgba)


def _px(rgba: bytes, b: int, h: int, x: int, y: int) -> bytes:
    x = 0 if x < 0 else (b - 1 if x >= b else x)
    y = 0 if y < 0 else (h - 1 if y >= h else y)
    o = (y * b + x) * 4
    return rgba[o : o + 4]


def scale2x(bitmap: Bitmap) -> Bitmap:
    b, h, rgba = bitmap
    nb, nh = b * 2, h * 2
    output = bytearray(nb * nh * 4)
    for y in range(h):
        for x in range(b):
            p = _px(rgba, b, h, x, y)
            a = _px(rgba, b, h, x, y - 1)
            c = _px(rgba, b, h, x - 1, y)
            d = _px(rgba, b, h, x + 1, y)
            e = _px(rgba, b, h, x, y + 1)
            e0 = a if (c == a and c != e and a != d) else p
            e1 = d if (a == d and a != c and d != e) else p
            e2 = c if (e == c and e != d and c != a) else p
            e3 = e if (d == e and d != a and e != c) else p
            o0 = ((y * 2) * nb + x * 2) * 4
            o1 = ((y * 2 + 1) * nb + x * 2) * 4
            output[o0 : o0 + 4] = e0
            output[o0 + 4 : o0 + 8] = e1
            output[o1 : o1 + 4] = e2
            output[o1 + 4 : o1 + 8] = e3
    return nb, nh, bytes(output)


def scale3x(bitmap: Bitmap) -> Bitmap:
    b, h, rgba = bitmap
    nb, nh = b * 3, h * 3
    output = bytearray(nb * nh * 4)
    for y in range(h):
        for x in range(b):
            p = _px(rgba, b, h, x, y)
            a = _px(rgba, b, h, x - 1, y - 1)
            bb = _px(rgba, b, h, x, y - 1)
            c = _px(rgba, b, h, x + 1, y - 1)
            d = _px(rgba, b, h, x - 1, y)
            f = _px(rgba, b, h, x + 1, y)
            g = _px(rgba, b, h, x - 1, y + 1)
            hh = _px(rgba, b, h, x, y + 1)
            i = _px(rgba, b, h, x + 1, y + 1)
            if bb != hh and d != f:
                e = [d if d == bb else p,
                     bb if (d == bb and p != c) or (bb == f and p != a) else p,
                     f if f == bb else p,
                     d if (d == bb and p != g) or (d == hh and p != a) else p,
                     p,
                     f if (bb == f and p != i) or (hh == f and p != c) else p,
                     d if d == hh else p,
                     hh if (d == hh and p != i) or (hh == f and p != g) else p,
                     f if f == hh else p]
            else:
                e = [p] * 9
            for k, val in enumerate(e):
                o = ((y * 3 + k // 3) * nb + x * 3 + k % 3) * 4
                output[o : o + 4] = val
    return nb, nh, bytes(output)


def _soften(bitmap: Bitmap) -> Bitmap:
    """Light 3x3 average that respects transparent pixels."""
    b, h, rgba = bitmap
    output = bytearray(rgba)
    for y in range(h):
        for x in range(b):
            o = (y * b + x) * 4
            if rgba[o + 3] == 0:
                continue
            running_sum = [0, 0, 0]
            n = 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = _px(rgba, b, h, x + dx, y + dy)
                    if q[3] == 0:
                        continue
                    weight = 4 if (dx == 0 and dy == 0) else 1
                    for k in range(3):
                        running_sum[k] += q[k] * weight
                    n += weight
            for k in range(3):
                output[o + k] = running_sum[k] // n
    return b, h, bytes(output)


def enlarge(bitmap: Bitmap, factor: int, *, soft: bool = False) -> Bitmap:
    """Upscales by 1, 2, 3, 4, 6 or 8 by composing scale2x and scale3x."""
    step_plan = {1: [], 2: [2], 3: [3], 4: [2, 2], 6: [2, 3], 8: [2, 2, 2]}
    if factor not in step_plan:
        raise ValueError(f"unsupported factor: {factor} (use 1, 2, 3, 4, 6 or 8)")
    for step in step_plan[factor]:
        bitmap = scale2x(bitmap) if step == 2 else scale3x(bitmap)
    if soft and factor > 1:
        bitmap = _soften(bitmap)
    return bitmap
