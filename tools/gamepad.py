"""The gamepad, as in the CTR viewer: the first controller pyglet finds,
connected before or after the start (ControllerManager).

Buttons arrive as events (`on_button`: the pyglet names "a", "b", "x", "y",
"back", "start", "leftshoulder", "rightshoulder", "leftstick", "rightstick",
and "dpup", "dpdown", "dpleft", "dpright" for the d-pad); sticks, triggers
and held buttons are read by the viewer at every frame. The stick vectors
come from pyglet's events, which give Y up as positive with both XInput and
DirectInput (the raw `lefty` attribute does not).

Nothing is rebindable: the mapping is in Viewer, and Help -> Gamepad draws it.
"""

from __future__ import annotations

import pyglet
from pyglet.math import Vec2

DEADZONE = 0.2


def _dead(v: Vec2) -> Vec2:
    x = v.x if abs(v.x) > DEADZONE else 0.0
    y = v.y if abs(v.y) > DEADZONE else 0.0
    return Vec2(x, y)


class Gamepad:
    def __init__(self, on_button):
        self.on_button = on_button
        self.controller = None
        self.left = Vec2()
        self.right = Vec2()
        self.left_trigger = self.right_trigger = 0.0
        self.held: set[str] = set()
        self.dpad = (0, 0)
        self.manager = None
        try:
            self.manager = pyglet.input.ControllerManager()
            self.manager.push_handlers(on_connect=self._on_connect, on_disconnect=self._on_disconnect)
            found = self.manager.get_controllers()
        except Exception as e:  # noqa: BLE001
            print(f"no gamepad support: {e}")
            found = []
        if found:
            self._attach(found[0])

    @property
    def connected(self) -> bool:
        return self.controller is not None

    @property
    def name(self) -> str:
        return self.controller.name if self.controller is not None else ""

    def _attach(self, controller):
        try:
            controller.open()
        except Exception as e:  # noqa: BLE001
            print(f"gamepad not opened: {e}")
            return
        controller.push_handlers(self)
        self.controller = controller
        print(f"gamepad connected: {controller.name}")

    def _on_connect(self, controller):
        if self.controller is None:
            self._attach(controller)

    def _on_disconnect(self, controller):
        if controller is self.controller:
            self.controller = None
            self.release()
            print("gamepad disconnected")

    def release(self):
        """Nothing held (out of focus, disconnected)."""
        self.left, self.right = Vec2(), Vec2()
        self.left_trigger = self.right_trigger = 0.0
        self.held.clear()
        self.dpad = (0, 0)

    # ---- pyglet controller events

    def on_button_press(self, controller, button):
        self.held.add(button)
        self.on_button(button)

    def on_button_release(self, controller, button):
        self.held.discard(button)

    def on_dpad_motion(self, controller, vector):
        new = (round(vector.x), round(vector.y))
        old = self.dpad
        self.dpad = new
        for axis, minus, plus in ((0, "dpleft", "dpright"), (1, "dpdown", "dpup")):
            if new[axis] != old[axis] and new[axis] != 0:
                self.on_button(plus if new[axis] > 0 else minus)

    def on_stick_motion(self, controller, stick, vector):
        if stick == "leftstick":
            self.left = _dead(vector)
        elif stick == "rightstick":
            self.right = _dead(vector)

    def on_trigger_motion(self, controller, trigger, value):
        value = max(0.0, min(1.0, value))
        if trigger == "lefttrigger":
            self.left_trigger = value
        elif trigger == "righttrigger":
            self.right_trigger = value
