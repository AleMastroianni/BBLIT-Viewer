"""Gates and who opens them (game/gates.py) against the reverse project's list.

    .venv/Scripts/python checks/check_gates.py [L03D1 ...]

`..\\BBLIT_Decomp_Ale\\docs\\lists\\keys.md` is written by that project's own
reader (note N36, findings 323 and 331): for every gate, which state opens it
and whose rule writes the byte it waits on, going up to three steps back. The
viewer reads the same data and goes up **one** step, which is what it writes on
the box ("GATE <- #78") and draws a line for.

Two things, with the thresholds fixed before running it:

1. **Who opens what.** The viewer says who makes the LAST step into a state
   happen; the list writes out the whole chain, up to three steps. So the
   comparison is on what the viewer claims to read: the (gate, state) pairs the
   list reaches **in one step**, where the two must find exactly the same
   writers -- threshold **95%**. The pairs the list reaches in more steps are
   counted and printed apart, not averaged in.

   Two earlier shapes of this check, both said here: comparing the writers of a
   whole gate in one lump gave 48.1% (it mixed the states of the gates that
   have more than one), and following the whole chain in the viewer too gave
   68.8% (it finds more writers than the list prints, which stops at twelve
   rows).
2. **The population.** A gate of the list must be a gate for the viewer too
   (`gates.is_gate`): threshold **95%** again.

The null for both: the same count with the written value ignored, which lets
in every object that writes that byte with any value.

Exits with 1 if either threshold is missed. Without the reverse project on
disk the check is skipped.
"""
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import gates  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

LIST = os.path.join(os.path.dirname(PROJECT_DIR), "BBLIT_Decomp_Ale", "docs", "lists", "keys.md")
THRESHOLD = 0.95
LEVEL = re.compile(r"^## .* \(`(\w+)`\)\s*$")
GATE = re.compile(r"^- \*\*object (\d+) ")
TO_STATE = re.compile(r"^  - to state (\d+):")
FROM_TO = re.compile(r"^    - from (\d+) to (\d+) when ")
WRITER = re.compile(r"^      - (object|template) (\d+) ")


def read_list(path):
    """{level: {gate number: {state: {writer numbers}}}}, first step only.

    The list groups the writers under the state they take the gate to, and the
    viewer keeps them the same way. Comparing the two in one lump, which is
    what the first run of this check did, mixes the writers of all the states
    of a gate together and fails on the gates with more than one.
    """
    out, level, gate, state = {}, None, None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = LEVEL.match(line)
        if m:
            level, gate, state = m.group(1).upper(), None, None
            continue
        m = GATE.match(line)
        if m and level:
            gate, state = int(m.group(1)), None
            out.setdefault(level, {}).setdefault(gate, {})
            continue
        m = TO_STATE.match(line)
        if m and gate is not None:
            state = int(m.group(1))
            out[level][gate].setdefault(state, {"writers": set(), "steps": 0})
            continue
        m = FROM_TO.match(line)
        if m and gate is not None and state is not None:
            out[level][gate][state]["steps"] += 1
            continue
        m = WRITER.match(line)
        if m and level and gate is not None and state is not None:
            out[level][gate][state]["writers"].add(int(m.group(2)))
    return out


def main():
    if not os.path.exists(LIST):
        print("the reverse project's list is not here, check skipped:", LIST)
        return 0
    listed = read_list(LIST)
    names = [n.upper() for n in sys.argv[1:]] or sorted(listed)
    with_writers = same = population = are_gates = longer = 0
    null_same = 0
    for name in names:
        files = [f for f in os.listdir(paths.DATA_BZE) if f.upper() == name + ".BZE"]
        if not files or name not in listed:
            continue
        sec = sections(os.path.join(paths.DATA_BZE, files[0]), os.path.join(PROJECT_DIR, "extracted"))
        lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
        mine = {g["number"]: g for g in gates.gates_of(lvl)}
        loose = gates.writers(lvl)
        for number, by_state in sorted(listed[name].items()):
            population += 1
            if number in mine:
                are_gates += 1
            for state, entry in sorted(by_state.items()):
                theirs = entry["writers"]
                if not theirs:
                    continue
                if entry["steps"] > 1:
                    longer += 1          # the list reaches it in more than one step
                    continue
                with_writers += 1
                ours = set(mine[number]["opened_by"].get(state, ())) if number in mine else set()
                if ours == theirs:
                    same += 1
                else:
                    print(f"{name}: gate {number} to state {state}: list {sorted(theirs)} "
                          f"!= viewer {sorted(ours)}")
                # the null: everybody who writes that byte, whatever the value
                anybody = set()
                for move in (mine[number]["transitions"] if number in mine else ()):
                    if move["byte"] is None or move["to"] != state:
                        continue
                    anybody |= {w[0] for w in loose.get((move["byte"], move["index"]), ())}
                null_same += anybody == theirs
    rate = same / with_writers if with_writers else 0.0
    kept = are_gates / population if population else 0.0
    print(f"gate states of the list with a first-step writer: {with_writers}; the viewer finds "
          f"the same writers for {same} ({100 * rate:.1f}%, threshold {100 * THRESHOLD:.0f}%; "
          f"null, the written value ignored: {null_same}); "
          f"{longer} more the list reaches in two steps or three, left out on purpose")
    print(f"gates of the list that are gates for the viewer too: {are_gates} of {population} "
          f"({100 * kept:.1f}%, threshold {100 * THRESHOLD:.0f}%)")
    ok = rate >= THRESHOLD and kept >= THRESHOLD
    print("the viewer reads the gates as the reverse list does" if ok else "THRESHOLD MISSED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
