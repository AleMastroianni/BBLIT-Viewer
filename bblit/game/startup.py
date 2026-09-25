"""What is alive when a level has just loaded: the first tick of the level,
run the way the engine runs it (the reverse's N73 and N74, its recipe of
N74 section 3).

- **The tables:** the 256 level bytes are zero; the save bytes are a new
  game's (byte 0 = 3, 1 = 6, 2 = 6, 14 = 56, the rest 0), or a save given
  as {index: value}.
- **The objects:** every placed object (blocks 0x07 and 0x0A) exists from the
  first tick, in the order of the file; a type 14 starts in state 2 if it
  has one, else 1, in the first slot. The pass walks them in that order, and
  a clone born during the pass is appended to its end and runs its own first
  tick in the same pass (N73 section 4).
- **A type 14** walks the rules of its step's group in order (N73 section 2):
  the masks (nothing has touched anything yet: a mask fails), the gates of
  the effect word (frame 0 has just begun: effect 0x40 passes when its frame
  is 0, the end of the animation 0x4 does not; a random draw is not taken
  here and is counted apart), the condition on the tables as they are at that
  moment, the target (the first live object with that id; 0x400000 sends it
  to a state), the distance (in plan, from the places), the action, the
  effects (off its parent, a clone, a hanging on Bugs, a delete by id, its
  own death), then
  0x8000 goes on, 0x10 stops, anything else changes the state and stops.
- **A type 16** walks its whole list, with the skip labels (N73 section 3).
- **What is not done here:** the culling (every object runs, as they all do
  sooner or later under a free camera; the triggers run from tick 1 anyway),
  the handlers of the other types (4, 9, 31, 32, 34, 36: none of them clones
  at the first tick on the disc's reading), the animation rows (a row that
  clones at frame 0).

`Startup(lvl).alive` gives the object numbers of the placed objects still
alive after the first tick, `born` the clones born and still alive, each
with the route of rules that made it as `game/catalog.py` writes routes, and
`on_bugs` the objects hanging from Bugs after it.
"""

from __future__ import annotations

import math

from game import clone_life as cl

NEW_GAME = cl.NEW_GAME

# the conditions on the tables, read on concrete values
_LEVEL_TESTS, _SAVE_TESTS, _PAIR_TESTS = cl._LEVEL_TESTS, cl._SAVE_TESTS, cl._PAIR_TESTS
# at the first tick: true whatever the tables (N74's table)
_TRUE = {0x00, 0x0B, 0x30, 0x4D, 0x35, 0x36, 0x0D, 0x45, 0x51, 0x5B}
TARGETED = 0x400000 | 0x18000000 | 0x40000000   # the rule needs its target (N73 section 2.5)
TAKES = 0x20000000
DIES_TOO = 0x2000000
DETACH = 0x8


class _Live:
    __slots__ = ("number", "obj", "key", "place", "area", "state", "route", "dead", "on_bugs")

    def __init__(self, number, obj, key, place, area, route):
        self.number, self.obj, self.key, self.route = number, obj, key, route
        self.place, self.area = place, area
        states = {s["number"] for s in obj.get("states", ())}
        self.state = 2 if 2 in states else (1 if 1 in states else None)
        self.dead = False
        self.on_bugs = False


