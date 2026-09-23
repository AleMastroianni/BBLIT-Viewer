"""The steps the flag Invisible walls skips as "covered by a visible face".

    .venv/Scripts/python tools/skipped_steps.py [--level LS01]

A step (finding 298: ground more than 100 units higher in the next
sub-cell) stops Bugs whether or not something is drawn over it. The flag
used to draw only the steps with no visible near-vertical face nearby
(`collision._seen_between` over `raster_vertical`), and that raster took
every face, cut-outs and semi-transparent ones included: the ropes of the
boat in Era selector (`LS01`, X 7760, Z 18360-18900) counted as a wall and
opened a gap in the STEP WALL in front of the mast, where the game stops
you (seen in a recording of the game).

For every level: steps in all, steps covered when every face counts, steps
covered when only SOLID faces count (opaque texture, no cut-out entry, no
blend), and the LS01 line of the mast. Bars, set before the change: on that
line no step stays covered with solid faces; over the disc the covered set
can only shrink.
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))

from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def faces_of(level, solid_only):
    """The level's faces (terrain and placed objects) as corner lists."""
    out = []
    for t in level.lvl["terrain"]:
        try:
            vs, vl_, _ = geo.read_terrain(level.sec4, t["offset"])
        except Exception:  # noqa: BLE001
            continue
        sp = t["translation"]
        for vl in vl_:
            if solid_only and (vl.blend is not None or vl.tex_id in level.cut_outs):
                continue
            out.append([tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners])
    lo, hi = level.terrain_lo, level.terrain_hi
    diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
    out += level._object_faces(diagonal, solid_only=solid_only)
    return out


def survey(level):
    steps_all = collision.step_walls(level.collision_blocks, collision.raster_vertical(faces_of(level, False)))
    steps_solid = collision.step_walls(level.collision_blocks, collision.raster_vertical(faces_of(level, True)))
    real = [s for s in steps_all if not s[8]]                  # not from a 0x7E hole
    covered_all = sum(1 for s in real if s[6])
    covered_solid = sum(1 for s in steps_solid if not s[8] and s[6])
    return len(real), covered_all, covered_solid, steps_solid


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--level")
    args = parser.parse_args()
    total = [0, 0, 0]
    rows = []
    for file_path in levels_in(paths.find_levels_folder(None)):
        code = os.path.splitext(os.path.basename(file_path))[0]
        if args.level and code.lower() != args.level.lower():
            continue
        try:
            table = texmod.construct(os.path.dirname(file_path), code, "extracted")
            level = Level(file_path, "extracted", table, None,
                          level_cache.fetch("extracted", code, level_cache.signature(file_path)) or {})
        except Exception as e:  # noqa: BLE001
            print(f"{code}: not built ({e})")
            continue
        if not level.collision_blocks:
            continue
        n, c_all, c_solid, steps_solid = survey(level)
        rows.append((code, n, c_all, c_solid))
        for i, v in enumerate((n, c_all, c_solid)):
            total[i] += v
        if code.upper() == "LS01":
            mast = [s for s in steps_solid if not s[8] and s[0] == s[2] == 7760 and s[3] >= 18360 and s[1] <= 18900]
            print(f"LS01, the line X 7760 Z 18360-18900 with solid faces: {len(mast)} runs, "
                  f"{sum(1 for s in mast if s[6])} covered: "
                  + ", ".join(f"Z {s[1]}-{s[3]} {'COVERED' if s[6] else 'drawn'}" for s in mast))
    print("\nsteps (not from holes): in all, covered with every face, covered with solid faces only")
    for code, n, c_all, c_solid in sorted(rows, key=lambda r: -(r[2] - r[3]))[:15]:
        print(f"  {in_prose(code)[:48]:48s} {n:5d} {c_all:5d} {c_solid:5d}")
    print(f"  total over {len(rows)} levels: {total[0]} steps, {total[1]} covered with every face, "
          f"{total[2]} with solid faces only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
