"""Every game face a wall flag colours, and how well it belongs to its wall.

    .venv/Scripts/python tools/wall_face_audit.py L03A [--near x,y,z] [--top 40]
    .venv/Scripts/python tools/wall_face_audit.py --all --json FILE

A face does not have to be parallel to the collision plane to be "the
wall's face" (`game/walls.py`): a wall drawn at 45 degrees
used to be thrown out, and the flag fell back on the collision staircase.
The looser rule can also take in a face that only crosses the strip on the
slant and belongs somewhere else -- a walkway showed up tinted STEP WALL
in Hey... What's up, Dock? 1. This lists, for every face attributed to a
run, the four numbers that say whether it really is that wall's face:

* **tilt**: how far the face leans from vertical, in degrees (the rule
  takes up to about 20; 0 is a wall, 90 would be a floor);
* **off**: the angle between the face and the wall's plane, in degrees
  (0 = parallel, what the old rule demanded; over 18.2 the face is one the
  old rule threw out -- marked `new`);
* **in**: how much of the face falls inside the run's strip, as a
  percentage of the whole face. A face that touches the strip sideways and
  lies elsewhere has a small number here;
* **free**: whether the face looks toward the side the wall stops you from.
  A face looking the other way is somebody else's wall.

The suspicion score is written out so the list can be read: looking the
wrong way counts most, then how little of the face is in the strip, then
the slant. Nothing here changes what the viewer draws: it is a census.
"""
import json
import math
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

UNITS = 128.0
OLD_PARALLEL_DEGREES = math.degrees(math.acos(0.95))   # 18.19: the old rule


def _normal(p):
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    return None if ln == 0 else (n[0] / ln, n[1] / ln, n[2] / ln)


def _faces_of(level):
    """The solid faces the wall flags look at: the terrain's and the placed
    objects', exactly as `overlays._heightmap` collects them."""
    from game import geometry as geo
    solid = []
    for t in level.lvl["terrain"]:
        try:
            vs, faces, _ = geo.read_terrain(level.sec4, t["offset"])
        except Exception:  # noqa: BLE001
            continue
        sp = t["translation"]
        for vl in faces:
            if vl.blend is None and vl.tex_id not in level.cut_outs:
                solid.append([tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners])
    lo, hi = level.terrain_lo, level.terrain_hi
    diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
    return solid, level._object_faces(diagonal, solid_only=True)


def _covers(level, solid, objects):
    """(kind, axis, plane, free, runs) for every cover the viewer builds:
    the hard walls of each block and the steps."""
    from game import collision
    heights = collision.raster_vertical(solid + objects)
    panels = list(dict.fromkeys(collision.hard_walls(level.collision_blocks, heights)))
    sides = {}
    for p in panels:
        sides.setdefault(p[:4] + p[6:7] + p[8:10], set()).add(p[7])
    hard = [p for p in panels if len(sides[p[:4] + p[6:7] + p[8:10]]) == 1]
    out = {}
    for xa, za, xb, zb, base, top, visible, (fx, fz), _g_low, g_high in hard:
        axis = "x" if xa == xb else "z"
        plane = xa if axis == "x" else za
        a0, a1 = (min(za, zb), max(za, zb)) if axis == "x" else (min(xa, xb), max(xa, xb))
        out.setdefault(("HARD WALL", axis, plane, base, top, (fx, fz)), []).append((a0, a1, top, base, visible))
    for xa, za, xb, zb, high, low, visible, (sx, sz), hole in collision.step_walls(level.collision_blocks, heights):
        axis = "x" if xa == xb else "z"
        plane = xa if axis == "x" else za
        a0, a1 = (min(za, zb), max(za, zb)) if axis == "x" else (min(xa, xb), max(xa, xb))
        out.setdefault(("STEP WALL", axis, plane, None, None, (sx, sz)), []).append((a0, a1, high, low, visible))
    return out


def _ring(points):
    return [points[0], points[1], points[3], points[2]] if len(points) == 4 else list(points)


