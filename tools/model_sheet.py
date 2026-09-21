"""Contact sheet of a level's models, one per cell.

It lets you look the props in the face without hunting for them in the level: if an
object is assembled wrong, it shows up here immediately.

    python tools/model_sheet.py extracted/L03A -o extracted/L03A/models.png
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bblit"))
from support import paths  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import montage  # noqa: E402
from game import rig as rigmod  # noqa: E402
from game import textures as texmod  # noqa: E402
from game import tim  # noqa: E402
from render_obj import _png  # noqa: E402


def draw_cell(vertices, faces, tex, cell_size, azimuth=35.0, elevation=25.0):
    """Draws a model into a square cell, returns RGB."""
    buf = bytearray(cell_size * cell_size * 3)
    for i in range(0, len(buf), 3):
        buf[i : i + 3] = b"\x14\x16\x1c"
    if not vertices or not faces:
        return bytes(buf)
    zbuf = [1e18] * (cell_size * cell_size)

    mi = [min(p[k] for p in vertices) for k in range(3)]
    ma = [max(p[k] for p in vertices) for k in range(3)]
    mid = [(a + b) / 2 for a, b in zip(mi, ma)]
    a, e = math.radians(azimuth), math.radians(elevation)
    ca, sa, ce, se = math.cos(a), math.sin(a), math.cos(e), math.sin(e)

    def proj(p):
        d = [p[k] - mid[k] for k in range(3)]
        x = d[0] * ca - d[2] * sa
        y = -(d[1]) * ce - (d[0] * sa + d[2] * ca) * se
        z = (d[0] * sa + d[2] * ca) * ce - d[1] * se
        return x, y, z

    points = [proj(p) for p in vertices]
    span = max(max(abs(p[0]) for p in points), max(abs(p[1]) for p in points), 1e-6)
    scale_factor = 0.42 * cell_size / span
    screen_pts = [(p[0] * scale_factor + cell_size / 2, p[1] * scale_factor + cell_size / 2, p[2]) for p in points]

    for vl in faces:
        for tri in geo.triangles(len(vl.corners)):
            idx = [vl.corners[i] for i in tri]
            p0, p1, p2 = (screen_pts[i] for i in idx)
            double_area = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
            if abs(double_area) < 1e-9:
                continue
            color_value = [sum(vl.colors[i][k] for i in tri) / 3 / 255 for k in range(3)]
            bitmap = tex.get(vl.tex_id) if vl.tex_id is not None else None
            if bitmap:
                tb, th, rgba = bitmap
                s = ((th // 2) * tb + tb // 2) * 4
                color_value = [min(1.0, color_value[k] * rgba[s + k] / 255 * 2) for k in range(3)]
            xmin = max(int(min(p0[0], p1[0], p2[0])), 0)
            xmax = min(int(max(p0[0], p1[0], p2[0])) + 1, cell_size - 1)
            ymin = max(int(min(p0[1], p1[1], p2[1])), 0)
            ymax = min(int(max(p0[1], p1[1], p2[1])) + 1, cell_size - 1)
            for y in range(ymin, ymax + 1):
                for x in range(xmin, xmax + 1):
                    px, py = x + 0.5, y + 0.5
                    b0 = ((p1[0] - px) * (p2[1] - py) - (p2[0] - px) * (p1[1] - py)) / double_area
                    b1 = ((p2[0] - px) * (p0[1] - py) - (p0[0] - px) * (p2[1] - py)) / double_area
                    b2 = 1 - b0 - b1
                    if b0 < 0 or b1 < 0 or b2 < 0:
                        continue
                    z = b0 * p0[2] + b1 * p1[2] + b2 * p2[2]
                    o = y * cell_size + x
                    if z >= zbuf[o]:
                        continue
                    zbuf[o] = z
                    buf[o * 3 : o * 3 + 3] = bytes(min(255, int(255 * k)) for k in color_value)
    return bytes(buf)


def main() -> None:
    p = argparse.ArgumentParser(description="contact sheet of a level's models")
    p.add_argument("map")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--cell-size", type=int, default=150)
    p.add_argument("--columns", type=int, default=8)
    p.add_argument("--assemble", action="store_true", help="position the parts with the rig")
    p.add_argument("--model", type=int, help="a single model, filling the cell")
    p.add_argument("--azimuth", type=float, default=35.0)
    p.add_argument("--elevation", type=float, default=25.0)
    p.add_argument("--data", default=paths.DATA_BZE,
                   help=".bze folder, for the texture chain")
    args = p.parse_args()

    stem = os.path.basename(args.map)
    sec3 = open(os.path.join(args.map, f"{stem}_id03.bin"), "rb").read()
    sec4 = open(os.path.join(args.map, f"{stem}_id04.bin"), "rb").read()
    lvl = json.load(open(os.path.join(args.map, f"{stem.lower()}.json"), encoding="utf-8"))
    res = {r["id"]: r for r in lvl["resources"]}

    # the texture table is cumulative across files (see textures.py)
    tex = {}
    try:
        table = texmod.construct(args.data, stem, os.path.dirname(args.map))
        sources = {tid: source for tid, source in table.slots.items()}
    except Exception:  # noqa: BLE001
        sources = {t["id"]: (sec3, t["offset"]) for t in lvl["textures"]}
    for tid, (block, offset) in sources.items():
        try:
            tex[tid] = tim.read_tim(block, offset)
        except Exception:  # noqa: BLE001
            pass

    # models actually used by a placed object, with their rig
    used_models = {}
    for o in lvl["objects"]:
        if not o["position"] or o["block_type"] == 0x08:
            continue
        mid = next((i for i in o["resources"] if i in res and res[i]["data_kind"] == "model"
                    and res[i]["size"] > 12), None)
        if mid is None or mid in used_models:
            continue
        used_models[mid] = o["resources"]

    ids = [args.model] if args.model else sorted(used_models)
    if args.model and args.model not in used_models:
        used_models[args.model] = next((o["resources"] for o in lvl["objects"]
                                     if args.model in o["resources"]), [args.model])
    n_cols = args.columns
    row_no = (len(ids) + n_cols - 1) // n_cols
    cell_size = args.cell_size
    sheet = bytearray(n_cols * cell_size * row_no * cell_size * 3)

    print(f"{len(ids)} models, grid {n_cols} x {row_no} (row-major order):")
    for n, mid in enumerate(ids):
        trans = montage.transforms(sec4, used_models[mid], res) if args.assemble else None
        vertices, faces, _ = geo.read_model(sec4, res[mid]["offset"], trans)
        parts_info = f", {len(trans)} parts assembled" if trans else ""
        nobj = struct.unpack_from("<I", sec4, res[mid]["offset"] + 8)[0]
        print(f"  cell {n:>3} (row {n // n_cols + 1}, column {n % n_cols + 1}): "
              f"model {mid}, {nobj} parts, {len(faces)} faces{parts_info}")
        rgb = draw_cell(vertices, faces, tex, cell_size, args.azimuth, args.elevation)
        cx, cy = (n % n_cols) * cell_size, (n // n_cols) * cell_size
        for y in range(cell_size):
            o = ((cy + y) * n_cols * cell_size + cx) * 3
            sheet[o : o + cell_size * 3] = rgb[y * cell_size * 3 : (y + 1) * cell_size * 3]

    _png(args.output, n_cols * cell_size, row_no * cell_size, bytes(sheet))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
