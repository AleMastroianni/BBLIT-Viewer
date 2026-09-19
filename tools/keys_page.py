"""Help -> Keyboard and Help -> Gamepad, drawn pages as in the CTR viewer.

Keyboard: above, the key rows in columns (click or Enter: the next key
pressed becomes the new one, Esc cancels; right click: remove the key;
"Restore default keys"; the locked keys greyed with a padlock); below, the
keyboard, orange where a key is used, grey where it is free, a padlock on
the locked ones, and a line saying what the key under the mouse does. If a
key is left without a function when leaving the page, the last saved set
comes back.

Gamepad: a controller drawn in the middle (ours, not the CTR viewer's), a
line from every control to what it does, information only.

A custom page takes the menu's input and drawing (menu.Page `custom`).
"""

from __future__ import annotations

import math
import time

import pyglet
from pyglet.window import key

import keybinds as kb
from menu import (BACKGROUND_COLOR, DESCRIPTION_COLOR, FONT, HIGHLIGHT_COLOR, SELECTED_TEXT_COLOR,
                  TEXT_COLOR, TITLE_COLOR, ellipsize, wrap_lines)
from texts import language, t

ORANGE = (255, 165, 0, 255)
OK_COLOR = (140, 255, 150, 255)
ERROR_COLOR = (255, 110, 110, 255)
WHITE = (255, 255, 255, 255)
LOCKED_TEXT = (165, 165, 165, 255)
BOUND_FILL = (255, 140, 0, 255)
BOUND_TEXT = (30, 18, 0, 255)
FREE_FILL = (52, 52, 58, 235)
FREE_TEXT = (175, 175, 180, 255)
CAP_BORDER = (0, 0, 0, 200)
PANEL = (0, 0, 0, 150)

LOCKED_ROWS = ("keys.row.esc", "keys.row.nav", "keys.row.confirm", "keys.row.move", "keys.row.shift",
               "keys.row.page", "keys.row.num_tps", "keys.row.fullscreen", "keys.row.quit",
               "keys.row.mouse_look", "keys.row.wheel")

_widths: dict = {}


def text_width(text, size):
    """Width in pixels of `text` at `size` points (measured at 20 and scaled)."""
    w = _widths.get(text)
    if w is None:
        w = _widths[text] = pyglet.text.Label(text, font_name=FONT, font_size=20).content_width
    return w * size / 20.0


def fit_size(text, width, size):
    w = text_width(text, size)
    return size if w <= width or w == 0 else max(4.0, size * width / w)


class _Drawing:
    """A batch with seven layers and the objects that keep it alive."""

    def __init__(self):
        self.batch = pyglet.graphics.Batch()
        self.groups = [pyglet.graphics.Group(order=i) for i in range(7)]
        self.keep = []

    def rect(self, x, y, w, h, color, layer=0):
        self.keep.append(pyglet.shapes.Rectangle(x, y, max(1, w), max(1, h), color=color,
                                                 batch=self.batch, group=self.groups[layer]))

    def label(self, text, x, y, size, color, layer=3, anchor_x="left", anchor_y="baseline"):
        self.keep.append(pyglet.text.Label(text, font_name=FONT, font_size=size, x=x, y=y, color=color,
                                           anchor_x=anchor_x, anchor_y=anchor_y,
                                           batch=self.batch, group=self.groups[layer]))

    def padlock(self, left, bottom, size, color, layer=4):
        """A small padlock of height `size` (bottom-left corner); returns its width."""
        width = size * 0.8
        body = size * 0.55
        thick = max(1.0, round(size * 0.14))
        self.rect(left, bottom, width, body, color, layer)
        shackle_top = bottom + body + size * 0.42
        self.rect(left + width * 0.18, bottom + body, thick, shackle_top - bottom - body, color, layer)
        self.rect(left + width * 0.82 - thick, bottom + body, thick, shackle_top - bottom - body, color, layer)
        self.rect(left + width * 0.18, shackle_top - thick, width * 0.64, thick, color, layer)
        return width

    def draw(self):
        self.batch.draw()


