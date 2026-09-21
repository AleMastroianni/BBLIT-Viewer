"""Inventory of placement problems, on every level of the menu: what is
drawn far from the rest, or missing.

    .venv/Scripts/python tools/inventory_placement.py [L03C1 ...] [--json out.json]

Four counts per level, all from the data the viewer reads:

1. sections: the terrain blocks joined when their boxes (game units, block
   translation applied) come within 1000 units of each other; every group
   but the largest is a separate section, with its distance from it. A
   separate section is not an error by itself: areas reached through a
   teleport are placed apart in the game too.
2. off collision: terrain blocks whose upward faces do not sit on the
   collision ground of the level (fewer than 20% within 20 units, finding
   283), counting only the faces with collision ground somewhere under them
   (at least 20 such faces): the cart tracks of L03C1 and L03C2 have no
   ground, and no ground is not a misplacement.
3. out of bounds: placed objects that draw a model and stand more than
   2000 units (about 15 m) outside the box of all the terrain.
4. template only: models (grouped by shape, vertex and face count) that
   other levels place, but that this level has only as a template spawned
   by a rule: with Cloned templates off the viewer does not draw them.

Prints one line per level with something to report, then the totals.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

JOIN = 1000          # blocks closer than this belong to the same section
OUT = 2000           # an object this far outside the terrain box is out of bounds
MATCH = 0.2          # below this share of faces on the collision ground: off collision


def upward_centres(vertices, faces, shift):
    out = []
    for vl in faces:
        p = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners[:3]]
        u = [p[1][k] - p[0][k] for k in range(3)]
        v = [p[2][k] - p[0][k] for k in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = sum(c * c for c in n) ** 0.5
        # up is +Y of the file normal (finding 283): ceilings are left out
        if ln == 0 or n[1] / ln < 0.7:
            continue
        q = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners]
        out.append(tuple(sum(c[k] for c in q) / len(q) for k in range(3)))
    return out


def box_gap(a, b):
    """Distance between two boxes (0 if they touch or overlap)."""
    return max(max(a[0][k] - b[1][k], b[0][k] - a[1][k], 0) for k in range(3))


def level_data(name):
    sec = sections(os.path.join(paths.DATA_BZE, name + ".bze"), "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    try:
        blocks = collision.read_level_blocks(sec[4], lvl)
    except Exception:  # noqa: BLE001
        blocks = []
    return sec, lvl, blocks


def inventory(name, shapes_placed_elsewhere=None):
    sec, lvl, blocks = level_data(name)
    report = {"level": name, "sections": [], "off_collision": [], "out_of_bounds": [], "template_only": []}

    # terrain boxes
    boxes = []
    for k, t in enumerate(lvl["terrain"]):
        try:
            v, f, _ = geo.read_terrain(sec[4], t["offset"])
        except Exception:  # noqa: BLE001
            continue
        if not v:
            continue
        tr = t["translation"]
        lo = [min(p[i] for p in v) + tr[i] for i in range(3)]
        hi = [max(p[i] for p in v) + tr[i] for i in range(3)]
        boxes.append((k, t, v, f, (lo, hi)))
    if not boxes:
        return report, {}

    # 1. sections
    groups = [[b] for b in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if any(box_gap(a[4], b[4]) <= JOIN for a in groups[i] for b in groups[j]):
                    groups[i] += groups.pop(j)
                    merged = True
                    break
            if merged:
                break
    groups.sort(key=lambda g: -sum(len(b[3]) for b in g))
    for g in groups[1:]:
        gap = min(box_gap(a[4], b[4]) for a in g for b in groups[0])
        report["sections"].append({"blocks": [b[0] for b in g], "areas": sorted({b[1]["zone"] for b in g}),
                                   "faces": sum(len(b[3]) for b in g), "distance": round(gap)})

    # 2. off collision
    ground_areas = defaultdict(int)
    for b in blocks:
        w, h, m = collision.subcell_map(b)
        ground_areas[b.area] += sum(1 for x in m if x not in collision.NO_GROUND)
    for k, t, v, f, _box in boxes:
        if ground_areas.get(t["zone"], 0) < 100:
            continue
        pts = [p for p in upward_centres(v, f[::2], t["translation"])
               if any(b.ground_height(p[0], p[2]) is not None for b in blocks)]
        if len(pts) < 20:
            continue
        ok = sum(1 for x, y, z in pts
                 if any((g := b.ground_height(x, z)) is not None and abs(g - y) <= 20 for b in blocks))
        if ok / len(pts) < MATCH:
            report["off_collision"].append({"block": k, "area": t["zone"], "translation": t["translation"],
                                            "match": round(ok / len(pts), 2)})

    # 3. out of bounds, 4. template only
    lo = [min(b[4][0][i] for b in boxes) for i in range(3)]
    hi = [max(b[4][1][i] for b in boxes) for i in range(3)]
    models = {r["id"]: r for r in lvl["resources"] if r["data_kind"] == "model" and r["size"] > 12}
    shape_of, kinds = {}, defaultdict(set)
    for mid, r in models.items():
        try:
            mv, mf, _ = geo.read_model(sec[4], r["offset"], None)
            shape_of[mid] = (len(mv), len(mf))
        except Exception:  # noqa: BLE001
            pass
    for n, o in enumerate(lvl["objects"]):
        mid = next((r for r in o["resources"] if r in models), None)
        if mid is None:
            continue
        placed = o["block_type"] != 0x08
        if mid in shape_of:
            kinds[shape_of[mid]].add("placed" if placed else "template")
        if placed and o["position"]:
            p = o["position"]
            outside = max(max(lo[i] - p[i], p[i] - hi[i], 0) for i in range(3))
            if outside > OUT:
                report["out_of_bounds"].append({"object": n, "model": mid, "shape": shape_of.get(mid),
                                                "position": p, "outside": round(outside)})
    if shapes_placed_elsewhere is not None:
        for shape, k in kinds.items():
            if k == {"template"} and shape in shapes_placed_elsewhere and shape[1] >= 40:
                report["template_only"].append({"shape": shape, "placed_in": len(shapes_placed_elsewhere[shape])})
    return report, {s: k for s, k in kinds.items()}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    if out_json in args:
        args.remove(out_json)
    names = args or sorted({v[1] for v in levels.all_entries()})
    names = [n for n in names if os.path.exists(os.path.join(paths.DATA_BZE, n + ".bze"))]
    # first pass: where each shape is placed
    first = {}
    placed_in = defaultdict(set)
    for name in names:
        report, kinds = inventory(name)
        first[name] = report
        for shape, k in kinds.items():
            if "placed" in k:
                placed_in[shape].add(name)
    reports = []
    for name in names:
        report, _ = inventory(name, {s: lv - {name} for s, lv in placed_in.items() if lv - {name}})
        reports.append(report)
    totals = defaultdict(int)
    for r in reports:
        parts = []
        for item_key in ("sections", "off_collision", "out_of_bounds", "template_only"):
            if r[item_key]:
                totals[item_key] += len(r[item_key])
                totals[item_key + "_levels"] += 1
                parts.append(f"{item_key} {len(r[item_key])}")
        if parts:
            print(f"{r['level']:10s} " + ", ".join(parts))
    print("totals:", dict(totals))
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(reports, f, indent=1)


if __name__ == "__main__":
    main()
