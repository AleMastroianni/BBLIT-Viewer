"""How many step walls the Invisible walls flag shows: the steps of more
than 100 units (findings 298, 309: the wall sweep stops a mover entering a
sub-cell whose ground is more than 100 units above it), with nothing drawn
there.

    .venv/Scripts/python tools/measure_step_walls.py [L03A ...]

The steps are `collision.step_walls` (the same the flag draws): runs of
40-unit sub-cell edges inside each block, between two ground sub-cells, or
between a ground sub-cell and a 0x7E hole (the hole counts as the slab's
base: always the low side), counted apart. A run is "seen" when a visible
near-vertical face (terrain or placed object, as for the hard walls:
collision.raster_vertical, +-2 sub-cells) passes between the two grounds.

First run, ground to ground only: 12,333 runs, 597 with nothing drawn
(525 m) in 20 levels.

A measure, nothing to pass: it prints the counts and exits with 0.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from support import paths  # noqa: E402
import viewer  # noqa: E402

STEP = collision.TOLERANCE      # 100 units


def run_length(p):
    """A run's length in sub-cells."""
    return (abs(p[2] - p[0]) + abs(p[3] - p[1])) // collision.SUBCELL


def main():
    names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
    keys = ("edges", "runs", "unseen_edges", "unseen_runs")
    total = {kind: dict.fromkeys(keys, 0) for kind in ("ground", "hole")}
    unseen_levels = {"ground": 0, "hole": 0}
    for name in names:
        file_path = os.path.join(paths.DATA_BZE, name + ".bze")
        if not os.path.exists(file_path):
            continue
        lv = viewer.Level(file_path, "extracted", None, None, {}, families=())
        if not lv.collision_blocks:
            continue
        face_list = []
        for t in lv.lvl["terrain"]:
            try:
                vs, vl_, _ = geo.read_terrain(lv.sec4, t["offset"])
            except Exception:  # noqa: BLE001
                continue
            sp = t["translation"]
            face_list += [[tuple(vs[hh][k] + sp[k] for k in range(3)) for hh in vl.corners] for vl in vl_]
        diagonal = max(hi - lo for hi, lo in zip(lv.terrain_hi, lv.terrain_lo)) or 1.0
        vertical_heights = collision.raster_vertical(face_list + lv._object_faces(diagonal))
        runs = collision.step_walls(lv.collision_blocks, vertical_heights)
        text = []
        for kind, hole in (("ground", False), ("hole", True)):
            mine = [r for r in runs if r[8] == hole]
            row = {"edges": sum(run_length(r) for r in mine), "runs": len(mine),
                   "unseen_edges": sum(run_length(r) for r in mine if not r[6]),
                   "unseen_runs": sum(1 for r in mine if not r[6])}
            for k in keys:
                total[kind][k] += row[k]
            unseen_levels[kind] += row["unseen_runs"] > 0
            text.append(f"{kind} {row['runs']:5d} runs, {row['unseen_runs']:4d} with nothing drawn")
        print(f"{name:10s} " + "; ".join(text), flush=True)
    print()
    for kind, what in (("ground", "between two ground sub-cells"), ("hole", "from a 0x7E hole (its low side)")):
        t = total[kind]
        print(f"steps {what}: {t['edges']} sub-cell edges in {t['runs']} runs "
              f"({t['edges'] * collision.SUBCELL / geo.UNITS_PER_METER:.0f} m); with nothing drawn "
              f"{t['unseen_edges']} edges in {t['unseen_runs']} runs "
              f"({t['unseen_edges'] * collision.SUBCELL / geo.UNITS_PER_METER:.0f} m) in {unseen_levels[kind]} levels")


if __name__ == "__main__":
    main()
