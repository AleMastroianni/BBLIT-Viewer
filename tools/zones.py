"""The zones (load script block 0x09) that kill the player or respawn
them directly: for the viewer's "Death zones" and "Death floor" flags.

A zone is a box (finding 103): origin (x, y, z), extent
in X and in Z, and in Y from its floor up to "Y limit" higher up (the game's
Y grows downwards; the limit is negative). Its rules (0x33)
carry an effects word at +16 (finding 169):

* 0x200000: the player goes into a series of animations and the lives
  counter drops to zero: death, and you restart from the checkpoint;
* 0x40000000: teleport to the three parameters: a direct respawn at a fixed
  point (the recovery net of L04A2: six zones over the whole floor, all
  towards (7900, -15520, 5000)). Nothing grabs the player in the game: a
  zone kills, hurts, or respawns you.

On the menu levels: 165 zones with 0x200000 in 46 levels, 15 with
teleport in 4, and 9 that hurt (action 0x48, finding 158) in 3. The
rules' conditions are not evaluated: you see where the zone CAN act.

The shape is the game's test (`0x434c70` in this build, finding 290): the
distance from the origin, d = p - origin; Y is tested WITHOUT rotation,
y_limit <= d.y <= 0 (plus the object's own box bottom, left out here);
X and Z after rotating d by the negated angles, M = Rz(-a2) Ry(-a1)
Rx(-a0) (finding 105), 0 <= (M d).x <= extent X and 0 <= (M d).z <= extent Z.
Bit 0 of the first flag word skips the rotation (700 of 1147 zones). Of
the zones that kill, teleport or hurt only two are really rotated, both
around Y: a death zone of L05A4 and a damage zone of L02A4.
"""

from __future__ import annotations

import math

DEATH = 0x200000
TELEPORT = 0x40000000
# a zone covering at least this fraction of the ground's plan is the
# level's "death floor" (the sea of L03A, the abyss of L05A5)
FLOOR_FRACTION = 0.5


def kind_of(z: dict) -> str | None:
    """"death" or "teleport" or None."""
    effects = 0
    for r in z.get("rules", []):
        effects |= r["effect"]
    if effects & DEATH:
        return "death"
    if effects & TELEPORT:
        return "teleport"
    return None


DAMAGE = 0x48      # action: damage (finding 158)
NO_ROTATION = 1    # bit 0 of the first flag word: the test ignores the rotation


def hurts(z: dict) -> bool:
    """Whether a rule of the zone runs the damage action (0x48)."""
    return any(r["action"][0] == DAMAGE for r in z.get("rules", []))


def _matrix(angles):
    """M = Rz(-a2) Ry(-a1) Rx(-a0), 4096 = one turn, with the signs of the
    game's RotMatrixX/Y/Z (BugsDecomp gte.c): what the test applies to d."""
    a0, a1, a2 = (-a * 2 * math.pi / 4096.0 for a in angles)
    cx, sx, cy, sy, cz, sz = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1), math.cos(a2), math.sin(a2)
    rx = ((1, 0, 0), (0, cx, -sx), (0, sx, cx))
    ry = ((cy, 0, sy), (0, 1, 0), (-sy, 0, cy))
    rz = ((cz, -sz, 0), (sz, cz, 0), (0, 0, 1))

    def mul(a, b):
        return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))

    return mul(rz, mul(ry, rx))


class ZoneShape:
    """Where a zone acts, in game coordinates: between two horizontal
    planes, and in plan a rectangle turned by the rotation (a slanted
    prism if the rotation is not only around Y)."""

    def __init__(self, z: dict):
        self.origin = z["origin"]
        ex, y_limit, ez, _radius = z["size"]
        self.ex, self.ez = ex, ez
        self.dy0, self.dy1 = min(0, y_limit), max(0, y_limit)
        angles = [a % 4096 for a in (z.get("rotation") or (0, 0, 0))]
        rotated = any(angles) and not (z.get("flags", [0])[0] & NO_ROTATION)
        self.m = _matrix(angles) if rotated else None

    @property
    def area(self) -> float:
        return float(self.ex) * self.ez

    def _d_at(self, lx, dy, lz):
        """The d with (M d).x = lx, (M d).z = lz at height dy."""
        if self.m is None:
            return lx, dy, lz
        m = self.m
        # [[m00, m02], [m20, m22]] (dx, dz) = (lx - m01 dy, lz - m21 dy)
        det = m[0][0] * m[2][2] - m[0][2] * m[2][0]
        bx, bz = lx - m[0][1] * dy, lz - m[2][1] * dy
        return (bx * m[2][2] - m[0][2] * bz) / det, dy, (m[0][0] * bz - m[2][0] * bx) / det

    def corners(self):
        """The 8 corners, index 4*ix + 2*iy + iz (as viewer._add_box)."""
        ox, oy, oz = self.origin
        output = []
        for lx in (0, self.ex):
            for dy in (self.dy0, self.dy1):
                for lz in (0, self.ez):
                    dx, dy_, dz = self._d_at(lx, dy, lz)
                    output.append((ox + dx, oy + dy_, oz + dz))
        return output

    def vertical_span(self, x, z):
        """The (top, bottom) Y of the vertical line at (x, z) inside the
        zone (Y down: top < bottom), or None if the line misses it."""
        ox, oy, oz = self.origin
        dx, dz = x - ox, z - oz
        lo, hi = self.dy0, self.dy1
        if self.m is None:
            if not (0 <= dx <= self.ex and 0 <= dz <= self.ez):
                return None
            return oy + lo, oy + hi
        # (M d).x = m00 dx + m01 dy + m02 dz, linear in dy: clip [lo, hi]
        for row, extent in ((self.m[0], self.ex), (self.m[2], self.ez)):
            a, b = row[1], row[0] * dx + row[2] * dz
            if abs(a) < 1e-12:
                if not (0 <= b <= extent):
                    return None
                continue
            t0, t1 = (0 - b) / a, (extent - b) / a
            lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if lo > hi:
                return None
        return oy + lo, oy + hi


def shape_of(z: dict) -> ZoneShape | None:
    """The zone's shape, or None if it has no origin or size, or has a
    negative extent (a disabled zone: the game's test `0 <= x <= extent`
    never finds it)."""
    if not z.get("origin") or not z.get("size"):
        return None
    ex, _y_limit, ez, _radius = z["size"]
    if ex < 0 or ez < 0:
        return None
    return ZoneShape(z)


def trap_shape(z: dict) -> ZoneShape | None:
    """The shape of a zone that ends a fall badly: it kills, respawns you
    directly (teleport) or hurts (action 0x48). None otherwise. Used by the
    no-collision flag: falling into one of these is not a safe fall."""
    if kind_of(z) or hurts(z):
        return shape_of(z)
    return None
