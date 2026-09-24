"""Which cloned templates the game has in each level (`game/clone_life.py`),
against the old "at startup" test, on the whole disc.

    .venv/Scripts/python tools/clone_census.py [--level L03C2] [--rules]

For every rule of a placed object that clones a template (effect 0x100 or
0x40000): LEVEL (comes by itself and stays: Cloned templates -> In the level),
PASSING (comes by itself and ends by itself) or EVENT (needs Bugs), next to
what `scene._at_startup` said (a condition true on zeroed tables and no
radius, masks and states not looked at). `--rules` lists the rules one by
one; with `--level` only that level. At the end, for the levels with roles in
`preferences.py` `always_cloned`, which of those roles the reading already
puts in the level by itself.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))

from game import clone_life  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from support import preferences  # noqa: E402
from window import scene  # noqa: E402


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def level_data(file_path):
    sec = scene.sections(file_path, os.path.join(PROJECT_DIR, "extracted"))
    return loadscript.export_level(loadscript.parse(sec[1])[0])


def survey(code, file_path, show_rules):
    lvl = level_data(file_path)
    started = time.perf_counter()
    kinds = clone_life.kinds(lvl)
    ms = (time.perf_counter() - started) * 1000
    counts, rows, in_level_roles = Counter(), [], set()
    for n, o in enumerate(lvl["objects"]):
        if o["block_type"] == 0x08 or not o["position"]:
            continue
        for i, r in enumerate(o.get("rules", ())):
            if not r["effect"] & clone_life.CLONES or r["field28"] <= 0:
                continue
            kind = kinds[("placed", n, i)]
            old = "at start" if scene._at_startup(r) else "later"
            counts[kind] += 1
            counts[(kind, old)] += 1
            if kind == clone_life.LEVEL:
                in_level_roles.add(r["field28"])
            rows.append(f"    object {n} rule {i} -> template id {r['field28']}: {kind} (old: {old})")
    print(f"{in_prose(code)}: {counts[clone_life.LEVEL]} in the level, "
          f"{counts[clone_life.PASSING]} passing, {counts[clone_life.EVENT]} event; "
          f"old at start {sum(v for k, v in counts.items() if isinstance(k, tuple) and k[1] == 'at start')}; "
          f"{ms:.0f} ms")
    if show_rules:
        print("\n".join(rows))
    return counts, in_level_roles


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--level")
    ap.add_argument("--rules", action="store_true")
    args = ap.parse_args()
    total, curated = Counter(), []
    for file_path in scene.levels_in(paths.DATA_BZE):
        code = os.path.splitext(os.path.basename(file_path))[0]
        if args.level and code.upper() != args.level.upper():
            continue
        counts, roles = survey(code, file_path, args.rules)
        total.update(counts)
        always = preferences.for_level(code)["always_cloned"]
        if always:
            curated.append((code, sorted(always & roles), sorted(always - roles)))
    print()
    for kind in (clone_life.LEVEL, clone_life.PASSING, clone_life.EVENT):
        print(f"{kind}: {total[kind]} rules ({total[(kind, 'at start')]} were 'at start', "
              f"{total[(kind, 'later')]} 'later')")
    for code, found, not_found in curated:
        print(f"{in_prose(code)} always_cloned: in the level by itself {found}; not {not_found}")


if __name__ == "__main__":
    main()
