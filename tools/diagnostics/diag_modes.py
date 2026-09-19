"""Diagnostic: do modes 0x4A/0x4E really carry a texture id at +4?

The docs say "texture index at +4, no UV in the record", and that is why
my exporter draws them in flat colour. But they are almost half of the
level's faces, and the user sees many white or grey quads.

A test that can fail: if that field is a texture id, it must almost always
be an id REGISTERED by the level, much more often than a random number in
the same range. And if the faces are textured, their colours must almost
all be the neutral grey 128, which is how the PSX says "take the texture
as it is".
"""

from __future__ import annotations

import collections
import json
import os
import random
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import export_obj as geo  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))
known_ids = {t["id"] for t in lvl["textures"]}

rec = []


def scan(start, item_count):
    pos, n = start, 0
    while n < item_count:
        m = sec4[pos + 3]
        if m not in geo.MODES:
            break
        if m in (0x4A, 0x4E):
            k = [sec4[pos + 8 + 4 * i : pos + 11 + 4 * i] for i in range(3 if m == 0x4A else 4)]
        elif m in (0x3C, 0x40):
            k = [sec4[pos + 16 + 4 * i : pos + 19 + 4 * i] for i in range(geo.MODES[m][1])]
        else:
            k = [sec4[pos + 16 : pos + 19]]
        rec.append((m, struct.unpack_from("<H", sec4, pos + 4)[0],
                    struct.unpack_from("<H", sec4, pos + 6)[0], k))
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

zu = [r for r in rec if r[0] in (0x4A, 0x4E)]
mu = [r for r in rec if r[0] in (0x3C, 0x40)]
print(f"{stem}: 0x4A/0x4E {len(zu)} records, 0x3C/0x40 {len(mu)} records")

ok = sum(1 for m, a, b, k in zu if a in known_ids)
lo, hi = min(known_ids), max(known_ids)
null_rate = sum(1 for _ in range(20000) if random.randint(lo, hi) in known_ids) / 20000
print(f"  u16 at +4 is a registered texture id: {ok}/{len(zu)} = {100 * ok / len(zu):.1f}%"
      f"   (random in {lo}..{hi}: {100 * null_rate:.1f}%)")


def is_neutral(k):
    return all(abs(c - 128) <= 10 for kl in k for c in kl)


print(f"  all colours neutral (~128): without UV {100 * sum(1 for r in zu if is_neutral(r[3])) / len(zu):.0f}%"
      f"   with UV {100 * sum(1 for r in mu if is_neutral(r[3])) / len(mu):.0f}%")
print("  u16 at +6 without UV:", dict(collections.Counter(b for m, a, b, k in zu).most_common(5)))
print("  u16 at +6 with UV (palette):", dict(collections.Counter(b for m, a, b, k in mu).most_common(5)))
