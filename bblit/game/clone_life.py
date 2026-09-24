"""Which clones the game really has in a level, and for how long.

A template (block 0x08) becomes a live object when a rule of a live object
clones it (effect 0x100 or 0x40000, the template's id in field +28: Ombelll's
finding 194, our 274 and 279). Whether that rule ever fires by itself is what
this module reads, the way the engine walks the rules (the reverse's notes
N10-N13, N20, N30):

* a **type 14** object walks, every tick, the rules of the group of the step
  it is in; it starts in state 2 (else 1), a state is a playlist of up to five
  steps, and when the playlist is over it goes back to state 1. A rule passes
  when its masks match the object's flags, its gates hold (frame, end of the
  animation, a draw, a radius, "hit by id", the side test) and its condition
  is true; it moves the object to the state in +2 unless effect 0x10, and
  without effect 0x8000 the walk stops there;
* a **type 16** trigger (and the other small handlers that carry rules) walks
  its whole list every tick; with bit 4 of the second static flag word it runs
  only while Bugs is within 2000 in plan;
* effect 0x10000 (third parameter not 1) deletes the object that fired; a step
  with control bit 4 deletes it at its end; types 31 (bullet) and 32 (text)
  always end by themselves (N13a), a type 4 sprite with an 0x10000 rule after
  one cycle.

What runs **by itself** is read without Bugs doing anything: Bugs stands where
the level starts him, nobody touches, hits, carries or presses anything, the
level and save bytes start at zero and take every value that the rules able
to fire by themselves write into them (a fixed point: the ride of Mine or
mine? 3 is a trigger that writes byte 49 = 40 at its first tick, and each
stretch writes the next number at the end of its animation). Time passes, so
frames, animation ends, clocks and draws do come. The camera is free, so
culling by distance or area stops nobody for long.

Each cloning rule gets one of three answers:

* `LEVEL`: it fires by itself and the clone does not end by itself: the game
  has it in the level (the rails and galleries of the mines, the torches'
  flames). A clone that another object deletes later (a gallery behind the
  ride) is still LEVEL: it is part of the place while it is there;
* `PASSING`: it fires by itself but the clone ends by itself (a flash, a
  sprite that plays once, a text), or the object that made it deletes it
  again a few frames later (what an attacker swings, finding 317);
* `EVENT`: it needs Bugs (a touch, a radius, a hit, a button, a state of his),
  or a byte only such a rule writes: what appears later.

Readings that are choices, not code: a mask on the object's own flags is never
met by itself (not even 0x2, on the ground); an undecoded condition (0x5C,
0x5D, 0x60, ...) is false; the radius to another object is measured between
the places in the file.
"""

from __future__ import annotations

import math
from collections import deque

LEVEL, PASSING, EVENT = "level", "passing", "event"

CLONES = 0x100 | 0x40000
STAYS = 0x10                     # the rule does not change state
GO_ON = 0x8000                   # the walk goes on to the next rule
DELETES_SELF = 0x10000           # (third parameter not 1: 1 kills the player)
SENDS = 0x400000                 # another object (or Bugs) to the state in +24
DELETES_ID = 0x4000000
FRAME, END, DRAW, DRAW_28 = 0x40, 0x4, 0x2, 0x20000
RADIUS_BUGS, RADIUS_ID, OUTSIDE = 0x08000000, 0x10000000, 0x200000
HIT_BY_ID, SIDE_TEST = 0x2000, 0x20
END_MARKER = 0xFFF0
LOOP, ONCE_HOLD = 0x1, 0x802
DELETED_AT_END = 0x4             # step control bit
NEAR_BUGS_ONLY = 0x4             # second static flag word of a type 16
NEAR_BUGS_RANGE = 2000

ALL = frozenset(range(256))

