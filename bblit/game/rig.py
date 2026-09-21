"""Rig and rest pose: how the parts of a model are assembled.

The vertices of a TMD part are in LOCAL space, around their own
origin. What puts each part in its place are two resources with magic 0x50
(Ombelll's MODELFORMAT.md §5z):

* the **rig** (type 1) builds the tree: it creates the parts, links them to
  the parts of the TMD model and says which part is the parent of which;
* the **animation** (type 2) is a sequence of poses; pose 0 is the rest
  pose, and holds the transform of every part.

Stacking the parts on the origin without a pose does exactly what it looks like:
the object comes out disassembled.

Stream format, read by `FUN_0044e400`. The pointer starts at
`data + 8`, so what looked like header fields are actually
the header of the first block:

    u32 A   low16 = number of words, high16 = NUMBER OF RECORDS in the block
    u32 B   time of the pose, in frames
    then    `record` records

Each record starts with a u32:

    bit 0-15   part id
    bit 16-19  type
    bit 20-23  flags
    bit 24-31  RECORD LENGTH in words, header included

The last field makes the format self-describing: even an unknown type
can be skipped without losing sync.
"""

from __future__ import annotations

import functools
import math
import struct

# record types (bit 16-19)
T_STOP, T_TRS, T_MESH, T_PARENT, T_FIELD24, T_CREATE, T_BOX, T_CHAIN = 0, 1, 2, 3, 6, 8, 9, 0xA


class Part:
    """A part of the rig."""

    __slots__ = ("id", "mesh", "parent_ref", "rotation", "scale_factor", "position", "hidden")

    def __init__(self, part_id):
        self.id = part_id
        self.mesh = None       # 1-based index into the TMD object table
        self.parent_ref = None      # parent id, 0 or 0xFFFF = the object itself
        self.rotation = (0, 0, 0)
        self.scale_factor = (4096, 4096, 4096)
        self.position = (0, 0, 0)
        self.hidden = False  # removed by a type 8 record with flag 0xB (finding 280)


def is_stream(data: bytes, offset: int) -> int | None:
    """Returns the type of the 0x50 stream, or None."""
    if offset + 4 > len(data):
        return None
    magic, category = struct.unpack_from("<HH", data, offset)
    return category if magic == 0x0050 else None


def read_blocks(data: bytes, offset: int, measure: int, max_blocks: int = 1):
    """Reads the first `max_blocks` pose blocks and returns the records."""
    pos = offset + 8           # the stream pointer starts at data + 8
    end_pos = offset + measure
    blocks = []
    while pos + 8 <= end_pos and len(blocks) < max_blocks:
        a, anim_time = struct.unpack_from("<II", data, pos)
        item_count = a >> 16
        pos += 8
        records = []
        for _ in range(item_count):
            if pos + 4 > end_pos:
                break
            header = struct.unpack_from("<I", data, pos)[0]
            part_id = header & 0xFFFF
            category = (header >> 16) & 0xF
            flag_bits = (header >> 20) & 0xF
            width_words = (header >> 24) & 0xFF
            payload = data[pos + 4 : pos + max(width_words, 1) * 4]
            records.append((part_id, category, flag_bits, payload))
            # a record with length 0 is a stopper: it counts as one word
            pos += max(width_words, 1) * 4
        blocks.append((anim_time, records))
    return blocks


def _trs(flag_bits: int, payload: bytes):
    """Reads rotation, scale and position according to flags 2, 4 and 8."""
    rot = scale_factor = pos = None
    o = 0
    if flag_bits & 2:            # three s16 angles, 4096 = one full turn
        rot = struct.unpack_from("<hhh", payload, o)
        o += 8
    if flag_bits & 4:            # three s16 scale values, 4096 = 1.0
        scale_factor = struct.unpack_from("<hhh", payload, o)
        o += 8
    if flag_bits & 8:            # three s32 position values
        pos = struct.unpack_from("<iii", payload, o)
        o += 12
    return rot, scale_factor, pos


