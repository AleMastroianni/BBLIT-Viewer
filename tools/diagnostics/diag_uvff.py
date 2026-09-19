"""`FF FF` in the first UV: padding or the (255,255) corner?

My reader treats a face as untextured when the first two UV bytes are
FF FF. But FF FF is also the coordinate of the bottom-right corner, so the
criterion may throw away genuinely textured faces.

A discriminating test: if those faces really were untextured, the id field
at +6 would be garbage. If instead they are textured, that id must be a
registered slot, and the OTHER UVs of the same face must not all be FF.
"""

from __future__ import annotations

import collections
import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import paths  # noqa: E402
import export_obj as geo  # noqa: E402
import textures as texmod  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
DATA = sys.argv[2] if len(sys.argv) > 2 else paths.DATA_BZE
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))
table = texmod.construct(DATA, stem, os.path.dirname(MAP))

ff, normal_uvs = [], []


def scan(start, item_count):
    pos, n = start, 0
    while n < item_count:
        m = sec4[pos + 3]
        if m not in geo.MODES:
            break
        if m in geo.UV_MODES:
            corners = geo.MODES[m][1]
            uv = [(sec4[pos + 4], sec4[pos + 5]), (sec4[pos + 8], sec4[pos + 9]),
                  (sec4[pos + 12], sec4[pos + 13]), (sec4[pos + 14], sec4[pos + 15])][:corners]
            tid = struct.unpack_from("<H", sec4, pos + 6)[0]
            (ff if uv[0] == (255, 255) else normal_uvs).append((tid, uv, m))
        pos += geo.MODES[m][0]
        n += 1


for t in lvl["terrain"]:
    basis = t["offset"] + 12
    _vt, _nv, _a, _b, pt, n_prim, _c = struct.unpack_from("<7i", sec4, basis)
    pos, running_sum = basis + pt, 0
    while running_sum < n_prim:
        item_count, mode, l4, nd = struct.unpack_from("<HHHH", sec4, pos)
        if mode != 0x1000:
            p = pos + 8 + max(nd, 1) * 8
            cnt, tag = struct.unpack_from("<HH", sec4, p)
            if tag == 0x4400:
                scan(p + 4 + 12 * cnt, max(item_count - 2, 0))
        running_sum += item_count
        pos += l4 * 4

for r in lvl["resources"]:
    if r["data_kind"] != "model" or r["size"] <= 12:
        continue
    off = r["offset"]
    _m, _f, nobj = struct.unpack_from("<III", sec4, off)
    b2 = off + 12
    for i in range(nobj):
        _v, _nv, _x, _y, p_, n_p, _z = struct.unpack_from("<7i", sec4, b2 + 28 * i)
        scan(b2 + p_, n_p)

print(f"{stem}: faces in a mode with UV: {len(ff) + len(normal_uvs)}")
print(f"  with first UV = FF FF (which I discard): {len(ff)}")
print(f"  with a normal first UV:                  {len(normal_uvs)}")

if ff:
    n_valid = sum(1 for tid, _uv, _m in ff if tid in table)
    print(f"  of the discarded ones, id registered in the table: {n_valid}/{len(ff)} "
          f"({100 * n_valid / len(ff):.1f}%)")
    all_ff = sum(1 for _t, uv, _m in ff if all(p == (255, 255) for p in uv))
    print(f"  with ALL UVs at FF FF (real padding):              {all_ff}/{len(ff)}")
    print("  UV examples of the discarded ones:", [uv for _t, uv, _m in ff[:4]])
n_valid_control = sum(1 for tid, _uv, _m in normal_uvs if tid in table)
print(f"  control: on the non-discarded ones the id is valid: {n_valid_control}/{len(normal_uvs)}")
print("  modes of the discarded ones:", dict(collections.Counter(hex(m) for _t, _uv, m in ff)))
