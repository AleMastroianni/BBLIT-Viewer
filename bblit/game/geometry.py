"""Reads a level's geometry: the terrain and the models of the objects
(Ombelll's MODELFORMAT.md). The OBJ export that used to live here is the
tool `tools/obj_export.py`.

Model: TMD header with float32 vertices.

    +0  u32 magic 0x41   +4 u32 flags   +8 u32 nobj
    +12 object table, nobj records of 28 bytes:
        vert_top, n_vert, norm_top, n_norm, prim_top, n_prim, scale
    all offsets are relative to model start + 12

Vertex: 16 bytes, f32 x, y, z + u32 id; bit 15 of the id marks an ALIAS,
i.e. the copy of the same vertex in another part's block. A primitive's
indices are IDs within its own part, never global indices.

Terrain: the chunk is a list of SECTORS, not a normal model.

    +0 u16 number of polygons + 2   (counts the dispatcher entries: header
                                     and point block are not polygons)
    +2 u16 modus (0x0000, 0x0800, 0x0C00, 0x1000)
    +4 u16 record length divided by four
    +6 u16 number of bounding faces (6 at 0x0800/0x0C00)

Modus 0x1000 is an invisible collision wall: it must not be drawn.

Conversion to a Y-up, right-handed system: (x, -y, -z), which has
determinant +1, PLUS reversing the vertex order of every face,
because the source is LEFT-HANDED (finding 180). Negating only Y mirrors
the whole level.
"""

from __future__ import annotations

import math
import os
import struct
import sys as _sys  # noqa: E402
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# mode -> (size, number of corners, index positions, texture position)
MODES = {
    0x34: (24, 3, (14, 20, 22), 6),    # flat triangle
    0x38: (28, 4, (20, 22, 24, 26), 6),  # flat quad
    # Gouraud triangle: the vertex of the first UV and first color is the one
    # at +28, not at +14 (finding 277: 1195 pairs of adjacent triangles with
    # consistent colors versus 6). It is a rotation: the winding does not change.
    0x3C: (32, 3, (28, 30, 14), 6),
    0x40: (40, 4, (32, 34, 36, 38), 6),  # Gouraud quad
    0x4A: (28, 3, (20, 22, 24), 4),    # triangle, no UV
    0x4E: (32, 4, (24, 26, 28, 30), 4),  # quad, no UV
}
UV_MODES = {0x34, 0x38, 0x3C, 0x40}
UNITS_PER_METER = 128.0  # 128 units = 1 meter


class Face:
    __slots__ = ("corners", "tex_id", "uvs", "colors", "blend", "two_sided")

    def __init__(self, corners, tex_id, uvs, colors, blend=None, two_sided=False):
        self.corners = corners      # indices into the global vertex list
        self.tex_id = tex_id    # texture id, or None
        self.uvs = uvs            # list of (u, v) 0..255, or None
        self.colors = colors    # list of (r, g, b)
        self.blend = blend          # None = opaque, otherwise 0..3 (see BLEND_MODES)
        # bit 0x02 of the flag byte at +2 (finding 307): drawn from both
        # sides; the others the game culls by the sign of the screen cross
        # product, the visible side being where (v0 - v1) x (v2 - v1) points
        self.two_sided = two_sided


# The four PlayStation blend modes, selected by bits 5-6 of the word at +10
# when bit 3 of the flag at +2 says the primitive is semi-transparent.
# B is what is already on screen, F the face being drawn.
BLEND_MODES = {
    0: ("meta", "B/2 + F/2"),
    1: ("additivo", "B + F"),
    2: ("sottrattivo", "B - F"),
    3: ("quarto", "B + F/4"),
}


def _read_color(data: bytes, o: int) -> tuple[int, int, int]:
    return (data[o], data[o + 1], data[o + 2])


