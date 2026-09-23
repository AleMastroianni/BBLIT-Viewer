"""Dump, for every level, the wall runs the flags draw: the hard-wall runs
(with their visibility) and the steps as 40-unit edges, as collision.hard_walls
and collision.step_walls give them, without the hard walls' heights (which changed when the
walls went up to the ceiling of their block).

    .venv/Scripts/python tools/wall_runs_dump.py OUT.json [BBLIT_DIR]

`BBLIT_DIR` is the `bblit/` folder of the code to run (by default this
project's): the same script run on an older checkout (a `git worktree` of
the commit before the change) gives the dump to compare with, and
`tools/wall_flag_proof.py` compares two dumps. Written for the proof that
before the flag Invisible walls went, the runs it drew were exactly those of
Hard walls "only the invisible ones" plus Steps, on the whole disc.
"""
import json
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBLIT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(PROJECT_DIR, "bblit")
CACHE = os.path.join(PROJECT_DIR, "extracted")
sys.path.insert(0, BBLIT)


def _key(panel):
    """(xa, za, xb, zb, visible, ground low, ground high): the old code kept
    the heights from the ground in the tuple, the new one the block's and
    the grounds after them."""
    grounds = panel[8:10] if len(panel) > 8 else panel[4:6]
    return panel[:4] + panel[6:7] + tuple(grounds)


def one(path):
    from window.scene import Level
    from game import geometry as geo, collision
    lvl = Level(path, CACHE, None, None, {}, families=set())
    solid = []
    for t in lvl.lvl["terrain"]:
        try:
            vs, vl_, _ = geo.read_terrain(lvl.sec4, t["offset"])
        except Exception:  # noqa: BLE001
            continue
        sp = t["translation"]
        for vl in vl_:
            if vl.blend is None and vl.tex_id not in lvl.cut_outs:
                solid.append([tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners])
    lo, hi = lvl.terrain_lo, lvl.terrain_hi
    diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
    vh = collision.raster_vertical(solid + lvl._object_faces(diagonal, solid_only=True))
    panels = list(dict.fromkeys(collision.hard_walls(lvl.collision_blocks, vh)))
    sides = {}
    for p in panels:
        sides.setdefault(_key(p), set()).add(p[7])
    hard = [p for p in panels if len(sides[_key(p)]) == 1]
    runs = sorted({(p[0], p[1], p[2], p[3], tuple(p[7]), bool(p[6])) for p in hard})
    # the steps as 40-unit edges, not runs: a run splits where the hole
    # flag changes, and the flag's rule changed (collision.grounded), so
    # the runs are compared piece by piece
    steps = set()
    for xa, za, xb, zb, high, low, visible, side, hole in collision.step_walls(lvl.collision_blocks, vh):
        if xa == xb:
            for z in range(min(za, zb), max(za, zb), 40):
                steps.add((xa, z, xa, z + 40, high, low, bool(visible), tuple(side), bool(hole)))
        else:
            for x in range(min(xa, xb), max(xa, xb), 40):
                steps.add((x, za, x + 40, za, high, low, bool(visible), tuple(side), bool(hole)))
    steps = sorted(steps)
    name = os.path.splitext(os.path.basename(path))[0].upper()
    return name, {"hard": runs, "steps": steps}


def main():
    from support import paths
    from window.scene import levels_in
    files = levels_in(paths.DATA_BZE)
    with Pool(8) as pool:
        out = dict(pool.map(one, files))
    with open(sys.argv[1], "w") as f:
        json.dump(out, f)
    print("levels", len(out), "hard runs", sum(len(v["hard"]) for v in out.values()),
          "invisible", sum(1 for v in out.values() for r in v["hard"] if not r[5]),
          "steps", sum(len(v["steps"]) for v in out.values()))


if __name__ == "__main__":
    main()
