"""The walls of the collision heightmap drawn on the game's own faces.

A wall run (collision.hard_walls, collision.step_walls) is a vertical
rectangle on a sub-cell edge: an axis-aligned plane (x = const or z =
const), a stretch along the other axis and a band of heights. Where the
game draws a face ON that plane -- a crate's side, a house wall -- the flag
colours that face, clipped to the run (a face going over the ceiling of the
block is cut there), with its own edges, instead of a panel over it that
fights it for depth and flickers (the rule here: the flags colour the faces
that are there; new geometry only where the game draws nothing). The
parts of the run no such face covers get a panel, and one outline around
the whole uncovered region instead of an edge per run, or many short runs
made a curtain of black lines.

Everything here is in game units and game coordinates (Y down). A face is
"on" the plane when it **stands up** (its normal near the horizontal: a
floor or a ramp crossing the strip is not a wall's face), **faces the
wall's axis** at least FACING, and comes within PLANE_TOLERANCE of the
plane: the collision edges lie on the 40-unit grid, the modelled face a
little off it (measured on the disc: within one sub-cell in nearly every
case, and the few farther ones are walls the game puts well before the
face, which are the panel's to show).

**A face does not have to be parallel to the plane.** It used to: with the
old `PARALLEL = 0.95` a wall drawn at 45
degrees (0.707) was thrown out, so along every diagonal wall on the disc
the flag could never colour the face that is there and fell back on the
collision staircase -- 40-unit runs alternating between x-planes and
z-planes. Seen along one of the two axes the perpendicular half of that
staircase is edge on, a sliver one or two pixels wide right on the joint
between two panels, and since a flag's fill writes no depth its alpha adds
to the panel behind: a bright line every 40 units (`reference/changes/
29_wall_stripes`). Colouring the slanted face the game really draws
removes the staircase and the lines with it.

A face that is not parallel is kept with the distance from the plane at
each of its corners (the third number of a point here, `(along, y, d)`),
so it is drawn where it really is and not flattened onto the plane.
"""

from __future__ import annotations

from game.collision import SUBCELL

# a face this far from the wall's plane (either side) is the wall's face
PLANE_TOLERANCE = 48
# a face is flat (one plane) when its vertices stay within this of it
FLATNESS = 8
# the face has to stand up: its normal no further than this from the
# horizontal, about 20 degrees off vertical. A floor, a ramp or a ceiling
# crossing the strip is not the wall's face
UPRIGHT = 0.35
# and it has to face the wall's axis at least this much (cosine): 1 is
# parallel to the plane, 0.5 is 60 degrees off it, which takes a wall drawn
# at 45 degrees (0.707) and leaves out a face perpendicular to the wall,
# which would project onto the plane as a line
FACING = 0.5
# the coverage grid: the sub-cell, both along the wall and in height
CELL = SUBCELL
EPS = 0.5


def _normal(p):
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    return None if ln == 0 else (n[0] / ln, n[1] / ln, n[2] / ln)


def _ring(points):
    """A face's corners round its outline: a PlayStation quad is Z-ordered
    (0, 1, 3, 2 round), a triangle or anything else is taken in order."""
    return [points[0], points[1], points[3], points[2]] if len(points) == 4 else list(points)