def triangles(n: int) -> list[tuple[int, int, int]]:
    """How a primitive is split into triangles.

    A PlayStation quad is a **Z**, not a fan: its triangles
    are (0,1,2) and (1,3,2). Treating it as a fan — (0,1,2) and (0,2,3) —
    gives a bow tie: a triangular hole on one side and an overlap
    on the other. Measured on L03A: 516 of the 2378 terrain quads (22%) change
    area between the two readings.

    The vertex order is then reversed because the source is left-handed
    (finding 180).
    """
    if n == 3:
        basis = [(0, 1, 2)]
    elif n == 4:
        basis = [(0, 1, 2), (1, 3, 2)]
    else:
        basis = [(0, k, k + 1) for k in range(1, n - 1)]
    return [t[::-1] for t in basis]


def read_primitives(data: bytes, start: int, item_count: int, index_map, *, local=False, stat=None):
    """Reads `item_count` primitive records. `index_map` translates an index into a vertex.

    `stat`, if given, collects the census counts: the records never read
    because the chain stops on an unknown mode, and how many records per
    mode and per flag. Without `stat` the behavior is identical.
    """
    faces, pos, n_read, rejected = [], start, 0, 0
    while n_read < item_count:
        mode = data[pos + 3]
        if mode not in MODES:
            # the chain breaks off: the rest of the part is not read
            if stat is not None:
                stat["unknown_mode"] = stat.get("unknown_mode", 0) + (item_count - n_read)
            break
        if stat is not None:
            per_mode = stat.setdefault("per_mode", {})
            per_mode[mode] = per_mode.get(mode, 0) + 1
            per_flag = stat.setdefault("per_flag", {})
            lookup_key = (mode, data[pos + 2])
            per_flag[lookup_key] = per_flag.get(lookup_key, 0) + 1
        measure, corners, idx_pos, tex_pos = MODES[mode]
        flag_byte = data[pos + 2]

        raw = [struct.unpack_from("<H", data, pos + o)[0] for o in idx_pos[:corners]]
        try:
            points = [index_map(i) for i in raw]
        except (KeyError, IndexError):
            rejected += 1
            pos += measure
            n_read += 1
            continue

        tex_id = uvs = blend = None
        if mode in (0x4A, 0x4E):
            # These modes have no UVs because they do not need them: the field at
            # +4 names a SOLID-COLOR texture (in the corpus they are 4x4), so
            # sampling it at any point gives the same color. Drawing them
            # with only the vertex color makes them come out white or gray.
            tex_id = struct.unpack_from("<H", data, pos + tex_pos)[0]
            uvs = [(128, 128)] * corners
        elif mode in UV_MODES:
            # WARNING: `FF FF` in the first UV does NOT mean "no texture".
            # It is the corner coordinate (255,255), and discarding those faces
            # loses 1158 of 3048 in L03A — all with a registered texture id
            # and none with all UVs at FF. An untextured face is recognized
            # by an id that does not exist in the table, not by these bytes.
            tex_id = struct.unpack_from("<H", data, pos + tex_pos)[0]
            pairs = [(data[pos + 4], data[pos + 5]), (data[pos + 8], data[pos + 9]),
                     (data[pos + 12], data[pos + 13]), (data[pos + 14], data[pos + 15])]
            uvs = pairs[:corners]
            # bit 3 of the flag = semi-transparent; the mode is in bits 5-6
            # of the word at +10, which otherwise carries the palette id
            if flag_byte & 0x08:
                blend = (struct.unpack_from("<H", data, pos + 10)[0] >> 5) & 3

        if mode in (0x34, 0x38):
            colors = [_read_color(data, pos + 16)] * corners
        elif mode in (0x3C, 0x40):
            colors = [_read_color(data, pos + 16 + 4 * i) for i in range(corners)]
        else:
            colors = [_read_color(data, pos + 8 + 4 * i) for i in range(corners)]

        faces.append(Face(points, tex_id, uvs, colors, blend, bool(flag_byte & 0x02)))
        pos += measure
        n_read += 1
    return faces, pos, rejected


