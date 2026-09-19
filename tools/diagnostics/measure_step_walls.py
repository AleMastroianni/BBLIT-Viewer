"""How many walls the Invisible walls flag missed before the step walls:
the steps of more than 100 units between two sub-cells with ground
(finding 298: the wall sweep stops a mover whose next sub-cell has ground
more than 100 units above it), with nothing drawn there.

    .venv/Scripts/python tools/diagnostics/measure_step_walls.py [L03A ...]

The steps are `collision.step_walls` (the same the flag draws): runs of
40-unit sub-cell edges inside each block. A run is "seen" when a visible
near-vertical face (terrain or placed object, as for the hard walls:
collision.raster_vertical, +-2 sub-cells) passes between the two grounds.
Counted apart and never drawn: edges between a ground sub-cell and a 0x7E
one more than 100 units over the slab base (a ledge you fall from).

First run: 12,333 runs, 597 with nothing drawn (525 m)
in 20 levels.

A measure, nothing to pass: it prints the counts and exits with 0.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import collision  # noqa: E402
import export_obj as geo  # noqa: E402
import levels  # noqa: E402
import paths  # noqa: E402
import viewer  # noqa: E402

STEP = collision.TOLERANCE      # 100 units


def run_length(p):
    """A run's length in sub-cells."""
    return (abs(p[2] - p[0]) + abs(p[3] - p[1])) // collision.SUBCELL


def hole_edges(b):
    w, h, m = collision.subcell_map(b)
    n = 0
    for axis in ("x", "z"):
        outer, inner = (w, h) if axis == "x" else (h, w)
        for i in range(1, outer):
            for j in range(inner):
                a, c = (m[j * w + i - 1], m[j * w + i]) if axis == "x" else (m[(i - 1) * w + j], m[i * w + j])
                ga, gc = a not in collision.NO_GROUND, c not in collision.NO_GROUND
                if (ga and c == 0x7E) or (gc and a == 0x7E):
                    if b.y_floor - collision.height_units(b, a if ga else c) > STEP:
                        n += 1
    return n


def main():
    names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
    total = {"edges": 0, "runs": 0, "unseen_edges": 0, "unseen_runs": 0, "holes": 0, "hard": 0, "invisible": 0}
    per_level = []
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
        panels = collision.hard_walls(lv.collision_blocks, vertical_heights)
        row = {"edges": sum(run_length(r) for r in runs), "runs": len(runs),
               "unseen_edges": sum(run_length(r) for r in runs if not r[6]),
               "unseen_runs": sum(1 for r in runs if not r[6]),
               "holes": sum(hole_edges(b) for b in lv.collision_blocks),
               "hard": len(panels), "invisible": sum(1 for p in panels if not p[6])}
        for k in total:
            total[k] += row[k]
        per_level.append((name, row))
        print(f"{name:10s} step edges {row['edges']:6d} in {row['runs']:5d} runs, with nothing drawn "
              f"{row['unseen_edges']:6d} in {row['unseen_runs']:5d} runs; hole edges {row['holes']:5d}; "
              f"hard wall panels {row['hard']:4d}, invisible {row['invisible']:4d}", flush=True)
    print()
    print(f"{len(per_level)} levels with a heightmap")
    print(f"steps of more than {STEP} units: {total['edges']} sub-cell edges in {total['runs']} runs "
          f"({total['edges'] * collision.SUBCELL / geo.UNITS_PER_METER:.0f} m)")
    print(f"  with nothing drawn: {total['unseen_edges']} edges in {total['unseen_runs']} runs "
          f"({total['unseen_edges'] * collision.SUBCELL / geo.UNITS_PER_METER:.0f} m), in "
          f"{sum(1 for _, r in per_level if r['unseen_runs'])} levels")
    print(f"  ground next to a 0x7E hole more than {STEP} over the slab base: {total['holes']} edges (not counted above)")
    print(f"hard wall panels: {total['hard']}, {total['invisible']} of them invisible walls")


if __name__ == "__main__":
    main()
