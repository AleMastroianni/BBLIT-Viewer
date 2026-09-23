"""The piece cache (tools/level_cache.py) against building from scratch.

    .venv/Scripts/python checks/check_level_cache.py [L03A L01A ...]

For each level: builds it from scratch, saves the pieces to a temporary
folder, reads them back and rebuilds the level from there. The two levels
must have the same groups with the same bytes (triangles and frames), the
same faces (how many triangles each one became: the sorted list is ordered
per face), the same counters, bounds and sprites. Then a different signature must make the
file be ignored. Without arguments it tests every level the menu opens.
Exits with 1 if anything differs.
"""
import os
import sys
import tempfile
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from support import level_cache  # noqa: E402
from game import levels  # noqa: E402
from support import paths  # noqa: E402
from game import textures as texmod  # noqa: E402
from viewer import Level  # noqa: E402


def fingerprint(built_level):
    groups_by_key = {k: (g.tex_id, g.category, g.blend, g.spin, g.data.tobytes(),
                  [b.tobytes() for b in g.frames], list(g.face_tris))
                  for k, g in built_level.face_groups.items()}
    # the names floating over the collision boxes are not triangles in a
    # group, so they used to be outside this and a difference in them went
    # unseen: a name was written both inside the clone's piece and from the
    # job list, so a level built from scratch had 27 of them twice over and
    # a level mounted from the cache had them once. Sorted, because what has
    # to be the same is the SET of names, not the order they were made in.
    return (groups_by_key, dict(built_level.stat), built_level.lo, built_level.hi, built_level.terrain_lo, built_level.terrain_hi,
            repr(built_level.sprites), sorted(repr(entry) for entry in built_level.box_labels))


name_list = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
n_identical, different_levels, broken = 0, [], []
t_scratch = t_cache = 0.0
with tempfile.TemporaryDirectory() as tmp:
    for entry_name in name_list:
        file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
        if not os.path.exists(file_path):
            continue
        table = texmod.construct(paths.DATA_BZE, entry_name, "extracted")
        pieces = {}
        a = time.perf_counter()
        try:
            from_scratch = Level(file_path, "extracted", table, None, pieces)
        except Exception as e:  # noqa: BLE001
            # does not build even without the cache: left out of the test
            broken.append(f"{entry_name} ({type(e).__name__})")
            continue
        b = time.perf_counter()
        signature = level_cache.signature(file_path)
        level_cache.store(tmp, entry_name, signature, pieces)
        c = time.perf_counter()
        loaded = level_cache.fetch(tmp, entry_name, signature)
        from_cache = Level(file_path, "extracted", table, None, loaded)
        d = time.perf_counter()
        t_scratch += b - a
        t_cache += d - c
        ok = loaded is not None and len(loaded) == len(pieces) and fingerprint(from_scratch) == fingerprint(from_cache)
        if ok:
            n_identical += 1
        else:
            different_levels.append(entry_name)
            print(f"DIFFERENT: {entry_name}")
    last_name = entry_name
    signature_ignored = level_cache.fetch(tmp, last_name, level_cache.signature(file_path) + "x") is None
print(f"{n_identical} levels identical from the cache and from scratch, {len(different_levels)} different")
print(f"not buildable even from scratch: {', '.join(broken) or 'none'}")
print(f"different signature -> file ignored: {'yes' if signature_ignored else 'NO'}")
print(f"time: from scratch {t_scratch:.1f} s, from the cache {t_cache:.1f} s")
sys.exit(1 if different_levels or not signature_ignored else 0)