def model_vertices(sec4: bytes, offset: int, part_transforms=None, weld=True):
    """A model's vertices, part by part, already transformed.

    Each part's vertices are in LOCAL space. `part_transforms` is a
    map TMD-part-index -> (3x3 matrix, translation) that puts them in
    place; without it the parts stay stacked on the origin, which is
    how a multi-part model comes out disassembled. Returns the vertex
    list and, for each drawn copy of a part, the pair (part index, map
    id -> index in the list).

    A part whose transform is a list is drawn once per transform (finding
    347: the game draws rig parts, and the knight links its helmet twice);
    `copies` gives, in order, which TMD part each drawn copy is.
    """
    _magic, _flag_bits, nobj = struct.unpack_from("<III", sec4, offset)
    basis = offset + 12

    def _world_vertex(i, v, mt):
        vt = struct.unpack_from("<i", sec4, basis + 28 * i)[0]
        x, y, z, vid = struct.unpack_from("<fffI", sec4, basis + vt + 16 * v)
        if mt is not None:
            m, t = mt
            x, y, z = (m[0][0] * x + m[0][1] * y + m[0][2] * z + t[0],
                       m[1][0] * x + m[1][1] * y + m[1][2] * z + t[1],
                       m[2][0] * x + m[2][1] * y + m[2][2] * z + t[2])
        return (x, y, z), vid

    # A vertex with bit 0x8000 in its id is the copy of a vertex of ANOTHER
    # part, the one with the same id without the bit (finding 276). It must
    # be welded to the original's position: transformed with its own part it opens
    # gaps at the joints (shoulders, arms, Merlin's face).
    per_part = []
    own = {}
    for i in range(nobj):
        n_vert = struct.unpack_from("<i", sec4, basis + 28 * i + 4)[0]
        mt = part_transforms.get(i) if part_transforms else None
        for copy in (mt if isinstance(mt, list) else [mt]):
            entries = [_world_vertex(i, v, copy) for v in range(n_vert)]
            per_part.append((i, entries))
            # a hidden copy (all-zero matrix) never lends its vertices to a weld
            if isinstance(mt, list) and not any(any(r) for r in copy[0]):
                continue
            for p, vid in entries:
                if not vid & 0x8000:
                    own[vid & 0x7FFF] = p

    vertices, ids_per_part = [], []
    for i, entries in per_part:
        begin = len(vertices)
        ids = {}
        for v, (p, vid) in enumerate(entries):
            if vid & 0x8000 and weld:
                p = own.get(vid & 0x7FFF, p)
            vertices.append(p)
            ids[vid & 0x7FFF] = begin + v  # faces name the id without the bit
        ids_per_part.append((i, ids))
    return vertices, ids_per_part


def read_model(sec4: bytes, offset: int, part_transforms=None, stat=None, weld=True):
    """Returns (vertices, faces, rejected) of a model (see `model_vertices`)."""
    magic, _flag_bits, nobj = struct.unpack_from("<III", sec4, offset)
    if magic != 0x41:
        raise ValueError(f"no model at {offset}")
    basis = offset + 12
    vertices, ids_per_part = model_vertices(sec4, offset, part_transforms, weld)
    faces, rejected = [], 0
    for i, ids in ids_per_part:
        _vt, _n_vert, _nt, _n_norm, pt, n_prim, _scale_field = struct.unpack_from("<7i", sec4, basis + 28 * i)
        part_faces, _pos, n_rejected = read_primitives(sec4, basis + pt, n_prim, lambda k: ids[k],
                                                    stat=stat)
        faces += part_faces
        rejected += n_rejected
    return vertices, faces, rejected


