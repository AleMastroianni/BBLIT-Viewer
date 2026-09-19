"""The texture table: numbered slots, filled in two ways.

The game registers each TIM in a numbered slot (`FUN_004229a0`, table at
0x52fd60, opcode 0x2A). But not all the slots referenced by the faces come from
there: objects of type 2 and 20 with opcode `0x0B` fill a slot on every
frame with an animated texture (finding 275). These are the eyes of Bugs and of
Merlin, the sun's halo, the water, the ripples. Across the whole disc: 520
slots of this kind in 79 files, none registered by its own file, and they cover
518 of the 545 ids referenced but not registered.

Finding 260 had explained those same slots with a CUMULATIVE table
across files (`title -> L03ACOM -> L03A`): the evidence was weak, because almost
every file registers the low slots and those around 291, and the on-screen
result was wrong (a barrel strap in place of the eyes). After finding
275 no slot is left for the chain to explain in L03A, so the companion files
are no longer added by default: they can be requested with `extra`.
"""

from __future__ import annotations

import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
import bze  # noqa: E402
import loadscript  # noqa: E402


def sections(bze_path: str, cache: str, ids=(1, 3, 4)) -> dict[int, bytes]:
    """Decompresses the requested sections, with an on-disk cache."""
    stem = os.path.splitext(os.path.basename(bze_path))[0]
    cache_dir = os.path.join(cache, stem)
    os.makedirs(cache_dir, exist_ok=True)
    output = {}
    entries, data = bze.open_bze(bze_path)
    for s in entries:
        if s.id not in ids:
            continue
        file_path = os.path.join(cache_dir, f"{stem}_id{s.id:02d}.bin")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                output[s.id] = f.read()
        else:
            output[s.id] = bze.section_bytes(data, s)
            with open(file_path, "wb") as f:
                f.write(output[s.id])
    return output


def find_level_file(data_dir: str, name: str) -> str | None:
    """Finds a .bze by name, case-insensitively."""
    target = name.lower() + ".bze"
    for f in os.listdir(data_dir):
        if f.lower() == target:
            return os.path.join(data_dir, f)
    return None


def companions(data_dir: str, level: str) -> list[str]:
    """The files that register textures before the level, in load order.

    `title` is opened at startup; the area's common file (for example
    `L03ACOM` for `L03A` and `L03A2`) carries the shared objects.
    """
    names = ["title"]
    stem = level.rstrip("0123456789")
    for candidate_name in (stem + "COM", level + "COM"):
        if candidate_name.lower() != level.lower() and find_level_file(data_dir, candidate_name):
            names.append(candidate_name)
            break
    return names


def animated_slots(lvl: dict, sec4: bytes) -> dict[int, dict]:
    """The slots the level fills on every frame (finding 275).

    An object of type 2 or 20 with opcode `0x0B` is not drawn: it writes into the
    slot named by `0x0B` a frame taken from one of its `0x40` resources, a
    model (magic 0x41) made only of `0x64` primitives, one per frame,
    with the texture id at +10. Frame k is the k-th record.

    What picks the frame:
    - type 2: the `0x3F` resource, byte pairs (frame, duration in ticks);
    - type 20: no sequence, `0x42` = (first, last, duration), a loop.

    These are the eyes of Bugs and of Merlin, the sun's halo, the flowing water,
    the ripples: no file registers them, because they are not static textures.
    """
    res = {r["id"]: r for r in lvl["resources"]}
    output = {}
    for o in lvl["objects"]:
        slot = o.get("texture_slot")
        if slot is None:
            continue
        spr = sprite(o, res, sec4)
        if spr is not None:
            output[slot] = {"frames": spr["frames"], "sequence": spr["sequence"]}
    return output


