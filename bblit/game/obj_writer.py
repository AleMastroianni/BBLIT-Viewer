"""OBJ + MTL from the geometry the viewer reads (`game/geometry.py`): the
writer of `tools/obj_export.py` and of the Export page (`support/export.py`).
"""

from __future__ import annotations

import os

from game.geometry import BLEND_MODES, _transform, triangles, uv_to_texture

# the four PlayStation blend modes by name, for the comment in the MTL
# (BLEND_MODES has the formulas)
BLEND_WORDS = {0: "half", 1: "add", 2: "subtract", 3: "quarter"}


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

    def face_count(self) -> int:
        return sum(len(entries) for entries in self.face_groups.values())

    def texture_ids(self) -> set:
        return {t for entries in self.face_groups.values() for _, _, t, _ in entries if t is not None}

    def write_obj(self, obj_path, texture_dir="textures", texture_file=None, cut_outs=()):
        """`texture_file(id)`: the image's path as the MTL names it
        (default `<texture_dir>/<id>.png`). A texture in `cut_outs` (with
        see-through texels) also gets its image as the alpha map, so the
        leaves and railings keep their shape."""
        if texture_file is None:
            def texture_file(t):
                return f"{texture_dir}/{t}.png"
        mtl_path = os.path.splitext(obj_path)[0] + ".mtl"
        materials = {(t, m) for entries in self.face_groups.values()
                      for _, _, t, m in entries if t is not None}
        textures = {t for t, _ in materials}

        with open(mtl_path, "w", encoding="utf-8") as m:
            m.write("newmtl color\nKd 1 1 1\n\n")
            for t, blend in sorted(materials, key=lambda x: (x[0], -1 if x[1] is None else x[1])):
                name = f"tex{t}" if blend is None else f"tex{t}_m{blend}"
                m.write(f"newmtl {name}\nKd 1 1 1\nmap_Kd {texture_file(t)}\n")
                if t in cut_outs:
                    m.write(f"map_d {texture_file(t)}\n")
                if blend is None:
                    m.write("d 1\n\n")
                else:
                    # OBJ only knows dissolve: additive and subtractive
                    # cannot be expressed and must be set by hand in Blender
                    m.write(f"d {0.5 if blend == 0 else 0.75}\n"
                            f"# PSX blend {blend}: {BLEND_WORDS[blend]}, {BLEND_MODES[blend][1]}\n\n")

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