class Startup:
    """The first tick of a level (see the module's docstring)."""

    def __init__(self, lvl, save=None):
        self.lvl = lvl
        objects = lvl["objects"]
        self.level = [0] * 256
        self.save = [0] * 256
        for i, v in (save if save is not None else NEW_GAME).items():
            self.save[i] = v & 0xFF
        self.templates = {}
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08 and o["role"] not in self.templates:
                self.templates[o["role"]] = n
        player = next((o for o in objects if o.get("start") and o.get("position")), None)
        self.bugs = tuple(player["position"]) if player else None
        self.bugs_area = player.get("area") if player else None
        self.bugs_series = cl._first_slot(player) if player else None
        self.chain = []
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08:
                continue
            place = tuple(o["position"]) if o.get("position") else (0, 0, 0)
            self.chain.append(_Live(n, o, ("placed", n), place, o.get("area"), ()))
        self.random_draws = 0      # rules that a random draw would have fired
        self._pass()
        self.alive = {x.number for x in self.chain if not x.dead and x.key[0] == "placed"}
        self.born = {}
        for x in self.chain:
            if x.key[0] == "template" and not x.dead:
                self.born[x.route] = x
        self.on_bugs = {x.number for x in self.chain if not x.dead and x.on_bugs}

    # ---- the tables
    def _condition(self, live, rule) -> bool:
        op, a, b = rule["condition"]
        if op in _LEVEL_TESTS:
            return _LEVEL_TESTS[op](self.level[b], a)
        if op in _SAVE_TESTS:
            return _SAVE_TESTS[op](self.save[b], a)
        if op in _PAIR_TESTS:
            table, test = _PAIR_TESTS[op]
            t = self.level if table == "level" else self.save
            return test(t[b], t[a])
        if op in _TRUE:
            return True
        w = a | (b << 8)
        if op in (0x15, 0x18):          # the clock (0 at the first tick) < w
            return w > 0
        if op in (0x16, 0x19):          # > w: never at the first tick
            return False
        if op == 0x17:                  # == w
            return w == 0
        if op in (0x0C, 0x4E):          # Bugs's series / step key == a
            return self.bugs_series == a
        if op in (0x0E, 0x2C):
            return (self.bugs_area == a) == (op == 0x0E)
        if op in (0x3A, 0x3B, 0x3C):
            word = live.obj.get("camera_y") or 0
            return {0x3A: word == a, 0x3B: word > a, 0x3C: word < a}[op]
        if op == 0x4A:
            return live.area == a
        return False                    # pads held, Bugs hit or holding, menus: not at the first tick

    def _act(self, live, rule):
        act, byte_value, index, word = rule["action"]
        value = (word & 0xFFFF) if act in cl._WORD_VALUE else byte_value
        if act not in cl._LEVEL_WRITES and act not in cl._SAVE_WRITES:
            return
        table = self.level if act in cl._LEVEL_WRITES else self.save
        index &= 0xFF
        now = table[index]
        if act in (0x03, 0x04, 0x17):
            new = now + 1
            if act == 0x17:             # also one on save byte [value] (N77)
                self.save[value & 0xFF] = (self.save[value & 0xFF] + 1) & 0xFF
        elif act in (0x05, 0x06):
            new = now - 1
        elif act in (0x07, 0x08):
            new = 0
        elif act in (0x0B, 0x0C):
            new = now | value
        elif act in (0x0D, 0x0E):
            new = now & value
        elif act in (0x12, 0x13):
            new = value
        elif act in (0x0F, 0x10):
            new = 0                     # a random value: 0 here, and not followed
        elif act in (0x14, 0x1B):
            new = self.level[value & 0xFF]
        elif act in (0x15, 0x1C):
            new = self.save[value & 0xFF]
        elif act == 0x16:
            new = now + 1
            self.level[value & 0xFF] = (self.level[value & 0xFF] + 1) & 0xFF
        elif act in (0x24, 0x25):
            new = now + value
        elif act in (0x27, 0x28):
            new = now - value
        else:
            new = live.obj.get("camera_y") or 0
        table[index] = new & 0xFF

    # ---- the gates and the target
    def _live_by_id(self, ident):
        return next((x for x in self.chain if not x.dead and x.obj.get("role") == ident), None)

    def _gates(self, live, rule):
        """(passes, target, drawn): the masks, the frame and end gates, the
        random draws, the target and its distance."""
        effect = rule["effect"]
        if rule["mask"] or rule.get("mask2", 0):
            return False, None
        if effect & cl.FRAME and rule["field24"] != 0:
            return False, None
        if effect & cl.END:
            return False, None
        if effect & (cl.DRAW | cl.DRAW_28):
            self.random_draws += 1
            return False, None
        if effect & (cl.HIT_BY_ID | cl.SIDE_TEST):
            return False, None
        target = None
        if effect & TARGETED:
            if effect & cl.RADIUS_BUGS:
                target = "bugs"
                where = self.bugs
            else:
                target = self._live_by_id(rule["field28"])
                if target is None:
                    return False, None
                where = target.place
            if effect & (cl.RADIUS_BUGS | cl.RADIUS_ID):
                if where is None:
                    return False, None
                d = math.hypot(live.place[0] - where[0], live.place[2] - where[2])
                if effect & 0x1:
                    d = math.dist(live.place, where)
                inside = d <= (rule["field24"] & 0xFFFF)
                if inside == bool(effect & cl.OUTSIDE):
                    return False, None
            if effect & 0x40000000 and rule["field24"] != 0:
                return False, None      # the target's frame: 0 at the first tick
        return True, target

    def _fire(self, live, i, rule, target):
        """The action and the effects of a rule that passed. True when the
        object died."""
        effect = rule["effect"]
        self._act(live, rule)
        if effect & DETACH:             # first of the effects: off its parent (N73 section 2.7)
            live.on_bugs = False
        if effect & cl.SENDS and target not in (None, "bugs"):
            target.state = rule["field24"]
        if effect & cl.CLONES and rule["field28"] > 0:
            n = self.templates.get(rule["field28"])
            if n is not None:
                t = self.lvl["objects"][n]
                clone = _Live(n, t, ("template", rule["field28"]), live.place, live.area,
                              live.route + ((live.key, i),))
                clone.on_bugs = bool(effect & 0x80 and effect & 0x1000)
                self.chain.append(clone)
        elif effect & 0x1000 and not effect & TAKES:
            live.on_bugs = True         # the object itself hangs from Bugs (N76), at his root
            if self.bugs is not None:
                live.place, live.area = self.bugs, self.bugs_area
        if effect & cl.DELETES_ID:
            victim = self._live_by_id(rule["field28"])
            if victim is not None:
                victim.dead = True
        if (effect & cl.DELETES_SELF and rule["field28"] != 1) or effect & DIES_TOO:
            live.dead = True
            return True
        return False

    # ---- the walks
    def _run_type14(self, live):
        obj = live.obj
        steps = {s["key"]: s for s in obj.get("steps", ())}
        state = next((s for s in obj.get("states", ()) if s["number"] == live.state), None)
        if state is None:
            return
        key = next((k for k in state["slots"][:1] if k != cl.END_MARKER), None)
        step = steps.get(key)
        group = step.get("rules") if step else None
        if not group:
            return
        for i, rule in enumerate(obj.get("rules", ())):
            if rule["key"] != group:
                continue
            passes, target = self._gates(live, rule)
            if not passes or not self._condition(live, rule):
                continue
            if self._fire(live, i, rule, target):
                return
            effect = rule["effect"]
            if effect & cl.GO_ON:
                continue
            if not effect & cl.STAYS and not effect & cl.SIDE_TEST:
                live.state = rule["next_state"] or obj["states"][0]["number"]
            return

    def _run_trigger(self, live):
        rules = list(enumerate(live.obj.get("rules", ())))
        pos = 0
        while pos < len(rules):
            i, rule = rules[pos]
            passes, target = self._gates(live, rule)
            if not passes or not self._condition(live, rule):
                label = rule["next_state"]
                if not label:
                    pos += 1
                    continue
                pos = next((p for p in range(pos + 1, len(rules)) if rules[p][1]["key"] == label), len(rules))
                continue
            if self._fire(live, i, rule, target):
                return
            if not rule["effect"] & cl.GO_ON:
                return
            pos += 1

    def _pass(self):
        k = 0
        while k < len(self.chain):
            live = self.chain[k]
            k += 1
            if live.dead:
                continue
            kind = live.obj.get("category")
            if kind == 14 and live.state is not None:
                self._run_type14(live)
            elif kind == 16:
                self._run_trigger(live)
