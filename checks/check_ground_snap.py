"""The objects the game keeps on the ground (finding 340): does the viewer
put them where the game does?

    .venv/Scripts/python checks/check_ground_snap.py [L05A2 ...]

A type 14 object whose starting step has neither 0x1 nor 0x80000000 in its
control dword stands on the collision ground of its area at every tick; its
file height means nothing. The reverse's survey (`check_ground_snap.py` of
`BBLIT_Decomp_Ale`, the cutscenes and the `_8` files left out) found 158 such
objects, 24 of them more than 30 units from their ground.

This opens every level as the viewer does (`scene.Level`, which calls
`collision.settle_objects`) and measures, for every object of that class,
the gap between where the viewer puts it and its ground; and it checks that
no other object moved.

Bar fixed before the change: 0 settling objects more
than 30 units from their ground, and 0 other objects moved. Before the
change: 24 of them (the reverse's list). Exits with 1 otherwise.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import collision  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

GAP = 30


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def one_level(file_path):
    code = os.path.splitext(os.path.basename(file_path))[0]
    # the file as it is, for what the other objects must still be
    raw = loadscript.export_level(loadscript.parse(sections(file_path, "extracted")[1])[0])
    level = Level(file_path, "extracted", None, None, {}, families=())
    blocks = level.collision_blocks
    settling = far = moved_others = 0
    far_list = []
    for n, (o, r) in enumerate(zip(level.lvl["objects"], raw["objects"])):
        if collision.settles(r):
            if not blocks:
                continue
            x, y, z = o["position"]
            found = collision.ground_below(blocks, x, y, z, o.get("area"))
            if found is None:
                continue
            settling += 1
            if abs(found[0] - y) > GAP:
                far += 1
                far_list.append((n, r["position"], o["position"], round(found[0])))
        elif o["position"] != r["position"]:
            moved_others += 1
    return code, settling, far, moved_others, far_list


def main():
    wanted = {a.lower() for a in sys.argv[1:]}
    file_paths = [p for p in levels_in(paths.DATA_BZE)
                  if not os.path.splitext(os.path.basename(p))[0].lower().endswith("_8")
                  and (not wanted or os.path.splitext(os.path.basename(p))[0].lower() in wanted)]
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, min(8, os.cpu_count() or 2))) as pool:
        answers = list(pool.map(one_level, file_paths))
    settling = far = others = 0
    for code, s, f, m, far_list in answers:
        settling += s
        far += f
        others += m
        for n, file_pos, pos, ground in far_list:
            print(f"  FAR   {in_prose(code)[:44]:44s} object {n:4d}  file {file_pos}  viewer {pos}  ground {ground}")
        if m:
            print(f"  MOVED {in_prose(code)[:44]:44s} {m} objects that the game does not settle")
    print(f"{len(file_paths)} levels; settling objects with ground under them: {settling}; "
          f"more than {GAP} units from it: {far}; other objects moved: {others}")
    return 1 if far or others else 0


if __name__ == "__main__":
    sys.exit(main())
