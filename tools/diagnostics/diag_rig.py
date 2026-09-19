"""Which objects have multiple parts, and do they have a rig to assemble them?

A multi-part model has the vertices of each part in local space: without a
pose they all end up at the origin, i.e. the object comes out disassembled.
"""

from __future__ import annotations

import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rig  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))

res = {r["id"]: r for r in lvl["resources"]}
categories = {}
for r in lvl["resources"]:
    if r["data_kind"] == "stream" and r["offset"] is not None:
        categories[r["id"]] = rig.is_stream(sec4, r["offset"])

multi_part_count = single_part_count = 0
n_with_rig = n_without_rig = 0
examples = []
for o in lvl["objects"]:
    if not o["position"] or o["block_type"] == 0x08:
        continue
    mid = next((i for i in o["resources"] if i in res and res[i]["data_kind"] == "model"
                and res[i]["size"] > 12), None)
    if mid is None:
        continue
    nobj = struct.unpack_from("<I", sec4, res[mid]["offset"] + 8)[0]
    if nobj <= 1:
        single_part_count += 1
        continue
    multi_part_count += 1
    rigs = [i for i in o["resources"] if categories.get(i) == 1]
    poses = [i for i in o["resources"] if categories.get(i) == 2]
    if rigs:
        n_with_rig += 1
    else:
        n_without_rig += 1
    if len(examples) < 12:
        examples.append((o.get("role"), mid, nobj, rigs[:2], poses[:3],
                            [res[i]["role"] for i in o["resources"] if i in res][:6]))

print(f"{stem}: placed objects with a model")
print(f"  with a single part:   {single_part_count}")
print(f"  with multiple parts:  {multi_part_count}  (of which with rig: {n_with_rig}, without: {n_without_rig})")
print("\nexamples (object role, model, parts, rig, poses, resource roles):")
for role, mid, nobj, rigs, poses, roles in examples:
    print(f"  role {role}: model {mid} with {nobj} parts, rig {rigs}, poses {poses}, roles {roles}")
