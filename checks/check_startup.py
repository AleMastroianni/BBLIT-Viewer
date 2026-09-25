"""The viewer's first tick (`game/startup.py`) against the reverse's, level
by level: how far the two readings of N74 are from each other.

    .venv/Scripts/python checks/check_startup.py [--level MERLIN] [--list]

`..\\BBLIT_Decomp_ALE\\docs\\lists\\startup\\<level>.json` (the reverse's
`make_startup.py`) says what is alive at tick 1 by the recipe of N74, with
one difference of set-up from the viewer: it judges the culling from the
camera's start (an object far from it does not run until the camera comes
closer), while the viewer runs every object, because its camera is free and
reaches every one sooner or later. So every difference is put in one of two
piles: **culling** when the reverse says that the object, or the object that
clones it, does not run at the start; **other** for the rest, which is where
the two readings really part.

Two conventions, not readings: the reverse keeps Bugs apart (its key
`bugs`) and does not list the texture animators of types 2 and 20, which
have no place in the file; both are left out of the comparison and counted
as "not listed".

At tick 1 it compares:

- the placed objects alive (by the number of the object block, the same in
  both);
- the clones alive, as pairs (who clones it, the template's id): the reverse
  names the rule by its words, not by its index;
- the state of the placed type 14 objects alive in both;
- what hangs from Bugs.

With `--list` it prints the differences one by one. Exits with 1 when a
difference of the pile "other" is left, or when the reverse's files are
missing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import startup as startupmod  # noqa: E402
from support import paths  # noqa: E402
from window import scene  # noqa: E402

STARTUP_DIR = os.path.join(os.path.dirname(paths.PROJECT_DIR), "BBLIT_Decomp_ALE",
                           "docs", "lists", "startup")
# the objects the reverse's lists leave out: the player (kept apart as
# `bugs`) and the texture animators without a place (types 2 and 20)
UNLISTED = (1, 2, 20)
CLONE_REF = re.compile(r"clone \d+ \(template \d+, id (\d+)\)")


def theirs_of(code):
    """The reverse's file for a level, found without regard to case."""
    for name in os.listdir(STARTUP_DIR):
        if name.lower() == code.lower() + ".json":
            with open(os.path.join(STARTUP_DIR, name), encoding="utf-8") as f:
                return json.load(f)
    return None


def spawner_of(ref):
    """("object", n) or ("template", id) from the reverse's spawner words."""
    if ref.startswith("object "):
        return ("object", int(ref.split()[1]))
    m = CLONE_REF.match(ref)
    return ("template", int(m.group(1))) if m else ("?", ref)


def compare(code, file_path):
    sec = scene.sections(file_path, os.path.join(PROJECT_DIR, "extracted"))
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    mine = startupmod.Startup(lvl)
    theirs = theirs_of(code)
    if theirs is None:
        return None
    alive = theirs["at_tick"]["1"]["alive"]
    runs = {a["file_index"]: a["runs"] for a in alive if a["kind"] == "placed"}
    # the placed objects that exist in their list at all (alive), and whether they run
    their_placed = {a["file_index"] for a in alive if a["kind"] == "placed"}
    counts = Counter()
    listing = []

    def note(pile, what, text):
        counts[(pile, what)] += 1
        listing.append(f"    {pile:7s} {what:7s} {text}")

    # 1. the placed objects alive (Bugs and the texture animators: not listed)
    unlisted = {n for n in mine.alive if lvl["objects"][n].get("category") in UNLISTED}
    counts[("not listed", "placed")] += len(unlisted - their_placed)
    for n in sorted((mine.alive - unlisted) ^ their_placed):
        side = "only the viewer" if n in mine.alive else "only the reverse"
        pile = "culling" if runs.get(n) is False else "other"
        note(pile, "placed", f"object {n}: alive for {side}")
    # 2. the clones alive, as (spawner, template id)
    my_clones = Counter()
    for live in mine.born.values():
        key, _i = live.route[-1]
        spawner = ("object", key[1]) if key[0] == "placed" else ("template", key[1])
        my_clones[(spawner, live.obj.get("role"))] += 1
    their_clones = Counter()
    for a in alive:
        if a["kind"] == "clone" and a.get("born"):
            their_clones[(spawner_of(a["born"]["spawner"]), a["id"])] += 1
    for pair in sorted(set(my_clones) | set(their_clones), key=str):
        a, b = my_clones[pair], their_clones[pair]
        if a == b:
            continue
        spawner = pair[0]
        pile = "culling" if spawner[0] == "object" and runs.get(spawner[1]) is False else "other"
        note(pile, "clone", f"{spawner[0]} {spawner[1]} -> template id {pair[1]}: viewer {a}, reverse {b}")
    # 3. the states of the placed type 14 objects alive in both
    my_state = {x.number: x.state for x in mine.chain if x.key[0] == "placed" and not x.dead}
    for a in alive:
        n = a.get("file_index")
        if a["kind"] != "placed" or a.get("type") != 14 or n not in my_state or a.get("state") is None:
            continue
        if my_state[n] != a["state"]:
            pile = "culling" if a["runs"] is False else "other"
            note(pile, "state", f"object {n}: viewer state {my_state[n]}, reverse {a['state']}")
    # 4. what hangs from Bugs
    their_bugs = {a["file_index"] for a in alive if a["kind"] == "placed" and a.get("parent") == "Bugs"}
    for n in sorted(mine.on_bugs ^ their_bugs):
        side = "only the viewer" if n in mine.on_bugs else "only the reverse"
        pile = "culling" if runs.get(n) is False else "other"
        note(pile, "on Bugs", f"object {n}: on Bugs for {side}")
    return counts, listing


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--level")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(STARTUP_DIR):
        print(f"the reverse's files are not at {STARTUP_DIR}: they are the reference of this check")
        sys.exit(1)
    total = Counter()
    rows = []
    for file_path in scene.levels_in(paths.DATA_BZE):
        code = os.path.splitext(os.path.basename(file_path))[0]
        if args.level and code.upper() != args.level.upper():
            continue
        result = compare(code, file_path)
        if result is None:
            print(f"{code}: no file of the reverse")
            total[("missing", "")] += 1
            continue
        counts, listing = result
        total.update(counts)
        other = sum(v for (pile, _w), v in counts.items() if pile == "other")
        culling = sum(v for (pile, _w), v in counts.items() if pile == "culling")
        name = levels.official_name(code) or code
        detail = ", ".join(f"{w} {v}" for (pile, w), v in sorted(counts.items()) if pile == "other")
        rows.append(f"{name} ({code}): other {other}{' (' + detail + ')' if detail else ''}; culling {culling}")
        if args.list and listing:
            rows.extend(listing)
    print("\n".join(rows))
    other = sum(v for (pile, _w), v in total.items() if pile == "other")
    culling = sum(v for (pile, _w), v in total.items() if pile == "culling")
    by_what = {w: v for (pile, w), v in sorted(total.items()) if pile == "other"}
    print(f"\nall levels: other {other} {by_what}; culling {culling}; "
          f"not listed by the reverse {total[('not listed', 'placed')]}; missing files {total[('missing', '')]}")
    sys.exit(1 if other or total[("missing", "")] else 0)


if __name__ == "__main__":
    main()
