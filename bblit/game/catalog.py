"""The catalogue of a level's objects for the Animations menu: seven
categories, families inside them and the exemplars of each family, built
from the data.

Every object of the level ends up in exactly one category, the first of
these that fits, each as the engine's code decides it:

1. **characters**, "whoever has a head", before everything else (a
   character whose box changes as it steps aside, or an enemy a touch
   defeats, is still a character): the player, and a type 14 whose rig is a
   skeleton of at least 11 parts, with at least two states or two
   animations (one state and one animation is a statue: scenery). On the
   disc the number of parts has no clean gap (7 parts: 36 models, 8: 70, 9:
   43); below 11, on the levels looked at, there are only things (the golden
   carrot of Wabbit on the run! 1 has 8 parts, the blue chests of Hey...
   What's up, Dock? 1 three), from 11 up the crabs (11), the pirates (24),
   the helpers of Nowhere (28), Merlin (31) and Bugs (38);
2. **collectables**: a touch by Bugs (rule mask 0x8000) deletes it, directly
   or by sending it to a state that ends deleted, or adds to a counter of the
   save (byte 3 carrots, 5 clocks, 7 and 252 golden carrots: finding
   335);
3. **carried**: type 5 (the pushable crate, finding 317), the first static
   flag word's bit 0x800 (Bugs can pick it up, finding 320) or rules waiting
   on being held, let go or put down (masks 0x800, 0x1000, 0x80000);
4. **opening**: its box changes with its state (finding 323,
   `gates.gates_of`): gates, doors, boulders. An invisible thing that opens
   (a gate with no model) stays here; any other thing with neither a model
   nor a sprite goes to the invisible logic;
5. **effects**: type 4 (a looping sprite), 31 (a bullet), 32 (a text), a
   sprite object (the flame, the glow), and a checkpoint (a rule with effect
   0x100000: Bugs's place becomes his restart point);
6. **staged**: a type 14 with more than one state that none of the above
   took (bridges, barrels, what walks without a skeleton), and the platforms
   of types 12 to 29 but 14 and 16 (trampolines, lifts, see-saws, conveyors:
   finding 324);
7. **rest**: what none of these took, in two families of families: scenery
   (anything with a model: type 0, the skies, the one-state type 14 pieces
   such as the rails of the mines) and invisible logic (no model: triggers,
   the camera director, and the texture animators of types 2 and 20, which
   have sprite frames but fill a texture slot and are never drawn as a
   thing).

A **family** is the objects of one category with the same model (or the
same sprite, or, with neither, the same type). **A model number is a
resource number of that level only**: model 229 is Merlin's double in Nowhere
(31 parts) and something else in Mine or mine? 3 (24 parts); the same number
in two levels says nothing about the two things. An **exemplar** is one thing
in the level: a placed object, or one clone, reached through the rule that
makes it (`clone_life`), clones of clones included, three levels deep as the
viewer builds them. Its **provenance** is what the data says about where it
comes from: placed by the file, parked at the origin (placed at (0, 0, 0), or
with no place in the file), cloned by a parent, held at a parent's bone
(effect 0x80), or made by no rule of the level.
"""

from __future__ import annotations

from game import clone_life
from game import gates as gatesmod
from game import montage
from game import startup as startupmod
from game import textures as texmod

CATEGORIES = ("characters", "staged", "carried", "collectables", "effects", "opening", "rest")
SCENERY, LOGIC = "scenery", "logic"

TOUCH = 0x8000
HELD_MASKS = 0x800 | 0x1000 | 0x80000
CAN_BE_PICKED_UP = 0x800            # first static flag word (finding 320)
RESTART_POINT = 0x100000            # rule effect: Bugs's place becomes his restart point
COUNTERS = {3, 5, 7, 252}           # save bytes: carrots, clocks, golden carrots (finding 335)
COUNTER_STEPS = {0x04, 0x17, 0x25}  # actions that add to a save byte
HELD = 0x80                         # a clone held at the parent's attachment marker
TO_BUGS = 0x1000                    # a clone that hangs from Bugs
PLATFORMS = set(range(12, 30)) - {14, 16}
HEAD_PARTS = 11                     # a skeleton of this many parts or more

PLACED, PARKED, CLONED, HELD_AT_BONE, NEVER_MADE = (
    "placed", "parked", "cloned", "held", "never_made")
