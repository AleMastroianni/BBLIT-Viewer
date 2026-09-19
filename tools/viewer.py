"""Native level viewer for Lost in Time. Reads the .bze files directly.

    .venv/Scripts/python tools/viewer.py L03A
    .venv/Scripts/python tools/viewer.py L03A --screenshot out.png  (one screenshot, then exits)

Controls:
    mouse (right button held)     look
    W A S D                       move, Q/E up and down
    Shift                         faster, Ctrl slower
    wheel                         change base speed
    T                             textures on/off
    F                             wireframe
    O                             props on/off
    P                             stop / restart all animations
    - +                           animation ticks per second
    L                             bilinear filter (like the PC) / sharp texels
    N                             animated textures on/off
    H                             sky dome on/off
    M                             semi-transparent blending on/off
    G                             cloned templates: off / at startup / all
    [ ]                           previous / next level
    R                             back to the starting point
    Esc                           menu (Backspace or M back, arrows and Enter)
    Alt+Enter                     fullscreen

The menu (tools/menu.py, texts in tools/texts.py) follows the layout of the CTR
viewer: Load level, Level options (with Flags), Video options, General
options, Help. Settings persist from one run to the next
(tools/settings.py); entity states and flags chosen from the menu last
only for the session.

There is no intermediate format: the .bze files are decompressed, the load
script read and the geometry built in memory. The decompressed sections go
into an on-disk cache, because decompressing in Python takes a few seconds.
"""

from __future__ import annotations

import argparse
import ctypes
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from array import array  # noqa: E402

import pyglet  # noqa: E402

# pyglet checks for errors after EVERY OpenGL call: loading L03A meant
# 104 thousand checks, 0.9 s. It is only useful for debugging rendering, and must
# be turned off before importing pyglet.gl (menu.py imports it too).
pyglet.options["debug_gl"] = False

import paths  # noqa: E402

import bze  # noqa: E402
import export_obj as geo  # noqa: E402
import collision  # noqa: E402
import zones  # noqa: E402
import level_cache  # noqa: E402
import loadscript  # noqa: E402
import montage  # noqa: E402
import rig as rigmod  # noqa: E402
import textures as texmod  # noqa: E402
import preferences  # noqa: E402
import tim  # noqa: E402
import upscale  # noqa: E402
import settings as settings_mod  # noqa: E402
import levels  # noqa: E402
import menu as menumod  # noqa: E402
import texts  # noqa: E402
from texts import t  # noqa: E402

import pyglet  # noqa: E402
from pyglet.gl import (  # noqa: E402
    GL_ARRAY_BUFFER, GL_BLEND, GL_CLAMP_TO_EDGE, GL_COLOR_BUFFER_BIT, GL_CULL_FACE,
    GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_FILL, GL_FLOAT, GL_FRONT_AND_BACK, GL_LINE,
    GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_NEAREST, GL_NEAREST, GL_ONE_MINUS_SRC_ALPHA, GL_RGBA, GL_SRC_ALPHA,
    GL_DYNAMIC_DRAW, GL_FALSE, GL_FUNC_ADD, GL_FUNC_REVERSE_SUBTRACT, GL_ONE, GL_STATIC_DRAW, GL_TRUE,
    GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_TRIANGLES, GL_UNSIGNED_BYTE, glBindBuffer,
    glBindTexture, glBindVertexArray, glBlendFunc, glBufferData, glClear, glClearColor,
    glDisable, glDrawArrays, glEnable, glEnableVertexAttribArray, glGenBuffers, glGenTextures,
    glBlendEquation, glDeleteBuffers, glDeleteTextures, glDeleteVertexArrays, glDepthMask,
    glGenVertexArrays, glGenerateMipmap, glPolygonMode,
    glTexImage2D, glTexParameteri,
    glVertexAttribPointer,
)
from pyglet.graphics.shader import Shader, ShaderProgram  # noqa: E402
from pyglet.math import Mat4, Vec3  # noqa: E402

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
# rules on every logic tick (docs finding 188), and the logic runs at 30 per
# second against the 15 animation blocks (finding 278). NOT measured:
# the rotation speed of the anchors will tell (280).
RULE_PASSES_PER_TICK = 2

# the invisible walls (0x1000 sectors), when shown: a magenta the game
# does not use, at half transparency (blend 0)
COLOR_INVISIBLE_WALLS = (255, 40, 200)
# the faces without collision (flag No collision): a cyan, like the second overlay
# of the CTR viewer, also at half transparency
COLOR_NO_COLLISION = (40, 230, 255)
# no collision, but the fall ends in a death/damage/teleport zone: faint
COLOR_NO_COLLISION_TRAP = (0, 120, 160)
# the objects' collision boxes (flag Collision boxes): orange, at half transparency
COLOR_COLLISION_BOXES = (255, 150, 20)
# the zones (keys Z and K): red where you die, purple where you get picked up
# and put back at a fixed point (teleport)
COLOR_DEATH = (235, 25, 25)
COLOR_TELEPORT = (170, 70, 255)
# the heightmap (flags Ground, Hard walls) and the fake walls (Fake walls)
COLOR_GROUND = (60, 170, 80)              # covered by a visible face
COLOR_INVISIBLE_GROUND = (140, 255, 60)  # no visible face above
COLOR_PIXEL = (255, 255, 255)              # isolated sub-cells, with the ray
COLOR_HARD_WALLS = (60, 120, 255)
# the collision volume of each mini area (flag Area boxes)
COLOR_AREA_BOXES = (255, 170, 60)
# the 0x1000 terrain faces (flag 0x1000 faces): not walls (tested in the game)
COLOR_FACES_1000 = (150, 150, 150)
# group -> viewer attribute that turns it on (the menu flags)
OVERLAYS = {
    "faces_1000": "show_faces_1000", "invisible_walls": "show_invisible_walls",
    "no_collision": "show_no_collision",
    "no_collision_trap": "show_no_collision",
    "area_boxes": "show_area_boxes", "area_boxes_lines": "show_area_boxes",
    "collision_boxes": "show_collision_boxes", "collision_boxes_lines": "show_collision_boxes",
    "death_zones": "show_death_zones", "death_zones_lines": "show_death_zones",
    "death_floor": "show_death_floor", "death_floor_lines": "show_death_floor",
    "covered_ground": "show_ground", "invisible_ground": "show_ground",
    "pixel": "show_ground", "pixel_beam": "show_ground",
    "hard_walls": "show_hard_walls",
}

# on the main menu background (like "ctrviewer by DCxDemo")
SIGNATURE = "BBLIT Viewer by AleMastroianni"

VERTEX_SHADER = """#version 330 core
in vec3 position;
in vec3 color;
in vec2 uv;
uniform mat4 mvp;
out vec3 v_color;
out vec2 v_uv;
void main() {
    gl_Position = mvp * vec4(position, 1.0);
    v_color = color;
    v_uv = uv;
}
"""

FRAGMENT_SHADER = """#version 330 core
in vec3 v_color;
in vec2 v_uv;
uniform sampler2D tex_sampler;
uniform int has_texture;
uniform int show_textures;
uniform float alpha;
uniform float blend_scale;
uniform float albedo;
out vec4 color_out;
void main() {
    // the original has no lights: the vertex color is baked lighting.
    // On the PC the factor is 1, not the PlayStation's 2 (128 = neutral):
    // measured on the L03A sea, (0,0,63) in the game and (0,0,63) here with 1,
    // (0,0,125) with 2 (finding 268)
    if (has_texture == 1 && show_textures == 1) {
        vec4 t = texture(tex_sampler, v_uv);
        if (t.a < 0.5) discard;
        color_out = vec4(t.rgb * v_color * albedo * blend_scale, alpha);
    } else {
        color_out = vec4(v_color * blend_scale, alpha);
    }
}
"""


# --------------------------------------------------------------- loading

def sections(bze_path: str, cache: str) -> dict[int, bytes]:
    """Decompresses sections 1, 3 and 4, with an on-disk cache."""
    stem = os.path.splitext(os.path.basename(bze_path))[0]
    cache_dir = os.path.join(cache, stem)
    os.makedirs(cache_dir, exist_ok=True)
    output = {}
    entries, data = bze.open_bze(bze_path)
    for s in entries:
        if s.id not in (1, 3, 4):
            continue
        file_path = os.path.join(cache_dir, f"{stem}_id{s.id:02d}.bin")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                output[s.id] = f.read()
        else:
            output[s.id] = bze.section_bytes(data, s)
            with open(file_path, "wb") as f:
                f.write(output[s.id])
    return output


class FaceGroup:
    """A group of triangles sharing texture and blending."""

    __slots__ = ("tex_id", "data", "vao", "vbo", "item_count", "category", "blend", "frames", "vaos",
                 "spin")

    def __init__(self, tex_id, category, blend=None, n_frames=0, spin=None):
        self.tex_id = tex_id
        self.blend = blend            # None = opaque, otherwise 0..3
        self.category = category          # "terrain", "props", "sky_dome", a clone group or an overlay
        # 8 floats per vertex (position, color, uv), in a compact array
        self.data = array("f")
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


# conditions that can be evaluated at level start, when table 1
# is zeroed (docs finding 161); the opcodes are those of FUN_0042a7d0
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
    stops at the first true one without effect 0x8000 (docs finding 188): here
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


