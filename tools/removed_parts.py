"""How much of the disc the "type 8 record with flag 0xB removes a part"
reading takes away (finding 280, PROVEN_RAW_DATA: read from the data, never
from the game's code).

    .venv/Scripts/python tools/removed_parts.py
    .venv/Scripts/python tools/removed_parts.py L02A6 L03A
    .venv/Scripts/python tools/removed_parts.py --json out.json

The observation that started it: the knights of
What's cookin', Doc? 6 (L02A6) are, he is 90% sure, never seen without their
helmet in the game, while six of their thirteen animations "remove" the five
helmet parts with such a record and never put them back. If the reading is
wrong it is not only the helmet: it is every model that uses the record.

Three counts, over every object and template of every level that has a rig:

1. **the flags of the type 8 records**, in the rigs and in the animations:
   finding 280 says type 8 has flag 0 in a rig (it creates the part) and
   ALWAYS 0xB in an animation. If that "always" holds on the whole disc,
   0xB may just be the animation's form of "create", not "remove".
2. **parts an animation removes and never gives back**: a type 8 0xB record
   and no TRS for that part until the end of the stream. With the removal
   reading the part is missing for the whole animation; with a reset
   reading it sits at its rest place.
3. **what the viewer does not draw**: the pose the viewer shows (the game's
   starting role, or the preference), the parts with a mesh left hidden, and
   how many vertices that is. This is what the user can see missing.

Counted once per (level, model, stream): many objects share a model.
It only counts; it changes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter, defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import levels  # noqa: E402
from game import montage  # noqa: E402
from game import rig as rigmod  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

REMOVE_FLAG = 0xB


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code.upper()})" if name else code.upper()


def stream_records(sec4, stream):
    """Every record of a stream, in order, with the block it is in."""
    return [(b, record) for b, (_t, records) in
            enumerate(rigmod.read_blocks(sec4, stream["offset"], stream["size"], 100000))
            for record in records]


def never_given_back(records):
    """The parts a stream removes (type 8, flag 0xB) with no TRS after it, to
    the end of the stream."""
    removed, back = {}, set()
    for b, (part, category, flag, _p) in records:
        if category == rigmod.T_CREATE and flag == REMOVE_FLAG:
            removed.setdefault(part, b)
            back.discard(part)
        elif category == rigmod.T_TRS and part in removed:
            back.add(part)
    return {p for p in removed if p not in back}


def mesh_vertices(sec4, model):
    """Vertices of each TMD part of a model."""
    _magic, _flags, nobj = struct.unpack_from("<III", sec4, model["offset"])
    basis = model["offset"] + 12
    return [struct.unpack_from("<i", sec4, basis + 28 * i + 4)[0] for i in range(nobj)]


def survey(code, file_path, flags_in_rigs, flags_in_anims):
    table = texmod.construct(os.path.dirname(file_path), code, "extracted")
    level = Level(file_path, "extracted", table, None,
                  level_cache.fetch("extracted", code, level_cache.signature(file_path)) or {})
    sec4 = level.sec4
    res = {r["id"]: r for r in level.lvl["resources"]}
    seen_streams, seen_models = set(), {}
    never = []            # (model, stream role, parts, vertices)
    shown_missing = {}    # model -> (objects, parts, vertices, total vertices, role)
    for n, o in enumerate(level.lvl["objects"]):
        mid = next((r for r in o["resources"] if res.get(r, {}).get("data_kind") == "model"), None)
        if mid is None or res[mid]["size"] <= 12:
            continue
        streams = [res[r] for r in o["resources"]
                   if res.get(r, {}).get("data_kind") == "stream" and res[r]["offset"] is not None]
        rigs = [s for s in streams if rigmod.is_stream(sec4, s["offset"]) == 1]
        anims = [s for s in streams if rigmod.is_stream(sec4, s["offset"]) in (2, 4)]
        if not rigs:
            continue
        rig = rigs[0]
        verts = mesh_vertices(sec4, res[mid])
        rest = rigmod.construct(sec4, rig["offset"], rig["size"])
        mesh_of = {d.id: d.mesh - 1 for d in rest.values() if d.mesh}
        # 1. the flags, once per stream
        for s, where in [(rig, flags_in_rigs)] + [(a, flags_in_anims) for a in anims]:
            if s["id"] in seen_streams:
                continue
            for _b, (_part, category, flag, _p) in stream_records(sec4, s):
                if category == rigmod.T_CREATE:
                    where[flag] += 1
        # 2. removed and never given back, once per (model, stream)
        for a in anims:
            if (mid, a["id"]) in seen_streams:
                continue
            seen_streams.add((mid, a["id"]))
            gone = never_given_back(stream_records(sec4, a))
            parts = sorted(mesh_of[p] for p in gone if p in mesh_of and mesh_of[p] < len(verts))
            if parts:
                never.append({"model": mid, "role": a["role"], "parts": parts,
                              "vertices": sum(verts[i] for i in parts), "of": sum(verts)})
        for s in [rig] + anims:
            seen_streams.add(s["id"])
        # 3. what the viewer does not draw, in the pose it shows
        role = level._role_of(o)
        r2, pose = montage.choose_sources(sec4, o["resources"], res, o, role=role)
        if r2 is None:
            continue
        parts = rigmod.construct(sec4, r2["offset"], r2["size"], pose["offset"] if pose else None,
                                 pose["size"] if pose else 0)
        # a mesh is missing only if NO part that links it is shown: the game
        # draws parts, and the knight links its helmet twice (finding 347)
        linked = defaultdict(list)
        for d in parts.values():
            if d.mesh and d.mesh - 1 < len(verts):
                linked[d.mesh - 1].append(d.hidden)
        hidden = sorted(mesh for mesh, flags in linked.items() if all(flags))
        if hidden:
            entry = shown_missing.setdefault(mid, {"objects": [], "parts": hidden,
                                                   "vertices": sum(verts[i] for i in hidden),
                                                   "of": sum(verts),
                                                   "role": pose["role"] if pose else None,
                                                   "all": len(hidden) == len(linked)})
            entry["objects"].append(n)
    return never, shown_missing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", help="level codes; all of them by default")
    parser.add_argument("--json", dest="json_path", help="the counts, as data")
    args = parser.parse_args(argv)
    file_paths = levels_in(paths.DATA_BZE)
    if args.levels:
        wanted = {c.lower() for c in args.levels}
        file_paths = [p for p in file_paths if os.path.splitext(os.path.basename(p))[0].lower() in wanted]

    flags_in_rigs, flags_in_anims = Counter(), Counter()
    report = {}
    for file_path in file_paths:
        code = os.path.splitext(os.path.basename(file_path))[0]
        try:
            never, missing = survey(code, file_path, flags_in_rigs, flags_in_anims)
        except Exception as error:  # noqa: BLE001
            report[code] = {"error": f"{type(error).__name__}: {error}"}
            print("!", end="", flush=True)
            continue
        report[code] = {"never_given_back": never, "shown_missing": missing}
        print(".", end="", flush=True)
    print()

    print("\n=== 1. flags of the type 8 records ===")
    print(f"in the rigs:       {dict(sorted(flags_in_rigs.items()))}")
    print(f"in the animations: {dict(sorted(flags_in_anims.items()))}")

    rows = [(code, r) for code, r in report.items() if "error" not in r]
    never_all = [(code, e) for code, r in rows for e in r["never_given_back"]]
    print(f"\n=== 2. parts an animation removes and never gives back: "
          f"{len(never_all)} (model, animation) pairs, {len({(c, e['model']) for c, e in never_all})} "
          f"models, in {len({c for c, _e in never_all})} levels ===")
    by_level = defaultdict(list)
    for code, e in never_all:
        by_level[code].append(e)
    for code in sorted(by_level, key=lambda c: -len(by_level[c]))[:30]:
        es = by_level[code]
        models = sorted({e["model"] for e in es})
        print(f"  {in_prose(code)[:52]:52s} {len(es):4d} animations of {len(models):3d} models")

    missing_all = [(code, mid, e) for code, r in rows for mid, e in r["shown_missing"].items()]
    partial = [(c, m, e) for c, m, e in missing_all if not e["all"]]
    print(f"\n=== 3. what the viewer does not draw, in the pose it shows: "
          f"{len(missing_all)} models in {len({c for c, _m, _e in missing_all})} levels "
          f"({sum(len(e['objects']) for _c, _m, e in missing_all)} objects) ===")
    print(f"  of which the WHOLE model is hidden (it starts invisible): "
          f"{len(missing_all) - len(partial)}")
    print(f"  of which only SOME parts are hidden (a piece missing): {len(partial)}, "
          f"{sum(e['vertices'] for _c, _m, e in partial)} vertices")
    for code, mid, e in sorted(partial, key=lambda x: -x[2]["vertices"])[:40]:
        print(f"    {in_prose(code)[:46]:46s} model {mid:4d} role {e['role']!s:>4s}  "
              f"{len(e['objects']):3d} objects  parts {e['parts']}  "
              f"{e['vertices']:4d} of {e['of']:4d} vertices")

    broken = {c: r["error"] for c, r in report.items() if "error" in r}
    if broken:
        print("\nlevels that would not open:", broken)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump({"flags_in_rigs": flags_in_rigs, "flags_in_anims": flags_in_anims,
                       "levels": report}, f, indent=1, default=str)
        print("written to", args.json_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
