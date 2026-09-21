"""Three sweeps over every level of the disc, to size up three problems
before repairing any of them.

    .venv/Scripts/python tools/survey.py
    .venv/Scripts/python tools/survey.py --only camera
    .venv/Scripts/python tools/survey.py --side 40 --json out.json

1. **the opening camera, as it was before `opening_camera`** (the viewer's
   camera now starts behind the player: `controls.opening_camera`,
   `checks/check_start_camera.py`). The old formula put the camera at the
   middle of the terrain box, raised by 0.35 and pulled back by 0.75 of the
   LONGEST side of the box, whichever axis that is. Reported: how far outside
   the terrain box the starting point falls, per axis, in metres -- and,
   because being outside the box is what pulling back means and every level
   of the disc comes out "outside", the measure that does tell a good opening
   view from a bad one: how much of the frame the terrain fills, with the
   viewer's own projection. 1.00 is exactly full; above 1.00 the level runs
   off the edges of the screen.
2. **objects placed at (0, 0, 0).** The game's origin is not inside most
   levels: an object left there is one the game puts somewhere else at
   runtime (fireballs, the whirlwind and company). Counted per level, with
   the object's number and whether it draws a model.
3. **triangles with an absurd side.** A model whose part is mounted without
   its transform gets vertices at the wrong scale, and its triangles come out
   enormous (the black spikes of The Carrot-henge Mystery 3). The sky dome is
   left out of the count: it is huge on purpose and on its own would hide
   everything else.

Every measure is in viewer metres (128 game units = 1 metre, VIEWER.md).
This tool only counts: it changes nothing and repairs nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import levels  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from ui import settings as settings_mod  # noqa: E402
from window.overlays import OVERLAYS  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

SIDE = 40.0          # a triangle side longer than this, in metres, is absurd
DEFAULT_FIELD_OF_VIEW = settings_mod.DEFAULTS["field_of_view"]   # what the viewer opens with


def in_prose(code):
    """The rule for prose: the name, with the file code in brackets."""
    name = levels.official_name(code)
    return f"{name} ({code.upper()})" if name else code.upper()


def build(file_path):
    """The level as the viewer opens it, without a window: the flags are off,
    so only what is always drawn is built."""
    name = os.path.splitext(os.path.basename(file_path))[0]
    table = texmod.construct(os.path.dirname(file_path), name, "extracted")
    signature = level_cache.signature(file_path)
    pieces = level_cache.fetch("extracted", name, signature) or {}
    return Level(file_path, "extracted", table, None, pieces)


def opening_camera(level, fov=DEFAULT_FIELD_OF_VIEW, aspect=1280 / 760):
    """Where `controls.reset_camera` puts the camera, and what you see from
    there.

    Being outside the terrain box is not by itself a fault: the formula pulls
    the camera back on purpose, and every level of the disc comes out
    "outside". What tells a good opening view from a bad one is **how much of
    the screen the level fills** and **whether all of it is in frame**, so
    both are measured here, with the viewer's own projection (`fov` is the
    vertical angle, `drawing.py`).
    """
    lo, hi = level.terrain_lo, level.terrain_hi
    middle = [(a + b) / 2 for a, b in zip(lo, hi)]
    radius = max(hi[i] - lo[i] for i in range(3)) or 10.0
    pos = (middle[0], middle[1] + radius * 0.35, middle[2] + radius * 0.75)
    outside = [max(0.0, lo[i] - pos[i], pos[i] - hi[i]) for i in range(3)]

    # the camera of reset_camera: yaw -90, pitch -22 (controls.py)
    yaw, pitch = math.radians(-90.0), math.radians(-22.0)
    forward = (math.cos(pitch) * math.cos(yaw), math.sin(pitch), math.cos(pitch) * math.sin(yaw))
    right = (-math.sin(yaw), 0.0, math.cos(yaw))
    up = tuple(forward[(k + 1) % 3] * right[(k + 2) % 3] - forward[(k + 2) % 3] * right[(k + 1) % 3]
               for k in range(3))
    half_up = math.tan(math.radians(fov) / 2)
    half_side = half_up * aspect
    widest_side = widest_up = 0.0
    behind = 0
    for corner in [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]:
        d = [corner[k] - pos[k] for k in range(3)]
        depth = sum(d[k] * forward[k] for k in range(3))
        if depth <= 0.01:
            behind += 1
            continue
        widest_side = max(widest_side, abs(sum(d[k] * right[k] for k in range(3))) / depth / half_side)
        widest_up = max(widest_up, abs(sum(d[k] * up[k] for k in range(3))) / depth / half_up)
    # 1.0 = the level exactly fills the frame; below that it is small in the
    # middle of the screen, above it runs off the edges
    fills = max(widest_side, widest_up)
    return pos, outside, radius, {"fills": round(fills, 2), "behind": behind,
                                  "side": round(widest_side, 2), "up": round(widest_up, 2)}


def at_the_origin(level):
    """The placed objects sitting at (0, 0, 0), as the game's file has them."""
    models = {r["id"] for r in level.lvl["resources"] if r["data_kind"] == "model"}
    found = []
    for n, o in enumerate(level.lvl["objects"]):
        position = o.get("position")
        if not position or tuple(position[:3]) != (0, 0, 0):
            continue
        has_model = any(r in models for r in o["resources"])
        found.append({"object": n, "model": has_model, "block_type": o["block_type"]})
    return found


