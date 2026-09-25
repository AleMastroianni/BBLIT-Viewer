"""A sheet of the type 14 models whose rig has between N and M parts, on the
whole disc: where the line of "whoever has a head" falls
(`game/catalog.HEAD_PARTS`) is decided by looking at them all together.

    .venv/Scripts/python tools/skeleton_sheet.py [--low 9] [--high 13] [-o sheet.png]

One cell per (level, model), the parts assembled with the rig in the pose
the object starts with (`montage.transforms` with the object), and under it the level's name, the model's number IN THAT LEVEL (a
resource number: the same number in two levels is two different things),
the number of parts, how many animations and states the object has, the
category the catalogue gives it now and one object that uses it. The list
is printed too.
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from game import catalog  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import montage  # noqa: E402
from game import textures as texmod  # noqa: E402
from game import tim  # noqa: E402
from model_sheet import draw_cell  # noqa: E402
from support import paths  # noqa: E402
from window import scene  # noqa: E402

CELL = 300
LABEL = 66
COLUMNS = 5


def _where(cat, lvl, n):
    """A place to look at object n: its own, or its parent's for a clone."""
    for fams in cat.families.values():
        for f in fams:
            for e in f["exemplars"]:
                if e["object"] != n:
                    continue
                o = lvl["objects"][n if e["parent"] is None else e["parent"]]
                place = o.get("position")
                if place and tuple(place) != (0, 0, 0):
                    how = "placed" if e["parent"] is None else f"cloned by object {e['parent']}"
                    return f"{place[0]}, {place[1]}, {place[2]} ({how})"
    return "no place: made by no rule, or parked at the origin"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--low", type=int, default=9)
    ap.add_argument("--high", type=int, default=13)
    ap.add_argument("-o", "--output", default=os.path.join(PROJECT_DIR, "reference", "skeletons_9_13.png"))
    args = ap.parse_args()
    cache = os.path.join(PROJECT_DIR, "extracted")
    cells, table_rows = [], []
    for file_path in scene.levels_in(paths.DATA_BZE):
        code = os.path.splitext(os.path.basename(file_path))[0]
        sec = scene.sections(file_path, cache)
        lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
        res = {r["id"]: r for r in lvl["resources"]}
        cat = catalog.Catalogue(lvl, sec[4])
        table = texmod.construct(paths.DATA_BZE, code, cache)
        seen = set()
        for n, o in enumerate(lvl["objects"]):
            if o.get("category") != 14:
                continue
            mid = catalog.model_of(o, res)
            if mid is None or mid in seen:
                continue
            parts = catalog.skeleton_parts(o, res, sec[4])
            if not args.low <= parts <= args.high:
                continue
            seen.add(mid)
            trans = montage.transforms(sec[4], o["resources"], res, o)
            vertices, faces, _ = geo.read_model(sec[4], res[mid]["offset"], trans)
            tex = {}
            for face in faces:
                if face.tex_id is not None and face.tex_id not in tex:
                    source = table.get(face.tex_id)
                    try:
                        tex[face.tex_id] = tim.read_tim(*source) if source else None
                    except Exception:  # noqa: BLE001
                        tex[face.tex_id] = None
            rgb = draw_cell(vertices, faces, tex, CELL)
            roles = len({s["role"] for s in o.get("steps", ())})
            name = levels.official_name(code) or code
            cells.append((rgb, [f"{name[:34]} ({code})",
                                f"model {mid} (this level) - {parts} parts",
                                f"{roles} anim., {len(o.get('states', ()))} states - "
                                f"{cat.category[n][0]} - obj {n}"]))
            table_rows.append(f"| {name} ({code}) | {mid} | {parts} | {roles} | "
                              f"{len(o.get('states', ()))} | {cat.category[n][0]} | {n} | "
                              f"{_where(cat, lvl, n)} |")
    rows = (len(cells) + COLUMNS - 1) // COLUMNS
    sheet = Image.new("RGB", (COLUMNS * CELL, rows * (CELL + LABEL)), (20, 22, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, (rgb, lines) in enumerate(cells):
        x, y = (i % COLUMNS) * CELL, (i // COLUMNS) * (CELL + LABEL)
        sheet.paste(Image.frombytes("RGB", (CELL, CELL), rgb), (x, y))
        for k, line in enumerate(lines):
            draw.text((x + 6, y + CELL + 4 + 19 * k), line, fill=(235, 235, 235), font=font)
    sheet.save(args.output)
    table = os.path.splitext(args.output)[0] + ".md"
    head = ["# Type 14 models with a skeleton of %d to %d parts" % (args.low, args.high), "",
            "Made by `tools/skeleton_sheet.py`. The model number is a resource number OF THAT LEVEL:",
            "the same number in two levels is two different things. \"Where\" is a game point to go and",
            "look at it: the object's own place, or the place of the object that clones it.", "",
            "| level | model | parts | animations | states | category now | object | where |",
            "|---|---|---|---|---|---|---|---|"]
    with open(table, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(head + table_rows) + "\n")
    print(f"{len(cells)} models, wrote {args.output} and {table}")


if __name__ == "__main__":
    main()
