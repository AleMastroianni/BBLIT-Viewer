"""The keys, as in the CTR viewer (Help -> Keyboard): the ones with a single
function can be changed, the ones with several are locked.

Each rebindable action has exactly one key. The default is a Windows
virtual-key code, turned into the pyglet symbol the active layout produces
(`symbol_of_vk`, the same steps as pyglet's own key handler): on an Italian
keyboard the key right of 0 is "'" and the one after it "ì", on a US one
"-" and "=". The keyboard picture places character keys by scan code and
labels them from the layout, so an Italian keyboard shows ò where a US one
shows ;.

Actions live in a context: "scene" (menu closed), "menu" (menu open) or
"any". Two actions may share a key only in different contexts, like M:
Semi-transparency with the menu closed, Back with the menu open.

Stored in the settings as {action: pyglet symbol}; a missing, invalid,
locked or reserved key falls back to the default, and if the result has
duplicates every action goes back to its default.
"""

from __future__ import annotations

import ctypes

from pyglet.window import key

try:
    import pyglet.window  # noqa: F401  (winkey imports pyglet.window: load it first)
    from pyglet.libs.win32.winkey import chmap, keymap
    _user32 = ctypes.windll.user32
except (ImportError, AttributeError, OSError):      # not Windows
    chmap, keymap, _user32 = {}, {}, None

MAPVK_VSC_TO_VK = 1
MAPVK_VK_TO_CHAR = 2

# (action, text key of what it does, context, default virtual-key code)
ACTIONS = [
    ("camera_up", "keys.camera_up", "scene", 0x45),          # E
    ("camera_down", "keys.camera_down", "scene", 0x51),      # Q
    ("reset_camera", "help.reset", "scene", 0x52),           # R
    ("level_prev", "keys.level_prev", "scene", 0xDB),        # VK_OEM_4: [ on US
    ("level_next", "keys.level_next", "scene", 0xDD),        # VK_OEM_6: ] on US
    ("textures", "level.texture", "scene", 0x54),            # T
    ("props", "level.props", "scene", 0x4F),                 # O
    ("sky", "level.sky", "scene", 0x48),                     # H
    ("blending", "level.blending", "scene", 0x4D),           # M
    ("wireframe", "level.wireframe", "scene", 0x46),         # F
    ("texanim", "level.texanim", "scene", 0x4E),             # N
    ("clones", "level.clones", "scene", 0x47),               # G
    ("pause", "help.pause", "scene", 0x50),                  # P
    ("tps_down", "keys.tps_down", "scene", 0xBD),            # VK_OEM_MINUS
    ("tps_up", "keys.tps_up", "scene", 0xBB),                # VK_OEM_PLUS
    ("filter", "video.filter", "scene", 0x4C),               # L
    ("hide_ui", "help.hide_ui", "any", 0x70),                # F1
    ("menu_back", "keys.menu_back", "menu", 0x4D),           # M
    ("menu_back_alt", "keys.menu_back_alt", "menu", 0x08),   # Backspace
]
ACTION_IDS = [a[0] for a in ACTIONS]
TEXT_OF = {a[0]: a[1] for a in ACTIONS}
CONTEXT_OF = {a[0]: a[2] for a in ACTIONS}

# keys with several functions (or fixed ones): never rebindable, never
# accepted as a new key; the text says what they do
LOCKED = {
    key.ESCAPE: "keys.locked.esc",
    key.RETURN: "keys.locked.enter",
    key.SPACE: "keys.locked.space",
    key.W: "keys.locked.w", key.A: "keys.locked.a", key.S: "keys.locked.s", key.D: "keys.locked.d",
    key.UP: "keys.locked.up", key.DOWN: "keys.locked.down",
    key.LEFT: "keys.locked.left", key.RIGHT: "keys.locked.right",
    key.PAGEUP: "keys.locked.pageup", key.PAGEDOWN: "keys.locked.pagedown",
    key.LSHIFT: "keys.locked.shift", key.RSHIFT: "keys.locked.shift",
    key.LCTRL: "keys.locked.ctrl",
    key.LALT: "keys.locked.alt", key.RALT: "keys.locked.alt",
    key.F4: "keys.locked.f4",
    key.NUM_ADD: "keys.locked.num_tps", key.NUM_SUBTRACT: "keys.locked.num_tps",
}
# Windows keys and the menu key open system UI; lock keys toggle a state;
# right Ctrl is half of AltGr on Italian layouts; F10 activates the window
# menu; Print Screen is taken by the Snipping Tool
SYSTEM_VKS = (0x5B, 0x5C, 0x5D, 0x14, 0x90, 0x91, 0xA3, 0x79, 0x2C)


