"""The collision ground, split the way it was asked for.

Today the Ground flag has two classes: a sub-cell is "covered" when a drawn
up-facing face passes within 100 units of it, "invisible" otherwise. But
what stays lit in Era selector is **not** an invisible platform, it is
a **slope** -- the heightmap climbs in steps of 128 while the drawn ground
is smooth, so the cells in between miss the threshold by 36 to 100 units and
light up as a crust of pixels over a floor that is there.

So three classes, not two:

* **covered**: a face within COVER units -- the game's face gets the tint;
* **slope**: no face that close, but one within SLOPE units -- the floor IS
  drawn, only at another height (slopes, staircases). No crust: at most a
  light mark on the face, and a menu entry of its own, off by default;
* **invisible**: no drawn face above this cell at all (or only one further
  than SLOPE) -- this is the one that matters for glitch hunting, and it
  stays bright.

    .venv/Scripts/python tools/ground_split.py [LS01 ...] [--json FILE]

It also prints how the cells fall by distance, so the two thresholds are
read off the data and not guessed.
"""
import json
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

COVER = 32.0       # the knee measured on the disc (the census)
SLOPE = 160.0      # beyond one step of the heightmap (128) the face is not this cell's floor
BANDS = (16, 32, 48, 64, 100, 128, 160, 256, 512)


def one(path):
    from game import collision
    from game import geometry as geo
    from window.scene import Level, sections
    name = os.path.splitext(os.path.basename(path))[0].upper()
    lvl = Level(path, "extracted", None, None, {}, families=set())
    sec4 = lvl.sec4
    face_list = []
    for t in lvl.lvl["terrain"]:
        try:
            vs, faces, _ = geo.read_terrain(sec4, t["offset"])
        except Exception:  # noqa: BLE001
            continue
        sp = t["translation"]
        for vl in faces:
            face_list.append([tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners])
    covering = collision.raster_faces(face_list)
    bands = [0] * (len(BANDS) + 1)
    none_at_all = 0
    cells = covered = slope = invisible = 0
    for b in lvl.collision_blocks:
        w, h, m = collision.subcell_map(b)
        for gz in range(h):
            row = m[gz * w:(gz + 1) * w]
            for gx in range(w):
                v = row[gx]
                if v in collision.NO_GROUND:
                    continue
                y = collision.height_units(b, v)
                x, z = b.ox + gx * collision.SUBCELL, b.oz + gz * collision.SUBCELL
                cells += 1
                heights = covering.get((int(x // collision.SUBCELL), int(z // collision.SUBCELL)))
                if not heights:
                    none_at_all += 1
                    invisible += 1
                    bands[-1] += 1
                    continue
                gap = min(abs(a - y) for a in heights)
                for i, edge in enumerate(BANDS):
                    if gap <= edge:
                        bands[i] += 1
                        break
                else:
                    bands[-1] += 1
                if gap <= COVER:
                    covered += 1
                elif gap <= SLOPE:
                    slope += 1
                else:
                    invisible += 1
    return name, dict(cells=cells, covered=covered, slope=slope, invisible=invisible,
                      no_face=none_at_all, bands=bands)


def main():
    from support import paths
    from window.scene import levels_in
    out_file = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != out_file]
    files = levels_in(paths.DATA_BZE)
    wanted = {a.upper() for a in args}
    if wanted:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0].upper() in wanted]
    with Pool(min(8, len(files))) as pool:
        rows = pool.map(one, files)
    print(f"{'level':10s} {'cells':>9s} {'covered':>9s} {'slope':>9s} {'invisible':>9s} {'no face':>9s}")
    total = dict(cells=0, covered=0, slope=0, invisible=0, no_face=0)
    bands = [0] * (len(BANDS) + 1)
    for name, r in rows:
        for k in total:
            total[k] += r[k]
        for i, n in enumerate(r["bands"]):
            bands[i] += n
        print(f"{name:10s} {r['cells']:9d} {r['covered']:9d} {r['slope']:9d} {r['invisible']:9d} {r['no_face']:9d}")
    print(f"{'total':10s} {total['cells']:9d} {total['covered']:9d} {total['slope']:9d} "
          f"{total['invisible']:9d} {total['no_face']:9d}")
    print("\ncells by the distance to the nearest drawn face:")
    running = 0
    for i, edge in enumerate(BANDS):
        running += bands[i]
        print(f"   <= {edge:4d} units {bands[i]:9d}   running {running:9d}"
              f"   {100.0 * running / max(1, total['cells']):5.1f}%")
    print(f"   further / none {bands[-1]:9d}   of which no face at all {total['no_face']:9d}")
    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({n: r for n, r in rows}, f, indent=1)
        print("written", out_file)


if __name__ == "__main__":
    main()
