"""Proof that `collision.LazyVerticalRaster` gives the walls and the steps
that the full `collision.raster_vertical` gives.

    .venv/Scripts/python tools/raster_lazy_proof.py [L03A LS01 ...]

For every playable level (or the ones named), with the faces the viewer's
heightmap family uses:

1. every sub-cell the walls and the steps ask about holds the same heights in
   both (as a multiset: their two readers take a maximum and an "is there
   one", so the order does not matter to them);
2. `collision.hard_walls` gives the same list with either;
3. `collision.step_walls` gives the same list with either;

and the seconds: the full raster, and the lazy one (made while the walls and
the steps ask). Exits with 1 at any difference.
"""

from __future__ import annotations

import os
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

from game import collision  # noqa: E402
from game import levels  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import paths  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

LAZY = collision.LazyVerticalRaster
faces_seen = []


class Spy(LAZY):
    def __init__(self, face_points):
        faces_seen.append(list(face_points))
        super().__init__(face_points)


def main():
    wanted = {n.upper() for n in sys.argv[1:]}
    collision.LazyVerticalRaster = Spy
    bad = 0
    total_full = total_lazy = 0.0
    for file_path in levels_in(paths.DATA_BZE):
        name = os.path.splitext(os.path.basename(file_path))[0]
        if wanted and name.upper() not in wanted:
            continue
        faces_seen.clear()
        table = texmod.construct(os.path.dirname(file_path), name, "extracted")
        level = Level(file_path, "extracted", table, None, {}, families={"heightmap"})
        label = f"{levels.official_name(name) or name} ({name})"
        if not faces_seen:
            print(f"{label}: no heightmap family built")
            continue
        faces, blocks = faces_seen[-1], level.collision_blocks
        t0 = time.perf_counter()
        full = collision.raster_vertical(faces)
        t1 = time.perf_counter()
        walls_full = collision.hard_walls(blocks, full)
        steps_full = collision.step_walls(blocks, full)
        t2 = time.perf_counter()
        lazy = LAZY(faces)
        walls_lazy = collision.hard_walls(blocks, lazy)
        steps_lazy = collision.step_walls(blocks, lazy)
        t3 = time.perf_counter()
        asked = lazy._ready
        cells_same = all(sorted(full.get(k, ())) == sorted(lazy._cells.get(k, ())) for k in asked)
        ok = cells_same and walls_full == walls_lazy and steps_full == steps_lazy
        t_full, t_lazy = t1 - t0, (t3 - t2) - (t2 - t1)      # the raster's own share
        total_full += t_full
        total_lazy += max(0.0, t_lazy)
        print(f"{label}: raster {t_full:.2f} s -> {max(0.0, t_lazy):.2f} s; sub-cells asked {len(asked)}, "
              f"triangles sampled {len(lazy._sampled)} of {len(lazy._triangles)}; "
              f"{'identical' if ok else 'DIFFERENT'} (cells {cells_same}, walls {walls_full == walls_lazy}, "
              f"steps {steps_full == steps_lazy})", flush=True)
        bad += not ok
    print(f"raster in all: {total_full:.1f} s -> {total_lazy:.1f} s")
    print("all identical" if not bad else f"{bad} levels DIFFERENT")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