def _scale(win):
    return max(0.75, min(1.6, win.height / 760.0))


# ------------------------------------------------------------------ keyboard

class KeyboardPage:
    def __init__(self, bindings, on_saved):
        self.bindings = bindings
        self.on_saved = on_saved          # the set is complete: save the settings
        self.capturing = None
        self.selection = 0
        self.status = None                # (text, colour, until)
        self.mouse = (-1, -1)
        self._drawing = None
        self._draw_key = None
        self._row_rects = []              # (x, y, w, h, index)
        self._caps = []                   # (Cap, [(x, y, w, h)])
        self._rows_per_column = 1
        self.dirty = True

    # ---- rows

    def rows(self):
        return ([("bind", a) for a in kb.ACTION_IDS] + [("reset", None)]
                + [("locked", k) for k in LOCKED_ROWS] + [("back", None)])

    @staticmethod
    def selectable(row):
        return row[0] != "locked"

    def row_text(self, row, capture=True):
        kind, payload = row
        if kind == "bind":
            if capture and self.capturing == payload:
                return f"{t('keys.press_key')} - {t(kb.TEXT_OF[payload])}"
            return f"{kb.key_name(self.bindings.key(payload), t)} - {t(kb.TEXT_OF[payload])}"
        if kind == "reset":
            return t("keys.reset")
        if kind == "locked":
            return t(payload)
        return t("menu.back")

    # ---- page life

    def enter(self, menu):
        self.capturing = None
        self.selection = 0
        self.dirty = True

    def leave(self, menu):
        self.capturing = None
        if self.bindings.revert_if_incomplete():
            self.set_status(t("keys.reverted"), DESCRIPTION_COLOR, 6)

    def set_status(self, text, color, seconds=4.0):
        self.status = (text, color, time.monotonic() + seconds)
        self.dirty = True

    def _status_text(self):
        if self.status and time.monotonic() < self.status[2]:
            return self.status
        return None

    # ---- input

    def press(self, symbol, modifiers, menu) -> bool:
        if self.capturing is not None:
            if symbol == key.ESCAPE:
                self.capturing = None
                self.set_status(t("keys.cancelled"), WHITE)
            else:
                self._capture(symbol)
            return True
        rows = self.rows()
        if symbol in (key.UP, key.W):
            self._move(-1)
        elif symbol in (key.DOWN, key.S):
            self._move(1)
        elif symbol in (key.LEFT, key.A):
            self._move(-self._rows_per_column)
        elif symbol in (key.RIGHT, key.D):
            self._move(self._rows_per_column)
        elif symbol in (key.ENTER, key.NUM_ENTER, key.SPACE):
            self._activate(rows[self.selection], menu)
        elif symbol in menu.back_keys():
            menu.go_back()
        self.dirty = True
        return True

    def _move(self, step):
        rows = self.rows()
        i = max(0, min(len(rows) - 1, self.selection + step))
        direction = 1 if step > 0 else -1
        while not self.selectable(rows[i]):
            i += direction
            if not 0 <= i < len(rows):
                return
        self.selection = i

    def _activate(self, row, menu):
        kind, payload = row
        if kind == "bind":
            self.capturing = payload
            self.set_status(t("keys.press_new", action=t(kb.TEXT_OF[payload])), WHITE, 30)
        elif kind == "reset":
            self.capturing = None
            self.bindings.reset()
            self.on_saved()
            self.set_status(t("keys.defaults_restored"), OK_COLOR)
        elif kind == "back":
            menu.go_back()

    def _capture(self, symbol):
        action = self.capturing
        name = kb.key_name(symbol, t)
        result, owner = self.bindings.check(action, symbol)
        what = t(kb.TEXT_OF[action])
        if result == "ok":
            self.capturing = None
            if self.bindings.assign(action, symbol):
                self.on_saved()
                self.set_status(t("keys.saved", action=what, key=name), OK_COLOR)
            else:
                missing = ", ".join(t(kb.TEXT_OF[a]) for a in self.bindings.unbound())
                self.set_status(t("keys.not_saved_yet", action=what, key=name, missing=missing), ORANGE, 8)
        elif result == "locked":
            self.set_status(t("keys.is_locked", key=name), ERROR_COLOR)
        elif result == "system":
            self.set_status(t("keys.is_system", key=name), ERROR_COLOR)
        elif result == "in_use":
            self.set_status(t("keys.in_use", key=name, owner=t(kb.TEXT_OF[owner])), ERROR_COLOR)
        else:
            self.set_status(t("keys.unsupported", key=name), ERROR_COLOR)

    def _row_at(self, x, y):
        for rx, ry, rw, rh, i in self._row_rects:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return i
        return None

    def mouse_over(self, x, y, menu) -> bool:
        self.mouse = (x, y)
        i = self._row_at(x, y)
        if i is not None and self.capturing is None and self.selectable(self.rows()[i]):
            self.selection = i
        self.dirty = True
        return True

    def click(self, x, y, button, menu) -> bool:
        self.mouse = (x, y)
        i = self._row_at(x, y)
        rows = self.rows()
        if button == pyglet.window.mouse.RIGHT:
            if i is not None and rows[i][0] == "bind":
                action = rows[i][1]
                self.selection = i
                if self.bindings.key(action) is not None:
                    name = kb.key_name(self.bindings.key(action), t)
                    self.bindings.unbind(action)
                    self.capturing = None
                    self.set_status(t("keys.removed", key=name, action=t(kb.TEXT_OF[action])), ORANGE, 8)
            elif self.capturing is None:
                menu.go_back()
        elif i is not None and self.selectable(rows[i]) and self.capturing is None:
            self.selection = i
            self._activate(rows[i], menu)
        self.dirty = True
        return True

    def wheel(self, x, y, sy, menu) -> bool:
        return True

    # ---- drawing

    def draw(self, win, menu):
        status = self._status_text()
        hovered = self._cap_at(*self.mouse)
        state = (win.width, win.height, self.selection, self.capturing, status and status[0],
                 id(hovered), tuple(self.bindings.current.get(a) for a in kb.ACTION_IDS), language())
        if self.dirty or state != self._draw_key or self._drawing is None:
            self._layout(win, status)
            self._draw_key = state
            self.dirty = False
        self._drawing.draw()

    def _cap_at(self, x, y):
        for cap, rects in self._caps:
            for rx, ry, rw, rh in rects:
                if rx <= x < rx + rw and ry <= y < ry + rh:
                    return cap
        return None

    def _layout(self, win, status):
        d = _Drawing()
        s = _scale(win)
        d.rect(0, 0, win.width, win.height, (0, 0, 0, 110))
        margin, pad = round(12 * s), round(10 * s)
        left, width = margin, win.width - 2 * margin
        inner = width - 2 * pad

        # upper half: the rows, in the column count that gives the largest text
        rows = self.rows()
        texts = [self.row_text(r, capture=False) for r in rows]
        top, bottom = win.height - margin, win.height / 2 + margin / 2
        d.rect(left, bottom, width, top - bottom, PANEL)
        avail = top - bottom - 2 * pad
        best = None
        for columns in (2, 3, 4):
            per_column = math.ceil(len(rows) / columns)
            row_h = avail / per_column
            column_w = inner / columns
            by_height = row_h * 0.58 / 1.333
            widest = max(text_width(tx, 10) + (row_h if r[0] == "locked" else 0) / 1.0
                         for tx, r in zip(texts, rows))
            by_width = 10 * (column_w - 20) / max(1.0, widest)
            size = min(15 * s, by_height, by_width)
            if best is None or size > best[0] + 0.01:
                best = (size, columns, per_column, row_h, column_w)
        size, columns, per_column, row_h, column_w = best
        self._rows_per_column = per_column
        self._row_rects = []
        for i, row in enumerate(rows):
            column, line = divmod(i, per_column)
            x = left + pad + column * column_w
            y = top - pad - (line + 1) * row_h
            w, h = column_w - 4, row_h - 2
            if self.selectable(row):
                self._row_rects.append((x, y, w, h, i))
            selected = i == self.selection
            if selected:
                d.rect(x, y, w, h, HIGHLIGHT_COLOR, 1)
            text_left = x + 6
            color = SELECTED_TEXT_COLOR if selected else TEXT_COLOR
            if row[0] == "locked":
                lock = h * 0.55
                text_left += d.padlock(x + 6, y + (h - lock) / 2, lock, LOCKED_TEXT) + 6
                color = LOCKED_TEXT
            elif row[0] == "bind" and not selected and self.bindings.key(row[1]) is None:
                color = ERROR_COLOR
            text = ellipsize(self.row_text(row), x + w - text_left - 6, size)
            d.label(text, text_left, y + h / 2, size, color, anchor_y="center")

        # lower half: the keyboard
        top, bottom = win.height / 2 - margin / 2, margin
        d.rect(left, bottom, width, top - bottom, PANEL)
        area_x, area_w = left + pad, inner
        area_top, area_bottom = top - pad, bottom + pad
        text_size = min(13 * s, 13.0)
        line_h = text_size * 1.333 * 1.35
        legend = t("keys.legend")
        d.label(legend, area_x, area_top - line_h * 0.8, fit_size(legend, area_w, text_size), ORANGE)
        board_top = area_top - line_h - 4 * s
        board_h = board_top - (area_bottom + line_h + 4 * s)
        unit = min(area_w / kb.UNITS_WIDE, board_h / kb.UNITS_HIGH)
        gap = max(1.0, unit * 0.08)
        board_left = area_x + (area_w - unit * kb.UNITS_WIDE) / 2

        def to_rect(x, y, w, h):
            return (board_left + x * unit + gap / 2, board_top - (y + h) * unit + gap / 2,
                    max(1.0, w * unit - gap), max(1.0, h * unit - gap))

        hovered = None
        self._caps = []
        mx, my = self.mouse
        for cap in kb.layout():
            rects = [to_rect(cap.x, cap.y, cap.w, cap.h)]
            if cap.extra:
                rects.append(to_rect(*cap.extra))
            self._caps.append((cap, rects))
            bound = cap.symbol is not None and (cap.symbol in kb.LOCKED or self.bindings.is_bound(cap.symbol))
            is_hovered = any(rx <= mx < rx + rw and ry <= my < ry + rh for rx, ry, rw, rh in rects)
            if is_hovered:
                hovered = cap
            fill = BOUND_FILL if bound else FREE_FILL
            for rx, ry, rw, rh in rects:
                d.rect(rx, ry, rw, rh, WHITE if is_hovered else CAP_BORDER, 1)
                d.rect(rx + 2, ry + 2, rw - 4, rh - 4, fill, 2)
            if cap.extra:
                (ax, ay, aw, ah), (bx, by, bw, bh) = rects
                d.rect(bx + 2, by + bh - 4, bw - 4, ay - (by + bh) + 8, fill, 2)
            rx, ry, rw, rh = rects[0]
            if cap.symbol is not None and cap.symbol in kb.LOCKED:
                lock = max(7.0, rh * 0.24)
                d.padlock(rx + rw - 4 - lock * 0.8, ry + rh - 4 - lock, lock, (30, 18, 0, 215))
            text = t(cap.text) if cap.text.startswith("keys.cap.") else cap.text
            text_pt = min(rh * 0.5 / 1.333, 13 * s)
            text_pt = fit_size(text, rw - 6, text_pt)
            d.label(text, rx + rw / 2, ry + rh / 2, text_pt, BOUND_TEXT if bound else FREE_TEXT,
                    anchor_x="center", anchor_y="center")

        # the line under the keyboard
        if status:
            info, color = status[0], status[1]
        elif hovered is None or hovered.symbol is None:
            info, color = t("keys.mouse_help"), (205, 205, 205, 255)
        else:
            name = t(hovered.text) if hovered.text.startswith("keys.cap.") else hovered.text
            if hovered.symbol in kb.LOCKED:
                info, color = f"{name} ({t('keys.locked')}): {t(kb.LOCKED[hovered.symbol])}", ORANGE
            elif self.bindings.is_bound(hovered.symbol):
                actions = ", ".join(t(kb.TEXT_OF[a]) for a in self.bindings.actions_for(hovered.symbol))
                info, color = f"{name}: {actions}", ORANGE
            else:
                info, color = f"{name}: {t('keys.free')}", WHITE
        d.label(info, area_x, area_bottom + line_h * 0.25, fit_size(info, area_w, text_size), color)
        self._drawing = d


