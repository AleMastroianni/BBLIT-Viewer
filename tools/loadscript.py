"""Parser for the load script (section id 1), per Ombelll's FORMATS.md §5.

The bytecode is made of blocks:

    0x2D '-'   opens a block; the next byte is the block TYPE
    0x2E '.'   closes the block
    0x2F '/'   end of the script
    0x2C ','   separator at the top level
    0x00       padding

Each opcode is one byte plus a fixed-size payload, and **the opcode table
depends on the block type**: the same byte means different things in
different blocks. A parser with a flat table goes out of
sync (measured: 4.5%).

The test this parser must pass is the one from the docs: the script
is consumed 100%, with very few unknown bytes per file.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
from collections import Counter

# ---------------------------------------------------------------- tables

# object blocks: 0x07 world object, 0x08 template, 0x0A trigger
OBJECT_OPS = {
    0x0F: 2,   # reference to a resource (model / animation / rig)
    0x10: 12,  # position, 3 x int32
    0x11: 6,   # rotation, 3 x int16
    0x12: 12,  # scale, 3 x int32 (4096 = 1.0)
    0x13: 1,   # object type (object+0x2c); 1 = the player
    0x0B: 4,
    0x0C: 4,
    0x15: 1,
    0x1F: 1,   # area number
    0x1E: 2, 0x38: 2, 0x39: 2, 0x46: 2,
    0x18: 4, 0x19: 4, 0x1A: 4, 0x1D: 4, 0x27: 4, 0x3A: 4,
    0x1B: 6, 0x42: 6,
    0x16: 8,   # two static flag words
    0x1C: 8,
    0x32: 12,  # state (playlist of max 5 steps)
    0x41: 20,
    0x34: 24,  # player step
    0x30: 32,  # step
    0x31: 32,  # second rule table
    0x17: 36,
    0x35: 40,
}

BLOCK_OPS: dict[int, dict[int, int]] = {
    0x00: {0x01: 8, 0x02: 8, 0x04: 8, 0x44: 12, 0x4C: 48, 0x4D: 48},
    0x05: {0x06: 3},
    0x07: OBJECT_OPS,
    0x08: OBJECT_OPS,
    0x09: {0x10: 12, 0x11: 6, 0x16: 8, 0x1C: 8, 0x1F: 1, 0x33: 32},  # zone
    0x0A: OBJECT_OPS,
    0x20: {0x10: 12, 0x11: 6, 0x12: 12, 0x21: 4, 0x24: 8, 0x39: 2, 0x43: 1},  # terrain
    0x22: {0x0D: 12, 0x24: 8, 0x25: 8, 0x26: 4, 0x27: 4, 0x28: 3, 0x3F: 12, 0x40: 8},
    0x29: {0x2A: 8},   # texture: u32 offset, u32 id
    0x36: {0x37: 8},   # collision heightmap
    0x3B: {0x2B: 12, 0x3C: 4, 0x3D: 6, 0x3E: 28},
    0x45: {},          # header marker
    0x47: {0x48: 8},
    0x49: {0x4A: 48},  # game texts, six languages
}

OPEN, CLOSE, END, SEP = 0x2D, 0x2E, 0x2F, 0x2C


class ScriptBlock:
    def __init__(self, category: int, offset: int):
        self.category = category
        self.offset = offset
        self.ops: list[tuple[int, bytes]] = []


def parse(data: bytes) -> tuple[list[ScriptBlock], dict]:
    blocks: list[ScriptBlock] = []
    open_blocks: list[ScriptBlock] = []
    unknown = Counter()
    i, n = 0, len(data)
    finished = False

    while i < n and not finished:
        b = data[i]
        if b == 0x00 or b == SEP:
            i += 1
        elif b == OPEN:
            category = data[i + 1]
            block = ScriptBlock(category, i)
            blocks.append(block)
            open_blocks.append(block)
            i += 2
        elif b == CLOSE:
            if open_blocks:
                open_blocks.pop()
            i += 1
        elif b == END:
            finished = True
            i += 1
        elif open_blocks:
            table = BLOCK_OPS.get(open_blocks[-1].category, {})
            if b in table:
                measure = table[b]
                open_blocks[-1].ops.append((b, data[i + 1 : i + 1 + measure]))
                i += 1 + measure
            else:
                unknown[(open_blocks[-1].category, b)] += 1
                i += 1
        else:
            unknown[(None, b)] += 1
            i += 1

    rest = data[i:]
    stats = {
        "consumed": i,
        "total": n,
        "tail": len(rest),
        "tail_nonzero": sum(1 for c in rest if c),
        "unknown": sum(unknown.values()),
        "unknown_detail": {f"blok 0x{s:02X} op 0x{o:02X}" if s is not None else f"top 0x{o:02X}": c
                            for (s, o), c in unknown.most_common()},
    }
    return blocks, stats


# ---------------------------------------------------------------- extraction

def _s32(p: bytes, o: int) -> int:
    return struct.unpack_from("<i", p, o)[0]


def _u16(p: bytes, o: int) -> int:
    return struct.unpack_from("<H", p, o)[0]


def _s16(p: bytes, o: int) -> int:
    return struct.unpack_from("<h", p, o)[0]


def export_level(blocks: list[ScriptBlock]) -> dict:
    """Collects what the geometry needs: resources, objects, terrain, textures."""
    resources, objects, terrain, textures, zones, collision_blocks = [], [], [], [], [], []

    for block in blocks:
        if block.category == 0x22:
            r = {"role": None, "id": None, "offset": None, "size": None, "data_kind": None}
            for op, p in block.ops:
                if op == 0x27:
                    r["role"], r["id"] = _u16(p, 0), _u16(p, 2)
                elif op == 0x24:  # drawable model, magic 0x41
                    r["offset"], r["size"] = struct.unpack("<II", p)
                    r["data_kind"] = "model"
                elif op == 0x25:  # behaviour / animation stream, magic 0x50
                    r["offset"], r["size"] = struct.unpack("<II", p)
                    r["data_kind"] = "stream"
                elif op == 0x40:  # frames of an animated texture (finding 275)
                    r["offset"], r["size"] = struct.unpack("<II", p)
                    r["data_kind"] = "sprite_frames"
                elif op == 0x3F:  # sequence: pairs (frame, duration in ticks)
                    r["item_count"], r["offset"], r["size"] = struct.unpack("<III", p)
                    r["data_kind"] = "frame_sequence"
            resources.append(r)

        elif block.category in (0x07, 0x08, 0x0A):
            o = {
                "block_type": block.category,
                "resources": [],
                "position": None,
                "rotation": None,
                "scale_factor": None,
                "category": None,
                "area": None,
                "role": None,
                "start": False,
                # states (0x32) and steps (0x30, 0x34 for the player): used to
                # know which animation the game starts (Ombelll's findings 188, 89)
                "states": [],
                "steps": [],
                # second rule table (0x31, Ombelll's FORMATS): used to know
                # which templates the object spawns (effect 0x100/0x40000)
                "rules": [],
                # objects of type 2 and 20: the texture slot they fill on
                # every frame (0x0B) and, for type 20, the cycle (0x42)
                "texture_slot": None,
                "cycle": None,
            }
            for op, p in block.ops:
                if op == 0x0F:
                    o["resources"].append(_u16(p, 0))
                elif op == 0x0B:
                    o["texture_slot"] = struct.unpack_from("<I", p, 0)[0]
                elif op == 0x42:
                    o["cycle"] = [_u16(p, 0), _u16(p, 2), _u16(p, 4)]
                elif op == 0x10:
                    o["position"] = [_s32(p, 0), _s32(p, 4), _s32(p, 8)]
                elif op == 0x11:
                    o["rotation"] = [_s16(p, 0), _s16(p, 2), _s16(p, 4)]
                elif op == 0x12:
                    o["scale_factor"] = [_s32(p, 0), _s32(p, 4), _s32(p, 8)]
                elif op == 0x13:
                    o["category"] = p[0]
                    o["start"] = p[0] == 1
                elif op == 0x1F:
                    o["area"] = p[0]
                elif op == 0x27:
                    o["role"] = _u16(p, 0)
                elif op == 0x32:
                    # state number, then five slots; 0xFFF0 ends the list
                    o["states"].append({"number": _u16(p, 0),
                                            "slots": [_u16(p, 2 + 2 * k) for k in range(5)]})
                elif op == 0x31:
                    o["rules"].append({
                        "key": _u16(p, 0),
                        "condition": [p[12], p[13], p[14]],
                        # code, value (byte), index, and the value as s16:
                        # action 0x26 (rotate) reads it that way (finding 138)
                        "action": [p[15], p[16], _u16(p, 18), _s16(p, 16)],
                        "effect": struct.unpack_from("<I", p, 20)[0],
                        "field24": struct.unpack_from("<i", p, 24)[0],
                        "field28": struct.unpack_from("<i", p, 28)[0],
                    })
                elif op in (0x30, 0x34):
                    # +0 the key looked up by the slots, +2 the animation role
                    o["steps"].append({"key": _u16(p, 0), "role": _u16(p, 2)})
            objects.append(o)

        elif block.category == 0x20:
            t = {"offset": None, "size": None, "translation": [0, 0, 0], "zone": None}
            for op, p in block.ops:
                if op == 0x24:
                    t["offset"], t["size"] = struct.unpack("<II", p)
                elif op == 0x10:
                    t["translation"] = [_s32(p, 0), _s32(p, 4), _s32(p, 8)]
                elif op == 0x21:
                    t["zone"] = struct.unpack("<I", p)[0]
            terrain.append(t)

        elif block.category == 0x29:
            for op, p in block.ops:
                if op == 0x2A:
                    offset, tid = struct.unpack("<II", p)
                    textures.append({"offset": offset, "id": tid})

        elif block.category == 0x09:
            z = {"origin": None, "rotation": None, "number": None, "size": None, "rules": []}
            for op, p in block.ops:
                if op == 0x10:
                    z["origin"] = [_s32(p, 0), _s32(p, 4), _s32(p, 8)]
                elif op == 0x11:
                    z["rotation"] = [_s16(p, 0), _s16(p, 2), _s16(p, 4)]
                elif op == 0x1F:
                    z["number"] = p[0]
                elif op == 0x1C:
                    # X extent, Y limit (negative: the zone rises that far
                    # above its Y), Z extent, plan-view radius (u16)
                    # (finding 103)
                    z["size"] = [_s16(p, 0), _s16(p, 2), _s16(p, 4), _u16(p, 6)]
                elif op == 0x33:
                    # the zone rule: condition at +8, action at +11,
                    # effects at +16 and three parameters at +20/+24/+28 (finding 100;
                    # the L04A2 teleport leads to (7900, -15520, 5000),
                    # SPEEDRUN.md, and that is where they are)
                    z["rules"].append({
                        "condition": [p[8], p[9], p[10]],
                        "action": [p[11], p[12], _u16(p, 14)],
                        "effect": struct.unpack_from("<I", p, 16)[0],
                        "parameters": [_s32(p, 20), _s32(p, 24), _s32(p, 28)],
                    })
            zones.append(z)

        elif block.category == 0x36:
            # collision heightmap (finding 110): (offset, size) of a
            # block in section 4; read by tools/collision.py
            for op, p in block.ops:
                if op == 0x37:
                    offset, measure = struct.unpack("<II", p)
                    collision_blocks.append({"offset": offset, "size": measure})

    return {
        "resources": resources,
        "objects": objects,
        "terrain": terrain,
        "textures": textures,
        "zones": zones,
        "heightmaps": collision_blocks,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="reads section 1 of a .bze")
    p.add_argument("bin", help="section id 1, already decompressed")
    p.add_argument("--json", help="write the extract to this file")
    args = p.parse_args()

    with open(args.bin, "rb") as f:
        data = f.read()
    blocks, stat = parse(data)

    categories = Counter(b.category for b in blocks)
    print(f"{args.bin}: {len(data)} bytes, {len(blocks)} blocks")
    print(f"  consumed {stat['consumed']}/{stat['total']} "
          f"({100 * stat['consumed'] / stat['total']:.2f}%), "
          f"tail {stat['tail']} bytes of which {stat['tail_nonzero']} non-zero, "
          f"unknown bytes {stat['unknown']}")
    if stat["unknown_detail"]:
        print("  unknown:", stat["unknown_detail"])
    print("  blocks:", {f"0x{s:02X}": c for s, c in sorted(categories.items())})

    output = export_level(blocks)
    n_positioned = sum(1 for o in output["objects"] if o["position"])
    print(f"  resources {len(output['resources'])} (models {sum(1 for r in output['resources'] if r['data_kind'] == 'model')}), "
          f"objects {len(output['objects'])} of which {n_positioned} with position, "
          f"terrain {len(output['terrain'])}, textures {len(output['textures'])}, zones {len(output['zones'])}")

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=1)
        print(f"  wrote {args.json}")


if __name__ == "__main__":
    main()