class ParallelFaces:
    """The game's solid upright faces, filed under every sub-cell they reach
    along each axis, so the faces near a run are found without a scan of
    them all. A face is filed under an axis when it faces that axis at
    least FACING: a wall drawn at 45 degrees is filed under both, and gets
    coloured for the runs of both halves of the collision staircase."""

    def __init__(self, faces):
        self.by_key = {}
        self.count = 0
        for p in faces:
            n = _normal(p)
            if n is None or abs(n[1]) > UPRIGHT:
                continue
            ring = _ring(p)
            plane_d = n[0] * ring[0][0] + n[1] * ring[0][1] + n[2] * ring[0][2]
            if max(abs(n[0] * q[0] + n[1] * q[1] + n[2] * q[2] - plane_d) for q in ring) > FLATNESS:
                continue        # not one plane: nothing to colour
            self.count += 1
            for axis, c in (("x", 0), ("z", 2)):
                if abs(n[c]) < FACING:
                    continue
                lo = min(q[c] for q in ring) - PLANE_TOLERANCE
                hi = max(q[c] for q in ring) + PLANE_TOLERANCE
                for k in range(int(lo // CELL), int(hi // CELL) + 1):
                    self.by_key.setdefault((axis, k), []).append(ring)

    def near(self, axis, plane):
        """The faces that come within PLANE_TOLERANCE of `plane`, each as a
        polygon of (along, y, distance from the plane): the distance is per
        corner, so a face that is not parallel keeps its slant."""
        c = 0 if axis == "x" else 2
        a = 2 if axis == "x" else 0
        out = []
        for ring in self.by_key.get((axis, int(plane // CELL)), ()):
            poly = [(q[a], q[1], q[c] - plane) for q in ring]
            if min(abs(q[2]) for q in poly) <= PLANE_TOLERANCE:
                out.append(poly)
        return out


def area(poly):
    return sum(poly[i - 1][0] * p[1] - p[0] * poly[i - 1][1] for i, p in enumerate(poly)) / 2.0


def clip(poly, a0, a1, y0, y1):
    """A convex polygon in (along, y, ...), clipped to the rectangle
    [a0, a1] x [y0, y1] (Sutherland-Hodgman); [] when nothing is left. Any
    further numbers a point carries (the distance from the wall's plane)
    are interpolated with it, so a slanted face keeps its slant."""
    def cut(points, inside, cross):
        out = []
        for i, p in enumerate(points):
            q = points[i - 1]
            pin, qin = inside(p), inside(q)
            if pin:
                if not qin:
                    out.append(cross(q, p))
                out.append(p)
            elif qin:
                out.append(cross(q, p))
        return out

    def crossing(coord, value):
        def f(q, p):
            t = (value - q[coord]) / (p[coord] - q[coord])
            return tuple(q[i] + t * (p[i] - q[i]) for i in range(len(q)))
        return f

    points = list(poly)
    for coord, value, keep_greater in ((0, a0, True), (0, a1, False), (1, y0, True), (1, y1, False)):
        if not points:
            break
        inside = ((lambda p, v=value, c=coord: p[c] >= v - EPS) if keep_greater
                  else (lambda p, v=value, c=coord: p[c] <= v + EPS))
        points = cut(points, inside, crossing(coord, value))
    # drop the points the clipping doubled
    cleaned = []
    for p in points:
        if not cleaned or abs(p[0] - cleaned[-1][0]) > EPS or abs(p[1] - cleaned[-1][1]) > EPS:
            cleaned.append(p)
    if len(cleaned) > 1 and abs(cleaned[0][0] - cleaned[-1][0]) <= EPS and abs(cleaned[0][1] - cleaned[-1][1]) <= EPS:
        cleaned.pop()
    return cleaned if len(cleaned) >= 3 and abs(area(cleaned)) > EPS else []


def contains(poly, point):
    """Whether a polygon holds the point, by crossing number.

    It used to ask the polygon to be CONVEX and take the sign of the cross
    product round it. A clipped piece is not always convex: the game's quads
    are not all flat-convex once projected, and the clipping then leaves a
    spike. Where that happened the answer was "outside" for points that are
    inside, so a cell under a face was read as uncovered and got a panel on
    top of the coloured face (9 of them in Hey... What's up, Dock? 1). For a
    convex polygon this gives exactly the same answer."""
    x, y = point[0], point[1]
    inside = False
    for i, p in enumerate(poly):
        q = poly[i - 1]
        if (q[1] > y) != (p[1] > y):
            t = (y - q[1]) / (p[1] - q[1])
            if x < q[0] + t * (p[0] - q[0]):
                inside = not inside
    return inside


def is_rectangle(poly):
    """Whether the polygon is (nearly) its own bounding rectangle."""
    a0, a1 = min(p[0] for p in poly), max(p[0] for p in poly)
    y0, y1 = min(p[1] for p in poly), max(p[1] for p in poly)
    box = (a1 - a0) * (y1 - y0)
    return box > 0 and abs(area(poly)) >= 0.9 * box


class WallCover:
    """The coverage of the runs on one plane and one side (the runs of one
    hard-wall block, or the steps of one kind): which sub-cells of each run
    the game's faces cover, the panels for the rest and one outline round
    the uncovered region."""

    def __init__(self, axis, plane, runs, parallel, free=None):
        """`runs`: (a0, a1, y_top, y_base, key) in game units, y_top < y_base
        (Y down), `key` whatever tells the runs apart for the caller (their
        visibility). `parallel`: a ParallelFaces. `free`: +1 or -1, which
        way along the plane's axis the side the wall stops you from lies;
        None leaves that test out."""
        self.axis, self.plane = axis, plane
        self.runs = runs
        self.faces = parallel.near(axis, plane)
        candidates = []         # (run index, polygon (along, y, distance from the plane))
        for poly in self.faces:
            for r, (a0, a1, top, base, _key) in enumerate(runs):
                piece = clip(poly, a0, a1, top, base)
                # the piece has to stay near the plane over the whole run:
                # a slanted face drifts away from it, and past the tolerance
                # it is another wall's face, not this one's
                if not piece or max(abs(q[2]) for q in piece) > PLANE_TOLERANCE:
                    continue
                # and it has to be on the side you walk, the free side.
                # Measured on the PIECE, not on the whole face: a long
                # slanted wall would otherwise be judged by a corner of
                # itself that lies somewhere else. WHICH WAY the face looks
                # cannot be used: only 0.8% of the attributions have the
                # normal on the free side, so the game does not wind its
                # faces that way
                if free is not None:
                    d_mid = sum(q[2] for q in piece) / len(piece)
                    if d_mid * free < -CELL:
                        continue
                candidates.append((r, piece))
        # the rows: the sub-cell grid where a face may cover part of a run;
        # with no face near, each run is one row, so a wall 160 sub-cells
        # tall does not cost 160 rows of cells for nothing
        self.cells = {}         # (i, j) -> run index; i along the wall, j the row
        self.rows = {}          # (i, j) -> (y_low, y_high) of the cell (Y down: y_high < y_low)
        fine = bool(candidates)
        for r, (a0, a1, top, base, _key) in enumerate(runs):
            i0, i1 = int(round(a0 / CELL)), int(round(a1 / CELL))
            if fine:
                j0, j1 = int(top // CELL), int((base - EPS) // CELL) + 1
                for j in range(j0, j1):
                    y_high, y_low = max(top, j * CELL), min(base, (j + 1) * CELL)
                    if y_low <= y_high:
                        continue
                    for i in range(i0, i1):
                        self.cells[(i, j)] = r
                        self.rows[(i, j)] = (y_low, y_high)
            else:
                for i in range(i0, i1):
                    self.cells[(i, r)] = r
                    self.rows[(i, r)] = (base, top)
        self.covered = set()
        self.clipped = []
        for r, piece in candidates:
            # a cell is covered when the face holds its middle. It used to
            # take all four corners, which a face crossing the strip on the
            # slant almost never does: the face was coloured AND a panel was
            # drawn over the same place, twice the geometry and two tints on
            # one pixel. The middle is what says "the face is here"
            lo_a, hi_a = min(p[0] for p in piece), max(p[0] for p in piece)
            lo_y, hi_y = min(p[1] for p in piece), max(p[1] for p in piece)
            mine = []
            for i in range(int(lo_a // CELL), int((hi_a - EPS) // CELL) + 1):
                for j in range(int(lo_y // CELL), int((hi_y - EPS) // CELL) + 1):
                    if self.cells.get((i, j)) != r:
                        continue
                    y_low, y_high = self.rows[(i, j)]
                    if contains(piece, ((i + 0.5) * CELL, (y_low + y_high) / 2.0)):
                        mine.append((i, j))
            # a piece that holds not one cell of its run is drawn and claims
            # nothing: it takes no panel away and only adds a tint where the
            # face happens to graze the strip. Out (on the census of
            # Hey... What's up, Dock? 1)
            if not mine:
                continue
            self.clipped.append((r, piece))
            self.covered.update(mine)

    def _chosen(self, wanted):
        return {c for c, r in self.cells.items() if c not in self.covered
                and (wanted is None or wanted(self.runs[r][4]))}

    def panels(self, wanted=None):
        """The uncovered cells as rectangles (a0, a1, y_top, y_base), merged
        along the wall and equal stretches stacked when their rows touch;
        `wanted(key)` keeps only the runs whose key it accepts."""
        chosen = self._chosen(wanted)
        spans = {}              # row -> [(i0, i1)]
        for j in {j for _i, j in chosen}:
            cols = sorted(i for i, jj in chosen if jj == j)
            row_spans, start, last = [], cols[0], cols[0]
            for i in cols[1:]:
                if i == last + 1:
                    last = i
                else:
                    row_spans.append((start, last + 1))
                    start = last = i
            row_spans.append((start, last + 1))
            spans[j] = row_spans
        out = []
        done = set()
        # from the lowest row up (Y down: the largest y_low first)
        for j in sorted(spans, key=lambda jj: -self.rows[(spans[jj][0][0], jj)][0]):
            for span in spans[j]:
                if (span, j) in done:
                    continue
                done.add((span, j))
                y_base, y_top = self.rows[(span[0], j)]
                # stack the same span from the rows above while they touch
                while True:
                    above = next((jj for jj in spans if (span, jj) not in done and span in spans[jj]
                                  and abs(self.rows[(span[0], jj)][0] - y_top) <= EPS), None)
                    if above is None:
                        break
                    done.add((span, above))
                    y_top = self.rows[(span[0], above)][1]
                out.append((span[0] * CELL, span[1] * CELL, y_top, y_base))
        return out

    def outline(self, wanted=None):
        """The boundary of the uncovered region, as segments ((a, y), (a, y))
        merged where they run on: the sides of the cells whose neighbour is
        covered, out of the region or nothing."""
        chosen = self._chosen(wanted)
        # a cell's neighbours, by the places its sides are at (coarse rows
        # are one per run, so a side is matched by its coordinates)
        horizontal, vertical = {}, {}       # (y, a0) -> a1 ; (a, y0) -> y1
        sides_h, sides_v = {}, {}           # (y, a0, a1) count ; (a, y0, y1) count
        for i, j in chosen:
            x0, x1 = i * CELL, (i + 1) * CELL
            y_low, y_high = self.rows[(i, j)]
            sides_h[(y_low, x0, x1)] = sides_h.get((y_low, x0, x1), 0) + 1
            sides_h[(y_high, x0, x1)] = sides_h.get((y_high, x0, x1), 0) + 1
            sides_v[(x0, y_high, y_low)] = sides_v.get((x0, y_high, y_low), 0) + 1
            sides_v[(x1, y_high, y_low)] = sides_v.get((x1, y_high, y_low), 0) + 1
        # a side two cells share is inside the region; the others are the boundary
        for (y, x0, x1), n in sides_h.items():
            if n == 1:
                horizontal[(y, x0)] = x1
        for (x, y0, y1), n in sides_v.items():
            if n == 1:
                vertical[(x, y0)] = y1
        segments = []
        for table, along in ((horizontal, True), (vertical, False)):
            used = set()
            for start in sorted(table):
                if start in used:
                    continue
                fixed, a = start
                end = table[start]
                used.add(start)
                while (fixed, end) in table and (fixed, end) not in used:
                    used.add((fixed, end))
                    end = table[(fixed, end)]
                segments.append(((a, fixed), (end, fixed)) if along else ((fixed, a), (fixed, end)))
        return segments

    def face_pieces(self, wanted=None):
        """The game's faces on the runs, clipped to them: (polygon
        (along, y, distance from the plane), run key)."""
        return [(piece, self.runs[r][4]) for r, piece in self.clipped
                if wanted is None or wanted(self.runs[r][4])]

    def to_3d(self, point, off=0.0):
        """A point (along, y) of this plane back into game coordinates,
        `off` along the plane's axis. A point that carries its own distance
        from the plane (a piece of a face) uses that instead."""
        a, y = point[0], point[1]
        if len(point) > 2:
            off = point[2]
        return (self.plane + off, y, a) if self.axis == "x" else (a, y, self.plane + off)