# what the placed objects at the origin really are (finding 369 for
# Nowhere's twelve): none of them stands at the origin in the game
PAUSE_PAGE, SCRIPT, SKY, ON_BUGS, TEXTURE = "pause_page", "script", "sky", "on_bugs", "texture"
# types 2 and 20 fill a texture slot of the level at every frame (finding
# 275): they have sprite frames but are never drawn as a thing, and no place
TEXTURE_ANIMATORS = (2, 20)
PAUSE_BIT = 0x40000000             # second static flag word: runs while paused (finding 339)
FOLLOWS_CAMERA = 0x20000000        # the same word: carried to the camera (finding 339)


def _steps_of(obj, number):
    steps = {s["key"]: s for s in obj.get("steps", ())}
    state = next((s for s in obj.get("states", ()) if s["number"] == number), None)
    return [steps[k] for k in (state["slots"] if state else ()) if k != 0xFFF0 and k in steps]


def _ends_deleted(obj, rule) -> bool:
    """Whether a rule deletes the object, or sends it to a state that ends
    with it deleted (a step with control bit 4, or a rule of that state
    that deletes it with no mask)."""
    if rule["effect"] & clone_life.DELETES_SELF and rule["field28"] != 1:
        return True
    if not rule["next_state"] or rule["effect"] & clone_life.STAYS:
        return False
    steps = _steps_of(obj, rule["next_state"])
    if any(s.get("control", 0) & 4 for s in steps):
        return True
    groups = {s.get("rules") for s in steps}
    return any(r["key"] in groups and r["effect"] & clone_life.DELETES_SELF and not r["mask"]
               and r["field28"] != 1 for r in obj.get("rules", ()))


def model_of(obj, res):
    return next((x for x in obj.get("resources", ()) if res.get(x, {}).get("data_kind") == "model"
                 and res[x]["size"] > 12), None)


def skeleton_parts(obj, res, sec4) -> int:
    """How many parts the object's rig has (0 without one)."""
    try:
        return len(montage.parts_of(sec4, obj.get("resources", ()), res, obj)) if obj.get("resources") else 0
    except Exception:  # noqa: BLE001
        return 0


def category_of(obj, number, gate_objects, res, sec4):
    """(category, why) of one object: the first rule of the module's
    docstring that fits."""
    kind = obj.get("category")
    flags = obj.get("static_flags") or [0, 0]
    rules = obj.get("rules", ())
    touched = [r for r in rules if r["mask"] & TOUCH]
    if kind == 1:
        return "characters", "the player"
    if kind in TEXTURE_ANIMATORS:
        return "rest", "invisible logic"
    if kind == 14 and obj.get("states"):
        parts = skeleton_parts(obj, res, sec4)
        if parts >= HEAD_PARTS and (len(obj["states"]) >= 2
                                    or len({s["role"] for s in obj.get("steps", ())}) >= 2):
            return "characters", f"a skeleton of {parts} parts"
    if any(_ends_deleted(obj, r) for r in touched):
        return "collectables", "a touch by Bugs takes it away"
    if any(r["action"][0] in COUNTER_STEPS and r["action"][2] in COUNTERS for r in touched):
        return "collectables", "a touch by Bugs adds to a counter"
    if kind == 5:
        return "carried", "the pushable crate (type 5)"
    if flags[0] & CAN_BE_PICKED_UP:
        return "carried", "Bugs can pick it up"
    if any(r["mask"] & HELD_MASKS for r in rules):
        return "carried", "it waits on being held, let go or put down"
    if number in gate_objects:
        return "opening", "its box changes with its state"
    drawn = model_of(obj, res) is not None or texmod.sprite(obj, res, sec4) is not None
    if not drawn and kind != 9:
        return "rest", "invisible logic"
    if kind in (4, 31, 32):
        return "effects", {4: "a looping sprite", 31: "a bullet", 32: "a text"}[kind]
    if texmod.sprite(obj, res, sec4) is not None and model_of(obj, res) is None:
        return "effects", "a sprite"
    if any(r["effect"] & RESTART_POINT for r in rules):
        return "effects", "a checkpoint"
    if kind == 14 and obj.get("states"):
        if len(obj["states"]) >= 2:
            return "staged", "more than one state"
    if kind in PLATFORMS:
        return "staged", f"a platform (type {kind})"
    if model_of(obj, res) is not None or kind == 9:
        return "rest", "scenery"
    return "rest", "invisible logic"


