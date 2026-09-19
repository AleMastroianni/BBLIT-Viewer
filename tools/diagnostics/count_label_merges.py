"""Before the combined flag names ("DTH + DMG"): how many things share a
name or a place, on every level of the menu.

    .venv/Scripts/python tools/diagnostics/count_label_merges.py [L03A ...]

1. Zones: the effects of each zone that kills, hurts or teleports (all its
   rules together: DEATH 0x200000, TELEPORT 0x40000000, damage action
   0x48), counted by combination; DEATH on a zone at least half the terrain
   footprint counts as the death floor (DFL).
2. Zones with the same box (origin, size, rotation, rotation flag): the
   groups and the effects they put together.
3. Faces: every overlay fill of the built level (the flags' groups, edges
   and names left out) as triangles, positions rounded to 1/100 m; a
   triangle drawn twice in the same group, or in two groups, is counted per
   pair of groups. Only whole triangles: partial overlaps are not counted.

A measure, nothing to pass: it prints the counts and exits with 0.
"""
import collections
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import export_obj as geo  # noqa: E402
import levels  # noqa: E402
import paths  # noqa: E402
import textures as texmod  # noqa: E402
import viewer  # noqa: E402
import zones  # noqa: E402

FLOATS_PER_VERTEX = 8           # x y z, r g b, u v (Level._add_faces)


def effects_of(z, floor):
    effects = 0
    for r in z.get("rules", []):
        effects |= r["effect"]
    out = []
    if effects & zones.DEATH:
        out.append("DFL" if floor else "DTH")
    if zones.hurts(z):
        out.append("DMG")
    if effects & zones.TELEPORT:
        out.append("RSP")
    return tuple(out)


def triangles(group):
    data = group.data
    step = 3 * FLOATS_PER_VERTEX
    for i in range(0, len(data) - step + 1, step):
        yield frozenset(tuple(round(data[i + k * FLOATS_PER_VERTEX + a], 2) for a in range(3)) for k in range(3))


def main():
    names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
    combos = collections.Counter()
    combo_levels = collections.defaultdict(set)
    same_box = collections.Counter()
    same_box_levels = collections.defaultdict(set)
    within = collections.Counter()
    within_levels = collections.defaultdict(set)
    between = collections.Counter()
    between_levels = collections.defaultdict(set)
    for name in names:
        file_path = os.path.join(paths.DATA_BZE, name + ".bze")
        if not os.path.exists(file_path):
            continue
        table = texmod.construct(paths.DATA_BZE, name, "extracted")
        lv = viewer.Level(file_path, "extracted", table, None, {})
        lo, hi = lv.terrain_lo, lv.terrain_hi
        footprint = (hi[0] - lo[0]) * (hi[2] - lo[2]) * geo.UNITS_PER_METER ** 2
        boxes = collections.defaultdict(list)
        for z in lv.lvl["zones"]:
            shape = zones.shape_of(z)
            if shape is None or not (zones.kind_of(z) or zones.hurts(z)):
                continue
            e = effects_of(z, footprint and shape.area >= zones.FLOOR_FRACTION * footprint)
            combos[e] += 1
            combo_levels[e].add(name)
            key = (tuple(z["origin"]), tuple(z["size"]), tuple(a % 4096 for a in (z.get("rotation") or (0, 0, 0))),
                   bool(shape.m is not None))
            boxes[key].append(e)
        for members in boxes.values():
            if len(members) > 1:
                union = tuple(sorted({x for m in members for x in m}))
                k = (len(members), union)
                same_box[k] += 1
                same_box_levels[k].add(name)
        seen = {}
        for g in lv.face_groups.values():
            c = g.category
            if c not in viewer.OVERLAYS or c.endswith("_lines") or "_label" in c:
                continue
            for tri in triangles(g):
                if len(tri) < 3:
                    continue            # degenerate
                if tri in seen:
                    other = seen[tri]
                    if other == c:
                        within[c] += 1
                        within_levels[c].add(name)
                    else:
                        pair = tuple(sorted((other, c)))
                        between[pair] += 1
                        between_levels[pair].add(name)
                else:
                    seen[tri] = c
        print(f"{name} done", flush=True)

    def levels_text(s):
        s = sorted(s)
        return ", ".join(s[:8]) + (f" (+{len(s) - 8})" if len(s) > 8 else "")

    print("\n1. zones by their effects")
    for e, n in combos.most_common():
        print(f"   {' + '.join(e):16s} {n:5d} zones in {len(combo_levels[e]):3d} levels: {levels_text(combo_levels[e])}")
    print("\n2. zones sharing the same box (group size, effects together)")
    if not same_box:
        print("   none")
    for (size, union), n in same_box.most_common():
        print(f"   {size} zones, {' + '.join(union):16s} {n:4d} boxes in {len(same_box_levels[(size, union)]):3d} levels: "
              f"{levels_text(same_box_levels[(size, union)])}")
    print("\n3a. the same triangle twice in one group")
    if not within:
        print("   none")
    for c, n in within.most_common():
        print(f"   {c:24s} {n:7d} triangles in {len(within_levels[c]):3d} levels: {levels_text(within_levels[c])}")
    print("\n3b. the same triangle in two groups")
    if not between:
        print("   none")
    for pair, n in between.most_common():
        print(f"   {pair[0]} = {pair[1]}: {n} triangles in {len(between_levels[pair])} levels: "
              f"{levels_text(between_levels[pair])}")


if __name__ == "__main__":
    main()
