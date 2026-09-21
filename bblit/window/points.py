"""Camera and points, for the glitch hunting: where the camera is in game
units, where Bugs would land under it (the shadow point), the bookmarks of
a level and the lines copied for memory tools and BizHawk.

`Points` is that part of the viewer window (`app.Viewer` inherits it).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re  # noqa: E402
import time  # noqa: E402

from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from pyglet.math import Vec3  # noqa: E402
from ui.texts import t  # noqa: E402

try:
    from support import private_export  # noqa: E402  (private copies only: left out of the public version)
except ImportError:
    private_export = None


class Points:
    """Camera and points (`app.Viewer` inherits it)."""

    SHADOW_RADIUS = 32      # game units (25 cm): a marker, not the game's shadow size
    FEEDBACK_SECONDS = 2.0

    @staticmethod
    def _game_point(pos):
        """A viewer position (metres, axes x, -y, -z) in integer game units."""
        u = geo.UNITS_PER_METER
        return round(pos.x * u), round(-pos.y * u), round(-pos.z * u)

    def _shadow_of(self, pos):
        """The shadow point under a camera position: the point in game units
        and the collision block it lands on (collision.ground_below: the
        game's ground query, falling straight down), or the camera point and
        None when nothing is under it."""
        gx, gy, gz = self._game_point(pos)
        found = collision.ground_below(self.current_level.collision_blocks, gx, gy, gz)
        if found is None:
            return (gx, gy, gz), None
        ground, grid_block = found
        return (gx, ground, gz), grid_block

    @staticmethod
    def _coords_text(point):
        return ", ".join(str(round(w)) for w in point)

    def _shadow_text(self, pos):
        point, grid_block = self._shadow_of(pos)
        if grid_block is None:
            return t("camera.no_ground")
        return f"{self._coords_text(point)}   ·   {t('camera.area', area=grid_block.area)}"

    def _bookmarks(self):
        """The bookmarks of the open level, only the well-formed ones (the
        settings file can be edited by hand)."""
        if self.current_level is None:
            return []
        marks = self.user_settings["bookmarks"].get(self.current_level.name, [])
        keys = ("x", "y", "z", "yaw", "pitch")
        return [m for m in marks if isinstance(m, dict) and isinstance(m.get("n"), int)
                and all(isinstance(m.get(k), (int, float)) and not isinstance(m.get(k), bool) for k in keys)] \
            if isinstance(marks, list) else []

    def _store_bookmarks(self, marks):
        all_marks = dict(self.user_settings["bookmarks"])     # never the DEFAULTS dict
        if marks:
            all_marks[self.current_level.name] = marks
        else:
            all_marks.pop(self.current_level.name, None)
        self.user_settings["bookmarks"] = all_marks
        self.user_settings.persist()

    def _camera_mark(self, n):
        u = geo.UNITS_PER_METER
        return {"n": n, "x": round(self.pos.x * u, 2), "y": round(-self.pos.y * u, 2),
                "z": round(-self.pos.z * u, 2), "yaw": round(self.yaw, 2), "pitch": round(self.pitch, 2)}

    @staticmethod
    def _mark_pos(mark):
        u = geo.UNITS_PER_METER
        return Vec3(mark["x"] / u, -mark["y"] / u, -mark["z"] / u)

    @staticmethod
    def _mark_name(mark):
        name = mark.get("name")
        return name if isinstance(name, str) and name.strip() else t("camera.bookmark", n=mark["n"])

    def _add_bookmark(self):
        marks = self._bookmarks()
        marks.append(self._camera_mark(max((m["n"] for m in marks), default=0) + 1))
        self._store_bookmarks(marks)
        self.menu.rebuild()

    def _open_bookmark(self, i):
        self._bookmark_i = i
        self._delete_armed = False
        self.menu.open_page("bookmark")

    def _go_to_bookmark(self):
        marks = self._bookmarks()
        if 0 <= self._bookmark_i < len(marks):
            mark = marks[self._bookmark_i]
            self.pos, self.yaw, self.pitch = self._mark_pos(mark), float(mark["yaw"]), float(mark["pitch"])
            self.menu.hide()

    def _replace_bookmark(self, item_key):
        marks = self._bookmarks()
        if 0 <= self._bookmark_i < len(marks):
            old = marks[self._bookmark_i]
            new = self._camera_mark(old["n"])
            if "name" in old:
                new["name"] = old["name"]
            marks[self._bookmark_i] = new
            self._store_bookmarks(marks)
            self._delete_armed = False
            self._feedback = (item_key, time.monotonic())
            self.menu.rebuild()

    def _delete_bookmark(self):
        marks = self._bookmarks()
        if not self._delete_armed:
            self._delete_armed = True
            return
        if 0 <= self._bookmark_i < len(marks):
            del marks[self._bookmark_i]
            self._store_bookmarks(marks)
        self._delete_armed = False
        self.menu.go_back()
        self.menu.rebuild()

    def _point_text(self, kind, pos, label):
        """One point for the clipboard. `kind` "lua": a table entry like the
        waypoints of BBLIT_Tasing.lua; "private": the line of private_export.
        The shadow point in game units; with nothing under the camera, the
        camera point, said in the comment."""
        (x, y, z), grid_block = self._shadow_of(pos)
        note = t("export.shadow") if grid_block is not None else t("export.camera_no_ground")
        level = self.current_level.name
        if kind == "private":
            return private_export.line(level, (x, y, z), label, note)
        return f"{{ X = {x}, Y = {y}, Z = {z} }}, -- BBLIT {level}, {label}, {note}"

    def _all_bookmarks_lua(self):
        level = self.current_level.name
        table_name = re.sub(r"\W", "_", f"{t('export.table_name')}_{level}")
        lines = [f"-- BBLIT {level}: {t('export.table_comment')}", f"local {table_name} = {{"]
        lines += ["  " + self._point_text("lua", self._mark_pos(m), self._mark_name(m)) for m in self._bookmarks()]
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _copy(self, item_key, text):
        try:
            self.set_clipboard_text(text)
        except Exception as e:  # noqa: BLE001
            print(f"clipboard not available: {e}")
            return
        self._delete_armed = False
        self._feedback = (item_key, time.monotonic())

    def _feedback_text(self, item_key, text_key="camera.copied"):
        fresh = (self._feedback is not None and self._feedback[0] == item_key
                 and time.monotonic() - self._feedback[1] < self.FEEDBACK_SECONDS)
        return t(text_key) if fresh else ""