class Catalogue:
    """`families`: {category: [family, ...]}; a family is a dict with
    `category`, `key`, `label` (what the data says it is), `why` (the rule
    that put it in its category), `model`, `objects` (the object numbers
    whose data it uses) and `exemplars`. An exemplar is a dict with `object`
    (the number of the object whose data it is), `provenance` (PLACED,
    PARKED, CLONED, HELD_AT_BONE or NEVER_MADE), `parent` (object number or
    None), `route` (the chain of (key, rule) that makes it, empty for a
    placed object), `kind` (clone_life's answer for the last rule of the
    route, or None for a placed object), `at_start` (alive after the first
    tick of a new game, `game/startup.py`: the recipe of finding 367) and
    `in_level` (it comes by itself, sooner or later, with Bugs doing nothing:
    placed, or every rule of the route LEVEL in `clone_life`)."""

    def __init__(self, lvl, sec4, kinds=None, save=None):
        self.lvl = lvl
        # the first tick of the level, on a new game unless a save is given
        self.startup = startupmod.Startup(lvl, save)
        objects = lvl["objects"]
        res = {r["id"]: r for r in lvl["resources"]}
        self.kinds = kinds if kinds is not None else clone_life.kinds(lvl)
        try:
            gate_objects = {g["number"] for g in gatesmod.gates_of(lvl)}
        except Exception:  # noqa: BLE001
            gate_objects = set()
        self.templates = {}
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08 and o["role"] not in self.templates:
                self.templates[o["role"]] = n
        self.category = {}
        for n, o in enumerate(objects):
            self.category[n] = category_of(o, n, gate_objects, res, sec4)
        exemplars = []
        made = set()
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08:
                continue
            provenance = self._provenance(n, o, res)
            exemplars.append({"object": n, "provenance": provenance, "parent": None, "route": (),
                              "kind": None, "at_start": n in self.startup.alive, "in_level": True})
            self._clones(n, ("placed", n), (), True, exemplars, made, 1)
        # a template no rule makes; a second template with a role already
        # taken is one too: the game clones the first (finding 68)
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08 and n not in made:
                exemplars.append({"object": n, "provenance": NEVER_MADE, "parent": None,
                                  "route": (), "kind": None, "at_start": False, "in_level": False})
        families = {}
        for e in exemplars:
            n = e["object"]
            o = objects[n]
            cat, why = self.category[n]
            mid = model_of(o, res)
            spr = texmod.sprite(o, res, sec4) if mid is None else None
            if cat == "rest":
                sub = SCENERY if why == "scenery" else LOGIC
                key = (cat, sub, mid if mid is not None else ("type", o.get("category")))
            elif mid is not None:
                key = (cat, "model", mid)
            elif spr is not None:
                key = (cat, "sprite", spr["frames"][0])
            else:
                key = (cat, "type", o.get("category"))
            fam = families.get(key)
            if fam is None:
                fam = families[key] = {"category": cat, "key": key, "why": why, "model": mid,
                                       "objects": [], "exemplars": []}
            if n not in fam["objects"]:
                fam["objects"].append(n)
            fam["exemplars"].append(e)
        self.families = {c: [] for c in CATEGORIES}
        for fam in families.values():
            self.families[fam["category"]].append(fam)
        for c in CATEGORIES:
            self.families[c].sort(key=lambda f: (-len(f["exemplars"]), f["objects"][0]))

    def _provenance(self, n, o, res):
        """What the data says about where a placed object is (finding 369): on Bugs
        from the first tick, a sky at the camera, a page of the pause menu,
        and at the origin a script without a model; else placed by the file,
        or parked at the origin when nothing of these explains it."""
        flags = o.get("static_flags") or [0, 0]
        place = o.get("position")
        at_origin = not place or tuple(place) == (0, 0, 0)
        if o.get("category") in TEXTURE_ANIMATORS:
            return TEXTURE
        if n in self.startup.on_bugs:
            return ON_BUGS
        if o.get("category") == 9 or (o.get("category") == 14 and flags[1] & FOLLOWS_CAMERA):
            return SKY
        if at_origin and model_of(o, res) is None and o.get("category") in (16, 36):
            return SCRIPT
        if flags[1] & PAUSE_BIT:
            return PAUSE_PAGE
        return PARKED if at_origin else PLACED

    def _clones(self, n_parent, key, route, parent_in_level, out, made, depth):
        """The clones an object makes, and theirs, as the viewer builds them
        (three levels deep); `key` is clone_life's key of the parent."""
        objects = self.lvl["objects"]
        for i, rule in enumerate(objects[n_parent].get("rules", ())):
            if not rule["effect"] & clone_life.CLONES or rule["field28"] <= 0:
                continue
            n = self.templates.get(rule["field28"])
            if n is None:
                continue
            kind = self.kinds.get(key + (i,), clone_life.EVENT)
            held = rule["effect"] & (HELD | TO_BUGS)
            step = route + ((key, i),)
            in_level = parent_in_level and kind == clone_life.LEVEL
            out.append({"object": n, "provenance": HELD_AT_BONE if held else CLONED,
                        "parent": n_parent, "route": step, "kind": kind,
                        "at_start": step in self.startup.born, "in_level": in_level})
            made.add(n)
            if depth < 3 and n != n_parent:
                self._clones(n, ("template", rule["field28"]), step, in_level, out, made, depth + 1)

    def counts(self):
        """{category: number of exemplars}."""
        return {c: sum(len(f["exemplars"]) for f in fams) for c, fams in self.families.items()}