def convex_order(pts) -> tuple[int, int, int, int]:
    """The order of an invisible wall's four corners that gives a
    convex quadrilateral: (0,1,2,3) for 1434 of the 1527 walls of the menu
    levels, (0,1,3,2) for the other 93 (measured on all the menu levels). If
    neither is convex (does not happen), the first."""
    for corner_order in ((0, 1, 2, 3), (0, 1, 3, 2)):
        p = [pts[i] for i in corner_order]
        n = [0.0, 0.0, 0.0]
        for i in range(4):
            a, b = p[i], p[(i + 1) % 4]
            n[0] += (a[1] - b[1]) * (a[2] + b[2])
            n[1] += (a[2] - b[2]) * (a[0] + b[0])
            n[2] += (a[0] - b[0]) * (a[1] + b[1])
        signs = set()
        for i in range(4):
            a, b, c = p[i], p[(i + 1) % 4], p[(i + 2) % 4]
            u = [b[k] - a[k] for k in range(3)]
            v = [c[k] - b[k] for k in range(3)]
            x = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            d = x[0] * n[0] + x[1] * n[1] + x[2] * n[2]
            if abs(d) > 1e-6:
                signs.add(d > 0)
        if len(signs) == 1:
            return corner_order
    return (0, 1, 2, 3)


class TerrainSector:
    """One entry group of a terrain object's stream (terrain_sectors)."""
    __slots__ = ("kind", "pos", "end", "item_count", "points_pos", "point_count", "prims_pos", "prim_count")

    def __init__(self, kind, pos, end, item_count, points_pos=0, point_count=0, prims_pos=0, prim_count=0):
        self.kind = kind                # "sector", "wall" (0x1000) or "rejected" (no point block)
        self.pos, self.end = pos, end   # first byte, and the byte after the last
        self.item_count = item_count    # the dispatcher entries it takes
        self.points_pos, self.point_count = points_pos, point_count   # the points, 12 bytes each
        self.prims_pos, self.prim_count = prims_pos, prim_count       # the polygons


def terrain_sectors(sec4: bytes, pos: int, n_prim: int):
    """The sectors of one terrain object, from its stream at `pos` whose
    dispatcher entries add up to `n_prim` (Ombelll's finding 150: header,
    point block `0x44`, polygons, and field +0 of a header counts its
    entries). The one walk of the sectors: read_terrain, census.py and the
    diagnostics use it.

    A sector can lack its header (finding 289): the stream starts with the
    point block, and the polygons run up to the next header or point block.
    Only 3 blocks on the disc, the first sector of CCMERLIN and L03A2_8 and
    all of CCEND (no global vertices): walked entry by entry like the
    game's dispatcher, each ends exactly on its vertex table (or on the
    block's end)."""
    running_sum = 0
    while running_sum < n_prim:
        if sec4[pos + 3] == 0x44:
            point_count = struct.unpack_from("<H", sec4, pos)[0]
            q = pos + 4 + 12 * point_count
            n_poly, r = 0, q
            while running_sum + 1 + n_poly < n_prim and sec4[r + 3] in MODES:
                r += MODES[sec4[r + 3]][0]
                n_poly += 1
            yield TerrainSector("sector", pos, r, 1 + n_poly, pos + 4, point_count, q, n_poly)
            running_sum += 1 + n_poly
            pos = r
            continue
        item_count, mode, length_words, n_bound_faces = struct.unpack_from("<HHHH", sec4, pos)
        reclen = length_words * 4
        if reclen <= 0 or pos + reclen > len(sec4):
            return
        running_sum += item_count
        if mode == 0x1000:
            yield TerrainSector("wall", pos, pos + reclen, item_count)
        else:
            # the header takes 8 bytes plus max(n_bound_faces, 1) faces of 8: even without
            # bounding faces the dispatcher step still skips one
            p = pos + 8 + max(n_bound_faces, 1) * 8
            point_count, tag = struct.unpack_from("<HH", sec4, p)
            if tag != 0x4400:
                yield TerrainSector("rejected", pos, pos + reclen, item_count)
            else:
                yield TerrainSector("sector", pos, pos + reclen, item_count, p + 4, point_count,
                                    p + 4 + 12 * point_count, max(item_count - 2, 0))
        pos += reclen


