"""Which hard wall am I looking at: a ray from a camera, and the walls around it.

    .venv/Scripts/python tools/wall_at.py L03A 10941,-3691,10709 [--look yaw,pitch] [--radius 40]

Everything in game units and game coordinates (Y down, 128 units = 1 m). The
camera is given as the status bar shows it.

With `--look` it casts the ray and prints, in order, every hard-wall run it
goes through: the run's ends, the floor and the ceiling of its block (the
height a hard wall stops you between, finding 309 and the user's three
recordings), whether anything is drawn on it, and where the ray meets it.
Any solid face of the game the ray meets first is printed too, so a wall
behind a crate is not mistaken for one in the open.

Without `--look` it lists every run within `--radius` metres sorted by
distance, with its bearing from the camera and how tall it looks from there
in degrees: a near 12.5 m wall and a far 50 m column are told apart by the
angle they fill, not by their height.
"""
import math
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

UNITS = 128.0


def _runs(level):
    from game import collision
    from game import geometry as geo
    face_list, solid = [], []
    for t in level.lvl["terrain"]:
        try:
            vs, faces, _ = geo.read_terrain(level.sec4, t["offset"])
        except Exception:  # noqa: BLE001
            continue
        sp = t["translation"]
        for vl in faces:
            corners = [tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners]
            face_list.append(corners)
            if vl.blend is None and vl.tex_id not in level.cut_outs:
                solid.append(corners)
    # the same input the viewer uses (overlays._heightmap): the terrain's
    # solid faces AND the placed objects', or a wall a crate hides would
    # come out "invisible" here and "visible" in the viewer
    lo, hi = level.terrain_lo, level.terrain_hi
    diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
    heights = collision.raster_vertical(solid + level._object_faces(diagonal, solid_only=True))
    panels = list(dict.fromkeys(collision.hard_walls(level.collision_blocks, heights)))
    sides = {}
    for p in panels:
        sides.setdefault(p[:4] + p[6:7] + p[8:10], set()).add(p[7])
    return [p for p in panels if len(sides[p[:4] + p[6:7] + p[8:10]]) == 1], solid


def _quad(run):
    """The run's rectangle in game coordinates: (plane axis, plane, a0, a1,
    y_top, y_base)."""
    xa, za, xb, zb, base, top, _vis, _free, _lo, _hi = run
    if xa == xb:
        return "x", xa, min(za, zb), max(za, zb), top, base
    return "z", za, min(xa, xb), max(xa, xb), top, base


def _hit(run, origin, direction):
    """Where the ray meets the run's rectangle, or None."""
    axis, plane, a0, a1, y_top, y_base = _quad(run)
    c = 0 if axis == "x" else 2
    a = 2 if axis == "x" else 0
    if abs(direction[c]) < 1e-9:
        return None
    t = (plane - origin[c]) / direction[c]
    if t <= 0:
        return None
    p = tuple(origin[k] + t * direction[k] for k in range(3))
    if a0 - 0.5 <= p[a] <= a1 + 0.5 and y_top - 0.5 <= p[1] <= y_base + 0.5:
        return t, p
    return None


def _face_hit(face, origin, direction):
    tris = [(face[0], face[1], face[2])] + ([(face[1], face[3], face[2])] if len(face) == 4 else [])
    best = None
    for a, b, c in tris:
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        den = sum(n[k] * direction[k] for k in range(3))
        if abs(den) < 1e-9:
            continue
        t = sum(n[k] * (a[k] - origin[k]) for k in range(3)) / den
        if t <= 0 or (best is not None and t >= best):
            continue
        p = [origin[k] + t * direction[k] for k in range(3)]
        # inside the triangle
        ok = True
        for p0, p1 in ((a, b), (b, c), (c, a)):
            e = [p1[k] - p0[k] for k in range(3)]
            w = [p[k] - p0[k] for k in range(3)]
            cr = (e[1] * w[2] - e[2] * w[1], e[2] * w[0] - e[0] * w[2], e[0] * w[1] - e[1] * w[0])
            if sum(cr[k] * n[k] for k in range(3)) < -1e-6:
                ok = False
                break
        if ok:
            best = t
    return best