def sprite(o: dict, res: dict, sec4: bytes) -> dict | None:
    """Frames, sequence and size of an object made of sprites.

    The frames are in a `0x40` resource: a 0x41 model of 16-byte `0x64`
    primitives, texture id at +10, width and height at +12/+14
    (in world units, 128 = 1 m), blending as for the faces. The sequence is in a `0x3F` resource, as
    pairs (frame, duration in ticks); without it, the `0x42` loop (first,
    last, duration). Applies to the animated slots (275) and to the world
    sprites, like the torch flame (279).
    """
    frames, sizes, blends, sequence = [], [], [], None
    for rid in o["resources"]:
        r = res.get(rid)
        if r is None:
            continue
        if r["data_kind"] == "sprite_frames":
            off = r["offset"]
            nobj = struct.unpack_from("<I", sec4, off + 8)[0]
            for i in range(nobj):
                _vt, _nv, _nt, _nn, pt, n_prim, _s = struct.unpack_from("<7i", sec4, off + 12 + 28 * i)
                for k in range(n_prim):
                    rec = off + 12 + pt + 16 * k
                    if sec4[rec + 3] == 0x64:
                        frames.append(struct.unpack_from("<H", sec4, rec + 10)[0])
                        sizes.append(struct.unpack_from("<hh", sec4, rec + 12))
                        # as for the faces: bit 3 of the flag at +2 = semi-transparent,
                        # the blending in bits 5-6 of the word (here at +6)
                        if not blends:
                            blends.append((struct.unpack_from("<H", sec4, rec + 6)[0] >> 5) & 3
                                          if sec4[rec + 2] & 0x08 else None)
        elif r["data_kind"] == "frame_sequence":
            d = sec4[r["offset"]: r["offset"] + 2 * r["item_count"]]
            sequence = [(d[2 * i], d[2 * i + 1]) for i in range(r["item_count"])]
    if not frames:
        return None
    if sequence is None:
        first, last, duration = o.get("cycle") or (0, len(frames) - 1, 1)
        sequence = [(k, max(duration, 1)) for k in range(first, min(last, len(frames) - 1) + 1)]
    sequence = [(f, d) for f, d in sequence if f < len(frames)] or [(0, 1)]
    return {"frames": frames, "sequence": sequence, "size": sizes[0], "blend": blends[0]}


class TextureTable:
    """texture id -> (asset block, offset), with the file chain."""

    def __init__(self):
        self.slots: dict[int, tuple[bytes, int]] = {}
        self.origins: dict[int, str] = {}
        # slots filled at runtime: slot -> {"frames": [(block, offset)], "sequence": [(f, tick)]}
        self.animated_slots: dict[int, dict] = {}

    def add_file(self, name: str, sec1: bytes, sec3: bytes, sec4: bytes | None = None) -> int:
        blocks, _stat = loadscript.parse(sec1)
        lvl = loadscript.export_level(blocks)
        n = 0
        for t in lvl["textures"]:
            self.slots[t["id"]] = (sec3, t["offset"])
            self.origins[t["id"]] = name
            self.animated_slots.pop(t["id"], None)
            n += 1
        if sec4 is not None:
            # after the registrations: the frames are ids from the same file
            for slot, a in animated_slots(lvl, sec4).items():
                frames = [self.slots[t] for t in a["frames"] if t in self.slots]
                if len(frames) != len(a["frames"]):
                    continue
                self.animated_slots[slot] = {"frames": frames, "sequence": a["sequence"]}
                # when static, the first frame of the sequence is shown
                self.slots[slot] = frames[a["sequence"][0][0]]
                self.origins[slot] = name + " (animated)"
        return n

    def bitmap(self, slot: int, tick: int):
        """The frame of an animated slot at the given tick, or None."""
        a = self.animated_slots.get(slot)
        if a is None:
            return None
        total = sum(d for _f, d in a["sequence"])
        t = tick % total
        for f, d in a["sequence"]:
            if t < d:
                return a["frames"][f]
            t -= d
        return a["frames"][a["sequence"][-1][0]]

    def __contains__(self, tid):
        return tid in self.slots

    def get(self, tid):
        return self.slots.get(tid)


def construct(data_dir: str, level: str, cache: str, extra: list[str] | None = None) -> TextureTable:
    table = TextureTable()
    names = list(extra) if extra is not None else []
    for name in names + [level]:
        file_path = find_level_file(data_dir, name)
        if not file_path:
            continue
        sec = sections(file_path, cache, ids=(1, 3, 4))
        if 1 in sec and 3 in sec:
            table.add_file(name, sec[1], sec[3], sec.get(4))
    return table


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else paths.DATA_BZE
    level = sys.argv[2] if len(sys.argv) > 2 else "L03A"
    t = construct(data_dir, level, "extracted")
    slots_per_file: dict[str, int] = {}
    for name in t.origins.values():
        slots_per_file[name] = slots_per_file.get(name, 0) + 1
    print(f"{level}: {len(t.slots)} texture slots in use")
    for name, n in slots_per_file.items():
        print(f"  {n:>4} come from {name}")
