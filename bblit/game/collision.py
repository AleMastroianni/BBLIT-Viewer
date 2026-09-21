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


def _subcell_byte(b: HeightmapBlock, x: float, z: float) -> int:
    dx, dz = x - b.ox, z - b.oz
    c = b.grid[int(dx // CELL_UNITS) + int(dz // CELL_UNITS) * b.width_units] & 0x0FFF
    i = c * 64 + int((dz % CELL_UNITS) // SUBCELL) * 8 + int((dx % CELL_UNITS) // SUBCELL)
    return b.tiles[i] if i < len(b.tiles) else NO_GROUND[0]


def sweep_stops(grid_blocks, a, b, y) -> bool:
    """Does the game's wall sweep stop a mover at height `y` going from the
    point a = (x, z) to the next sub-cell b (finding 298, `0x434e40`)? It
    stops on (1) a 0x7F sub-cell, (2) ground more than 100 units above the
    mover (a 0x7E sub-cell counts as the slab's base), (3) a point in no
    block at the mover's height. A mover outside every block is not checked:
    it moves freely. The drawn terrain never counts."""
    current = block_at(grid_blocks, a[0], y, a[1])
    if current is None:
        return False
    x, z = b
    if current.ox <= x < current.ox + current.ext_x and current.oz <= z < current.oz + current.ext_z:
        target = current
    else:
        target = block_at(grid_blocks, x, y, z)
        if target is None:
            return True
    v = _subcell_byte(target, x, z)
    if v == 0x7F:
        return True
    if v == 0x7E:
        ground = target.y_floor
    else:
        v = v - 256 if v > 127 else v
        ground = target.y_floor + target.height_scale * -abs(v)
    return ground - y < -TOLERANCE


def wall_crossable(grid_blocks, corner_points) -> bool | None:
    """A vertical face (normal within ~17 degrees of horizontal, at least 60
    units tall): True if the sweep lets a mover through it at its centre, in
    both directions, at its foot, middle and top (20 units in); None if the
    face is not such a wall. Finding 298's own test missed its bars, so the
    viewer only marks the walls joined to a face with no collision under it
    (Level._terrain_overlays), not every wall this says True for."""
    p = corner_points
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    horizontal = (n[0] ** 2 + n[2] ** 2) ** 0.5
    if ln == 0 or horizontal == 0 or abs(n[1]) / ln > 0.3:
        return None
    ys = [q[1] for q in p]
    top, foot = min(ys), max(ys)            # Y down
    if foot - top < 60:
        return None
    step = (n[0] / horizontal * SUBCELL, n[2] / horizontal * SUBCELL)
    cx = sum(q[0] for q in p) / len(p)
    cz = sum(q[2] for q in p) / len(p)
    side_a, side_b = (cx + step[0], cz + step[1]), (cx - step[0], cz - step[1])
    return not any(sweep_stops(grid_blocks, side_a, side_b, y) or sweep_stops(grid_blocks, side_b, side_a, y)
                   for y in (foot - 20, (top + foot) / 2, top + 20))


def no_collision_kind(grid_blocks: list[HeightmapBlock], corner_points, trap_zones=()) -> str | None:
    """A walkable face with no collision under it that you fall through
    safely. `corner_points`: the face's vertices in game coordinates (Y down).

    Only faces with an up normal within ~45 degrees of vertical are judged
    (up is +Y of the file normal: 8384 of the 8443 faces with ground under
    them). The face qualifies if at its centre no block has ground within
    TOLERANCE of it. Then the fall from the centre decides the kind:
    "safe" if the first thing met is ground, "trap" if it is one of the
    `trap_zones` (zones that kill, hurt or teleport: zones.trap_shape, with
    their rotation). A
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
    for zone in trap_zones:
        span = zone.vertical_span(x, z)
        if span is not None and span[1] >= y:
            contact = max(span[0], y)                    # where the fall enters the zone
            if landing is None or contact <= landing:
                return "trap"
    return "safe"

def read_level_blocks(sec4: bytes, lvl: dict) -> list[HeightmapBlock]:
    """All the collision blocks of a level (`loadscript.export_level`)."""
    output = []
    for item in lvl.get("heightmaps", []):
        output += fetch(sec4, item["offset"])
    return output


# ----------------------------------------------------- the game's ground query
# (build 74ab71e1; the documents' FUN_00436b60 and FUN_00436c20, finding 111)

def block_at(grid_blocks, x: int, y: int, z: int, area: int | None = None):
    """The block containing the point, as `0x436cd0` finds it: first the
    blocks of `area` (the area the object had in the last frame), then all
    of them in file order. Inside: ox <= x < ox + extent, the same in Z,
    and y_ceiling < y <= y_floor (Y down: the slab from its top to its base)."""
    def inside(b):
        return (b.y_ceiling < y <= b.y_floor and b.ox <= x < b.ox + b.ext_x
                and b.oz <= z < b.oz + b.ext_z)
    if area is not None:
        for b in grid_blocks:
            if b.area == area and inside(b):
                return b
    for b in grid_blocks:
        if inside(b):
            return b
    return None


def ground_below(grid_blocks, x: int, y: int, z: int, area: int | None = None):
    """Where a point falling straight down from (x, y, z) lands: (ground Y,
    block), or None if nothing is under it. The ground of a block is read
    as `0x436d90` does; on a 0x7E ("no ground") or 0x7F (hard wall)
    sub-cell the game gives the slab's base as the ground, so the fall goes
    on into the block under it. Above every slab the point falls to the
    first top it meets. If the point is inside a slab but under its ground,
    the answer is that ground, above the point: where the game puts an
    object standing there.

    Integer game coordinates. The origins of all 479 blocks of the menu's
    levels are multiples of 320 and not negative: the game's sub-cell from
    the absolute x % 320 is the same as `ground_height`'s from x - ox."""
    for _ in range(len(grid_blocks) + 1):
        b = block_at(grid_blocks, x, y, z, area)
        if b is None:
            # in the air: the nearest slab top under the point
            tops = [c.y_ceiling for c in grid_blocks
                    if c.y_ceiling >= y and c.ox <= x < c.ox + c.ext_x and c.oz <= z < c.oz + c.ext_z]
            if not tops:
                return None
            y = min(tops) + 1
            continue
        g = b.ground_height(x, z)
        if g is not None:
            return g, b
        y, area = b.y_floor + 1, b.area
    return None


# the type 14 handler moves an object only if the control dword of its step
# has neither of these (finding 340): 0x1 skips the whole movement part
# (`0x440a59`), 0x80000000 frees it in 3D and skips the ground (`0x442a54`)
STEP_STILL, STEP_FREE = 0x1, 0x80000000
# bits of the second dword of opcode 0x16: follows the camera, runs in pause
# (findings 339): not objects standing anywhere
CAMERA_OR_PAUSE = 0x60000000
TYPE_14 = 14


def settles(obj) -> bool:
    """Does the game keep this placed object on the collision ground (finding
    340)? A type 14 object whose starting step has neither 0x1 nor
    0x80000000 in its control dword goes through the ground query
    `0x437500` at every tick, with a zero move too: it stands on the ground
    of the heightmap of its area, or falls onto it at most 70 a tick. The
    boxes of other objects are never ground. The types 0, 4 and 12 to 29
    never ask."""
    from game import montage       # here: montage imports rig, rig nothing of ours
    if obj.get("block_type") == 0x08 or obj.get("category") != TYPE_14:
        return False
    pos = obj.get("position")
    if not pos or tuple(pos) == (0, 0, 0):
        return False
    flags = obj.get("static_flags") or [0, 0]
    if flags[1] & CAMERA_OR_PAUSE:
        return False
    step = montage.start_step(obj)
    control = step.get("control") if step else None
    return control is not None and not control & (STEP_STILL | STEP_FREE)


def settle_objects(lvl: dict, grid_blocks) -> list[tuple]:
    """Puts on the ground the placed objects the game keeps there, as the
    game has them after their first ticks: their file height is not where
    they stand (24 on the disc more than 30 units off, the list of
    `check_ground_snap.py` of the reverse). Changes `position[1]` in place, so
    everything that follows the object (its box, its name, its clones) goes
    with it, and keeps the file's in `file_position`. Returns (index, file
    Y, ground Y) for every object moved."""
    moved = []
    if not grid_blocks:
        return moved
    for n, o in enumerate(lvl["objects"]):
        if not settles(o):
            continue
        x, y, z = o["position"]
        found = ground_below(grid_blocks, x, y, z, o.get("area"))
        if found is None:
            continue           # nothing under it: the game would let it fall
        ground = int(round(found[0]))
        if ground != y:
            o["file_position"] = list(o["position"])
            o["position"] = [x, ground, z]
            moved.append((n, y, ground))
    return moved


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
            # the same sums in the same order as when this was written out in
            # full: only the lookups move out of the inner loop, so every
            # float is the one it was (check_walls says so, number by number)
            a0, a1, a2 = a[0], a[1], a[2]
            b0, b1, b2 = b[0], b[1], b[2]
            c0, c1, c2 = c[0], c[1], c[2]
            put = out.setdefault
            for i in range(steps + 1):
                l1 = i / steps
                x1, y1, z1 = l1 * a0, l1 * a1, l1 * a2
                for j in range(steps + 1 - i):
                    l2 = j / steps
                    l3 = 1 - l1 - l2
                    x = x1 + l2 * b0 + l3 * c0
                    yv = y1 + l2 * b1 + l3 * c1
                    z = z1 + l2 * b2 + l3 * c2
                    put((int(x // SUBCELL), int(z // SUBCELL)), []).append(yv)
    return out


def _seen_between(b, vertical_heights, cells, low, high):
    """A visible near-vertical face (raster_vertical) within +-2 sub-cells
    (80 units) of one of the two sub-cells, at a height between `high` and
    `low` (Y down: high < low): a visible wall often stands a sub-cell or
    two off the edge."""
    if vertical_heights is None:
        return False
    for gx, gz in cells:
        kx = int((b.ox + gx * SUBCELL) // SUBCELL)
        kz = int((b.oz + gz * SUBCELL) // SUBCELL)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                if any(high <= yv <= low for yv in vertical_heights.get((kx + dx, kz + dz), ())):
                    return True
    return False


def hard_walls(grid_blocks: list[HeightmapBlock], vertical_heights=None):
    """The hard walls: vertical panels on the edges between a 0x7F sub-cell
    and one that is not, merged into continuous runs along the edge.

    Returns (xa, za, xb, zb, y_base, y_top, visible, free): the base sits 16
    units under the lowest ground next to the run, the top HARD_WALL_HEIGHT
    over the highest, so a run is one clean panel. `visible` is True when a
    visible near-vertical face (raster_vertical) passes through one of the
    two sub-cells at a height inside the panel: a wall you can see. The
    others stop you with nothing drawn: the invisible walls. `free` is the
    unit (dx, dz) from the edge towards the sub-cell that is not 0x7F: the
    side the wall stops you from (finding 309: the sweep stops whoever
    enters a 0x7F sub-cell, and Bugs is put back if he ends up in one).
    Nothing between two 0x7F sub-cells; a run ends where the free side
    changes.
    """
    out = []
    for b in grid_blocks:
        w, h, m = subcell_map(b)

        def ground(ax, az):
            if 0 <= ax < w and 0 <= az < h and m[az * w + ax] not in NO_GROUND:
                return height_units(b, m[az * w + ax])
            return b.y_floor

        for axis in ("x", "z"):
            outer, inner = (w, h) if axis == "x" else (h, w)
            for i in range(outer + 1):
                run = None                    # (j0, [ground heights], visible, free)
                for j in range(inner + 1):
                    wall, yb, vis, free = False, None, None, None
                    if j < inner:
                        # a on the - side of the edge, c on the + side
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
                            sign = 1 if a == 0x7F else -1
                            free = (sign, 0) if axis == "x" else (0, sign)
                            yb = ground(*open_cell)
                            vis = _seen_between(b, vertical_heights, cells, yb + 16, yb - HARD_WALL_HEIGHT)
                    if run and (not wall or vis != run[2] or free != run[3]):
                        j0, ys, v0, f0 = run
                        base, top = max(ys) + 16, min(ys) - HARD_WALL_HEIGHT
                        if axis == "x":
                            out.append((b.ox + i * SUBCELL, b.oz + j0 * SUBCELL, b.ox + i * SUBCELL,
                                        b.oz + j * SUBCELL, base, top, v0, f0))
                        else:
                            out.append((b.ox + j0 * SUBCELL, b.oz + i * SUBCELL, b.ox + j * SUBCELL,
                                        b.oz + i * SUBCELL, base, top, v0, f0))
                        run = None
                    if wall:
                        if run is None:
                            run = (j, [yb], vis, free)
                        else:
                            run[1].append(yb)
    return out


def step_walls(grid_blocks: list[HeightmapBlock], vertical_heights=None):
    """The steps that stop you (findings 298, 309): the wall sweep stops a
    mover entering a sub-cell whose ground is more than 100 units above it,
    so a step stops you only going up, from its low side. The 40-unit
    sub-cell edges, inside a block, between two sub-cells whose grounds
    differ by more than TOLERANCE, a 0x7E sub-cell counting as the slab's
    base (a hole is the low side of a step, never the high one); 0x7F
    sub-cells are hard walls, not steps. Merged into runs along the edge as
    the hard walls are.

    Returns (xa, za, xb, zb, y_high, y_low, visible, low, hole): the panel
    from the lowest low ground to the highest high ground of the run (Y
    down: y_high < y_low). `visible` as for the hard walls, between the two
    grounds. `low` is the unit (dx, dz) from the edge towards the low side,
    where the step stops you; `hole` is True when the low side is a 0x7E
    sub-cell. A run ends where visibility, low side or kind change. The
    block sides are area_walls."""
    out = []
    for b in grid_blocks:
        w, h, m = subcell_map(b)

        def ground_of(v):
            return b.y_floor if v == 0x7E else height_units(b, v)

        for axis in ("x", "z"):
            outer, inner = (w, h) if axis == "x" else (h, w)
            for i in range(1, outer):
                run = None                    # [j0, high, low, visible, low side, hole]
                for j in range(inner + 1):
                    step = None
                    if j < inner:
                        # a on the - side of the edge, c on the + side
                        if axis == "x":
                            a, c, cells = m[j * w + i - 1], m[j * w + i], ((i - 1, j), (i, j))
                        else:
                            a, c, cells = m[(i - 1) * w + j], m[i * w + j], ((j, i - 1), (j, i))
                        if a != 0x7F and c != 0x7F and not (a == 0x7E and c == 0x7E):
                            ya, yc = ground_of(a), ground_of(c)
                            if abs(ya - yc) > TOLERANCE:
                                high, low = min(ya, yc), max(ya, yc)
                                sign = 1 if yc > ya else -1          # towards the lower ground (Y down)
                                side = (sign, 0) if axis == "x" else (0, sign)
                                hole = (c if sign == 1 else a) == 0x7E
                                step = (high, low, _seen_between(b, vertical_heights, cells, low, high), side, hole)
                    if run is not None and (step is None or step[2:] != tuple(run[3:])):
                        j0, high, low, vis, side, hole = run
                        if axis == "x":
                            out.append((b.ox + i * SUBCELL, b.oz + j0 * SUBCELL, b.ox + i * SUBCELL,
                                        b.oz + j * SUBCELL, high, low, vis, side, hole))
                        else:
                            out.append((b.ox + j0 * SUBCELL, b.oz + i * SUBCELL, b.ox + j * SUBCELL,
                                        b.oz + i * SUBCELL, high, low, vis, side, hole))
                        run = None
                    if step is not None:
                        if run is None:
                            run = [j, step[0], step[1], step[2], step[3], step[4]]
                        else:
                            run[1], run[2] = min(run[1], step[0]), max(run[2], step[1])
    return out


def area_walls(grid_blocks: list[HeightmapBlock]):
    """The sides of the blocks that stop a mover inside them (finding 298:
    the sweep stops when the next point is in no block at the mover's
    height): each side of each slab, sub-cell by sub-cell, minus the heights
    where another block continues it just outside. Only from inside: a
    mover outside every block is not checked at all.

    Returns (xa, za, xb, zb, y_top, y_base, inside) panels, runs merged along
    the side; `inside` is the unit (dx, dz) pointing into the block."""
    out = []
    for b in grid_blocks:
        x0, z0, x1, z1 = b.ox, b.oz, b.ox + b.ext_x, b.oz + b.ext_z
        # (fixed coordinate, outside offset, along from, along to, axis, inside)
        for fixed, outside, a0, a1, axis, inside in ((x0, -1, z0, z1, "x", (1, 0)), (x1, 0, z0, z1, "x", (-1, 0)),
                                                     (z0, -1, x0, x1, "z", (0, 1)), (z1, 0, x0, x1, "z", (0, -1))):
            run = None                      # (start, intervals)
            pos = a0
            while True:
                intervals = None
                if pos < a1:
                    mid = pos + SUBCELL // 2
                    px, pz = (fixed + outside, mid) if axis == "x" else (mid, fixed + outside)
                    # the heights of b's slab that no other block holds just outside
                    free = [(b.y_ceiling, b.y_floor)]
                    for c in grid_blocks:
                        if c is b or not (c.ox <= px < c.ox + c.ext_x and c.oz <= pz < c.oz + c.ext_z):
                            continue
                        cut = []
                        for top, base in free:
                            if c.y_floor <= top or c.y_ceiling >= base:
                                cut.append((top, base))
                                continue
                            if c.y_ceiling > top:
                                cut.append((top, c.y_ceiling))
                            if c.y_floor < base:
                                cut.append((c.y_floor, base))
                        free = cut
                    intervals = tuple(free)
                if run is not None and intervals != run[1]:
                    for top, base in run[1]:
                        if axis == "x":
                            out.append((fixed, run[0], fixed, pos, top, base, inside))
                        else:
                            out.append((run[0], fixed, pos, fixed, top, base, inside))
                    run = None
                if pos >= a1:
                    break
                if run is None and intervals:
                    run = (pos, intervals)
                pos += SUBCELL
    return out


def jump_ceilings(grid_blocks: list[HeightmapBlock]):
    """Where a jump stops (finding 299, `0x437360`): the top of every slab,
    where the head of a jumping Bugs stops (his origin about 410 lower),
    except the sub-cells where the block just above has no ground (0x7E or
    0x7F: the ground asked for just above the top is not there, and the jump
    goes on into that block). Returns (x0, z0, x1, z1, y) rectangles, the
    sub-cells merged in rows and the equal rows merged."""
    out = []
    for b in grid_blocks:
        w, h = b.ext_x // SUBCELL, b.ext_z // SUBCELL
        above = [c for c in grid_blocks if c is not b and c.y_ceiling < b.y_ceiling <= c.y_floor
                 and c.ox < b.ox + b.ext_x and b.ox < c.ox + c.ext_x
                 and c.oz < b.oz + b.ext_z and b.oz < c.oz + c.ext_z]
        maps = [(c, subcell_map(c)) for c in above]

        def stops(ix, iz):
            x, z = b.ox + ix * SUBCELL + SUBCELL // 2, b.oz + iz * SUBCELL + SUBCELL // 2
            for c, (cw, _ch, m) in maps:
                if c.ox <= x < c.ox + c.ext_x and c.oz <= z < c.oz + c.ext_z:
                    v = m[int((z - c.oz) // SUBCELL) * cw + int((x - c.ox) // SUBCELL)]
                    return v not in NO_GROUND
            return True

        open_rows = {}                      # (x run) -> (z start, last z)
        for iz in range(h + 1):
            runs = set()
            if iz < h:
                ix = 0
                while ix < w:
                    if stops(ix, iz):
                        start = ix
                        while ix < w and stops(ix, iz):
                            ix += 1
                        runs.add((start, ix))
                    else:
                        ix += 1
            for key in list(open_rows):
                if key not in runs:
                    zs, ze = open_rows.pop(key)
                    out.append((b.ox + key[0] * SUBCELL, b.oz + zs * SUBCELL,
                                b.ox + key[1] * SUBCELL, b.oz + (ze + 1) * SUBCELL, b.y_ceiling))
            for key in runs:
                if key in open_rows:
                    open_rows[key] = (open_rows[key][0], iz)
                else:
                    open_rows[key] = (iz, iz)
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
