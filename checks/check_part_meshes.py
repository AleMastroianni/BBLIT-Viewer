"""Parts or meshes: does the viewer draw what the game draws, frame by frame?

    .venv/Scripts/python checks/check_part_meshes.py
    .venv/Scripts/python checks/check_part_meshes.py L02A6 LS01

Finding 347: the game draws PARTS. The scene loop walks the object's chain
and draws the model pointer of every part whose visible byte is on (no
0x8000 bit, a non-zero composed matrix), so one TMD mesh can be on screen
through one part, the other, or both. The knight's rig (model 112) links
the helmet and the visor twice: once on the head (parts 7, 8) and once in a
loose helmet (parts 25, 26).

For every object and template with a rig, every animation stream of it, and
every tick of that stream (from the first complete pose, as the viewer
builds them), this compares:

* the game: how many shown parts link each mesh;
* the viewer: how many copies of the mesh `rig.transforms` puts on screen
  (a copy with an all-zero matrix is a hidden one).

A (level, model, stream, mesh) counts as wrong if at least one tick
disagrees. Counted once per (level, model, stream).

Threshold, fixed before the change: 0 wrong on the whole disc. Measured:
48 before (the four copies of the knight's rig, in
What's cookin', Doc? 1 and 6, "Witch" way to Albuquerque? 2 and The
Carrot-henge Mystery 4), 0 after, over 8,736 (model, stream) pairs and
192,088 ticks. Exits with 1 if anything is wrong.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import levels  # noqa: E402
from game import rig as rigmod  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code.upper()})" if name else code.upper()


def _shown(m) -> bool:
    return any(abs(v) > 1e-12 for row in m for v in row)


def game_counts(parts) -> Counter:
    """Mesh (0-based) -> number of parts that draw it."""
    per_part = rigmod.per_part(parts)
    out = Counter()
    for d in parts.values():
        if d.mesh and not d.hidden and _shown(per_part[d.id][0]):
            out[d.mesh - 1] += 1
    return out


def viewer_counts(parts) -> Counter:
    """Mesh (0-based) -> copies the viewer puts on screen."""
    out = Counter()
    for mesh, value in rigmod.transforms(parts).items():
        copies = value if isinstance(value, list) else [value]
        out[mesh] += sum(1 for m, _t in copies if _shown(m))
    return out


def survey(code, file_path):
    table = texmod.construct(os.path.dirname(file_path), code, "extracted")
    level = Level(file_path, "extracted", table, None,
                  level_cache.fetch("extracted", code, level_cache.signature(file_path)) or {})
    sec4 = level.sec4
    res = {r["id"]: r for r in level.lvl["resources"]}
    seen = set()
    streams = ticks = 0
    wrong = []        # (model, role, mesh, game, viewer, first tick)
    twice = set()     # models whose rig links a mesh from more than one part
    for o in level.lvl["objects"]:
        mid = next((r for r in o["resources"] if res.get(r, {}).get("data_kind") == "model"), None)
        if mid is None or res[mid]["size"] <= 12:
            continue
        st = [res[r] for r in o["resources"]
              if res.get(r, {}).get("data_kind") == "stream" and res[r]["offset"] is not None]
        rigs = [s for s in st if rigmod.is_stream(sec4, s["offset"]) == 1]
        anims = [s for s in st if rigmod.is_stream(sec4, s["offset"]) in (2, 4)]
        if not rigs:
            continue
        rig = rigs[0]
        rest = rigmod.construct(sec4, rig["offset"], rig["size"])
        links = Counter(d.mesh for d in rest.values() if d.mesh)
        if any(c > 1 for c in links.values()):
            twice.add(mid)
        for a in anims:
            if (mid, rig["id"], a["id"]) in seen:
                continue
            seen.add((mid, rig["id"], a["id"]))
            streams += 1
            parts, done = {}, set()
            for _t, records in rigmod.read_blocks(sec4, rig["offset"], rig["size"], 64):
                rigmod._apply_records(parts, done, records)
            started, bad = False, {}
            for tick, (_t, records) in enumerate(rigmod.read_blocks(sec4, a["offset"], a["size"], 600)):
                rigmod._apply_records(parts, done, records)
                if not started and not rigmod._complete(parts, done):
                    continue
                started = True
                ticks += 1
                g, v = game_counts(parts), viewer_counts(parts)
                for mesh in set(g) | set(v):
                    if g[mesh] != v[mesh] and mesh not in bad:
                        bad[mesh] = (g[mesh], v[mesh], tick)
            for mesh, (gc, vc, tick) in sorted(bad.items()):
                wrong.append((mid, a["role"], mesh, gc, vc, tick))
    return streams, ticks, wrong, twice


def one_level(file_path):
    """The survey of one level, or its error: run in its own process."""
    code = os.path.splitext(os.path.basename(file_path))[0]
    try:
        return code, survey(code, file_path), None
    except Exception as error:  # noqa: BLE001
        return code, None, f"{type(error).__name__}: {error}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", help="level codes; all of them by default")
    args = parser.parse_args(argv)
    file_paths = levels_in(paths.DATA_BZE)
    if args.levels:
        wanted = {c.lower() for c in args.levels}
        file_paths = [p for p in file_paths if os.path.splitext(os.path.basename(p))[0].lower() in wanted]
    if len(file_paths) < 2:
        answers = [one_level(p) for p in file_paths]
    else:
        import concurrent.futures
        workers = max(1, min(8, (os.cpu_count() or 2)))
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            # in the order of the files: the printed lines must not depend on the machine
            answers = list(pool.map(one_level, file_paths))
    total_streams = total_ticks = 0
    all_wrong, twice_by_level, broken = [], {}, {}
    for code, result, error in answers:
        if error:
            broken[code] = error
            continue
        streams, ticks, wrong, twice = result
        total_streams += streams
        total_ticks += ticks
        all_wrong += [(code,) + w for w in wrong]
        if twice:
            twice_by_level[code] = sorted(twice)
    print(f"{len(file_paths)} levels, {total_streams} (model, stream) pairs, {total_ticks} ticks")
    print(f"rigs that link a mesh from more than one part: {twice_by_level}")
    print(f"WRONG (level, model, stream, mesh): {len(all_wrong)}")
    for code, mid, role, mesh, gc, vc, tick in all_wrong[:80]:
        print(f"  {in_prose(code)[:44]:44s} model {mid:4d} role {role!s:>4s} mesh {mesh:3d}: "
              f"game {gc}, viewer {vc} (first at tick {tick})")
    if broken:
        print("levels that would not open:", broken)
    return 1 if all_wrong or broken else 0


if __name__ == "__main__":
    sys.exit(main())