# conditions on a level byte (index b) against the value a, or against the
# level byte a; the same codes offset for the save bytes (make_states.COND)
_LEVEL_TESTS = {
    0x01: lambda v, a: v == a, 0x25: lambda v, a: v != a, 0x03: lambda v, a: v > a,
    0x05: lambda v, a: v >= a, 0x07: lambda v, a: v < a, 0x09: lambda v, a: v <= a,
    0x46: lambda v, a: _s8(v) > _s8(a), 0x47: lambda v, a: _s8(v) < _s8(a),
    0x1E: lambda v, a: bool(v & a), 0x27: lambda v, a: not v & a,
}
_SAVE_TESTS = {
    0x02: lambda v, a: v == a, 0x26: lambda v, a: v != a, 0x04: lambda v, a: v > a,
    0x06: lambda v, a: v >= a, 0x08: lambda v, a: v < a, 0x0A: lambda v, a: v <= a,
    0x59: lambda v, a: _s8(v) < _s8(a), 0x1F: lambda v, a: bool(v & a),
    0x28: lambda v, a: not v & a,
}
# byte against byte: (table, test on (b, a))
_PAIR_TESTS = {
    0x0F: ("level", lambda x, y: x == y), 0x3D: ("level", lambda x, y: x == y),
    0x3F: ("level", lambda x, y: x != y), 0x41: ("level", lambda x, y: y < x),
    0x43: ("level", lambda x, y: x < y),
    0x10: ("save", lambda x, y: x == y), 0x3E: ("save", lambda x, y: x == y),
    0x40: ("save", lambda x, y: x != y),
}
# conditions that hold, or not, whatever the tables: Bugs standing still at
# his start and nobody pressing anything; the object's own clock runs
_ALWAYS = {0x00, 0x0B, 0x30, 0x4D, 0x35, 0x36, 0x0D, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A,
           0x45, 0x5B, 0x51}
# the clock ones are not certain: they hold at some tick, not at every one
_CLOCK = {0x15, 0x16, 0x17, 0x18, 0x19, 0x1A}

# actions that write a level byte (index i, value v) and a save byte
_LEVEL_WRITES = {0x03, 0x05, 0x07, 0x0B, 0x0D, 0x12, 0x0F, 0x14, 0x16, 0x1C, 0x24, 0x27, 0x2D}
_SAVE_WRITES = {0x04, 0x17, 0x06, 0x08, 0x0C, 0x0E, 0x13, 0x10, 0x15, 0x1B, 0x25, 0x28}
# the actions whose value is the whole word at +16 (make_states.WORD_VALUE)
_WORD_VALUE = {0x0F, 0x10, 0x14, 0x15, 0x16, 0x1B, 0x1C}
# the actions that step a byte up or down: they can fire again and again
_STEPS = {0x03, 0x05, 0x04, 0x17, 0x06, 0x16, 0x24, 0x25, 0x27, 0x28}
# types whose handler ends the object by itself (N13a)
_SHORT_LIVED = {31, 32}


def _s8(v):
    return v - 256 if v >= 128 else v


def _step_ends(step) -> bool:
    return (step.get("play", LOOP) & 0x803) not in (LOOP, ONCE_HOLD)


class _Actor:
    """A live object of the reading: a placed object, or a template as it is
    once cloned (one per template, at every place it is cloned from)."""

    __slots__ = ("obj", "places", "area", "states", "walker", "fired", "stays")

    def __init__(self, obj, place, area):
        self.obj = obj
        self.places = [place]
        self.area = area
        self.walker = obj.get("category") == 14 and bool(obj.get("states"))
        start = 2 if any(s["number"] == 2 for s in obj.get("states", ())) else 1
        self.states = {start} if self.walker else set()
        self.fired = set()               # indices of the rules that can fire
        self.stays = None                # _survives, once the tables are final


