"""On the whole disc: for every level, how the walls that stop Bugs are
shown by the flags Hard walls and Steps, now that a wall is drawn on the
game's face where the game has one on it (walls.py) and as a panel where it
has none. The east side of the crates of Hey... What's up, Dock? 1 stopped
him and was not coloured, and there were many like it: this counts them.

    .venv/Scripts/python tools/wall_coverage.py [L03A ...]

Per level: hard-wall runs, those with nothing drawn (invisible), the runs
that have a game face on them, the faces coloured and the panels drawn;
the same for the steps. By construction every run is either coloured on a
face or drawn as a panel: no run is left without anything, which is the
check this makes. `check_walls.py` still guards the rest.
"""
import os
import sys
from multiprocessing import Pool

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

KEYS = ("hard_walls", "invisible_walls", "wall_runs_with_faces", "wall_faces", "wall_faces_slanted",
        "wall_panels", "step_walls", "step_walls_covered", "hole_steps", "hole_steps_covered", "drop_walls")


def one(path):
    from window.scene import Level
    lvl = Level(path, "extracted", None, None, {}, families={"heightmap"})
    name = os.path.splitext(os.path.basename(path))[0].upper()
    return name, {k: lvl.stat.get(k, 0) for k in KEYS}


def main():
    from support import paths
    from window.scene import levels_in
    files = levels_in(paths.DATA_BZE)
    wanted = {a.upper() for a in sys.argv[1:]}
    if wanted:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0].upper() in wanted]
    with Pool(8) as pool:
        rows = pool.map(one, files)
    print(f"{'level':10s} {'hard':>6s} {'unseen':>6s} {'w/face':>6s} {'faces':>6s} {'slant':>6s} {'panels':>6s} "
          f"{'steps':>6s} {'cover':>6s} {'hole':>6s} {'hcover':>6s} {'drops':>6s}")
    totals = {k: 0 for k in KEYS}
    for name, stat in rows:
        for k in KEYS:
            totals[k] += stat[k]
        print(f"{name:10s} {stat['hard_walls']:6d} {stat['invisible_walls']:6d} {stat['wall_runs_with_faces']:6d} "
              f"{stat['wall_faces']:6d} {stat['wall_faces_slanted']:6d} {stat['wall_panels']:6d} "
              f"{stat['step_walls']:6d} "
              f"{stat['step_walls_covered']:6d} {stat['hole_steps']:6d} {stat['hole_steps_covered']:6d} {stat['drop_walls']:6d}")
    print(f"{'total':10s} {totals['hard_walls']:6d} {totals['invisible_walls']:6d} {totals['wall_runs_with_faces']:6d} "
          f"{totals['wall_faces']:6d} {totals['wall_faces_slanted']:6d} {totals['wall_panels']:6d} "
          f"{totals['step_walls']:6d} "
          f"{totals['step_walls_covered']:6d} {totals['hole_steps']:6d} {totals['hole_steps_covered']:6d} {totals['drop_walls']:6d}")


if __name__ == "__main__":
    main()
