"""Which objects come out white, and why.

For each model it computes the colour its flat-colour faces really
produce: 4x4 texture colour times vertex colour, with 128 as neutral.
If the result is white, the question is whether the data says so or my maths.
"""

from __future__ import annotations

import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import export_obj as geo  # noqa: E402
import tim  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
stem = os.path.basename(MAP)
sec3 = open(os.path.join(MAP, f"{stem}_id03.bin"), "rb").read()
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))

tex_color = {}
for t in lvl["textures"]:
    try:
        b, h, rgba = tim.read_tim(sec3, t["offset"])
    except Exception:  # noqa: BLE001
        continue
    if b * h <= 16:
        tex_color[t["id"]] = tuple(rgba[:3])

table_rows = []
for r in lvl["resources"]:
    if r["data_kind"] != "model" or r["size"] <= 12:
        continue
    off = r["offset"]
    _m, _f, nobj = struct.unpack_from("<III", sec4, off)
    basis = off + 12
    faces = 0
    running_sum = [0.0, 0.0, 0.0]
    ids = set()
    for i in range(nobj):
        _v, _nv, _x, _y, pt, n_prim, _z = struct.unpack_from("<7i", sec4, basis + 28 * i)
        pos, n = basis + pt, 0
        while n < n_prim:
            m = sec4[pos + 3]
            if m not in geo.MODES:
                break
            if m in (0x4A, 0x4E):
                tid = struct.unpack_from("<H", sec4, pos + 4)[0]
                ids.add(tid)
                tk = tex_color.get(tid)
                if tk:
                    k = sec4[pos + 8 : pos + 11]
                    for c in range(3):
                        running_sum[c] += min(255.0, tk[c] * (k[c] / 128.0))
                    faces += 1
            pos += geo.MODES[m][0]
            n += 1
    if faces:
        table_rows.append((r["id"], faces, [s / faces for s in running_sum], sorted(ids)))

table_rows.sort(key=lambda r: -r[1])
print(f"{stem}: models with flat-colour faces, by number of faces")
print(f"{'resource':>8} {'faces':>6}  {'resulting colour':>18}   referenced textures")
for rid, n, color_value, ids in table_rows[:16]:
    r, g, b = (int(c) for c in color_value)
    almost_white = "  <-- almost white" if min(r, g, b) > 200 else ""
    print(f"{rid:>8} {n:>6}  {r:>3},{g:>3},{b:>3}         {ids[:5]}{almost_white}")

white_models = [x for x in table_rows if min(x[2]) > 200]
print(f"\nmodels that come out almost white: {len(white_models)}/{len(table_rows)}")
white_textures = {i for i, k in tex_color.items() if min(k) > 240}
print(f"4x4 textures of almost white colour: {sorted(white_textures)}")
