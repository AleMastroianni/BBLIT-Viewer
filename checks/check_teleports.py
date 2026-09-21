"""Where the zones send you: the destinations and the level changes
(finding 326).

    .venv/Scripts/python checks/check_teleports.py [L03A L01A ...]

A zone rule can send somebody to a fixed point (ENTRANCE: the way in from
another level, Bugs is put down only when the byte the level change wrote
says so; TELEPORT: Bugs, with no condition at all; RECOVER: the object
inside the zone, the recovery nets; RESTART: where Bugs comes back after a
death) or to another level (the first parameter is the LevID). The viewer
draws an arrow to the point and writes on the zone the NAME of the level it
leads to or comes from, so all of it has to be right:

* every LevID of a level change must name a file of the level table, and
  that file must be on the disc;
* a destination must land in the level it belongs to. The stand-in for
  "a place in the level" is a placed object: on the disc a destination is a
  median 136 units (about 1 m) from the nearest one, and the farthest is
  2090. The null hypothesis is the same point measured against ANOTHER
  level's objects: a median of 4351 units, and only a third of them inside
  the threshold, because the levels share the same coordinate range.

* every level of the table must have a name to write, and every entrance
  must find the level it comes from;
* the addressee of a zone rule (finding 337) must count out as the reverse
  project read it: of the 2397 rules of the disc, 1847 speak to Bugs, 548 to
  another object and **2 are dead**, with an addressee (100000) no object can
  have. Those two are the starting zones of *Hey... What's up, Dock?* parts 1
  and 2; the viewer draws them grey, with DEAD in the name. Counted over the
  same levels as that project's lists, which leave out the `_8` twins and the
  cutscenes: with them the same reading gives 2760, 2103, 653 and 4, the two
  extra dead ones being the twins of those same zones.

Exits with 1 if a LevID is unknown, if a destination lands farther than the
threshold, if an entrance has no source, or if the null is not clearly
worse.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
import math  # noqa: E402

from game import entrances  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import zones  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

# game units, 128 = 1 m: how far a destination may be from the nearest
# placed object of its own level (the worst on the disc is 2090)
REACH = 2100
# the null must put well under this share inside REACH (it manages a third)
NULL_SHARE = 0.5
failures = []


def probe(entry_name, cond):
    print(("OK   " if cond else "FAIL ") + entry_name)
    if not cond:
        failures.append(entry_name)


def nearest(points, p):
    """The distance to the nearest of `points`."""
    return min(math.dist(q, p) for q in points) if points else float("inf")


names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
placed, found = {}, []
rule_count = to_bugs = to_object = dead_rules = 0
dead_where = []
counts = {"ENTRANCE": 0, "TELEPORT": 0, "RECOVER": 0, "RESTART": 0}
changes = []
entrance_rules = []
for name in names:
    path = os.path.join(paths.DATA_BZE, name + ".bze")
    if not os.path.exists(path):
        continue
    sec = sections(path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    placed[name] = [o["position"] for o in lvl["objects"] if o["position"]]
    counted = not (name.upper().endswith("_8") or name.upper().startswith("CC"))
    for z in lvl["zones"]:
        for rule in z.get("rules", []):
            if not counted:
                continue
            rule_count += 1
            if zones.is_dead(rule):
                dead_rules += 1
                dead_where.append((name, rule["addressee"]))
            elif rule.get("addressee") == zones.BUGS:
                to_bugs += 1
            else:
                to_object += 1
        for label, point, rule in zones.destinations(z):
            counts[label] = counts.get(label, 0) + 1
            found.append((name, label, point))
            if label == "ENTRANCE":
                entrance_rules.append((name, rule))
        for levid in zones.level_changes(z):
            changes.append((name, levid))
print(f"{len(placed)} levels; destinations {counts}; level changes {len(changes)}")
print(f"zone rules: {rule_count} in all, to Bugs {to_bugs}, to another object "
      f"{to_object}, dead {dead_rules} {dead_where}")
if not sys.argv[1:]:
    probe("the addressees count out as the reverse project read them (finding 337)",
          (rule_count, to_bugs, to_object, dead_rules) == (2397, 1847, 548, 2))

probe("the disc has destinations and level changes to check",
      len(found) > 50 and len(changes) > 20)

# every level change names a file that is really there
unknown = [(name, levid) for name, levid in changes if levels.file_of_levid(levid) is None]
probe(f"every level change names a file of the level table ({len(changes)} of them)", not unknown)
if unknown:
    print("   unknown LevIDs:", unknown[:8])
absent = [(name, levels.file_of_levid(levid)) for name, levid in changes
          if levels.file_of_levid(levid)
          and not os.path.exists(os.path.join(paths.DATA_BZE, levels.file_of_levid(levid) + ".bze"))]
probe("and that file is on the disc", not absent)
if absent:
    print("   missing files:", absent[:8])
probe("a level change never leads to the level it is in",
      not [(n, levels.file_of_levid(k)) for n, k in changes if levels.file_of_levid(k) == n])

# every destination lands near a placed object of its own level
with_objects = [n for n in sorted(placed) if len(placed[n]) >= 5]
checked = [(name, label, point) for name, label, point in found if name in with_objects]
out = [(nearest(placed[name], point), name, label, point) for name, label, point in checked]
worst = max(out)[0] if out else float("inf")
probe(f"every destination lands within {REACH} units of a placed object of its own level "
      f"(worst {worst:.0f}, {len(out)} destinations)", out and worst <= REACH)
for gap, name, label, point in sorted(out, reverse=True)[:5]:
    print(f"   {name:9s} {label:9s} {point}  {gap:.0f} units away")

# the null: the same point against the objects of the next level
null_inside = 0
for name, label, point in checked:
    other = with_objects[(with_objects.index(name) + 1) % len(with_objects)]
    if nearest(placed[other], point) <= REACH:
        null_inside += 1
null_share = null_inside / len(checked) if checked else 1.0
print(f"null hypothesis (another level's objects): {null_inside} of {len(checked)} "
      f"({100 * null_share:.1f}%) would pass as well")
probe(f"and the null is clearly worse (under {100 * NULL_SHARE:.0f}%)", null_share < NULL_SHARE)

# the names the viewer writes: a level of the table always has one, and every
# entrance knows the level it comes from
nameless = [n for n in names
            if os.path.exists(os.path.join(paths.DATA_BZE, n + ".bze"))
            and levels.official_name(n, in_english=True) is None]
probe("every file of the level table has a name to write instead of its code", not nameless)
if nameless:
    print("   without a name:", nameless[:8])
# the _8 variants are not in the game's level table, so no level change can
# lead to one and no entrance of theirs has a source: they are left out
listed = [(name, rule) for name, rule in entrance_rules if not name.lower().endswith("_8")]
orphans = [name for name, rule in listed
           if not entrances.sources_of(rule, name, paths.DATA_BZE, "extracted")]
probe(f"every entrance of a listed level finds where it comes from ({len(listed)} of them)", not orphans)
if orphans:
    print("   no source found in:", orphans[:8])
for name, rule in entrance_rules:
    source = entrances.sources_of(rule, name, paths.DATA_BZE, "extracted")
    print("   %-9s <- %s" % (levels.official_name(name, in_english=True) or name,
                             " / ".join(levels.official_name(s, in_english=True) or s for s in source)))

print(f"\n{len(failures)} failed" if failures else "\nall consistent")
sys.exit(1 if failures else 0)
