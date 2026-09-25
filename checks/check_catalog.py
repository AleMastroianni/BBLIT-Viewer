"""The catalogue of the Animations menu (`game/catalog.py`).

    .venv/Scripts/python checks/check_catalog.py

On every playable level: every object of the file is reached from exactly
one category, and the exemplars of a category add up to the sum of its
families. On the test levels, the cases looked at by hand:

- Nowhere (MERLIN): Merlin (object 122, a skeleton of 11 parts whose box
  changes with its state) is a character there at the start; the helpers
  (model 272) are characters none of which is there at the start (they are
  born when a trial starts, as seen in the game);
- Nowhere, the reverse's N75 and N76: the small crate (template 310) is
  there after the first tick, objects 127 and 142 hang from Bugs from it,
  and the placed objects with no place or at (0, 0, 0) are seven pages of
  the pause menu, five scripts without a model (54, 55, 56, 146, 171), the
  sky, the two on Bugs and twelve texture animators: none parked;
- Mine or mine? 3 (L03C2): the rails (template 1238, one state) are in The
  rest, scenery; they come by themselves, but not at the first tick (the
  trigger that starts the ride waits for its clock to pass 0: N74);
- Hey... What's up, Dock? 1 (L03A): the blue chests (templates 764-766) are
  not characters (three parts), and the crabs (model 276, 11 parts) and the
  pirates (model 112, 24 parts) are.

Exits with 1 if anything fails.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

from game import catalog  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from window import scene  # noqa: E402

results = []


def probe(name, ok):
    results.append(ok)
    print(("OK   " if ok else "FAIL ") + name)


def build(code):
    fp = os.path.join(paths.DATA_BZE, code + ".bze")
    sec = scene.sections(fp, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    return lvl, catalog.Catalogue(lvl, sec[4])


def exemplars_of(cat, n):
    return [e for fams in cat.families.values() for f in fams for e in f["exemplars"] if e["object"] == n]


complete = 0
levels = scene.levels_in(paths.DATA_BZE)
for fp in levels:
    code = os.path.splitext(os.path.basename(fp))[0]
    lvl, cat = build(code)
    homes = {}
    for c, fams in cat.families.items():
        for f in fams:
            for n in f["objects"]:
                homes.setdefault(n, set()).add(c)
    if len(homes) == len(lvl["objects"]) and all(len(h) == 1 for h in homes.values()):
        complete += 1
    else:
        print(f"     {code}: {len(homes)} of {len(lvl['objects'])} objects reached")
probe(f"every object reached from exactly one category: {complete} of {len(levels)} levels",
      complete == len(levels))

lvl, cat = build("MERLIN")
ex = exemplars_of(cat, 122)
probe("Nowhere: Merlin (object 122) is a character there at the start",
      cat.category[122][0] == "characters" and ex and all(e["at_start"] for e in ex))
helpers = [f for f in cat.families["characters"] if f["model"] == 272]
probe("Nowhere: the helpers (model 272) are characters, none there at the start",
      len(helpers) == 1 and helpers[0]["exemplars"] and not any(e["at_start"] for e in helpers[0]["exemplars"]))

crate = exemplars_of(cat, cat.templates[310])
probe("Nowhere: the small crate (template 310) is there after the first tick (N75)",
      crate and any(e["at_start"] for e in crate))
probe("Nowhere: objects 127 and 142 hang from Bugs from the first tick (N75, N76)",
      {127, 142} <= cat.startup.on_bugs)
from collections import Counter  # noqa: E402
origin = [n for n, o in enumerate(lvl["objects"]) if o["block_type"] != 0x08
          and (not o["position"] or tuple(o["position"]) == (0, 0, 0))]
prov = Counter(next(e["provenance"] for e in exemplars_of(cat, n) if e["parent"] is None) for n in origin)
probe(f"Nowhere: nothing parked at the origin (N76): {dict(prov)}",
      prov == Counter({"texture": 12, "pause_page": 7, "script": 5, "on_bugs": 2, "sky": 1}))

lvl, cat = build("L03C2")
n = cat.templates.get(1238)
ex = exemplars_of(cat, n) if n is not None else []
probe("Mine or mine? 3: the rails (template 1238) are scenery in The rest, by themselves but not at tick 1",
      n is not None and cat.category[n] == ("rest", "scenery") and ex
      and all(e["in_level"] and not e["at_start"] for e in ex))

lvl, cat = build("L03A")
probe("Hey... What's up, Dock? 1: the blue chests (764-766) are not characters",
      all(cat.category[cat.templates[r]][0] != "characters" for r in (764, 765, 766)))
probe("Hey... What's up, Dock? 1: the crabs (model 276) and the pirates (model 112) are characters",
      {276, 112} <= {f["model"] for f in cat.families["characters"]})
sums = all(sum(len(f["exemplars"]) for f in cat.families[c]) == cat.counts()[c] for c in catalog.CATEGORIES)
probe("the count of a category is the sum of its families", sums)

failed = results.count(False)
print(f"\n{len(results) - failed}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