class Level:
    """A level built in memory, in pieces: every terrain block, every
    object and every clone is a piece (its triangles per group, its
    bounds, its counters). `_pieces` is the memory of pieces already built for
    this level: rebuilding it for a state chosen from the menu redoes
    only the pieces whose role changed (before: 4.3 s to raise the bridges)."""

    def __init__(self, bze_path: str, cache: str, table=None, session_poses=None, pieces=None):
        self.name = os.path.splitext(os.path.basename(bze_path))[0]
        self.table = table
        sec = sections(bze_path, cache)
        blocks, _stat = loadscript.parse(sec[1])
        self.lvl = loadscript.export_level(blocks)
        self.sec3, self.sec4 = sec[3], sec[4]
        # the table: registered slots plus animated slots (finding 275)
        if self.table is None:
            self.sizes = tim.sizes(self.sec3, self.lvl["textures"])
        else:
            self.sizes = {}
            for tid, (block, offset) in self.table.slots.items():
                m = tim.sizes(block, [{"id": tid, "offset": offset}])
                self.sizes.update(m)
        self.res = {r["id"]: r for r in self.lvl["resources"]}
        try:
            self.collision_blocks = collision.read_level_blocks(self.sec4, self.lvl)
        except Exception:  # noqa: BLE001
            self.collision_blocks = []     # without a heightmap no face is judged
        # zones that kill, hurt or teleport: a fall into one is not a safe fall
        self.trap_boxes = [b for z in self.lvl["zones"] if (b := zones.trap_box(z))]
        self.face_groups: dict[tuple, FaceGroup] = {}
        self.stat = {"terrain": 0, "props": 0, "sky_dome": 0, "triangles": 0, "untextured": 0,
                     "from_game": 0, "fallback": 0, "clones": 0, "clones_at_start": 0,
                     "clones_without_model": 0}
        self.lo = [1e9, 1e9, 1e9]
        self.hi = [-1e9, -1e9, -1e9]
        self.sprites: list[dict] = []
        # the chosen level state (bridges, barrels, torches: preferences.py);
        # `session_poses` holds those changed from the menu, session only
        self.pref = preferences.for_level(self.name)
        self.pref["pose"] = {**self.pref["pose"], **(session_poses or {})}
        self._pieces = pieces if pieces is not None else {}
        self._current_piece = None       # the piece being built (see _piece)
        self._build()

    # ---- pieces

    def _piece(self, item_key, build_items):
        """Mounts piece `item_key`: from memory if present, otherwise builds it
        (`build_items` calls _add_faces) and remembers it. The counters the build
        changes are remembered as a difference and reapplied."""
        piece = self._pieces.get(item_key)
        if piece is None:
            before = dict(self.stat)
            self._current_piece = {}
            self._stamps = {}           # by id(faces): valid only inside this piece
            self._p_lo, self._p_hi = [1e9, 1e9, 1e9], [-1e9, -1e9, -1e9]
            try:
                build_items()
            finally:
                groups_by_key = {s: (meta, array("f", data_items), [array("f", b) for b in frames])
                          for s, (meta, data_items, frames) in self._current_piece.items()}
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
        self._mount(piece)

    def _mount(self, piece):
        """Adds a piece's triangles to the level's groups (copying them:
        the piece in memory stays intact for the next rebuild)."""
        groups_by_key, lo, hi, _delta = piece
        for lookup_key, ((tex_id, category, blend, spin), data_items, frames) in groups_by_key.items():
            face_group = self.face_groups.get(lookup_key)
            if face_group is None:
                face_group = self.face_groups[lookup_key] = FaceGroup(tex_id, category, blend, len(frames), spin)
            face_group.data.extend(data_items)
            for target, b in zip(face_group.frames, frames):
                target.extend(b)
        for i in range(3):
            self.lo[i] = min(self.lo[i], lo[i])
            self.hi[i] = max(self.hi[i], hi[i])

    def _add_faces(self, vertices, faces, category, *, rot=None, scale_factor=1.0, pos=(0, 0, 0), anim=None,
              spin=None, counted=True):
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
        for tex_id, blend, bare, tri_vertices in stamp:
            if bare and first_idx:
                self.stat["untextured"] += 1
            lookup_key = ((tex_id, category, blend) + ((anim[0],) if anim else ())
                       + ((spin[0],) if spin else ()))
            item = targets.get(lookup_key)
            if item is None:
                meta = (tex_id, category, blend, (pivot, spin[1]) if spin else None)
                item = targets[lookup_key] = (meta, [], [[] for _ in range(anim[2] if anim else 0)])
            target = item[2][anim[1]] if anim else item[1]
            for h, attrs in tri_vertices:
                target.extend(converted[h])
                target.extend(attrs)
            if first_idx and counted:
                self.stat["triangles"] += len(tri_vertices) // 3

    def _stamp(self, faces):
        """For each face: texture, blending, whether its texture is missing, and
        the vertices of its triangles as (vertex index, color and uv).

        A texture the level does not register does not exist: the color applies.
        The game scales the uvs by (size - 1) and samples at the texel
        center. A PSX quad is Z-ordered, not a fan: (0,1,2) and (1,3,2)."""
        output = []
        for vl in faces:
            tex_id = vl.tex_id if vl.tex_id in self.sizes else None
            bare = vl.tex_id is not None and tex_id is None
            uvs = None if bare else vl.uvs
            measure = self.sizes[tex_id] if uvs else None
            vertex_attrs = []
            for i in range(len(vl.corners)):
                r, g, b = vl.colors[i]
                u, v = geo.uv_to_texture(uvs[i][0], uvs[i][1], measure) if uvs else (0.0, 0.0)
                vertex_attrs.append((r / 255.0, g / 255.0, b / 255.0, u, v))
            tri_vertices = [(vl.corners[i], vertex_attrs[i]) for d in geo.triangles(len(vl.corners)) for i in d]
            output.append((tex_id, vl.blend, bare, tri_vertices))
        return output

    def _build(self):
        for k, t in enumerate(self.lvl["terrain"]):
            def ground_height(t=t):
                invisible_walls = []
                vertices, faces, stat = geo.read_terrain(self.sec4, t["offset"], invisible_walls)
                self._add_faces(vertices, faces, "terrain", pos=tuple(t["translation"]))
                if invisible_walls:
                    # the invisible walls (flag Invisible walls): two triangles per quad, in
                    # a separate group, semi-transparent and in a color the
                    # game does not have; off by default, as in the game
                    face_list = []
                    for a, b, c, d in invisible_walls:
                        face_list.append(geo.Face((a, b, c), None, None, [COLOR_FACES_1000] * 3, 0))
                        face_list.append(geo.Face((a, c, d), None, None, [COLOR_FACES_1000] * 3, 0))
                    self._add_faces(vertices, face_list, "faces_1000", pos=tuple(t["translation"]), counted=False)
                    self.stat["walls_drawn"] = self.stat.get("walls_drawn", 0) + len(invisible_walls)
                # walkable faces with no collision terrain below (key
                # C): a cyan copy, raised by 4 units so it does not flicker
                # on the texture (collision.no_collision_kind)
                if self.collision_blocks:
                    # no collision: bright cyan where you land safely, a faint
                    # dark cyan where the fall ends in a death/damage zone
                    sp = t["translation"]
                    kinds = {"safe": [], "trap": []}
                    for vl in faces:
                        kind = collision.no_collision_kind(
                            self.collision_blocks,
                            [tuple(vertices[h][k] + sp[k] for k in range(3)) for h in vl.corners],
                            self.trap_boxes)
                        if kind:
                            kinds[kind].append(vl)
                    for kind, category, draw_color, blend in (
                            ("safe", "no_collision", COLOR_NO_COLLISION, 0),
                            ("trap", "no_collision_trap", COLOR_NO_COLLISION_TRAP, 3)):
                        face_list = [geo.Face(vl.corners, None, None, [draw_color] * len(vl.corners), blend)
                                 for vl in kinds[kind]]
                        if face_list:
                            self._add_faces(vertices, face_list, category, pos=(sp[0], sp[1] - 4, sp[2]), counted=False)
                            self.stat[category] = self.stat.get(category, 0) + len(face_list)
                self.stat["terrain"] += len(faces)
                for item_key in ("sectors", "wall_sectors"):
                    if item_key in stat:
                        self.stat[item_key] = self.stat.get(item_key, 0) + stat[item_key]
            self._piece(("terrain_block", k), ground_height)
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
            role = self.pref["pose"].get(mid)
            self._piece(("object", n, role),
                        lambda n=n, o=o, mid=mid, role=role: self._placed_object(n, o, models[mid], role, diagonal))

        self._build_clones(models)
        self._piece(("zone",), self._death_zones)
        self._piece(("heightmap",), self._heightmap)

    def _placed_object(self, n, o, model, role, diagonal):
        """The triangles of a placed object (one piece)."""
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
        rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
        scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0

        # a prop as large as the whole level is sky or sea: it encloses the
        # scene in a dome and goes into a group that can be turned off
        span = max(max(p[k] for p in vertices) - min(p[k] for p in vertices)
                   for k in range(3)) * scale_factor / geo.UNITS_PER_METER
        category = "sky_dome" if span > 0.8 * diagonal else "props"
        self._add_collision_box(o, role, rot, scale_factor, diagonal)
        step = _spin_speed(o)
        spin = (("spin", n), step) if step else None
        # an animation that actually changes something: one group per frame
        if frames and any(b != frames[0] for b in frames[1:]):
            for f, tr in enumerate(frames):
                verts, _ids = geo.model_vertices(self.sec4, model["offset"], tr)
                self._add_faces(verts, faces, category, rot=rot, scale_factor=scale_factor,
                           pos=tuple(o["position"]), anim=(("anim", n), f, len(frames)),
                           spin=spin)
            self.stat["animated"] = self.stat.get("animated", 0) + 1
        else:
            self._add_faces(vertices, faces, category, rot=rot, scale_factor=scale_factor, pos=tuple(o["position"]),
                       spin=spin)
        if spin:
            self.stat["spinning"] = self.stat.get("spinning", 0) + 1
        self.stat["props" if category == "props" else "sky_dome"] = \
            self.stat.get("props" if category == "props" else "sky_dome", 0) + 1

    def _add_collision_box(self, o, role, rot, scale_factor, diagonal):
        """The object's collision box (flag Collision boxes), with the object's position,
        rotation and scale (montage.collision_box), as in the CTR
        viewer: sharp edges and a barely visible fill (blend
        B + F/4). The edges are degenerate triangles (a, b, b)
        drawn as lines: no diagonals. Touches neither bounds nor counters."""
        try:
            box = montage.collision_box(self.sec4, o["resources"], self.res, o, role=role)
        except Exception:  # noqa: BLE001
            return
        if not box:
            return
        x0, y0, z0, x1, y1, z1 = box
        # a box whose footprint is as large as the level (sky dome, sea)
        # would cover everything; one that is only tall (the star column of
        # L05A3C, 150 m) stays: it really is an invisible wall
        if max(abs(x1 - x0), abs(z1 - z0)) * scale_factor / geo.UNITS_PER_METER > 0.8 * diagonal:
            return
        self._add_box(box, "collision_boxes", COLOR_COLLISION_BOXES, rot=rot, scale_factor=scale_factor,
                      pos=tuple(o["position"]))
        self.stat["collision_boxes"] = self.stat.get("collision_boxes", 0) + 1

    def _add_box(self, box, category, draw_color, rot=None, scale_factor=1.0, pos=(0, 0, 0), filled=True):
        """A box as in the CTR viewer: barely visible fill
        (blend B + F/4, group `category`) and sharp edges (group
        `category + "_lines"`: degenerate triangles (a, b, b) drawn as lines, no
        diagonals). Touches neither bounds nor counters."""
        x0, y0, z0, x1, y1, z1 = box
        box_corners = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        # index = 4*ix + 2*iy + iz; each face with its 4 corners in Z order
        face_list = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 4, 5), (2, 3, 6, 7), (0, 2, 4, 6), (1, 3, 5, 7)]
        if filled:
            faces = [geo.Face(f, None, None, [draw_color] * 4, 3) for f in face_list]
            self._add_faces(box_corners, faces, category, rot=rot, scale_factor=scale_factor, pos=pos, counted=False)
        edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
                   if bin(a ^ b).count("1") == 1]          # 12: differ in one axis
        edge_faces = [geo.Face((a, b, b), None, None, [draw_color] * 3, None) for a, b in edges]
        self._add_faces(box_corners, edge_faces, category + "_lines", rot=rot, scale_factor=scale_factor, pos=pos, counted=False)

    def _object_faces(self, diagonal):
        """The faces of the placed objects in game coordinates, in their
        starting pose (no animation, no clones): what the invisible-walls
        test counts as visible besides the terrain (a gate, a fence). Sky
        domes as large as the level are left out."""
        out = []
        models = {r["id"]: r for r in self.lvl["resources"] if r["data_kind"] == "model"}
        for o in self.lvl["objects"]:
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None or models[mid]["size"] <= 12:
                continue
            try:
                role = self.pref["pose"].get(mid)
                trans = montage.transforms(self.sec4, o["resources"], self.res, o, {}, role=role)
                vertices, faces, _ = geo.read_model(self.sec4, models[mid]["offset"], trans)
            except Exception:  # noqa: BLE001
                continue
            if not faces:
                continue
            rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
            scale = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            px, py, pz = o["position"]
            pts = []
            for x, y, z in vertices:
                if rot is not None:
                    x, y, z = (rot[0][0] * x + rot[0][1] * y + rot[0][2] * z,
                               rot[1][0] * x + rot[1][1] * y + rot[1][2] * z,
                               rot[2][0] * x + rot[2][1] * y + rot[2][2] * z)
                pts.append((x * scale + px, y * scale + py, z * scale + pz))
            span = max(max(q[k] for q in pts) - min(q[k] for q in pts) for k in range(3)) / geo.UNITS_PER_METER
            if span > 0.8 * diagonal:
                continue
            out += [[pts[h] for h in vl.corners] for vl in faces]
        return out

    def _heightmap(self):
        """The overlays from the collision heightmap for the whole level:
        Ground (collision.surfaces), Hard walls and Invisible walls
        (collision.hard_walls, split by visibility) and Area boxes
        (collision.volumes)."""
        if not self.collision_blocks:
            return
        face_list = []
        for t in self.lvl["terrain"]:
            try:
                vs, vl_, _ = geo.read_terrain(self.sec4, t["offset"])
            except Exception:  # noqa: BLE001
                continue
            sp = t["translation"]
            face_list += [[tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners] for vl in vl_]
        covered, invisible, pixel = collision.surfaces(self.collision_blocks, collision.raster_faces(face_list))

        def add_planes(rects, category, draw_color, blend, lift=16):
            # 16 units over the heightmap (Y down): above the visible surface
            # it matches (median 7 units apart, finding 283), not under it
            corner_points, vl = [], []
            for x0, z0, x1, z1, y in rects:
                y -= lift
                first_idx = len(corner_points)
                corner_points += [(x0, y, z0), (x1, y, z0), (x0, y, z1), (x1, y, z1)]
                vl.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), None, None,
                                   [draw_color] * 4, blend))
            if vl:
                self._add_faces(corner_points, vl, category, counted=False)

        add_planes(covered, "covered_ground", COLOR_GROUND, 3)
        add_planes(invisible, "invisible_ground", COLOR_INVISIBLE_GROUND, 0)
        add_planes(pixel, "pixel", COLOR_PIXEL, None, lift=20)
        # a beam over every pixel, to find it from afar
        corner_points, vl = [], []
        for x0, z0, x1, z1, y in pixel:
            for (xa, za), (xb, zb) in (((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)),
                                       ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))):
                first_idx = len(corner_points)
                corner_points += [(xa, y, za), (xb, y, zb), (xa, y - 2000, za), (xb, y - 2000, zb)]
                vl.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), None, None,
                                   [COLOR_PIXEL] * 4, 0))
        if vl:
            self._add_faces(corner_points, vl, "pixel_beam", counted=False)
        # hard walls: all of them (blue), and those with nothing drawn next
        # to them, neither terrain nor objects (magenta: the invisible walls)
        lo, hi = self.terrain_lo, self.terrain_hi
        diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
        vertical_heights = collision.raster_vertical(face_list + self._object_faces(diagonal))
        panels = collision.hard_walls(self.collision_blocks, vertical_heights)
        for category, draw_color, keep_fn in (("hard_walls", COLOR_HARD_WALLS, lambda v: True),
                                      ("invisible_walls", COLOR_INVISIBLE_WALLS, lambda v: not v)):
            corner_points, vl = [], []
            for xa, za, xb, zb, base, top, visible in panels:
                if not keep_fn(visible):
                    continue
                first_idx = len(corner_points)
                corner_points += [(xa, base, za), (xb, base, zb), (xa, top, za), (xb, top, zb)]
                vl.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), None, None,
                                   [draw_color] * 4, 0))
            if vl:
                self._add_faces(corner_points, vl, category, counted=False)
            self.stat[category] = len(vl)
        # the collision volume of each mini area, as a box
        volumes = collision.volumes(self.collision_blocks)
        for x0, y0, z0, x1, y1, z1 in volumes:
            # edges only: a filled box this large would tint the whole view
            self._add_box((x0, y0, z0, x1, y1, z1), "area_boxes", COLOR_AREA_BOXES, filled=False)
        self.stat["area_boxes"] = len(volumes)
        self.stat["invisible_ground"] = len(invisible)
        self.stat["pixel"] = len(pixel)

    def _death_zones(self):
        """The zones that kill or pick up the player (zones.py): red for
        death, purple for teleport. Those at least half the size of the terrain
        footprint are the "death floor" (flag Death floor), the others the
        death zones (flag Death zones)."""
        lo, hi = self.terrain_lo, self.terrain_hi
        footprint = (hi[0] - lo[0]) * (hi[2] - lo[2]) * geo.UNITS_PER_METER ** 2
        for z in self.lvl["zones"]:
            kind_of = zones.kind_of(z)
            box = zones.zone_box(z) if kind_of else None
            if box is None:
                continue
            area = (box[3] - box[0]) * (box[5] - box[2])
            category = "death_floor" if footprint and area >= zones.FLOOR_FRACTION * footprint else "death_zones"
            self._add_box(box, category, COLOR_DEATH if kind_of == "death" else COLOR_TELEPORT)
            self.stat[category] = self.stat.get(category, 0) + 1

    def _build_clones(self, models):
        """The templates that the objects' rules make appear.

        In the game a template (block 0x08, no position) becomes visible
        when a `0x31` rule of a live object carries effect 0x100 or
        0x40000: `FUN_00448d40` clones the template whose role is field +28,
        at the object's position and with its rotation (docs finding 194). The
        lit torches, the blue chests and the falling crates work like this.

        Static version, and a declared approximation: the conditions
        are not evaluated, so what CAN appear is shown. Each pair
        (object, role) only once; the first template with the role wins,
        as in `FUN_00448d40` (finding 68).

        A clone can in turn clone (finding 279): the torch, cloned by
        a trigger, clones the flame on its own top. For a freshly born
        template only the rules of its starting step that are true at startup
        apply; at most three levels deep.
        """
        self.templates = {}
        self._idx = {}               # id(object) -> index in the level, for the keys
        for n, o in enumerate(self.lvl["objects"]):
            self._idx[id(o)] = n
            if o["block_type"] == 0x08 and o["role"] not in self.templates:
                self.templates[o["role"]] = o
        self._models = models
        seen_keys = set()
        for n, o in enumerate(self.lvl["objects"]):
            if o["block_type"] == 0x08 or not o["position"]:
                continue
            rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
            for i_rule, r in enumerate(o.get("rules", [])):
                role = r["field28"]
                if not (r["effect"] & (0x100 | 0x40000)) or role <= 0 or (n, role) in seen_keys:
                    continue
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
                    category = "clones_at_start" if _at_startup(r) else "clones"
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
        elif spr is not None:
            # a sprite: a square facing the camera, drawn every
            # frame (Viewer._draw_sprites); sizes in world units
            self.sprites.append({"pos": geo._transform((0, 0, 0), pos=pos), "category": category,
                                 "size": (spr["size"][0] / geo.UNITS_PER_METER, spr["size"][1] / geo.UNITS_PER_METER),
                                 "frames": spr["frames"], "sequence": spr["sequence"],
                                 "blend": spr["blend"]})
            self.stat["sprite"] = self.stat.get("sprite", 0) + 1
        else:
            self.stat["clones_without_model"] += 1
        if depth >= 3:
            return
        lookup_key = montage.start_key(t)
        for i_rule, r in enumerate(t.get("rules", [])):
            if (r["effect"] & (0x100 | 0x40000) and r["field28"] > 0
                    and r["key"] == lookup_key and _at_startup(r)):
                self._spawn_clone(t, r, pos, rot, category, depth + 1, route + (i_rule,))

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


