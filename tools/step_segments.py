"""Every 40-unit piece of edge the steps cover, as a set, for the proof that
nothing disappears when the runs are cut differently.

    .venv/Scripts/python tools/step_segments.py --json FILE [L03A ...]

A run is a stretch of sub-cell edges merged together. Cutting a run where
the ground changes (so the panel follows the floor instead of being the
run's bounding box) changes how many runs there are,
so counting runs proves nothing. What must not change is the **set of
sub-cell edges** the steps cover: one entry per 40 units of edge, with the
side the step stops you from. This dumps that set, level by level, so the
same tool run on the old code and on the new one can be compared piece by
piece.

It also writes the vertical extent of each piece, so the shrinking of the
panels can be measured without guessing.
"""
import json
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

SUB = 40


def one(path):
    from game import collision
    from game import geometry as geo
    from window.scene import Level
    name = os.path.splitext(os.path.basename(path))[0].upper()
    level = Level(path, "extracted", None, None, {}, families=set())
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
    heights = collision.raster_vertical(solid + level._object_faces(diagonal, solid_only=True))
    pieces = {}
    for xa, za, xb, zb, high, low, _vis, (sx, sz), hole in collision.step_walls(level.collision_blocks, heights):
        axis = "x" if xa == xb else "z"
        plane = xa if axis == "x" else za
        a0, a1 = (min(za, zb), max(za, zb)) if axis == "x" else (min(xa, xb), max(xa, xb))
        for a in range(int(a0), int(a1), SUB):
            pieces[f"{axis}|{plane:.0f}|{a}|{sx}|{sz}"] = [round(high), round(low), int(bool(hole))]
    total = sum(v[1] - v[0] for v in pieces.values())
    return name, pieces, total


def main():
    from support import paths
    from window.scene import levels_in
    argv = sys.argv[1:]
    taken = {i + 1 for i, a in enumerate(argv) if a == "--json"}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in taken]
    out_file = argv[argv.index("--json") + 1] if "--json" in argv else None
    files = levels_in(paths.DATA_BZE)
    wanted = {a.upper() for a in args}
    if wanted:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0].upper() in wanted]
    with Pool(min(8, len(files))) as pool:
        rows = pool.map(one, files)
    report = {}
    for name, pieces, total in rows:
        report[name] = pieces
        print(f"{name:10s} {len(pieces):7d} pezzi di bordo, altezza totale dei pannelli {total:9d} unita'")
    print(f"{'total':10s} {sum(len(p) for _n, p, _t in rows):7d} pezzi, "
          f"{sum(t for _n, _p, t in rows):9d} unita'")
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f)
        print("written", out_file)


if __name__ == "__main__":
    main()
