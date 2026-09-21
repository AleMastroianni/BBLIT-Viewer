"""Gates: the solid objects whose box changes with their state, and who opens
them (findings 323 and 331).

Nothing makes an object solid or not solid with a flag while the game runs: a
box changes only because the object is deleted, because an animation record of
type 9 sets another one, or because the object moves (finding 323). So a gate
is an object with more than one state whose box changes from state to state,
and "opening" it means playing the state where its box goes away or shrinks.

**Who opens it** comes from the rules: a rule that moves the object to that
state waits on a level byte (`0x4b2260[i]`) or on a save byte
(`config+0x10040[i]`), and another object's rule writes that byte (finding
316). The reverse project's `keys.md` walks the same chain up to three steps;
here one step is enough to say "gate 37 is opened by object 78", which is what
the viewer writes on the box and draws a line for.

Read from the data, as `..\\BBLIT_Decomp_Ale\\docs\\lists\\keys.md` is:
`checks/check_gates.py` compares the two.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import hazards  # noqa: E402

# Which condition codes read a byte and which action codes write one, and what
# each of them means: the whole vocabulary of the disc, as the reverse project
# read it in the code (finding 331). The viewer used to know two of the
# thirteen actions that write a level byte, and then missed, for example, the
# switch of *The Planet X File! 5* (`L05A5`), which writes byte 206 with
# action 0x03.
LEVEL_BYTE_TESTS = {0x01, 0x25, 0x03, 0x05, 0x07, 0x09, 0x46, 0x47, 0x1E, 0x27,
                    0x0F, 0x3D, 0x3F, 0x41, 0x43}
SAVE_BYTE_TESTS = {0x02, 0x26, 0x04, 0x06, 0x08, 0x0A, 0x59, 0x1F, 0x28, 0x10, 0x3E, 0x40}
# a test between two bytes says nothing about a single writer: left out, as the
# reverse project's list does
BYTE_TO_BYTE = {0x0F, 0x3D, 0x3F, 0x41, 0x43, 0x10, 0x3E, 0x40}
LEVEL_BYTE_WRITES = {0x03, 0x05, 0x07, 0x0B, 0x0D, 0x12, 0x0F, 0x14, 0x16, 0x1C, 0x24,
                     0x27, 0x2D}
SAVE_BYTE_WRITES = {0x04, 0x17, 0x06, 0x08, 0x0C, 0x0E, 0x13, 0x10, 0x15, 0x1B, 0x25, 0x28}
# the actions whose value is a whole word, not a byte
WORD_VALUE = {0x0F, 0x10, 0x14, 0x15, 0x16, 0x1B, 0x1C, 0x22, 0x52, 0x31, 0x32, 0x26,
              0x2B, 0x5C}
# the actions that set bits (|=) and the ones that clear bits (&=): an OR can
# only make a "bit set" test true, an AND only a "bit clear" one
SETS_BITS = {0x0B, 0x0C}
CLEARS_BITS = {0x0D, 0x0E}
WRITES_VALUE = {0x12, 0x13}
WRITES_ZERO = {0x07, 0x08}
BIT_TESTS_SET = {0x1E, 0x1F}
BIT_TESTS_CLEAR = {0x27, 0x28}


def passes(test, operand, value) -> bool:
    """Does the byte `value` pass condition `test` with operand `operand`?
    (The unsigned forms; the signed ones are taken as unsigned, as the reverse
    project's list does.)"""
    if test in (0x01, 0x02):
        return value == operand
    if test in (0x25, 0x26):
        return value != operand
    if test in (0x03, 0x04, 0x46):
        return value > operand
    if test in (0x05, 0x06):
        return value >= operand
    if test in (0x07, 0x08, 0x47, 0x59):
        return value < operand
    if test in (0x09, 0x0A):
        return value <= operand
    if test in BIT_TESTS_SET:
        return bool(value & operand)
    if test in BIT_TESTS_CLEAR:
        return not value & operand
    return True


# an object whose box only tells the game somebody touched it: a pickup, a
# trigger. It stops nobody, so it is not a gate (finding 323)
ONLY_SIGNALS = 0x2000000
# a bit of this mask in the first flag word stops Bugs (finding 300): only
# those are opened by the menu's choice
STOPS_BUGS = 0x9A690A
# with this bit Bugs can stand on it: a floor, a lift, a drawbridge. Those are
# not opened either: what the menu opens is what blocks the way
STAND_ON = 0x8
# the object moves by itself: then its box changes because it moved, not
# because a state changed it
MOVES = 0x2


def _byte_test(rule):
    """("level"/"save", index, operand, test code) the rule waits on, or None.
    A test that compares two bytes says nothing about a single writer."""
    op, value, index = rule["condition"]
    if op in BYTE_TO_BYTE:
        return None
    if op in LEVEL_BYTE_TESTS:
        return ("level", index, value, op)
    if op in SAVE_BYTE_TESTS:
        return ("save", index, value, op)
    return None


def _byte_write(rule) -> tuple[str, int] | None:
    """("level"/"save", index) the rule writes, or None."""
    code, _value, index, _s16 = rule["action"]
    if code in LEVEL_BYTE_WRITES:
        return ("level", index)
    if code in SAVE_BYTE_WRITES:
        return ("save", index)
    return None


def writers(lvl) -> dict[tuple[str, int], list[tuple[int, int, int]]]:
    """{("level", 78): [(object number, action code, value), ...]}: who writes
    each byte of the level, and with what.

    The numbers are the objects' own numbers, the ones the viewer writes on
    their boxes. Templates count too: a gate can wait on a byte that a cloned
    object writes.
    """
    found: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
    for number, o in enumerate(lvl["objects"]):
        for rule in o.get("rules", ()):
            key = _byte_write(rule)
            if key is None:
                continue
            code, value, _index, word = rule["action"]
            entry = (number, code, word if code in WORD_VALUE else value)
            if entry not in found.setdefault(key, []):
                found[key].append(entry)
    return found


def _fits(test, operand, code, written) -> bool:
    """Can this write make that test true? (The reverse project's `fits`,
    finding 331.) Writing a value is checked against the test; an OR can only
    set bits and an AND can only clear them; increments, copies and random
    values always fit, because what they leave behind is not known here."""
    if code in WRITES_VALUE:
        return passes(test, operand, written)
    if code in WRITES_ZERO:
        return passes(test, operand, 0)
    if code in SETS_BITS:
        return ((test in BIT_TESTS_SET and bool(written & operand))
                or test not in BIT_TESTS_SET | BIT_TESTS_CLEAR)
    if code in CLEARS_BITS:
        return ((test in BIT_TESTS_CLEAR and bool(~written & operand))
                or test not in BIT_TESTS_SET | BIT_TESTS_CLEAR)
    return True


# The four abilities are bits of save byte 8 (finding 336): each magic device
# tests its own bit in its rules, and that is how the viewer knows which one it
# asks for. Bit 2 is set only by the "all abilities" cheat and read by nothing;
# bit 128 is the key Bugs carries.
ABILITIES = {1: "FAN", 4: "MUSIC", 8: "SUPER JUMP", 16: "OPEN SESAME"}
ABILITY_BYTE = 8
ABILITY_TESTS = {0x1F, 0x28}          # save byte & mask, set or clear


def ability_of(obj) -> str | None:
    """The ability a magic device asks for, or None if the object is not one
    (finding 336): the name goes on its box instead of what its box does, which
    for the open sesame device of *Follow the Red Pirate Road* (`L03D1`) said
    only PLATFORM."""
    for rule in obj.get("rules", ()):
        op, value, index = rule["condition"]
        if op in ABILITY_TESTS and index == ABILITY_BYTE:
            for bit, name in ABILITIES.items():
                if value & bit:
                    return name
    return None


def _states_of(obj) -> dict[int, list[int]]:
    return {s["number"]: [k for k in s["slots"] if k != hazards.END_MARKER]
            for s in obj.get("states", ())}


def _roles_of(obj, keys) -> list[int]:
    by_key = {st["key"]: st for st in obj.get("steps", ())}
    return [by_key[k]["role"] for k in keys if k in by_key]


def is_gate(obj) -> bool:
    """A solid object with more than one state, that does not move by itself
    and is not a pickup (the population of `state_boxes.md`)."""
    if obj.get("category") != 14 or obj["block_type"] == 0x08 or not obj["position"]:
        return False
    flags = (obj.get("static_flags") or (0, 0))[0]
    if flags & ONLY_SIGNALS:
        return False
    if any(st.get("control", 0) & MOVES for st in obj.get("steps", ())):
        return False
    return len(_states_of(obj)) > 1


def transitions(obj) -> list[dict]:
    """Every rule of the object that moves it to another state, with what it
    waits on: {from, to, byte, index, value, always}."""
    by_key = {st["key"]: st for st in obj.get("steps", ())}
    in_state = {}
    for number, keys in _states_of(obj).items():
        for key in keys:
            in_state.setdefault(key, []).append(number)
    # the step each rule group belongs to, once: looking it up rule by rule
    # made opening a level with many gates take seconds
    by_group = {}
    for st in by_key.values():
        if st.get("rules"):
            by_group.setdefault(st["rules"], st)
    out = []
    for rule in obj.get("rules", ()):
        if not rule.get("next_state"):
            continue
        step = by_group.get(rule["key"])
        sources = in_state.get(step["key"], []) if step else []
        test = _byte_test(rule)
        out.append({"from": sources, "to": rule["next_state"],
                    "byte": test[0] if test else None,
                    "index": test[1] if test else None,
                    "value": test[2] if test else None,
                    "test": test[3] if test else None,
                    "always": test is None and rule["condition"][0] == 0})
    return out


def gates_of(lvl) -> list[dict]:
    """The gates of a level: {number, object, states, transitions, opened_by}.

    `opened_by` is {state: [object numbers]}: who writes the byte the rule that
    moves the gate INTO that state waits on -- one step, the last one. A gate
    that opens in two steps (*Follow the Red Pirate Road* (`L03D1`) object 35
    goes from 1 to 314 on a level byte and only then to 172) has the writers of
    its last step here, and the reverse project's `keys.md` is where the whole
    chain is written out.
    """
    who = writers(lvl)
    found = []
    for number, o in enumerate(lvl["objects"]):
        if not is_gate(o):
            continue
        moves = transitions(o)
        opened_by: dict[int, list[int]] = {}
        for move in moves:
            if move["byte"] is None:
                continue
            for other, code, written in who.get((move["byte"], move["index"]), ()):
                if not _fits(move["test"], move["value"], code, written):
                    continue
                if other not in opened_by.setdefault(move["to"], []):
                    opened_by[move["to"]].append(other)
        found.append({"number": number, "object": o, "states": _states_of(o),
                      "transitions": moves, "opened_by": opened_by,
                      "start": hazards.start_state(o)})
    return found


# a step with this bit in its control dword deletes the object when its
# animation ends (finding 323): the gate does not exist any more
DELETES_AT_END = 0x4


def deletes(obj, state) -> bool:
    """Whether the state ends with the object deleted."""
    by_key = {st["key"]: st for st in obj.get("steps", ())}
    return any(by_key[k].get("control", 0) & DELETES_AT_END
               for k in _states_of(obj).get(state, ()) if k in by_key)


def _box_of(sec4, res, obj, role):
    """The box a role's animation sets, read here and not through
    `montage.collision_box`.

    The checks replace that function to turn the flag Collision boxes off
    (`checks/check_walls.py`), and which state a gate is shown in is geometry,
    not an overlay: reading the box through it made the two builds of that
    check differ in four levels.
    """
    import struct

    from game import montage
    from game import rig as rigmod

    try:
        _r, pose = montage.choose_sources(sec4, obj["resources"], res, obj, role=role)
        if pose is None:
            return None
        for _anim_time, records in rigmod.read_blocks(sec4, pose["offset"], pose["size"], 1):
            for _d, category, _v, payload in records:
                if category == rigmod.T_BOX and len(payload) >= 12:
                    return struct.unpack_from("<6h", payload, 0)
    except Exception:  # noqa: BLE001
        return None
    return None


def box_volume(sec4, res, obj, state, cache=None) -> float | None:
    """How big the object's box is in a state, or None when it has none.

    The box of a state is the one its animation sets (a type 9 record, finding
    323); an empty box stops nobody.
    """
    roles = roles_of_state(obj, state)
    best = None
    for role in roles:
        # a level has many gates of the same model: the box of a (resources,
        # role) pair is read once, or opening a level costs seconds
        key = (tuple(obj["resources"]), role)
        if cache is not None and key in cache:
            box = cache[key]
        else:
            box = _box_of(sec4, res, obj, role)
            if cache is not None:
                cache[key] = box
        if not box:
            continue
        x0, y0, z0, x1, y1, z1 = box
        volume = abs(x1 - x0) * abs(y1 - y0) * abs(z1 - z0)
        best = volume if best is None else max(best, volume)
    return best


def open_and_closed(sec4, res, gate, cache=None) -> tuple[int | None, int | None]:
    """(the state where the gate is most open, the one where it is most shut).

    Only the states a SWITCH can put it in count, that is the ones a rule
    waiting on a level or save byte leads to (`opened_by`), plus the state the
    game starts it in. Taking any state with a smaller box would pick "hit"
    (state 3) and "dead" (state 4), which are what happens when something
    strikes the object, not a gate opening: in *Hey... What's up, Dock? 1*
    (`L03A`) that made the crate pile #94 disappear.

    Among those states the one whose box is smallest -- an emptied box, or none
    at all, or the object deleted -- is "open", and the biggest is "shut". A
    gate no switch opens, or one whose boxes never change, gets (None, None)
    and is left as the game starts it.
    """
    obj = gate["object"]
    # only what blocks the way is opened: an object whose box does not stop
    # Bugs is not a gate to open but a thing of the game (the crate pile #94 of
    # *Hey... What's up, Dock? 1* (`L03A`) is a PLATFORM and its "open" state
    # is the explosion). The rule about defaults: switches are pulled
    # when the effect opens or moves geometry, not when it deletes objects.
    flags = (obj.get("static_flags") or (0, 0))[0]
    if not flags & STOPS_BUGS or flags & STAND_ON:
        return (None, None)
    candidates = set(gate["opened_by"]) | ({gate["start"]} if gate["start"] else set())
    sizes = {}
    for state in candidates:
        if state not in gate["states"]:
            continue
        sizes[state] = (-1.0 if deletes(obj, state)
                        else box_volume(sec4, res, obj, state, cache))
    known = {state: v for state, v in sizes.items() if v is not None}
    if len(known) < 2 or len(set(known.values())) < 2:
        return (None, None)
    opened = min(known, key=lambda k: known[k])
    shut = max(known, key=lambda k: known[k])
    return (opened, shut)


def groups_of(lvl, found=None) -> dict[int, list[int]]:
    """{switch object number: [gate numbers]}: the gates that the same object
    opens, which is the grouping the reverse project's `keys.md` shows. A gate
    nothing opens, or one whose switch opens only it, is not in a group: the
    level's own entry covers it.
    """
    by_switch: dict[int, list[int]] = {}
    for gate in (found if found is not None else gates_of(lvl)):
        for who in gate["opened_by"].values():
            for switch in who:
                if switch != gate["number"] and gate["number"] not in by_switch.setdefault(switch, []):
                    by_switch[switch].append(gate["number"])
    return {switch: sorted(numbers) for switch, numbers in by_switch.items() if len(numbers) > 1}


def roles_of_state(obj, state) -> list[int]:
    """The animation roles a state plays, in playlist order: what the viewer
    has to play to show the gate in that state."""
    return _roles_of(obj, _states_of(obj).get(state, []))
