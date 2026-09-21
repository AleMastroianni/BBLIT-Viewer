"""The "Visibility by area as in the game" option (findings 293-295).

    .venv/Scripts/python checks/check_area_visibility.py [LS01 ...]

1. Splitting by area draws the same triangles: for every level, the level
   built with `split_areas=True` and the one without must hold, group by
   group (same texture, category and blending), exactly the same triangles,
   only shared out between the areas. A triangle lost or duplicated fails.
   With the option off, only the skies cut by area keep their area (Era
   selector has one sky per era, and the game shows one at a time); any
   other group split there fails.
2. The portals (the 0x1000 quads, finding 293): the area each one leads to
   must be the area of another terrain piece of the same level. On the menu
   levels there are 1527 of them, and 1527 name another piece.
3. `LS01` (finding 295): six terrain pieces, no portals, and the collision
   block at the centre of each one gives that same area, so from an island
   only its own piece and its own sky are drawn.

Exits with 1 if anything fails.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import collision  # noqa: E402
from game import levels  # noqa: E402
from support import paths  # noqa: E402
from game import textures as texmod  # noqa: E402
import viewer  # noqa: E402

FLOATS_PER_VERTEX = 8


def triangles(group):
    data = group.data
    step = 3 * FLOATS_PER_VERTEX
    return sorted(bytes(data[i:i + step].tobytes()) for i in range(0, len(data) - step + 1, step))


def main():
    whole_disc = not sys.argv[1:]
    names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
    results = []
    portals_total = portals_named = 0
    same_triangles = different = 0
    area_leaks = []
    for name in names:
        file_path = os.path.join(paths.DATA_BZE, name + ".bze")
        if not os.path.exists(file_path):
            continue
        table = texmod.construct(paths.DATA_BZE, name, "extracted")
        plain = viewer.Level(file_path, "extracted", table, None, {}, families=())
        split = viewer.Level(file_path, "extracted", table, None, {}, families=(), split_areas=True)

        def by_group(level):
            # the area taken off the key on BOTH sides: a sky cut by area
            # keeps its area even in the plain level (Era selector: one sky per era, drawn one at a time)
            out = {}
            for lookup_key, g in level.face_groups.items():
                base = tuple(k for k in lookup_key if not (isinstance(k, tuple) and k and k[0] == "area"))
                out.setdefault(base, []).extend(triangles(g))
            return out

        joined, whole = by_group(split), by_group(plain)
        ok = joined.keys() == whole.keys() and all(sorted(joined[k]) == sorted(whole[k]) for k in whole)
        same_triangles += ok
        different += not ok
        if not ok:
            print(f"DIFFERENT: {name}")
        # ...but in the plain level ONLY the skies may keep an area: anything
        # else split there would be the option leaking in while it is off
        leaked = sorted({g.category for g in plain.face_groups.values()
                         if g.area is not None and g.category != "sky_dome"})
        if leaked:
            area_leaks.append(f"{name}: {leaked}")
        areas = {t["zone"] for t in plain.lvl["terrain"]}
        for _source, target, _corners in plain.portals():
            portals_total += 1
            portals_named += target in areas
    results.append(("splitting by area keeps every triangle", different == 0))
    print(f"levels where the split holds the same triangles: {same_triangles}, different: {different}")
    for line in area_leaks:
        print(f"  split with the option off: {line}")
    results.append(("with the option off only the skies keep an area", not area_leaks))
    results.append(("every portal names an area of the level", portals_named == portals_total))
    if whole_disc:
        results.append(("the 1527 portals of the disc are all there", portals_total == 1527))
    print(f"portals: {portals_total}, naming an area of the same level: {portals_named}")

    if "LS01" in names:
        lv = viewer.Level(os.path.join(paths.DATA_BZE, "LS01.bze"), "extracted", None, None, {}, families=(),
                          split_areas=True)
        piece_areas = sorted({t["zone"] for t in lv.lvl["terrain"]})
        results.append(("LS01: six terrain pieces, one per area", piece_areas == [1, 2, 3, 4, 5, 6]))
        results.append(("LS01: no portals", not lv.portals()))
        good = True
        for b in lv.collision_blocks:
            x = b.ox + b.ext_x // 2
            z = b.oz + b.ext_z // 2
            y = (b.y_ceiling + b.y_floor) // 2
            found = collision.block_at(lv.collision_blocks, x, y, z)
            good = good and found is not None and found.area == b.area
        results.append(("LS01: the block at the centre of each one gives its own area", good))
        skies = {g.area for g in lv.face_groups.values() if g.category == "sky_dome"}
        results.append(("LS01: every sky belongs to an area", skies and None not in skies))
        print(f"LS01: pieces {piece_areas}, skies of the areas {sorted(skies)}")

    for what, ok in results:
        print(("OK   " if ok else "FAIL ") + what)
    return 1 if not all(ok for _w, ok in results) else 0


if __name__ == "__main__":
    sys.exit(main())