def construct(data: bytes, rig_offset: int, rig_size: int,
         pose_offset: int | None = None, pose_size: int = 0,
         max_pose_blocks: int = 8) -> dict[int, Part]:
    """Builds the parts from the rig and places them with the rest pose.

    The first block of an animation does not always hold the pose: in several
    streams it holds only the "create part" records, and the transforms arrive
    in the following blocks. So several blocks are read, stopping as soon as
    every part carrying a mesh has received its transform.
    """
    parts: dict[int, Part] = {}
    transformed: set[int] = set()

    def process(offset, measure, *, is_rig):
        blocks = read_blocks(data, offset, measure,
                               max_blocks=64 if is_rig else max_pose_blocks)
        for _anim_time, records in blocks:
            if not is_rig and _complete(parts, transformed):
                break      # the pose is complete: the following blocks are motion
            _apply_records(parts, transformed, records)

    process(rig_offset, rig_size, is_rig=True)
    if pose_offset is not None:
        process(pose_offset, pose_size, is_rig=False)
    return parts


def _complete(parts, transformed) -> bool:
    # every part with a mesh has its transform, or has been removed
    # (finding 280); but a block that removes everything is not a pose: many
    # streams open that way (pirate, Merlin) and the pose arrives in the next block
    with_mesh = [d for d in parts.values() if d.mesh]
    return (bool(transformed) and all(d.id in transformed for d in with_mesh)
            and any(not d.hidden for d in with_mesh))


def _apply_records(parts: dict[int, Part], transformed: set[int], records) -> None:
    """Applies the records of a block: creates parts, links meshes and parents, moves."""
    for part_id, category, flag_bits, payload in records:
        if category == T_CREATE:
            d = parts.setdefault(part_id, Part(part_id))
            # In animations type 8 always has flag 0xB, and removes the
            # part: the first TRS that puts it back is complete in 638 cases out of 638
            # (finding 280). For the pose it counts as settled.
            if flag_bits == 0xB:
                d.hidden = True
                transformed.add(part_id)
        elif category == T_MESH and len(payload) >= 4:
            parts.setdefault(part_id, Part(part_id)).mesh = struct.unpack_from("<I", payload, 0)[0]
        elif category == T_PARENT and len(payload) >= 4:
            parts.setdefault(part_id, Part(part_id)).parent_ref = struct.unpack_from("<I", payload, 0)[0]
        elif category == T_TRS:
            d = parts.setdefault(part_id, Part(part_id))
            transformed.add(part_id)
            d.hidden = False
            rot, scale_factor, pos = _trs(flag_bits, payload)
            if rot is not None:
                d.rotation = rot
            if scale_factor is not None:
                d.scale_factor = scale_factor
            if pos is not None:
                d.position = pos


def animation(data: bytes, rig_offset: int, rig_size: int, pose_offset: int, pose_size: int,
             max_blocks: int = 600) -> list[dict[int, tuple]]:
    """The transforms of every frame of an animation (finding 278).

    A stream block is one tick (the times are 0, 1, 2, ...) and carries
    only the records of the parts that change: the state accumulates block by
    block, without interpolation. The first frame is the first block in
    which every part with a mesh has received its transform, i.e. the
    pose that `construct` uses when static.
    """
    parts: dict[int, Part] = {}
    transformed: set[int] = set()
    for _anim_time, records in read_blocks(data, rig_offset, rig_size, 64):
        _apply_records(parts, transformed, records)
    frames = []
    for _anim_time, records in read_blocks(data, pose_offset, pose_size, max_blocks):
        _apply_records(parts, transformed, records)
        if frames or _complete(parts, transformed):
            frames.append(transforms(parts))
    # The last block is an end-of-loop placeholder: it changes no part
    # (135 animations out of 135 in L03A, L03A2, L03ACOM, L01a, MERLIN). The PC
    # does not show it; keeping it froze the carrot for one tick every loop.
    if len(frames) > 2 and frames[-1] == frames[-2]:
        frames.pop()
    return frames


def animation_per_part(data: bytes, rig_offset: int, rig_size: int, pose_offset: int,
                       pose_size: int, max_blocks: int = 600) -> list[dict[int, tuple]]:
    """Like `animation`, but with `per_part`: also the parts that draw nothing.

    That is what an attachment marker is (finding 279): a part with no mesh
    that a clone hangs from, so to follow it frame by frame -- the crab's claw
    of finding 317 -- the transforms of the parts without a mesh are needed
    too. Same frames as `animation`, one for one.
    """
    parts: dict[int, Part] = {}
    transformed: set[int] = set()
    for _anim_time, records in read_blocks(data, rig_offset, rig_size, 64):
        _apply_records(parts, transformed, records)
    frames, plain = [], []
    for _anim_time, records in read_blocks(data, pose_offset, pose_size, max_blocks):
        _apply_records(parts, transformed, records)
        if frames or _complete(parts, transformed):
            frames.append(per_part(parts))
            plain.append(transforms(parts))
    # the same end-of-loop placeholder `animation` drops, dropped the same way
    if len(plain) > 2 and plain[-1] == plain[-2]:
        frames.pop()
    return frames


