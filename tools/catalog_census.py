"""The catalogue of the Animations menu (`game/catalog.py`), level by level.

    .venv/Scripts/python tools/catalog_census.py [--level MERLIN] [--families]

For each level: the seven categories with the number of exemplars (things in
the level: placed objects and clones) and of families, and how many of the
exemplars the game has when the level has just loaded. With `--families`
every family: what put it in its category, its model, its exemplars by
provenance and the object numbers. At the end, for the levels with roles in
`preferences.py` `always_cloned` (the hand curation), where the catalogue
puts those roles; without `--level`, the totals of the disc.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))

from game import catalog  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from support import preferences  # noqa: E402
from window import scene  # noqa: E402

NAMES = {"characters": "Characters", "staged": "Things with stages", "carried": "Carried and pushed",
         "collectables": "Collectables", "effects": "Effects and signs", "opening": "Things that open",
         "rest": "The rest"}


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def build(file_path):
    sec = scene.sections(file_path, os.path.join(PROJECT_DIR, "extracted"))
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    started = time.perf_counter()
    cat = catalog.Catalogue(lvl, sec[4])
    return lvl, cat, (time.perf_counter() - started) * 1000


def survey(code, file_path, show_families):
    lvl, cat, ms = build(file_path)
    print(f"{in_prose(code)} ({ms:.0f} ms)")
    totals = Counter()
    for c in catalog.CATEGORIES:
        fams = cat.families[c]
        ex = [e for f in fams for e in f["exemplars"]]
        totals[c] += len(ex)
        extra = ""
        if c == "rest":
            sub = Counter(f["key"][1] for f in fams for _e in f["exemplars"])
            extra = f"  (scenery {sub['scenery']}, invisible logic {sub['logic']})"
        print(f"  {NAMES[c]:20s} {catalog.in_words(ex)}; {len(fams)} families{extra}")
        if not show_families:
            continue
        for f in fams:
            prov = Counter(e["provenance"] for e in f["exemplars"])
            what = f"{f['key'][1]} {f['key'][2]}" + (" (this level)" if f["key"][1] == "model" else "")
            print(f"      {what}: {catalog.in_words(f['exemplars'])} "
                  f"- {f['why']} - {dict(prov)} - objects {f['objects'][:8]}"
                  f"{' ...' if len(f['objects']) > 8 else ''}")
    reached = {n for fams in cat.families.values() for f in fams for n in f["objects"]}
    missing = [n for n in range(len(lvl["objects"])) if n not in reached]
    print(f"  objects of the file reached from a category: {len(reached)} of {len(lvl['objects'])}"
          f"{'' if not missing else ', missing ' + str(missing[:10])}")
    always = preferences.for_level(code)["always_cloned"]
    if always:
        print(f"  the hand curation (always_cloned, {len(always)} roles):")
        for role in sorted(always):
            n = cat.templates.get(role)
            if n is None:
                continue
            ex = [e for fams in cat.families.values() for f in fams for e in f["exemplars"]
                  if e["object"] == n]
            print(f"      role {role} (object {n}): {NAMES[cat.category[n][0]]}, {cat.category[n][1]}; "
                  f"{sum(e['at_start'] for e in ex)} of {len(ex)} exemplars there at the start")
    return totals


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--level")
    ap.add_argument("--families", action="store_true")
    args = ap.parse_args()
    grand = Counter()
    for file_path in scene.levels_in(paths.DATA_BZE):
        code = os.path.splitext(os.path.basename(file_path))[0]
        if args.level and code.upper() != args.level.upper():
            continue
        grand.update(survey(code, file_path, args.families))
    if not args.level:
        print("\nthe disc:", {NAMES[c]: grand[c] for c in catalog.CATEGORIES})


if __name__ == "__main__":
    main()