def _holds(poly, point):
    """Whether a polygon holds a point, by crossing number: `walls.contains`
    asks the polygon to be convex, and a clipped piece is not always (the
    game's quads are not all flat-convex once projected), so the census
    would read "no cell" where there is one."""
    x, y = point
    inside = False
    for i, b in enumerate(poly):
        a = poly[i - 1]
        if (a[1] > y) != (b[1] > y):
            t = (y - a[1]) / (b[1] - a[1])
            if x < a[0] + t * (b[0] - a[0]):
                inside = not inside
    return inside


def one(name):
    from game import walls
    from window.scene import Level
    from support import paths
    level = Level(os.path.join(paths.DATA_BZE, name + ".bze"), "extracted", None, None, {}, families=set())
    solid, objects = _faces_of(level)
    every = solid + objects
    # the same index ParallelFaces builds, but keeping the face itself
    index = {}
    upright = 0
    for p in every:
        n = _normal(p)
        if n is None or abs(n[1]) > walls.UPRIGHT:
            continue
        ring = _ring(p)
        d0 = sum(n[k] * ring[0][k] for k in range(3))
        if max(abs(sum(n[k] * q[k] for k in range(3)) - d0) for q in ring) > walls.FLATNESS:
            continue
        upright += 1
        for axis, c in (("x", 0), ("z", 2)):
            if abs(n[c]) < walls.FACING:
                continue
            lo = min(q[c] for q in ring) - walls.PLANE_TOLERANCE
            hi = max(q[c] for q in ring) + walls.PLANE_TOLERANCE
            for k in range(int(lo // walls.CELL), int(hi // walls.CELL) + 1):
                index.setdefault((axis, k), []).append((ring, n))

    rows = []
    for (kind, axis, plane, base, top, free), runs in _covers(level, solid, objects).items():
        c = 0 if axis == "x" else 2
        a = 2 if axis == "x" else 0
        for ring, n in index.get((axis, int(plane // walls.CELL)), ()):
            poly = [(q[a], q[1], q[c] - plane) for q in ring]
            if min(abs(q[2]) for q in poly) > walls.PLANE_TOLERANCE:
                continue
            whole = abs(walls.area(poly))
            if whole <= 0:
                continue
            for a0, a1, y_top, y_base, visible in runs:
                piece = walls.clip(poly, a0, a1, y_top, y_base)
                if not piece or max(abs(q[2]) for q in piece) > walls.PLANE_TOLERANCE:
                    continue
                inside = abs(walls.area(piece)) / whole
                strip = max(1.0, (a1 - a0) * (y_base - y_top))
                fill = abs(walls.area(piece)) / strip
                # the cells of the run whose middle the piece holds: the very
                # test the viewer uses to say "here the face is the wall"
                # (WallCover.covered). A piece that holds none is drawn and
                # claims nothing: it is the noise to cut
                cells = 0
                for i in range(int(a0 // walls.CELL), int((a1 - walls.EPS) // walls.CELL) + 1):
                    for j in range(int(y_top // walls.CELL), int((y_base - walls.EPS) // walls.CELL) + 1):
                        cy_low = min(y_base, (j + 1) * walls.CELL)
                        cy_high = max(y_top, j * walls.CELL)
                        if cy_low <= cy_high:
                            continue
                        if _holds(piece, ((i + 0.5) * walls.CELL, (cy_low + cy_high) / 2.0)):
                            cells += 1
                tilt = math.degrees(math.asin(min(1.0, abs(n[1]))))
                off = math.degrees(math.acos(min(1.0, abs(n[c]))))
                # WHICH WAY THE FACE LOOKS cannot be read from its winding:
                # measured on Hey... What's up, Dock? 1, only 0.8% of the
                # attributions the OLD rule made have the normal on the free
                # side, so the game does not wind its faces that way. What
                # can be read is WHICH SIDE OF THE PLANE the face is on: a
                # wall's face is on the side you walk, the free side
                d_mid = sum(q[2] for q in piece) / len(piece)
                free_c = free[0] if axis == "x" else free[1]
                looks_free = d_mid * free_c >= -walls.FLATNESS
                centre = [sum(q[k] for q in piece) / len(piece) for k in range(3)]
                x, z = ((plane + centre[2], centre[0]) if axis == "x" else (centre[0], plane + centre[2]))
                # how much of the RUN the face covers is what tells a wall's
                # face from one that only grazes the strip: a long slanted
                # wall gives every run a small SHARE OF ITSELF but fills the
                # run, a face crossing sideways fills neither
                score = ((200.0 if cells == 0 else 0.0) + (0.0 if looks_free else 100.0)
                         + off * 2.0 + tilt * 3.0)
                rows.append(dict(kind=kind, axis=axis, plane=plane, a0=a0, a1=a1,
                                 y_top=y_top, y_base=y_base, floor=base, ceiling=top,
                                 visible=bool(visible), free=list(free),
                                 tilt=round(tilt, 1), off=round(off, 1), inside=round(inside, 3),
                                 d_mid=round(d_mid, 1),
                                 fill=round(fill, 3), cells=cells,
                                 looks_free=looks_free, new=off > OLD_PARALLEL_DEGREES,
                                 at=[round(x), round(centre[1]), round(z)], score=round(score, 1)))
    rows.sort(key=lambda r: -r["score"])
    return name, upright, rows


def _line(r):
    ends = (f"x {r['plane']:.0f}, z {r['a0']:.0f}..{r['a1']:.0f}" if r["axis"] == "x"
            else f"z {r['plane']:.0f}, x {r['a0']:.0f}..{r['a1']:.0f}")
    return (f"   {r['score']:7.1f}  {r['kind']:9s} {ends:28s}  y {r['y_base']:.0f}..{r['y_top']:.0f}"
            f"  |  tilt {r['tilt']:4.1f}  off {r['off']:4.1f}  in {r['inside'] * 100:5.1f}%"
            f"  cop {r['fill'] * 100:5.1f}%  celle {r['cells']:3d}"
            f"  lato {'si' if r['looks_free'] else 'NO':2s} d {r['d_mid']:6.1f}  {'new' if r['new'] else '   '}"
            f"  |  a ({r['at'][0]}, {r['at'][1]}, {r['at'][2]})")


def main():
    from support import paths
    from window.scene import levels_in
    argv = sys.argv[1:]
    taken = {i + 1 for i, a in enumerate(argv) if a in ("--json", "--top", "--near")}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in taken]
    out_file = argv[argv.index("--json") + 1] if "--json" in argv else None
    top = int(argv[argv.index("--top") + 1]) if "--top" in argv else 30
    near = ([float(w) for w in argv[argv.index("--near") + 1].split(",")]
            if "--near" in argv else None)
    if "--all" in sys.argv:
        names = [os.path.splitext(os.path.basename(f))[0] for f in levels_in(paths.DATA_BZE)]
        with Pool(8) as pool:
            result = pool.map(one, names)
    else:
        result = [one(n) for n in (args or ["L03A"])]
    report = {}
    for name, upright, rows in result:
        new_rows = [r for r in rows if r["new"]]
        wrong = [r for r in new_rows if not r["looks_free"]]
        empty = [r for r in new_rows if r["cells"] == 0]
        old_empty = [r for r in rows if not r["new"] and r["cells"] == 0]
        report[name] = dict(upright_faces=upright, attributed=len(rows), new=len(new_rows),
                            new_wrong_side=len(wrong), new_no_cell=len(empty),
                            old_no_cell=len(old_empty), rows=rows[:200])
        print(f"== {name}: {upright} facce in piedi, {len(rows)} attribuzioni, "
              f"{len(new_rows)} solo dalla regola nuova ({len(empty)} non tengono nessuna cella, "
              f"{len(wrong)} dalla parte sbagliata del piano); "
              f"con la vecchia regola senza celle: {len(old_empty)} su {len(rows) - len(new_rows)}")
        chosen = rows
        if near:
            chosen = sorted(rows, key=lambda r: sum((r["at"][k] - near[k]) ** 2 for k in range(3)))
            chosen = [r for r in chosen if sum((r["at"][k] - near[k]) ** 2 for k in range(3)) ** 0.5 < 4000]
            chosen.sort(key=lambda r: -r["score"])
            print(f"   (solo entro 31 m da {near[0]:.0f}, {near[1]:.0f}, {near[2]:.0f}: {len(chosen)})")
        for r in chosen[:top]:
            print(_line(r))
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print("written", out_file)


if __name__ == "__main__":
    main()