# ------------------------------------------------------------------ gamepad

# (name key, text key, slot on the ring, anchor in pad units; y down)
CALLOUTS = [
    ("pad.select", "pad.select_does", 0, (-0.30, -0.25)),
    ("pad.start", "pad.start_does", 1, (0.30, -0.25)),
    ("pad.r2", "pad.r2_does", 2, (0.56, -0.50)),
    ("pad.r1", "pad.r1_does", 3, (0.58, -0.40)),
    ("pad.triangle", "pad.nothing", 4, (0.52, -0.20)),
    ("pad.circle", "pad.circle_does", 5, (0.64, -0.08)),
    ("pad.cross", "pad.cross_does", 6, (0.52, 0.04)),
    ("pad.square", "pad.nothing", 7, (0.40, -0.08)),
    ("pad.right_stick", "pad.right_stick_does", 8, (0.24, 0.12)),
    ("pad.left_stick", "pad.left_stick_does", 9.2, (-0.24, 0.12)),
    ("pad.dpad", "pad.dpad_does", 10.4, (-0.52, -0.08)),
    ("pad.l1", "pad.l1_does", 11.6, (-0.58, -0.40)),
    ("pad.l2", "pad.l2_does", 12.8, (-0.56, -0.50)),
]
SLOTS = 14