class Reading:
    """The fixed point of a level: which rules can fire by themselves, what
    the bytes can hold, and which clones stay."""

    def __init__(self, lvl):
        objects = lvl["objects"]
        self.objects = objects
        self.templates = {}
        for o in objects:
            if o["block_type"] == 0x08 and o["role"] not in self.templates:
                self.templates[o["role"]] = o
        player = next((o for o in objects if o.get("start") and o.get("position")), None)
        self.bugs = tuple(player["position"]) if player else None
        self.bugs_area = player.get("area") if player else None
        self.tables = {"level": {}, "save": {}}
        # a template read as if cloned changes nothing (_actor_for)
        self._dry = False
        # the work queue of the fixed point, and who reads each byte
        self._queue, self._queued = deque(), set()
        self._current = None
        self._readers: dict = {}
        self._hypothetical: dict = {}
        self.actors: dict = {}
        for n, o in enumerate(objects):
            if o["block_type"] != 0x08 and o.get("position") is not None:
                self.actors[("placed", n)] = _Actor(o, tuple(o["position"]), o.get("area"))
        self.by_id: dict = {}
        for key, actor in self.actors.items():
            if actor.obj.get("role"):
                self.by_id.setdefault(actor.obj["role"], []).append(key)
        self._run()

    # -- the tables ------------------------------------------------------------
    def _values(self, table, index):
        if self._current is not None:
            self._readers.setdefault((table, index & 0xFFFF), set()).add(self._current)
        return self.tables[table].get(index, {0})

    def _write(self, table, index, values) -> bool:
        if self._dry:
            return False
        index &= 0xFFFF
        now = self.tables[table].setdefault(index, {0})
        new = {v & 0xFF for v in values} - now
        if new:
            now |= new
            for reader in self._readers.get((table, index), ()):
                self._enqueue(reader)
            return True
        return False

    def _condition(self, actor, rule):
        """(can hold, holds at every tick) with the tables as they are."""
        op, a, b = rule["condition"]
        if op in _LEVEL_TESTS or op in _SAVE_TESTS:
            table = "level" if op in _LEVEL_TESTS else "save"
            test = (_LEVEL_TESTS if op in _LEVEL_TESTS else _SAVE_TESTS)[op]
            results = {test(v, a) for v in self._values(table, b)}
            return True in results, results == {True}
        if op in _PAIR_TESTS:
            table, test = _PAIR_TESTS[op]
            results = {test(x, y) for x in self._values(table, b) for y in self._values(table, a)}
            return True in results, results == {True}
        if op in _ALWAYS:
            return True, op not in _CLOCK
        if op in (0x0E, 0x2C):            # Bugs's area == / != a
            same = self.bugs_area == a
            holds = same if op == 0x0E else not same
            return holds, holds
        if op in (0x3A, 0x3B, 0x3C):      # its word +0x1e (opcode 0x1E) against a
            word = actor.obj.get("camera_y") or 0
            holds = {0x3A: word == a, 0x3B: word > a, 0x3C: word < a}[op]
            return holds, holds
        if op == 0x4A:                    # its area == a
            holds = actor.area == a
            return holds, holds
        return False, False

    def _distance(self, actor, other, rule, plan=False):
        """Whether a radius gate can hold, from the places in the file."""
        if other is None:
            return False
        radius = rule["field24"] & 0xFFFF
        outside = bool(rule["effect"] & OUTSIDE)
        for p in actor.places:
            d = math.hypot(p[0] - other[0], p[2] - other[2]) if plan else math.dist(p, other)
            if (d > radius) if outside else (d <= radius):
                return True
        return False

    def _gates(self, actor, rule):
        """(can hold, holds at every tick) for the masks and the gates."""
        if rule["mask"] or rule.get("mask2", 0):
            return False, False
        effect = rule["effect"]
        if effect & (HIT_BY_ID | SIDE_TEST):
            return False, False
        if effect & RADIUS_BUGS:
            return self._distance(actor, self.bugs, rule), False
        if effect & RADIUS_ID:
            target = rule["field28"]
            places = [p for key in self.by_id.get(target, ()) for p in self.actors[key].places]
            return any(self._distance(actor, p, rule) for p in places), False
        certain = not effect & (FRAME | END | DRAW | DRAW_28)
        return True, certain

    # -- the walk --------------------------------------------------------------
    def _groups(self, actor):
        """(rule group key, step) of every step of the states it can be in."""
        steps = {s["key"]: s for s in actor.obj.get("steps", ())}
        by_number = {s["number"]: s for s in actor.obj.get("states", ())}
        for number in sorted(actor.states):
            state = by_number.get(number)
            if state is None:
                continue
            for key in state["slots"]:
                if key == END_MARKER:
                    break
                step = steps.get(key)
                if step is not None:
                    yield number, step

    def _walk(self, actor, rules) -> bool:
        changed = False
        for i, rule in rules:
            can, certain = self._gates(actor, rule)
            if can:
                can, sure = self._condition(actor, rule)
                certain = certain and sure
            if not can:
                continue
            if i not in actor.fired:
                actor.fired.add(i)
                changed = True
            changed |= self._fire(actor, rule)
            if certain and not rule["effect"] & GO_ON:
                break
        return changed

    def _act(self, actor, rule) -> bool:
        """The rule's action on the tables: whether a byte took a new value."""
        changed = False
        act, byte_value, index, word = rule["action"]
        value = (word & 0xFFFF) if act in _WORD_VALUE else byte_value
        if act in _LEVEL_WRITES or act in _SAVE_WRITES:
            table = "level" if act in _LEVEL_WRITES else "save"
            now = self._values(table, index)
            if act in (0x03, 0x04, 0x17):
                new = {v + 1 for v in now}
            elif act in (0x05, 0x06):
                new = {v - 1 for v in now}
            elif act in (0x07, 0x08):
                new = {0}
            elif act in (0x0B, 0x0C):
                new = {v | value for v in now}
            elif act in (0x0D, 0x0E):
                new = {v & value for v in now}
            elif act in (0x12, 0x13):
                new = {value}
            elif act in (0x0F, 0x10):
                new = set(range(max(1, value))) if value <= 256 else ALL
            elif act == 0x14:
                new = set(self._values("level", value))
            elif act == 0x15:
                new = set(self._values("save", value))
            elif act == 0x1B:
                new = set(self._values("level", value))
            elif act == 0x1C:
                new = set(self._values("save", value))
            elif act == 0x16:
                new = {v + 1 for v in now}
                changed |= self._write("level", value, {v + 1 for v in self._values("level", value)})
            elif act in (0x24, 0x25):
                new = {v + value for v in now}
            elif act in (0x27, 0x28):
                new = {v - value for v in now}
            else:                         # 0x2d: its word +0x1e
                new = {actor.obj.get("camera_y") or 0}
            changed |= self._write(table, index, new)
        return changed

    def _fire(self, actor, rule) -> bool:
        effect = rule["effect"]
        changed = self._act(actor, rule)
        if changed and rule["action"][0] in _STEPS:
            # a counter: the rule fires again at the next tick as long as it
            # can, so its closure is taken here rather than by walking
            # everything again once per value (the same fixed point)
            while (self._gates(actor, rule)[0] and self._condition(actor, rule)[0]
                   and self._act(actor, rule)):
                pass
        if effect & CLONES and rule["field28"] > 0:
            changed |= self._clone(actor, rule["field28"])
        if effect & SENDS and not effect & RADIUS_BUGS and not self._dry:
            for key in self.by_id.get(rule["field28"], ()):
                target = self.actors[key]
                if target.walker and rule["field24"] not in target.states:
                    target.states.add(rule["field24"])
                    self._enqueue(target)
        if actor.walker and rule["next_state"] and not effect & STAYS:
            if rule["next_state"] not in actor.states:
                actor.states.add(rule["next_state"])
                changed = True
        return changed

    def _clone(self, actor, role) -> bool:
        if self._dry:
            return False
        template = self.templates.get(role)
        if template is None:
            return False
        key = ("template", role)
        clone = self.actors.get(key)
        place = actor.places[0]
        if clone is None:
            clone = self.actors[key] = _Actor(template, place, actor.area)
            self.by_id.setdefault(role, []).append(key)
            self._enqueue(clone)
        elif place not in clone.places:
            clone.places.append(place)
            self._enqueue(clone)
        return False

    def _run_actor(self, actor) -> bool:
        obj = actor.obj
        rules = list(enumerate(obj.get("rules", ())))
        if obj.get("category") == 14 and not actor.walker:
            return False                  # a type 14 with no state walks nothing
        if not actor.walker:
            if obj.get("category") == 16 and (obj.get("static_flags") or [0, 0])[1] & NEAR_BUGS_ONLY:
                if self.bugs is None or not any(
                        math.hypot(p[0] - self.bugs[0], p[2] - self.bugs[2]) <= NEAR_BUGS_RANGE
                        for p in actor.places):
                    return False
            return self._walk(actor, rules)
        changed = False
        for number, step in list(self._groups(actor)):
            group = step.get("rules")
            if group:
                changed |= self._walk(actor, [(i, r) for i, r in rules if r["key"] == group])
        # a playlist that runs out goes back to state 1
        for number, state in [(s["number"], s) for s in obj.get("states", ())]:
            if number not in actor.states or 1 in actor.states:
                continue
            keys = [k for k in state["slots"] if k != END_MARKER]
            steps = {s["key"]: s for s in obj.get("steps", ())}
            last = steps.get(keys[-1]) if keys else None
            if last is not None and _step_ends(last):
                actor.states.add(1)
                changed = True
        return changed

    def _enqueue(self, actor):
        if id(actor) not in self._queued:
            self._queued.add(id(actor))
            self._queue.append(actor)

    def _run(self):
        """To the fixed point, re-reading an actor only when something it
        reads has changed: a table byte, its states, its places."""
        for actor in self.actors.values():
            self._enqueue(actor)
        while self._queue:
            actor = self._queue.popleft()
            self._queued.discard(id(actor))
            self._current = actor
            if self._run_actor(actor):
                self._enqueue(actor)
        self._current = None

    # -- how long a clone lasts ----------------------------------------------------
    def _eventual(self, actor, rule) -> bool:
        """A rule that will fire at some tick whatever happens: no mask, no
        radius, no hit, and a condition that holds on every value the tables
        can take (or the object's clock)."""
        if rule["mask"] or rule.get("mask2", 0):
            return False
        if rule["effect"] & (HIT_BY_ID | SIDE_TEST | RADIUS_BUGS | RADIUS_ID):
            return False
        op = rule["condition"][0]
        return op in _CLOCK or self._condition(actor, rule)[1]

    def _rules_survive(self, actor, rules, here, alive):
        """Walking one list of rules: False when a death comes before any way
        out, True when the walk can end without dying, None when nothing in
        the list decides."""
        for _i, rule in rules:
            can, certain = self._gates(actor, rule)
            if can:
                can, sure = self._condition(actor, rule)
                certain = certain and sure
            if not can:
                continue
            effect = rule["effect"]
            if effect & DELETES_SELF and rule["field28"] != 1:
                if self._eventual(actor, rule):
                    return False
                continue
            if effect & GO_ON:
                continue
            target = here
            if actor.walker and rule["next_state"] and not effect & STAYS:
                target = rule["next_state"]
            if target == here or target in alive:
                return True
            if certain:
                return False
        return None

    def _state_survives(self, actor, number, alive) -> bool:
        obj = actor.obj
        steps = {s["key"]: s for s in obj.get("steps", ())}
        state = next((s for s in obj.get("states", ()) if s["number"] == number), None)
        if state is None:
            return False
        rules = list(enumerate(obj.get("rules", ())))
        for key in state["slots"]:
            if key == END_MARKER:
                break
            step = steps.get(key)
            if step is None:
                continue
            group = step.get("rules")
            verdict = self._rules_survive(actor, [(i, r) for i, r in rules if r["key"] == group],
                                          number, alive) if group else None
            if verdict is not None:
                return verdict
            if not _step_ends(step):
                return True               # it holds or loops here and nothing ends it
            if step.get("control", 0) & DELETED_AT_END:
                return False
        return number == 1 or 1 in alive  # the playlist is over: back to state 1

    def _survives(self, actor) -> bool:
        """Whether the clone can last: False only when it ends by itself
        whatever the tables hold (a flash that deletes itself at the end of its
        animation), True when some value of the tables keeps it (a stretch of
        the mines' rails, kept while the ride is near it)."""
        if actor.stays is not None:
            return actor.stays
        obj = actor.obj
        if obj.get("category") in _SHORT_LIVED:
            actor.stays = False
        elif obj.get("category") == 14 and not actor.walker:
            actor.stays = False           # no step left: deleted at its start (N13a)
        elif not actor.walker:
            actor.stays = self._rules_survive(actor, list(enumerate(obj.get("rules", ()))),
                                              None, set()) is not False
        else:
            alive = set(actor.states)
            changed = True
            while changed:
                changed = False
                for number in sorted(alive):
                    if not self._state_survives(actor, number, alive):
                        alive.discard(number)
                        changed = True
            start = 2 if any(s["number"] == 2 for s in obj.get("states", ())) else 1
            actor.stays = start in alive
        return actor.stays

    # -- the answers -----------------------------------------------------------
    def _actor_for(self, key):
        """The actor of a key; a template that nothing clones by itself is
        read as it would be once cloned (the torch a trigger lights: its flame
        comes by itself), against the final tables and writing nothing."""
        actor = self.actors.get(key)
        if actor is not None or key[0] != "template":
            return actor
        actor = self._hypothetical.get(key[1])
        if actor is None:
            template = self.templates.get(key[1])
            if template is None:
                return None
            place = tuple(template.get("position") or (0, 0, 0))
            actor = _Actor(template, place, template.get("area"))
            self._hypothetical[key[1]] = actor
            self._dry = True
            try:
                while self._run_actor(actor):
                    pass
            finally:
                self._dry = False
        return actor

    def fires(self, key, i_rule) -> bool:
        """Whether rule `i_rule` of actor `key` ("placed", n) or ("template",
        role) can fire by itself."""
        actor = self._actor_for(key)
        return actor is not None and i_rule in actor.fired

    def kind(self, key, rule_index, rule) -> str:
        """LEVEL, PASSING or EVENT for a cloning rule of an actor."""
        if not self.fires(key, rule_index):
            return EVENT
        if self._takes_back(key, rule):
            return PASSING
        clone = self._actor_for(("template", rule["field28"]))
        return PASSING if clone is not None and not self._survives(clone) else LEVEL

    def _takes_back(self, key, rule) -> bool:
        """Whether the object that makes the clone deletes it again by
        itself, from the same group of rules: frame A clones what it holds,
        frame B deletes the live object with that id (finding 317, the
        attackers). The clone comes and goes at every turn of the animation."""
        actor = self._actor_for(key)
        for i, other in enumerate(actor.obj.get("rules", ())):
            if (other["key"] == rule["key"] and other["effect"] & DELETES_ID
                    and other["field28"] == rule["field28"] and i in actor.fired
                    and self._eventual(actor, other)):
                return True
        return False

