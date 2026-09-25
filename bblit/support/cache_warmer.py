"""Fills the piece cache (level_cache.py) in the background, so that the
first opening of a level is as fast as going back to one already seen
(measured: median 0.76 s, up to 4.8 s for CC1A -> about 0.05 s).

The viewer starts it at launch as a separate process, with low priority and
no window (`viewer.py --warm-cache FOLDER --parent PID`, the same for the
executable). It builds, one by one, the menu levels of the folder whose
saved pieces are missing or from other code, exactly as the viewer builds
them when it opens one with the flags off (same `Level`, same pieces:
check_level_cache.py), and saves them. Nothing about what is drawn changes:
only when the work is done. Between two levels it checks that the viewer is
still open, otherwise it stops; a level it is building is never half saved
(level_cache.store).
"""

from __future__ import annotations

import os
import subprocess
import sys

from support import level_cache
from game import levels


def order(folder: str, extra: bool = True) -> list[str]:
    """The .bze files of the folder that the menu opens, in menu order.
    Without `extra` the Extra files (cutscenes, menu, credits, `_8`
    variants) are left out: only the Debug build's menu lists them, and the
    other copies would build and save 24 files nobody opens."""
    try:
        on_disc = {os.path.splitext(f)[0].upper(): os.path.join(folder, f)
                   for f in os.listdir(folder) if f.lower().endswith(".bze")}
    except OSError:
        return []
    seen, output = set(), []
    for item in levels.all_entries():
        name = item[1].upper()
        if not extra and levels.is_extra(name):
            continue
        if name in on_disc and name not in seen:
            seen.add(name)
            output.append(on_disc[name])
    return output


def parent_alive(pid: int | None) -> bool:
    if not pid:
        return True
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x00100000, False, pid)   # SYNCHRONIZE
        if not handle:
            return False
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x102   # WAIT_TIMEOUT: still running
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def run(folder: str, cache: str, parent_pid: int | None = None) -> None:
    from game import textures as texmod
    from ui import settings as settings_mod
    from viewer import Level
    for file_path in order(folder, extra=settings_mod.build() == "Debug"):
        if not parent_alive(parent_pid):
            return
        name = os.path.splitext(os.path.basename(file_path))[0]
        signature = level_cache.signature(file_path)
        if level_cache.is_current(cache, name, signature):
            continue
        pieces = {}
        try:
            table = texmod.construct(folder, name, cache)
            # as the viewer opens it: the characters that move are on
            # (app.py, show_movers), and their pieces have keys of their own
            Level(file_path, cache, table, None, pieces, families=set(), movers=True)
        except Exception:  # noqa: BLE001
            continue   # a level that does not build: the viewer will say so when opened
        # the viewer may have opened and saved it meanwhile, maybe with more
        # pieces (the flags): that copy stays
        if not level_cache.is_current(cache, name, signature):
            level_cache.store(cache, name, signature, pieces)


def _launch(arguments: list[str]):
    """A viewer process of its own, low priority and no window."""
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable,
                   os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "viewer.py")]
    command += arguments + ["--parent", str(os.getpid())]
    flags = 0
    if os.name == "nt":
        flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=flags)
    except OSError:
        return None


def start(folder: str | None, cache: str):
    """Launches run() in a process of its own; returns it, or None."""
    if not folder:
        return None
    return _launch(["--warm-cache", folder, "--cache", cache])

def run_flags(file_path: str, cache: str, parent_pid: int | None = None) -> None:
    """Builds ONE level with every flag family and adds its pieces to the
    saved ones. The viewer starts this as soon as it opens a level: by the
    time the user asks for a flag the work is already done and turning it on
    is only showing groups (`app.ensure_overlays`). What it builds is what
    the viewer would build itself, piece for piece: same `Level`, same keys.
    """
    from game import textures as texmod
    from viewer import Level
    from window.scene import FAMILIES
    if not parent_alive(parent_pid):
        return
    folder = os.path.dirname(file_path)
    name = os.path.splitext(os.path.basename(file_path))[0]
    signature = level_cache.signature(file_path)
    pieces = level_cache.fetch(cache, name, signature) or {}
    before = len(pieces)
    try:
        table = texmod.construct(folder, name, cache)
        Level(file_path, cache, table, None, pieces, families=tuple(FAMILIES), movers=True)
    except Exception:  # noqa: BLE001
        return
    if len(pieces) <= before:
        _mark_flags_done(file_path, cache)   # everything was there already
        return
    if not parent_alive(parent_pid):
        return
    # whoever else saved meanwhile keeps its pieces: the union is stored
    saved = level_cache.fetch(cache, name, signature) or {}
    saved.update(pieces)
    level_cache.store(cache, name, signature, saved)
    if level_cache.is_current(cache, name, signature):
        _mark_flags_done(file_path, cache)


FLAGS_DONE = "flags_done.txt"


def flags_key(file_path: str) -> str:
    """What the flag families of a level depend on: the level's piece
    signature (its file and the code) and the folder's levels (the ENTRANCE
    names, game/entrances.py)."""
    from game import entrances
    return level_cache.signature(file_path) + "|" + entrances.folder_signature(os.path.dirname(file_path))


def flags_done(file_path: str, cache: str) -> bool:
    """Whether the flag families of this level are already saved for this
    very key: then the viewer does not start the builder again (it cost
    1-3 s of processor at every level change for nothing)."""
    name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        with open(os.path.join(cache, name, FLAGS_DONE), encoding="ascii") as f:
            return f.read().strip() == flags_key(file_path)
    except (OSError, ValueError):
        return False


def _mark_flags_done(file_path: str, cache: str) -> None:
    name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        with open(os.path.join(cache, name, FLAGS_DONE), "w", encoding="ascii") as f:
            f.write(flags_key(file_path))
    except OSError:
        pass


def start_flags(file_path: str, cache: str):
    """Launches run_flags in a process of its own; returns it, or None."""
    return _launch(["--warm-flags", file_path, "--cache", cache])