# --------------------------------------------------------------- viewer

def levels_in(folder):
    """The .bze files in a folder that the viewer can open, in alphabetical
    order: loading screens (L_*, SCREEN*, LOADING) are left out, they have
    no 3D environment (check_levels.py)."""
    if not folder:
        return []
    try:
        everything = sorted((f for f in os.listdir(folder) if f.lower().endswith(".bze")), key=str.lower)
    except OSError:
        return []
    return [os.path.join(folder, f) for f in everything
            if not f.lower().startswith(("l_", "screen", "loading"))]


def resolve_levels_folder(folder):
    """The folder given by the user, or Datas/bze or bze inside it:
    the game folder works too."""
    for beneath in ("", os.path.join("Datas", "bze"), "bze"):
        c = os.path.join(folder, beneath) if beneath else folder
        if paths.has_levels(c):
            return c
    return None


class Viewer(pyglet.window.Window):
    def __init__(self, level_files, cache, index=0, screenshot=None, scale_factor=None, language=None,
                 data=None, level=None):
        """`level_files=None`: the levels are looked up (paths.find_levels_folder), in
        `data` if given, then in the folder chosen in General options, then in
        bze_levels/. Without levels the viewer starts anyway, with the background
        and the page explaining what to copy."""
        # in screenshot mode no user settings: the verification
        # screenshots must come out identical (settings.py)
        self.user_settings = settings_mod.Settings(enabled=not screenshot)
        user_settings = self.user_settings
        texts.set_language(language or user_settings["language"])
        self.build = settings_mod.build()
        super().__init__(1280, 760, resizable=True, vsync=user_settings["vsync"],
                         caption=t('title') + (f" — {self.build}" if self.build else ""))
        if level_files is None:
            self.folder = paths.find_levels_folder(data or user_settings["levels_folder"] or None)
            level_files = levels_in(self.folder)
            names = [os.path.splitext(os.path.basename(p))[0].lower() for p in level_files]
            # without a requested level (or if it is missing) no level: start
            # from the main menu over the background
            index = names.index(level.lower()) if level and level.lower() in names else None
        else:
            self.folder = os.path.dirname(level_files[0]) if level_files else None
        self.level_files = level_files
        self.cache = cache
        self.index = index
        self.current_level = None
        self.screenshot = screenshot
        self.scale_factor = scale_factor if scale_factor is not None else user_settings["texture_scale"]

        self.program = ShaderProgram(Shader(VERTEX_SHADER, "vertex"),
                                     Shader(FRAGMENT_SHADER, "fragment"))
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.05, 0.06, 0.09, 1.0)

        self.show_textures = user_settings["texture"]
        self.show_props = user_settings["props"]
        # the glitch-hunting flags: always off at every start, never saved
        for attr in set(OVERLAYS.values()):
            setattr(self, attr, False)
        self.show_sky = user_settings["sky"]
        self.albedo = user_settings["albedo"]   # factor on the vertex color of textured faces
        self.show_blending = user_settings["blending"]
        # templates that the rules make appear (key G):
        # 0 off, 1 those appearing at startup, 2 all possible ones
        self.show_clones = user_settings["clones"]
        self.wireframe = user_settings["wireframe"]
        self.fov = user_settings["field_of_view"]
        self.show_status_bar = user_settings["status_bar"]
        self.speed = 20.0
        self.held_keys = set()
        self.looking = False
        self.textures = {}
        self.anim_time = 0.0
        self.animated_textures = user_settings["animated_textures"]   # animated textures (key N)
        self.fixed_tick = None  # --tick or "initial pose": animations frozen on one tick
        self.paused = False   # P: all animations stopped where they are
        self.tps = user_settings["ticks_per_second"]  # keys - and +
        self._sprite_vao = self._sprite_vbo = None
        self.bilinear = user_settings["bilinear_filter"]   # L: bilinear filter like the PC / sharp texels
        # entity states chosen from the menu, per level: model -> role
        self.session_poses: dict[str, dict[int, int]] = {}
        self.status_bar = pyglet.text.Label("", x=10, y=8, font_name=menumod.FONT, font_size=11,
                                       color=(225, 228, 235, 255))
        self._status_background = pyglet.shapes.Rectangle(0, 0, 1, 26, color=(0, 0, 0, 150))
        # as in the CTR viewer: name and author on the main menu background
        self.signature = pyglet.text.Label(SIGNATURE, font_name=menumod.FONT, font_size=14,
                                       color=(235, 238, 245, 210),
                                       anchor_x="right", anchor_y="bottom")
        self.menu = menumod.Menu(self._build_pages())
        self._load_icon()
        self._background = self._load_background()
        if self.level_files and self.index is not None:
            self.load_level(self.level_files[self.index])
        else:
            self.index = 0
            self.menu.show(self._start_page())
        if user_settings["fullscreen"] and not screenshot:
            self.set_fullscreen(True)

        pyglet.clock.schedule_interval(self.update, 1 / 60.0)
        if screenshot:
            pyglet.clock.schedule_once(self._screenshot, 0.6)

    def _load_icon(self):
        """The window icon, `resources/icon_*.png`; if missing, the window
        keeps pyglet's."""
        folder = paths.RESOURCES_DIR
        icon_images = []
        for icon_size in (16, 32, 64, 128, 256):
            file_path = os.path.join(folder, f"icon_{icon_size}.png")
            if os.path.exists(file_path):
                icon_images.append(pyglet.image.load(file_path))
        if icon_images:
            self.set_icon(*icon_images)

    def _load_background(self):
        """The background without levels, `resources/background.png`."""
        file_path = os.path.join(paths.RESOURCES_DIR, "background.png")
        return pyglet.image.load(file_path) if os.path.exists(file_path) else None

    def _draw_background(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        self.clear()
        glClearColor(0.05, 0.06, 0.09, 1.0)
        if self._background is None:
            return
        # covers the window without distortion, centered
        k = max(self.width / self._background.width, self.height / self._background.height)
        b, h = self._background.width * k, self._background.height * k
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        self._background.blit((self.width - b) / 2, (self.height - h) / 2, width=b, height=h)

    # ---- levels folder

    def _use_levels_dir(self, folder):
        """Reads the levels from another folder; if a level is already open
        and the new folder has it too, it stays."""
        self.folder = folder
        current = (os.path.basename(self.level_files[self.index]).lower()
                   if self.current_level is not None and self.level_files else None)
        self.level_files = levels_in(folder)
        names = [os.path.basename(p).lower() for p in self.level_files]
        if current in names:
            self.index = names.index(current)
            self.menu.rebuild()
            return
        self._free_gpu()
        self.current_level = None
        self.index = 0
        self.menu.show(self._start_page())

    def _choose_levels_dir(self):
        """The Windows dialog to choose the folder; the choice is kept
        in the settings."""
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        try:
            selected = filedialog.askdirectory(parent=root, title=t("data.choose"),
                                             initialdir=self.folder or paths.APP_DIR)
        finally:
            root.destroy()
        if not selected:
            return
        folder = resolve_levels_folder(os.path.normpath(selected))
        if folder is None:
            print(t("data.no_bze", c=selected))
            return
        self.user_settings["levels_folder"] = folder
        self.user_settings.persist()
        self._use_levels_dir(folder)
        if self.current_level is not None:
            self.menu.hide()

    def _open_levels_dir(self):
        os.makedirs(paths.LEVELS_DIR, exist_ok=True)
        os.startfile(paths.LEVELS_DIR)

    def _retry(self):
        self._use_levels_dir(paths.find_levels_folder(self.user_settings["levels_folder"] or None))
        if self.current_level is not None:
            self.menu.hide()

    # -------------------------------------------------- settings and menu

    def _save_settings(self):
        """The current state into the settings: what was changed with the
        shortcut keys also persists to the next run."""
        user_settings = self.user_settings
        user_settings["language"] = texts.language()
        user_settings["texture"], user_settings["props"], user_settings["sky"] = self.show_textures, self.show_props, self.show_sky
        user_settings["blending"], user_settings["wireframe"] = self.show_blending, self.wireframe
        user_settings["animated_textures"], user_settings["clones"] = self.animated_textures, self.show_clones
        user_settings["ticks_per_second"] = float(self.tps)
        user_settings["fullscreen"], user_settings["bilinear_filter"] = self.fullscreen, self.bilinear
        user_settings["texture_scale"], user_settings["albedo"] = self.scale_factor, float(self.albedo)
        user_settings["field_of_view"], user_settings["status_bar"] = self.fov, self.show_status_bar
        user_settings.persist()

    def on_close(self):
        self._save_settings()
        super().on_close()

    def _animation_state(self):
        if self.fixed_tick is not None:
            return "pose"
        return "paused" if self.paused else "playing"

    def _set_animation_state(self, state):
        self.fixed_tick = 0 if state == "pose" else None
        self.paused = state == "paused"

    def _set_tps(self, tps):
        # animation time stays continuous: the past is rescaled
        tick = self.anim_time * self.tps
        self.tps = float(tps)
        self.anim_time = tick / self.tps

    def _set_filter(self, bilinear):
        self.bilinear = bilinear
        for name in self.textures.values():
            if name:
                glBindTexture(GL_TEXTURE_2D, name)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                                GL_LINEAR if self.bilinear else GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                                GL_LINEAR_MIPMAP_LINEAR if self.bilinear else GL_LINEAR_MIPMAP_NEAREST)

    def _set_texture_scale(self, scale_factor):
        """The textures are rebuilt at the new scale the next time they are needed."""
        self.scale_factor = scale_factor
        names = [n for n in self.textures.values() if n]
        if names:
            glDeleteTextures(len(names), (ctypes.c_uint * len(names))(*names))
        self.textures = {}

    def _group_state(self, entity_group):
        own = self.session_poses.get(self.current_level.name, {})
        default_role = preferences.for_level(self.current_level.name)["pose"].get(entity_group["model"])
        return own.get(entity_group["model"], default_role)

    def _set_group_state(self, entity_group, role):
        """A state chosen from the menu: lasts for the session, the level is rebuilt."""
        self.session_poses.setdefault(self.current_level.name, {})[entity_group["model"]] = role
        self.load_level(self.level_files[self.index], camera=False)

    def _open_level(self, i, camera=None):
        """Loads level i. With `camera` (x, y, z, yaw, pitch) it opens it from
        there: the Era selector at the center of an era. If that level is already
        open, only the camera moves."""
        if not (camera and self.current_level is not None and i == self.index):
            self.index = i
            self.load_level(self.level_files[i])
        if camera:
            x, y, z, yaw, pitch = camera
            self.pos, self.yaw, self.pitch = Vec3(x, y, z), yaw, pitch
        self.menu.hide()

    def _build_pages(self):
        M = menumod

        def resume():
            if self.current_level is None:
                self.menu.show(self._start_page())
            else:
                self.menu.hide()

        def main_items():
            resume_item = M.Action("menu.resume", resume)
            resume_item.disabled = self.current_level is None    # nothing to resume
            return [resume_item,
                    M.Submenu("menu.load", "load"),
                    M.Submenu("menu.level", "level"),
                    M.Submenu("menu.video", "video"),
                    M.Submenu("menu.general", "general"),
                    M.Submenu("menu.help", "help"),
                    M.Action("menu.quit", self.close)]

        def per_file():
            # the folder's files by name, case-insensitive (l01c, Merlin)
            return {os.path.splitext(os.path.basename(p))[0].upper(): i
                    for i, p in enumerate(self.level_files)}

        def level_item(title_text, levid, file, part_label, note, single_part, available_files, extra):
            """A menu row for a level: the part (or the title, if the
            level is in a single piece), the file on the right, the LevID below. If
            the file is not in the levels folder the row is grayed out."""
            i = available_files.get(file.upper())
            if part_label is not None:
                label_text = lambda p=part_label, n=note: t("load.part", n=p) + (f" — {n}" if n else "")
            else:
                label_text = lambda ti=title_text, n=note: ti + (f" ({n})" if n else "")
            if single_part and part_label is not None:
                label_text = lambda ti=title_text, p=part_label: f"{ti} — {t('load.part', n=p)}"
            if extra.get("label"):
                label_text = lambda e=extra["label"]: t(e)
            # the full name in the description: the label may be shortened
            entry_name = lambda ti=title_text, p=part_label, n=note, e=extra.get("label"): " — ".join(
                x for x in (ti, t(e) if e else "", t("load.part", n=p) if p is not None else "", n)
                if x)
            if levid is None:
                desc = lambda f=file, nm=entry_name: t("load.desc_variant", entry_name=nm(), file=f)
            else:
                desc = lambda f=file, n=levid, nm=entry_name: t("load.desc_level", entry_name=nm(), id=n, file=f)
            if i is None:
                desc = lambda f=file: t("load.missing", file=f)
            item = M.Action(None, lambda i=i, c=extra.get("camera"): self._open_level(i, c),
                            desc=desc, label_text=label_text,
                            right_text=lambda f=file, i=i: f + ("  ●" if i == self.index
                                                            and self.current_level is not None else ""))
            item.disabled = i is None
            return item

        def level_list(titles):
            menu_items, available_files = [], per_file()
            for title_text, title_entries in titles:
                single_part = len(title_entries) == 1
                if not single_part:
                    menu_items.append(M.Section(None, label_text=lambda ti=title_text: ti))
                for v in title_entries:
                    menu_items.append(level_item(title_text, v[0], v[1], v[2], v[3], single_part, available_files,
                                             levels.extra_of(v)))
            return menu_items

        def load_items():
            menu_items = [M.Submenu(era, f"era:{era}", desc="load.desc_era")
                    for era, _titles, _bonus in levels.ERAS]
            # Nowhere under Dimension X, opened directly
            menu_items += level_list(levels.NOWHERE)
            menu_items += [M.Section(None, label_text=lambda: ""),
                     M.Submenu("extra.title", "extra", desc="load.desc_extra"),
                     M.Back()]
            return menu_items

        def era_page(titles, bonus):
            def build_items():
                menu_items = level_list(titles)
                if bonus:
                    menu_items += [M.Section("load.bonus")] + level_list(bonus)
                return menu_items + [M.Back()]
            return build_items

        def section_pages(section_list):
            def build_items():
                menu_items = []
                for section, titles in section_list:
                    # a section with a single group of the same name (Era
                    # selector): the title only once
                    if not (len(titles) == 1 and titles[0][0] == t(section)):
                        menu_items.append(M.Section(section))
                    menu_items += level_list(titles)
                if section_list is levels.EXTRA and self.build == "Debug":
                    # only in the Debug build, for now
                    menu_items += [M.Section(None, label_text=lambda: ""),
                             M.Submenu("extra.cutscenes", "cutscenes",
                                         desc="extra.desc_cutscenes")]
                return menu_items + [M.Back()]
            return build_items

        def flags():
            """The overlays for glitch hunting."""
            def item(item_key, attr_name, desc):
                return M.YesNo(item_key, lambda: getattr(self, attr_name),
                              lambda v: setattr(self, attr_name, v), desc)
            return [item("level.invisible_walls", "show_invisible_walls", "desc.invisible_walls"),
                    item("level.no_collision", "show_no_collision", "desc.no_collision"),
                    item("level.collision_boxes", "show_collision_boxes", "desc.collision_boxes"),
                    item("level.death_zones", "show_death_zones", "desc.death_zones"),
                    item("level.death_floor", "show_death_floor", "desc.death_floor"),
                    item("level.ground", "show_ground", "desc.ground"),
                    item("level.hard_walls", "show_hard_walls", "desc.hard_walls"),
                    item("level.area_boxes", "show_area_boxes", "desc.area_boxes"),
                    item("level.faces_1000", "show_faces_1000", "desc.faces_1000"),
                    M.Back()]

        def level():
            if self.current_level is None:
                return [M.Info(lambda: t("level.no_level")), M.Back()]
            menu_items = [M.Submenu("level.flags", "flags", desc="desc.flags"),
                    M.Section("level.rendering"),
                    M.YesNo("level.texture", lambda: self.show_textures,
                           lambda v: setattr(self, "show_textures", v), "desc.texture"),
                    M.YesNo("level.props", lambda: self.show_props,
                           lambda v: setattr(self, "show_props", v), "desc.props"),
                    M.YesNo("level.sky", lambda: self.show_sky,
                           lambda v: setattr(self, "show_sky", v), "desc.sky"),
                    M.YesNo("level.blending", lambda: self.show_blending,
                           lambda v: setattr(self, "show_blending", v), "desc.blending"),
                    M.YesNo("level.wireframe", lambda: self.wireframe,
                           lambda v: setattr(self, "wireframe", v), "desc.wireframe"),
                    M.Section("level.entities"),
                    M.Choice("level.animations",
                             [("playing", "level.anim.playing"), ("paused", "level.anim.paused"),
                              ("pose", "level.anim.pose")],
                             self._animation_state, self._set_animation_state, "desc.animations"),
                    M.Number("level.tps", lambda: self.tps, self._set_tps, 1, 60,
                             desc="desc.tps"),
                    M.YesNo("level.texanim", lambda: self.animated_textures,
                           lambda v: setattr(self, "animated_textures", v), "desc.texanim"),
                    M.Choice("level.clones",
                             [(0, "level.clones.off"), (1, "level.clones.at_start"),
                              (2, "level.clones.all")],
                             lambda: self.show_clones, lambda v: setattr(self, "show_clones", v),
                             "desc.clones")]
            for entity_group in self.current_level.pref["entity_groups"]:
                menu_items.append(M.Choice(f"group.{entity_group['name']}",
                                     [(role, f"state.{name}") for role, name in entity_group["states"]],
                                     lambda g=entity_group: self._group_state(g),
                                     lambda role, g=entity_group: self._set_group_state(g, role),
                                     "desc.group"))
            menu_items.append(M.Back())
            return menu_items

        def video():
            return [M.YesNo("video.fullscreen", lambda: self.fullscreen,
                           lambda v: self.set_fullscreen(v), "desc.fullscreen"),
                    M.YesNo("video.vsync", lambda: self.user_settings["vsync"], self._toggle_vsync),
                    M.YesNo("video.filter", lambda: self.bilinear, self._set_filter, "desc.filter"),
                    M.Choice("video.scale", [(n, lambda n=n: f"x{n}") for n in (1, 2, 3, 4)],
                             lambda: self.scale_factor, self._set_texture_scale, "desc.scale"),
                    M.Choice("video.color", [(1.0, "video.color.pc"), (2.0, "video.color.psx")],
                             lambda: self.albedo, lambda v: setattr(self, "albedo", v),
                             "desc.color"),
                    M.Number("video.fov", lambda: self.fov, lambda v: setattr(self, "fov", v),
                             40, 100, increment=5, number_format="{:.0f}°"),
                    M.Back()]

        def general_items():
            return [M.Choice("general.language",
                             [(c, lambda c=c: texts.LANGUAGE_NAMES[c]) for c in texts.LANGUAGES],
                             texts.language, self._set_language, "desc.language"),
                    M.YesNo("general.status_bar", lambda: self.show_status_bar,
                           lambda v: setattr(self, "show_status_bar", v), "desc.status_bar"),
                    M.Action("general.folder", self._choose_levels_dir,
                             desc=lambda: t("general.desc_folder", c=self.folder or "—"),
                             right_text=lambda: os.path.basename(self.folder or "") or "—"),
                    M.Action("data.open", self._open_levels_dir, desc="data.desc_open"),
                    M.Back()]

        def data_items():
            # the screen without levels: what to copy and where
            return [M.Info(lambda: t("data.line1")),
                    M.Info(lambda: t("data.line2")),
                    M.Info(lambda: t("data.line3")),
                    M.Info(lambda: t("data.line4")),
                    M.Section(None, label_text=lambda: ""),
                    M.Action("data.open", self._open_levels_dir, desc="data.desc_open"),
                    M.Action("data.choose", self._choose_levels_dir, desc="data.desc_choose"),
                    M.Action("data.retry", self._retry, desc="data.desc_retry"),
                    M.Submenu("menu.general", "general"),
                    M.Action("menu.quit", self.close)]

        def help_items():
            # (key, or text key of its name; text key of the function)
            lines = [("W A S D", "help.move"), ("Q / E", "help.up_down"),
                     ("help.k.mouse", "help.look"), ("help.k.wheel", "help.wheel"),
                     ("Shift / Ctrl", "help.shift"), ("Esc", "help.menu"),
                     ("help.k.nav", "help.menu_nav"), ("Backspace / M", "help.back"),
                     ("[  ]", "help.levels"), ("R", "help.reset"),
                     ("T", "level.texture"), ("O", "level.props"), ("H", "level.sky"),
                     ("M", "level.blending"), ("F", "level.wireframe"),
                     ("N", "level.texanim"), ("G", "level.clones"), ("P", "help.pause"),
                     ("- / +", "help.tps"), ("L", "video.filter"), ("help.k.alt", "help.fullscreen")]
            return ([M.Info(lambda k=k: t(k), lambda c=c: t(c)) for k, c in lines]
                    + [M.Back()])


        return {
            # as in the CTR viewer: name and author on the main page
            "main": M.Page(lambda: t("menu.main"), main_items, 360),
            "load": M.Page(lambda: t("load.title"), load_items, 360),
            "extra": M.Page(lambda: t("extra.title"), section_pages(levels.EXTRA), 720),
            "cutscenes": M.Page(lambda: t("extra.cutscenes"), section_pages(levels.CUTSCENES), 720),
            **{f"era:{era}": M.Page(lambda era=era: t(era), era_page(titles, bonus), 720)
               for era, titles, bonus in levels.ERAS},
            "level": M.Page(lambda: t("level.title",
                                          n=self.current_level.name if self.current_level else "—"), level),
            "flags": M.Page(lambda: t("level.flags"), flags, 440),
            "missing_data": M.Page(lambda: t("data.title"), data_items, 640),
            "video": M.Page(lambda: t("video.title"), video),
            "general": M.Page(lambda: t("general.title"), general_items),
            "help": M.Page(lambda: t("help.title"), help_items, 520),
        }

    def _toggle_vsync(self, v):
        self.user_settings["vsync"] = v
        self.set_vsync(v)

    def _set_language(self, language):
        texts.set_language(language)
        self.set_caption(t('title') + (f" — {self.build}" if self.build else ""))
        self.menu.rebuild()

    # -------------------------------------------------- gpu

    def tick(self) -> int:
        """The animation tick: frozen with P or with --tick."""
        if self.fixed_tick is not None:
            return self.fixed_tick
        return int(self.anim_time * self.tps)

    def _gl_texture(self, tid):
        table = self.current_level.table
        # an animated slot (finding 275) changes frame over time
        source = table.bitmap(tid, self.tick()) if table and self.animated_textures else None
        if source is None:
            source = table.get(tid) if table else None
        if source is None:
            tex = next((t for t in self.current_level.lvl["textures"] if t["id"] == tid), None)
            source = (self.current_level.sec3, tex["offset"]) if tex else None
        if source is None:
            return None
        # the cache is per source, not per slot: several slots and several frames
        # can point to the same TIM
        lookup_key = (id(source[0]), source[1])
        if lookup_key in self.textures:
            return self.textures[lookup_key]
        try:
            b, h, rgba = tim.read_tim(source[0], source[1])
            if self.scale_factor != 1:
                b, h, rgba = upscale.enlarge((b, h, rgba), self.scale_factor)
        except Exception:  # noqa: BLE001
            self.textures[lookup_key] = None
            return None
        name = ctypes.c_uint()
        glGenTextures(1, ctypes.byref(name))
        glBindTexture(GL_TEXTURE_2D, name.value)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
                        GL_LINEAR_MIPMAP_LINEAR if self.bilinear else GL_LINEAR_MIPMAP_NEAREST)
        # the PC filters textures bilinearly (screenshots of the PC game):
        # like the PC by default, key L for sharp texels
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR if self.bilinear else GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        buf = (ctypes.c_ubyte * len(rgba)).from_buffer_copy(rgba)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, b, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buf)
        glGenerateMipmap(GL_TEXTURE_2D)
        self.textures[lookup_key] = name.value
        return name.value

    def _upload(self, face_group: FaceGroup):
        """A group goes to the graphics card in a single buffer. For an animated
        object all frames sit in a row in the same buffer and the current
        frame's range is drawn: before, it was one buffer per
        frame, 8660 on L03A, 1.6 s just to create them."""
        if face_group.frames:
            combined, ranges = array("f"), []
            for data in face_group.frames:
                ranges.append((len(combined) // 8, len(data) // 8))
                combined.extend(data)
            face_group.data = combined
            self._upload_one(face_group)
            face_group.vaos = [(face_group.vao, face_group.vbo, first_idx, n) for first_idx, n in ranges]
            face_group.frames = []
            return
        self._upload_one(face_group)

    def _upload_one(self, face_group: FaceGroup):
        vao = ctypes.c_uint()
        vbo = ctypes.c_uint()
        glGenVertexArrays(1, ctypes.byref(vao))
        glGenBuffers(1, ctypes.byref(vbo))
        glBindVertexArray(vao.value)
        glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
        # the array is passed as is: no element-by-element copy
        address, n = face_group.data.buffer_info()
        glBufferData(GL_ARRAY_BUFFER, n * 4, ctypes.c_void_p(address) if n else None, GL_STATIC_DRAW)
        step = 8 * 4
        for name, measure, offset in (("position", 3, 0), ("color", 3, 12), ("uv", 2, 24)):
            place = self.program.attributes[name]["location"]
            glEnableVertexAttribArray(place)
            glVertexAttribPointer(place, measure, GL_FLOAT, False, step, ctypes.c_void_p(offset))
        glBindVertexArray(0)
        face_group.vao, face_group.vbo, face_group.item_count = vao.value, vbo.value, len(face_group.data) // 8
        face_group.data = array("f")

    # -------------------------------------------------- level

    def _free_gpu(self, texture=True):
        """Buffers (and textures) of the previous level: without this, every
        level or state change from the menu left video memory occupied. The
        textures stay when the same level is rebuilt."""
        if getattr(self, "current_level", None) is None:
            return
        vaos, vbos = set(), set()
        for face_group in self.current_level.face_groups.values():
            if face_group.vao:
                vaos.add(face_group.vao)
                vbos.add(face_group.vbo)
        if vaos:
            glDeleteVertexArrays(len(vaos), (ctypes.c_uint * len(vaos))(*vaos))
            glDeleteBuffers(len(vbos), (ctypes.c_uint * len(vbos))(*vbos))
        if texture:
            self._set_texture_scale(self.scale_factor)

    def load_level(self, file_path, camera=True):
        """Loads a level. `camera=False` leaves the camera where it is: used when
        the same level is rebuilt for a state chosen from the menu.

        The same level is rebuilt with the pieces already built and the same
        textures: only what the chosen state changes is redone."""
        name = os.path.splitext(os.path.basename(file_path))[0]
        same_level = self.current_level is not None and self.current_level.name == name
        self._free_gpu(texture=not same_level)
        if not same_level:
            self.textures = {}
            # the piece memory holds one level only: RAM does not grow;
            # those built in the past come back from disk (level_cache.py)
            self._signature = level_cache.signature(file_path)
            self._pieces = level_cache.fetch(self.cache, name, self._signature) or {}
            self._texture_table = texmod.construct(os.path.dirname(file_path), name, self.cache)
        n_known = len(self._pieces)
        self.current_level = Level(file_path, self.cache, self._texture_table, self.session_poses.get(name), self._pieces)
        if len(self._pieces) > n_known:
            level_cache.store(self.cache, name, self._signature, self._pieces)
        for face_group in self.current_level.face_groups.values():
            self._upload(face_group)
        self.lo, self.hi = self.current_level.bounds()
        lo, hi = self.current_level.terrain_lo, self.current_level.terrain_hi
        if camera:
            self.reset_camera()
        print(f"{self.current_level.name}: {self.current_level.stat['triangles']} triangles, "
              f"{self.current_level.stat['props']} props ({self.current_level.stat.get('animated', 0)} animated) + {self.current_level.stat['sky_dome']} sky, "
              f"{len(self.current_level.face_groups)} groups, "
              f"{len(self.current_level.sizes)} texture, "
              f"{hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} m")

    def reset_camera(self):
        lo, hi = self.current_level.terrain_lo, self.current_level.terrain_hi
        mid = [(a + b) / 2 for a, b in zip(lo, hi)]
        radius = max(hi[i] - lo[i] for i in range(3)) or 10.0
        self.pos = Vec3(mid[0], mid[1] + radius * 0.35, mid[2] + radius * 0.75)
        self.yaw, self.pitch = -90.0, -22.0
        self.speed = max(8.0, radius / 12.0)

    # -------------------------------------------------- input

    def on_key_press(self, symbol, modifiers):
        if self.screenshot:
            return      # screenshot mode: see update
        k = pyglet.window.key
        if symbol == k.ESCAPE:
            # as in the CTR viewer: Esc opens and closes the menu, Exit quits
            if self.current_level is None:
                self.menu.show(self._start_page())    # without a level the menu stays
            elif self.menu.is_open:
                self.menu.hide()
                self._save_settings()
            else:
                self.held_keys.clear()
                if self.menu.stack and self.menu.stack[0][0] == "missing_data":
                    self.menu.show()      # from the no-levels screen to the main page
                else:
                    self.menu.reopen()      # where it was left
            return pyglet.event.EVENT_HANDLED    # pyglet would close the window
        if symbol in (k.ENTER, k.NUM_ENTER) and modifiers & k.MOD_ALT:
            self.set_fullscreen(not self.fullscreen)
            return
        if self.menu.press(symbol, modifiers) or self.current_level is None:
            return
        if symbol == k.T:
            self.show_textures = not self.show_textures
        elif symbol == k.F:
            self.wireframe = not self.wireframe
        elif symbol == k.O:
            self.show_props = not self.show_props
        elif symbol == k.H:
            self.show_sky = not self.show_sky
        elif symbol == k.M:
            self.show_blending = not self.show_blending
        elif symbol == k.G:
            self.show_clones = (self.show_clones + 1) % 3
        elif symbol == k.N:
            self.animated_textures = not self.animated_textures
        elif symbol == k.L:
            self._set_filter(not self.bilinear)
        elif symbol == k.P:
            self.fixed_tick = None
            self.paused = not self.paused
        elif symbol in (k.MINUS, k.NUM_SUBTRACT, k.EQUAL, k.PLUS, k.NUM_ADD):
            step = -1.0 if symbol in (k.MINUS, k.NUM_SUBTRACT) else 1.0
            self._set_tps(max(1.0, min(60.0, self.tps + step)))
        elif symbol == k.R:
            self.reset_camera()
        elif symbol in (k.BRACKETLEFT, k.BRACKETRIGHT):
            step = -1 if symbol == k.BRACKETLEFT else 1
            self.index = (self.index + step) % len(self.level_files)
            self.load_level(self.level_files[self.index])
        else:
            self.held_keys.add(symbol)

    def on_key_release(self, symbol, modifiers):
        self.held_keys.discard(symbol)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.screenshot or self.menu.click(x, y, button):
            return
        if button == pyglet.window.mouse.RIGHT:
            self.looking = True
            self.set_exclusive_mouse(True)

    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.RIGHT and self.looking:
            self.looking = False
            self.set_exclusive_mouse(False)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.screenshot or self.menu.mouse_over(x, y):
            return
        if self.looking:
            self.yaw += dx * 0.15
            self.pitch = max(-89.0, min(89.0, self.pitch + dy * 0.15))

    on_mouse_drag = lambda self, x, y, dx, dy, b, m: self.on_mouse_motion(x, y, dx, dy)  # noqa: E731

    def on_mouse_scroll(self, x, y, sx, sy):
        if self.screenshot or self.menu.wheel(x, y, sy):
            return
        self.speed = max(1.0, self.speed * (1.2 if sy > 0 else 1 / 1.2))

    def on_deactivate(self):
        """Out of focus (for example while switching to an emulator): no keys
        left held down and no mouse look, as in the CTR viewer."""
        self.held_keys.clear()
        if self.looking:
            self.looking = False
            self.set_exclusive_mouse(False)

    def update(self, dt):
        if not self.paused:
            self.anim_time += dt
        if self.screenshot:
            # in screenshot mode the window can steal focus from another
            # instance: keys pressed there would move this camera
            return
        if self.menu.is_open or self.current_level is None:
            return      # with the menu open (or no level) the camera stays still
        k = pyglet.window.key
        move_speed = self.speed * dt
        if k.LSHIFT in self.held_keys or k.RSHIFT in self.held_keys:
            move_speed *= 5
        if k.LCTRL in self.held_keys:
            move_speed *= 0.2
        j, p = math.radians(self.yaw), math.radians(self.pitch)
        forward = Vec3(math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        right_vec = Vec3(-math.sin(j), 0.0, math.cos(j))
        movement = Vec3(0.0, 0.0, 0.0)
        if k.W in self.held_keys:
            movement += forward
        if k.S in self.held_keys:
            movement -= forward
        if k.D in self.held_keys:
            movement += right_vec
        if k.A in self.held_keys:
            movement -= right_vec
        if k.E in self.held_keys:
            movement += Vec3(0.0, 1.0, 0.0)
        if k.Q in self.held_keys:
            movement -= Vec3(0.0, 1.0, 0.0)
        if movement.length() > 0:
            self.pos += movement.normalize() * move_speed

    # -------------------------------------------------- drawing

    def on_draw(self):
        if self.current_level is None:
            # no level: the Dimension X space and the menu, always open
            self._draw_background()
            if not self.menu.is_open:
                self.menu.show(self._start_page())
            self._draw_signature()
            self.menu.draw_menu(self)
            return
        self.clear()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # pyglet's HUD, when drawing text, TURNS OFF blending at the end
        # (pyglet/text/layout/base.py): re-enabled only once at startup,
        # from the second frame on every semi-transparent face came out opaque —
        # the plants' shadows were black squares (finding 273)
        glEnable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)

        j, p = math.radians(self.yaw), math.radians(self.pitch)
        forward = Vec3(math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        far_plane = max(self.hi[i] - self.lo[i] for i in range(3)) * 4 + 100
        proj = Mat4.perspective_projection(self.width / self.height, 0.1, far_plane, float(self.fov))
        view = Mat4.look_at(self.pos, self.pos + forward, Vec3(0.0, 1.0, 0.0))

        self.program.use()
        self.program["mvp"] = proj @ view
        self.program["show_textures"] = 1 if self.show_textures else 0
        self.program["albedo"] = self.albedo
        drawn_triangles = 0
        # rule passes so far, for the rotating objects (280)
        if self.fixed_tick is not None:
            rule_passes = self.fixed_tick * RULE_PASSES_PER_TICK
        else:
            rule_passes = self.anim_time * self.tps * RULE_PASSES_PER_TICK

        visible_groups = [g for g in self.current_level.face_groups.values()
                     if not (g.category == "props" and not self.show_props)
                     and not (g.category in OVERLAYS and not getattr(self, OVERLAYS[g.category]))
                     and not (g.category == "clones" and self.show_clones < 2)
                     and not (g.category == "clones_at_start" and self.show_clones < 1)
                     and g.category != "sky_dome"]

        def draw_face_group(face_group):
            tex = self._gl_texture(face_group.tex_id) if face_group.tex_id is not None else None
            self.program["has_texture"] = 1 if tex else 0
            glBindTexture(GL_TEXTURE_2D, tex or 0)
            if face_group.vaos:
                vao, _vbo, first_idx, item_count = face_group.vaos[self.tick() % len(face_group.vaos)]
            else:
                vao, first_idx, item_count = face_group.vao, 0, face_group.item_count
            if face_group.spin:
                # the game's Y rotation, around the vertical through the object's
                # point; the direction flips with the axes (x, -y, -z)
                pivot, step = face_group.spin
                angle = -step * rule_passes * 2 * math.pi / 4096.0
                p = Vec3(*pivot)
                self.program["mvp"] = (proj @ view @ Mat4.from_translation(p)
                                       @ Mat4.from_rotation(angle, Vec3(0.0, 1.0, 0.0))
                                       @ Mat4.from_translation(-p))
            glBindVertexArray(vao)
            if face_group.category.endswith("_lines"):
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glDrawArrays(GL_TRIANGLES, first_idx, item_count)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe else GL_FILL)
            else:
                glDrawArrays(GL_TRIANGLES, first_idx, item_count)
            if face_group.spin:
                self.program["mvp"] = proj @ view
            return item_count // 3

        def set_blend(blend):
            """The four PlayStation blend modes (docs MODELFORMAT 5b)."""
            if blend is None:
                glBlendEquation(GL_FUNC_ADD)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                self.program["alpha"], self.program["blend_scale"] = 1.0, 1.0
            elif blend == 0:      # B/2 + F/2
                glBlendEquation(GL_FUNC_ADD)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                self.program["alpha"], self.program["blend_scale"] = 0.5, 1.0
            elif blend == 1:      # B + F
                glBlendEquation(GL_FUNC_ADD)
                glBlendFunc(GL_ONE, GL_ONE)
                self.program["alpha"], self.program["blend_scale"] = 1.0, 1.0
            elif blend == 2:      # B - F
                # the shadows (palms, crates) are subtractive: with the PC's
                # factor 1 (268, measured on opaque faces) they came out almost
                # invisible. Factor 2 like the PSX (neutral color 128): tuned by eye
                # on screenshots of the PC game, not measured
                glBlendEquation(GL_FUNC_REVERSE_SUBTRACT)
                glBlendFunc(GL_ONE, GL_ONE)
                self.program["alpha"], self.program["blend_scale"] = 1.0, 2.0
            else:                # B + F/4
                glBlendEquation(GL_FUNC_ADD)
                glBlendFunc(GL_ONE, GL_ONE)
                self.program["alpha"], self.program["blend_scale"] = 1.0, 0.25

        # the sky dome follows the camera: it is centered on the level's
        # origin (object 0 of L03A, model 1, 367 x 245 x 367 m) and drawn
        # fixed at the origin it leaves the starting point on its edge. It goes
        # first and without depth, so everything else passes in front of it.
        if self.show_sky:
            self.program["mvp"] = proj @ view @ Mat4.from_translation(self.pos)
            glDepthMask(GL_FALSE)
            for face_group in self.current_level.face_groups.values():
                if face_group.category == "sky_dome":
                    set_blend(face_group.blend if self.show_blending else None)
                    drawn_triangles += draw_face_group(face_group)
            glDepthMask(GL_TRUE)
            self.program["mvp"] = proj @ view

        # opaque ones first, with depth writes
        set_blend(None)
        for face_group in visible_groups:
            if face_group.blend is None:
                drawn_triangles += draw_face_group(face_group)

        drawn_triangles += self._draw_sprites(forward, set_blend)
        set_blend(None)

        # then the semi-transparent ones, without writing depth
        if self.show_blending:
            glDepthMask(GL_FALSE)
            for face_group in visible_groups:
                if face_group.blend is not None:
                    set_blend(face_group.blend)
                    drawn_triangles += draw_face_group(face_group)
            set_blend(None)
            glDepthMask(GL_TRUE)
        else:
            for face_group in visible_groups:
                if face_group.blend is not None:
                    drawn_triangles += draw_face_group(face_group)

        glBindVertexArray(0)
        self.program.stop()

        # status bar and menu without depth test: the letter quads
        # overlap and with the test on they would discard each other
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_DEPTH_TEST)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.drawn_triangles = drawn_triangles
        if self.show_status_bar:
            self._draw_status_bar()
        if self.menu.is_open and self.menu.stack and self.menu.stack[-1][0] == "main":
            self._draw_signature()
        self.menu.draw_menu(self)
        glEnable(GL_DEPTH_TEST)

    def _start_page(self):
        """The page with no level open: the main menu if there are
        levels to load, otherwise the one explaining what to copy."""
        return "main" if self.level_files else "missing_data"

    def _draw_signature(self):
        """Bottom right, above the status bar."""
        s = max(0.75, min(1.6, self.height / 760.0))
        self.signature.font_size = 14 * s
        status_bar = round(26 * s) if (self.current_level is not None and self.show_status_bar) else 0
        self.signature.x, self.signature.y = self.width - round(16 * s), status_bar + round(12 * s)
        glEnable(GL_BLEND)
        self.signature.draw()
        self.signature_drawn = True    # for test_menu.py

    def _draw_status_bar(self):
        """Level, position in game units and in meters, speed, animation
        state: what is always needed, glitch hunting included."""
        x, y, z = self.pos.x, self.pos.y, self.pos.z
        # the viewer uses (x, -y, -z) in meters, 128 units = 1 meter (VIEWER.md)
        gx, gy, gz = x * geo.UNITS_PER_METER, -y * geo.UNITS_PER_METER, -z * geo.UNITS_PER_METER
        pieces = [self.current_level.name,
                 f"{t('status.game')} {gx:.0f}, {gy:.0f}, {gz:.0f}",
                 f"m {x:.1f} {y:.1f} {z:.1f}",
                 t("status.speed", v=self.speed),
                 f"{self.drawn_triangles} tri"]
        state = self._animation_state()
        if state != "playing":
            pieces.append(t("status.paused") if state == "paused" else t("status.pose"))
        pieces.append(t("status.menu"))
        s = max(0.75, min(1.6, self.height / 760.0))
        self.status_bar.font_size = 11 * s
        self.status_bar.x, self.status_bar.y = round(10 * s), round(7 * s)
        self.status_bar.text = "   ·   ".join(pieces)
        self._status_background.width, self._status_background.height = self.width, round(26 * s)
        glEnable(GL_BLEND)
        self._status_background.draw()
        self.status_bar.draw()

    def _draw_sprites(self, forward, set_blend):
        """The sprites (torch flames, ...) as squares facing the camera."""
        visible_groups = [sp for sp in self.current_level.sprites
                     if not (sp["category"] == "clones" and self.show_clones < 2)
                     and not (sp["category"] == "clones_at_start" and self.show_clones < 1)]
        if not visible_groups:
            return 0
        if self._sprite_vao is None:
            vao, vbo = ctypes.c_uint(), ctypes.c_uint()
            glGenVertexArrays(1, ctypes.byref(vao))
            glGenBuffers(1, ctypes.byref(vbo))
            glBindVertexArray(vao.value)
            glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
            for name, measure, offset in (("position", 3, 0), ("color", 3, 12), ("uv", 2, 24)):
                place = self.program.attributes[name]["location"]
                glEnableVertexAttribArray(place)
                glVertexAttribPointer(place, measure, GL_FLOAT, False, 32, ctypes.c_void_p(offset))
            self._sprite_vao, self._sprite_vbo = vao.value, vbo.value
        right_vec = forward.cross(Vec3(0.0, 1.0, 0.0)).normalize()
        op = right_vec.cross(forward).normalize()
        glBindVertexArray(self._sprite_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._sprite_vbo)
        glDepthMask(GL_FALSE)
        n = 0
        for sp in visible_groups:
            set_blend(sp["blend"] if self.show_blending else None)
            f = self.current_level.sprite_frame(sp, self.tick())
            tex = self._gl_texture(f)
            self.program["has_texture"] = 1 if tex else 0
            glBindTexture(GL_TEXTURE_2D, tex or 0)
            # the sprite RESTS on the attachment point, it is not centered on it:
            # the torch flame in the game sits above the top (observed in the
            # game; record 0x64 carries no origin)
            c = Vec3(*sp["pos"])
            b, h = sp["size"][0] / 2, sp["size"][1]
            corners = [c - right_vec * b, c + right_vec * b,
                      c - right_vec * b + op * h, c + right_vec * b + op * h]
            uvs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
            data = []
            for i in (0, 1, 2, 1, 3, 2):
                p = corners[i]
                data += [p.x, p.y, p.z, 1.0, 1.0, 1.0, uvs[i][0], uvs[i][1]]
            arr = (ctypes.c_float * len(data))(*data)
            glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(arr), arr, GL_DYNAMIC_DRAW)
            glDrawArrays(GL_TRIANGLES, 0, 6)
            n += 2
        glDepthMask(GL_TRUE)
        return n

    def _screenshot(self, dt):
        pyglet.image.get_buffer_manager().get_color_buffer().save(self.screenshot)
        print(f"screenshot written to {self.screenshot}")
        self.close()


