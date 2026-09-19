"""Renders the same model with every candidate pose, to pick the right one.

A character assembled with the pose of an animation caught mid-movement
comes out with its pieces out of place. Here all the available poses are
viewed side by side.
"""

from __future__ import annotations

import json
import os
import sys

# the tools live one folder up (tools/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import export_obj as geo  # noqa: E402
import rig as rigmod  # noqa: E402
import textures as texmod  # noqa: E402
import tim  # noqa: E402
from model_sheet import draw_cell  # noqa: E402
from render_obj import _png  # noqa: E402

MAP = sys.argv[1]
MODEL = int(sys.argv[2])
OUTPUT_PATH = sys.argv[3]
stem = os.path.basename(MAP)
sec4 = open(os.path.join(MAP, f"{stem}_id04.bin"), "rb").read()
sec3 = open(os.path.join(MAP, f"{stem}_id03.bin"), "rb").read()
lvl = json.load(open(os.path.join(MAP, f"{stem.lower()}.json"), encoding="utf-8"))
res = {r["id"]: r for r in lvl["resources"]}

tex = {}
for t in lvl["textures"]:
    try:
        tex[t["id"]] = tim.read_tim(sec3, t["offset"])
    except Exception:  # noqa: BLE001
        pass

obj = next(o for o in lvl["objects"]
           if o["position"] and o["block_type"] != 0x08 and MODEL in o["resources"])
rigs = [res[i] for i in obj["resources"]
        if i in res and res[i]["data_kind"] == "stream"
        and rigmod.is_stream(sec4, res[i]["offset"]) == 1]
poses = [res[i] for i in obj["resources"]
         if i in res and res[i]["data_kind"] == "stream"
         and rigmod.is_stream(sec4, res[i]["offset"]) in (2, 4)]
print(f"model {MODEL}: rig {rigs[0]['id']}, {len(poses)} candidate poses")

CELL_PX, N_COLS = 170, 6
row_no = (len(poses) + N_COLS - 1) // N_COLS
sheet = bytearray(N_COLS * CELL_PX * row_no * CELL_PX * 3)
for n, p in enumerate(poses):
    parts = rigmod.construct(sec4, rigs[0]["offset"], rigs[0]["size"], p["offset"], p["size"])
    trans = rigmod.transforms(parts)
    vertices, faces, _ = geo.read_model(sec4, res[MODEL]["offset"], trans)
    image_height = (max(v[1] for v in vertices) - min(v[1] for v in vertices)) if vertices else 0
    print(f"  cell {n:>2} (row {n // N_COLS + 1}, col {n % N_COLS + 1}): "
          f"pose {p['id']} role {p['role']}, height {image_height:.0f}")
    rgb = draw_cell(vertices, faces, tex, CELL_PX)
    cx, cy = (n % N_COLS) * CELL_PX, (n // N_COLS) * CELL_PX
    for y in range(CELL_PX):
        o = ((cy + y) * N_COLS * CELL_PX + cx) * 3
        sheet[o : o + CELL_PX * 3] = rgb[y * CELL_PX * 3 : (y + 1) * CELL_PX * 3]

_png(OUTPUT_PATH, N_COLS * CELL_PX, row_no * CELL_PX, bytes(sheet))
print(f"written {OUTPUT_PATH}")
