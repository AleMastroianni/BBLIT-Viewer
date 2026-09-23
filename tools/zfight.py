"""On the whole disc: where the flags can still fight the depth buffer.

Z-fighting was still showing somewhere after the depth work. This counts,
level by level, the two cases it can come from:

* a flag's face **in the same plane as a face of the game** while its group
  has **no depth offset** (`overlays.PULLED_FORWARD`): the two surfaces then
  take turns, pixel by pixel, from one frame to the next;
* a flag's **fill over another flag's fill**: two overlays in the same place,
  which fight each other the same way and also double the tint.

    .venv/Scripts/python tools/zfight.py [L03A ...] [--json FILE] [--all]

How it measures. Every group of a built level is read back as triangles in
world coordinates (the same buffers the viewer draws) and filed by its
plane: the unit normal, turned to a canonical side, quantised to about two
degrees, and the distance from the origin. Two triangles can only fight if
their planes agree, so only the triangles in the matching normal buckets are
compared, and only those whose distances are within NEAR; then a separating
axis test on the plane says whether they really cover each other.

* |gap| <= SAME (1 unit): **same plane** -- it fights at any distance;
* |gap| <= NEAR (8 units): **near** -- far from the camera the depth buffer
  cannot tell them apart any more (0.1 m near plane, 24-bit depth: about 3
  units at 200 m).

Surfaces that CROSS each other (different planes, like the heightmap's flat
sub-cells over the game's smooth slopes) are not this tool's job: they are
counted, cell by cell, by `tools/ground_split.py`.

Groups WITH a depth offset are listed too, with `--all`, so the lists say
what the offset already covers and what it does not.
"""
import json
import os
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

# a group's buffer is in the viewer's metres (128 game units = 1 m), so the
# thresholds, written in game units, are turned into metres here: reading
# them as metres made every plane within 128 units "the same plane"
UNITS_PER_METER = 128.0
SAME = 1.0 / UNITS_PER_METER     # game units: the same plane
NEAR = 8.0 / UNITS_PER_METER     # game units: near enough to fight at a distance
QUANT = 32.0      # the normal's quantisation (1 step is about 1.8 degrees)
FLOATS = 8        # floats per vertex in a group's buffer (pos, colour, uv)
WALL_PREFIXES = ("hard_walls", "invisible_walls", "step_walls", "hole_steps")


def _triangles(group):
    """A group's triangles as ((x, y, z) x 3), in world coordinates."""
    data = group.data
    return [(tuple(data[i:i + 3]), tuple(data[i + FLOATS:i + FLOATS + 3]),
             tuple(data[i + 2 * FLOATS:i + 2 * FLOATS + 3]))
            for i in range(0, len(data), FLOATS * 3)]


