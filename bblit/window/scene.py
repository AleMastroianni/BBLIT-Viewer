"""A level built in memory: its pieces, its groups of triangles and the
templates the rules clone.

There is no intermediate format: the `.bze` sections are decompressed (an
on-disk cache: decompressing in Python takes seconds), the load script is
read and the geometry built here. What the flags draw over it is in
`overlays.py`.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from array import array  # noqa: E402

from game import clone_life  # noqa: E402
from game import collision  # noqa: E402
from game import gates as gatesmod  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import montage  # noqa: E402
from game import movers as moversmod  # noqa: E402
from support import paths  # noqa: E402
from support import preferences  # noqa: E402
from game import rig as rigmod  # noqa: E402
from game import textures as texmod  # noqa: E402
from game import tim  # noqa: E402
from game import zones  # noqa: E402
from window.overlays import FAMILIES, OverlayBuilder  # noqa: E402

# Animation ticks per second (textures 275, models 278): MEASURED.
# Measured in BizHawk (PSX NTSC-U) with frame advance: the normal carrot does
# a turn in 68, 68, 67 frames (203 in 3 turns). Its animation has 17
# blocks, the last an end-of-turn placeholder that repeats the second-to-last, and
# the PSX shows them all: 17 ticks every 67.7 frames at 60 Hz = 15.07 ticks per
# second, one block every exactly 4 frames. The PC does not show the placeholder
# (no carrot pause), and the viewer drops it (rig.animation).
# Keys - and + or --tps to change it.
TICKS_PER_SECOND = 15.0

# Object rule passes per animation tick. The type 14 handler walks the step's
# rules on every logic tick (Ombelll's finding 188), and the logic runs at 30 per
# second against the 15 animation blocks (finding 278). NOT measured:
# the rotation speed of the anchors will tell (280).
RULE_PASSES_PER_TICK = 2

# Bit of the second static flag word (object+0xc) that puts a TYPE 14 object
# wherever the camera is, at every tick. Together with type 9, which is
# always placed that way, this is how the game draws the sky and the sea:
# read in its code by the reverse (note N39 of BBLIT_Decomp_ALE), 97 such
# objects on the disc (docs/lists/placement.md there).
FOLLOWS_CAMERA = 0x20000000
# a rule effect: the object takes the object whose id is field +28 as its
# child (finding 330: the vehicles that carry Bugs); Bugs is object id 1
TAKES_CHILD, BUGS_ID = 0x20000000, 1


def carried_by_camera(obj) -> bool:
    """The game's own test for an object it puts wherever the camera is, at
    every tick (the reverse's note N39): type 9, or type 14 with bit
    0x20000000 in the second dword of opcode 0x16. That is the sky and the
    sea, and a few small things that ride along with the camera. Its place
    in the file is overwritten on the first tick and means nothing; only
    the height of opcode 0x1E stays (`obj["camera_y"]`)."""
    if obj.get("category") == 9:
        return True
    flags = obj.get("static_flags") or [0, 0]
    return obj.get("category") == 14 and bool(flags[1] & FOLLOWS_CAMERA)


def camera_place(obj) -> tuple:
    """Where an object carried by the camera is built: around the origin,
    raised by the word of opcode 0x1E. The drawing then moves it with the
    camera (Drawing.on_draw, the sky_dome pass)."""
    return (0, obj.get("camera_y") or 0, 0)

def sections(bze_path: str, cache: str) -> dict[int, bytes]:
    """Decompresses sections 1, 3 and 4, with an on-disk cache that follows
    the `.bze` (textures.sections)."""
    return texmod.sections(bze_path, cache, ids=(1, 3, 4))


class FaceGroup:
    """A group of triangles sharing texture and blending."""

    __slots__ = ("tex_id", "data", "vao", "vbo", "item_count", "category", "blend", "frames", "vaos",
                 "spin", "sorted", "area", "face_tris", "mover", "two_sided")

    def __init__(self, tex_id, category, blend=None, n_frames=0, spin=None, area=None, mover=None,
                 two_sided=False):
        self.tex_id = tex_id
        self.blend = blend            # None = opaque, otherwise 0..3
        self.category = category          # "terrain", "props", "sky_dome", a clone group or an overlay
        # 8 floats per vertex (position, color, uv), in a compact array
        self.data = array("f")
        # how many triangles each face of `data` became, in order: the sorted
        # list is ordered one face at a time, as the PC does (finding 306)
        self.face_tris = []
        self.vao = self.vbo = None
        self.item_count = 0
        # animated objects (finding 278): a list of triangles per frame
        self.frames = [array("f") for _ in range(n_frames)]
        # after upload, for an animated object: (vao, vbo, first vertex,
        # vertex count) per frame, all in the same buffer
        self.vaos = []
        # rotating objects (action 0x26, finding 280): (pivot, units per
        # rule pass), with 4096 = one turn around the vertical axis
        self.spin = spin
        # semi-transparent and still: drawn from BlendSorter, back to front
        self.sorted = False
        # with "Visibility by area": the area this group belongs to, or None
        # for what the game always draws (finding 295)
        self.area = area
        # "Moving characters" (finding 317): the index of the object this
        # group belongs to. Its triangles are built around the object's own
        # origin and placed by the simulation when drawing (game/movers.py)
        self.mover = mover
        # the faces the game draws from both sides (bit 0x02 of their flag,
        # finding 307) are in groups of their own: with Video options ->
        # Backface culling the other groups are culled as the game culls them
        self.two_sided = two_sided


def _condition_at_startup(cond) -> bool:
    op, val, _index = cond
    if op == 0x00:
        return True                 # no condition
    if op in (0x01, 0x02):
        return val == 0          # equal, on a zeroed table
    if op == 0x25:
        return val != 0          # not equal
    if op in (0x27, 0x28):
        return True                 # bit clear: at zero it is
    return False                    # bit set, time, buttons, other: not at startup


def _at_startup(rule) -> bool:
    """A clone that appears immediately: condition true on empty tables and no
    distance target (0x08000000 player, 0x10000000 role)."""
    return (_condition_at_startup(rule["condition"])
            and not rule["effect"] & 0x18000000)


def _spin_speed(obj) -> int:
    """How much an object turns on each rule pass (finding 280).

    Action 0x26 adds `value * 16 + index` (two s16) to the object's Y rotation
    (`obj+0xDE`, read in the handler at 0x0042D070 of this build).
    The type 14 handler walks the current step's rules on every tick and
    stops at the first true one without effect 0x8000 (Ombelll's finding 188): here
    the starting step is walked with the conditions evaluated at startup.

    A step that ends when the object gets near a role (effect
    0x10000000 without 0x8000: the pirate that goes from one waypoint to the
    next and turns at each stop) is a path segment, which the viewer
    does not simulate: no continuous rotation. The anchor looks for a role too
    (an enemy below, 0x10008000), but without leaving the step.
    """
    lookup_key = montage.start_key(obj)
    rules = [r for r in obj.get("rules", []) if r["key"] == lookup_key]
    if lookup_key is None or any(r["effect"] & 0x10000000 and not r["effect"] & 0x8000
                              for r in rules):
        return 0
    step = 0
    for r in rules:
        if not _at_startup(r):
            continue
        rule_action = r["action"]
        if rule_action[0] == 0x26:
            index = rule_action[2] - 0x10000 if rule_action[2] & 0x8000 else rule_action[2]
            step += rule_action[3] * 16 + index
        if not r["effect"] & 0x8000:
            break
    return step


class Level(OverlayBuilder):
    def __init__(self, bze_path: str, cache: str, table=None, session_poses=None, pieces=None,
                 families=tuple(FAMILIES), split_areas=False, movers=False,
                 gate_state="open", gate_choices=None, gate_links="off", sky_choice=None):
        self.families = frozenset(families)
        # "Visibility by area as in the game": the terrain pieces and the
        # objects cut by area go into groups of their own, one per area, so
        # the viewer can leave out the areas the game would not draw (293,
        # 294, 295). Off: exactly the groups of before
        self.split_areas = split_areas
        # "Moving characters" (finding 317): the objects the game moves are
        # built around their own origin and placed by this simulation when
        # drawing; off, everything is exactly as before, byte for byte
        self.move_characters = movers
        self.mover_sim = None
        # Gates (finding 323): which state every gate is shown in. "open" is
        # the default, by the rule about defaults: a gate that opens
        # only moves geometry, and the level is worth seeing the way it is once
        # you have been through it. "shut" and "game" (the state the game
        # starts it in) are the other choices, and `gate_choices` overrides the
        # general one for the gates of one switch (menu: Gates of #78).
        self.gate_state = gate_state
        self.gate_choices = dict(gate_choices or {})
        # "Who opens what": "off", "gates" (only what really opens something)
        # or "all" (every object that waits on a byte somebody writes, with
        # REACTS in its name). What is in the data is not dropped, it is
        # marked and can be turned off
        self.gate_links = gate_links
        self.gates = {}
        self.gate_groups = {}
        self.name = os.path.splitext(os.path.basename(bze_path))[0]
        # where the file came from: the ENTRANCE names read the level changes
        # of the other files in the same folder (game/entrances.py)
        self.bze_folder, self.cache_folder = os.path.dirname(bze_path), cache
        self.table = table
        sec = sections(bze_path, cache)
        blocks, _stat = loadscript.parse(sec[1])
        self.lvl = loadscript.export_level(blocks)
        self.sec3, self.sec4 = sec[3], sec[4]
        # the table: registered slots plus animated slots (finding 275)
        if self.table is None:
            self.sizes = tim.sizes(self.sec3, self.lvl["textures"])
            # the textures with a transparent entry: their faces are drawn
            # with the semi-transparent ones, not with the opaque ones
            # (finding 306, tim.cut_outs)
            self.cut_outs = tim.cut_outs(self.sec3, self.lvl["textures"])
        else:
            self.sizes = {}
            self.cut_outs = set()
            for tid, (block, offset) in self.table.slots.items():
                one = [{"id": tid, "offset": offset}]
                self.sizes.update(tim.sizes(block, one))
                self.cut_outs |= tim.cut_outs(block, one)
        self.res = {r["id"]: r for r in self.lvl["resources"]}
        try:
            self.collision_blocks = collision.read_level_blocks(self.sec4, self.lvl)
        except Exception:  # noqa: BLE001
            self.collision_blocks = []     # without a heightmap no face is judged
        # the objects the game keeps on the ground, at their ground and not
        # at the height of the file (finding 340), before anything reads
        # where they are: their boxes, names and clones go with them
        self.settled = collision.settle_objects(self.lvl, self.collision_blocks)
        # zones that kill, hurt or teleport: a fall into one is not a safe fall
        self.trap_zones = [s for z in self.lvl["zones"] if (s := zones.trap_shape(z))]
        self.face_groups: dict[tuple, FaceGroup] = {}
        self.stat = {"terrain": 0, "props": 0, "sky_dome": 0, "triangles": 0, "untextured": 0,
                     "from_game": 0, "fallback": 0, "clones": 0, "clones_in_level": 0,
                     "clones_without_model": 0}
        self.lo = [1e9, 1e9, 1e9]
        self.hi = [-1e9, -1e9, -1e9]
        self.sprites: list[dict] = []
        # the names floating above the collision boxes (flag Collision boxes):
        # {"pos", "text"}, drawn by window/drawing.py facing the camera
        self.box_labels: list[dict] = []
        # a held child's name moves with its bone: {(template, parent): entry}
        self._label_frames: dict = {}
        # the chosen level state (bridges, barrels, torches: preferences.py);
        # `session_poses` holds those changed from the menu, session only
        self.pref = preferences.for_level(self.name)
        self.pref["pose"] = {**self.pref["pose"], **(session_poses or {})}
        self._pieces = pieces if pieces is not None else {}
        self._current_piece = None       # the piece being built (see _piece)
        self._portals = None             # the 0x1000 quads, read on demand
        # how far the game follows the portals from each area (opcode 0x43)
        self.portal_depth = {t["zone"]: t["portal_depth"] for t in self.lvl["terrain"]}
        # the area of the placed player: the area to start from when the
        # camera is in no collision block (finding 295)
        self.player_area = next((o["area"] for o in self.lvl["objects"] if o.get("start")), None)
        self._read_gates()
        # the skies that take turns (finding 314): which one is shown
        self._read_sky_choices(sky_choice)
        if self.move_characters:
            self.mover_sim = moversmod.Simulation(self.lvl, self.collision_blocks)
        self._build()
        # the selector's run records (overlays._wall_overlays): they ride in
        # the piece cache, so a level mounted from disk has them too
        self.wall_picks = self._pieces.get(("wall_picks",), [])

    def _read_sky_choices(self, sky_choice):
        """The skies the game alternates, and the one to show.

        In three levels two skies are carried with the camera but never stand
        together: a rule of one object deletes one sky (effect 0x4000000
        naming its role, finding 314) and clones the other (0x100 / 0x40000).
        Read on the whole disc with `tools/sky_rules.py`: *"Witch" way to
        Albuquerque? 1* (`L02B1`, objects 47 and 143), *2* (`L02B2`, 39 and
        131) and *The Carrot-henge Mystery 3* (`L02C3`, 91 and 132); nowhere
        else does a rule delete a sky while another is cloned.

        `sky_choices`: [(role, object number, at start)] of the skies that take
        turns, the one shown first; empty where nothing alternates.
        `sky_hidden`: the roles not built. The default is the sky the level
        starts with (placed, or cloned by a rule true at startup); where
        none is (`L02C3` starts in a cave, both skies arrive later) it is the
        one `preferences.py` names, else the first by object number.
        """
        self.sky_choices, self.sky_hidden = [], set()
        objects = self.lvl["objects"]
        templates = {}
        for o in objects:
            if o["block_type"] == 0x08 and o["role"] not in templates:
                templates[o["role"]] = o
        skies = {}          # role -> first camera follower with a model
        models = {r["id"]: r for r in self.lvl["resources"] if r["data_kind"] == "model"}
        for n, o in enumerate(objects):
            if not carried_by_camera(o) or not o["role"] or o["role"] <= 0:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None or models[mid]["size"] <= 12 or o["role"] in skies:
                continue
            skies[o["role"]] = n
        if len(skies) < 2:
            return
        clones, deletes = 0x100 | 0x40000, 0x4000000
        exclusive = set()
        for x in objects:
            if x["block_type"] == 0x08:
                continue
            group = [x] + [templates[r["field28"]] for r in x.get("rules", ())
                           if r["effect"] & clones and r["field28"] in templates]
            gone = {r["field28"] for g in group for r in g.get("rules", ()) if r["effect"] & deletes}
            born = {r["field28"] for g in group for r in g.get("rules", ()) if r["effect"] & clones}
            for a in gone & set(skies):
                for b in born & set(skies):
                    if a != b:
                        exclusive |= {a, b}
        if len(exclusive) < 2:
            return
        # at start: placed, or cloned by a rule true at startup, following the
        # templates a startup clone makes in turn (as _build_clones does)
        at_start = {role for role in exclusive
                    if objects[skies[role]]["block_type"] != 0x08 and objects[skies[role]]["position"]}

        def startup_clones(obj, depth):
            for r in obj.get("rules", ()):
                if r["effect"] & clones and _at_startup(r) and r["field28"] in templates:
                    t = templates[r["field28"]]
                    if t["role"] in exclusive:
                        at_start.add(t["role"])
                    if depth < 3:
                        startup_clones(t, depth + 1)

        for o in objects:
            if o["block_type"] != 0x08 and o["position"]:
                startup_clones(o, 1)
        roles = sorted(exclusive, key=lambda role: skies[role])
        default = self.pref.get("sky")
        if default not in exclusive:
            default = next((role for role in roles if role in at_start), roles[0])
        chosen = sky_choice if sky_choice in exclusive else default
        roles.sort(key=lambda role: (role != chosen, skies[role]))
        self.sky_choices = [(role, skies[role], role in at_start) for role in roles]
        self.sky_hidden = exclusive - {chosen}

    def _read_gates(self):
        """The gates of the level, the state each one is shown in, and the
        groups (game/gates.py). Read once per level: the choice of state and
        the flag Collision boxes both use it."""
        self.gates, self.gate_groups = {}, {}
        try:
            found = gatesmod.gates_of(self.lvl)
            self.gate_groups = gatesmod.groups_of(self.lvl, found)
        except Exception:  # noqa: BLE001
            return
        box_cache = {}
        by_gate = {}
        for switch, numbers in self.gate_groups.items():
            for number in numbers:
                by_gate.setdefault(number, switch)
        for gate in found:
            opened = shut = None
            if self.gate_state != "game" or self.gate_choices:
                opened, shut = gatesmod.open_and_closed(self.sec4, self.res, gate, box_cache)
            switch = by_gate.get(gate["number"])
            chosen = self.gate_choices.get(switch, self.gate_state)
            state = {"open": opened, "shut": shut}.get(chosen)
            # who opens it: only the switches of the state that OPENS it. The
            # other states of an object also wait on bytes, and drawing a line
            # for each of them filled the level with lines that do not say
            # "this opens that" (in *Follow the Red Pirate Road* (`L03D1`) 69
            # of 88 were not gates at all)
            openers = set()
            # only what blocks the way: an object Bugs can stand on, or one
            # his box only touches, is not a gate that opens. The same test the menu's Gates entry uses
            flags = (gate["object"].get("static_flags") or (0, 0))[0]
            blocks = bool(flags & gatesmod.STOPS_BUGS) and not flags & gatesmod.STAND_ON
            start_size = gatesmod.box_volume(self.sec4, self.res, gate["object"], gate["start"],
                                             box_cache) if gate["start"] else None
            for state, who in (gate["opened_by"].items() if blocks else ()):
                if state == gate["start"]:
                    continue
                if gatesmod.deletes(gate["object"], state):
                    changes = True
                else:
                    size = gatesmod.box_volume(self.sec4, self.res, gate["object"], state, box_cache)
                    changes = size is not None and size != start_size
                if changes:
                    openers |= {n for n in who if n != gate["number"]}
            openers = sorted(openers)
            self.gates[gate["number"]] = {
                "gate": gate, "open": opened, "shut": shut, "switch": switch,
                "state": state,
                "gone": state is not None and gatesmod.deletes(gate["object"], state),
                "opened_by": openers,
                # everything that writes a byte this object waits on, whatever
                # the state: not drawn, but the name on the box can use it
                "reacts_to": sorted({n for who in gate["opened_by"].values() for n in who
                                     if n != gate["number"]}),
            }

    def gate_role(self, number):
        """The animation role that shows a gate in the state chosen for it, or
        None to leave it as the game starts it."""
        info = self.gates.get(number)
        if not info or info["state"] is None:
            return None
        roles = gatesmod.roles_of_state(info["gate"]["object"], info["state"])
        return roles[0] if roles else None

    def _piece(self, item_key, build_items, mount=True, area=None):
        """Mounts piece `item_key`: from memory if present, otherwise builds it
        (`build_items` calls _add_faces) and remembers it. The counters the build
        changes are remembered as a difference and reapplied. With
        `mount=False` the caller mounts the returned piece later."""
        piece = self._pieces.get(item_key)
        if piece is None:
            before = dict(self.stat)
            self._current_piece = {}
            self._stamps = {}           # by id(faces): valid only inside this piece
            self._p_lo, self._p_hi = [1e9, 1e9, 1e9], [-1e9, -1e9, -1e9]
            try:
                build_items()
            finally:
                groups_by_key = {s: (meta, array("f", data_items), [array("f", b) for b in frames],
                                     face_tris)
                          for s, (meta, data_items, frames, face_tris) in self._current_piece.items()}
                self._current_piece = None
            # new keys at zero too: the rebuild must give the
            # same counters as the first time
            delta = {k: v - before.get(k, 0) for k, v in self.stat.items()
                     if k not in before or v != before[k]}
            piece = (groups_by_key, self._p_lo, self._p_hi, delta)
            self._pieces[item_key] = piece
        else:
            for k, d in piece[3].items():
                self.stat[k] = self.stat.get(k, 0) + d
        if mount:
            self._mount(piece, area)
        return piece

    def _mount(self, piece, area=None, keep_area=False):
        """Adds a piece's triangles to the level's groups (copying them:
        the piece in memory stays intact for the next rebuild). With
        `split_areas` a piece that the game cuts by area (a terrain piece,
        an object with bit 0 of opcode 0x3A) goes into groups of its own.
        `keep_area`: its own groups even without `split_areas` (a sky cut by
        area: only one of them is drawn at a time)."""
        groups_by_key, lo, hi, _delta = piece
        if not (self.split_areas or keep_area):
            area = None
        for lookup_key, ((tex_id, category, blend, spin, mover, two_sided), data_items, frames,
                         face_tris) in groups_by_key.items():
            if area is not None:
                lookup_key = lookup_key + (("area", area),)
            face_group = self.face_groups.get(lookup_key)
            if face_group is None:
                face_group = self.face_groups[lookup_key] = FaceGroup(tex_id, category, blend, len(frames),
                                                                      spin, area, mover, two_sided)
            face_group.data.extend(data_items)
            face_group.face_tris.extend(face_tris)
            for target, b in zip(face_group.frames, frames):
                target.extend(b)
        for i in range(3):
            self.lo[i] = min(self.lo[i], lo[i])
            self.hi[i] = max(self.hi[i], hi[i])

    def _add_faces(self, vertices, faces, category, *, rot=None, scale_factor=1.0, pos=(0, 0, 0), anim=None,
              spin=None, counted=True, mover=None):
        """Adds faces to the piece being built. `anim` = (key, frame,
        n_frames) for an animated object: its groups are its own, one per
        frame. `spin` = (key, units per pass) for a rotating
        object: its groups are its own too, and rotate around the vertical
        through `pos`. The keys use the object's index, not `id()`, which Python
        recycles between one rebuild and the next. `counted=False` (the invisible
        walls) touches neither bounds nor the triangle count: the initial
        camera and the statistics stay as before."""
        converted = [geo._transform(p, rot=rot, scale_factor=scale_factor, pos=pos) for p in vertices]
        used_pts = [converted[h] for h in {h for vl in faces for h in vl.corners}]
        if used_pts and counted:
            # the piece's bounds, from only the vertices a face uses: loose
            # ones (L01a has some) would widen the terrain and move the
            # initial camera
            for axis_idx in range(3):
                column = [p[axis_idx] for p in used_pts]
                self._p_lo[axis_idx] = min(self._p_lo[axis_idx], min(column))
                self._p_hi[axis_idx] = max(self._p_hi[axis_idx], max(column))
        targets = self._current_piece
        pivot = geo._transform((0, 0, 0), pos=pos) if spin else None
        # the face stamp is made once per model: the frames of
        # an animated object only change the positions
        # keyed by id(), but the list itself is kept alongside: a freed list's
        # id can be reused by a new one, and then the stamp would be another
        # model's (the many overlay boxes hit this once, with IndexError)
        hit = self._stamps.get(id(faces))
        if hit is not None and hit[0] is faces:
            stamp = hit[1]
        else:
            stamp = self._stamp(faces)
            self._stamps[id(faces)] = (faces, stamp)
        first_idx = anim is None or anim[1] == 0
        for tex_id, blend, bare, tri_vertices, two_sided in stamp:
            if bare and first_idx:
                self.stat["untextured"] += 1
            lookup_key = ((tex_id, category, blend) + ((anim[0],) if anim else ())
                       + ((spin[0],) if spin else ()) + ((("mover", mover),) if mover is not None else ())
                       + ((("two_sided",),) if two_sided else ()))
            item = targets.get(lookup_key)
            if item is None:
                meta = (tex_id, category, blend, (pivot, spin[1]) if spin else None, mover, two_sided)
                item = targets[lookup_key] = (meta, [], [[] for _ in range(anim[2] if anim else 0)], [])
            target = item[2][anim[1]] if anim else item[1]
            for h, attrs in tri_vertices:
                target.extend(converted[h])
                target.extend(attrs)
            if anim is None:
                # how many triangles this face became: the PC orders the
                # semi-transparent faces one FACE at a time, not one triangle
                # at a time (finding 306), and a quad is two of them
                item[3].append(len(tri_vertices) // 3)
            if first_idx and counted:
                self.stat["triangles"] += len(tri_vertices) // 3

    def _stamp(self, faces):
        """For each face: texture, blending, whether its texture is missing, and
        the vertices of its triangles as (vertex index, color and uv).

        A texture the level does not register does not exist: the color applies.
        The uvs are stored as byte / 255 over the whole texture, the OpenGL
        renderer's rule (finding 328); the chosen rule is applied when drawing
        (`drawing.py`). A PSX quad is Z-ordered, not a fan: (0,1,2) and (1,3,2)."""
        output = []
        for vl in faces:
            label = isinstance(vl.tex_id, str)      # a flag's name (flag_labels): uvs already 0..1
            tex_id = vl.tex_id if label or vl.tex_id in self.sizes else None
            bare = vl.tex_id is not None and tex_id is None
            uvs = None if bare else vl.uvs
            vertex_attrs = []
            for i in range(len(vl.corners)):
                r, g, b = vl.colors[i]
                if label:
                    u, v = uvs[i]
                else:
                    u, v = geo.uv_to_unit(uvs[i][0], uvs[i][1]) if uvs else (0.0, 0.0)
                vertex_attrs.append((r / 255.0, g / 255.0, b / 255.0, u, v))
            tri_vertices = [(vl.corners[i], vertex_attrs[i]) for d in geo.triangles(len(vl.corners)) for i in d]
            output.append((tex_id, vl.blend, bare, tri_vertices, vl.two_sided))
        return output

    def _build(self):
        for k, t in enumerate(self.lvl["terrain"]):
            self._piece(("terrain_block", k), lambda t=t: self._terrain_block(t), area=t["zone"])
            if "terrain_overlays" in self.families:
                self._piece(("terrain_overlays", k), lambda t=t: self._terrain_overlays(t))
        # the terrain bounds are used to frame the camera: props can
        # be huge (the sky dome) and would throw off the framing
        self.terrain_lo = list(self.lo)
        self.terrain_hi = list(self.hi)
        diagonal = max(h - l for h, l in zip(self.terrain_hi, self.terrain_lo)) or 1.0

        models = {r["id"]: r for r in self.lvl["resources"] if r["data_kind"] == "model"}
        for n, o in enumerate(self.lvl["objects"]):
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None or models[mid]["size"] <= 12:
                continue
            role = self.gate_role(n) or self.pref["pose"].get(mid)
            if self.gates.get(n, {}).get("gone"):
                continue            # in this state the game deletes it: nothing to draw
            if o["role"] in self.sky_hidden and carried_by_camera(o):
                continue            # the sky the game swaps for the one shown
            moving = self.mover_sim is not None and n in self.mover_sim.by_index
            piece = self._piece(("object", n, role, moving),
                                lambda n=n, o=o, mid=mid, role=role, moving=moving:
                                    self._placed_object(n, o, models[mid], role, diagonal,
                                                        mover=n if moving else None),
                                mount=False)
            # the box only for an object that draws something (a piece
            # without groups read no faces), and mounted before the object,
            # as when it was part of it: same drawing order
            if "collision_boxes" in self.families and piece[0]:
                self._piece(("collision_box", n, role),
                            lambda o=o, role=role: self._object_collision_box(o, role, diagonal))
            # cut by area only with bit 0 of opcode 0x3A (finding 294). A sky
            # cut that way keeps its area ALWAYS, not only with Visibility by
            # area on: Era selector has five of them, one per era, and the
            # game shows the one of the area you are in (Drawing.sky_area)
            area = o["area"] if o["cull_flags"] & 1 else None
            self._mount(piece, area, keep_area=area is not None and carried_by_camera(o))

        if "collision_boxes" in self.families:
            # the names float above the objects and are drawn every frame
            # facing the camera, so they are a list, not triangles in a piece
            self._collision_box_labels(models, diagonal)
            if self.gate_links != "off":
                # only when the flag asks for them: with it off there is
                # nothing to build, and a check that turns the overlays off
                # must find none of them (checks/check_walls.py)
                self._piece(("gate_links", self.gate_links), self._gate_links)
        self._build_clones(models)
        if "collision_boxes" in self.families:
            # the clones' names, after the clones: out of the piece cache, like
            # the objects' names
            self._clone_labels()
        if "zones" in self.families:
            self._piece(("zone",), self._death_zones)
        if "heightmap" in self.families:
            self._piece(("heightmap",), self._heightmap)

    def portals(self):
        """The portals of the level (the 0x1000 quads, finding 293):
        (area of the piece, area seen through, the quad's four corners in
        game coordinates). Read once, kept."""
        if self._portals is None:
            self._portals = []
            for t in self.lvl["terrain"]:
                quads, areas = [], []
                try:
                    vertices, _faces, _stat = geo.read_terrain(self.sec4, t["offset"], quads, areas)
                except Exception:  # noqa: BLE001
                    continue
                sp = t["translation"]
                for quad, area in zip(quads, areas):
                    self._portals.append((t["zone"], area,
                                          [tuple(vertices[h][k] + sp[k] for k in range(3)) for h in quad]))
        return self._portals

    def _terrain_block(self, t):
        """The triangles of a terrain block (one piece)."""
        vertices, faces, stat = geo.read_terrain(self.sec4, t["offset"], [])
        self._add_faces(vertices, faces, "terrain", pos=tuple(t["translation"]))
        self.stat["terrain"] += len(faces)
        for item_key in ("sectors", "wall_sectors"):
            if item_key in stat:
                self.stat[item_key] = self.stat.get(item_key, 0) + stat[item_key]

    def _placed_object(self, n, o, model, role, diagonal, mover=None):
        """The triangles of a placed object (one piece).

        `mover` (the object's index) builds them around the object's own
        origin, with no position and no Y rotation: the simulation puts them
        where they are when drawing (window/drawing.py)."""
        try:
            # a model's parts are in local space: without the rig
            # they end up stacked on the origin ("disassembled" objects)
            trans = montage.transforms(self.sec4, o["resources"], self.res, o, self.stat, role=role)
            vertices, faces, _ = geo.read_model(self.sec4, model["offset"], trans)
            frames = montage.animation(self.sec4, o["resources"], self.res, o, role=role)
        except Exception:  # noqa: BLE001
            return
        if not faces:
            return
        rotation = o["rotation"]
        if mover is not None and rotation:
            rotation = [rotation[0], 0, rotation[2]]     # the heading comes from the simulation
        rot = geo._rotation_matrix(rotation) if rotation else None
        scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
        place = (0, 0, 0) if mover is not None else tuple(o["position"])

        # what the game carries with the camera (the sky, the sea) goes into
        # the group that follows the camera and can be turned off, built
        # where the game puts it: the file's position does not count. The
        # viewer used to guess it by size ("as large as the whole level"),
        # which in When Sam met Bunny, 56 m across, dragged three ordinary
        # objects around with the camera and left the real sky 154 m off in
        # "Witch" way to Albuquerque? 1 (checks/check_sky.py)
        if carried_by_camera(o):
            category, place = "sky_dome", camera_place(o)
        else:
            category = "props"
        step = _spin_speed(o)
        spin = (("spin", n), step) if step else None
        # an animation that actually changes something: one group per frame
        if frames and any(b != frames[0] for b in frames[1:]):
            for f, tr in enumerate(frames):
                verts, _ids = geo.model_vertices(self.sec4, model["offset"], tr)
                self._add_faces(verts, faces, category, rot=rot, scale_factor=scale_factor,
                           pos=place, anim=(("anim", n), f, len(frames)),
                           spin=spin, mover=mover)
            self.stat["animated"] = self.stat.get("animated", 0) + 1
        else:
            self._add_faces(vertices, faces, category, rot=rot, scale_factor=scale_factor, pos=place,
                       spin=spin, mover=mover)
        if spin:
            self.stat["spinning"] = self.stat.get("spinning", 0) + 1
        self.stat["props" if category == "props" else "sky_dome"] = \
            self.stat.get("props" if category == "props" else "sky_dome", 0) + 1

    def _build_clones(self, models):
        """The templates that the objects' rules make appear.

        In the game a template (block 0x08, no position) becomes visible
        when a `0x31` rule of a live object carries effect 0x100 or
        0x40000: `FUN_00448d40` clones the template whose role is field +28,
        at the object's position and with its rotation (Ombelll's finding 194). The
        lit torches, the blue chests and the falling crates work like this.

        Which of them the game really has is read by `game/clone_life.py`,
        the rules walked as the engine walks them with Bugs doing nothing:
        what comes by itself and stays is "clones_in_level" (Cloned
        templates -> In the level: the rails of the mines), the rest --
        what needs Bugs, what comes and goes by itself -- is "clones" (All).
        Each pair (object, role) only once; the first template with the role
        wins, as in `FUN_00448d40` (finding 68).

        A clone can in turn clone (finding 279): the torch, cloned by
        a trigger, clones the flame on its own top. A freshly born template
        clones what its own rules make come by itself, never more in the
        level than itself; at most three levels deep.
        """
        # the answers ride in the piece cache: a level mounted from disk
        # does not read its rules again
        self.clone_kinds = self._pieces.get(("clone_kinds",))
        if self.clone_kinds is None:
            self.clone_kinds = self._pieces[("clone_kinds",)] = clone_life.kinds(self.lvl)
        self.templates = {}
        self._clone_label_jobs = []
        self._idx = {}               # id(object) -> index in the level, for the keys
        for n, o in enumerate(self.lvl["objects"]):
            self._idx[id(o)] = n
            if o["block_type"] == 0x08 and o["role"] not in self.templates:
                self.templates[o["role"]] = o
        self._models = models
        seen_keys = set()
        self._sky_roles_built = set()
        for n, o in enumerate(self.lvl["objects"]):
            if o["block_type"] == 0x08 or not o["position"]:
                continue
            rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
            # with Moving characters on, what an attacker swings is a child
            # held at the marker, alive only between two frames (finding 317)
            swung = self._attack_rules(o) if self.move_characters else {}
            boxes_on = "collision_boxes" in self.families
            moving = self.mover_sim is not None and n in self.mover_sim.by_index
            if swung:
                place = (0, 0, 0) if moving else tuple(o["position"])
                held_rot = rot
                if moving and o["rotation"]:
                    held_rot = geo._rotation_matrix([o["rotation"][0], 0, o["rotation"][2]])
                for role_id, span in swung.items():
                    self._clone_label_jobs.append((role_id, n, place, held_rot, span))
                    self._piece(("held", n, role_id, span, moving, boxes_on),
                                lambda o=o, n=n, role_id=role_id, span=span, place=place,
                                held_rot=held_rot, moving=moving, boxes_on=boxes_on:
                                    self._held_clone(o, n, role_id, span, place, held_rot, "always",
                                                     mover=n if moving else None, boxes_on=boxes_on))
            for i_rule, r in enumerate(o.get("rules", [])):
                role = r["field28"]
                if not (r["effect"] & (0x100 | 0x40000)) or role <= 0 or (n, role) in seen_keys:
                    continue
                if role in swung:
                    continue          # already there, hanging from its bone
                seen_keys.add((n, role))
                if role in self.pref["always_cloned"]:
                    # an "equal" condition on a variable fixed by the user
                    # is evaluated: the blue crates appear in only one order
                    op, val, index = r["condition"]
                    if op in (0x01, 0x02) and index in self.pref["table1"]                             and self.pref["table1"][index] != val:
                        continue
                    # always shown (preferences.py), once per place
                    place = (role, tuple(o["position"]))
                    if place in seen_keys:
                        continue
                    seen_keys.add(place)
                    category = "always"
                else:
                    kind = self.clone_kinds.get(("placed", n, i_rule), clone_life.EVENT)
                    category = "clones_in_level" if kind == clone_life.LEVEL else "clones"
                self._spawn_clone(o, r, tuple(o["position"]), rot, category, 1, (n, i_rule))

    def _attach_point(self, parent_ref, rule, pos, rot):
        """Where a clone appears. With bit 0x80 of the effect, field +24
        picks a part of the parent's rig: the k-th one marked by a record
        0xA in its animation (finding 279: the top of the torch), and if
        there are none the k-th child of the root (274: the three blue chests).
        Readings consistent with the data and the screenshots, not read in the code."""
        if not (rule["effect"] & 0x80 and rule["field24"] >= 1):
            return pos
        parts = montage.parts_of(self.sec4, parent_ref["resources"], self.res, parent_ref)
        if not parts:
            return pos
        candidates = montage.attach_points(self.sec4, parent_ref["resources"], self.res, parent_ref)
        if not candidates:
            root_part = next(iter(parts.values()))
            candidates = [d.id for d in parts.values() if d.parent_ref == root_part.id]
        if rule["field24"] > len(candidates) or candidates[rule["field24"] - 1] not in parts:
            return pos
        _m, t = rigmod.per_part(parts)[candidates[rule["field24"] - 1]]
        if rot is not None:
            t = tuple(sum(rot[i][k] * t[k] for k in range(3)) for i in range(3))
        return (pos[0] + t[0], pos[1] + t[1], pos[2] + t[2])

    def _role_of(self, obj):
        """The role chosen (preferences.py or menu) for an object's model."""
        mid = next((x for x in obj["resources"] if x in self._models), None)
        return self.pref["pose"].get(mid) if mid is not None else None

    def _spawn_clone(self, parent_ref, rule, pos, rot, category, depth, route):
        """A clone. `route` identifies the clone stably: parent and
        rule, also for clones of clones; its piece key adds the
        roles chosen for the parent (the attachment depends on its pose) and for
        the clone, so a state change redoes only what it touches."""
        t = self.templates.get(rule["field28"])
        if t is None:
            self.stat["clones_without_model"] += 1
            return
        if carried_by_camera(t):
            if t["role"] in self.sky_hidden:
                return          # the sky the game swaps for the one shown
            # a sky cloned by more than one rule (the rocks of The
            # Carrot-henge Mystery 3, objects 88 and 125): one is enough,
            # it follows the camera wherever it was cloned from
            if t["role"] in self._sky_roles_built:
                return
            self._sky_roles_built.add(t["role"])
        parent_role, role = self._role_of(parent_ref), self._role_of(t)
        attach_key = ("attach_point", route, parent_role)
        if attach_key not in self._pieces:
            self._pieces[attach_key] = self._attach_point(parent_ref, rule, pos, rot)
        pos = self._pieces[attach_key]
        models = self._models
        mid = next((x for x in t["resources"] if x in models), None)
        spr = texmod.sprite(t, self.res, self.sec4)
        n_t = self._idx[id(t)]
        if mid is not None and models[mid]["size"] > 12:
            self._piece(("clone", route, category, parent_role, role),
                        lambda: self._clone(t, n_t, models[mid], role, pos, rot, category))
            # the box only for the clones the viewer always shows
            # (preferences.py: torches, crates, barrels, anchors) and for what
            # an attacker swings: the ones behind the flag Cloned templates
            # would leave their boxes hanging with the clone itself hidden
            if "collision_boxes" in self.families and category == "always":
                n_parent = self._idx.get(id(parent_ref))
                if n_parent is not None:
                    self._clone_label_jobs.append((rule["field28"], n_parent, pos, rot, None))
                    self._piece(("clone_box", route, parent_role, role, True),
                                lambda t=t, n_t=n_t, n_parent=n_parent, pos=pos, rot=rot:
                                    self._clone_collision_box(t, n_t, n_parent, pos, rot))
        elif spr is not None:
            # a sprite: a square facing the camera, drawn every
            # frame (Viewer._draw_sprites); sizes in world units.
            # The game doubles the box AND applies the object's scale twice
            # (finding 305): width = 2 w sx^2, height = 2 h sy^2. On the
            # torch of Hey... What's up, Dock? part 1 that is 77 x 184 for
            # the flame (record 32 x 64, scale 1.1 and 1.2) and 512 x 512
            # for the glow (64 x 64, scale 2 and 2), against the 32 x 64 and
            # 64 x 64 the viewer drew before.
            scale_factor = t.get("scale_factor") or [4096, 4096, 4096]
            sx, sy = scale_factor[0] / 4096.0, scale_factor[1] / 4096.0
            # centred on its point, not resting on it, when the second dword
            # of the template's opcode 0x16 has bit 0x8000000 (finding 338):
            # the torch's glow sits on the flame, the flame on the torch's top
            flags = t.get("static_flags") or [0, 0]
            self.sprites.append({"pos": geo._transform((0, 0, 0), pos=pos), "category": category,
                                 "centred": bool(flags[1] & 0x8000000),
                                 "size": (2.0 * spr["size"][0] * sx * sx / geo.UNITS_PER_METER,
                                          2.0 * spr["size"][1] * sy * sy / geo.UNITS_PER_METER),
                                 "frames": spr["frames"], "sequence": spr["sequence"],
                                 "blend": spr["blend"]})
            self.stat["sprite"] = self.stat.get("sprite", 0) + 1
        else:
            self.stat["clones_without_model"] += 1
        if depth >= 3:
            return
        for i_rule, r in enumerate(t.get("rules", [])):
            if not (r["effect"] & (0x100 | 0x40000) and r["field28"] > 0):
                continue
            kind = self.clone_kinds.get(("template", t["role"], i_rule), clone_life.EVENT)
            if kind == clone_life.EVENT:
                continue          # only what the clone makes come by itself
            # what the clone makes and loses again (the torch's puff, 508,
            # a template with no state: deleted on its first tick) goes
            # under All, whoever the parent is, the curated ones included
            child = category if kind == clone_life.LEVEL else "clones"
            self._spawn_clone(t, r, pos, rot, child, depth + 1, route + (i_rule,))

    def _attack_rules(self, obj):
        """The rules of the object's current step that swing something
        (finding 317): {template role: (first frame, last frame)}.

        Frame `A` clones the template held at the attachment marker (effect
        0x40 for the frame, 0x100 / 0x40000 to clone, 0x80 held), frame `B`
        deletes the live object with that id (0x4000000): in between the child
        hangs from the marker's bone and follows it.
        """
        step_key = montage.start_key(obj)
        group = next((st.get("rules") for st in obj.get("steps", ()) if st["key"] == step_key), None)
        if not group:
            return {}
        clones, deletes, found = {}, {}, False
        for rule in obj.get("rules", ()):
            if rule["key"] != group:
                if found:
                    break
                continue
            found = True
            effect, frame, role = rule["effect"], rule["field24"], rule["field28"]
            if not effect & 0x40 or role <= 0:
                continue
            if effect & (0x100 | 0x40000) and effect & 0x80:
                clones.setdefault(role, frame)
            elif effect & 0x4000000:
                deletes.setdefault(role, frame)
        return {role: (frame, deletes[role]) for role, frame in clones.items() if role in deletes}

    def _held_clone(self, parent_ref, n_parent, role_id, span, pos, rot, category, mover=None,
                    boxes_on=False):
        """A child held at the attachment marker, frame by frame (finding 317).

        The crab's claw and the pirate's club never fly: they are cloned on one
        frame of the animation the parent repeats and deleted on another, and
        in between they follow the marker's bone -- the going out and coming
        back is the bone's animation. Here the child becomes one group per
        frame of the PARENT's animation, empty on the frames where it does not
        exist, so the viewer's own animation clock shows it appearing and
        disappearing with no work per frame.
        """
        t = self.templates.get(role_id)
        if t is None:
            return
        model_id = next((x for x in t["resources"] if x in self._models), None)
        if model_id is None or self._models[model_id]["size"] <= 12:
            return
        parent_role = self._role_of(parent_ref)
        bones = montage.marker_animation(self.sec4, parent_ref["resources"], self.res,
                                         parent_ref, role=parent_role)
        markers = montage.attach_points(self.sec4, parent_ref["resources"], self.res, parent_ref)
        if not bones or not markers or markers[0] not in bones[0]:
            return
        marker = markers[0]
        try:
            trans = montage.transforms(self.sec4, t["resources"], self.res, t, role=self._role_of(t))
            vertices, faces, _ = geo.read_model(self.sec4, self._models[model_id]["offset"], trans)
        except Exception:  # noqa: BLE001
            return
        if not faces:
            return
        first, last = span
        n_frames = len(bones)
        lookup_key = ("held", n_parent, role_id)
        for f in range(n_frames):
            alive = first <= f < last if first <= last else (f >= first or f < last)
            if not alive or marker not in bones[f]:
                continue
            m, translation = bones[f][marker]
            # the bone in the parent's frame, then the parent's own place:
            # R = parent rotation * bone matrix, P = parent rotation * bone
            # translation + parent position
            if rot is not None:
                matrix = tuple(tuple(sum(rot[i][k] * m[k][j] for k in range(3)) for j in range(3))
                               for i in range(3))
                offset = tuple(sum(rot[i][k] * translation[k] for k in range(3)) for i in range(3))
            else:
                matrix, offset = m, translation
            place = (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2])
            self._add_faces(vertices, faces, category, rot=matrix, pos=place,
                            anim=(lookup_key, f, n_frames), mover=mover)
            if boxes_on:
                self._clone_collision_box(t, self._idx[id(t)], n_parent, place, matrix,
                                          frame=f, n_frames=n_frames, counted=f == first)
        self.stat["held_clones"] = self.stat.get("held_clones", 0) + 1

    def _clone(self, t, n_t, model, role, pos, rot, category):
        """The triangles of a clone (one piece)."""
        try:
            trans = montage.transforms(self.sec4, t["resources"], self.res, t, role=role)
            vertices, faces, _ = geo.read_model(self.sec4, model["offset"], trans)
            frames = montage.animation(self.sec4, t["resources"], self.res, t, role=role)
        except Exception:  # noqa: BLE001
            return
        if not faces:
            return
        if carried_by_camera(t):
            # the sky and the sea also arrive as a cloned TEMPLATE, and then
            # the rule of _placed_object never saw them: they were drawn as
            # ordinary clones, standing still in the middle of the level
            # (the black cones and the block of The Carrot-henge Mystery 3),
            # and with Cloned templates off the level had no sky at all.
            # Like a placed sky they are built where the game puts them
            # (camera_place) and the drawing moves them with the camera
            category, pos = "sky_dome", camera_place(t)
        # a rotating clone (finding 280): the anchors, the clocks
        step = _spin_speed(t)
        spin = (("spin", n_t, pos), step) if step else None
        # a clone animates too (finding 278): the floating barrel
        if frames and any(b != frames[0] for b in frames[1:]):
            lookup_key = ("clone_anim", n_t, pos)
            for f, tr in enumerate(frames):
                verts, _ids = geo.model_vertices(self.sec4, model["offset"], tr)
                self._add_faces(verts, faces, category, rot=rot, pos=pos,
                           anim=(lookup_key, f, len(frames)), spin=spin)
        else:
            self._add_faces(vertices, faces, category, rot=rot, pos=pos, spin=spin)
        self.stat[category] = self.stat.get(category, 0) + 1
        if spin:
            self.stat["spinning"] = self.stat.get("spinning", 0) + 1

    def sprite_frame(self, sp, tick):
        """The texture id of a sprite's current frame."""
        total = sum(d for _f, d in sp["sequence"])
        t = tick % total
        for f, d in sp["sequence"]:
            if t < d:
                return sp["frames"][f]
            t -= d
        return sp["frames"][sp["sequence"][-1][0]]

    def bounds(self):
        return self.lo, self.hi

    def start_place(self):
        """Where the player starts, as (x, y, z, heading, source) in game
        units, or None: what the opening camera looks from.

        1. The placed player, the object with the start flag (opcode 0x13):
           in every playable level it stands inside the terrain. The
           ENTRANCE rules (finding 326) are not the start: on the disc only
           7 levels have them, and they are the places you come back to from
           another level.
        2. A player placed at the origin is carried by something else. In
           Downhill Duck! (finding 330) a trigger clones a vehicle whose rule
           takes object 1, Bugs, as its child (effect 0x20000000): the start
           is the first object that clones such a template.
        3. Nothing of the two, and the cutscenes, whose placed Bugs is an
           actor (CC3A and CC5A put theirs next to the origin, outside the
           terrain): None."""
        if levels.is_film(self.name):
            return None
        objects = self.lvl["objects"]
        player = next((o for o in objects if o.get("start")), None)
        if player and player.get("position") and tuple(player["position"]) != (0, 0, 0):
            rot = player.get("rotation") or (0, 0, 0)
            return (*player["position"], rot[1], "player")
        takes_bugs = {o["role"] for o in objects if o["block_type"] == 0x08
                      and any(r["effect"] & TAKES_CHILD and r["field28"] == BUGS_ID
                              for r in o.get("rules", []))}
        for n, o in enumerate(objects):
            if o["block_type"] == 0x08 or not o.get("position"):
                continue
            if any(r["effect"] & (0x100 | 0x40000) and r["field28"] in takes_bugs
                   for r in o.get("rules", [])):
                rot = o.get("rotation") or (0, 0, 0)
                return (*o["position"], rot[1], f"object {n}")
        return None


def levels_in(folder, extra=False):
    """The .bze files in a folder that the viewer can open, in alphabetical
    order: loading screens (L_*, SCREEN*, LOADING) are left out, they have
    no 3D environment (check_levels.py).

    Without `extra` the Extra files are left out too (`levels.playable`):
    the 16 cutscenes, the menu and the credits, and the six `_8` variants.
    That is what a run over the whole disc means, and the default is off so
    that a tool written later gets it without
    remembering. Only the viewer's own menu asks for `extra=True`."""
    if not folder:
        return []
    try:
        everything = sorted((f for f in os.listdir(folder) if f.lower().endswith(".bze")), key=str.lower)
    except OSError:
        return []
    found = [os.path.join(folder, f) for f in everything
             if not f.lower().startswith(("l_", "screen", "loading"))]
    return found if extra else levels.playable(found)


def resolve_levels_folder(folder):
    """The folder given by the user, or Datas/bze or bze inside it:
    the game folder works too."""
    for beneath in ("", os.path.join("Datas", "bze"), "bze"):
        c = os.path.join(folder, beneath) if beneath else folder
        if paths.has_levels(c):
            return c
    return None