def read_terrain(sec4: bytes, offset: int, invisible_walls: list | None = None,
                 portal_areas: list | None = None):
    """Reads a terrain chunk as a list of sectors (terrain_sectors).

    With `invisible_walls` (a list) it also collects the invisible walls (modus 0x1000):
    one quad per record, indices into the block's global vertex list
    (MODELFORMAT, "Modus 0x10"), as 4 indices into `vertices` in convex
    order. In the menu levels: 1527 records, all 20 bytes, all with
    the indices inside the block, all vertical. The last 4 bytes are the area
    seen through the portal (finding 293): with `portal_areas` (a list) they
    are collected alongside, one per quad."""
    _magic, _flag_bits, nobj = struct.unpack_from("<III", sec4, offset)
    basis = offset + 12
    vertices, faces = [], []
    stat = {"sectors": 0, "wall_sectors": 0, "polygons": 0, "expected": 0, "rejected": 0, "clean": 0}

    for i in range(nobj):
        vt, n_vert, _nt, _nn, pt, n_prim, _scale_field = struct.unpack_from("<7i", sec4, basis + 28 * i)
        global_start = len(vertices)
        for v in range(n_vert):
            x, y, z, _vid = struct.unpack_from("<fffI", sec4, basis + vt + 16 * v)
            vertices.append((x, y, z))

        stat["expected"] += n_prim
        end_pos = basis + pt
        for sector in terrain_sectors(sec4, basis + pt, n_prim):
            stat["sectors"] += 1
            end_pos = sector.end
            if sector.kind == "wall":
                stat["wall_sectors"] += 1          # invisible collision walls
                stat["polygons"] += max(sector.item_count - 2, 0)
                if invisible_walls is not None and sector.end - sector.pos == 20:
                    q = struct.unpack_from("<4H", sec4, sector.pos + 8)
                    if all(h < n_vert for h in q):
                        pts = [vertices[global_start + h] for h in q]
                        invisible_walls.append(tuple(global_start + q[i] for i in convex_order(pts)))
                        if portal_areas is not None:
                            portal_areas.append(struct.unpack_from("<I", sec4, sector.pos + 16)[0])
                continue
            if sector.kind == "rejected":
                stat["polygons"] += max(sector.item_count - 2, 0)
                stat["rejected"] += 1
                continue
            stat["polygons"] += sector.prim_count
            local_start = len(vertices)
            for k in range(sector.point_count):
                vertices.append(struct.unpack_from("<fff", sec4, sector.points_pos + 12 * k))
            sector_faces, next_pos, n_rejected = read_primitives(
                sec4, sector.prims_pos, sector.prim_count, lambda i, s=local_start: s + i, local=True, stat=stat)
            faces += sector_faces
            stat["rejected"] += n_rejected
            if next_pos == sector.end:
                stat["clean"] += 1
        stat["ends_on_vertices"] = (end_pos - basis) == vt
    return vertices, faces, stat


def _transform(p, *, scale_factor=1.0, rot=None, pos=(0, 0, 0), meters=True):
    x, y, z = p
    if rot is not None:
        x, y, z = (rot[0][0] * x + rot[0][1] * y + rot[0][2] * z,
                   rot[1][0] * x + rot[1][1] * y + rot[1][2] * z,
                   rot[2][0] * x + rot[2][1] * y + rot[2][2] * z)
    x = x * scale_factor + pos[0]
    y = y * scale_factor + pos[1]
    z = z * scale_factor + pos[2]
    d = UNITS_PER_METER if meters else 1.0
    return (x / d, -y / d, -z / d)  # determinant +1; the vertex order must be reversed


def _rotation_matrix(corners):
    """Rx*Ry*Rz, with 4096 = one full turn (Ombelll's finding 32)."""
    ax, ay, az = [h * 2 * math.pi / 4096.0 for h in corners]
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    return mul(mul(rx, ry), rz)


