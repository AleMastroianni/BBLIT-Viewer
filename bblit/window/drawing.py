"""What the viewer draws every frame: the shaders, the textures on the
graphics card, the frame itself (scene, sprites, status bar) and the
screenshots.

`Drawing` is the drawing part of the viewer window (`app.Viewer` inherits
it).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ctypes  # noqa: E402
import math  # noqa: E402
from array import array  # noqa: E402

import pyglet  # noqa: E402

# pyglet checks for errors after EVERY OpenGL call: loading L03A meant
# 104 thousand checks, 0.9 s. It is only useful for debugging rendering, and must
# be turned off before importing pyglet.gl (menu.py imports it too).
pyglet.options["debug_gl"] = False

from game import geometry as geo  # noqa: E402
from ui import flag_labels  # noqa: E402
from support import paths  # noqa: E402
from game import tim  # noqa: E402
from support import upscale  # noqa: E402
from window.overlays import (BOX_ALPHA, BOX_BLEND, LABEL_HEIGHT, LABEL_NEAR,  # noqa: E402
                             LINK_WIDTH, ONE_SIDED, OVERLAYS, OVERLAY_BLEND,
                             PULLED_FORWARD, THICK_LINES, THICK_LINE_WIDTH, THROUGH_WALLS,
                             WALL_ALPHA, WALL_BLEND)
from window.scene import FaceGroup, RULE_PASSES_PER_TICK  # noqa: E402
from ui.texts import t  # noqa: E402

from pyglet.gl import (  # noqa: E402
    GL_ARRAY_BUFFER, GL_BACK, GL_BLEND, GL_CLAMP_TO_EDGE, GL_COLOR_BUFFER_BIT, GL_CULL_FACE, GL_REPEAT,
    GL_DEPTH_BUFFER_BIT, GL_DEPTH_TEST, GL_FILL, GL_FLOAT, GL_FRONT_AND_BACK, GL_LINE,
    GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_NEAREST, GL_NEAREST, GL_ONE_MINUS_SRC_ALPHA, GL_RGBA, GL_SRC_ALPHA,
    GL_DEPTH_TEST, GL_DYNAMIC_DRAW, GL_FALSE, GL_FUNC_ADD, GL_STATIC_DRAW, GL_TRUE,
    GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER, GL_POLYGON_OFFSET_FILL, GL_POLYGON_OFFSET_LINE, glPolygonOffset,
    GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, GL_TRIANGLES, GL_UNSIGNED_BYTE, glBindBuffer,
    glBindTexture, glBindVertexArray, glBlendFunc, glBufferData, glBufferSubData, glClear, glClearColor,
    glDisable, glDrawArrays, glEnable, glEnableVertexAttribArray, glGenBuffers, glGenTextures,
    glBlendEquation, glDeleteBuffers, glDeleteVertexArrays, glDepthFunc, glDepthMask, GL_LEQUAL, GL_LESS,
    glCullFace, glGenVertexArrays, glGenerateMipmap, glLineWidth, glPolygonMode,
    glTexImage2D, glTexParameteri,
    glVertexAttribPointer,
    GL_STENCIL_BUFFER_BIT, GL_STENCIL_TEST, GL_NOTEQUAL, GL_KEEP, GL_REPLACE,
    glStencilFunc, glStencilOp, glStencilMask,
)
from pyglet.math import Mat4, Vec3  # noqa: E402

# Level options -> Wireframe: off, Skeleton (lines only), Grid (textures and
# the triangle edges over them, as in the CTR viewer)
WIRE_OFF, WIRE_SKELETON, WIRE_GRID = 0, 1, 2
# The walls' see-through fills, by kind, in drawing order: every group of one
# kind (its panels, the game's faces it colours, and both from the outside
# side) is drawn in one pass with the stencil, so a pixel is tinted ONCE per
# kind. Without it two pieces of the same wall -- the staircase a diagonal
# collision wall is made of, a panel and the face under it -- each added
# their 25% and drew a bright line where no edge exists. Hard walls last:
# where two kinds meet, theirs is the
# colour on top
STENCIL_CLASSES = ("hole_steps_covered", "hole_steps", "step_walls_covered", "step_walls",
                   "invisible_walls", "hard_walls")
# how far a wall's flag is pulled toward the camera, as a share of its
# distance (the shader): the fill a little, the outlines and the names more,
# so they stay over it. A share, not a fixed offset: a fixed one grows with
# the distance and ends up showing the flag through the wall
PULL_FILL = 0.001
PULL_EDGES = 0.002


def wall_class(category):
    """The kind of wall a group's fill belongs to, or None if it is not one
    (a name, an outline, another flag)."""
    if category.endswith(("_label", "_lines")):
        return None
    for kind in STENCIL_CLASSES:
        if category.startswith(kind):
            return kind
    return None


def wall_pull(category):
    """How much a group is pulled toward the camera: a wall's fill or the
    face it colours a little, its outline and its name more. 0 for
    everything else, which keeps the depth offset it has today."""
    if not any(category.startswith(kind) for kind in STENCIL_CLASSES):
        return 0.0
    return PULL_EDGES if category.endswith(("_label", "_lines")) else PULL_FILL
GRID_COLOR = (0.0, 0.0, 0.0, 0.7)

# a sprite nearer than this to the camera is not drawn (finding 305): 150
# game units, in the viewer's metres
NEAR_SPRITE = 150.0 / 128.0

# on the main menu background (like "ctrviewer by DCxDemo")
SIGNATURE = "BBLIT Viewer by AleMastroianni"

VERTEX_SHADER = """#version 330 core
in vec3 position;
in vec3 color;
in vec2 uv;
uniform mat4 mvp;
// the walls' flags are drawn on the surface they describe: instead of a
// depth offset, which is fixed and lets an overlay through a wall as the
// distance grows, the vertex is pulled toward the camera in view space by a
// SHARE of its distance, as the CTR viewer does. 0 = no pull
uniform mat4 view_matrix;
uniform mat4 projection;
uniform float pull;
// the texture coordinate rule (finding 328): the uv in the buffer is the
// OpenGL renderer's byte / 255, and these four turn it into the chosen one
uniform vec2 uv_low;
uniform vec2 uv_high;
uniform vec2 uv_scale;
uniform vec2 uv_offset;
out vec3 v_color;
out vec2 v_uv;
void main() {
    if (pull > 0.0) {
        vec4 vp = view_matrix * vec4(position, 1.0);
        vp.xyz *= 1.0 - min(0.25, pull * (1.0 + length(vp.xyz) * 0.0025));
        gl_Position = projection * vp;
    } else {
        gl_Position = mvp * vec4(position, 1.0);
    }
    v_color = color;
    v_uv = clamp(uv, uv_low, uv_high) * uv_scale + uv_offset;
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
// The PC has no alpha test at all (finding 306): the game's own faces are
// cut out by the alpha of their texture, in the sorted pass. It is left for
// the viewer's own names, which are drawn over everything and must not write
// depth where the glyphs are not.
uniform int alpha_test;
uniform vec4 override;
out vec4 color_out;
void main() {
    // Wireframe -> Grid: the triangle edges in one dark colour
    if (override.a > 0.0) {
        color_out = override;
        return;
    }
    // the original has no lights: the vertex color is baked lighting.
    // On the PC the factor is 1, not the PlayStation's 2 (128 = neutral):
    // measured on the L03A sea, (0,0,63) in the game and (0,0,63) here with 1,
    // (0,0,125) with 2 (finding 268)
    if (has_texture == 1 && show_textures == 1) {
        vec4 t = texture(tex_sampler, v_uv);
        if (alpha_test == 1 && t.a < 0.5) discard;
        // the sprites: the game's glAlphaFunc(GL_GREATER, 0) (N69)
        if (alpha_test == 2 && t.a <= 0.0) discard;
        // the alpha the renderer built into the texture when it loaded it
        // (finding 305): one blend function for every mode
        color_out = vec4(t.rgb * v_color * albedo * blend_scale, alpha * t.a);
    } else {
        color_out = vec4(v_color * blend_scale, alpha);
    }
}
"""


class BlendSorter:
    """The still semi-transparent triangles of the scene, drawn back to front
    like the PlayStation's ordering table (sorted by depth): with "half"
    blending (mode 0, B/2 + F/2) the order changes the result, and drawn
    group by group a face behind could come out over one in front (water,
    glass, halos). The additive and subtractive modes go in the same order:
    for them it changes nothing.

    One buffer for all of them; it is sorted again only when the camera
    moves, by the depth of the centre of each FACE along the view direction
    -- one entry per face, as the PC orders them (finding 306), so the two
    triangles of a quad stay together -- and drawn in runs of consecutive
    faces of the same group (texture and mode). Left out, and drawn as
    before after these: animated and rotating objects (their geometry
    changes with the tick) and the flags' overlays. The sky has a sorter of
    its own, built around the camera (finding 346)."""

    def __init__(self):
        self.centres = []        # (x, y, z) per face
        self.owner = []          # the group of each face
        self.chunks = []         # the face's vertices, as bytes
        self.vertices = []       # how many vertices each face has
        self.order = None
        self.runs = []           # [group, first vertex, vertex count]
        self.camera = None
        self.vao = self.vbo = None

    def add(self, face_group, data):
        """One entry per FACE, as the PC orders them (finding 306): a quad is
        two triangles and they stay together, at the mean of the face's own
        vertices (the two the triangles share counted once). Fewer entries to
        sort and, above all, fewer runs to draw."""
        k = 0
        for n_triangles in face_group.face_tris:
            size = 24 * n_triangles
            if k + size > len(data):
                break
            corners = {(data[k + v], data[k + v + 1], data[k + v + 2])
                       for v in range(0, size, 8)}
            self.centres.append((sum(p[0] for p in corners) / len(corners),
                                 sum(p[1] for p in corners) / len(corners),
                                 sum(p[2] for p in corners) / len(corners)))
            self.owner.append(face_group)
            self.chunks.append(data[k:k + size].tobytes())
            self.vertices.append(3 * n_triangles)
            k += size

    def back_to_front(self, pos, forward):
        """The face indices, the farthest first."""
        px, py, pz = pos
        fx, fy, fz = forward
        c = self.centres
        return sorted(range(len(c)), key=lambda i: -((c[i][0] - px) * fx + (c[i][1] - py) * fy
                                                      + (c[i][2] - pz) * fz))

    def update(self, pos, forward):
        """Sorts again if the camera moved; uploads only if the order changed."""
        camera = (tuple(pos), tuple(forward))
        if camera == self.camera or not self.chunks:
            return
        self.camera = camera
        order = self.back_to_front(pos, forward)
        if order == self.order:
            return
        self.order = order
        data = b"".join(self.chunks[i] for i in order)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(GL_ARRAY_BUFFER, 0, len(data), data)
        runs, owner, vertices = [], self.owner, self.vertices
        first = 0
        for i in order:
            if runs and runs[-1][0] is owner[i]:
                runs[-1][2] += vertices[i]
            else:
                runs.append([owner[i], first, vertices[i]])
            first += vertices[i]
        self.runs = runs


class Drawing:
    """The drawing part of the viewer window (`app.Viewer` inherits it)."""

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

    def draw_loading(self, name):
        """One frame saying which level is coming, drawn before the level is
        built. Building blocks the event loop for a second or more, so
        without this the window keeps showing the LAST frame of the level
        that is leaving: with the camera inside the terrain of Era selector
        that looked like a broken screen, and the status bar still named the
        old level."""
        self.switch_to()
        glDisable(GL_DEPTH_TEST)
        glClearColor(0.05, 0.06, 0.09, 1.0)
        self.clear()
        glEnable(GL_BLEND)
        s = max(0.75, min(1.6, self.height / 760.0))
        self.status_bar.font_size = 16 * s
        self.status_bar.text = t("status.loading", name=name)
        self.status_bar.x, self.status_bar.y = round(24 * s), round(24 * s)
        self.status_bar.draw()
        self.flip()
        self.status_bar.x, self.status_bar.y = round(10 * s), round(7 * s)
        glEnable(GL_DEPTH_TEST)

    def tick(self) -> int:
        """The animation tick: frozen with P or with --tick."""
        if self.fixed_tick is not None:
            return self.fixed_tick
        return int(self.anim_time * self.tps)

    def _gl_texture(self, tid, blend=None):
        """The texture on the card, converted as the PC converts it when it
        loads it: the gamma (finding 306) and, for a semi-transparent face,
        the alpha of its blend mode (finding 305). One copy per mode, as the
        game keeps one copy per mode a texture is used with."""
        if isinstance(tid, str):
            return self._label_texture(tid)
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
        blend = None if blend in (OVERLAY_BLEND, BOX_BLEND, WALL_BLEND) else blend
        lookup_key = (id(source[0]), source[1], blend)
        if lookup_key in self.textures:
            return self.textures[lookup_key]
        try:
            b, h, rgba = tim.read_tim(source[0], source[1], tim.pc_colour(blend))
            if self.scale_factor != 1:
                b, h, rgba = upscale.enlarge((b, h, rgba), self.scale_factor)
        except Exception:  # noqa: BLE001
            self.textures[lookup_key] = None
            return None
        name = ctypes.c_uint()
        glGenTextures(1, ctypes.byref(name))
        glBindTexture(GL_TEXTURE_2D, name.value)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self.min_filter())
        # the PC filters textures bilinearly (screenshots of the PC game):
        # like the PC by default, key L for sharp texels
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR if self.bilinear else GL_NEAREST)
        wrap = self.uv_wrap()
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)
        buf = (ctypes.c_ubyte * len(rgba)).from_buffer_copy(rgba)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, b, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, buf)
        glGenerateMipmap(GL_TEXTURE_2D)
        self.textures[lookup_key] = name.value
        return name.value

    def _label_texture(self, tid):
        """A flag's name as a texture (flag_labels), always in English."""
        text = tid.split(":", 1)[1]
        lookup_key = ("label", text)
        if lookup_key not in self.textures:
            width, height, rgba = flag_labels.texture_rgba(text)
            name = ctypes.c_uint()
            glGenTextures(1, ctypes.byref(name))
            glBindTexture(GL_TEXTURE_2D, name.value)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            buf = (ctypes.c_ubyte * len(rgba)).from_buffer_copy(rgba)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, buf)
            glGenerateMipmap(GL_TEXTURE_2D)
            self.textures[lookup_key] = name.value
        return self.textures[lookup_key]

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

    def _upload_sorter(self, sorter):
        """The buffer of the sorted semi-transparent triangles, filled in the
        order of the first frame (BlendSorter.update)."""
        if not sorter.chunks:
            return
        vao, vbo = ctypes.c_uint(), ctypes.c_uint()
        glGenVertexArrays(1, ctypes.byref(vao))
        glGenBuffers(1, ctypes.byref(vbo))
        glBindVertexArray(vao.value)
        glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
        glBufferData(GL_ARRAY_BUFFER, sum(len(c) for c in sorter.chunks), None, GL_DYNAMIC_DRAW)
        for name, measure, offset in (("position", 3, 0), ("color", 3, 12), ("uv", 2, 24)):
            place = self.program.attributes[name]["location"]
            glEnableVertexAttribArray(place)
            glVertexAttribPointer(place, measure, GL_FLOAT, False, 8 * 4, ctypes.c_void_p(offset))
        glBindVertexArray(0)
        sorter.vao, sorter.vbo = vao.value, vbo.value

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
        for sorter in (getattr(self, "_blend_sorter", None), getattr(self, "_sky_sorter", None)):
            if sorter is not None and sorter.vao:
                vaos.add(sorter.vao)
                vbos.add(sorter.vbo)
        self._blend_sorter = self._sky_sorter = None
        if vaos:
            glDeleteVertexArrays(len(vaos), (ctypes.c_uint * len(vaos))(*vaos))
            glDeleteBuffers(len(vbos), (ctypes.c_uint * len(vbos))(*vbos))
        if texture:
            self._set_texture_scale(self.scale_factor)

    def uniform(self, name, value):
        """A uniform, pushed only when it changes. With the cut-out faces in
        the sorted list a frame can be a thousand runs of a few triangles
        (`L01A`: 16 runs before, 1288 after), and each was setting the same
        handful of uniforms again: same picture, a third of the calls."""
        if self._uniform_cache.get(name) != value:
            self.program[name] = value
            self._uniform_cache[name] = value

    def min_filter(self):
        """How a texture is read when it is smaller on the screen than it is
        in the file. The PC uses GL_LINEAR and no mipmaps at all (finding
        306): far away it keeps its grain, and it shimmers as the camera
        moves. Video options -> Distant textures puts the mipmaps back."""
        if not self.mipmaps:
            return GL_LINEAR if self.bilinear else GL_NEAREST
        return GL_LINEAR_MIPMAP_LINEAR if self.bilinear else GL_LINEAR_MIPMAP_NEAREST

    def uv_wrap(self):
        """What happens past the edge of a texture. The PC's OpenGL renderer
        REPEATS on every profile (finding 341: the three glTexParameterf of
        the program all set GL_REPEAT), so near 0 or 1 the linear filter mixes
        in the opposite edge of the same texture; the clamp to [0.01, 0.99]
        keeps that mixing to textures under 50 texels a side (geometry.py).
        The software renderer and the PlayStation never get there, so for
        their rule clamping at the edge changes nothing."""
        return GL_CLAMP_TO_EDGE if self.uv_rule == geo.UV_PSX else GL_REPEAT

    def push_uv_rule(self, tex_id):
        """The chosen rule for the texture about to be drawn, as four uniforms
        (findings 328, 341). Only the PlayStation rule changes from texture to
        texture (it needs its size), so this pushes nothing most of the time.
        A flag's name (and the names over the boxes, `None`) is not a texture
        of the game: left alone, its coordinates go outside 0..1."""
        transform = self._uv_memo.get(tex_id)
        if transform is None:
            label = tex_id is None or isinstance(tex_id, str)
            measure = None if label or self.current_level is None else self.current_level.sizes.get(tex_id)
            transform = geo.uv_transform(geo.UV_RAW if label else self.uv_rule, measure)
            self._uv_memo[tex_id] = transform
        if transform != self._uv_pushed:
            low, high, scale, offset = transform
            self.program["uv_low"], self.program["uv_high"] = low, high
            self.program["uv_scale"], self.program["uv_offset"] = scale, offset
            self._uv_pushed = transform

    def forget_uv_rule(self):
        """After a change of rule, of level or of texture sizes."""
        self._uv_memo, self._uv_pushed = {}, None

    def on_draw(self):
        if self.current_level is None:
            # no level: the blue background and the menu, always open
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
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe == WIRE_SKELETON else GL_FILL)

        j, p = math.radians(self.yaw), math.radians(self.pitch)
        forward = Vec3(math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        far_plane = max(self.hi[i] - self.lo[i] for i in range(3)) * 4 + 100
        proj = Mat4.perspective_projection(self.width / self.height, 0.1, far_plane, float(self.fov))
        view = Mat4.look_at(self.pos, self.pos + forward, Vec3(0.0, 1.0, 0.0))

        self.program.use()
        self._uv_pushed = None
        self._uniform_cache = {}
        self.program["mvp"] = proj @ view
        # the two halves apart, for the groups drawn with the pull
        self.program["view_matrix"] = view
        self.program["projection"] = proj
        self.program["show_textures"] = 1 if self.show_textures else 0
        self.program["albedo"] = self.albedo
        # every face of the game goes through the same blend function now
        # (finding 305), so it is set once for the frame and not per run
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        drawn_triangles = 0
        # rule passes so far, for the rotating objects (280)
        if self.fixed_tick is not None:
            rule_passes = self.fixed_tick * RULE_PASSES_PER_TICK
        else:
            rule_passes = self.anim_time * self.tps * RULE_PASSES_PER_TICK

        # "Moving characters" (finding 317): the simulation is run to this
        # frame's tick once, and every mover's groups are placed with it
        sim = self.current_level.mover_sim
        mover_mvp = {}
        if sim is not None:
            sim.run_to(int(rule_passes))
            # one matrix per character, not one per group: a character is
            # several groups (one per animation frame) and building the matrix
            # again for each of them was most of the cost
            for mover in sim.movers:
                angle = -mover.heading * 2 * math.pi / 4096.0
                mover_mvp[mover.index] = (proj @ view
                                          @ Mat4.from_translation(Vec3(*geo._transform(mover.pos)))
                                          @ Mat4.from_rotation(angle, Vec3(0.0, 1.0, 0.0)))

        areas = self._visible_areas(proj @ view) if self.show_area_visibility else None
        visible_groups = [g for g in self.current_level.face_groups.values()
                     if (areas is None or g.area is None or g.area in areas)
                     and not (g.category == "props" and not self.show_props)
                     and not (g.category in OVERLAYS and not self._overlay_shown(g.category))
                     # the flag names are textures: without textures they would be black quads
                     and not (g.category.endswith("_label") and not self.show_textures)
                     and not (g.category == "clones" and self.show_clones < 2)
                     and not (g.category == "clones_at_start" and self.show_clones < 1)
                     and g.category != "sky_dome"]

        # face culling is switched only when it changes from one group to the
        # next: 573 groups each turning it on and off cost milliseconds
        cull_state = [False]
        glCullFace(GL_BACK)

        def set_cull(on):
            if on != cull_state[0]:
                (glEnable if on else glDisable)(GL_CULL_FACE)
                cull_state[0] = on

        def draw_face_group(face_group):
            tex = (self._gl_texture(face_group.tex_id, face_group.blend)
                   if face_group.tex_id is not None else None)
            self.uniform("has_texture", 1 if tex else 0)
            self.push_uv_rule(face_group.tex_id)
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
                mvp = proj @ view
                if face_group.category == "sky_dome":
                    # a spinning object carried with the camera (the streaks
                    # of the night sky of Magic Hare Blower, object 262) turns
                    # around the camera, like the sky pass places it: without
                    # this it turned around the level's origin, 100 m away,
                    # and was never seen from where Bugs stands
                    mvp = mvp @ Mat4.from_translation(self.pos)
                self.program["mvp"] = (mvp @ Mat4.from_translation(p)
                                       @ Mat4.from_rotation(angle, Vec3(0.0, 1.0, 0.0))
                                       @ Mat4.from_translation(-p))
            elif face_group.mover is not None and face_group.mover in mover_mvp:
                # a character the game moves: its triangles are around its own
                # origin, the simulation says where it is and which way it faces
                self.program["mvp"] = mover_mvp[face_group.mover]
            glBindVertexArray(vao)
            # the alpha test is only for the viewer's own names (see the
            # shader): everything of the game's is cut out by its alpha
            self.uniform("alpha_test", 1 if face_group.category.endswith("_label") else 0)
            # the game's own faces, culled as the game culls them (finding
            # 307) with Video options -> Backface culling; the two-sided ones
            # (bit 0x02) stay. The flags' one-sided groups have a rule of
            # their own (ONE_SIDED), with the same front face
            set_cull(face_group.category in ONE_SIDED or (
                self.backface_culling and face_group.category not in OVERLAYS and not face_group.two_sided))
            # a link's line is drawn through the geometry, so it can be
            # followed to where it goes even behind a wall
            through = face_group.category in THROUGH_WALLS
            if through:
                glDisable(GL_DEPTH_TEST)
            pull = wall_pull(face_group.category)
            self.uniform("pull", pull)
            pulled = None if pull else PULLED_FORWARD.get(face_group.category)
            if pulled:
                # drawn on the terrain face itself (the walls of a piece
                # without collision): pulled toward the camera in the depth
                # test, or it would flicker against the face under it; the
                # edges and the name further, so the fill does not cover them
                glEnable(GL_POLYGON_OFFSET_LINE if face_group.category.endswith("_lines")
                         else GL_POLYGON_OFFSET_FILL)
                glPolygonOffset(*pulled)
            # a flag's see-through fill (a wall, a box) writes no depth:
            # drawn after the game's faces, it would else cut out every flag,
            # name and shadow drawn after it that stands behind it, in its
            # whole face (the flags made holes behind themselves). The
            # opaque fills, the zones, keep hiding
            # what is behind them, as an opaque thing does; and so does No
            # collision, at 75%: without the depth write the inner faces of
            # a piece (the mushroom of Wabbit on the run! 2) showed through
            # its top and the white grew denser, not clearer
            see_through = (face_group.category in OVERLAYS
                           and face_group.blend in (BOX_BLEND, WALL_BLEND))
            if see_through:
                glDepthMask(GL_FALSE)
            if face_group.category.endswith("_lines"):
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                # the red outline of what hurts is drawn thicker, or a red line
                # on an orange box edge would look like its own shadow
                thick = face_group.category in THICK_LINES
                if thick:
                    glLineWidth(LINK_WIDTH if through else THICK_LINE_WIDTH)
                glDrawArrays(GL_TRIANGLES, first_idx, item_count)
                if thick:
                    glLineWidth(1.0)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe == WIRE_SKELETON else GL_FILL)
            else:
                glDrawArrays(GL_TRIANGLES, first_idx, item_count)
            if see_through:
                glDepthMask(GL_TRUE)
            if pulled:
                glDisable(GL_POLYGON_OFFSET_FILL)
                glDisable(GL_POLYGON_OFFSET_LINE)
            if through:
                glEnable(GL_DEPTH_TEST)
            if face_group.spin or face_group.mover is not None:
                self.program["mvp"] = (proj @ view @ Mat4.from_translation(self.pos)
                                       if face_group.category == "sky_dome" else proj @ view)
            return item_count // 3

        def set_blend(blend):
            """The PC has ONE blend function for every semi-transparent face
            (finding 305): the four PlayStation modes are already in the
            alpha of the texture, built when it was loaded (tim.pc_colour).
            Only the viewer's own overlays still have a blend of their own.
            The alpha test goes off wherever the alpha means something."""
            alpha = 1.0
            if blend == OVERLAY_BLEND:
                alpha = 0.75
            elif blend == BOX_BLEND:
                # a collision box: the model inside it has to be visible
                alpha = BOX_ALPHA
            elif blend == WALL_BLEND:
                # a wall's fill: nearly transparent, the edges and names full
                alpha = WALL_ALPHA
            self.uniform("alpha", alpha)
            self.uniform("blend_scale", 1.0)

        def draw_sorted(sorter, shown, camera):
            """A sorted list's faces, the farthest first (finding 306): only
            those of the groups drawn this frame."""
            n = 0
            if sorter is None or not sorter.vao:
                return n
            sorter.update(camera, forward)
            glBindVertexArray(sorter.vao)
            for face_group, first_idx, item_count in sorter.runs:
                if id(face_group) not in shown:
                    continue
                tex = (self._gl_texture(face_group.tex_id, face_group.blend)
                       if face_group.tex_id is not None else None)
                self.uniform("has_texture", 1 if tex else 0)
                self.uniform("alpha_test", 0)
                self.uniform("pull", 0.0)
                self.push_uv_rule(face_group.tex_id)
                glBindTexture(GL_TEXTURE_2D, tex or 0)
                set_blend(face_group.blend)
                set_cull(self.backface_culling and not face_group.two_sided)
                glDrawArrays(GL_TRIANGLES, first_idx, item_count)
                n += item_count // 3
            set_cull(False)
            return n

        cut_outs = self.current_level.cut_outs

        # the sky follows the camera: it is built around the origin (object 0
        # of L03A, model 1, 367 x 245 x 367 m) and moved with the camera. As
        # in the game (finding 346) the objects carried with the camera have
        # no path of their own: the depth is tested (GL_LEQUAL) and written,
        # so between two domes the nearer face wins, pixel by pixel; every
        # opaque face first, then the cut-out and semi-transparent ones of
        # all of them, the farthest first, blended, without alpha test. Then
        # the depth is cleared and the world drawn over it: in the game sky
        # and world share one depth buffer, the same picture as long as the
        # world is nearer than the sky, and clearing keeps a free camera far
        # above a level usable (the one declared difference).
        if self.show_sky:
            self.program["mvp"] = proj @ view @ Mat4.from_translation(self.pos)
            glDepthFunc(GL_LEQUAL)
            sky_area = self.sky_area()
            # a sky cut by area is drawn only in its own area, with or
            # without Visibility by area: one sky at a time, as the game
            sky_groups = [g for g in self.current_level.face_groups.values()
                          if g.category == "sky_dome" and (g.area is None or g.area == sky_area)]
            set_blend(None)
            for face_group in sky_groups:
                if face_group.blend is None and face_group.tex_id not in cut_outs:
                    drawn_triangles += draw_face_group(face_group)
            if self.show_blending:
                # around the camera, like the sky: the camera is the origin
                drawn_triangles += draw_sorted(self._sky_sorter, {id(g) for g in sky_groups},
                                               (0.0, 0.0, 0.0))
            for face_group in sky_groups:
                if ((face_group.blend is not None or face_group.tex_id in cut_outs)
                        and not (face_group.sorted and self.show_blending)):
                    set_blend(face_group.blend if self.show_blending else None)
                    drawn_triangles += draw_face_group(face_group)
            set_blend(None)
            glDepthFunc(GL_LESS)
            glClear(GL_DEPTH_BUFFER_BIT)
            self.program["mvp"] = proj @ view

        # the opaque ones first; the faces of a texture with a transparent
        # entry are NOT opaque for the PC (finding 306): they go with the
        # semi-transparent ones, in the sorted pass
        set_blend(None)
        for face_group in visible_groups:
            if face_group.blend is None and face_group.tex_id not in cut_outs:
                drawn_triangles += draw_face_group(face_group)

        set_cull(False)
        set_blend(None)

        # then the semi-transparent ones: the still ones back to front
        # (BlendSorter), then the moving ones and the overlays; the sprites
        # come last of all, as the game's flush draws them (N69)
        # the walls' fills are drawn apart, one pass per kind with the
        # stencil (STENCIL_CLASSES): here they are taken out of the ordinary
        # passes and the rest goes on as before
        wall_fills = [g for g in visible_groups if wall_class(g.category)]
        wall_fill_ids = {id(g) for g in wall_fills}
        if self.show_blending:
            # the PC never turns depth writes off (finding 306): the still
            # faces come back to front from the BlendSorter, so a nearer one
            # hiding a farther one is what the game does
            drawn_triangles += draw_sorted(self._blend_sorter, {id(g) for g in visible_groups},
                                           self.pos)
            for face_group in visible_groups:
                if id(face_group) in wall_fill_ids:
                    continue
                if not face_group.sorted and (face_group.blend is not None
                                              or face_group.tex_id in cut_outs):
                    set_blend(face_group.blend)
                    drawn_triangles += draw_face_group(face_group)
            set_blend(None)
        else:
            for face_group in visible_groups:
                if id(face_group) in wall_fill_ids:
                    continue
                if face_group.blend is not None or face_group.tex_id in cut_outs:
                    drawn_triangles += draw_face_group(face_group)

        # the walls, kind by kind: the stencil is cleared for each kind and a
        # fragment is kept only where that kind has not been drawn yet, so
        # its 25% is laid on a pixel once and never doubles
        if wall_fills:
            by_kind = {}
            for face_group in wall_fills:
                by_kind.setdefault(wall_class(face_group.category), []).append(face_group)
            glEnable(GL_STENCIL_TEST)
            glStencilOp(GL_KEEP, GL_KEEP, GL_REPLACE)
            glStencilMask(0xFF)
            glStencilFunc(GL_NOTEQUAL, 1, 0xFF)
            for kind in STENCIL_CLASSES:
                groups = by_kind.get(kind)
                if not groups:
                    continue
                glClear(GL_STENCIL_BUFFER_BIT)
                for face_group in groups:
                    set_blend(face_group.blend)
                    drawn_triangles += draw_face_group(face_group)
            glDisable(GL_STENCIL_TEST)
            glStencilMask(0x00)
            self.uniform("pull", 0.0)
            set_blend(None)

        if self.wireframe == WIRE_GRID:
            # Grid: the edges of every triangle drawn, in one dark colour, on
            # the surface (pulled a little toward the camera, no flicker)
            set_blend(None)
            self.program["override"] = GRID_COLOR
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glEnable(GL_POLYGON_OFFSET_LINE)
            glPolygonOffset(-1.0, -2.0)
            glDepthMask(GL_FALSE)
            for face_group in visible_groups:
                if face_group.category not in OVERLAYS:
                    draw_face_group(face_group)
            glDepthMask(GL_TRUE)
            glDisable(GL_POLYGON_OFFSET_LINE)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            self.program["override"] = (0.0, 0.0, 0.0, 0.0)

        set_cull(False)
        # the collision boxes' names: last, facing the camera, over the boxes
        if self.show_collision_boxes and self.show_textures:
            set_blend(None)
            drawn_triangles += self._draw_box_labels(forward)

        if self.show_camera_shadow:
            self._draw_camera_shadow()

        # the selected run, drawn through everything so it is found at once
        if self.picked:
            self._draw_pick_highlight()

        # the sprites (torch flames, glows) last, as the game's last pass
        # (N69): unsorted, in the level's order, depth written, and the alpha
        # test GL_GREATER 0 so a transparent texel writes nothing. Nothing of
        # the game's comes after them, so a sprite cannot cut a hole in it;
        # the viewer's own names and shadow are drawn before them for the
        # same reason
        set_cull(False)
        self.program.use()
        for sp in self._sprites_in_view(forward):
            drawn_triangles += self._draw_sprite(sp, forward, set_blend)
        set_blend(None)

        glBindVertexArray(0)
        self.program.stop()

        # status bar and menu without depth test: the letter quads
        # overlap and with the test on they would discard each other
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDisable(GL_DEPTH_TEST)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self.drawn_triangles = drawn_triangles
        if not self.ui_hidden:
            # the drawn pages (Keyboard, Gamepad) take the whole window
            if self.picked and self.menu.custom() is None:
                self._draw_pick_panel()
            if self.show_status_bar and self.menu.custom() is None:
                self._draw_status_bar()
            if self.menu.is_open and self.menu.stack and self.menu.stack[-1][0] == "main":
                self._draw_signature()
            self.menu.draw_menu(self)
        glEnable(GL_DEPTH_TEST)

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
        if self.show_area_visibility and self.area_in_use is not None:
            pieces.append(t("status.area", n=self.area_in_use))
        state = self._animation_state()
        if state != "playing":
            pieces.append(t("status.paused") if state == "paused" else t("status.pose"))
        if self.pick_enabled:
            pieces.append(t("status.pick"))
        pieces.append(t("status.menu"))
        s = max(0.75, min(1.6, self.height / 760.0))
        self.status_bar.font_size = 11 * s
        self.status_bar.x, self.status_bar.y = round(10 * s), round(7 * s)
        self.status_bar.text = "   ·   ".join(pieces)
        self._status_background.width, self._status_background.height = self.width, round(26 * s)
        glEnable(GL_BLEND)
        self._status_background.draw()
        self.status_bar.draw()

    def _draw_pick_panel(self):
        """The selector's card, top left: what was picked, in words."""
        lines = self.picked_card()
        if not lines:
            return
        s = max(0.75, min(1.6, self.height / 760.0))
        self.pick_text.font_size = 11 * s
        self.pick_text.text = chr(10).join(lines)
        self.pick_text.width = round(740 * s)
        self.pick_text.x = round(14 * s)
        self.pick_text.y = self.height - round(14 * s)
        height = round(len(lines) * 16.5 * s) + round(16 * s)
        self._pick_background.width = round(764 * s)
        self._pick_background.height = height
        self._pick_background.x, self._pick_background.y = round(6 * s), self.height - height - round(6 * s)
        glEnable(GL_BLEND)
        self._pick_background.draw()
        self.pick_text.draw()

    def _draw_pick_highlight(self):
        """The selected run's rectangle, drawn through the geometry: the
        colour alone is not enough to say what was taken, so the card names
        it, and this says where it is."""
        entry = self.picked[self.picked_i % len(self.picked)]
        info = entry.get("run")
        u = geo.UNITS_PER_METER
        if info is not None:
            a0, a1, y_top, y_base = info["a0"], info["a1"], info["y_top"], info["y_base"]
            if info["axis"] == "x":
                corners = [(info["plane"], y_base, a0), (info["plane"], y_base, a1),
                           (info["plane"], y_top, a1), (info["plane"], y_top, a0)]
            else:
                corners = [(a0, y_base, info["plane"]), (a1, y_base, info["plane"]),
                           (a1, y_top, info["plane"]), (a0, y_top, info["plane"])]
        else:
            corners = [entry["tri"][0], entry["tri"][1], entry["tri"][2], entry["tri"][2]]
            corners = [(c[0] * u, -c[1] * u, -c[2] * u) for c in corners]
        pts = [(c[0] / u, -c[1] / u, -c[2] / u) for c in corners]
        data = []
        for a, b, c in ((0, 1, 2), (0, 2, 3)):
            for i in (a, b, c):
                data += [pts[i][0], pts[i][1], pts[i][2], 1.0, 1.0, 0.2, 0.0, 0.0]
        if self._pick_vao is None:
            vao, vbo = ctypes.c_uint(), ctypes.c_uint()
            glGenVertexArrays(1, ctypes.byref(vao))
            glGenBuffers(1, ctypes.byref(vbo))
            glBindVertexArray(vao.value)
            glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
            for name, measure, offset in (("position", 3, 0), ("color", 3, 12), ("uv", 2, 24)):
                place = self.program.attributes[name]["location"]
                glEnableVertexAttribArray(place)
                glVertexAttribPointer(place, measure, GL_FLOAT, False, 32, ctypes.c_void_p(offset))
            self._pick_vao, self._pick_vbo = vao.value, vbo.value
        self.program.use()
        glBindVertexArray(self._pick_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._pick_vbo)
        arr = (ctypes.c_float * len(data))(*data)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(arr), arr, GL_DYNAMIC_DRAW)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.program["has_texture"], self.program["blend_scale"] = 0, 1.0
        self.program["alpha_test"] = 0
        self.program["pull"] = 0.0
        glDisable(GL_DEPTH_TEST)
        glDepthMask(GL_FALSE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        self.program["alpha"] = 0.28
        glDrawArrays(GL_TRIANGLES, 0, len(data) // 8)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glLineWidth(3.0)
        self.program["alpha"] = 1.0
        glDrawArrays(GL_TRIANGLES, 0, len(data) // 8)
        glLineWidth(1.0)
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe == WIRE_SKELETON else GL_FILL)
        glDepthMask(GL_TRUE)
        glEnable(GL_DEPTH_TEST)
        glBindVertexArray(0)
        self.program.stop()

    def _draw_camera_shadow(self):
        """Camera and points -> Show the shadow: a black disc on the ground
        the game's query finds under the camera (Viewer._shadow_of), 4 units
        above it like the other overlays, and an amber rim drawn without
        depth, so it shows even where the heightmap is under the visible
        terrain. Nothing when there is no ground below."""
        (gx, gy, gz), grid_block = self._shadow_of(self.pos)
        if grid_block is None:
            return
        u = geo.UNITS_PER_METER
        cx, cy, cz = gx / u, -(gy - 4) / u, -gz / u
        r = self.SHADOW_RADIUS / u
        steps = 32
        ring = [(math.cos(2 * math.pi * i / steps), math.sin(2 * math.pi * i / steps)) for i in range(steps + 1)]
        disc, rim = [], []
        for (c0, s0), (c1, s1) in zip(ring, ring[1:]):
            for px, pz in ((0.0, 0.0), (c0, s0), (c1, s1)):
                disc += [cx + px * r, cy, cz + pz * r, 0.0, 0.0, 0.0, 0.0, 0.0]
            inner, outer = 0.82 * r, r
            quad = [(c0 * inner, s0 * inner), (c0 * outer, s0 * outer), (c1 * outer, s1 * outer),
                    (c0 * inner, s0 * inner), (c1 * outer, s1 * outer), (c1 * inner, s1 * inner)]
            for px, pz in quad:
                rim += [cx + px, cy, cz + pz, 1.0, 0.72, 0.15, 0.0, 0.0]
        if self._shadow_vao is None:
            vao, vbo = ctypes.c_uint(), ctypes.c_uint()
            glGenVertexArrays(1, ctypes.byref(vao))
            glGenBuffers(1, ctypes.byref(vbo))
            glBindVertexArray(vao.value)
            glBindBuffer(GL_ARRAY_BUFFER, vbo.value)
            for name, measure, offset in (("position", 3, 0), ("color", 3, 12), ("uv", 2, 24)):
                place = self.program.attributes[name]["location"]
                glEnableVertexAttribArray(place)
                glVertexAttribPointer(place, measure, GL_FLOAT, False, 32, ctypes.c_void_p(offset))
            self._shadow_vao, self._shadow_vbo = vao.value, vbo.value
        glBindVertexArray(self._shadow_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._shadow_vbo)
        data = disc + rim
        arr = (ctypes.c_float * len(data))(*data)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(arr), arr, GL_DYNAMIC_DRAW)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glBindTexture(GL_TEXTURE_2D, 0)
        self.program["has_texture"], self.program["blend_scale"] = 0, 1.0
        glDepthMask(GL_FALSE)
        self.program["alpha"] = 0.6
        glDrawArrays(GL_TRIANGLES, 0, len(disc) // 8)
        glDisable(GL_DEPTH_TEST)
        self.program["alpha"] = 0.9
        glDrawArrays(GL_TRIANGLES, len(disc) // 8, len(rim) // 8)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_TRUE)
        self.program["alpha"] = 1.0
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE if self.wireframe == WIRE_SKELETON else GL_FILL)

    def _make_sprite_buffer(self):
        """The buffer the squares facing the camera are drawn from (sprites and
        the collision boxes' names): made once, rewritten every frame."""
        if self._sprite_vao is not None:
            return
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

    def _sprites_in_view(self, forward):
        """The sprites (torch flames, ...) drawn this frame, in the level's
        order (the game draws them by texture bucket, never sorted: N69).
        The game does not draw a sprite nearer than 150 units to the camera
        (finding 305, the projection at 0x4383f0), measured along the view
        direction as the projection does."""
        out = []
        for sp in self.current_level.sprites:
            if (sp["category"] == "clones" and self.show_clones < 2) or \
                    (sp["category"] == "clones_at_start" and self.show_clones < 1):
                continue
            if (Vec3(*sp["pos"]) - self.pos).dot(forward) >= NEAR_SPRITE:
                out.append(sp)
        return out

    def _draw_sprite(self, sp, forward, set_blend):
        """One sprite as a square facing the camera: depth written, alpha
        test GL_GREATER 0, as the game's last pass (N69)."""
        self._make_sprite_buffer()
        right_vec = forward.cross(Vec3(0.0, 1.0, 0.0)).normalize()
        op = right_vec.cross(forward).normalize()
        glBindVertexArray(self._sprite_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._sprite_vbo)
        set_blend(sp["blend"] if self.show_blending else None)
        self.uniform("alpha_test", 2)
        f = self.current_level.sprite_frame(sp, self.tick())
        tex = self._gl_texture(f, sp["blend"] if self.show_blending else None)
        self.uniform("has_texture", 1 if tex else 0)
        self.push_uv_rule(f)
        glBindTexture(GL_TEXTURE_2D, tex or 0)
        # the sprite RESTS on the attachment point (the torch flame in the
        # game sits above the top), unless its template carries the
        # centring bit of finding 338: then it is centred on it (the glow)
        c = Vec3(*sp["pos"])
        b, h = sp["size"][0] / 2, sp["size"][1]
        if sp.get("centred"):
            c = c - op * (h / 2)
        corners = [c - right_vec * b, c + right_vec * b,
                   c - right_vec * b + op * h, c + right_vec * b + op * h]
        # the texture's first row is its top (v = 0), so the bottom corners
        # take v = 1: drawn the other way up, the flame's body sat at the top
        # of its square and its loose tips at the bottom, a metre over the
        # torch's head, while in the game it rests on it (the photo
        # Torch2_Docks.png)
        uvs = [(0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0)]
        data = []
        for i in (0, 1, 2, 1, 3, 2):
            p = corners[i]
            data += [p.x, p.y, p.z, 1.0, 1.0, 1.0, uvs[i][0], uvs[i][1]]
        arr = (ctypes.c_float * len(data))(*data)
        glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(arr), arr, GL_DYNAMIC_DRAW)
        glDrawArrays(GL_TRIANGLES, 0, 6)
        self.uniform("alpha_test", 0)
        return 2

    def _draw_box_labels(self, forward):
        """The collision boxes' names, floating above each object and facing
        the camera (overlays._collision_box_labels).

        Same square-facing-the-camera as the sprites, with the name's texture:
        the letters keep the same size in the world, so a name reads from any
        direction and never lies flat on a box.
        """
        labels = self.current_level.box_labels
        if not labels:
            return 0
        right_vec = forward.cross(Vec3(0.0, 1.0, 0.0)).normalize()
        op = right_vec.cross(forward).normalize()
        self._make_sprite_buffer()
        glBindVertexArray(self._sprite_vao)
        glBindBuffer(GL_ARRAY_BUFFER, self._sprite_vbo)
        self.uniform("has_texture", 1)
        self.uniform("alpha_test", 1)
        self.uniform("alpha", 1.0)
        self.push_uv_rule(None)
        n = 0
        tick = self.tick()
        for label in labels:
            place = label["pos"]
            frames = label.get("frames")
            if frames:
                # a held child's name moves with its bone, and is not there on
                # the frames where the child does not exist (finding 317)
                place = frames[tick % len(frames)]
                if place is None:
                    continue
            c = Vec3(*geo._transform(place))
            # a name behind the camera is not drawn: the same pixels, one draw
            # call less (they are one each)
            depth = (c - self.pos).dot(forward)
            if depth <= 0.0:
                continue
            tex, width, height = self._floating_label(label["text"])
            h = LABEL_HEIGHT / geo.UNITS_PER_METER
            # closer than LABEL_NEAR the name stops growing: it keeps the size
            # it has there, so standing next to an object does not fill the
            # screen with its name
            if depth < LABEL_NEAR:
                h *= depth / LABEL_NEAR
            b = h * width / height / 2.0
            corners = [c - right_vec * b, c + right_vec * b,
                       c - right_vec * b + op * h, c + right_vec * b + op * h]
            glBindTexture(GL_TEXTURE_2D, tex)
            uvs = [(0.0, 1.0), (1.0, 1.0), (0.0, 0.0), (1.0, 0.0)]
            data = []
            for i in (0, 1, 2, 1, 3, 2):
                p = corners[i]
                data += [p.x, p.y, p.z, 1.0, 1.0, 1.0, uvs[i][0], uvs[i][1]]
            arr = (ctypes.c_float * len(data))(*data)
            glBufferData(GL_ARRAY_BUFFER, ctypes.sizeof(arr), arr, GL_DYNAMIC_DRAW)
            glDrawArrays(GL_TRIANGLES, 0, 6)
            n += 2
        self.uniform("alpha_test", 0)
        return n

    def texture_names(self):
        """Every GL name in the texture cache, and nothing else.

        `self.textures` does not hold one shape of value: a normal texture
        and a flag's name are the GL name itself, a texture that could not
        be read is None, and a name floating above an object is
        `(name, width, height)`, because its size is needed to draw its
        quad. Whoever walks the cache to bind or to delete has to take the
        name out first: handing the tuple straight to `glDeleteTextures`
        raised a TypeError in the middle of `_free_gpu`, with the level's
        VAOs and VBOs already deleted, so the frame after the level change
        drew freed buffers and the viewer died on an access violation. It
        only happened with a flag that writes names on, which is why a
        level change with the flags off never showed it.
        """
        for value in self.textures.values():
            if isinstance(value, tuple):
                value = value[0]
            if value:
                yield value

    def _floating_label(self, text):
        """(texture, width, height) of a name floating above an object, made
        once per text (flag_labels.floating_texture_rgba)."""
        lookup_key = ("floating", text)
        if lookup_key not in self.textures:
            width, height, rgba = flag_labels.floating_texture_rgba(text)
            name = ctypes.c_uint()
            glGenTextures(1, ctypes.byref(name))
            glBindTexture(GL_TEXTURE_2D, name.value)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            buf = (ctypes.c_ubyte * len(rgba)).from_buffer_copy(rgba)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, buf)
            glGenerateMipmap(GL_TEXTURE_2D)
            self.textures[lookup_key] = (name.value, width, height)
        return self.textures[lookup_key]

    def _screenshot(self, dt):
        pyglet.image.get_buffer_manager().get_color_buffer().save(self.screenshot)
        print(f"screenshot written to {self.screenshot}")
        self.close()
