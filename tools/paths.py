"""Where the viewer, its resources and the game's levels are.

No game data ships with the viewer: the `.bze` levels are read, in order, from
the folder chosen in General options, from `bze_levels/` next to the viewer,
and from the game folder given by the `BBLIT_DATA` environment variable (a
game folder or its `Datas\\bze`). The command-line tools use the same
folder by default (`DATA_BZE`).

A working copy can add its own copy of the game with a `local_data.py` next
to this file, outside the public repository: `game_dir(app_dir)` returns the
game folder (or None), and any other name it defines is available as
`paths.LOCAL`.
"""

from __future__ import annotations

import os
import sys

try:
    import local_data as LOCAL        # only in a working copy, never published
except ImportError:
    LOCAL = None

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The viewer folder: the project folder, or the folder of `BBLIT Viewer.exe`
# when it runs as an executable (PyInstaller). That is where portable.flag,
# userdata/, the level cache and bze_levels/ live.
IS_FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if IS_FROZEN else PROJECT_DIR
# icon and background: inside the executable if there, otherwise next to it
RESOURCES_DIR = (os.path.join(getattr(sys, "_MEIPASS", ""), "resources") if IS_FROZEN
           else os.path.join(PROJECT_DIR, "resources"))
# where the user copies the game's levels (the Datas/bze folder)
LEVELS_DIR = os.path.join(APP_DIR, "bze_levels")


def has_levels(folder: str | None) -> bool:
    """A folder with at least one .bze file."""
    try:
        return bool(folder) and any(f.lower().endswith(".bze") for f in os.listdir(folder))
    except OSError:
        return False


# the game folder: BBLIT_DATA first, then the working copy's own
GAME_DIR = (os.environ.get("BBLIT_DATA")
            or (LOCAL.game_dir(APP_DIR) if LOCAL is not None else None))
if GAME_DIR and has_levels(os.path.join(GAME_DIR, "Datas", "bze")):
    DATA_BZE = os.path.join(GAME_DIR, "Datas", "bze")
elif GAME_DIR and has_levels(GAME_DIR):
    DATA_BZE = GAME_DIR               # BBLIT_DATA pointing at Datas\bze itself
else:
    DATA_BZE = LEVELS_DIR
# the game's executable (the level table), when the whole game folder is known
GAME_EXE = os.path.join(GAME_DIR, "Datas", "bin", "bugs.exe") if GAME_DIR else None


def find_levels_folder(selected: str | None = None) -> str | None:
    """Where to read the levels from, in order: the folder chosen by the user
    (General options or --data), `bze_levels/` next to the viewer, then the
    game folder (`DATA_BZE`)."""
    for candidate_dir in (selected, LEVELS_DIR, DATA_BZE):
        if has_levels(candidate_dir):
            return candidate_dir
    return None
