"""Camera and input: keyboard, mouse and gamepad, and what each key does
in the scene.

`Controls` is the input part of the viewer window (`app.Viewer` inherits
it).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math  # noqa: E402

import pyglet  # noqa: E402

# pyglet checks for errors after EVERY OpenGL call: loading L03A meant
# 104 thousand checks, 0.9 s. It is only useful for debugging rendering, and must
# be turned off before importing pyglet.gl (menu.py imports it too).
pyglet.options["debug_gl"] = False

from pyglet.math import Vec3  # noqa: E402

from game import geometry as geo  # noqa: E402

import time  # noqa: E402


class Controls:
    """The input part of the viewer window (`app.Viewer` inherits it)."""

    PAD_MENU_KEYS = {"dpup": "UP", "dpdown": "DOWN", "dpleft": "LEFT", "dpright": "RIGHT", "a": "ENTER"}
    on_mouse_drag = lambda self, x, y, dx, dy, b, m: self.on_mouse_motion(x, y, dx, dy)  # noqa: E731

    def reset_camera(self):
        """The opening camera (`opening_camera`)."""
        self.pos, self.yaw, self.pitch, self.speed = opening_camera(self.current_level)

    def on_key_press(self, symbol, modifiers):
        if self.screenshot:
            return      # screenshot mode: see update
        k = pyglet.window.key
        if self.menu.capturing():
            # Help -> Keyboard waits for a key: every key goes there, Esc too
            self.menu.press(symbol, modifiers)
            return pyglet.event.EVENT_HANDLED
        if symbol == self.bindings.key("hide_ui") and self.current_level is not None:
            # the interface covered: nothing drawn over the scene, and the
            # menu (even if open) takes no keys, mouse or wheel until F1 again
            self.ui_hidden = not self.ui_hidden
            return pyglet.event.EVENT_HANDLED
        if self.ui_hidden and symbol == k.ESCAPE:
            self.ui_hidden = False      # Esc uncovers, and does nothing else
            return pyglet.event.EVENT_HANDLED
        if symbol == k.ESCAPE:
            self._toggle_menu()
            return pyglet.event.EVENT_HANDLED    # pyglet would close the window
        if symbol in (k.ENTER, k.NUM_ENTER) and modifiers & k.MOD_ALT:
            self.set_fullscreen(not self.fullscreen)
            return
        if (not self.ui_hidden and self.menu.press(symbol, modifiers)) or self.current_level is None:
            return
        actions = self.bindings.actions_for(symbol, "scene")
        if symbol in (k.NUM_SUBTRACT, k.NUM_ADD):
            actions = ["tps_down" if symbol == k.NUM_SUBTRACT else "tps_up"]    # fixed, besides the bound keys
        for action in actions:
            self._scene_action(action)
        if not actions or all(a in ("camera_up", "camera_down") for a in actions):
            self.held_keys.add(symbol)

    def _toggle_menu(self):
        """Esc (and Start on the gamepad): as in the CTR viewer, it opens and
        closes the menu; Quit is in the menu."""
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

    def _scene_action(self, action):
        """A rebindable action with the menu closed (keybinds.ACTIONS)."""
        if action == "textures":
            self.show_textures = not self.show_textures
        elif action == "wireframe":
            self.wireframe = (self.wireframe + 1) % 3      # off, Skeleton, Grid
        elif action == "props":
            self.show_props = not self.show_props
        elif action == "sky":
            self.show_sky = not self.show_sky
        elif action == "blending":
            self.show_blending = not self.show_blending
        elif action == "clones":
            self.show_clones = (self.show_clones + 1) % 3
        elif action == "texanim":
            self.animated_textures = not self.animated_textures
        elif action == "filter":
            self._set_filter(not self.bilinear)
        elif action == "pause":
            self.fixed_tick = None
            self.paused = not self.paused
        elif action in ("tps_down", "tps_up"):
            step = -1.0 if action == "tps_down" else 1.0
            self._set_tps(max(1.0, min(60.0, self.tps + step)))
        elif action == "reset_camera":
            self.reset_camera()
        elif action in ("level_prev", "level_next"):
            step = -1 if action == "level_prev" else 1
            self.index = (self.index + step) % len(self.level_files)
            self.load_level(self.level_files[self.index])

    def _on_pad_button(self, button):
        # out of focus the pad belongs to the other window (an emulator)
        if self.screenshot or not self.gamepad_enabled or not self.focused or self.menu.capturing():
            return
        k = pyglet.window.key
        if button == "start":
            if self.ui_hidden:
                self.ui_hidden = False
            else:
                self._toggle_menu()
        elif button == "back":
            if self.current_level is not None:
                self.ui_hidden = not self.ui_hidden
        elif self.ui_hidden or not self.menu.is_open:
            return
        elif button in self.PAD_MENU_KEYS:
            self.menu.press(getattr(k, self.PAD_MENU_KEYS[button]), 0)
        elif button == "b":
            self.menu.press(self.bindings.key("menu_back") or self.bindings.key("menu_back_alt"), 0)

    def on_key_release(self, symbol, modifiers):
        self.held_keys.discard(symbol)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.screenshot:
            return
        # the selector: Alt+click reads what is drawn on that pixel, and
        # clicking the same spot again steps down the stack (picking.py).
        # The one key added since the keys were settled
        if (button == pyglet.window.mouse.LEFT and modifiers & pyglet.window.key.MOD_ALT
                and self.pick_enabled and self.current_level is not None):
            self.pick_at(x, y)
            return pyglet.event.EVENT_HANDLED
        if not self.ui_hidden and self.menu.click(x, y, button):
            return
        if button == pyglet.window.mouse.RIGHT:
            self.looking = True
            self.set_exclusive_mouse(True)

    def on_mouse_release(self, x, y, button, modifiers):
        if button == pyglet.window.mouse.RIGHT and self.looking:
            self.looking = False
            self.set_exclusive_mouse(False)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.screenshot or (not self.ui_hidden and self.menu.mouse_over(x, y)):
            return
        if self.looking:
            self.yaw += dx * 0.15
            self.pitch = max(-89.0, min(89.0, self.pitch + dy * 0.15))

    def on_mouse_scroll(self, x, y, sx, sy):
        """The wheel scrolls the menu's list and nothing else: it no longer
        changes a value or, with the menu closed, the camera speed, which is
        Camera and points -> Camera speed."""
        if self.screenshot or self.ui_hidden:
            return
        self.menu.wheel(x, y, sy)

    def on_activate(self):
        self.focused = True

    def on_deactivate(self):
        """Out of focus (for example while switching to an emulator): no keys
        left held down and no mouse look, as in the CTR viewer."""
        self.focused = False
        self.held_keys.clear()
        if self.gamepad is not None:
            self.gamepad.release()
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
        if self._feedback is not None and time.monotonic() - self._feedback[1] >= self.FEEDBACK_SECONDS:
            self._feedback = None       # "copied ✓" goes away
            self.menu.dirty = True
        if (self.menu.is_open and not self.ui_hidden) or self.current_level is None:
            return      # with the menu open (or no level) the camera stays still
        k = pyglet.window.key
        pad = self.gamepad if (self.gamepad is not None and self.gamepad_enabled and self.focused
                               and self.gamepad.connected) else None
        if pad is not None:
            # L2 / R2 held: camera speed down / up, right stick: look
            trigger = pad.right_trigger - pad.left_trigger
            if trigger:
                self.speed = max(1.0, self.speed * 2.0 ** (trigger * dt * 1.5))
            self.yaw += pad.right.x * 120.0 * dt
            self.pitch = max(-89.0, min(89.0, self.pitch + pad.right.y * 90.0 * dt))
        move_speed = self.speed * dt
        if k.LSHIFT in self.held_keys or k.RSHIFT in self.held_keys or (pad is not None and "a" in pad.held):
            move_speed *= 5
        if k.LCTRL in self.held_keys:
            move_speed *= 0.2
        j, p = math.radians(self.yaw), math.radians(self.pitch)
        forward = Vec3(math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        right_vec = Vec3(-math.sin(j), 0.0, math.cos(j))
        up = Vec3(0.0, 1.0, 0.0)
        movement = Vec3(0.0, 0.0, 0.0)
        if k.W in self.held_keys:
            movement += forward
        if k.S in self.held_keys:
            movement -= forward
        if k.D in self.held_keys:
            movement += right_vec
        if k.A in self.held_keys:
            movement -= right_vec
        if self.bindings.key("camera_up") in self.held_keys:
            movement += up
        if self.bindings.key("camera_down") in self.held_keys:
            movement -= up
        if pad is not None:
            # d-pad like WASD, L1 / R1 down / up
            movement += forward * pad.dpad[1] + right_vec * pad.dpad[0]
            movement += up * (("rightshoulder" in pad.held) - ("leftshoulder" in pad.held))
        if movement.length() > 0:
            self.pos += movement.normalize() * move_speed
        if pad is not None and (pad.left.x or pad.left.y):
            # the left stick moves in proportion to how far it is pushed
            self.pos += (forward * pad.left.y + right_vec * pad.left.x) * move_speed


# the opening camera behind the player: metres back and up, and how far down
# it looks (a third-person view of where the level starts)
START_BACK, START_UP, START_PITCH = 5.0, 2.5, -15.0


def opening_camera(level):
    """(position, yaw, pitch, speed) of the opening camera: behind the player
    where the level starts (`Level.start_place`), looking the way the player
    faces. It used to stand back from the middle of the
    terrain by 0.75 of its longest side: outside the level in 79 levels out
    of 79, and inside the sky in the long ones (checks/check_start_camera.py).
    Without a start (the cutscenes) it stays inside the terrain box, at its
    top, a quarter of the depth from the near edge."""
    lo, hi = level.terrain_lo, level.terrain_hi
    radius = max(hi[i] - lo[i] for i in range(3)) or 10.0
    speed = max(8.0, radius / 12.0)
    start = level.start_place()
    if start is None:
        mid = [(a + b) / 2 for a, b in zip(lo, hi)]
        return Vec3(mid[0], hi[1], hi[2] - (hi[2] - lo[2]) * 0.25), -90.0, -22.0, speed
    x, y, z, heading, _source = start
    feet = geo._transform((x, y, z))
    # where the player faces, in the viewer's plane: the game turns +Z by the
    # heading around Y, and the viewer mirrors Z (geometry._transform: x, -y,
    # -z). Checked on the photos: from here the camera sees Bugs's back,
    # tail and all
    a = heading * 2 * math.pi / 4096.0
    fx, fz = math.sin(a), -math.cos(a)
    pos = Vec3(feet[0] - fx * START_BACK, feet[1] + START_UP, feet[2] - fz * START_BACK)
    return pos, math.degrees(math.atan2(fz, fx)), START_PITCH, speed