def in_words(exemplars) -> str:
    """How many, and when: "17: 10 at the start, 7 come when Bugs does
    something" or "292: 31 at the start, 78 come by themselves later, 183 come
    when Bugs does something" (numbers()). "At the start" is after the first
    tick of a new game."""
    total, at_start, by_itself, by_bugs, never = numbers(exemplars)
    text = f"{total}: {at_start} at the start"
    if by_itself:
        text += f", {by_itself} come by themselves later"
    if by_bugs:
        text += f", {by_bugs} come when Bugs does something"
    if never:
        text += f", {never} made by no rule"
    return text


def numbers(exemplars) -> tuple[int, int, int, int, int]:
    """(total, there at the start (after the first tick of a new game), coming
    later by themselves (clone_life's LEVEL), coming later when Bugs does
    something or for a moment, made by no rule)."""
    total = len(exemplars)
    at_start = sum(1 for e in exemplars if e["at_start"])
    never = sum(1 for e in exemplars if e["provenance"] == NEVER_MADE)
    by_itself = sum(1 for e in exemplars if not e["at_start"] and e["in_level"]
                    and e["provenance"] != NEVER_MADE)
    return total, at_start, by_itself, total - at_start - by_itself - never, never


# the conditions on a byte, for "when the level byte changes"
_LEVEL_BYTE_TESTS = set(clone_life._LEVEL_TESTS) | {0x0F, 0x3D, 0x3F, 0x41, 0x43}
_SAVE_BYTE_TESTS = set(clone_life._SAVE_TESTS) | {0x10, 0x3E, 0x40}
_BUTTONS = {0x39, 0x45, 0x4F, 0x5A, 0x5B, 0x5E}
# the steps of a chain that are something Bugs does (catalog._Reasons._explain)
_BUGS_DOES = {"touch", "button", "near", "zone"}


