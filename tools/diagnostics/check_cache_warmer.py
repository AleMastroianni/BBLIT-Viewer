"""The background filling of the piece cache (tools/cache_warmer.py).

    .venv/Scripts/python tools/diagnostics/check_cache_warmer.py [L03A L01A ...]

In a temporary cache:
1. with a parent that no longer exists it builds nothing;
2. launched as the viewer launches it (its own process, low priority), it
   saves every menu level of the folder (or the ones given) and exits;
3. every level rebuilt from those files is identical, group by group, to
   the same level built from scratch with the flags off (as the viewer opens
   it), with the fingerprint of check_level_cache.py;
4. a second run finds everything current and saves nothing.
Exits with 1 if anything is wrong.
"""
import os
import subprocess
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import cache_warmer  # noqa: E402
import level_cache  # noqa: E402
import paths  # noqa: E402
import textures as texmod  # noqa: E402
from viewer import Level  # noqa: E402


def fingerprint(built_level):
    """As in check_level_cache.py (a script: it cannot be imported)."""
    groups_by_key = {k: (g.tex_id, g.category, g.blend, g.spin, g.data.tobytes(),
                  [b.tobytes() for b in g.frames]) for k, g in built_level.face_groups.items()}
    return (groups_by_key, dict(built_level.stat), built_level.lo, built_level.hi, built_level.terrain_lo,
            built_level.terrain_hi, repr(built_level.sprites))


errors = 0
wanted = {n.upper() for n in sys.argv[1:]}
all_files = cache_warmer.order(paths.DATA_BZE)
files = [f for f in all_files if not wanted or os.path.splitext(os.path.basename(f))[0].upper() in wanted]
with tempfile.TemporaryDirectory() as tmp:
    folder = paths.DATA_BZE
    if wanted:
        # a folder with only the chosen levels (hard links, or copies)
        folder = os.path.join(tmp, "bze")
        os.makedirs(folder)
        for f in files:
            target = os.path.join(folder, os.path.basename(f))
            try:
                os.link(f, target)
            except OSError:
                import shutil
                shutil.copy2(f, target)
        files = cache_warmer.order(folder)
    cache = os.path.join(tmp, "cache")

    # 1. a dead parent: nothing is built
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    cache_warmer.run(folder, cache, dead.pid)
    built = [n for n in os.listdir(cache)] if os.path.isdir(cache) else []
    print(f"1. dead parent: {len(built)} levels built" + ("" if not built else "  <- WRONG"))
    errors += bool(built)

    # 2. as the viewer launches it
    a = time.perf_counter()
    proc = cache_warmer.start(folder, cache)
    proc.wait()
    t_warm = time.perf_counter() - a
    names = [os.path.splitext(os.path.basename(f))[0] for f in files]
    missing = [n for n in names if not level_cache.is_current(cache, n, level_cache.signature(os.path.join(folder, n + ".bze")))]
    size = sum(os.path.getsize(os.path.join(cache, n, level_cache.NAME)) for n in names if n not in missing)
    print(f"2. {len(names) - len(missing)} of {len(names)} levels saved in {t_warm:.1f} s, "
          f"{size / 1e6:.0f} MB; not saved: {', '.join(missing) or 'none'}")
    errors += bool(missing)

    # 3. from the saved files = from scratch
    different = []
    t_cache = t_scratch = 0.0
    for n in names:
        if n in missing:
            continue
        file_path = os.path.join(folder, n + ".bze")
        table = texmod.construct(folder, n, cache)
        a = time.perf_counter()
        pieces = level_cache.fetch(cache, n, level_cache.signature(file_path))
        from_cache = Level(file_path, cache, table, None, pieces, families=set())
        b = time.perf_counter()
        from_scratch = Level(file_path, cache, table, None, {}, families=set())
        c = time.perf_counter()
        t_cache += b - a
        t_scratch += c - b
        if fingerprint(from_cache) != fingerprint(from_scratch):
            different.append(n)
    print(f"3. {len(names) - len(missing) - len(different)} identical from the warmed cache and from scratch, "
          f"{len(different)} different {different or ''}; opening: from the cache {t_cache:.1f} s, "
          f"from scratch {t_scratch:.1f} s")
    errors += len(different)

    # 4. a second run saves nothing
    stamps = {n: os.path.getmtime(os.path.join(cache, n, level_cache.NAME)) for n in names if n not in missing}
    cache_warmer.run(folder, cache, None)
    rewritten = [n for n, m in stamps.items() if os.path.getmtime(os.path.join(cache, n, level_cache.NAME)) != m]
    print(f"4. second run: {len(rewritten)} files rewritten" + ("" if not rewritten else "  <- WRONG"))
    errors += bool(rewritten)
print("all consistent" if not errors else f"{errors} problems")
sys.exit(1 if errors else 0)
