"""The collision heightmap (load script block 0x36, Ombelll's FINDINGS
110-116): the game does not collide with the faces it draws, but with this.

A block (opcode 0x37: offset and size in section 4) is a `u32` with
the record count, then 68-byte records:

    +0  u16 area            +2  u16 height scale
    +4  u16 cells in X      +6  u16 cells in Z   (320-unit cells)
    +8  u16 extent X        +10 u16 extent Z
    +12 s32 origin X        +16 s32 origin Z
    +20 s32 base Y          +24 s32 top Y (Y down: it is the highest;
                            the blocks of a stack fit base on top)
    +28 u32 grid offset, +32 u32 tile offset, relative to the
        record count (not to the first record: finding 112)

The grid has one `u16` per cell: 12 bits of tile, 4 of flags (only
0x2000, never read by the game: finding 132). A tile is 8x8 signed
bytes, one per 40-unit sub-cell. The ground is
`y_floor + height_scale * -abs(byte)`; bytes 0x7E and 0x7F mean "no
ground here" (`FUN_00436c20`).
"""

from __future__ import annotations

import struct

CELL_UNITS = 320
SUBCELL = 40
NO_GROUND = (0x7E, 0x7F)


class HeightmapBlock:
    __slots__ = ("area", "height_scale", "width_units", "height_units", "ext_x", "ext_z", "ox", "oz",
                 "y_floor", "y_ceiling", "grid", "tiles")

    def ground_height(self, x: float, z: float) -> float | None:
        """The collision ground height at (x, z), or None if the point
        is outside the block or over a sub-cell with no ground."""
        dx, dz = x - self.ox, z - self.oz
        if not (0 <= dx < self.ext_x and 0 <= dz < self.ext_z):
            return None
        cx, cz = int(dx // CELL_UNITS), int(dz // CELL_UNITS)
        if cx >= self.width_units or cz >= self.height_units:
            return None
        grid_cell = self.grid[cx + cz * self.width_units]
        tile = grid_cell & 0x0FFF
        i = tile * 64 + int((dz % CELL_UNITS) // SUBCELL) * 8 + int((dx % CELL_UNITS) // SUBCELL)
        if i >= len(self.tiles):
            return None
        b = self.tiles[i]
        if b in NO_GROUND:
            return None
        b = b - 256 if b > 127 else b
        return self.y_floor + self.height_scale * -abs(b)


def fetch(sec4: bytes, offset: int) -> list[HeightmapBlock]:
    """The records of a 0x37 block."""
    n = struct.unpack_from("<I", sec4, offset)[0]
    grid_blocks = []
    for k in range(n):
        r = offset + 4 + 68 * k
        (area, height_scale, w, h, ex, ez, ox, oz, yp, yf, g, t) = struct.unpack_from(
            "<HHHHHHiiiiII", sec4, r)
        b = HeightmapBlock()
        b.area, b.height_scale, b.width_units, b.height_units = area, height_scale, w, h
        b.ext_x, b.ext_z, b.ox, b.oz, b.y_floor, b.y_ceiling = ex, ez, ox, oz, yp, yf
        b.grid = struct.unpack_from(f"<{w * h}H", sec4, offset + g)
        # the tiles run to the end of the block: take them all
        b.tiles = sec4[offset + t: offset + t + 64 * (max((c & 0x0FFF) for c in b.grid) + 1)]
        grid_blocks.append(b)
    return grid_blocks


# a walkable face is "without collision" if under its centre the
# heightmap has no ground within this distance: the game's step
# threshold (finding 116: more than 100 units above is a wall)
TOLERANCE = 100


def no_collision_kind(grid_blocks: list[HeightmapBlock], corner_points, trap_boxes=()) -> str | None:
    """A walkable face with no collision under it that you fall through
    safely. `corner_points`: the face's vertices in game coordinates (Y down).

    Only faces with an up normal within ~45 degrees of vertical are judged
    (up is +Y of the file normal: 8384 of the 8443 faces with ground under
    them). The face qualifies if at its centre no block has ground within
    TOLERANCE of it. Then the fall from the centre decides the kind:
    "safe" if the first thing met is ground, "trap" if it is one of the
    `trap_boxes` (zone boxes that kill, hurt or teleport: zones.trap_box). A
    lava surface over a death slab is a trap; the one spot where you land
    safely on the base below is safe. None if the face has collision.
    """
    p = corner_points
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    if ln == 0 or n[1] / ln < 0.7:
        return None
    x = sum(q[0] for q in p) / len(p)
    y = sum(q[1] for q in p) / len(p)
    z = sum(q[2] for q in p) / len(p)
    grounds = ground_heights(grid_blocks, x, z)
    if any(abs(g - y) <= TOLERANCE for g in grounds):
        return None
    below = [g for g in grounds if g > y]
    landing = min(below) if below else None          # the first ground under you
    for x0, y0, z0, x1, y1, z1 in trap_boxes:
        if x0 <= x <= x1 and z0 <= z <= z1 and y1 >= y:
            contact = max(y0, y)                         # where the fall enters the zone
            if landing is None or contact <= landing:
                return "trap"
    return "safe"

def read_level_blocks(sec4: bytes, lvl: dict) -> list[HeightmapBlock]:
    """All the collision blocks of a level (`loadscript.export_level`)."""
    output = []
    for item in lvl.get("heightmaps", []):
        output += fetch(sec4, item["offset"])
    return output


# ----------------------------------------------------------- for the flags
# (Ground, Hard walls, Fake walls): all in game coordinates, Y down

SUBCELLS_PER_CELL = CELL_UNITS // SUBCELL      # 8
HARD_WALL_HEIGHT = 640                       # how tall a hard wall is drawn (5 m)


def subcell_map(b: HeightmapBlock) -> tuple[int, int, bytearray]:
    """The bytes of all the block's sub-cells in a flat grid
    (width, height, bytes), 0x7E where the tile is missing."""
    w, h = b.width_units * SUBCELLS_PER_CELL, b.height_units * SUBCELLS_PER_CELL
    m = bytearray(b"\x7e" * (w * h))
    empty_tile = b"\x7e" * 64
    for cz in range(b.height_units):
        for cx in range(b.width_units):
            t = b.grid[cx + cz * b.width_units] & 0x0FFF
            tile = b.tiles[t * 64:(t + 1) * 64]
            if len(tile) < 64 or tile == empty_tile:
                continue
            for r in range(8):
                i = (cz * 8 + r) * w + cx * 8
                m[i:i + 8] = tile[r * 8:(r + 1) * 8]
    return w, h, m


def height_units(b: HeightmapBlock, v: int) -> int:
    v = v - 256 if v > 127 else v
    return b.y_floor + b.height_scale * -abs(v)


def ground_heights(grid_blocks: list[HeightmapBlock], x: float, z: float) -> list[int]:
    """The collision ground heights at (x, z), one per block."""
    return [g for b in grid_blocks if (g := b.ground_height(x, z)) is not None]


def is_hard_wall(grid_blocks: list[HeightmapBlock], x: float, z: float) -> bool:
    """A 0x7F sub-cell at (x, z): a wall at any height (finding 116)."""
    for b in grid_blocks:
        dx, dz = x - b.ox, z - b.oz
        if 0 <= dx < b.ext_x and 0 <= dz < b.ext_z:
            c = b.grid[int(dx // CELL_UNITS) + int(dz // CELL_UNITS) * b.width_units] & 0x0FFF
            i = c * 64 + int((dz % CELL_UNITS) // SUBCELL) * 8 + int((dx % CELL_UNITS) // SUBCELL)
            if i < len(b.tiles) and b.tiles[i] == 0x7F:
                return True
    return False


def raster_faces(face_points) -> dict[tuple[int, int], list[float]]:
    """For every 40-unit sub-cell (key x//40, z//40) the heights of the
    visible up-facing faces that cover it (at the sub-cell centre)."""
    output: dict[tuple[int, int], list[float]] = {}
    for p in face_points:
        u = [p[1][k] - p[0][k] for k in range(3)]
        v = [p[2][k] - p[0][k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
        if ln == 0 or n[1] / ln < 0.7:
            continue
        # the face's triangles (a PSX quad is Z-ordered: (0,1,2) and (1,3,2))
        tri = [(p[0], p[1], p[2])] + ([(p[1], p[3], p[2])] if len(p) == 4 else [])
        for a, b, c in tri:
            x0, x1 = min(a[0], b[0], c[0]), max(a[0], b[0], c[0])
            z0, z1 = min(a[2], b[2], c[2]), max(a[2], b[2], c[2])
            den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if den == 0:
                continue
            for gx in range(int(x0 // SUBCELL), int(x1 // SUBCELL) + 1):
                for gz in range(int(z0 // SUBCELL), int(z1 // SUBCELL) + 1):
                    x, z = gx * SUBCELL + SUBCELL / 2, gz * SUBCELL + SUBCELL / 2
                    l1 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / den
                    l2 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / den
                    l3 = 1 - l1 - l2
                    if l1 >= -0.01 and l2 >= -0.01 and l3 >= -0.01:
                        output.setdefault((gx, gz), []).append(l1 * a[1] + l2 * b[1] + l3 * c[1])
    return output


def surfaces(grid_blocks: list[HeightmapBlock], covered_cells: dict[tuple[int, int], list[float]]):
    """The collision ground for the Ground flag: three lists of rectangles
    (x0, z0, x1, z1, y), merged into rows along X when they share a height.

    * covered: there is a visible up-facing face within 100 units;
    * invisible: no visible face covers it (the missing bridge);
    * pixel: a sub-cell with ground and at least 3 of its 4 neighbours without,
      in the same block (the spots you land on in a pit, 40 x 40 units).
    """
    covered, invisible, pixel = [], [], []
    for b in grid_blocks:
        w, h, m = subcell_map(b)
        for gz in range(h):
            row = m[gz * w:(gz + 1) * w]
            current_run = None                                  # (gx0, value, class)
            for gx in range(w + 1):
                v = row[gx] if gx < w else 0x7E
                cell_class = None
                if v not in NO_GROUND:
                    y = height_units(b, v)
                    x, z = b.ox + gx * SUBCELL, b.oz + gz * SUBCELL
                    empty_neighbours = 0
                    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ax, az = gx + dx, gz + dz
                        if not (0 <= ax < w and 0 <= az < h) or m[az * w + ax] in NO_GROUND:
                            empty_neighbours += 1
                    if empty_neighbours >= 3:
                        pixel.append((x, z, x + SUBCELL, z + SUBCELL, y))
                    covering_heights = covered_cells.get((int(x // SUBCELL), int(z // SUBCELL)), ())
                    cell_class = "c" if any(abs(a - y) <= TOLERANCE for a in covering_heights) else "i"
                if current_run and (v != current_run[1] or cell_class != current_run[2]):
                    gx0, v0, c0 = current_run
                    if c0:
                        r = (b.ox + gx0 * SUBCELL, b.oz + gz * SUBCELL, b.ox + gx * SUBCELL,
                             b.oz + (gz + 1) * SUBCELL, height_units(b, v0))
                        (covered if c0 == "c" else invisible).append(r)
                    current_run = None
                if current_run is None:
                    current_run = (gx, v, cell_class)
    return covered, invisible, pixel


def raster_vertical(face_points) -> dict[tuple[int, int], list[float]]:
    """For every 40-unit sub-cell (key x//40, z//40) the heights of the
    visible near-vertical faces that pass through it, sampled every ~20
    units over each triangle. Used to tell a hard wall you can see from one
    you cannot."""
    out: dict[tuple[int, int], list[float]] = {}
    for p in face_points:
        u = [p[1][k] - p[0][k] for k in range(3)]
        v = [p[2][k] - p[0][k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
        if ln == 0 or abs(n[1]) / ln >= 0.7:
            continue
        tris = [(p[0], p[1], p[2])] + ([(p[1], p[3], p[2])] if len(p) == 4 else [])
        for a, b, c in tris:
            edge = max(sum((a[k] - b[k]) ** 2 for k in range(3)),
                       sum((b[k] - c[k]) ** 2 for k in range(3)),
                       sum((c[k] - a[k]) ** 2 for k in range(3))) ** 0.5
            steps = max(1, int(edge // 20) + 1)
            for i in range(steps + 1):
                for j in range(steps + 1 - i):
                    l1, l2 = i / steps, j / steps
                    l3 = 1 - l1 - l2
                    x = l1 * a[0] + l2 * b[0] + l3 * c[0]
                    yv = l1 * a[1] + l2 * b[1] + l3 * c[1]
                    z = l1 * a[2] + l2 * b[2] + l3 * c[2]
                    out.setdefault((int(x // SUBCELL), int(z // SUBCELL)), []).append(yv)
    return out


def hard_walls(grid_blocks: list[HeightmapBlock], vertical_heights=None):
    """The hard walls: vertical panels on the edges between a 0x7F sub-cell
    and one that is not, merged into continuous runs along the edge.

    Returns (xa, za, xb, zb, y_base, y_top, visible): the base sits 16 units
    under the lowest ground next to the run, the top HARD_WALL_HEIGHT over the
    highest, so a run is one clean panel. `visible` is True when a visible
    near-vertical face (raster_vertical) passes through one of the two
    sub-cells at a height inside the panel: a wall you can see. The others
    stop you with nothing drawn: the invisible walls.
    """
    out = []
    for b in grid_blocks:
        w, h, m = subcell_map(b)

        def ground(ax, az):
            if 0 <= ax < w and 0 <= az < h and m[az * w + ax] not in NO_GROUND:
                return height_units(b, m[az * w + ax])
            return b.y_floor

        def seen(cells, base, top):
            # a visible wall often stands a sub-cell or two off the edge of
            # the 0x7F cells: look within +-2 sub-cells (80 units) of both
            if vertical_heights is None:
                return False
            for gx, gz in cells:
                kx = int((b.ox + gx * SUBCELL) // SUBCELL)
                kz = int((b.oz + gz * SUBCELL) // SUBCELL)
                for dx in range(-2, 3):
                    for dz in range(-2, 3):
                        if any(top <= yv <= base for yv in vertical_heights.get((kx + dx, kz + dz), ())):
                            return True
            return False

        for axis in ("x", "z"):
            outer, inner = (w, h) if axis == "x" else (h, w)
            for i in range(outer + 1):
                run = None                    # (j0, [ground heights], visible)
                for j in range(inner + 1):
                    wall, yb, vis = False, None, None
                    if j < inner:
                        if axis == "x":
                            a = m[j * w + i - 1] if 0 < i <= w else 0x7E
                            c = m[j * w + i] if i < w else 0x7E
                            cells = ((i - 1, j), (i, j))
                        else:
                            a = m[(i - 1) * w + j] if 0 < i <= h else 0x7E
                            c = m[i * w + j] if i < h else 0x7E
                            cells = ((j, i - 1), (j, i))
                        if (a == 0x7F) != (c == 0x7F):
                            wall = True
                            open_cell = cells[1] if a == 0x7F else cells[0]
                            yb = ground(*open_cell)
                            vis = seen(cells, yb + 16, yb - HARD_WALL_HEIGHT)
                    if run and (not wall or vis != run[2]):
                        j0, ys, v0 = run
                        base, top = max(ys) + 16, min(ys) - HARD_WALL_HEIGHT
                        if axis == "x":
                            out.append((b.ox + i * SUBCELL, b.oz + j0 * SUBCELL, b.ox + i * SUBCELL,
                                        b.oz + j * SUBCELL, base, top, v0))
                        else:
                            out.append((b.ox + j0 * SUBCELL, b.oz + i * SUBCELL, b.ox + j * SUBCELL,
                                        b.oz + i * SUBCELL, base, top, v0))
                        run = None
                    if wall:
                        if run is None:
                            run = (j, [yb], vis)
                        else:
                            run[1].append(yb)
    return out


def volumes(grid_blocks: list[HeightmapBlock]) -> list[tuple[int, int, int, int, int, int]]:
    """The collision volume of each mini area: the blocks of one stack (same
    plan) from the base of the lowest to the top of the highest, as a box
    (x0, y_top, z0, x1, y_base, z1) in game coordinates. Whether its sides
    and top stop you is not known yet (finding 287): a candidate for a
    "box or dome around each mini area"."""
    stacks: dict[tuple[int, int, int, int], list[int]] = {}
    for b in grid_blocks:
        key = (b.ox, b.oz, b.ox + b.ext_x, b.oz + b.ext_z)
        stacks.setdefault(key, []).extend((b.y_floor, b.y_ceiling))
    return [(x0, min(ys), z0, x1, max(ys), z1) for (x0, z0, x1, z1), ys in stacks.items()]
