"""Exports a level's terrain and props to OBJ + MTL (Ombelll's MODELFORMAT.md).

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

import argparse
import json
import math
import os
import struct
import sys as _sys  # noqa: E402
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

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
    __slots__ = ("corners", "tex_id", "uvs", "colors", "blend")

    def __init__(self, corners, tex_id, uvs, colors, blend=None):
        self.corners = corners      # indices into the global vertex list
        self.tex_id = tex_id    # texture id, or None
        self.uvs = uvs            # list of (u, v) 0..255, or None
        self.colors = colors    # list of (r, g, b)
        self.blend = blend          # None = opaque, otherwise 0..3 (see BLEND_MODES)


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

        faces.append(Face(points, tex_id, uvs, colors, blend))
        pos += measure
        n_read += 1
    return faces, pos, rejected


def model_vertices(sec4: bytes, offset: int, part_transforms=None, weld=True):
    """A model's vertices, part by part, already transformed.

    Each part's vertices are in LOCAL space. `part_transforms` is a
    map TMD-part-index -> (3x3 matrix, translation) that puts them in
    place; without it the parts stay stacked on the origin, which is
    how a multi-part model comes out disassembled. Returns the vertex
    list and, for each part, the map id -> index in the list.
    """
    _magic, _flag_bits, nobj = struct.unpack_from("<III", sec4, offset)
    basis = offset + 12

    def _world_vertex(i, v):
        vt = struct.unpack_from("<i", sec4, basis + 28 * i)[0]
        x, y, z, vid = struct.unpack_from("<fffI", sec4, basis + vt + 16 * v)
        mt = part_transforms.get(i) if part_transforms else None
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
        entries = [_world_vertex(i, v) for v in range(n_vert)]
        per_part.append(entries)
        for p, vid in entries:
            if not vid & 0x8000:
                own[vid & 0x7FFF] = p

    vertices, ids_per_part = [], []
    for entries in per_part:
        begin = len(vertices)
        ids = {}
        for v, (p, vid) in enumerate(entries):
            if vid & 0x8000 and weld:
                p = own.get(vid & 0x7FFF, p)
            vertices.append(p)
            ids[vid & 0x7FFF] = begin + v  # faces name the id without the bit
        ids_per_part.append(ids)
    return vertices, ids_per_part


def read_model(sec4: bytes, offset: int, part_transforms=None, stat=None, weld=True):
    """Returns (vertices, faces, rejected) of a model (see `model_vertices`)."""
    magic, _flag_bits, nobj = struct.unpack_from("<III", sec4, offset)
    if magic != 0x41:
        raise ValueError(f"no model at {offset}")
    basis = offset + 12
    vertices, ids_per_part = model_vertices(sec4, offset, part_transforms, weld)
    faces, rejected = [], 0
    for i in range(nobj):
        _vt, _n_vert, _nt, _n_norm, pt, n_prim, _scale_field = struct.unpack_from("<7i", sec4, basis + 28 * i)
        ids = ids_per_part[i]
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


def read_terrain(sec4: bytes, offset: int, invisible_walls: list | None = None):
    """Reads a terrain chunk as a list of sectors (terrain_sectors).

    With `invisible_walls` (a list) it also collects the invisible walls (modus 0x1000):
    one quad per record, indices into the block's global vertex list
    (MODELFORMAT, "Modus 0x10"), as 4 indices into `vertices` in convex
    order. In the menu levels: 1527 records, all 20 bytes, all with
    the indices inside the block, all vertical. The last 4 bytes of the record
    (small numbers: 2, 4, 5, 6, 9...) are not read."""
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


def uv_to_texture(u: int, v: int, measure: tuple[int, int]) -> tuple[float, float]:
    """From bytes 0..255 to texture coordinates.

    The game does not divide by 256: `FUN_0041cd50` scales by (size - 1),
    so 255 is the LAST texel, not the right edge. Sampling is then at the
    texel center, otherwise with a linear filter the edge bleeds into the
    opposite texel.

    v must be COUNTED FROM THE BOTTOM: with v from the top the ACME lettering
    on the crates comes out upside down and the billboards of the distant
    islands are flipped, while in the game they are upright
    (finding 271).
    """
    b, h = measure
    x = u / 255.0 * (b - 1)
    y = (255 - v) / 255.0 * (h - 1)
    return ((x + 0.5) / b, (y + 0.5) / h)


class ObjWriter:
    """Collects vertices and faces and writes OBJ + MTL."""

    def __init__(self, sizes=None):
        self.v: list[tuple[float, float, float]] = []
        self.vc: list[tuple[int, int, int]] = []
        self.vt: list[tuple[float, float]] = []
        self.face_groups: dict[str, list] = {}
        self.sizes = sizes or {}
        self.untextured_count = 0

    def add_group(self, face_group, vertices, faces, **kw):
        basis = len(self.v)
        for p in vertices:
            self.v.append(_transform(p, **kw))
            self.vc.append((128, 128, 128))
        entries = self.face_groups.setdefault(face_group, [])
        for vl in faces:
            for h, k in zip(vl.corners, vl.colors):
                self.vc[basis + h] = k

            # a face naming a texture the level does not register
            # is not textured: the vertex color applies
            tex_id = vl.tex_id if vl.tex_id in self.sizes else None
            if vl.tex_id is not None and tex_id is None:
                self.untextured_count += 1

            uv_idx = None
            if vl.uvs and tex_id is not None:
                uv_idx = []
                for (u, vv) in vl.uvs:
                    tu, tv = uv_to_texture(u, vv, self.sizes[tex_id])
                    self.vt.append((tu, 1.0 - tv))
                    uv_idx.append(len(self.vt))

            # triangles are written, not polygons: a quad left to the
            # importer would be closed as a fan, which is wrong here
            for tri in triangles(len(vl.corners)):
                corners = [basis + vl.corners[i] + 1 for i in tri]
                uv = [uv_idx[i] for i in tri] if uv_idx else None
                entries.append((corners, uv, tex_id, vl.blend if tex_id is not None else None))

    def write_obj(self, obj_path, texture_dir="textures"):
        mtl_path = os.path.splitext(obj_path)[0] + ".mtl"
        materials = {(t, m) for entries in self.face_groups.values()
                      for _, _, t, m in entries if t is not None}
        textures = {t for t, _ in materials}

        with open(mtl_path, "w", encoding="utf-8") as m:
            m.write("newmtl color\nKd 1 1 1\n\n")
            for t, blend in sorted(materials, key=lambda x: (x[0], -1 if x[1] is None else x[1])):
                name = f"tex{t}" if blend is None else f"tex{t}_m{blend}"
                m.write(f"newmtl {name}\nKd 1 1 1\nmap_Kd {texture_dir}/{t}.png\n")
                if blend is None:
                    m.write("d 1\n\n")
                else:
                    # OBJ only knows dissolve: additive and subtractive
                    # cannot be expressed and must be set by hand in Blender
                    blend_name, blend_formula = BLEND_MODES[blend]
                    m.write(f"d {0.5 if blend == 0 else 0.75}\n"
                            f"# fusione PSX {blend}: {blend_name}, {blend_formula}\n\n")

        with open(obj_path, "w", encoding="utf-8") as f:
            f.write(f"mtllib {os.path.basename(mtl_path)}\n")
            for (x, y, z), (r, g, b) in zip(self.v, self.vc):
                f.write(f"v {x:.4f} {y:.4f} {z:.4f} {r/255:.3f} {g/255:.3f} {b/255:.3f}\n")
            for u, vv in self.vt:
                f.write(f"vt {u:.5f} {vv:.5f}\n")
            for face_group, entries in self.face_groups.items():
                f.write(f"g {face_group}\n")
                current_mtl = None
                for corners, uv_idx, tex_id, blend in sorted(
                        entries, key=lambda r: (r[2] is None, r[2] or 0, -1 if r[3] is None else r[3])):
                    if tex_id is None:
                        mat = "color"
                    else:
                        mat = f"tex{tex_id}" if blend is None else f"tex{tex_id}_m{blend}"
                    if mat != current_mtl:
                        f.write(f"usemtl {mat}\n")
                        current_mtl = mat
                    uv = uv_idx  # order and winding already fixed in add_group
                    if uv:
                        f.write("f " + " ".join(f"{h}/{t}" for h, t in zip(corners, uv)) + "\n")
                    else:
                        f.write("f " + " ".join(str(h) for h in corners) + "\n")
        return mtl_path, len(textures)


def main() -> None:
    p = argparse.ArgumentParser(description="a level's terrain and props -> OBJ")
    p.add_argument("section4", help="decompressed section id 4 (model block)")
    p.add_argument("json", help="load script extract")
    p.add_argument("-o", "--output", required=True, help=".obj file to write")
    p.add_argument("--no-props", action="store_true", help="terrain only")
    p.add_argument("--units", action="store_true", help="original units instead of meters")
    p.add_argument("--section3", help="section id 3, to know the texture sizes")
    p.add_argument("--chain", metavar="LEVEL", help="use the cumulative texture table")
    p.add_argument("--data", default=paths.DATA_BZE)
    p.add_argument("--textures-dir", default="textures",
                   help="texture folder referenced by the .mtl file")
    args = p.parse_args()

    with open(args.section4, "rb") as f:
        sec4 = f.read()
    with open(args.json, encoding="utf-8") as f:
        lvl = json.load(f)

    sizes = {}
    if args.chain:
        import textures as texmod
        import tim
        table = texmod.construct(args.data, args.chain, "extracted")
        for tid, (block, off) in table.slots.items():
            sizes.update(tim.sizes(block, [{"id": tid, "offset": off}]))
    elif args.section3:
        import tim
        with open(args.section3, "rb") as f:
            sizes = tim.sizes(f.read(), lvl["textures"])

    meters = not args.units
    w = ObjWriter(sizes)

    for i, t in enumerate(lvl["terrain"]):
        vertices, faces, stat = read_terrain(sec4, t["offset"])
        w.add_group(f"terrain_{i}", vertices, faces, pos=tuple(t["translation"]), meters=meters)
        print(f"terrain {i}: {stat['sectors']} sectors ({stat['wall_sectors']} invisible walls), "
              f"{len(faces)} drawable faces, {stat['polygons']}/{stat['expected']} expected polygons, "
              f"exact sectors {stat['clean']}/{stat['sectors']}, rejected {stat['rejected']}, chain ends on vertices: {stat.get('ends_on_vertices')}")

    if not args.no_props:
        models = {r["id"]: r for r in lvl["resources"] if r["data_kind"] == "model"}
        placed = n_empty = missing = 0
        for n, o in enumerate(lvl["objects"]):
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None:
                missing += 1
                continue
            res = models[mid]
            if res["size"] <= 12:
                n_empty += 1          # empty TMD: the file says "draw nothing"
                continue
            import montage
            trans = montage.transforms(sec4, o["resources"], {r["id"]: r for r in lvl["resources"]}, o)
            vertices, faces, _n_rejected = read_model(sec4, res["offset"], trans)
            # parts removed by the pose (finding 280) have all vertices at
            # one point: they are not needed in the OBJ
            faces = [vl for vl in faces if len({vertices[h] for h in vl.corners}) > 1]
            if not faces:
                continue
            rot = _rotation_matrix(o["rotation"]) if o["rotation"] else None
            scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            w.add_group(f"obj{n}_res{mid}", vertices, faces,
                       rot=rot, scale_factor=scale_factor, pos=tuple(o["position"]), meters=meters)
            placed += 1
        print(f"props: {placed} placed, {n_empty} with empty model, {missing} without model")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    mtl, n_tex = w.write_obj(args.output, args.textures_dir)
    if w.untextured_count:
        print(f"faces naming an unregistered texture, drawn with vertex color: {w.untextured_count}")
    print(f"wrote {args.output}: {len(w.v)} vertices, "
          f"{sum(len(l) for l in w.face_groups.values())} faces, {n_tex} textures in {os.path.basename(mtl)}")


if __name__ == "__main__":
    main()
