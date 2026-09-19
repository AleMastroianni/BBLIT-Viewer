"""Do modes 0x4A/0x4E reference the same textures their model already uses?

If the field at +4 were unused or garbage, its values would have no reason
to coincide with the textures used by the faces WITH UV of the same model.
If instead it is a real reference, the set must match much more than it
does for a random model.

The comparison is per model, and the control model is drawn at random from
the same level: that way the null hypothesis has the same id distribution.
"""

from __future__ import annotations

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


def ids_of_model(off):
    """(ids referenced by the faces without UV, ids used by the faces with UV)."""
    missing, present = set(), set()
    _m, _f, nobj = struct.unpack_from("<III", sec4, off)
    basis = off + 12
    for i in range(nobj):
        _v, _nv, _x, _y, pt, n_prim, _z = struct.unpack_from("<7i", sec4, basis + 28 * i)
        pos, n = basis + pt, 0
        while n < n_prim:
            m = sec4[pos + 3]
            if m not in geo.MODES:
                break
            if m in (0x4A, 0x4E):
                missing.add(struct.unpack_from("<H", sec4, pos + 4)[0])
            elif sec4[pos + 4 : pos + 6] != b"\xff\xff":
                present.add(struct.unpack_from("<H", sec4, pos + 6)[0])
            pos += geo.MODES[m][0]
            n += 1
    return missing, present


models = [r for r in lvl["resources"] if r["data_kind"] == "model" and r["size"] > 12]
pairs = []
for r in models:
    z, m = ids_of_model(r["offset"])
    if z and m:
        pairs.append((r["id"], z, m))

real_share = sum(len(z & m) / len(z) for _id, z, m in pairs) / len(pairs)
null_rate = 0.0
for _ in range(200):
    running_sum = 0.0
    for _id, z, _m in pairs:
        other_set = random.choice(pairs)[2]
        running_sum += len(z & other_set) / len(z)
    null_rate += running_sum / len(pairs)
null_rate /= 200

print(f"{stem}: {len(pairs)} models that have both faces with UV and faces without")
print(f"  share of 'without UV' ids the model also uses on the faces with UV: {100 * real_share:.1f}%")
print(f"  same share against a random model of the same level:               {100 * null_rate:.1f}%")

contained = sum(1 for _id, z, m in pairs if z <= m)
print(f"  models where the without-UV set is entirely contained in the other: {contained}/{len(pairs)}")
