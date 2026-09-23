"""The three classes of a collision edge, on the whole disc.

    .venv/Scripts/python tools/step_by_drop.py [L03A ...] [--json FILE]

An edge between two sub-cells of different ground is one of three things,
and the class is decided by the data, not by a byte (after testing in the
game):

* **EDGE** -- the low side is a 0x7E sub-cell over nothing: the rim of a
  floor over the void. The heightmap has no ground on the free side, so what
  the step rule measures there is not a rise between two floors, and the
  class cannot be read from it. It is drawn as thick as the floor really is
  (`collision._edge_bottom`); the user has tested in the game that the
  plank's own edge does stop him;
* **muro (HARD WALL)** -- there is ground on the free side and the rise is
  more than Bugs's jump (`collision.JUMP_HEIGHT`, 383): it just stops him;
* **gradino (STEP WALL)** -- ground on the free side and a rise of 101 to
  383: he clears it with a jump. Under 101 the sweep lets him walk up
  (findings 298 and 309), so no edge is listed at all.

The drop is measured on the run's REAL extent, which follows the floor
sub-cell by sub-cell; it used to be the bounding box of the merged run and
the block's floor, which invented a 12.5 m wall on a 97 cm plank.
"""
import json
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

UNITS = 128.0
JUMP = 383          # game units: how high Bugs gets from standing
BANDS = (100, 200, 383, 600, 1000, 1600, 3200)


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
    rows = dict(runs=0, edge=0, wall=0, step=0, bands=[0] * (len(BANDS) + 1), biggest=0)
    for _xa, _za, _xb, _zb, high, low, _visible, _free, hole in collision.step_walls(level.collision_blocks, heights):
        drop = low - high
        rows["runs"] += 1
        rows["biggest"] = max(rows["biggest"], drop)
        for i, edge in enumerate(BANDS):
            if drop <= edge:
                rows["bands"][i] += 1
                break
        else:
            rows["bands"][-1] += 1
        # the rim of a floor over the void: no ground on the free side, so
        # the rise is not between two floors and neither class fits
        if hole:
            rows["edge"] += 1
        elif drop > JUMP:
            rows["wall"] += 1
        else:
            rows["step"] += 1
    rows["hard_walls"] = len(list(dict.fromkeys(collision.hard_walls(level.collision_blocks, heights))))
    return name, rows


def main():
    from support import paths
    from window.scene import levels_in
    argv = sys.argv[1:]
    taken = {i + 1 for i, a in enumerate(argv) if a in ("--json", "--jump")}
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in taken]
    out_file = argv[argv.index("--json") + 1] if "--json" in argv else None
    files = levels_in(paths.DATA_BZE)
    wanted = {a.upper() for a in args}
    if wanted:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0].upper() in wanted]
    with Pool(min(8, len(files))) as pool:
        result = pool.map(one, files)
    print(f"{'livello':10s} {'tratti':>7s} {'EDGE':>7s} {'muri':>7s} {'gradini':>7s} "
          f"{'0x7F':>7s} {'max m':>7s}")
    total = dict(runs=0, edge=0, wall=0, step=0, hard_walls=0)
    bands = [0] * (len(BANDS) + 1)
    report = {}
    for name, r in result:
        report[name] = r
        for k in total:
            total[k] += r[k]
        for i, n in enumerate(r["bands"]):
            bands[i] += n
        print(f"{name:10s} {r['runs']:7d} {r['edge']:7d} {r['wall']:7d} {r['step']:7d} "
              f"{r['hard_walls']:7d} {r['biggest'] / UNITS:7.1f}")
    print(f"{'totale':10s} {total['runs']:7d} {total['edge']:7d} {total['wall']:7d} {total['step']:7d} "
          f"{total['hard_walls']:7d}")
    print(f"   EDGE + muri + gradini = {total['edge'] + total['wall'] + total['step']}, "
          f"tratti = {total['runs']}")
    print("\ntratti per dislivello:")
    running = 0
    for i, edge in enumerate(BANDS):
        running += bands[i]
        print(f"   <= {edge:5d} unita' ({edge / UNITS:5.2f} m) {bands[i]:7d}   somma {running:7d}"
              f"   {100.0 * running / max(1, total['runs']):5.1f}%")
    print(f"   oltre {bands[-1]:7d}")
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print("written", out_file)


if __name__ == "__main__":
    main()