def main() -> None:
    p = argparse.ArgumentParser(description="level viewer")
    p.add_argument("level", nargs="?", help="level to open (without: the main menu)")
    p.add_argument("--data", help="folder of the .bze files (if missing: the one in the settings, "
                                   "bze_levels/, then the BBLIT_DATA game folder)")
    p.add_argument("--cache", default=os.path.join(paths.APP_DIR, "extracted"))
    p.add_argument("--screenshot", help="write a PNG and exit")
    p.add_argument("--camera", help="fixed framing: x,y,z,yaw,pitch")
    p.add_argument("--no-blend", action="store_true", help="draw semi-transparent faces as opaque")
    p.add_argument("--sky", action="store_true", help="show the sky dome")
    p.add_argument("--invisible-walls", action="store_true", help="show the invisible walls")
    p.add_argument("--nocollision", action="store_true",
                   help="show the faces without collision")
    p.add_argument("--boxes", action="store_true", help="show the collision boxes")
    p.add_argument("--deathzones", action="store_true", help="show the death zones")
    p.add_argument("--deathfloor", action="store_true", help="show the death floor")
    p.add_argument("--ground", action="store_true", help="show the collision ground")
    p.add_argument("--hardwalls", action="store_true", help="show the heightmap's hard walls")
    p.add_argument("--areaboxes", action="store_true", help="show the area boxes")
    p.add_argument("--faces1000", action="store_true", help="show the 0x1000 terrain faces")
    p.add_argument("--clones", type=int, choices=(0, 1, 2),
                   help="cloned templates: 0 off, 1 at startup, 2 all (key G)")
    p.add_argument("--albedo", type=float, help="texture x vertex color factor (default 1; 2 is the PlayStation)")
    p.add_argument("--tick", type=int, help="freeze all animations on this tick (for screenshots)")
    p.add_argument("--tps", type=float, help="animation ticks per second (default 15, measured on the PSX)")
    p.add_argument("--scale-factor", type=int,
                   help="upscale the textures with scale2x/scale3x: 1, 2, 3, 4, 6 or 8")
    p.add_argument("--language", choices=texts.LANGUAGES, help="interface language")
    p.add_argument("--menu", help="open a menu page at startup (main, load, level, flags, video, "
                                  "general, help, extra): for verification screenshots")
    args = p.parse_args()

    v = Viewer(None, args.cache, screenshot=args.screenshot, scale_factor=args.scale_factor, language=args.language,
               data=args.data, level=args.level)
    if args.menu:
        v.menu.show("main")
        if args.menu != "main":
            v.menu.open_page(args.menu)
    if args.no_blend:
        v.show_blending = False
    if args.sky:
        v.show_sky = True
    if args.invisible_walls:
        v.show_invisible_walls = True
    if args.nocollision:
        v.show_no_collision = True
    if args.boxes:
        v.show_collision_boxes = True
    if args.deathzones:
        v.show_death_zones = True
    if args.deathfloor:
        v.show_death_floor = True
    if args.ground:
        v.show_ground = True
    if args.hardwalls:
        v.show_hard_walls = True
    if args.areaboxes:
        v.show_area_boxes = True
    if args.faces1000:
        v.show_faces_1000 = True
    if args.clones is not None:
        v.show_clones = args.clones
    if args.albedo is not None:
        v.albedo = args.albedo
    if args.tick is not None:
        v.fixed_tick = args.tick
    if args.tps:
        v.tps = args.tps
    if args.camera:
        x, y, z, yaw, pitch = (float(w) for w in args.camera.split(","))
        v.pos, v.yaw, v.pitch = Vec3(x, y, z), yaw, pitch
    pyglet.app.run()


def main_guarded() -> None:
    """For the console-less executable: an error ends up in errors.txt next
    to the viewer and in a message box, instead of vanishing (like the
    fatal_errors.txt of the CTR viewer)."""
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback
        label_text = traceback.format_exc()
        file_path = os.path.join(paths.APP_DIR, "errors.txt")
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(label_text + "\n")
        except OSError:
            pass
        if paths.IS_FROZEN:
            ctypes.windll.user32.MessageBoxW(None, label_text[-1500:], "BBLIT Viewer", 0x10)
        raise


if __name__ == "__main__":
    main_guarded()
