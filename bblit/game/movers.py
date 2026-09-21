"""The characters the game moves by itself (finding 317).

A type 14 object moves because of the step it is in: the control dword of the
step (opcode `0x30`, payload +12) says whether it goes forward, what it aims
at and how it turns, and a rule of the step's rule group moves it to another
state when it gets within a radius of its target. The waypoints of a patrol
are empty triggers carrying an id.

What is run here, once per logic tick (30 a second, finding 316):

1. the step of the current state (state 2 if the object has it, else 1);
2. turning towards the target, with the step's own way of turning;
3. forward `w20` units along the heading, the Y taken from the collision
   ground as the game does, stopped by the wall sweep;
4. a rule "within N of id M" of the step's group moves it to the next state;
   a playlist that runs out goes back to state 1.

**Bugs is not in the scene**, so an object whose target is Bugs stands still
(a choice): in the game that case never happens. Left out on purpose,
and said in the viewer's menu: bumping into other objects, wandering (the game
draws it at random), and the up-to-nine headings tried in front of a wall —
a mover that the sweep stops simply stops.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import collision  # noqa: E402
from game import hazards  # noqa: E402

TURN = 4096                  # a whole turn, in the game's units
TICKS_PER_SECOND = 30        # the game's logic clock (finding 316)
MAX_FALL = 70                # units a tick, from the first tick (finding 318)

# the bits of the step's control dword
GOES_FORWARD = 0x2
TARGET_ID = 0x200000         # the live object whose id is w22
TARGET_BUGS = 0x9000         # 0x8000 or 0x1000: Bugs
AWAY = 0x10000000
AT_ONCE = 0x1000
WANDERS = 0x2000000
FREE_3D = 0x80000000         # no ground under it
SIDEWAYS = 0x10000           # of w16: forward along local X
TURN_AT_MOST = 0x400         # of w16: at most the word of opcode 0x1D a tick
TURN_HALF = 0x20             # of w16: half the error
# the bits of a rule that ends a step
ARRIVAL = 0x18000000         # 0x10000000 an id, 0x08000000 Bugs
ARRIVAL_BUGS = 0x08000000
ARRIVAL_OUTSIDE = 0x200000   # outside the radius, not within
NOT_ARRIVAL = 0x8000


def _steps_by_key(obj):
    return {st["key"]: st for st in obj.get("steps", ()) if "control" in st}


def _reachable_states(obj, by_key):
    """The states the object can get to without Bugs: from the one it starts
    in, following the arrival rules that name an id (finding 317)."""
    start = hazards.start_state(obj) or 1
    seen, queue = {start}, [start]
    slots = {s["number"]: [k for k in s["slots"] if k != hazards.END_MARKER]
             for s in obj.get("states", ())}
    while queue:
        number = queue.pop()
        for key in slots.get(number, ()):
            step = by_key.get(key)
            group = step.get("rules") if step else None
            if not group:
                continue
            found = False
            for rule in obj.get("rules", ()):
                if rule["key"] != group:
                    if found:
                        break
                    continue
                found = True
                effect = rule["effect"]
                if (effect & ARRIVAL and not effect & (NOT_ARRIVAL | ARRIVAL_BUGS)
                        and rule["next_state"] and rule["next_state"] not in seen):
                    seen.add(rule["next_state"])
                    queue.append(rule["next_state"])
        # a playlist that runs out goes back to state 1 (finding 321)
        if 1 not in seen:
            seen.add(1)
            queue.append(1)
    return seen


def _moves(step) -> bool:
    """Does this step move the object across the floor? (Bobbing, hopping and
    the arc of something thrown are not here: they are A2 and A3.)"""
    return bool(step["control"] & GOES_FORWARD or step["w16"] & SIDEWAYS)


class Mover:
    """One object the viewer moves, and where it is at the tick it has run to.

    `pos` is in game units and `heading` in 4096ths of a turn, both floats;
    `still` says the object stands where it was placed (its target is Bugs, or
    its step does not move it), and then the viewer leaves it alone.
    """

    __slots__ = ("index", "obj", "start_pos", "start_heading", "pos", "heading", "state",
                 "slot", "still", "turn_rate", "_by_key", "_targets", "_blocks")

    def __init__(self, index, obj, targets, blocks, turn_rate):
        self.index, self.obj = index, obj
        self._by_key, self._targets, self._blocks = _steps_by_key(obj), targets, blocks
        self.turn_rate = turn_rate
        self.start_pos = tuple(float(v) for v in obj["position"])
        self.start_heading = float((obj["rotation"] or (0, 0, 0))[1])
        self.reset()

    def reset(self):
        self.pos = self.start_pos
        self.heading = self.start_heading
        self.state = hazards.start_state(self.obj) or 1
        self.slot = 0
        self.still = False

    # ------------------------------------------------------------------ state

    def _slots(self, number):
        for s in self.obj.get("states", ()):
            if s["number"] == number:
                return [k for k in s["slots"] if k != hazards.END_MARKER]
        return []

    def step(self):
        """The step the object is playing now, or None."""
        keys = self._slots(self.state)
        if self.slot >= len(keys):
            return None
        return self._by_key.get(keys[self.slot])

    def go_to(self, state):
        self.state, self.slot = state, 0

    # ------------------------------------------------------------------- tick

    def _target_point(self, step):
        """Where the step aims, or None when it aims at Bugs (not in the
        scene) or at nothing."""
        if step["control"] & TARGET_ID:
            return self._targets.get(step["w22"])
        return None

    def _turn_towards(self, step, point):
        """Turns the heading towards `point`, the way the step says."""
        dx, dz = point[0] - self.pos[0], point[2] - self.pos[2]
        if dx == 0 and dz == 0:
            return
        # the game's heading: 0 along +Z, growing towards +X (the viewer's
        # rotation matrix turns the model the same way)
        wanted = math.atan2(dx, dz) * TURN / (2 * math.pi)
        if step["control"] & AWAY:
            wanted += TURN / 2
        error = (wanted - self.heading + TURN / 2) % TURN - TURN / 2
        if step["control"] & AT_ONCE:
            self.heading = wanted % TURN
            return
        if step["w16"] & TURN_AT_MOST:
            rate = self.turn_rate or 0
            error = max(-rate, min(rate, error))
        elif step["w16"] & TURN_HALF:
            error /= 2.0
        else:
            error = error / float(1 << (self.turn_rate or 4))
        self.heading = (self.heading + error) % TURN

    def _arrival_rules(self, step):
        """The rules of the step's group that end it by distance (finding 317):
        (radius, outside, target point, next state)."""
        group = step.get("rules")
        out, seen = [], False
        if not group:
            return out
        for rule in self.obj.get("rules", ()):
            if rule["key"] != group:
                if seen:
                    break
                continue
            seen = True
            effect = rule["effect"]
            if not (effect & ARRIVAL) or effect & NOT_ARRIVAL or not rule["next_state"]:
                continue
            if effect & ARRIVAL_BUGS:
                continue                      # Bugs is not in the scene
            point = self._targets.get(rule["field28"])
            if point is not None:
                out.append((abs(rule["field24"]), bool(effect & ARRIVAL_OUTSIDE),
                            point, rule["next_state"]))
        return out

    def tick(self):
        """One logic tick."""
        step = self.step()
        if step is None:                      # the playlist ran out
            self.go_to(1)
            step = self.step()
        if step is None or not _moves(step):
            self.still = True
            return
        if step["control"] & TARGET_BUGS and not step["control"] & TARGET_ID:
            self.still = True                 # it wants Bugs, who is not here
            return
        self.still = False
        point = self._target_point(step)
        if point is not None and not step["control"] & WANDERS:
            self._turn_towards(step, point)
        speed = float(step["w20"])
        angle = self.heading * 2 * math.pi / TURN
        if step["w16"] & SIDEWAYS:
            angle += math.pi / 2
        x = self.pos[0] + speed * math.sin(angle)
        z = self.pos[2] + speed * math.cos(angle)
        y = self.pos[1]
        if not step["control"] & FREE_3D and self._blocks:
            if collision.sweep_stops(self._blocks, (int(self.pos[0]), int(self.pos[2])),
                                     (int(x), int(z)), int(y)):
                x, z = self.pos[0], self.pos[2]
            found = collision.ground_below(self._blocks, int(x), int(y), int(z))
            if found is not None:
                ground = float(found[0])
                # Y grows downwards: falling is going up in numbers, at most
                # MAX_FALL a tick from the first one (finding 318)
                y = min(ground, y + MAX_FALL) if ground > y else ground
        self.pos = (x, y, z)
        for radius, outside, point, next_state in self._arrival_rules(step):
            near = math.hypot(point[0] - self.pos[0], point[2] - self.pos[2]) <= radius
            if near != outside:
                self.go_to(next_state)
                break


class Simulation:
    """Every mover of a level, run to a given tick.

    The viewer asks for a tick and gets the positions: going forward costs the
    ticks in between, going back starts again from the placement, so a paused
    or rewound viewer is exact too.
    """

    def __init__(self, lvl, collision_blocks):
        targets = {}
        for o in lvl["objects"]:
            if o["block_type"] != 0x08 and o["position"] and o.get("role"):
                targets.setdefault(o["role"], tuple(float(v) for v in o["position"]))
        self.movers = []
        for index, o in enumerate(lvl["objects"]):
            if o["block_type"] == 0x08 or not o["position"] or o.get("category") != 14:
                continue
            by_key = _steps_by_key(o)
            slots = {s["number"]: [k for k in s["slots"] if k != hazards.END_MARKER]
                     for s in o.get("states", ())}
            # only the objects that move in a state they can actually get to
            # without Bugs: the still crabs have a moving step too (state 236,
            # when they are thrown), which they never reach here
            if not any(_moves(by_key[k])
                       for number in _reachable_states(o, by_key)
                       for k in slots.get(number, ()) if k in by_key):
                continue
            self.movers.append(Mover(index, o, targets, collision_blocks, o.get("turn_rate") or 0))
        self.by_index = {m.index: m for m in self.movers}
        self.at = 0

    def run_to(self, tick: int):
        """Runs every mover to `tick` logic ticks from the start."""
        tick = max(0, int(tick))
        if tick < self.at:
            for m in self.movers:
                m.reset()
            self.at = 0
        while self.at < tick:
            for m in self.movers:
                m.tick()
            self.at += 1
