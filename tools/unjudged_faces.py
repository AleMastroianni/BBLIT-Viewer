"""The faces joined to a NO COLLISION face that the flag never judges, by slope.

    .venv/Scripts/python tools/unjudged_faces.py [--level L01B] [--propose]

The flag No collision (finding 298, `collision.no_collision_kind` and
`wall_crossable`) judges floors (up normal within 45 degrees of vertical) and
walls (normal within about 17 degrees of horizontal). A face joined to a
face without collision with any other slope, a steep slope between 45 and
73 degrees or an overhang past 107 degrees, is never judged: the rim under
the flat top of the mushroom rock of Wabbit on the run! 2 (`L01B`, camera
14848, -5120, 5760) stays brown while Bugs falls through it.

This lists, on the whole disc, how many such faces there are, by 10-degree
bins of the angle between the face's up normal and vertical (0 = flat floor,
90 = wall, 180 = ceiling). With `--propose` it also applies the proposed
test to them (`collision.joined_face_crossable`) and counts what it marks.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from collections import Counter

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


FLOOR_LIMIT = math.degrees(math.acos(0.7))     # no_collision_kind judges up to here


def slope_degrees(p):
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
    if ln == 0:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, n[1] / ln))))


def survey(level, propose):
    """{bin: count} of the unjudged joined faces of a level, and the marked ones."""
    bins, marked = Counter(), Counter()
    for t in level.lvl["terrain"]:
        vertices, faces, _stat = geo.read_terrain(level.sec4, t["offset"], [], [])
        sp = t["translation"]
        corners_of = [[tuple(vertices[h][k] + sp[k] for k in range(3)) for h in vl.corners] for vl in faces]
        through = {i for i in range(len(faces))
                   if collision.no_collision_kind(level.collision_blocks, corners_of[i])}
        by_vertex = {}
        for i, vl in enumerate(faces):
            for h in vl.corners:
                by_vertex.setdefault(h, []).append(i)
        crossable = {}
        queue = sorted(through)
        while queue:
            i = queue.pop()
            for h in faces[i].corners:
                for j in by_vertex[h]:
                    if j in through:
                        continue
                    if j not in crossable:
                        crossable[j] = collision.wall_crossable(level.collision_blocks, corners_of[j])
                    if crossable[j]:
                        through.add(j)
                        queue.append(j)
        # the joined faces the two tests never judged: neither a floor nor a wall
        for i in through:
            for h in faces[i].corners:
                for j in by_vertex[h]:
                    if j in through or crossable.get(j) is not None:
                        continue
                    degrees = slope_degrees(corners_of[j])
                    if degrees is None or degrees <= FLOOR_LIMIT:
                        continue           # a floor: judged (it has collision)
                    crossable[j] = False       # counted once
                    b = int(degrees // 10) * 10
                    bins[b] += 1
                    if propose and collision.joined_face_crossable(level.collision_blocks, corners_of[j]):
                        marked[b] += 1
    return bins, marked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--level")
    parser.add_argument("--propose", action="store_true")
    args = parser.parse_args()
    total, total_marked, per_level = Counter(), Counter(), []
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
        bins, marked = survey(level, args.propose)
        if bins:
            per_level.append((code, sum(bins.values()), sum(marked.values()), dict(sorted(bins.items()))))
        total.update(bins)
        total_marked.update(marked)
    print("\nunjudged faces joined to a NO COLLISION face, by slope (degrees from vertical up):")
    for b in sorted(total):
        line = f"  {b:3d}-{b + 9:3d}: {total[b]:5d}"
        if args.propose:
            line += f"   marked by the proposed test: {total_marked[b]}"
        print(line)
    print(f"  total {sum(total.values())} in {len(per_level)} levels"
          + (f", marked {sum(total_marked.values())}" if args.propose else ""))
    for code, n, m, bins in sorted(per_level, key=lambda r: -r[1])[:15]:
        print(f"  {in_prose(code)[:48]:48s} {n:4d}" + (f" marked {m:4d}" if args.propose else "") + f"  {bins}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
