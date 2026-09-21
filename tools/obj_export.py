"""Exports a level's terrain and props to OBJ + MTL, from the geometry the
viewer reads (`bblit/game/geometry.py`).

    .venv/Scripts/python tools/obj_export.py SECTION4 LEVEL.json -o out.obj

Kept for looking at a level in Blender or another program: the viewer
itself has no intermediate format.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bblit"))
from game.geometry import (BLEND_MODES, _rotation_matrix, _transform, read_model,  # noqa: E402
                           read_terrain, triangles, uv_to_texture)
from support import paths  # noqa: E402

class ObjWriter:
    """Collects vertices and faces and writes OBJ + MTL."""

    def __init__(self, sizes=None):
        self.v: list[tuple[float, float, float]] = []
        self.vc: list[tuple[int, int, int]] = []
        self.vt: list[tuple[float, float]] = []
        self.face_groups: dict[str, list] = {}
        self.sizes = sizes or {}
        self.untextured_count = 0

    def add_group(self, face_group, vertices, faces, **kw):
        basis = len(self.v)
        for p in vertices:
            self.v.append(_transform(p, **kw))
            self.vc.append((128, 128, 128))
        entries = self.face_groups.setdefault(face_group, [])
        for vl in faces:
            for h, k in zip(vl.corners, vl.colors):
                self.vc[basis + h] = k

            # a face naming a texture the level does not register
            # is not textured: the vertex color applies
            tex_id = vl.tex_id if vl.tex_id in self.sizes else None
            if vl.tex_id is not None and tex_id is None:
                self.untextured_count += 1

            uv_idx = None
            if vl.uvs and tex_id is not None:
                uv_idx = []
                for (u, vv) in vl.uvs:
                    tu, tv = uv_to_texture(u, vv, self.sizes[tex_id])
                    self.vt.append((tu, 1.0 - tv))
                    uv_idx.append(len(self.vt))

            # triangles are written, not polygons: a quad left to the
            # importer would be closed as a fan, which is wrong here
            for tri in triangles(len(vl.corners)):
                corners = [basis + vl.corners[i] + 1 for i in tri]
                uv = [uv_idx[i] for i in tri] if uv_idx else None
                entries.append((corners, uv, tex_id, vl.blend if tex_id is not None else None))

    def write_obj(self, obj_path, texture_dir="textures"):
        mtl_path = os.path.splitext(obj_path)[0] + ".mtl"
        materials = {(t, m) for entries in self.face_groups.values()
                      for _, _, t, m in entries if t is not None}
        textures = {t for t, _ in materials}

        with open(mtl_path, "w", encoding="utf-8") as m:
            m.write("newmtl color\nKd 1 1 1\n\n")
            for t, blend in sorted(materials, key=lambda x: (x[0], -1 if x[1] is None else x[1])):
                name = f"tex{t}" if blend is None else f"tex{t}_m{blend}"
                m.write(f"newmtl {name}\nKd 1 1 1\nmap_Kd {texture_dir}/{t}.png\n")
                if blend is None:
                    m.write("d 1\n\n")
                else:
                    # OBJ only knows dissolve: additive and subtractive
                    # cannot be expressed and must be set by hand in Blender
                    blend_name, blend_formula = BLEND_MODES[blend]
                    m.write(f"d {0.5 if blend == 0 else 0.75}\n"
                            f"# fusione PSX {blend}: {blend_name}, {blend_formula}\n\n")

        with open(obj_path, "w", encoding="utf-8") as f:
            f.write(f"mtllib {os.path.basename(mtl_path)}\n")
            for (x, y, z), (r, g, b) in zip(self.v, self.vc):
                f.write(f"v {x:.4f} {y:.4f} {z:.4f} {r/255:.3f} {g/255:.3f} {b/255:.3f}\n")
            for u, vv in self.vt:
                f.write(f"vt {u:.5f} {vv:.5f}\n")
            for face_group, entries in self.face_groups.items():
                f.write(f"g {face_group}\n")
                current_mtl = None
                for corners, uv_idx, tex_id, blend in sorted(
                        entries, key=lambda r: (r[2] is None, r[2] or 0, -1 if r[3] is None else r[3])):
                    if tex_id is None:
                        mat = "color"
                    else:
                        mat = f"tex{tex_id}" if blend is None else f"tex{tex_id}_m{blend}"
                    if mat != current_mtl:
                        f.write(f"usemtl {mat}\n")
                        current_mtl = mat
                    uv = uv_idx  # order and winding already fixed in add_group
                    if uv:
                        f.write("f " + " ".join(f"{h}/{t}" for h, t in zip(corners, uv)) + "\n")
                    else:
                        f.write("f " + " ".join(str(h) for h in corners) + "\n")
        return mtl_path, len(textures)


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