def transforms(parts: dict[int, Part]) -> dict[int, tuple]:
    """Maps TMD part index (0-based) -> (matrix, translation).

    Transforms are CHAINED through the parents: the position of a part
    is relative to its parent. Measured on Bugs in L03A: without chaining
    the figure is 150 units tall and lies in a heap, with chaining 285, which
    is a character standing up.
    """
    cache: dict[int, tuple] = {}

    def world_transform(part: Part, depth=0):
        if part.id in cache:
            return cache[part.id]
        m, t = matrix(part)
        parent_ref = parts.get(part.parent_ref) if part.parent_ref not in (None, 0, 0xFFFF) else None
        if parent_ref is not None and parent_ref is not part and depth < 32:
            mo, to = world_transform(parent_ref, depth + 1)
            m = tuple(tuple(sum(mo[i][k] * m[k][j] for k in range(3)) for j in range(3))
                      for i in range(3))
            t = (mo[0][0] * t[0] + mo[0][1] * t[1] + mo[0][2] * t[2] + to[0],
                 mo[1][0] * t[0] + mo[1][1] * t[1] + mo[1][2] * t[2] + to[1],
                 mo[2][0] * t[0] + mo[2][1] * t[1] + mo[2][2] * t[2] + to[2])
        cache[part.id] = (m, t)
        return m, t

    # The game draws PARTS, not meshes (finding 347): one mesh linked by two
    # parts is drawn once for each part that is shown. Only the knight's rig
    # does it (4 rigs of 2,426: the helmet on the head and a loose one); for
    # it the value is a list, one transform per linking part in rig order,
    # and every other mesh keeps its single (matrix, translation).
    output = {}
    for d in parts.values():
        if not d.mesh:
            continue
        m, t = world_transform(d)
        if d.hidden:
            # a removed part (finding 280): all vertices in one point, its
            # faces degenerate and are not drawn
            m = ((0.0, 0.0, 0.0),) * 3
        mesh = d.mesh - 1                 # the mesh index is 1-based
        if mesh not in output:
            output[mesh] = (m, t)
        elif isinstance(output[mesh], list):
            output[mesh].append((m, t))
        else:
            output[mesh] = [output[mesh], (m, t)]
    return output


def per_part(parts: dict[int, Part]) -> dict[int, tuple]:
    """Like `transforms`, but by part id and also for parts without a mesh.

    Used for attachments: a clone can appear on a part of the parent's rig
    that draws nothing (Ombelll's finding 73-74). Same parent chaining
    as `transforms`.
    """
    cache: dict[int, tuple] = {}

    def world_transform(part: Part, depth=0):
        if part.id in cache:
            return cache[part.id]
        m, t = matrix(part)
        parent_ref = parts.get(part.parent_ref) if part.parent_ref not in (None, 0, 0xFFFF) else None
        if parent_ref is not None and parent_ref is not part and depth < 32:
            mo, to = world_transform(parent_ref, depth + 1)
            m = tuple(tuple(sum(mo[i][k] * m[k][j] for k in range(3)) for j in range(3))
                      for i in range(3))
            t = tuple(sum(mo[i][k] * t[k] for k in range(3)) + to[i] for i in range(3))
        cache[part.id] = (m, t)
        return m, t

    return {d.id: world_transform(d) for d in parts.values()}


def matrix(part: Part):
    """3x3 matrix and translation of a part, in the original units."""
    return _rotation_scale_matrix(tuple(part.rotation), tuple(part.scale_factor)), part.position


@functools.lru_cache(maxsize=65536)
def _rotation_scale_matrix(rotation, scale_factor):
    """The matrix of a rotation and a scale: cached, because the same ones
    recur across many frames and many parts (loading L03A spent 0.7 s
    on matrices alone)."""
    ax, ay, az = [h * 2 * math.pi / 4096.0 for h in rotation]
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    m = mul(mul(rx, ry), rz)          # the PSX composes Rx*Ry*Rz (finding 32)
    s = [w / 4096.0 for w in scale_factor]
    return tuple(tuple(m[i][j] * s[j] for j in range(3)) for i in range(3))