def _distance(run, origin):
    """The distance from the camera to the nearest point of the run's
    rectangle, in game units."""
    axis, plane, a0, a1, y_top, y_base = _quad(run)
    c = 0 if axis == "x" else 2
    a = 2 if axis == "x" else 0
    da = min(max(origin[a], a0), a1) - origin[a]
    dy = min(max(origin[1], y_top), y_base) - origin[1]
    dc = plane - origin[c]
    return (da * da + dy * dy + dc * dc) ** 0.5


def _bearing(run, origin):
    axis, plane, a0, a1, y_top, y_base = _quad(run)
    mid_a = (a0 + a1) / 2.0
    x, z = (plane, mid_a) if axis == "x" else (mid_a, plane)
    # the viewer's yaw: x to the right, z mirrored (drawing.py)
    return math.degrees(math.atan2(-(z - origin[2]), x - origin[0])) % 360.0


def main():
    from support import paths
    from window.scene import Level
    name = sys.argv[1]
    origin = tuple(float(w) for w in sys.argv[2].split(","))
    look = None
    if "--look" in sys.argv:
        look = [float(w) for w in sys.argv[sys.argv.index("--look") + 1].split(",")]
    radius = float(sys.argv[sys.argv.index("--radius") + 1]) if "--radius" in sys.argv else 40.0
    level = Level(os.path.join(paths.DATA_BZE, name + ".bze"), "extracted", None, None, {}, families=set())
    runs, solid = _runs(level)
    print(f"{name}: {len(runs)} tratti di muro duro, camera {origin[0]:.0f}, {origin[1]:.0f}, {origin[2]:.0f}")

    def show(run, extra=""):
        axis, plane, a0, a1, y_top, y_base = _quad(run)
        vis = "visibile" if run[6] else "INVISIBILE"
        ends = (f"x {plane:.0f}, z da {a0:.0f} a {a1:.0f}" if axis == "x"
                else f"z {plane:.0f}, x da {a0:.0f} a {a1:.0f}")
        print(f"   {ends}  |  pavimento {y_base:.0f}  soffitto {y_top:.0f}"
              f"  (alto {(y_base - y_top) / UNITS:.1f} m)  |  {vis}{extra}")

    if look is not None:
        j, p = math.radians(look[0]), math.radians(look[1])
        # the viewer's camera in game coordinates: x, -y, -z (drawing.py)
        direction = (math.cos(j) * math.cos(p), -math.sin(p), -math.sin(j) * math.cos(p))
        first_face = min((t for t in (_face_hit(f, origin, direction) for f in solid) if t), default=None)
        met = []
        for run in runs:
            h = _hit(run, origin, direction)
            if h:
                met.append((h[0], h[1], run))
        met.sort()
        print(f"   raggio yaw {look[0]:.1f} pitch {look[1]:.1f} -> direzione "
              f"({direction[0]:.3f}, {direction[1]:.3f}, {direction[2]:.3f})")
        if first_face is not None:
            q = [origin[k] + first_face * direction[k] for k in range(3)]
            print(f"   prima faccia solida del gioco a {first_face / UNITS:.1f} m "
                  f"({q[0]:.0f}, {q[1]:.0f}, {q[2]:.0f})")
        if not met:
            print("   il raggio non incontra nessun muro duro")
        for t, q, run in met:
            behind = " (dietro una faccia del gioco)" if first_face is not None and t > first_face else ""
            show(run, f"  |  colpito a {t / UNITS:.1f} m in ({q[0]:.0f}, {q[1]:.0f}, {q[2]:.0f}){behind}")
        return

    near = sorted(((_distance(r, origin), r) for r in runs), key=lambda kv: kv[0])
    print(f"   tratti entro {radius:.0f} m, dal piu' vicino:")
    for d, run in near:
        if d / UNITS > radius:
            break
        axis, plane, a0, a1, y_top, y_base = _quad(run)
        # how tall it looks from here
        top_angle = math.degrees(math.atan2(origin[1] - y_top, max(1.0, d)))
        base_angle = math.degrees(math.atan2(origin[1] - y_base, max(1.0, d)))
        show(run, f"  |  {d / UNITS:5.1f} m  direzione {_bearing(run, origin):5.1f} gradi"
                  f"  altezza apparente {abs(top_angle - base_angle):4.1f} gradi")


if __name__ == "__main__":
    main()
