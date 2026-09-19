"""Check of tools/levels.py against its two sources and against the disc.

    .venv/Scripts/python tools/diagnostics/check_levels.py

1. every LevID points, in the bugs.exe table (111 entries of 24 bytes from
   `..\\BZE\\TITLE.BZE;1`), to the file levels.py assigns to it;
2. in the LevID spreadsheet, if there is one (`LEVEL_ID_SHEET` in the working
   copy's `local_data.py`), row LevID - 1 contains the title and the note;
3. every file on the disc with a 3D environment (terrain in the load script)
   is in the menu, and every file in the menu exists on the disc.

The spreadsheet is read as a zip (xlsx = XML), with no extra libraries.
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import levels  # noqa: E402
import loadscript  # noqa: E402
import paths  # noqa: E402
from viewer import sections  # noqa: E402

SPREADSHEET = getattr(paths.LOCAL, "LEVEL_ID_SHEET", None)


def exe_level_table():
    data = open(paths.GAME_EXE, "rb").read()
    i = data.find(b"..\\BZE\\TITLE.BZE")
    output = []
    for k in range(111):
        item = data[i + 24 * k: i + 24 * (k + 1)].split(b"\0")[0].decode("latin1")
        output.append(item.split("\\")[-1].split(".")[0].upper())
    return output


def sheet_rows():
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(SPREADSHEET)
    shared_strings = ["".join(t.text or "" for t in si.iter(ns + "t"))
                 for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(ns + "si")]
    lines = []
    for row in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(ns + "row"):
        texts = []
        for c in row.findall(ns + "c"):
            v = c.find(ns + "v")
            if c.get("t") == "s" and v is not None:
                texts.append(shared_strings[int(v.text)])
        lines.append(" ".join(texts))
    return lines


def main():
    errors = 0
    exe = exe_level_table() if paths.GAME_EXE and os.path.exists(paths.GAME_EXE) else None
    lines = sheet_rows() if SPREADSHEET and os.path.exists(SPREADSHEET) else None
    menu_items = list(levels.all_entries())
    for levid, file, _era, title_text, _part, note, extra in menu_items:
        title_text = extra.get("sheet_name", title_text)
        note = extra.get("sheet_note", note)
        if levid is None:
            continue
        if exe is not None and exe[levid] != file.upper():
            print(f"LevID {levid}: levels.py says {file}, the executable {exe[levid]}")
            errors += 1
        if lines is not None:
            row = lines[levid - 1].lower() if levid >= 1 else lines[0].lower()
            words = [title_text] if levid >= 1 else ["main menu"]
            if note and isinstance(note, str):     # a game name with no spreadsheet note: nothing to compare
                words.append(note)
            for p in words:
                if p.lower() not in row:
                    print(f"LevID {levid}: '{p}' is not in the spreadsheet row: {lines[levid - 1]}")
                    errors += 1
    print(f"1-2. {sum(1 for v in menu_items if v[0] is not None)} entries with LevID checked"
          + ("" if exe is not None else " (bugs.exe not found: BBLIT_DATA is not a game folder)")
          + ("" if lines is not None else " (no spreadsheet: executable only)"))

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
    print(f"3. {len(in_menu)} files in the menu; {outside} files without a 3D environment stay out")
    print("all consistent" if not errors else f"{errors} inconsistencies")
    return errors


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
