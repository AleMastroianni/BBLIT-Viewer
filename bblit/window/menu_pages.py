"""The viewer's menu pages: what every entry of Load level, Level options,
Flags, Camera and points, Video options, General options and Help reads and
writes.

`MenuPages` is that part of the viewer window (`app.Viewer` inherits it);
the menu engine is `menu.py` and the texts are `texts.py`.
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

import ctypes  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from ui import menu as menumod  # noqa: E402
from support import paths  # noqa: E402
from support import preferences  # noqa: E402
from support import version  # noqa: E402
from ui import texts  # noqa: E402
from ui.texts import t  # noqa: E402

from pyglet.gl import (GL_LINEAR, GL_LINEAR_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_NEAREST, GL_NEAREST,
                       GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_TEXTURE_MIN_FILTER,
                       GL_TEXTURE_WRAP_S, GL_TEXTURE_WRAP_T, glBindTexture,
                       glDeleteTextures, glTexParameteri)  # noqa: E402

from window.drawing import WIRE_GRID, WIRE_OFF, WIRE_SKELETON  # noqa: E402
from window.scene import resolve_levels_folder  # noqa: E402

try:
    from support import private_export  # noqa: E402  (private copies only: left out of the public version)
except ImportError:
    private_export = None

# The vertical field of view of the PC game, 51,28 degrees (finding 327):
# 51 in the menu, next to the round values the viewer had before.
PC_FIELD_OF_VIEW = 51
FIELD_OF_VIEW_STOPS = sorted({PC_FIELD_OF_VIEW} | set(range(40, 101, 5)))
# Camera and points -> Camera speed: the base speeds offered, in metres per
# second (the opening speed of a level, radius / 12, is not on the list and
# moves to the next one either way)
CAMERA_SPEEDS = [1, 2, 3, 5, 8, 10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500]


class MenuPages:
    """The menu pages of the viewer window (`app.Viewer` inherits it)."""

    def _start_page(self):
        """The page with no level open: the main menu if there are
        levels to load, otherwise the one explaining what to copy."""
        return "main" if self.level_files else "missing_data"

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

        def level_item(title_text, levid, file, part_label, note, single_part, available_files, extra,
                       under_title=False):
            """A menu row for a level: the part (or the title, if the
            level is in a single piece), the file on the right, the LevID below. If
            the file is not in the levels folder the row is grayed out. Under its
            own title row (`under_title`) a single level shows the part, the
            note or, with neither, the title again. The game's own names follow
            the interface language (levels.name), read when drawn."""
            i = available_files.get(file.upper())
            ti_of = lambda ti=title_text: levels.name(ti)
            note_of = lambda n=note: levels.name(n)
            if part_label is not None:
                label_text = lambda p=part_label: t("load.part", n=p) + (f" — {note_of()}" if note_of() else "")
            elif under_title:
                label_text = lambda: note_of() or ti_of()
            else:
                label_text = lambda: ti_of() + (f" ({note_of()})" if note_of() else "")
            if single_part and part_label is not None:
                label_text = lambda p=part_label: f"{ti_of()} — {t('load.part', n=p)}"
            if extra.get("label"):
                label_text = lambda e=extra["label"]: t(e)
            # the full name in the description: the label may be shortened.
            # The Debug build adds the level's old note from the LevID
            # spreadsheet, for now
            old_note = extra.get("sheet_note") if self.build == "Debug" else None
            entry_name = lambda p=part_label, e=extra.get("label"), o=old_note: " — ".join(
                x for x in (ti_of(), t(e) if e else "", t("load.part", n=p) if p is not None else "", note_of())
                if x) + (f" · {o}" if o else "")
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

        def level_list(titles, every_title=False):
            """The rows of a list of titles. A title with several levels gets
            a title row above its parts; with `every_title` (the eras, Extra)
            also a title with a single level, so that it does not look like
            one more part of the title above."""
            menu_items, available_files = [], per_file()
            for title_text, title_entries in titles:
                single_part = len(title_entries) == 1
                under_title = not single_part or every_title
                if under_title:
                    menu_items.append(M.Section(None, label_text=lambda ti=title_text: levels.name(ti)))
                for v in title_entries:
                    menu_items.append(level_item(title_text, v[0], v[1], v[2], v[3], single_part and not under_title,
                                             available_files, levels.extra_of(v), under_title))
            return menu_items

        def load_items():
            # the Era selector first, then the eras
            menu_items = [M.Submenu("load.eras", "eras", desc="load.desc_eras")]
            menu_items += [M.Submenu(era, f"era:{era}", desc="load.desc_era")
                           for era, _titles, _bonus in levels.ERAS]
            # Nowhere under Dimension X, opened directly
            menu_items += level_list(levels.NOWHERE)
            # Extra (the `_8` variants, and inside it the menu, the credits
            # and the cutscenes) only in the Debug build: no other copy
            # lists any of it
            if self.build == "Debug":
                menu_items += [M.Section(None, label_text=lambda: ""),
                         M.Submenu("extra.title", "extra", desc="load.desc_extra")]
            menu_items += [M.Back()]
            return menu_items

        def era_page(titles, bonus):
            def build_items():
                menu_items = level_list(titles, every_title=True)
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
                    menu_items += level_list(titles, every_title=section_list in (levels.EXTRA, levels.HUB))
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
                def set_flag(v):
                    setattr(self, attr_name, v)
                    self.ensure_overlays()
                return M.YesNo(item_key, lambda: getattr(self, attr_name), set_flag, desc)
            return [M.Submenu("level.walls", "walls", desc="desc.walls"),
                    item("level.no_collision", "show_no_collision", "desc.no_collision"),
                    item("level.collision_boxes", "show_collision_boxes", "desc.collision_boxes"),
                    item("level.death_zones", "show_death_zones", "desc.death_zones"),
                    item("level.teleport_zones", "show_teleport_zones", "desc.teleport_zones"),
                    item("level.ground", "show_ground", "desc.ground"),
                    M.Choice("level.gate_links",
                             [("off", "level.gate_links.off"), ("gates", "level.gate_links.gates"),
                              ("all", "level.gate_links.all")],
                             lambda: self.show_gate_links, self._set_gate_links, "desc.gate_links"),
                    item("level.faces_1000", "show_faces_1000", "desc.faces_1000"),
                    M.Back()]

        def walls():
            """Flags -> Walls: every wall flag of the heightmap in one
            place. Hard walls and Steps choose between
            all of them and only the invisible ones."""
            def three_way(item_key, attr_name, desc):
                def set_flag(v):
                    setattr(self, attr_name, v)
                    self.ensure_overlays()
                return M.Choice(item_key, [("off", "level.walls.off"), ("all", "level.walls.all"),
                                           ("unseen", "level.walls.unseen")],
                                lambda: getattr(self, attr_name), set_flag, desc)

            def set_area_boxes(v):
                self.show_area_boxes = v
                self.ensure_overlays()
            return [three_way("level.hard_walls", "show_hard_walls", "desc.hard_walls"),
                    three_way("level.steps", "show_steps", "desc.steps"),
                    M.YesNo("level.hole_steps", lambda: self.show_hole_steps,
                            lambda v: setattr(self, "show_hole_steps", v), "desc.hole_steps"),
                    M.YesNo("level.area_boxes", lambda: self.show_area_boxes, set_area_boxes, "desc.area_boxes"),
                    M.YesNo("level.walls_outside", lambda: self.show_walls_outside,
                            lambda v: setattr(self, "show_walls_outside", v), "desc.walls_outside"),
                    M.Back()]

        def copy_item(item_key, desc, make_text, disabled=False):
            """An Action that copies to the clipboard and says "copied ✓"."""
            item = M.Action(item_key, lambda: self._copy(item_key, make_text()), desc=desc,
                            right_text=lambda: self._feedback_text(item_key))
            item.disabled = disabled
            return item

        def pick_page():
            """The selector: what Alt+click took, in words, with Copy."""
            menu_items = [M.YesNo("pick.enabled", lambda: self.pick_enabled,
                                  lambda v: setattr(self, "pick_enabled", v), "pick.desc"),
                          M.Section(None, label_text=lambda: "")]
            lines = self.picked_card()
            if not lines:
                menu_items.append(M.Info(lambda: t("pick.none")))
            else:
                for line in lines:
                    menu_items.append(M.Info(lambda line=line: line))
            clear_item = M.Action("pick.clear", self.clear_pick)
            clear_item.disabled = not lines
            menu_items += [M.Section(None, label_text=lambda: ""),
                           copy_item("pick.copy", "pick.desc_copy",
                                     lambda: chr(10).join(self.picked_card()), disabled=not lines),
                           clear_item,
                           M.Back()]
            return menu_items

        def camera():
            if self.current_level is None:
                return [M.Info(lambda: t("level.no_level")), M.Back()]
            marks = self._bookmarks()
            menu_items = [M.Info(lambda: t("camera.now"), lambda: self._coords_text(self._game_point(self.pos))),
                          M.Info(lambda: t("camera.shadow_point"), lambda: self._shadow_text(self.pos)),
                          M.YesNo("camera.show_shadow", lambda: self.show_camera_shadow,
                                  lambda v: setattr(self, "show_camera_shadow", v), "desc.show_shadow"),
                          # the camera's base speed (the wheel only scrolls the
                          # menus now; Shift and Ctrl held stay)
                          M.Number("camera.speed", lambda: self.speed, lambda v: setattr(self, "speed", float(v)),
                                   CAMERA_SPEEDS[0], CAMERA_SPEEDS[-1], number_format="{:.0f} m/s",
                                   desc="desc.camera_speed", stops=CAMERA_SPEEDS),
                          M.Action("camera.add", self._add_bookmark, desc="desc.camera_add"),
                          *([copy_item("camera.copy_ce", "desc.copy_ce",
                                       lambda: self._point_text("private", self.pos, t("camera.now")))]
                            if private_export else []),
                          copy_item("camera.copy_lua", "desc.copy_lua",
                                    lambda: self._point_text("lua", self.pos, t("camera.now"))),
                          copy_item("camera.copy_all_lua", "desc.copy_all_lua", self._all_bookmarks_lua,
                                    disabled=not marks),
                          M.Section("camera.bookmarks")]
            for i, mark in enumerate(marks):
                menu_items.append(M.Action(None, lambda i=i: self._open_bookmark(i), desc="desc.bookmark",
                                           label_text=lambda m=mark: self._mark_name(m),
                                           right_text=lambda m=mark: self._coords_text(
                                               (m["x"], m["y"], m["z"])) + "   ›"))
            if not marks:
                menu_items.append(M.Info(lambda: t("camera.no_bookmarks")))
            # the selector last, so the lines above keep their place
            menu_items.append(M.Section(None, label_text=lambda: ""))
            menu_items.append(M.Submenu("pick.title", "pick", desc="pick.desc"))
            menu_items.append(M.Back())
            return menu_items

        def bookmark():
            marks = self._bookmarks()
            if not (self.current_level is not None and 0 <= self._bookmark_i < len(marks)):
                return [M.Info(lambda: t("camera.no_bookmarks")), M.Back()]
            mark = marks[self._bookmark_i]
            pos = self._mark_pos(mark)
            name = self._mark_name(mark)
            return [M.Info(lambda: t("camera.now"), lambda: self._coords_text((mark["x"], mark["y"], mark["z"]))),
                    M.Info(lambda: t("camera.shadow_point"), lambda: self._shadow_text(pos)),
                    M.Action("bookmark.go", self._go_to_bookmark, desc="desc.bookmark_go"),
                    M.Action("bookmark.replace", lambda: self._replace_bookmark("bookmark.replace"),
                             right_text=lambda: self._feedback_text("bookmark.replace", "bookmark.replaced")),
                    *([copy_item("camera.copy_ce", "desc.copy_ce", lambda: self._point_text("private", pos, name))]
                      if private_export else []),
                    copy_item("camera.copy_lua", "desc.copy_lua", lambda: self._point_text("lua", pos, name)),
                    M.Action(None, self._delete_bookmark, desc="desc.bookmark_delete",
                             label_text=lambda: t("bookmark.confirm_delete" if self._delete_armed
                                                  else "bookmark.delete")),
                    M.Back()]

        def bookmark_title():
            marks = self._bookmarks()
            name = self._mark_name(marks[self._bookmark_i]) if 0 <= self._bookmark_i < len(marks) else "—"
            return t("bookmark.title", name=name, level=self.current_level.name if self.current_level else "—")

        def level():
            if self.current_level is None:
                return [M.Info(lambda: t("level.no_level")), M.Back()]
            menu_items = [M.Submenu("level.flags", "flags", desc="desc.flags"),
                    M.Submenu("level.camera", "camera", desc="desc.camera"),
                    M.Section("level.rendering"),
                    M.YesNo("level.texture", lambda: self.show_textures,
                           lambda v: setattr(self, "show_textures", v), "desc.texture"),
                    M.YesNo("level.props", lambda: self.show_props,
                           lambda v: setattr(self, "show_props", v), "desc.props"),
                    M.YesNo("level.sky", lambda: self.show_sky,
                           lambda v: setattr(self, "show_sky", v), "desc.sky"),
                    M.YesNo("level.blending", lambda: self.show_blending,
                           lambda v: setattr(self, "show_blending", v), "desc.blending"),
                    M.Choice("level.wireframe",
                             [(WIRE_OFF, "level.wire.off"), (WIRE_SKELETON, "level.wire.skeleton"),
                              (WIRE_GRID, "level.wire.grid")],
                             lambda: self.wireframe, lambda v: setattr(self, "wireframe", v), "desc.wireframe"),
                    M.YesNo("level.area_visibility", lambda: self.show_area_visibility,
                            self._set_area_visibility, "desc.area_visibility"),
                    M.Section("level.entities"),
                    M.Choice("level.animations",
                             [("playing", "level.anim.playing"), ("paused", "level.anim.paused"),
                              ("pose", "level.anim.pose")],
                             self._animation_state, self._set_animation_state, "desc.animations"),
                    M.Number("level.tps", lambda: self.tps, self._set_tps, 1, 60,
                             desc="desc.tps"),
                    M.YesNo("level.texanim", lambda: self.animated_textures,
                           lambda v: setattr(self, "animated_textures", v), "desc.texanim"),
                    M.YesNo("level.movers", lambda: self.show_movers,
                            self._set_movers, "desc.movers"),
                    M.Choice("level.clones",
                             [(0, "level.clones.off"), (1, "level.clones.in_level"),
                              (2, "level.clones.all")],
                             lambda: self.show_clones, lambda v: setattr(self, "show_clones", v),
                             "desc.clones")]
            if self.current_level.gates:
                # one row, whatever the number of switches: the choices are
                # on a page of their own (gates_page)
                menu_items.append(M.Submenu("level.gates", "gates", desc="desc.gates"))
            for entity_group in self.current_level.pref["entity_groups"]:
                menu_items.append(M.Choice(f"group.{entity_group['name']}",
                                     [(role, f"state.{name}") for role, name in entity_group["states"]],
                                     lambda g=entity_group: self._group_state(g),
                                     lambda role, g=entity_group: self._set_group_state(g, role),
                                     "desc.group"))
            if self.current_level.sky_choices:
                # the skies the game alternates (finding 314): one at a time,
                # the level's starting one first, like the states above
                default = self.current_level.sky_choices[0][0]
                menu_items.append(M.Choice(
                    "level.sky_choice",
                    [(role, lambda n=n, at_start=at_start, role=role:
                        t("level.sky_choice.start" if at_start else
                          "level.sky_choice.default" if role == default and not at_start else
                          "level.sky_choice.other", n=n))
                     for role, n, at_start in self.current_level.sky_choices],
                    lambda: self.current_level.sky_choices[0][0], self._set_sky_choice,
                    "desc.sky_choice"))
            menu_items.append(M.Back())
            return menu_items

        def gates_page():
            """Gates: the general state, then one choice per switch."""
            if self.current_level is None or not self.current_level.gates:
                return [M.Info(lambda: t("level.no_level")), M.Back()]
            states = [("open", "level.gates.open"), ("shut", "level.gates.shut"),
                      ("game", "level.gates.game")]
            menu_items = [M.Choice("level.gates.every", states, lambda: self.gate_state,
                                   self._set_gate_state, "desc.gates")]
            if self.current_level.gate_groups:
                menu_items.append(M.Section("level.gates.by_switch"))
            for switch in sorted(self.current_level.gate_groups):
                menu_items.append(M.Choice(
                    None, states,
                    lambda sw=switch: self.session_gate_choices.get(sw, self.gate_state),
                    lambda state, sw=switch: self._set_gate_group(sw, state),
                    "desc.gate_group",
                    label_text=lambda sw=switch: t("level.gates.of", n=sw)))
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
                    M.Choice("video.uv", [(geo.UV_PC, "video.uv.pc"),
                                          (geo.UV_PC_AMD, "video.uv.amd"), (geo.UV_PSX, "video.uv.psx")],
                             lambda: self.uv_rule, self._set_uv_rule, "desc.uv"),
                    M.Choice("video.distant", [(False, "video.distant.pc"), (True, "video.distant.smooth")],
                             lambda: self.mipmaps, self._set_mipmaps, "desc.distant"),
                    M.Number("video.fov", lambda: self.fov, lambda v: setattr(self, "fov", v),
                             40, 100, increment=5, number_format="{:.0f}°",
                             desc="desc.fov", stops=FIELD_OF_VIEW_STOPS,
                             labels={PC_FIELD_OF_VIEW: "video.fov.pc"}),
                    M.YesNo("video.backface", lambda: self.backface_culling,
                            lambda v: setattr(self, "backface_culling", v), "desc.backface"),
                    M.Back()]

        def general_items():
            return [M.Choice("general.language",
                             [(c, lambda c=c: texts.LANGUAGE_NAMES[c]) for c in texts.LANGUAGES],
                             texts.language, self._set_language, "desc.language"),
                    M.YesNo("general.status_bar", lambda: self.show_status_bar,
                           lambda v: setattr(self, "show_status_bar", v), "desc.status_bar"),
                    M.Submenu("general.keys", "help", desc="desc.general_keys"),
                    M.YesNo("general.gamepad", lambda: self.gamepad_enabled, self._set_gamepad,
                            "desc.general_gamepad"),
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
            # as in the CTR viewer: Help -> Keyboard / Gamepad (drawn pages)
            return [M.Submenu("help.keyboard", "keyboard", desc="desc.help_keyboard"),
                    M.Submenu("help.gamepad", "gamepad", desc="desc.help_gamepad"),
                    M.Submenu("help.about", "about", desc="desc.help_about"),
                    M.Back()]

        def about_items():
            # the version comes from support/version.py, like the window title
            return [M.Info(lambda: t("title"), lambda: version.VERSION),
                    M.Info(lambda: t("about.author"), "AleMastroianni"),
                    M.Info(lambda: t("about.build"), lambda: self.build or "—"),
                    M.Back()]

        return {
            # as in the CTR viewer: name and author on the main page
            "main": M.Page(lambda: t("menu.main"), main_items, 360),
            "load": M.Page(lambda: t("load.title"), load_items, 360),
            "eras": M.Page(lambda: t("load.eras"), section_pages(levels.HUB), 720),
            "extra": M.Page(lambda: t("extra.title"), section_pages(levels.EXTRA), 720),
            "cutscenes": M.Page(lambda: t("extra.cutscenes"), section_pages(levels.CUTSCENES), 720),
            **{f"era:{era}": M.Page(lambda era=era: t(era), era_page(titles, bonus), 720)
               for era, titles, bonus in levels.ERAS},
            "level": M.Page(lambda: t("level.title",
                                          n=self.current_level.name if self.current_level else "—"), level),
            "flags": M.Page(lambda: t("level.flags"), flags, 440),
            "gates": M.Page(lambda: t("level.gates"), gates_page, 440),
            "walls": M.Page(lambda: t("level.walls"), walls, 440),
            "camera": M.Page(lambda: t("camera.title", level=self.current_level.name if self.current_level else "—"),
                             camera, 600),
            "bookmark": M.Page(bookmark_title, bookmark, 600),
            "pick": M.Page(lambda: t("pick.title"), pick_page, 680),
            "missing_data": M.Page(lambda: t("data.title"), data_items, 640),
            "video": M.Page(lambda: t("video.title"), video),
            "general": M.Page(lambda: t("general.title"), general_items),
            "help": M.Page(lambda: t("help.title"), help_items),
            "about": M.Page(lambda: t("help.about"), about_items),
            "keyboard": M.Page(lambda: t("help.keyboard"), lambda: [], custom=self.keyboard_page),
            "gamepad": M.Page(lambda: t("help.gamepad"), lambda: [], custom=self.gamepad_page),
        }

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
        self._push_filters()

    def _set_mipmaps(self, mipmaps):
        """Video options -> Distant textures. The chain is always built when
        a texture is uploaded, so switching only changes how it is read:
        nothing is rebuilt and the picture changes on the same frame."""
        self.mipmaps = mipmaps
        self._push_filters()

    def _push_filters(self):
        for name in self.texture_names():
            glBindTexture(GL_TEXTURE_2D, name)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
                            GL_LINEAR if self.bilinear else GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self.min_filter())

    def _set_uv_rule(self, rule):
        """Video options -> Texture coordinates (findings 328, 341). Nothing is
        rebuilt: the buffers keep byte / 255 and the rule is applied while
        drawing; only what happens past the edge of a texture is a property of
        the texture itself."""
        self.uv_rule = rule
        self.forget_uv_rule()
        wrap = self.uv_wrap()
        for name in self.texture_names():
            glBindTexture(GL_TEXTURE_2D, name)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, wrap)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, wrap)

    def _set_texture_scale(self, scale_factor):
        """The textures are rebuilt at the new scale the next time they are needed."""
        self.scale_factor = scale_factor
        names = list(self.texture_names())
        if names:
            glDeleteTextures(len(names), (ctypes.c_uint * len(names))(*names))
        self.textures = {}

    def _group_state(self, entity_group):
        own = self.session_poses.get(self.current_level.name, {})
        default_role = preferences.for_level(self.current_level.name)["pose"].get(entity_group["model"])
        return own.get(entity_group["model"], default_role)

    def _set_sky_choice(self, role):
        """Level options -> Sky: the level is rebuilt with the other sky; the
        choice holds for the session, per level, like the object states."""
        self.session_sky[self.current_level.name] = role
        self.load_level(self.level_files[self.index], camera=False)

    def _set_group_state(self, entity_group, role):
        """A state chosen from the menu: lasts for the session, the level is rebuilt."""
        self.session_poses.setdefault(self.current_level.name, {})[entity_group["model"]] = role
        self.load_level(self.level_files[self.index], camera=False)

    def _toggle_vsync(self, v):
        self.user_settings["vsync"] = v
        self.set_vsync(v)

    def _set_language(self, language):
        texts.set_language(language)
        self.set_caption(version.window_title(t('title'), self.build))
        self.menu.rebuild()

    def _set_gamepad(self, on):
        self.gamepad_enabled = on
        if self.gamepad is not None:
            self.gamepad.release()

    def _save_settings(self):
        """The current state into the settings: what was changed with the
        shortcut keys also persists to the next run."""
        user_settings = self.user_settings
        user_settings["language"] = texts.language()
        user_settings["texture"], user_settings["props"], user_settings["sky"] = self.show_textures, self.show_props, self.show_sky
        user_settings["blending"], user_settings["wireframe"] = self.show_blending, int(self.wireframe)
        user_settings["animated_textures"], user_settings["clones_shown"] = self.animated_textures, self.show_clones
        user_settings["ticks_per_second"] = float(self.tps)
        user_settings["fullscreen"], user_settings["bilinear_filter"] = self.fullscreen, self.bilinear
        user_settings["mipmaps"] = self.mipmaps
        user_settings["texture_scale"], user_settings["albedo"] = self.scale_factor, float(self.albedo)
        user_settings["uv_rule"] = self.uv_rule
        user_settings["field_of_view"], user_settings["status_bar"] = self.fov, self.show_status_bar
        user_settings["backface_culling"] = self.backface_culling
        user_settings["key_bindings"], user_settings["gamepad"] = self.bindings.stored(), self.gamepad_enabled
        user_settings.persist()

    def _save_bindings(self):
        """Help -> Keyboard: a complete set of keys is saved at once."""
        self.user_settings["key_bindings"] = self.bindings.stored()
        self.user_settings.persist()

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
