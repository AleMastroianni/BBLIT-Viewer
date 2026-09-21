"""What hurts Bugs (game/hazards.py) against the reverse project's list.

    .venv/Scripts/python checks/check_hazards.py [L03A ...]

`..\\BBLIT_Decomp_Ale\\docs\\lists\\hazards.md` is written by that project's
own reader of the load script (note N17, finding 318), from the same `.bze`
files but with code written apart from this one: every type 14 object or
template with a dangerous step, the states it is dangerous in, how, how much
damage, which state Bugs is put in, and whether the object starts in that
step.

The viewer must say exactly the same thing for every object of every level in
the list: threshold fixed before running it, **100% agreement**, and the
totals of the list's header (346 objects, 98 dangerous from the start; 159
templates, 74 from the start) found again. Exits with 1 if anything differs.
Without the reverse project on disk the check is skipped (exit 0 and says so).
"""
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import hazards  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

LIST = os.path.join(os.path.dirname(PROJECT_DIR), "BBLIT_Decomp_Ale", "docs", "lists", "hazards.md")
# the reverse project's wording for the bits of the step's control dword
HOW = {"touch": "HURT", "blow at the marker": "BLOW", "hits objects": "HITS"}
ENTRY = re.compile(r"^- (object|template) (\d+)(?: \(id \d+\))?(?: at \([^)]*\))?: (.*)$")


def parse_list(path):
    """{level: {(tag, index): {entry, ...}}} and the header's totals."""
    found, totals, level = {}, {}, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("## "):
            level = line[3:].strip().upper()
        elif ":" in line and line[0].isalpha() and level is None:
            for part in line.split(","):
                key, _, value = part.rpartition(":")
                if key.strip() and value.strip().isdigit():
                    totals[key.strip()] = int(value.strip())
        else:
            m = ENTRY.match(line)
            if m and level:
                entries = set()
                for item in m.group(3).split("; "):
                    # "state 322/201: touch + hits objects, damage 1, Bugs to state 10 (START)"
                    head, _, rest = item.partition(": ")
                    states = tuple(sorted(int(n) for n in head[len("state "):].split("/") if n != "?"))
                    fields = rest.split(", ")
                    how = tuple(sorted(HOW[h] for h in fields[0].split(" + ")))
                    damage = int(fields[1][len("damage "):].split(" ")[0])
                    bugs = next((int(f[len("Bugs to state "):].split(" ")[0])
                                 for f in fields[2:] if f.startswith("Bugs to state")), 0)
                    entries.add((states, how, damage, bugs, item.endswith("(START)")))
                found.setdefault(level, {})[(m.group(1), int(m.group(2)))] = entries
    return found, totals


def mine(level_name):
    """The same thing read by the viewer: {(tag, index): {entry, ...}}."""
    files = [f for f in os.listdir(paths.DATA_BZE) if f.upper() == level_name.upper() + ".BZE"]
    if not files:
        return None
    sec = sections(os.path.join(paths.DATA_BZE, files[0]), os.path.join(PROJECT_DIR, "extracted"))
    if 1 not in sec:
        return None
    out = {}
    for index, o in enumerate(loadscript.export_level(loadscript.parse(sec[1])[0])["objects"]):
        steps = hazards.dangerous_steps(o)
        if not steps:
            continue
        tag = "template" if o["block_type"] == 0x08 else "object"
        out[(tag, index)] = {(tuple(s["states"]), tuple(sorted(s["how"])), s["damage"],
                              s["bugs_state"], s["start"]) for s in steps}
    return out


def main():
    if not os.path.exists(LIST):
        print("the reverse project's list is not here, check skipped:", LIST)
        return 0
    listed, totals = parse_list(LIST)
    names = [n.upper() for n in sys.argv[1:]] or sorted(listed)
    checked = missing = wrong = 0
    counted = {"object": 0, "template": 0, "object from the start": 0, "template from the start": 0}
    for name in names:
        ours = mine(name)
        if ours is None:
            print(f"{name}: level not on disk")
            missing += 1
            continue
        theirs = listed.get(name, {})
        for key in sorted(set(theirs) | set(ours)):
            checked += 1
            tag = key[0]
            if key in ours:
                counted[tag] += 1
                counted[tag + " from the start"] += any(e[4] for e in ours[key])
            if theirs.get(key) != ours.get(key):
                wrong += 1
                print(f"{name}: {key[0]} {key[1]}: list {sorted(theirs.get(key, ()))} "
                      f"!= viewer {sorted(ours.get(key, ()))}")
    print(f"{checked} objects and templates checked in {len(names)} levels: {wrong} differ")
    print(f"counted: {counted['object']} objects ({counted['object from the start']} dangerous from "
          f"the start), {counted['template']} templates ({counted['template from the start']} from the start)")
    header_ok = True
    if not sys.argv[1:] and totals:
        for key, ours_key in (("object", "object"), ("object dangerous from the start", "object from the start"),
                              ("template", "template"),
                              ("template dangerous from the start", "template from the start")):
            if key in totals and totals[key] != counted[ours_key]:
                header_ok = False
                print(f"header of the list: {key} = {totals[key]}, viewer = {counted[ours_key]}")
    ok = wrong == 0 and missing == 0 and header_ok
    print("the viewer says the same as the reverse list" if ok else "DIFFERENCES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