class _Reasons:
    """Why an exemplar is not there when the level has just loaded, as a code
    and its numbers, for the menu to put in words."""

    def __init__(self, cat):
        self.cat = cat
        self._writers = None

    def writers(self, table, index):
        if self._writers is None:
            try:
                self._writers = gatesmod.writers(self.cat.lvl)
            except Exception:  # noqa: BLE001
                self._writers = {}
        return sorted({n for n, _code, _value in self._writers.get((table, index), ())})

    def of(self, e):
        if e["at_start"]:
            return None
        if e["provenance"] == NEVER_MADE:
            return ("never_made", {})
        if not e["route"]:
            return ("gone_first_tick", {})     # placed, and deleted by its first tick
        objects = self.cat.lvl["objects"]
        # the first rule of the chain that does not fire by itself
        for key, i in e["route"]:
            n = key[1] if key[0] == "placed" else self.cat.templates.get(key[1])
            rule = objects[n]["rules"][i]
            kind = self.cat.kinds.get(key + (i,), clone_life.EVENT)
            if kind == clone_life.LEVEL:
                continue
            if kind == clone_life.PASSING:
                return ("passing", {"parent": n})
            if objects[n].get("category") == 16:
                chain = self._trigger_chain(n, i)
                if chain:
                    return ("chain", {"parent": n, "steps": chain})
            return self._event(n, rule)
        return ("by_itself", {})

    # ---- how far back the reason goes (finding 368: the helpers of
    # Nowhere come from Merlin's sign, through a zone and three bytes)

    def _writers_index(self):
        """{(table, byte): [(source, rule)]}: every rule that sets a byte,
        of an object ("object", n) or of a zone ("zone", k)."""
        if getattr(self, "_windex", None) is None:
            index = {}
            for n, o in enumerate(self.cat.lvl["objects"]):
                for rule in o.get("rules", ()):
                    for key in _sets(rule["action"]):
                        index.setdefault(key, []).append((("object", n), rule))
            for k, z in enumerate(self.cat.lvl.get("zones", ())):
                for rule in z.get("rules", ()):
                    for key in _sets(rule.get("action") or ()):
                        index.setdefault(key, []).append((("zone", k), rule))
            self._windex = index
        return self._windex

    def _trigger_chain(self, n, i):
        """Why a trigger's clone rule does not fire at the first tick: the
        first rule before it that stops the walk and holds at the start (the
        helpers' "Bugs is not in the trial's zone"), or the rule's own
        condition; then who sets that byte, back to what Bugs does."""
        rules = self.cat.lvl["objects"][n].get("rules", ())
        start = self.cat.startup
        blocker = rules[i]
        for rule in rules[:i]:
            stops = not rule["effect"] & (clone_life.GO_ON | clone_life.CLONES)
            if stops and rule["condition"][0] and _holds_at_start(start, rule):
                blocker = rule
                break
        return self._explain(blocker["condition"], 0, set())

    def _explain(self, condition, depth, seen):
        """[(what, numbers), ...] from what Bugs does to the condition. When
        no chain reaches Bugs within five bytes, the first object or zone that
        can make the condition true, as far as the data goes."""
        op, a, b = condition
        if depth > 4 or not op:
            return []
        if op in _LEVEL_BYTE_TESTS:
            key = ("level", b)
        elif op in _SAVE_BYTE_TESTS:
            key = ("save", b)
        else:
            return []
        if key in seen:
            return []
        seen = seen | {key}
        fallback = []
        for source, rule in self._writers_index().get(key, ()):
            act = rule["action"][0] if rule.get("action") else 0
            written = rule["action"][1] if len(rule["action"]) > 1 else 0
            if act in (0x14, 0x15, 0x1B, 0x1C):          # a copy: follow the byte copied
                value = rule["action"][3] if len(rule["action"]) > 3 else rule["action"][1]
                copied = (0x1E, 0xFF, value & 0xFF) if act in (0x14, 0x1B) else (0x1F, 0xFF, value & 0xFF)
                chain = self._explain(copied, depth + 1, seen)
                if chain and chain[0][0] in _BUGS_DOES:
                    return chain
                fallback = fallback or chain
                continue
            if not gatesmod._fits(op, a, act, written):
                continue          # this write cannot make the condition true (another bit)
            kind, number = source
            if kind == "zone":
                chain = self._explain(tuple(rule["condition"]), depth + 1, seen) + [("zone", {"zone": number})]
            elif rule.get("mask", 0) & TOUCH:
                return [("touch", {"parent": number})]
            elif rule["condition"][0] in _BUTTONS | {0x31}:
                return [("button", {"parent": number})]
            elif rule["effect"] & clone_life.RADIUS_BUGS:
                return [("near", {"parent": number, "metres": (rule["field24"] & 0xFFFF) / 128.0})]
            else:
                chain = self._explain(tuple(rule["condition"]), depth + 1, seen) + [("object", {"parent": number})]
            if chain and chain[0][0] in _BUGS_DOES:
                return chain
            fallback = fallback or chain
        return fallback


    def _event(self, n, rule):
        effect, (op, a, b) = rule["effect"], rule["condition"]
        if rule["mask"] & TOUCH:
            return ("touch", {"parent": n})
        if rule["mask"] & HELD_MASKS:
            return ("held", {"parent": n})
        if rule["mask"] or rule.get("mask2", 0):
            return ("state_of", {"parent": n})
        if effect & clone_life.HIT_BY_ID:
            return ("hit", {"parent": n})
        if effect & clone_life.RADIUS_BUGS:
            metres = (rule["field24"] & 0xFFFF) / 128.0
            key = "far" if effect & clone_life.OUTSIDE else "near"
            return (key, {"parent": n, "metres": metres})
        if op in _BUTTONS:
            return ("button", {"parent": n})
        if op in _LEVEL_BYTE_TESTS or op in _SAVE_BYTE_TESTS:
            table = "level" if op in _LEVEL_BYTE_TESTS else "save"
            return ("byte", {"parent": n, "table": table, "index": b,
                             "writers": self.writers(table, b)})
        return ("other", {"parent": n})


