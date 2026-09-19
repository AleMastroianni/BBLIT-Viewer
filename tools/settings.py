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

import paths

DEFAULTS = {
    "language": "en",
    "texture": True,
    "props": True,
    "sky": True,
    "blending": True,
    "wireframe": False,
    "animated_textures": True,
    "clones": 0,
    "ticks_per_second": 15.0,
    "fullscreen": False,
    "vsync": True,
    "bilinear_filter": True,
    "texture_scale": 1,
    "albedo": 1.0,
    "field_of_view": 65,
    "status_bar": True,
    # levels folder chosen in General options; empty = bze_levels/
    "levels_folder": "",
}

# the keys the settings file used before the code was translated:
# an old file is read with its values, then saved with the new keys
OLD_KEYS = {
    "lingua": "language", "cielo": "sky", "fusioni": "blending",
    "texture_animate": "animated_textures", "cloni": "clones",
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