def absurd_triangles(level, side):
    """Triangles with a side longer than `side` metres, split by what they
    belong to. Counted only on what the game itself draws: the flag overlays
    are the viewer's own drawing and the sky dome is huge on purpose, so both
    would only hide the models that are really built wrong. An animated
    object is counted in its first pose alone, or every model would be
    counted as many times as it has frames."""
    total = counted = 0
    by_category = defaultdict(int)
    longest = 0.0
    for face_group in level.face_groups.values():
        if face_group.category == "sky_dome" or face_group.category in OVERLAYS:
            continue
        run = face_group.frames[0] if face_group.frames else face_group.data
        n_vertices = len(run) // 8
        total += n_vertices // 3
        for first in range(0, n_vertices - 2, 3):
            p = [run[(first + j) * 8:(first + j) * 8 + 3] for j in range(3)]
            worst = 0.0
            for a, b in ((0, 1), (1, 2), (2, 0)):
                distance = sum((p[a][k] - p[b][k]) ** 2 for k in range(3)) ** 0.5
                worst = max(worst, distance)
            longest = max(longest, worst)
            if worst > side:
                counted += 1
                by_category[face_group.category] += 1
    return {"triangles": total, "absurd": counted, "longest": round(longest, 1),
            "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1]))}


def print_camera(report, fov):
    rows = [(r["camera"]["view"]["fills"], code, r) for code, r in report.items() if r.get("camera")]
    out = sum(1 for _f, _c, r in rows if any(r["camera"]["outside"]))
    off = [v for v in rows if v[0] > 1.0]
    small = [v for v in rows if v[0] < 0.5]
    print(f"\n=== 1. the opening camera ({len(rows)} levels, {fov:.0f} degrees of field of view) ===")
    print(f"outside the terrain box: {out} of {len(rows)} - on its own this says nothing, "
          f"pulling the camera back is what the formula is for")
    print(f"level running off the edges of the frame (fills > 1.00): {len(off)}")
    print(f"level small in the middle of the frame (fills < 0.50): {len(small)}")
    print("\nfills: 1.00 = the terrain exactly fills the frame; behind: box corners behind the camera")
    for fills, code, r in sorted(rows, reverse=True):
        camera = r["camera"]
        mark = "OFF FRAME" if fills > 1.0 else ("too small" if fills < 0.5 else "ok")
        print(f"fills {fills:5.2f}  {mark:9s} {in_prose(code):52s} "
              f"behind {camera['view']['behind']}   out of the box "
              f"x {camera['outside'][0]:5.1f} y {camera['outside'][1]:5.1f} z {camera['outside'][2]:6.1f} m"
              f"   (longest box side {camera['radius']:.0f} m)")


def print_origin(report):
    rows = [(len(r["origin"]), code, r) for code, r in report.items() if r.get("origin")]
    print(f"\n=== 2. objects placed at (0, 0, 0) "
          f"({sum(n for n, _c, _r in rows)} in {len(rows)} levels) ===")
    for n, code, r in sorted(rows, reverse=True):
        drawn = sum(1 for v in r["origin"] if v["model"])
        numbers = ", ".join(str(v["object"]) for v in r["origin"][:12])
        more = " ..." if len(r["origin"]) > 12 else ""
        print(f"{n:5d}   {in_prose(code):52s} {drawn} with a model   objects {numbers}{more}")


def print_triangles(report, side):
    rows = [(r["triangles"]["absurd"], code, r) for code, r in report.items() if r.get("triangles")]
    out = [v for v in rows if v[0]]
    # the cloned templates are OFF at every start (settings, "clones": 0), so
    # what a level shows as it opens is everything but them
    on_screen = sum(v for _n, _c, r in out
                    for k, v in r["triangles"]["by_category"].items() if k != "clones")
    print(f"\n=== 3. triangles with a side over {side:.0f} m, sky dome left out "
          f"({sum(n for n, _c, _r in out)} in {len(out)} levels of {len(rows)}) ===")
    print(f"of those, drawn as the level opens: {on_screen} - the rest are in the cloned templates, "
          f"which start off (Level options -> Cloned templates)")
    for n, code, r in sorted(out, reverse=True):
        kinds = ", ".join(f"{k} {v}" for k, v in list(r["triangles"]["by_category"].items())[:4])
        shown = sum(v for k, v in r["triangles"]["by_category"].items() if k != "clones")
        print(f"{n:6d} / {r['triangles']['triangles']:6d}   {in_prose(code):52s} "
              f"longest {r['triangles']['longest']:8.1f} m   on screen {shown:4d}   {kinds}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", help="level codes; all of them by default")
    parser.add_argument("--only", choices=("camera", "origin", "triangles"),
                        help="one sweep instead of the three")
    parser.add_argument("--side", type=float, default=SIDE,
                        help=f"a triangle side is absurd above this many metres (default {SIDE:.0f})")
    parser.add_argument("--fov", type=float, default=DEFAULT_FIELD_OF_VIEW,
                        help="vertical field of view for sweep 1 "
                             f"(default {DEFAULT_FIELD_OF_VIEW:.0f}, the viewer's; 51 is the PC's)")
    parser.add_argument("--json", dest="json_path", help="the three lists, as data")
    args = parser.parse_args(argv)

    file_paths = levels_in(paths.DATA_BZE)
    if args.levels:
        wanted = {c.lower() for c in args.levels}
        file_paths = [p for p in file_paths
                      if os.path.splitext(os.path.basename(p))[0].lower() in wanted]
    report = {}
    for file_path in file_paths:
        code = os.path.splitext(os.path.basename(file_path))[0]
        try:
            level = build(file_path)
        except Exception as error:  # noqa: BLE001
            report[code] = {"error": f"{type(error).__name__}: {error}"}
            print("!", end="", flush=True)
            continue
        row = {"name": levels.official_name(code)}
        if args.only in (None, "camera"):
            pos, outside, radius, view = opening_camera(level, args.fov)
            row["camera"] = {"pos": [round(v, 1) for v in pos],
                             "outside": [round(v, 1) for v in outside],
                             "lo": [round(v, 1) for v in level.terrain_lo],
                             "hi": [round(v, 1) for v in level.terrain_hi],
                             "radius": round(radius, 1), "view": view}
        if args.only in (None, "origin"):
            row["origin"] = at_the_origin(level)
        if args.only in (None, "triangles"):
            row["triangles"] = absurd_triangles(level, args.side)
        report[code] = row
        print(".", end="", flush=True)
    print()

    if args.only in (None, "camera"):
        print_camera(report, args.fov)
    if args.only in (None, "origin"):
        print_origin(report)
    if args.only in (None, "triangles"):
        print_triangles(report, args.side)

    broken = {c: r["error"] for c, r in report.items() if "error" in r}
    if broken:
        print("\nlevels that would not open:")
        for code, error in broken.items():
            print(f"  {in_prose(code)}: {error}")
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)
        print(f"\nwritten to {args.json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
