"""The opening camera of every level: inside the level, where the player
starts?

    .venv/Scripts/python checks/check_start_camera.py [L02A6 ...]

The viewer's opening camera (`controls.opening_camera`) stands behind the
player where the level starts (`Level.start_place`): the placed player, or,
when the player is placed at the origin, the object that clones the vehicle
carrying Bugs (Downhill Duck!, finding 330); in the cutscenes, with no
start, inside the terrain box.

Bar fixed before the change: the camera inside the
terrain box, widened by a declared margin of 3 metres (the camera stands 2.5
metres above the player's feet), in 79 levels out of 79. Before the change:
0 of 79 (`tools/survey.py --only camera`: the old formula put it outside in
every level). Also printed: where each start comes from. Exits with 1 below
the bar.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from collections import Counter  # noqa: E402

from game import levels  # noqa: E402
from support import paths  # noqa: E402
from window.controls import opening_camera  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

MARGIN = 3.0


def one_level(file_path):
    code = os.path.splitext(os.path.basename(file_path))[0]
    level = Level(file_path, "extracted", None, None, {}, families=())
    pos, _yaw, _pitch, _speed = opening_camera(level)
    lo, hi = level.terrain_lo, level.terrain_hi
    outside = [max(0.0, lo[i] - MARGIN - pos[i], pos[i] - hi[i] - MARGIN) for i in range(3)]
    start = level.start_place()
    return code, outside, start[4] if start else "none"


def main():
    wanted = {a.lower() for a in sys.argv[1:]}
    file_paths = [p for p in levels_in(paths.DATA_BZE)
                  if not wanted or os.path.splitext(os.path.basename(p))[0].lower() in wanted]
    import concurrent.futures
    with concurrent.futures.ProcessPoolExecutor(max_workers=max(1, min(8, os.cpu_count() or 2))) as pool:
        answers = list(pool.map(one_level, file_paths))
    inside, sources = 0, Counter()
    for code, outside, source in answers:
        sources[source.split()[0]] += 1
        if source.startswith("object"):
            print(f"  from an {source}: {levels.official_name(code) or code} ({code})")
        if any(outside):
            name = levels.official_name(code) or code
            print(f"  OUTSIDE {name} ({code}): by {[round(v, 1) for v in outside]} m on x, y, z")
        else:
            inside += 1
    print(f"starts: {dict(sources)}")
    print(f"{inside} of {len(answers)} levels with the opening camera inside the terrain "
          f"(margin {MARGIN} m; bar: all)")
    return 0 if inside == len(answers) else 1


if __name__ == "__main__":
    sys.exit(main())
