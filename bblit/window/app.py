"""The viewer window: it opens a level, keeps the flags and the settings,
and puts together the parts that draw (`drawing.py`), take the input
(`controls.py`), hold Camera and points (`points.py`) and build the menu
pages (`menu_pages.py`).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pyglet  # noqa: E402

# pyglet checks for errors after EVERY OpenGL call: loading L03A meant
# 104 thousand checks, 0.9 s. It is only useful for debugging rendering, and must
# be turned off before importing pyglet.gl (menu.py imports it too).
pyglet.options["debug_gl"] = False

from support import cache_warmer  # noqa: E402
from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from ui import gamepad as gamepadmod  # noqa: E402
from ui import keybinds  # noqa: E402
from support import level_cache  # noqa: E402
from ui import menu as menumod  # noqa: E402
from support import paths  # noqa: E402
from support import version  # noqa: E402
from ui import settings as settings_mod  # noqa: E402
from game import textures as texmod  # noqa: E402
from ui import texts  # noqa: E402
from ui.texts import t  # noqa: E402

from window.controls import Controls  # noqa: E402
from window.drawing import (BlendSorter, Drawing, FRAGMENT_SHADER, SIGNATURE, VERTEX_SHADER, WIRE_GRID,
                     WIRE_OFF)  # noqa: E402
from window.menu_pages import MenuPages  # noqa: E402
from window.overlays import FAMILIES, OVERLAYS, SHOWN_WHEN  # noqa: E402
from window import picking  # noqa: E402
from window.points import Points  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

from pyglet.gl import (GL_BLEND, GL_DEPTH_TEST, GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA,
                       glBlendFunc, glClearColor, glEnable)  # noqa: E402
from pyglet.graphics.shader import Shader, ShaderProgram  # noqa: E402
from pyglet.math import Vec3  # noqa: E402
from ui import keys_page  # noqa: E402


class Viewer(Drawing, Controls, Points, MenuPages, pyglet.window.Window):
    """The window: the level in front, the menu over it."""

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
        # a stencil buffer: the flags' see-through fills tint a pixel once per
        # kind of wall, so two pieces of the same wall cannot add their alpha
        # and draw a line that is not there (drawing.py, STENCIL_CLASSES)
        super().__init__(1280, 760, resizable=True, vsync=user_settings["vsync"],
                         caption=version.window_title(t('title'), self.build),
                         config=pyglet.gl.Config(double_buffer=True, depth_size=24, stencil_size=8))
        if level_files is None:
            self.folder = paths.find_levels_folder(data or user_settings["levels_folder"] or None)
            # Extra (the cutscenes, the menu, the credits, the `_8` variants)
            # is in the Debug build only: the other copies do not even list
            # those files
            level_files = levels_in(self.folder, extra=self.build == "Debug")
            names = [os.path.splitext(os.path.basename(p))[0].lower() for p in level_files]
            # without a requested level (or if it is missing) no level: start
            # from the main menu over the background
            index = names.index(level.lower()) if level and level.lower() in names else None
        else:
            self.folder = os.path.dirname(level_files[0]) if level_files else None
        self.level_files = level_files
        self.cache = cache
        self.index = index
        # the background filling of the piece cache: turned on by main()
        self.warm_cache = False
        self._warmer = None
        # the process building this level's flag families (cache_warmer.run_flags)
        self._flag_warmer = None
        self.current_level = None
        self._blend_sorter = None       # the still semi-transparent faces, back to front
        self._sky_sorter = None         # the same, for the sky (finding 346)
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
        # Walls -> Hard walls and Steps have three values: "off", "all" and
        # "unseen" (only those with nothing drawn over them)
        self.show_hard_walls = "off"
        self.show_steps = "off"
        # Walls: outside side, the sides where a wall does not stop you: shown, at every start
        self.show_walls_outside = True
        # Walls: edges over holes, the steps seen from a 0x7E hole: hidden, at every start
        self.show_hole_steps = False
        # "Visibility by area as in the game" (findings 293-295): off at
        # every start, no key; the area in use, kept when the camera is in
        # no collision block
        self.show_area_visibility = False
        self.area_in_use = None
        # "Moving characters" (finding 317): ON at every start and at every
        # level (the animations are still to be worked on, and on Nowhere
        # the wizard's helpers barely showed), no
        # key; on, the level is rebuilt with the movers' triangles around
        # their own origin (Level.movers)
        self.show_movers = True
        # "Who opens what" (findings 323, 331): off at every start and at every
        # level, like the flags; on, a line goes from each switch to the gate
        # it opens
        self.show_gate_links = "off"
        # Gates (finding 323): the state they are shown in. "open" at every
        # start and at every level, by the rule about defaults: opening
        # a gate only moves geometry, and the level is worth seeing the way it
        # is once you have been through it. Per group of gates (the ones one
        # switch opens) the choice can be changed for the session.
        self.gate_state = "open"
        self.session_gate_choices = {}
        # Camera and points: the shadow circle is off at every start, like the flags
        self.show_camera_shadow = False
        # the selector (Alt+click, picking.py): the stack found on the last
        # pixel, which of them is shown, and where it was clicked
        self.pick_enabled = True
        self.picked = []
        self.picked_i = 0
        self._pick_at = (-1, -1)
        # The flags, and the options that go with them, go back to these
        # values every time another level is loaded: what you switched on for one level does not follow
        # you into the next. Taken from the attributes themselves, so the ones
        # that start ON (Walls: outside side) come back on, not off. Loading
        # the SAME level again, which is what choosing a state from the menu
        # does, leaves them alone: they would go out under your hands.
        self._flags_at_start = {attr: getattr(self, attr)
                                for attr in set(OVERLAYS.values())
                                | {"show_walls_outside", "show_hole_steps",
                                   "show_area_visibility", "show_camera_shadow",
                                   "show_movers", "show_gate_links"}}
        # the gates go back to "open" at every level too, and the per-group
        # choices are forgotten: they name objects of the level that is going
        self._gate_state_at_start = self.gate_state
        self._shadow_area = None      # the area of the last shadow query (the game's hint)
        self._shadow_vao = self._shadow_vbo = None
        self._pick_vao = self._pick_vbo = None
        self._feedback = None         # (menu item, text key, time): "copied ✓" for a moment
        self._bookmark_i = 0          # the bookmark whose page is open
        self._delete_armed = False    # the first Enter on Delete
        # F1: interface hidden; the menu stays where it is but takes no input
        self.ui_hidden = False
        self.show_sky = user_settings["sky"]
        self.albedo = user_settings["albedo"]   # factor on the vertex color of textured faces
        self.show_blending = user_settings["blending"]
        # templates that the rules make appear (key G):
        # 0 off, 1 those appearing at startup, 2 all possible ones
        self.show_clones = user_settings["clones_shown"]
        # an old settings file has True/False: Skeleton/off
        self.wireframe = max(WIRE_OFF, min(WIRE_GRID, int(user_settings["wireframe"])))
        self.fov = user_settings["field_of_view"]
        # Video options -> Backface culling (finding 307): off by default
        self.backface_culling = user_settings["backface_culling"]
        self.show_status_bar = user_settings["status_bar"]
        self.speed = 20.0
        self.held_keys = set()
        self.looking = False
        self._looked = False          # the right button turned the camera (controls.py)
        self.textures = {}
        self.anim_time = 0.0
        self.animated_textures = user_settings["animated_textures"]   # animated textures (key N)
        self.fixed_tick = None  # --tick or "initial pose": animations frozen on one tick
        self.paused = False   # P: all animations stopped where they are
        self.tps = user_settings["ticks_per_second"]  # keys - and +
        self._sprite_vao = self._sprite_vbo = None
        self.bilinear = user_settings["bilinear_filter"]   # L: bilinear filter like the PC / sharp texels
        # Video options -> Distant textures: the PC has no mipmaps (306)
        self.mipmaps = user_settings["mipmaps"]
        # Video options -> Texture coordinates (findings 328, 341): "pc" (the
        # PC: byte / 255 clamped to [0.01, 0.99], repeated), "pc_amd" (an AMD
        # card: the game cuts a wider outer strip) or "psx" (the (size - 1)
        # rule); anything else saved, the old "pc_edge" too, becomes "pc"
        self.uv_rule = (user_settings["uv_rule"] if user_settings["uv_rule"] in geo.UV_RULES
                        else geo.UV_PC)
        self._uv_memo, self._uv_pushed = {}, None
        self._uniform_cache = {}   # uniforms pushed only when they change
        # entity states chosen from the menu, per level: model -> role
        self.session_poses: dict[str, dict[int, int]] = {}
        # the sky chosen from the menu where two take turns, per level: role
        self.session_sky: dict[str, int] = {}
        self.status_bar = pyglet.text.Label("", x=10, y=8, font_name=menumod.FONT, font_size=11,
                                       color=(225, 228, 235, 255))
        self._status_background = pyglet.shapes.Rectangle(0, 0, 1, 26, color=(0, 0, 0, 150))
        # the selector's card (Alt+click): a panel top left
        self.pick_text = pyglet.text.Label("", x=14, y=10, font_name=menumod.FONT, font_size=11,
                                           color=(235, 238, 245, 255), multiline=True, width=520,
                                           anchor_y="top")
        self._pick_background = pyglet.shapes.Rectangle(0, 0, 1, 1, color=(0, 0, 0, 185))
        # as in the CTR viewer: name and author on the main menu background
        self.signature = pyglet.text.Label(SIGNATURE, font_name=menumod.FONT, font_size=14,
                                       color=(235, 238, 245, 210),
                                       anchor_x="right", anchor_y="bottom")
        # keys (Help -> Keyboard) and gamepad (Help -> Gamepad), as in the CTR viewer
        self.bindings = keybinds.Bindings(user_settings["key_bindings"])
        texts.key_of_action = lambda action: keybinds.key_name(self.bindings.key(action), t)
        self.gamepad_enabled = user_settings["gamepad"]
        self.focused = True
        self.gamepad = None if screenshot else gamepadmod.Gamepad(self._on_pad_button)
        self.keyboard_page = keys_page.KeyboardPage(self.bindings, self._save_bindings)
        self.gamepad_page = keys_page.GamepadPage(
            lambda: (self.gamepad is not None and self.gamepad.connected,
                     self.gamepad.name if self.gamepad is not None else ""))
        self.menu = menumod.Menu(self._build_pages())
        self.menu.back_keys = lambda: (self.bindings.key("menu_back"), self.bindings.key("menu_back_alt"))
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

    def _use_levels_dir(self, folder):
        """Reads the levels from another folder; if a level is already open
        and the new folder has it too, it stays."""
        self.folder = folder
        current = (os.path.basename(self.level_files[self.index]).lower()
                   if self.current_level is not None and self.level_files else None)
        self.level_files = levels_in(folder, extra=self.build == "Debug")
        self.start_warmer()
        names = [os.path.basename(p).lower() for p in self.level_files]
        if current in names:
            self.index = names.index(current)
            self.menu.rebuild()
            return
        self._free_gpu()
        self.current_level = None
        self.index = 0
        self.menu.show(self._start_page())

    def start_warmer(self):
        """Starts cache_warmer.py on the levels folder. One started earlier on
        another folder is not killed (it could be saving a level): it ends
        by itself, like all of them when the viewer closes."""
        if not self.warm_cache or not self.level_files:
            return
        self._warmer = cache_warmer.start(self.folder, self.cache)

    def start_flag_warmer(self, file_path):
        """Builds this level's flag families in a process of its own, as soon
        as the level is open: turning a flag on then finds the pieces already
        saved and is only a matter of showing groups. One left over from
        another level is stopped: its work is for a level nobody is looking
        at any more, and it would only take processors away."""
        if not self.warm_cache:
            return
        if self._flag_warmer is not None and self._flag_warmer.poll() is None:
            try:
                self._flag_warmer.terminate()
            except OSError:
                pass
        self._flag_warmer = cache_warmer.start_flags(file_path, self.cache)

    def pick_up_warmed_flags(self):
        """Takes in what the flag warmer has saved meanwhile. The pieces are
        the same the viewer would build (same keys, same bytes:
        check_level_cache.py), so adding them changes nothing that is drawn,
        only how long it takes."""
        if self._flag_warmer is None or self.current_level is None:
            return
        saved = level_cache.fetch(self.cache, self.current_level.name, self._signature)
        if saved:
            for key, piece in saved.items():
                self._pieces.setdefault(key, piece)

    def on_close(self):
        self._save_settings()
        super().on_close()

    def _open_level(self, i, camera=None):
        """Loads level i. With `camera` (x, y, z, yaw, pitch) it opens it from
        there: the Era selector at the center of an era. If that level is already
        open, only the camera moves and the menu closes; a level that was
        loaded opens the menu on its main page, with Level options, whatever
        page the load started from."""
        loads = not (camera and self.current_level is not None and i == self.index)
        if loads:
            self.index = i
            self.load_level(self.level_files[i])
        if camera:
            x, y, z, yaw, pitch = camera
            self.pos, self.yaw, self.pitch = Vec3(x, y, z), yaw, pitch
        if loads:
            self.menu.show("main")
        else:
            self.menu.hide()

    def load_level(self, file_path, camera=True):
        """Loads a level. `camera=False` leaves the camera where it is: used when
        the same level is rebuilt for a state chosen from the menu.

        The same level is rebuilt with the pieces already built and the same
        textures: only what the chosen state changes is redone."""
        name = os.path.splitext(os.path.basename(file_path))[0]
        same_level = self.current_level is not None and self.current_level.name == name
        if not same_level and not self.screenshot:
            # building the level blocks the window: say what is coming, or
            # the last frame of the level that is leaving stays on screen
            self.draw_loading(levels.official_name(name) or name)
        if not same_level:
            # another level: the flags go back to how they start, before the
            # families are worked out from them
            for attr, value in self._flags_at_start.items():
                setattr(self, attr, value)
            self.area_in_use = None
            # the gates too: back to "open", and the per-group choices go,
            # because they name objects of the level that is leaving
            self.gate_state = self._gate_state_at_start
            self.session_gate_choices = {}
            # the animation clock goes back to zero, like the flags: poses,
            # bones and the movers' simulation all hang from it (`_tick`,
            # `mover_sim.run_to`), so another level carried on from the tick
            # of the one before and did not look like the level opened from
            # cold (`test_level_change.py`)
            self.anim_time = 0.0
            self._shadow_area = None    # the hint for the shadow: another level's area
            # the bookmark page names a bookmark of the level that is leaving
            self._bookmark_i, self._delete_armed = 0, False
            self.clear_pick()      # the selection names a run of the level that is leaving
        self._free_gpu(texture=not same_level)
        if not same_level:
            self.textures = {}
            # the piece memory holds one level only: RAM does not grow;
            # those built in the past come back from disk (level_cache.py)
            self._signature = level_cache.signature(file_path)
            self._pieces = level_cache.fetch(self.cache, name, self._signature) or {}
            self._texture_table = texmod.construct(os.path.dirname(file_path), name, self.cache)
        n_known = len(self._pieces)
        # the families with a flag on; on the same level also those already
        # built, whose flags are now off: they stay mounted, only hidden
        families = self._families_on() | (self.current_level.families if same_level else set())
        self.current_level = Level(file_path, self.cache, self._texture_table, self.session_poses.get(name), self._pieces,
                                   families=families, split_areas=self.show_area_visibility,
                                   movers=self.show_movers, gate_state=self.gate_state,
                                   gate_choices=self.session_gate_choices,
                                   gate_links=self.show_gate_links,
                                   sky_choice=self.session_sky.get(name))
        self.forget_uv_rule()   # the uv rule remembers each texture's size
        self.area_in_use = self.current_level.player_area
        if not same_level:
            # the level is open and drawn from here on: the families of its
            # flags are built in the background, without slowing this down
            self.start_flag_warmer(file_path)
        if len(self._pieces) > n_known:
            level_cache.store(self.cache, name, self._signature, self._pieces)
        self._prepare_groups()
        self.lo, self.hi = self.current_level.bounds()
        lo, hi = self.current_level.terrain_lo, self.current_level.terrain_hi
        if not same_level:
            # the open menu pages name things of the level that is leaving (a
            # line per group of entities, a line per group of gates): they are
            # rebuilt here and not only when the menu is reopened, so that no
            # moment goes by with the pages of one level over another
            self.menu.rebuild()
        if camera:
            self.reset_camera()
        print(f"{self.current_level.name}: {self.current_level.stat['triangles']} triangles, "
              f"{self.current_level.stat['props']} props ({self.current_level.stat.get('animated', 0)} animated) + {self.current_level.stat['sky_dome']} sky, "
              f"{len(self.current_level.face_groups)} groups, "
              f"{len(self.current_level.sizes)} texture, "
              f"{hi[0]-lo[0]:.0f} x {hi[1]-lo[1]:.0f} x {hi[2]-lo[2]:.0f} m")

    def _set_gate_links(self, mode):
        """Who opens what: off, only the gates, or every link. The level is
        rebuilt, because the names on the boxes change with it."""
        self.show_gate_links = mode
        if self.current_level is not None:
            self.load_level(self.level_files[self.index], camera=False)

    def _set_gate_state(self, state):
        """Level options -> Entities -> Gates: the level is rebuilt, because a
        gate in another state plays another animation and can be gone."""
        self.gate_state = state
        self.session_gate_choices = {}
        if self.current_level is not None:
            self.load_level(self.level_files[self.index], camera=False)

    def _set_gate_group(self, switch, state):
        """The same, for the gates one switch opens."""
        if state == self.gate_state:
            self.session_gate_choices.pop(switch, None)
        else:
            self.session_gate_choices[switch] = state
        if self.current_level is not None:
            self.load_level(self.level_files[self.index], camera=False)

    def _set_movers(self, on):
        """Moving characters: the level is rebuilt, because a mover's triangles
        are built around its own origin instead of where it is placed
        (Level.move_characters)."""
        self.show_movers = on
        if self.current_level is not None:
            self.load_level(self.level_files[self.index], camera=False)

    def _set_area_visibility(self, on):
        """Visibility by area: the level is rebuilt, because its groups are
        split by area or joined again (Level.split_areas)."""
        self.show_area_visibility = on
        if self.current_level is not None:
            self.load_level(self.level_files[self.index], camera=False)

    def _prepare_groups(self):
        """The level's groups to the graphics card, and the two sorted lists.

        The still faces that the PC draws in its one sorted list: the
        semi-transparent ones and those of a texture with a transparent entry
        (finding 306). The sky's have a list of their own, built around the
        camera like the sky itself: in the game they come after every opaque
        face of the sky, farthest first (finding 346), and the viewer clears
        the depth between the sky and the world."""
        self._blend_sorter = BlendSorter()
        self._sky_sorter = BlendSorter()
        cut_outs = self.current_level.cut_outs
        for face_group in self.current_level.face_groups.values():
            if ((face_group.blend is not None or face_group.tex_id in cut_outs)
                    and not face_group.frames and not face_group.spin
                    and face_group.category not in OVERLAYS):
                face_group.sorted = True
                sorter = self._sky_sorter if face_group.category == "sky_dome" else self._blend_sorter
                sorter.add(face_group, face_group.data)
            self._upload(face_group)
        self._upload_sorter(self._blend_sorter)
        self._upload_sorter(self._sky_sorter)

    def sky_area(self):
        """The area the game would say the camera is in: the one of the
        collision block it is in, the last one when it is in none, the placed
        player's at the start (N2 of the reverse). Kept up to date every
        frame, with Visibility by area on or off: it also chooses which sky
        to draw where a level has one per area (Era selector)."""
        level = self.current_level
        block = collision.block_at(level.collision_blocks, *self._game_point(self.pos), self.area_in_use)
        if block is not None:
            self.area_in_use = block.area
        return self.area_in_use

    def _visible_areas(self, mvp):
        """The areas the game would draw this frame (findings 293, 295): the
        area of the collision block the camera is in (the last one when it
        is in none, the placed player's at the start), and the areas reached
        through the portals on screen, as deep as the piece's opcode 0x43.
        None when the level has no areas to cut by."""
        level = self.current_level
        if self.sky_area() is None:
            return None
        visible = {self.area_in_use}
        frontier = [self.area_in_use]
        for _ in range(max(1, level.portal_depth.get(self.area_in_use, 1))):
            following = []
            for area in frontier:
                for source, target, corners in level.portals():
                    if source != area or target in visible:
                        continue
                    if self._on_screen(mvp, corners):
                        visible.add(target)
                        following.append(target)
            frontier = following
            if not frontier:
                break
        return visible

    @staticmethod
    def _on_screen(mvp, corners):
        """Whether a quad in game coordinates can be on screen: false only
        when all four corners are outside the same side of the frustum
        (the game clips the portal on the screen rectangle, finding 293)."""
        out = [0] * 6
        for point in corners:
            x, y, z = geo._transform(point)
            clip = [sum(mvp[j * 4 + i] * v for j, v in enumerate((x, y, z, 1.0))) for i in range(4)]
            w = clip[3]
            for k in range(3):
                out[2 * k] += clip[k] < -w
                out[2 * k + 1] += clip[k] > w
        return not any(n == 4 for n in out)

    def _flag_on(self, spec):
        """Whether a flag is on. Most are True or False; "Who opens what",
        Hard walls and Steps have three values and their off one is the
        string "off", which would be true for a plain truth test. A spec
        "name=value" (SHOWN_WHEN) asks for that value."""
        if "=" in spec:
            attr, wanted = spec.split("=", 1)
            return getattr(self, attr) == wanted
        value = getattr(self, spec)
        return bool(value) and value != "off"

    def _overlay_shown(self, category):
        rule = SHOWN_WHEN.get(category)
        if rule is None:
            return self._flag_on(OVERLAYS[category])
        all_of, any_of, none_of = rule
        return (all(self._flag_on(a) for a in all_of)
                and (not any_of or any(self._flag_on(a) for a in any_of))
                and not any(self._flag_on(a) for a in none_of))

    def _families_on(self):
        """The overlay families with at least one flag on."""
        return {family for family, flags in FAMILIES.items()
                if any(self._flag_on(a) for a in flags)}

    def groups_on_screen(self):
        """The groups drawn this frame, for the selector: the same rule as
        `on_draw` (without the cut by area, which needs the frame's matrix).
        Only what is drawn can be picked."""
        level = self.current_level
        if level is None:
            return []
        return [g for g in level.face_groups.values()
                if not (g.category == "props" and not self.show_props)
                and not (g.category in OVERLAYS and not self._overlay_shown(g.category))
                and not (g.category.endswith("_label") and not self.show_textures)
                and not (g.category == "clones" and self.show_clones < 2)
                and not (g.category == "clones_in_level" and self.show_clones < 1)
                and g.category != "sky_dome"]

    def pick_at(self, x, y):
        """Alt+click: the stack of what is drawn on that pixel. Clicking the
        same spot again steps down it; after the last one comes "nothing
        selected" (index len(picked)), then the first again."""
        if (abs(x - self._pick_at[0]) <= picking.SAME_PIXEL
                and abs(y - self._pick_at[1]) <= picking.SAME_PIXEL and self.picked):
            self.picked_i = (self.picked_i + 1) % (len(self.picked) + 1)
            return
        self._pick_at = (x, y)
        self.picked = picking.stack(self, x, y)
        self.picked_i = 0

    def picked_entry(self):
        """The selected thing, or None: nothing picked, or the step of the
        stack where nothing is selected."""
        if 0 <= self.picked_i < len(self.picked):
            return self.picked[self.picked_i]
        return None

    def picked_card(self):
        """The selected thing as lines of text, or [] when nothing is."""
        entry = self.picked_entry()
        if entry is None:
            return []
        head = [t("pick.of", n=self.picked_i + 1, total=len(self.picked))]
        return head + picking.card(entry, self.current_level)

    def clear_pick(self):
        self.picked, self.picked_i, self._pick_at = [], 0, (-1, -1)

    def ensure_overlays(self):
        """After a flag is turned on: if its family is not in the level yet,
        rebuild it where it is (the other pieces come from memory; the new
        ones are built now and stay in the cache). Turning a flag off only
        hides its groups."""
        level = self.current_level
        if level is not None and not self._families_on() <= level.families:
            # whatever the background process finished is used as it is; what
            # is missing is built now, only for the family that was asked for
            self.pick_up_warmed_flags()
            self.load_level(self.level_files[self.index], camera=False)
            if self.screenshot:
                # the rebuild can take longer than the wait before the
                # screenshot: it is taken after the rebuild, as at startup
                pyglet.clock.unschedule(self._screenshot)
                pyglet.clock.schedule_once(self._screenshot, 0.6)