def symbol_of_vk(vk: int) -> int:
    """The pyglet symbol for a virtual-key code on the active layout, as
    pyglet's Win32 key handler computes it."""
    symbol = keymap.get(vk)
    if symbol is None and _user32 is not None:
        symbol = chmap.get(_user32.MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR))
    return symbol if symbol is not None else key.user_key(vk)


def _char_of_vk(vk: int) -> str | None:
    if _user32 is None:
        return None
    value = _user32.MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR) & 0x7FFFFFFF
    return chr(value).upper() if value >= 32 else None


def _vk_of_scan(scan: int) -> int:
    return _user32.MapVirtualKeyW(scan, MAPVK_VSC_TO_VK) if _user32 is not None else 0


SYSTEM = frozenset(symbol_of_vk(vk) for vk in SYSTEM_VKS)


# ------------------------------------------------------------------ keyboard

class Cap:
    """One key of the picture, in key units: x, y, width, height; `extra`
    is the second rectangle of the L-shaped ISO Enter."""
    __slots__ = ("x", "y", "w", "h", "symbol", "text", "extra")

    def __init__(self, x, y, w, symbol, text, h=1.0, extra=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.symbol, self.text, self.extra = symbol, text, extra


UNITS_WIDE = 22.5
UNITS_HIGH = 6.5


def layout() -> list[Cap]:
    """The keyboard: main block 15 units wide, navigation from 15.25, numpad
    from 18.5 (the CTR viewer's layout). Character keys by scan code."""
    caps: list[Cap] = []

    def fixed(x, row, w, vk, text, h=1.0, extra=None):
        caps.append(Cap(x, row, w, symbol_of_vk(vk) if vk else None, text, h, extra))

    def scan(x, row, code, fallback, w=1.0):
        vk = _vk_of_scan(code)
        if not vk:
            caps.append(Cap(x, row, w, None, fallback))
            return
        caps.append(Cap(x, row, w, symbol_of_vk(vk), _char_of_vk(vk) or fallback))

    def scan_run(x, row, first, fallbacks):
        for i, c in enumerate(fallbacks):
            scan(x + i, row, first + i, c)

    y = 0.0
    fixed(0, y, 1, 0x1B, "Esc")
    for i in range(12):
        fixed(2 + i + (i // 4) * 0.5, y, 1, 0x70 + i, f"F{i + 1}")
    fixed(15.25, y, 1, 0x2C, "keys.cap.prtsc")
    fixed(16.25, y, 1, 0x91, "Scroll")
    fixed(17.25, y, 1, 0x13, "Pause")

    y = 1.5
    scan(0, y, 0x29, "`")
    scan_run(1, y, 0x02, "1234567890-=")
    fixed(13, y, 2, 0x08, "Backspace")
    fixed(15.25, y, 1, 0x2D, "Ins")
    fixed(16.25, y, 1, 0x24, "Home")
    fixed(17.25, y, 1, 0x21, "PgUp")
    fixed(18.5, y, 1, 0x90, "Num")
    fixed(19.5, y, 1, 0x6F, "/")
    fixed(20.5, y, 1, 0x6A, "*")
    fixed(21.5, y, 1, 0x6D, "-")

    y = 2.5
    fixed(0, y, 1.5, 0x09, "Tab")
    scan_run(1.5, y, 0x10, "QWERTYUIOP[]")
    fixed(13.5, y, 1.5, 0x0D, "Enter", extra=(13.75, y + 1, 1.25, 1))
    fixed(15.25, y, 1, 0x2E, "Del")
    fixed(16.25, y, 1, 0x23, "End")
    fixed(17.25, y, 1, 0x22, "PgDn")
    for i, n in enumerate("789"):
        fixed(18.5 + i, y, 1, 0x67 + i, n)
    fixed(21.5, y, 1, 0x6B, "+", h=2)

    y = 3.5
    fixed(0, y, 1.75, 0x14, "Caps")
    scan_run(1.75, y, 0x1E, "ASDFGHJKL;'")
    scan(12.75, y, 0x2B, "\\")
    for i, n in enumerate("456"):
        fixed(18.5 + i, y, 1, 0x64 + i, n)

    y = 4.5
    fixed(0, y, 1.25, 0xA0, "Shift")
    scan(1.25, y, 0x56, "<")
    scan_run(2.25, y, 0x2C, "ZXCVBNM,./")
    fixed(12.25, y, 2.75, 0xA1, "Shift")
    fixed(16.25, y, 1, 0x26, "↑")
    for i, n in enumerate("123"):
        fixed(18.5 + i, y, 1, 0x61 + i, n)
    fixed(21.5, y, 1, 0, "Ent", h=2)       # numpad Enter: the same key as Enter

    y = 5.5
    fixed(0, y, 1.25, 0xA2, "Ctrl")
    fixed(1.25, y, 1.25, 0x5B, "Win")
    fixed(2.5, y, 1.25, 0xA4, "Alt")
    fixed(3.75, y, 6.25, 0x20, "keys.cap.space")
    fixed(10, y, 1.25, 0xA5, "AltGr")
    fixed(11.25, y, 1.25, 0x5C, "Win")
    fixed(12.5, y, 1.25, 0x5D, "Menu")
    fixed(13.75, y, 1.25, 0xA3, "Ctrl")
    fixed(15.25, y, 1, 0x25, "←")
    fixed(16.25, y, 1, 0x28, "↓")
    fixed(17.25, y, 1, 0x27, "→")
    fixed(18.5, y, 2, 0x60, "0")
    fixed(20.5, y, 1, 0x6E, ".")
    return caps


_KEYBOARD_SYMBOLS: frozenset | None = None
_CAP_TEXT: dict | None = None


def on_keyboard(symbol) -> bool:
    global _KEYBOARD_SYMBOLS
    if _KEYBOARD_SYMBOLS is None:
        _KEYBOARD_SYMBOLS = frozenset(c.symbol for c in layout() if c.symbol is not None)
    return symbol in _KEYBOARD_SYMBOLS


def key_name(symbol, t) -> str:
    """A readable name: the label of its key on the picture, else pyglet's."""
    global _CAP_TEXT
    if symbol is None:
        return t("keys.no_key")
    if _CAP_TEXT is None:
        _CAP_TEXT = {}
        for c in layout():
            if c.symbol is not None and c.symbol not in _CAP_TEXT:
                _CAP_TEXT[c.symbol] = c.text
    text = _CAP_TEXT.get(symbol)
    if text is not None:
        return t(text) if text.startswith("keys.cap.") else text
    return key.symbol_string(symbol)


# ------------------------------------------------------------------ bindings

def defaults() -> dict[str, int]:
    return {a: symbol_of_vk(vk) for a, _t, _c, vk in ACTIONS}


def _clash(a: str, b: str) -> bool:
    ca, cb = CONTEXT_OF[a], CONTEXT_OF[b]
    return ca == cb or "any" in (ca, cb)


class Bindings:
    def __init__(self, stored: dict | None = None):
        self.defaults = defaults()
        self.current = dict(self.defaults)
        self.last_valid = dict(self.current)
        if stored:
            self.load(stored)

    # ---- reading

    def key(self, action):
        return self.current.get(action)

    def actions_for(self, symbol, context=None):
        """The actions with this key; with `context`, only those active there."""
        return [a for a in ACTION_IDS if symbol is not None and self.current.get(a) == symbol
                and (context is None or CONTEXT_OF[a] in (context, "any"))]

    def is_bound(self, symbol) -> bool:
        return bool(self.actions_for(symbol))

    def unbound(self):
        return [a for a in ACTION_IDS if self.current.get(a) is None]

    def complete(self) -> bool:
        return not self.unbound()

    # ---- changing

    def check(self, action, symbol):
        """("ok" | "locked" | "system" | "not_on_keyboard" | "in_use", owner)."""
        if symbol in LOCKED:
            return "locked", None
        if symbol in SYSTEM:
            return "system", None
        if symbol is None or not on_keyboard(symbol):
            return "not_on_keyboard", None
        for other in self.actions_for(symbol):
            if other != action and _clash(action, other):
                return "in_use", other
        return "ok", None

    def assign(self, action, symbol) -> bool:
        """Applies a checked key; True when the set is complete (then it is
        the new last valid set, to be saved)."""
        self.current[action] = symbol
        return self._after_change()

    def unbind(self, action):
        self.current[action] = None
        self._after_change()

    def reset(self):
        self.current = dict(self.defaults)
        self._after_change()

    def revert_if_incomplete(self):
        """Back to the last valid set if some action has no key: the actions
        that had none, or []."""
        missing = self.unbound()
        if missing:
            self.current = dict(self.last_valid)
        return missing

    def _after_change(self) -> bool:
        if self.complete():
            self.last_valid = dict(self.current)
            return True
        return False

    # ---- settings

    def stored(self) -> dict:
        """What goes into the settings: only the last valid set."""
        return {a: self.last_valid[a] for a in ACTION_IDS}

    def load(self, stored: dict):
        loaded = dict(self.defaults)
        for a, symbol in stored.items() if isinstance(stored, dict) else ():
            if a in loaded and isinstance(symbol, int) and not isinstance(symbol, bool):
                loaded[a] = symbol
        for a in ACTION_IDS:
            s = loaded[a]
            if s in LOCKED or s in SYSTEM or not on_keyboard(s):
                loaded[a] = self.defaults[a]
        clash = any(loaded[a] == loaded[b] and _clash(a, b)
                    for i, a in enumerate(ACTION_IDS) for b in ACTION_IDS[i + 1:])
        self.current = dict(self.defaults) if clash else loaded
        self.last_valid = dict(self.current)
