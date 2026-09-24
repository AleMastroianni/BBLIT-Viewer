"""Viewer settings that persist from one start to the next.

Same scheme as the CTR viewer: with a `portable.flag` file next to the viewer
(in the project folder) the settings live in `userdata/settings.json`
inside the copy itself; without it, in `Documents/BBLIT Viewer/settings.json`.

In screenshot mode (`--screenshot`) they are neither read nor written: the
verification screenshots must come out the same whatever the user has chosen.

The entity states chosen from the menu (bridges, barrels, crates) are NOT here:
they last for the session, and at start the ones in `preferences.py` come back.
"""

from __future__ import annotations

import ctypes
import json
import os

from support import paths

DEFAULTS = {
    "language": "en",
    "texture": True,
    "props": True,
    "sky": True,
    "blending": True,
    # 0 off, 1 Skeleton, 2 Grid (an old True/False reads as 1/0)
    "wireframe": 0,
    "animated_textures": True,
    # Level options -> Cloned templates: 0 off, 1 in the level (what the game
    # has there by itself, game/clone_life.py), 2 all. A new key: the old
    # "clones" meant "at start" and a saved 0 would hide the mines' rails
    "clones_shown": 1,
    "ticks_per_second": 15.0,
    "fullscreen": False,
    "vsync": True,
    "bilinear_filter": True,
    # Video options -> Distant textures. False = like the PC, which has no
    # mipmaps (finding 306): sharper far away, and it shimmers as you move.
    # True = the smooth ones the viewer had before
    "mipmaps": False,
    "texture_scale": 1,
    "albedo": 1.0,
    # how the byte uvs are read (findings 328, 341): "pc" the PC's OpenGL
    # renderer, clamped to [0.01, 0.99] and repeated, "pc_amd" the same on an
    # AMD card, "psx" the (size - 1) rule of the software renderer and the
    # PlayStation. A saved "pc_edge", the provisional default before finding
    # 341, is no rule any more: it falls back to "pc" (app.py)
    "uv_rule": "pc",
    "field_of_view": 65,
    # Video options -> Backface culling: off, the viewer shows every face
    # (its advantage over the game); on, the one-sided faces are culled as
    # the PC culls them (finding 307), to look inside a level from above
    "backface_culling": False,
    "status_bar": True,
    # levels folder chosen in General options; empty = bze_levels/
    "levels_folder": "",
    # camera bookmarks per level file (Camera and points): {"L03A": [{"n": 1,
    # "x": .., "y": .., "z": .., "yaw": .., "pitch": ..}]}, position in game
    # units; an optional "name" written by hand replaces "Bookmark n"
    "bookmarks": {},
    # the rebindable keys (keybinds.py): {action: pyglet symbol}; empty = defaults
    "key_bindings": {},
    # the first gamepad found drives camera and menu (gamepad.py)
    "gamepad": True,
}

# the keys the settings file used before the code was translated:
# an old file is read with its values, then saved with the new keys
OLD_KEYS = {
    "lingua": "language", "cielo": "sky", "fusioni": "blending",
    "texture_animate": "animated_textures",
    "tick_al_secondo": "ticks_per_second", "schermo_intero": "fullscreen",
    "filtro_bilineare": "bilinear_filter", "scala_texture": "texture_scale",
    "campo_visivo": "field_of_view", "barra_di_stato": "status_bar",
    "cartella_livelli": "levels_folder",
}


def _documents_dir() -> str:
    """The user's Documents folder (even if moved, for example to OneDrive)."""
    try:
        buf = ctypes.create_unicode_buffer(260)
        # CSIDL_PERSONAL = 5
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return buf.value
    except (AttributeError, OSError):
        pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def is_portable() -> bool:
    return os.path.exists(os.path.join(paths.APP_DIR, "portable.flag"))


def route() -> str:
    if is_portable():
        return os.path.join(paths.APP_DIR, "userdata", "settings.json")
    return os.path.join(_documents_dir(), "BBLIT Viewer", "settings.json")


def build() -> str:
    """The kind of copy, from the folder name, like the CTR viewer builds:
    a folder called "BBLIT <kind>", with kind Debug, Current, Development or
    Portable, shows the kind in the window title. Any other name shows nothing.
    """
    name = os.path.basename(paths.APP_DIR)
    kind_of = name[6:] if name.lower().startswith("bblit ") else name
    # known kinds only: a copy in any other folder shows nothing
    return kind_of if kind_of.lower() in ("debug", "current", "development", "portable") else ""


class Settings:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled          # False in screenshot mode
        self.setting_values = dict(DEFAULTS)
        if enabled:
            self._read_file()

    def _read_file(self) -> None:
        try:
            with open(route(), encoding="utf-8") as f:
                loaded = json.load(f)
        except (OSError, ValueError):
            return
        for item_key, value_text in loaded.items():
            item_key = OLD_KEYS.get(item_key, item_key)
            # only known keys of the same type: an old or hand-edited file
            # must not break startup
            if item_key in DEFAULTS and isinstance(value_text, type(DEFAULTS[item_key])):
                self.setting_values[item_key] = value_text

    def persist(self) -> None:
        if not self.enabled:
            return
        file_path = route()
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.setting_values, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"settings not saved to {file_path}: {e}")

    def __getitem__(self, item_key):
        return self.setting_values[item_key]

    def __setitem__(self, item_key, value_text):
        self.setting_values[item_key] = value_text