def _plane(t):
    """The triangle's plane as (normal, distance), the normal turned to a
    canonical side so that a face and its twin drawn the other way round
    land in the same bucket."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = (nx * nx + ny * ny + nz * nz) ** 0.5
    if ln < 1e-9:
        return None
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    for c in (nx, ny, nz):
        if abs(c) > 1e-6:
            if c < 0:
                nx, ny, nz = -nx, -ny, -nz
            break
    return (nx, ny, nz), nx * ax + ny * ay + nz * az


def _key(n):
    return (int(round(n[0] * QUANT)), int(round(n[1] * QUANT)), int(round(n[2] * QUANT)))


def _flat(tri, n):
    """The triangle's corners on the plane's two best axes."""
    ax = max(range(3), key=lambda k: abs(n[k]))
    u, v = (1, 2) if ax == 0 else ((0, 2) if ax == 1 else (0, 1))
    return [(p[u], p[v]) for p in tri]


def _overlap(p, q):
    """Do two triangles on the same plane cover each other? Separating axis
    on the six edge normals; touching at an edge does not count."""
    for tri in (p, q):
        for i in range(3):
            (x0, y0), (x1, y1) = tri[i], tri[(i + 1) % 3]
            ax, ay = -(y1 - y0), x1 - x0
            pa = [ax * x + ay * y for x, y in p]
            qa = [ax * x + ay * y for x, y in q]
            if min(pa) >= max(qa) - 1e-6 or min(qa) >= max(pa) - 1e-6:
                return False
    return True


class Planes:
    """Triangles filed by plane: normal bucket -> distances sorted, with the
    triangle and the group it comes from."""

    def __init__(self, items):
        self.buckets = defaultdict(list)
        for tri, tag in items:
            pl = _plane(tri)
            if pl is None:
                continue
            n, d = pl
            self.buckets[_key(n)].append((d, _flat(tri, n), tag))
        self.sorted = {}
        for key, rows in self.buckets.items():
            rows.sort(key=lambda r: r[0])
            self.sorted[key] = ([r[0] for r in rows], rows)

    def against(self, tri, skip_tag=None):
        """The smallest |gap| to a triangle of another surface that really
        covers this one, and the group it belongs to; None if there is
        none."""
        pl = _plane(tri)
        if pl is None:
            return None
        n, d = pl
        flat = _flat(tri, n)
        kx, ky, kz = _key(n)
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    hit = self.sorted.get((kx + dx, ky + dy, kz + dz))
                    if hit is None:
                        continue
                    keys, rows = hit
                    for i in range(bisect_left(keys, d - NEAR), bisect_right(keys, d + NEAR)):
                        od, oflat, tag = rows[i]
                        if tag == skip_tag:
                            continue
                        gap = abs(od - d)
                        if best is not None and gap >= best[0]:
                            continue
                        if _overlap(flat, oflat):
                            best = (gap, tag)
        return best


def one(path):
    from window.overlays import FAMILIES, OVERLAYS, PULLED_FORWARD
    from window.scene import Level
    name = os.path.splitext(os.path.basename(path))[0].upper()
    lvl = Level(path, "extracted", None, None, {}, families=set(FAMILIES))
    game, overlay = [], []
    for group in lvl.face_groups.values():
        if group.mover is not None:
            # its triangles are around the object's own origin: the
            # simulation places them when drawing, not here
            continue
        cat = group.category
        tris = _triangles(group)
        if cat in OVERLAYS or any(cat.startswith(p) for p in WALL_PREFIXES):
            if cat.endswith("_lines"):
                continue          # drawn as edges, not a surface
            overlay.append((cat, tris))
        elif cat != "sky_dome":
            game += [(t, cat) for t in tris]
    field = Planes(game)
    fills = [(cat, tris) for cat, tris in overlay if not cat.endswith("_label")]
    flag_field = Planes([(t, cat) for cat, tris in fills for t in tris])

    rows = {}
    for cat, tris in overlay:
        counts = dict(same=0, near=0, faces=len(tris), pulled=cat in PULLED_FORWARD)
        for tri in tris:
            hit = field.against(tri)
            if hit is None:
                continue
            if hit[0] <= SAME:
                counts["same"] += 1
            elif hit[0] <= NEAR:
                counts["near"] += 1
        if counts["same"] or counts["near"]:
            rows[cat] = counts

    pairs = defaultdict(int)
    for cat, tris in fills:
        for tri in tris:
            hit = flag_field.against(tri, skip_tag=cat)
            if hit is not None and not _twins(cat, hit[1]):
                pairs[tuple(sorted((cat, hit[1])))] += 1
    return name, rows, {f"{a} + {b}": v for (a, b), v in pairs.items()}


def _twins(a, b):
    """A group and its `_outside` twin are the same quad seen from the two
    sides, and only one of them is ever drawn (ONE_SIDED): not an overlap."""
    return a + "_outside" == b or b + "_outside" == a


def main():
    from support import paths
    from window.scene import levels_in
    show_all = "--all" in sys.argv
    out_file = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != out_file]
    files = levels_in(paths.DATA_BZE)
    wanted = {a.upper() for a in args}
    if wanted:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0].upper() in wanted]
    with Pool(min(8, len(files))) as pool:
        result = pool.map(one, files)
    report, totals = {}, defaultdict(lambda: [0, 0])
    pair_totals = defaultdict(int)
    for name, rows, pairs in result:
        report[name] = {"groups": rows, "pairs": pairs}
        bad = {c: r for c, r in rows.items() if show_all or not r["pulled"]}
        for cat, r in rows.items():
            if not r["pulled"]:
                totals[cat][0] += r["same"]
                totals[cat][1] += r["near"]
        for key, n in pairs.items():
            pair_totals[key] += n
        if bad or pairs:
            print(f"== {name}")
            for cat, r in sorted(bad.items(), key=lambda kv: -kv[1]["same"]):
                mark = "offset" if r["pulled"] else "NO offset"
                print(f"   {cat:34s} faces {r['faces']:6d}  same {r['same']:6d}  near {r['near']:6d}  {mark}")
            for key, n in sorted(pairs.items(), key=lambda kv: -kv[1]):
                print(f"   fill over fill  {key:56s} {n:6d}")
    print("\n== whole disc, groups with no depth offset")
    for cat, (same, near) in sorted(totals.items(), key=lambda kv: -kv[1][0]):
        print(f"   {cat:34s} same {same:7d}  near {near:7d}")
    print("== whole disc, fill over fill")
    for key, n in sorted(pair_totals.items(), key=lambda kv: -kv[1]):
        print(f"   {key:56s} {n:7d}")
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print("written", out_file)


if __name__ == "__main__":
    main()