class GamepadPage:
    def __init__(self, gamepad_state):
        self.gamepad_state = gamepad_state     # () -> (connected, name)
        self._drawing = None
        self._draw_key = None
        self._back = (0, 0, 0, 0)

    def enter(self, menu):
        self._draw_key = None

    def leave(self, menu):
        pass

    def press(self, symbol, modifiers, menu) -> bool:
        if symbol in (key.ENTER, key.NUM_ENTER, key.SPACE) or symbol in menu.back_keys():
            menu.go_back()
        return True

    def mouse_over(self, x, y, menu) -> bool:
        return True

    def click(self, x, y, button, menu) -> bool:
        bx, by, bw, bh = self._back
        if button == pyglet.window.mouse.RIGHT or (bx <= x < bx + bw and by <= y < by + bh):
            menu.go_back()
        return True

    def wheel(self, x, y, sy, menu) -> bool:
        return True

    def draw(self, win, menu):
        state = (win.width, win.height, self.gamepad_state(), language(),
                 tuple(menu.back_keys()))
        if state != self._draw_key or self._drawing is None:
            self._layout(win, menu)
            self._draw_key = state
        self._drawing.draw()

    def _layout(self, win, menu):
        d = _Drawing()
        s = _scale(win)
        d.rect(0, 0, win.width, win.height, (0, 0, 0, 170))
        margin = round(14 * s)
        size = 11.5 * s
        line_h = size * 1.333 * 1.25

        connected, name = self.gamepad_state()
        title = t("pad.title") + ("   ·   " + t("pad.connected", name=name) if connected
                                  else "   ·   " + t("pad.none"))
        d.label(title, win.width / 2, win.height - margin - line_h, 13.5 * s, ORANGE, anchor_x="center")

        # Back and the hint at the bottom
        back_text = t("menu.back")
        bw = text_width(back_text, size * 1.15) + 48 * s
        bh = line_h * 1.4
        bx, by = win.width / 2 - bw / 2, margin + line_h * 1.6
        d.rect(bx, by, bw, bh, HIGHLIGHT_COLOR, 1)
        d.label(back_text, win.width / 2, by + bh / 2, size * 1.15, SELECTED_TEXT_COLOR,
                anchor_x="center", anchor_y="center")
        self._back = (bx, by, bw, bh)
        backs = " / ".join(kb.key_name(k, t) for k in menu.back_keys() if k is not None)
        hint = t("pad.hint", keys=backs)
        d.label(hint, win.width / 2, margin + line_h * 0.3, size * 0.85, (190, 190, 190, 255), anchor_x="center")

        # the ring of labels around the pad
        side = win.width * 0.19
        blocks = []
        for name_key, text_key, slot, anchor in CALLOUTS:
            lines = wrap_lines(t(text_key), side, size)
            label = t(name_key)
            w = max([text_width(label, size)] + [text_width(x, size) for x in lines])
            blocks.append((label, lines, slot, anchor, w, line_h * (1 + len(lines))))
        top = win.height - margin - line_h * 2
        bottom = by + bh + margin
        cx, cy = win.width / 2, (top + bottom) / 2
        rx = max(80.0, win.width / 2 - side - margin)
        ry = max(60.0, (top - bottom) / 2 - max(b[5] for b in blocks) / 2 - 4)
        scale = min(rx * 0.62, ry * 0.72)
        origin = (cx, cy + 0.07 * scale)

        self._draw_pad(d, origin, scale)

        line_color = (235, 170, 70, 255)
        step = 2 * math.pi / SLOTS
        for label, lines, slot, anchor, w, h in blocks:
            angle = -math.pi / 2 - step / 2 + slot * step
            px, py = cx + math.cos(angle) * rx, cy - math.sin(angle) * ry
            ax, ay = origin[0] + anchor[0] * scale, origin[1] - anchor[1] * scale
            d.keep.append(pyglet.shapes.Line(ax, ay, px, py, thickness=max(1.5, 2 * s), color=line_color,
                                             batch=d.batch, group=d.groups[5]))
            d.keep.append(pyglet.shapes.Circle(ax, ay, max(3.0, scale * 0.018), color=line_color,
                                               batch=d.batch, group=d.groups[5]))
            right = math.cos(angle) > 0
            x0 = px + 8 if right else px - 8 - w
            block_top = py + h / 2
            d.rect(x0 - 6, block_top - h - 3, w + 12, h + 6, (0, 0, 0, 185), 5)

            def aligned(text):
                return x0 if right else x0 + w - text_width(text, size)
            y = block_top - line_h
            d.label(label, aligned(label), y + line_h * 0.25, size, ORANGE, layer=6)
            for x in lines:
                y -= line_h
                d.label(x, aligned(x), y + line_h * 0.25, size, WHITE, layer=6)
        self._drawing = d

    @staticmethod
    def _draw_pad(d, origin, s):
        """A pad of our own: rounded body with a touchpad, separate d-pad
        arrows, four face buttons with their symbols, two sticks, a light bar."""
        ox, oy = origin
        b, g = d.batch, d.groups

        def P(x, y):
            return ox + x * s, oy - y * s

        def rrect(x0, y0, x1, y1, r, color, layer):
            (ax, ay), (bx, by) = P(x0, y1), P(x1, y0)
            d.keep.append(pyglet.shapes.RoundedRectangle(ax, ay, bx - ax, by - ay, r * s, color=color,
                                                         batch=b, group=g[layer]))

        def ellipse(x, y, rxu, ryu, color, layer):
            cx, cy = P(x, y)
            d.keep.append(pyglet.shapes.Ellipse(cx, cy, rxu * s, ryu * s, color=color, batch=b, group=g[layer]))

        def circle(x, y, r, color, layer):
            cx, cy = P(x, y)
            d.keep.append(pyglet.shapes.Circle(cx, cy, r * s, color=color, batch=b, group=g[layer]))

        def line(x0, y0, x1, y1, thick, color, layer=2):
            (ax, ay), (bx, by) = P(x0, y0), P(x1, y1)
            d.keep.append(pyglet.shapes.Line(ax, ay, bx, by, thickness=max(1.5, thick * s), color=color,
                                             batch=b, group=g[layer]))

        outline = (14, 16, 22, 255)
        body = (206, 210, 220, 255)
        body_dark = (160, 166, 180, 255)
        detail = (38, 42, 54, 255)
        e = 0.022

        # triggers and bumpers
        for side in (-1, 1):
            x0, x1 = sorted((0.40 * side, 0.72 * side))
            rrect(x0 - e, -0.58 - e, x1 + e, -0.42, 0.06, outline, 0)
            rrect(x0, -0.58, x1, -0.42, 0.06, body_dark, 0)
            x0, x1 = sorted((0.38 * side, 0.76 * side))
            rrect(x0 - e, -0.47 - e, x1 + e, -0.36 + e, 0.05, outline, 0)
            rrect(x0, -0.47, x1, -0.36, 0.05, body, 1)
        # body and grips
        rrect(-0.80 - e, -0.40 - e, 0.80 + e, 0.20 + e, 0.22, outline, 1)
        ellipse(-0.58, 0.30, 0.23 + e, 0.38 + e, outline, 1)
        ellipse(0.58, 0.30, 0.23 + e, 0.38 + e, outline, 1)
        rrect(-0.80, -0.40, 0.80, 0.20, 0.22, body, 2)
        ellipse(-0.58, 0.30, 0.23, 0.38, body, 2)
        ellipse(0.58, 0.30, 0.23, 0.38, body, 2)
        # touchpad with the light bar under it, and the centre button
        rrect(-0.24, -0.38, 0.24, -0.08, 0.05, (178, 184, 198, 255), 3)
        rrect(-0.20, -0.07, 0.20, -0.05, 0.01, (90, 150, 255, 255), 3)
        circle(0.0, 0.04, 0.035, detail, 3)
        # Select (Share) and Start (Options), as slits beside the touchpad
        rrect(-0.33, -0.31, -0.28, -0.20, 0.02, detail, 3)
        rrect(0.28, -0.31, 0.33, -0.20, 0.02, detail, 3)
        # d-pad: four arrow keys
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            cx, cy = -0.52 + dx * 0.075, -0.08 + dy * 0.075
            rrect(cx - 0.042, cy - 0.042, cx + 0.042, cy + 0.042, 0.012, detail, 3)
        # face buttons
        r = 0.052
        for (x, y) in ((0.52, -0.20), (0.64, -0.08), (0.52, 0.04), (0.40, -0.08)):
            circle(x, y, r, detail, 3)
        t_ = 0.012
        green, red, blue, pink = (90, 205, 160, 255), (235, 90, 100, 255), (125, 165, 245, 255), (235, 145, 205, 255)
        line(0.52, -0.228, 0.497, -0.186, t_, green, 4)
        line(0.497, -0.186, 0.543, -0.186, t_, green, 4)
        line(0.543, -0.186, 0.52, -0.228, t_, green, 4)
        circle(0.64, -0.08, 0.026, red, 4)
        circle(0.64, -0.08, 0.016, detail, 4)
        line(0.498, 0.018, 0.542, 0.062, t_, blue, 4)
        line(0.542, 0.018, 0.498, 0.062, t_, blue, 4)
        for x0, y0, x1, y1 in ((0.380, -0.100, 0.420, -0.100), (0.420, -0.100, 0.420, -0.060),
                               (0.420, -0.060, 0.380, -0.060), (0.380, -0.060, 0.380, -0.100)):
            line(x0, y0, x1, y1, t_, pink, 4)
        # sticks
        for x in (-0.24, 0.24):
            circle(x, 0.12, 0.13, outline, 3)
            circle(x, 0.12, 0.095, (70, 74, 88, 255), 4)
            circle(x, 0.12, 0.06, (52, 56, 68, 255), 4)
