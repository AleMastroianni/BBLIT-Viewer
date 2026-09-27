"""Exports a level's terrain and props to OBJ + MTL, from the geometry the
viewer reads (`bblit/game/geometry.py`).

    .venv/Scripts/python tools/obj_export.py SECTION4 LEVEL.json -o out.obj

Kept for looking at a level in Blender or another program from the
command line; the viewer's own export is Level options -> Export
(`bblit/support/export.py`), with the same writer (`bblit/game/obj_writer.py`).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bblit"))
from game.geometry import _rotation_matrix, read_model, read_terrain  # noqa: E402
from game.obj_writer import ObjWriter  # noqa: E402
from support import paths  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="a level's terrain and props -> OBJ")
    p.add_argument("section4", help="decompressed section id 4 (model block)")
    p.add_argument("json", help="load script extract")
    p.add_argument("-o", "--output", required=True, help=".obj file to write")
    p.add_argument("--no-props", action="store_true", help="terrain only")
    p.add_argument("--units", action="store_true", help="original units instead of meters")
    p.add_argument("--section3", help="section id 3, to know the texture sizes")
    p.add_argument("--chain", metavar="LEVEL", help="use the cumulative texture table")
    p.add_argument("--data", default=paths.DATA_BZE)
    p.add_argument("--textures-dir", default="textures",
                   help="texture folder referenced by the .mtl file")
    args = p.parse_args()

    with open(args.section4, "rb") as f:
        sec4 = f.read()
    with open(args.json, encoding="utf-8") as f:
        lvl = json.load(f)

    sizes = {}
    if args.chain:
        from game import textures as texmod
        from game import tim
        table = texmod.construct(args.data, args.chain, "extracted")
        for tid, (block, off) in table.slots.items():
            sizes.update(tim.sizes(block, [{"id": tid, "offset": off}]))
    elif args.section3:
        from game import tim
        with open(args.section3, "rb") as f:
            sizes = tim.sizes(f.read(), lvl["textures"])

    meters = not args.units
    w = ObjWriter(sizes)

    for i, t in enumerate(lvl["terrain"]):
        vertices, faces, stat = read_terrain(sec4, t["offset"])
        w.add_group(f"terrain_{i}", vertices, faces, pos=tuple(t["translation"]), meters=meters)
        print(f"terrain {i}: {stat['sectors']} sectors ({stat['wall_sectors']} invisible walls), "
              f"{len(faces)} drawable faces, {stat['polygons']}/{stat['expected']} expected polygons, "
              f"exact sectors {stat['clean']}/{stat['sectors']}, rejected {stat['rejected']}, chain ends on vertices: {stat.get('ends_on_vertices')}")

    if not args.no_props:
        models = {r["id"]: r for r in lvl["resources"] if r["data_kind"] == "model"}
        placed = n_empty = missing = 0
        for n, o in enumerate(lvl["objects"]):
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None:
                missing += 1
                continue
            res = models[mid]
            if res["size"] <= 12:
                n_empty += 1          # empty TMD: the file says "draw nothing"
                continue
            from game import montage
            trans = montage.transforms(sec4, o["resources"], {r["id"]: r for r in lvl["resources"]}, o)
            vertices, faces, _n_rejected = read_model(sec4, res["offset"], trans)
            # parts removed by the pose (finding 280) have all vertices at
            # one point: they are not needed in the OBJ
            faces = [vl for vl in faces if len({vertices[h] for h in vl.corners}) > 1]
            if not faces:
                continue
            rot = _rotation_matrix(o["rotation"]) if o["rotation"] else None
            scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            w.add_group(f"obj{n}_res{mid}", vertices, faces,
                       rot=rot, scale_factor=scale_factor, pos=tuple(o["position"]), meters=meters)
            placed += 1
        print(f"props: {placed} placed, {n_empty} with empty model, {missing} without model")

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    mtl, n_tex = w.write_obj(args.output, args.textures_dir)
    if w.untextured_count:
        print(f"faces naming an unregistered texture, drawn with vertex color: {w.untextured_count}")
    print(f"wrote {args.output}: {len(w.v)} vertices, "
          f"{sum(len(l) for l in w.face_groups.values())} faces, {n_tex} textures in {os.path.basename(mtl)}")


if __name__ == "__main__":
    main()
