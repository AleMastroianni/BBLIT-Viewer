"""What is really in the 4 bytes at +4 of modes 0x4A/0x4E."""

from __future__ import annotations

import collections
import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import export_obj as geo  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))

examples, counted_values, flag_bits = [], collections.Counter(), collections.Counter()
for r in lvl["resources"]:
    if r["data_kind"] != "model" or r["size"] <= 12:
        continue
    off = r["offset"]
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
                counted_values[struct.unpack_from("<H", sec4, pos + 4)[0]] += 1
                flag_bits[sec4[pos + 2]] += 1
                if len(examples) < 6:
                    measure = geo.MODES[m][0]
                    examples.append((r["id"], m, sec4[pos : pos + measure].hex(" ")))
            pos += geo.MODES[m][0]
            n += 1

print("raw examples (resource id, mode, record bytes):")
for rid, m, hexs in examples:
    print(f"  resource {rid} mode 0x{m:02X}: {hexs}")

print(f"\ndistinct values of the u16 at +4: {len(counted_values)}")
print("  most frequent:", dict(counted_values.most_common(10)))
print(f"  range: {min(counted_values)}..{max(counted_values)}")
print("  flag byte at +2:", {hex(k): v for k, v in flag_bits.items()})

# does the field change within a single model, or is it constant per model?
per_model = {}
for r in lvl["resources"]:
    if r["data_kind"] != "model" or r["size"] <= 12:
        continue
    off = r["offset"]
    _m, _f, nobj = struct.unpack_from("<III", sec4, off)
    basis = off + 12
    s = set()
    for i in range(nobj):
        _v, _nv, _x, _y, pt, n_prim, _z = struct.unpack_from("<7i", sec4, basis + 28 * i)
        pos, n = basis + pt, 0
        while n < n_prim:
            m = sec4[pos + 3]
            if m not in geo.MODES:
                break
            if m in (0x4A, 0x4E):
                s.add(struct.unpack_from("<H", sec4, pos + 4)[0])
            pos += geo.MODES[m][0]
            n += 1
    if s:
        per_model[r["id"]] = s
single_value = sum(1 for s in per_model.values() if len(s) == 1)
print(f"\nmodels with faces without UV: {len(per_model)}, of which with ONE SINGLE value at +4: {single_value}")
for rid, s in list(per_model.items())[:8]:
    print(f"  resource {rid}: {sorted(s)[:8]}{' ...' if len(s) > 8 else ''}")