def kinds(lvl) -> dict:
    """The answer for every cloning rule of the level, in one dictionary a
    level can keep in its piece cache: {("placed", object index, rule index)
    or ("template", role, rule index): LEVEL, PASSING or EVENT}."""
    reading = Reading(lvl)
    out = {}
    for n, o in enumerate(lvl["objects"]):
        if o["block_type"] == 0x08:
            if reading.templates.get(o["role"]) is not o:
                continue          # the first template with a role is the one cloned
            key = ("template", o["role"])
        elif o.get("position") is not None:
            key = ("placed", n)
        else:
            continue
        for i, r in enumerate(o.get("rules", ())):
            if r["effect"] & CLONES and r["field28"] > 0:
                out[key + (i,)] = reading.kind(key, i, r)
    _one_of_each(lvl, out)
    return out


def _one_shot(rule) -> bool:
    return bool(rule["effect"] & DELETES_SELF) and rule["field28"] != 1


def _step_value(act, value, now):
    """One action on a known byte, or None for an action not followed here."""
    if act in (0x03, 0x04, 0x17):
        return (now + 1) & 0xFF
    if act in (0x05, 0x06):
        return (now - 1) & 0xFF
    if act in (0x07, 0x08):
        return 0
    if act in (0x12, 0x13):
        return value & 0xFF
    if act in (0x0B, 0x0C):
        return now | value
    if act in (0x0D, 0x0E):
        return now & value
    if act in (0x24, 0x25):
        return (now + value) & 0xFF
    if act in (0x27, 0x28):
        return (now - value) & 0xFF
    return None


