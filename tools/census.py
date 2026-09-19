"""Census of rendering defects, one row per level.

"There are still many errors" does not tell whether a fix improves anything.
This script counts, with the same reading the viewer uses, everything
the viewer draws wrong or does not draw, and separates it by cause:

  terrain   rejected sectors, sectors that do not end on the expected byte,
            chains that do not close on the vertices, rejected primitives
  textures  faces citing an id the cumulative table does not know
  modes     records never read because the chain stops on an unknown mode;
            0x4A/0x4E faces with the semi-transparency bit, which the reader
            draws opaque because the blend is read only in the UV modes
  props     placed objects without a model, with an empty model, multi-part
            without a rig, with a rig but no usable pose, with parts that have a
            mesh but no transform, exceptions while reading

A non-zero number is not automatically an error: the empty TMD and the
trigger without a model are the file saying "draw nothing". That is why
the columns are kept separate and not summed into a single score.

    python tools/census.py                  # L03A, L03ACOM, L03A2
    python tools/census.py L01A MERLIN
    python tools/census.py --all-levels     # all playable levels
    python tools/census.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402
import export_obj as geo  # noqa: E402
import loadscript  # noqa: E402
import montage  # noqa: E402
import textures as texmod  # noqa: E402

DATA = paths.DATA_BZE

# (key, short header, explanation) in the order they are printed
COLUMNS = [
    ("facce", "facce", "drawable faces read (terrain + props)"),
    ("ls_unknown", "ls?", "unrecognized load script bytes"),
    ("t_sector_errors", "sett!", "terrain sectors rejected or not ending on the expected byte"),
    ("t_chain_errors", "cat!", "terrain chunks whose chain does not end on the vertices"),
    ("rejected", "resp", "rejected primitives (index outside the part)"),
    ("unknown_mode", "modo?", "records never read: the chain stops on an unknown mode"),
    ("tex_unknown", "tex?", "faces citing a texture not registered in the chain"),
    ("blend_ignored", "semi0", "semi-transparent 0x4A/0x4E faces drawn opaque"),
    ("p_placed", "props", "placed objects (not the model-less ones, not the excluded triggers)"),
    ("p_no_model", "noMod", "placed 0x07 objects with no model at all"),
    ("p_empty", "vuoto", "objects with empty TMD (12 bytes): the file says not to draw"),
    ("p_no_rig", "noRig", "multi-part models without a rig: parts stacked on the origin"),
    ("p_no_pose", "noPos", "rig found but no pose with transforms"),
    ("p_loose_parts", "parti", "parts with a mesh but no transform, in total"),
    ("p_errors", "exc", "objects whose reading raises an exception"),
    ("pose_fallback", "pos~", "rigged objects whose pose does NOT come from the state -> step -> role chain"),
    ("sky_dome", "sky", "props as large as the level (sky or sea), off by default"),
]


def census_level(name: str, data_dir: str = DATA, cache: str = "extracted") -> dict:
    file_path = texmod.find_level_file(data_dir, name)
    if file_path is None:
        raise FileNotFoundError(name)
    sec = texmod.sections(file_path, cache, ids=(1, 3, 4))
    blocks, ls_stat = loadscript.parse(sec[1])
    lvl = loadscript.export_level(blocks)
    sec4 = sec[4]
    table = texmod.construct(data_dir, name, cache)

    r = {k: 0 for k, _, _ in COLUMNS}
    r["ls_unknown"] = ls_stat["unknown"]
    prim: dict = {}
    pose_stat: dict = {}
    failures: list[str] = []

    def count_textures(faces):
        for vl in faces:
            if vl.tex_id is not None and vl.tex_id not in table:
                r["tex_unknown"] += 1
        r["facce"] += len(faces)

    # ---- terrain
    diag_lo, diag_hi = [1e18] * 3, [-1e18] * 3
    for t in lvl["terrain"]:
        vertices, faces, st = geo.read_terrain(sec4, t["offset"])
        # a rejected sector (wrong point-block tag) is not "clean",
        # so this difference covers both
        r["t_sector_errors"] += st["sectors"] - st["wall_sectors"] - st["clean"]
        r["t_chain_errors"] += 0 if st.get("ends_on_vertices") else 1
        count_textures(faces)
        # second reading for the census: same records, but with the index
        # checked against the sector's point block (see _count_terrain_modes)
        r["rejected"] += _count_terrain_modes(sec4, t["offset"], prim)
        for p in vertices:
            q = [p[0] + t["translation"][0], p[1] + t["translation"][1], p[2] + t["translation"][2]]
            for k in range(3):
                diag_lo[k] = min(diag_lo[k], q[k])
                diag_hi[k] = max(diag_hi[k], q[k])
    diagonal = max(h - l for h, l in zip(diag_hi, diag_lo)) if lvl["terrain"] else 1.0

    # ---- props, with the same selection as the viewer
    res = {x["id"]: x for x in lvl["resources"]}
    models = {x["id"]: x for x in lvl["resources"] if x["data_kind"] == "model"}
    for n, o in enumerate(lvl["objects"]):
        if not o["position"] or o["block_type"] == 0x08:
            continue
        mid = next((x for x in o["resources"] if x in models), None)
        if mid is None:
            if o["block_type"] == 0x07:
                r["p_no_model"] += 1
            continue
        m = models[mid]
        if m["size"] <= 12:
            r["p_empty"] += 1
            continue
        r["p_placed"] += 1
        try:
            nobj = struct.unpack_from("<I", sec4, m["offset"] + 8)[0]
            rig_r, pose_r = montage.choose_sources(sec4, o["resources"], res, o, pose_stat)
            trans = montage.transforms(sec4, o["resources"], res, o)
            if nobj > 1:
                if rig_r is None:
                    r["p_no_rig"] += 1
                elif pose_r is None:
                    r["p_no_pose"] += 1
                if trans is not None:
                    basis = m["offset"] + 12
                    for i in range(nobj):
                        n_prim = struct.unpack_from("<i", sec4, basis + 28 * i + 20)[0]
                        if n_prim > 0 and i not in trans:
                            r["p_loose_parts"] += 1
            vertices, faces, n_rejected = geo.read_model(sec4, m["offset"], trans, stat=prim)
        except Exception as e:  # noqa: BLE001
            r["p_errors"] += 1
            failures.append(f"object {n} model {mid}: {type(e).__name__}: {e}")
            continue
        r["rejected"] += n_rejected
        count_textures(faces)
        if vertices:
            span = max(max(p[k] for p in vertices) - min(p[k] for p in vertices) for k in range(3))
            scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            if span * scale_factor > 0.8 * diagonal:
                r["sky_dome"] += 1

    r["pose_fallback"] = pose_stat.get("fallback", 0)
    r["unknown_mode"] = prim.get("unknown_mode", 0)
    r["blend_ignored"] = sum(c for (mode, flag_byte), c in prim.get("per_flag", {}).items()
                              if mode in (0x4A, 0x4E) and flag_byte & 0x08)
    r["per_mode"] = {f"0x{k:02X}": v for k, v in sorted(prim.get("per_mode", {}).items())}
    r["per_flag"] = {f"0x{m:02X}/0x{v:02X}": c for (m, v), c in sorted(prim.get("per_flag", {}).items())}
    r["failures"] = failures
    return r


def _count_terrain_modes(sec4: bytes, offset: int, prim: dict) -> int:
    """Replays the sector chain (export_obj.terrain_sectors) to count modes,
    flags and out-of-block indices.

    `read_terrain` translates a local index with `local_start + i` without
    comparing it to the point block size: an index that is too large
    is not rejected, but lands on a point of the NEXT sector, which
    the viewer appends afterwards. Here the index is checked, and the number of
    faces that would fall outside is what gets returned.
    """
    def index_checker(n):
        def index_map(k):
            if k >= n:
                raise IndexError(k)
            return k
        return index_map

    rejected = 0
    _magic, _vl, nobj = struct.unpack_from("<III", sec4, offset)
    basis = offset + 12
    for i in range(nobj):
        _vt, _nv, _nt, _nn, pt, n_prim, _s = struct.unpack_from("<7i", sec4, basis + 28 * i)
        for sector in geo.terrain_sectors(sec4, basis + pt, n_prim):
            if sector.kind == "sector":
                _vl, _next_pos, n_rejected = geo.read_primitives(sec4, sector.prims_pos, sector.prim_count,
                                                                 index_checker(sector.point_count), stat=prim)
                rejected += n_rejected
    return rejected


def playable_levels(data_dir: str) -> list[str]:
    names = []
    for f in sorted(os.listdir(data_dir)):
        stem, ext = os.path.splitext(f)
        if ext.lower() != ".bze":
            continue
        if stem.lower().startswith(("l_", "screen", "loading", "cc", "credits", "title")):
            continue
        if stem.lower().endswith("_8"):
            continue     # software renderer variants
        names.append(stem)
    return names


def main() -> None:
    p = argparse.ArgumentParser(description="census of rendering defects per level")
    p.add_argument("levels", nargs="*", default=["L03A", "L03ACOM", "L03A2"])
    p.add_argument("--all-levels", action="store_true", help="all playable levels")
    p.add_argument("--data", default=DATA)
    p.add_argument("--cache", default="extracted")
    p.add_argument("--json", help="also write the full counts to a JSON file")
    p.add_argument("--details", action="store_true", help="print modes and flags per level")
    args = p.parse_args()

    levels = playable_levels(args.data) if args.all_levels else args.levels
    header = f"{'level':<10}" + "".join(f"{h:>7}" for _, h, _ in COLUMNS)
    print(header)
    print("-" * len(header))
    total = {k: 0 for k, _, _ in COLUMNS}
    everything = {}
    for name in levels:
        try:
            r = census_level(name, args.data, args.cache)
        except FileNotFoundError:
            print(f"{name:<10} not found")
            continue
        everything[name] = r
        for k, _, _ in COLUMNS:
            total[k] += r[k]
        print(f"{name:<10}" + "".join(f"{r[k]:>7}" for k, _, _ in COLUMNS), flush=True)
        if args.details:
            print(f"{'':10}modes: {r['per_mode']}")
            print(f"{'':10}mode/flag: {r['per_flag']}")
        for failure in r["failures"][:5]:
            print(f"{'':10}! {failure}")
    print("-" * len(header))
    print(f"{'TOTAL':<10}" + "".join(f"{total[k]:>7}" for k, _, _ in COLUMNS))
    print()
    for k, h, explanation in COLUMNS:
        print(f"  {h:>6}  {explanation}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"levels": everything, "total": total}, f, indent=1)


if __name__ == "__main__":
    main()
