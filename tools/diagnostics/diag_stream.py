"""What an object's 0x50 streams really contain."""

from __future__ import annotations

import collections
import json
import os
import struct
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rig as rigmod  # noqa: E402

MAP = sys.argv[1] if len(sys.argv) > 1 else "extracted/L03A"
TARGET_ID = int(sys.argv[2]) if len(sys.argv) > 2 else None
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))

streams = [r for r in lvl["resources"]
           if r["data_kind"] == "stream" and r["offset"] is not None]
categories = collections.Counter(rigmod.is_stream(sec4, r["offset"]) for r in streams)
print(f"{stem}: {len(streams)} streams, types: {dict(categories)}")

chosen = [r for r in streams if TARGET_ID is None or r["id"] == TARGET_ID][:4]
for r in chosen:
    category = rigmod.is_stream(sec4, r["offset"])
    header = struct.unpack_from("<8H", sec4, r["offset"])
    print(f"\nresource {r['id']} (role {r['role']}), type {category}, {r['size']} bytes")
    print("  header u16:", list(header))
    blocks = rigmod.read_blocks(sec4, r["offset"], r["size"], max_blocks=3)
    print(f"  blocks read: {len(blocks)}")
    for anim_time, records in blocks[:3]:
        type_counts = collections.Counter(s for _d, s, _v, _l in records)
        print(f"    t={anim_time}: {len(records)} records, types {dict(type_counts)}")
        for part_id, s, flag_bits, payload in records[:6]:
            print(f"      part {part_id:>3} type {s:>2} flag {flag_bits:>2} "
                  f"payload {payload[:12].hex(' ')}")