# How a byte UV pair becomes a texture coordinate. The game has two
# renderers and they do not agree (findings 328, 341):
#   UV_PC      the OpenGL one, the one the PC plays with: byte / 255 over the
#              whole texture, then clamped to [0.01, 0.99] on both axes (a
#              last loop over the UV tables at `0x4228f4`, on every profile
#              but the software one), repeated past the edge (GL_REPEAT),
#              linear, one level. So bytes 0, 1, 2 give 0.01 and 253, 254,
#              255 give 0.99, and the opposite edge mixes in only on textures
#              under 50 texels a side: 18% on 32, 34% on 16, 42% on 8 (341).
#              The viewer's default;
#   UV_PC_AMD  the same, but an ATI / RAGE PRO driver (any AMD card) clamps
#              both coordinates to [4.5/255, 250.5/255], narrower: the outer
#              strip of every texture is never seen;
#   UV_PSX     the software renderer (`FUN_0041cd50`): scaled by (size - 1),
#              so 255 is the LAST texel, and sampled at the texel centre.
#              It is the PlayStation's rule, and the viewer's before
#              finding 328.
# The viewer stores byte / 255 in the buffers and every rule is a transform
# of it (`uv_transform`), applied when drawing: changing the rule costs
# nothing and does not rebuild the level. The clamp is applied to the
# vertices, as the game applies it to its tables: the faces interpolate
# between clamped corners in both.
# Before finding 341 the default was a provisional "pc_edge" (the
# PC coordinates with the last texel repeated past the edge), because plain
# repeating made the clock of *Wabbit on the run! 2* noisy and the game shows
# no noise in the game: finding 341 found the clamp that was missing.
UV_PC, UV_PC_AMD, UV_PSX = "pc", "pc_amd", "psx"
UV_RULES = (UV_PC, UV_PC_AMD, UV_PSX)
PC_UV_LOW, PC_UV_HIGH = 0.01, 0.99
AMD_UV_LOW, AMD_UV_HIGH = 4.5 / 255.0, 250.5 / 255.0
# the viewer's own names on the flags: not a texture of the game, and their
# coordinates go OUTSIDE 0..1 (`flag_labels.label_uvs` puts the text box in
# the middle of the face and lets the corners run past it), so no clamp
UV_RAW = "raw"
NO_CLAMP = 1.0e6


def uv_to_unit(u: int, v: int) -> tuple[float, float]:
    """From bytes 0..255 to 0..1 over the whole texture (rule UV_PC).

    v must be COUNTED FROM THE BOTTOM: with v from the top the ACME lettering
    on the crates comes out upside down and the billboards of the distant
    islands are flipped, while in the game they are upright
    (finding 271).
    """
    return (u / 255.0, (255 - v) / 255.0)


def uv_transform(rule: str, measure: tuple[int, int] | None):
    """(low, high, scale, offset), each a pair: the coordinate drawn is
    clamp(uv, low, high) * scale + offset. `measure` is the texture's size,
    which only UV_PSX needs. UV_RAW (a flag's name) leaves the coordinate
    alone."""
    if rule == UV_PC_AMD:
        return ((AMD_UV_LOW, AMD_UV_LOW), (AMD_UV_HIGH, AMD_UV_HIGH), (1.0, 1.0), (0.0, 0.0))
    if rule == UV_PC:
        return ((PC_UV_LOW, PC_UV_LOW), (PC_UV_HIGH, PC_UV_HIGH), (1.0, 1.0), (0.0, 0.0))
    wide = ((-NO_CLAMP, -NO_CLAMP), (NO_CLAMP, NO_CLAMP))
    if rule == UV_PSX and measure:
        b, h = measure
        return wide + (((b - 1) / b, (h - 1) / h), (0.5 / b, 0.5 / h))
    return wide + ((1.0, 1.0), (0.0, 0.0))


def uv_to_texture(u: int, v: int, measure: tuple[int, int], rule: str = UV_PSX) -> tuple[float, float]:
    """The coordinate a rule ends up drawing, computed here instead of on the
    graphics card: for the OBJ export, which has to bake it in."""
    pair = uv_to_unit(u, v)
    low, high, scale, offset = uv_transform(rule, measure)
    return tuple(min(max(pair[i], low[i]), high[i]) * scale[i] + offset[i] for i in (0, 1))