def _one_of_each(lvl, out):
    """A trigger that clones and deletes itself makes ONE clone: where it has
    several rules of that kind, each cloning something else, they are
    alternatives, and only one of them is in the level. On the disc: the
    twelve sign posts of Wabbit or Duck Season? (LB01), each a draw between
    Bugs's sign (at most 8, level byte 44) and Daffy's (at most 7, byte 45).
    The game draws at random; the viewer shows one outcome the game can
    give: the triggers in the order of the file, every draw won, the
    counters followed with their real values. The other alternative stays a
    "clones" rule (Cloned templates -> All)."""
    choices = []
    for n, o in enumerate(lvl["objects"]):
        if o["block_type"] == 0x08 or o.get("position") is None:
            continue
        rules = [(i, r) for i, r in enumerate(o.get("rules", ()))
                 if r["effect"] & CLONES and r["field28"] > 0 and _one_shot(r)
                 and out.get(("placed", n, i)) == LEVEL]
        if rules:
            choices.append((n, rules))
    if not any(len({r["field28"] for _i, r in rules}) > 1 for _n, rules in choices):
        return
    known = {}
    for n, rules in choices:
        taken = None
        for i, r in rules:
            op, a, b = r["condition"]
            table = "level" if op in _LEVEL_TESTS else "save" if op in _SAVE_TESTS else None
            if op and table is None:
                taken = i            # a condition not followed: the first one stays
                break
            if table is not None:
                test = (_LEVEL_TESTS if table == "level" else _SAVE_TESTS)[op]
                if not test(known.get((table, b), 0), a):
                    continue
            taken = i
            act, byte_value, index, word = r["action"]
            if act in _LEVEL_WRITES or act in _SAVE_WRITES:
                where = ("level" if act in _LEVEL_WRITES else "save", index)
                value = (word & 0xFFFF) if act in _WORD_VALUE else byte_value
                after = _step_value(act, value, known.get(where, 0))
                if after is not None:
                    known[where] = after
            break
        for i, _r in rules:
            if i != taken:
                out[("placed", n, i)] = EVENT
