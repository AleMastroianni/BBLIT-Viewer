"""Renders an OBJ to PNG with no external dependencies, to check the data.

It separates "the data is wrong" from "the engine draws it badly":
if this rendering is correct, the geometry is correct.

Uses the OBJ vertex colors (`v x y z r g b` extension), a z-buffer
and minimal lighting just to give relief.
"""

from __future__ import annotations

import argparse
import math
import struct
import zlib


def read_png(file_path: str):
    """Minimal PNG reader (8-bit RGBA), to resample the exported textures."""
    data = open(file_path, "rb").read()
    pos, idat, image_width, image_height = 8, bytearray(), 0, 0
    while pos < len(data):
        run_length = struct.unpack_from(">I", data, pos)[0]
        tag = data[pos + 4 : pos + 8]
        block = data[pos + 8 : pos + 8 + run_length]
        if tag == b"IHDR":
            image_width, image_height, depth, color_value = struct.unpack_from(">IIBB", block, 0)
            if depth != 8 or color_value != 6:
                raise ValueError(f"{file_path}: expected 8-bit RGBA")
        elif tag == b"IDAT":
            idat += block
        elif tag == b"IEND":
            break
        pos += 12 + run_length

    raw = zlib.decompress(bytes(idat))
    step, output, prev_row = image_width * 4, bytearray(), bytes(image_width * 4)
    p = 0
    for _y in range(image_height):
        filter_, rule = raw[p], bytearray(raw[p + 1 : p + 1 + step])
        p += 1 + step
        for i in range(step):
            a = rule[i - 4] if i >= 4 else 0
            b = prev_row[i]
            c = prev_row[i - 4] if i >= 4 else 0
            if filter_ == 1:
                rule[i] = (rule[i] + a) & 0xFF
            elif filter_ == 2:
                rule[i] = (rule[i] + b) & 0xFF
            elif filter_ == 3:
                rule[i] = (rule[i] + (a + b) // 2) & 0xFF
            elif filter_ == 4:
                pp = a + b - c
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                rule[i] = (rule[i] + pred) & 0xFF
        output += rule
        prev_row = bytes(rule)
    return image_width, image_height, bytes(output)


def read_mtl(file_path: str, png_dir: str):
    """material -> image (width, height, rgba), for materials with map_Kd."""
    import os
    textures, name = {}, None
    if not os.path.exists(file_path):
        return textures
    for rule in open(file_path, encoding="utf-8"):
        d = rule.split()
        if not d:
            continue
        if d[0] == "newmtl":
            name = d[1]
        elif d[0] == "map_Kd" and name:
            texture_file = os.path.join(png_dir, os.path.basename(d[1]))
            if os.path.exists(texture_file):
                try:
                    textures[name] = read_png(texture_file)
                except Exception:  # noqa: BLE001
                    pass
    return textures


def read_obj(file_path: str):
    v, vc, vt, faces = [], [], [], []
    material = None
    with open(file_path, encoding="utf-8") as f:
        for rule in f:
            d = rule.split()
            if not d:
                continue
            if d[0] == "v":
                v.append((float(d[1]), float(d[2]), float(d[3])))
                vc.append((float(d[4]), float(d[5]), float(d[6])) if len(d) >= 7 else (0.5, 0.5, 0.5))
            elif d[0] == "vt":
                vt.append((float(d[1]), float(d[2])))
            elif d[0] == "usemtl":
                material = d[1]
            elif d[0] == "f":
                idx, uvs = [], []
                for p in d[1:]:
                    tokens = p.split("/")
                    idx.append(int(tokens[0]) - 1)
                    uvs.append(int(tokens[1]) - 1 if len(tokens) > 1 and tokens[1] else None)
                for k in range(1, len(idx) - 1):
                    faces.append(((idx[0], idx[k], idx[k + 1]),
                                    (uvs[0], uvs[k], uvs[k + 1]), material))
    return v, vc, vt, faces


def _png(file_path, w, h, rgb):
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y * w * 3 : (y + 1) * w * 3]

    def block(tag, d):
        return struct.pack(">I", len(d)) + tag + d + struct.pack(">I", zlib.crc32(tag + d) & 0xFFFFFFFF)

    with open(file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(block(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(block(b"IDAT", zlib.compress(bytes(raw), 6)))
        f.write(block(b"IEND", b""))


def render(v, vc, faces, output, image_width=900, image_height=700, azimuth=45.0, elevation=35.0,
           vt=None, textures=None):
    bbox_min = [min(p[i] for p in v) for i in range(3)]
    bbox_max = [max(p[i] for p in v) for i in range(3)]
    mid = [(a + b) / 2 for a, b in zip(bbox_min, bbox_max)]

    a, e = math.radians(azimuth), math.radians(elevation)
    ca, sa, ce, se = math.cos(a), math.sin(a), math.cos(e), math.sin(e)
    right_vec = (ca, 0.0, -sa)
    op = (-sa * se, ce, -ca * se)
    depth_axis = (sa * ce, se, ca * ce)

    def project(p):
        d = (p[0] - mid[0], p[1] - mid[1], p[2] - mid[2])
        return (sum(d[i] * right_vec[i] for i in range(3)),
                sum(d[i] * op[i] for i in range(3)),
                sum(d[i] * depth_axis[i] for i in range(3)))

    points = [project(p) for p in v]
    sx = [p[0] for p in points]
    sy = [p[1] for p in points]
    scale_factor = 0.92 * min(image_width / (max(sx) - min(sx) + 1e-6), image_height / (max(sy) - min(sy) + 1e-6))
    screen_pts = [((p[0] * scale_factor + image_width / 2), (image_height / 2 - p[1] * scale_factor), p[2]) for p in points]

    buf = bytearray(image_width * image_height * 3)
    for i in range(0, len(buf), 3):
        buf[i : i + 3] = b"\x10\x12\x18"
    zbuf = [1e18] * (image_width * image_height)

    for tri, uv_tri, material in faces:
        p0, p1, p2 = (screen_pts[i] for i in tri)
        double_area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
        if abs(double_area) < 1e-9:
            continue
        w0, w1, w2 = (v[i] for i in tri)
        nx = (w1[1] - w0[1]) * (w2[2] - w0[2]) - (w1[2] - w0[2]) * (w2[1] - w0[1])
        ny = (w1[2] - w0[2]) * (w2[0] - w0[0]) - (w1[0] - w0[0]) * (w2[2] - w0[2])
        nz = (w1[0] - w0[0]) * (w2[1] - w0[1]) - (w1[1] - w0[1]) * (w2[0] - w0[0])
        normal_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        light = 0.55 + 0.45 * abs((nx * 0.3 + ny * 0.9 + nz * 0.3) / normal_len)
        color_value = [sum(vc[i][k] for i in tri) / 3 for k in range(3)]

        tex = textures.get(material) if textures else None
        has_uv = tex is not None and vt is not None and all(u is not None for u in uv_tri)

        xmin = max(int(min(p0[0], p1[0], p2[0])), 0)
        xmax = min(int(max(p0[0], p1[0], p2[0])) + 1, image_width - 1)
        ymin = max(int(min(p0[1], p1[1], p2[1])), 0)
        ymax = min(int(max(p0[1], p1[1], p2[1])) + 1, image_height - 1)
        for y in range(ymin, ymax + 1):
            for x in range(xmin, xmax + 1):
                px, py = x + 0.5, y + 0.5
                b0 = ((p1[0] - px) * (p2[1] - py) - (p2[0] - px) * (p1[1] - py)) / double_area
                b1 = ((p2[0] - px) * (p0[1] - py) - (p0[0] - px) * (p2[1] - py)) / double_area
                b2 = 1.0 - b0 - b1
                if b0 < 0 or b1 < 0 or b2 < 0:
                    continue
                z = b0 * p0[2] + b1 * p1[2] + b2 * p2[2]
                o = y * image_width + x
                if z >= zbuf[o]:
                    continue

                rgb = color_value
                if has_uv:
                    tb, th, rgba = tex
                    u = b0 * vt[uv_tri[0]][0] + b1 * vt[uv_tri[1]][0] + b2 * vt[uv_tri[2]][0]
                    vv = b0 * vt[uv_tri[0]][1] + b1 * vt[uv_tri[1]][1] + b2 * vt[uv_tri[2]][1]
                    tx = min(tb - 1, max(0, int(u * (tb - 1))))
                    ty = min(th - 1, max(0, int((1.0 - vv) * (th - 1))))
                    s = (ty * tb + tx) * 4
                    if rgba[s + 3] == 0:
                        continue  # TIM black: fully transparent
                    rgb = [rgba[s] / 255 * color_value[0] * 2, rgba[s + 1] / 255 * color_value[1] * 2,
                           rgba[s + 2] / 255 * color_value[2] * 2]
                    zbuf[o] = z
                    buf[o * 3 : o * 3 + 3] = bytes(min(255, int(255 * min(1.0, k) * light)) for k in rgb)
                    continue

                # the docs: a textured face is texture x color (128 = neutral,
                # hence factor 2); an untextured one shows the exact color
                zbuf[o] = z
                buf[o * 3 : o * 3 + 3] = bytes(
                    min(255, int(255 * min(1.0, k) * light)) for k in rgb)

    _png(output, image_width, image_height, bytes(buf))


def main() -> None:
    p = argparse.ArgumentParser(description="check rendering of an OBJ")
    p.add_argument("obj")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--azimuth", type=float, default=45.0)
    p.add_argument("--elevation", type=float, default=35.0)
    p.add_argument("--image-width", type=int, default=900)
    p.add_argument("--image-height", type=int, default=700)
    p.add_argument("--textures", help="folder with the texture PNGs")
    args = p.parse_args()

    import os

    v, vc, vt, faces = read_obj(args.obj)
    print(f"{args.obj}: {len(v)} vertices, {len(faces)} triangles")
    mi = [min(q[i] for q in v) for i in range(3)]
    ma = [max(q[i] for q in v) for i in range(3)]
    print("  bounding box:", " ".join(f"{a:.1f}..{b:.1f}" for a, b in zip(mi, ma)))

    textures = {}
    if args.textures:
        mtl = os.path.splitext(args.obj)[0] + ".mtl"
        textures = read_mtl(mtl, args.textures)
        present = sum(1 for _, _, m in faces if m in textures)
        print(f"  textures loaded: {len(textures)}; textured triangles: {present}/{len(faces)}")

    render(v, vc, faces, args.output, args.image_width, args.image_height, args.azimuth, args.elevation,
           vt=vt, textures=textures)
    print(f"  wrote {args.output}")


if __name__ == "__main__":
    main()