def _sets(action):
    """The bytes an action sets (not those it clears): [(table, byte)]."""
    if not action:
        return []
    act, index = action[0], action[2]
    if act in clone_life._LEVEL_WRITES:
        return [("level", index & 0xFF)]
    if act in clone_life._SAVE_WRITES:
        return [("save", index & 0xFF)]
    return []


def _holds_at_start(start, rule) -> bool:
    """A rule's condition on the tables after the first tick."""
    return start._condition(start.chain[0] if start.chain else None, rule)


def why_not(cat, e):
    """(code, numbers) of why exemplar `e` is not there when the level has
    just loaded, or None when it is. Codes: never_made, passing, touch, held,
    state_of, hit, near, far, button, byte, other, by_itself (it comes
    by itself, after the first tick), gone_first_tick (placed, and deleted by
    its first tick: a golden carrot already taken, a variant of another save)."""
    reasons = getattr(cat, "_reasons", None)
    if reasons is None:
        reasons = cat._reasons = _Reasons(cat)
    return reasons.of(e)


def place_of(cat, e):
    """Where exemplar `e` is, in game units: its own place, or that of the
    placed object its chain of clones starts from; None when it has none
    (parked at the origin, made by no rule)."""
    objects = cat.lvl["objects"]
    if e["route"]:
        key = e["route"][0][0]
        n = key[1] if key[0] == "placed" else None
    else:
        n = e["object"]
    if n is None:
        return None
    place = objects[n].get("position")
    if not place or tuple(place) == (0, 0, 0):
        return None
    return tuple(place)


def menu_families(cat, category):
    """The families the menu shows for a category: those of the catalogue,
    and for The rest two, Scenery and Invisible logic,
    each holding every exemplar of its kind. [(key, exemplars, family or
    None)]."""
    fams = cat.families[category]
    if category != "rest":
        return [(f["key"], f["exemplars"], f) for f in fams]
    out = []
    for sub in (SCENERY, LOGIC):
        ex = [e for f in fams if f["key"][1] == sub for e in f["exemplars"]]
        if ex:
            out.append((("rest", sub), ex, None))
    return out


def one_at_a_time(cat):
    """The sets of clones of which the game keeps one alive at a time, read
    from the level's script as finding 368 reads Nowhere's helpers: a
    type 16 trigger with a "stop" rule on a bit of a level byte (condition
    0x1E, no 0x8000), a rule that sets that bit and goes on (action 0x0B,
    0x8000), and two or more clone rules that end the walk (no 0x8000): it
    arms the bit and clones the first whose own condition holds, and the
    clone clears the bit when it goes. [set of routes, ...]."""
    out = []
    for n, o in enumerate(cat.lvl["objects"]):
        if o["block_type"] == 0x08 or o.get("category") != 16:
            continue
        rules = o.get("rules", ())
        stops = {(r["condition"][2], r["condition"][1]) for r in rules
                 if r["condition"][0] == 0x1E and not r["effect"] & clone_life.GO_ON
                 and not r["effect"] & clone_life.CLONES}
        arms = {(r["action"][2] & 0xFF, r["action"][1]) for r in rules
                if r["action"][0] == 0x0B and r["effect"] & clone_life.GO_ON}
        if not stops & arms:
            continue
        clones = frozenset(((("placed", n), i),) for i, r in enumerate(rules)
                           if r["effect"] & clone_life.CLONES and r["field28"] > 0
                           and not r["effect"] & clone_life.GO_ON)
        if len(clones) >= 2:
            out.append(clones)
    return out


def exemplar_id(e):
    """How the scene and the menu name an exemplar: ("placed", n) for a placed
    object, the route of rules for a clone, None for one no rule makes."""
    if e["route"]:
        return e["route"]
    if e["provenance"] == NEVER_MADE:
        return None
    return ("placed", e["object"])
