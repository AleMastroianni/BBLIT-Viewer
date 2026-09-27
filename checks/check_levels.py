"""Check of bblit/game/levels.py against the executable's level table and
against the disc.

    .venv/Scripts/python checks/check_levels.py

1. every LevID points, in the bugs.exe table (111 entries of 24 bytes from
   `..\\BZE\\TITLE.BZE;1`), to the file levels.py assigns to it;
2. every file on the disc with a 3D environment (terrain in the load script)
   is in the menu, and every file in the menu exists on the disc.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bblit"))
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402


def exe_level_table():
    data = open(paths.GAME_EXE, "rb").read()
    i = data.find(b"..\\BZE\\TITLE.BZE")
    output = []
    for k in range(111):
        item = data[i + 24 * k: i + 24 * (k + 1)].split(b"\0")[0].decode("latin1")
        output.append(item.split("\\")[-1].split(".")[0].upper())
    return output


def main():
    errors = 0
    exe = exe_level_table() if paths.GAME_EXE and os.path.exists(paths.GAME_EXE) else None
    menu_items = list(levels.all_entries())
    for levid, file, _era, title_text, _part, note, extra in menu_items:
        if levid is None:
            continue
        if exe is not None and exe[levid] != file.upper():
            print(f"LevID {levid}: levels.py says {file}, the executable {exe[levid]}")
            errors += 1
    print(f"1. {sum(1 for v in menu_items if v[0] is not None)} entries with LevID checked"
          + ("" if exe is not None else " (bugs.exe not found: BBLIT_DATA is not a game folder)"))

    in_menu = {v[1].upper() for v in menu_items}
    on_disc = {}
    for f in os.listdir(paths.DATA_BZE):
        if f.lower().endswith(".bze"):
            on_disc[os.path.splitext(f)[0].upper()] = f
    for file in sorted(in_menu - set(on_disc)):
        print(f"{file}: in the menu but not on the disc")
        errors += 1
    outside = 0
    for name, f in sorted(on_disc.items()):
        if name in in_menu:
            continue
        sec = sections(os.path.join(paths.DATA_BZE, f), os.path.join(paths.PROJECT_DIR, "extracted"))
        lvl = loadscript.export_level(loadscript.parse(sec[1])[0]) if 1 in sec else {"terrain": []}
        if lvl["terrain"]:
            print(f"{f}: has a 3D environment but is not in the menu")
            errors += 1
        else:
            outside += 1
    print(f"2. {len(in_menu)} files in the menu; {outside} files without a 3D environment stay out")
    print("all consistent" if not errors else f"{errors} inconsistencies")
    return errors


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
