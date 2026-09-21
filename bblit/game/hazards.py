"""What hurts Bugs, and in which of an object's states (finding 318).

Being dangerous is a property of the step an object is in, not of the object:
the control dword of a step (opcode `0x30`, payload +12) says how it hurts,
and the word +22 says by how much. The same reading as the reverse project's
`tools/lists/make_hazards.py` (note N17), whose list is
`..\\BBLIT_Decomp_Ale\\docs\\lists\\hazards.md`: 346 placed objects on the
disc have a dangerous step, only 98 in the state they start in (pirates and
crabs hurt while they attack, not while they patrol).

The viewer uses it for the red outline of the flag Collision boxes: bright red
when the object is dangerous in the state that is being shown, dark red when it
is dangerous in another of its states.
"""

from __future__ import annotations

# the bits of the step's control dword that make an object dangerous
HURT_ON_TOUCH = 0x800000    # when Bugs's box collision has marked it "touched"
BLOW_AT_MARKER = 0x10000    # the point of the attachment marker inside Bugs's box
HITS_OBJECTS = 0x20000      # the other objects whose box it touches
DANGEROUS = HURT_ON_TOUCH | BLOW_AT_MARKER | HITS_OBJECTS
# with this bit the word +22 is a target id, and the damage is 1
TARGET_ID = 0x200000
MAX_DAMAGE = 2

# the names written on the box (always English: ui/flag_labels.py)
NAMES = ((HURT_ON_TOUCH, "HURT"), (BLOW_AT_MARKER, "BLOW"), (HITS_OBJECTS, "HITS"))

END_MARKER = 0xFFF0         # ends the slot list of a state (montage)


def start_state(obj: dict) -> int | None:
    """The state the game starts the object in: 2 if it has it, else 1
    (finding 321), or None if it has no state at all."""
    numbers = {s["number"] for s in obj.get("states", ())}
    for n in (2, 1):
        if n in numbers:
            return n
    return None


def _steps_of(obj: dict, number: int) -> list[int]:
    """The step keys of a state, in playlist order."""
    for s in obj.get("states", ()):
        if s["number"] == number:
            return [k for k in s["slots"] if k != END_MARKER]
    return []


def shown_states(obj: dict, role: int | None = None) -> set[int]:
    """The states the viewer is showing the object in.

    Without a chosen role, the state it starts in; with one (the poses of
    `support/preferences.py`), every state that plays that role, because the
    viewer is showing that animation.
    """
    if role is None:
        start = start_state(obj)
        return {start} if start is not None else set()
    keys = {st["key"] for st in obj.get("steps", ()) if st.get("role") == role}
    return {s["number"] for s in obj.get("states", ())
            if keys & {k for k in s["slots"] if k != END_MARKER}}


def dangerous_steps(obj: dict) -> list[dict]:
    """The object's dangerous steps, in script order.

    Each one: `states` (the state numbers whose playlist holds it, empty when
    no state does), `how` (the names of the bits it carries), `damage` (0 to 2),
    `bugs_state` (the state Bugs is put in, 0 for none) and `start` (the object
    is already in this step when the level opens).
    """
    if obj.get("category") != 14:
        return []
    start = start_state(obj)
    start_keys = set(_steps_of(obj, start)) if start is not None else set()
    found = []
    for st in obj.get("steps", ()):
        control = st.get("control")
        if not control or not control & DANGEROUS:
            continue
        damage = 1 if control & TARGET_ID else min(max(st.get("w22", 0), 0), MAX_DAMAGE)
        found.append({"states": sorted(s["number"] for s in obj.get("states", ())
                                       if st["key"] in _steps_of(obj, s["number"])),
                      "how": [name for bit, name in NAMES if control & bit],
                      "damage": damage, "bugs_state": st.get("w28", 0),
                      "start": st["key"] in start_keys})
    return found


def hazard(obj: dict, role: int | None = None) -> tuple[str, list[str], int] | None:
    """What to write and how to colour the object's collision box, or None if
    the object never hurts.

    Returns ("now", names, damage) when it is dangerous in the state being
    shown, and ("other", names, damage) when only in another of its states
    (the pirates and crabs of *Hey... What's up, Dock? 1* (`L03A`), dangerous in state
    199, the attack). `names` are the ways it hurts, worst damage first.
    """
    steps = dangerous_steps(obj)
    if not steps:
        return None
    shown = shown_states(obj, role)
    now = [s for s in steps if shown & set(s["states"])]
    chosen = now or steps
    damage = max(s["damage"] for s in chosen)
    names = []
    for s in sorted(chosen, key=lambda s: -s["damage"]):
        names += [n for n in s["how"] if n not in names]
    return ("now" if now else "other", names, damage)
