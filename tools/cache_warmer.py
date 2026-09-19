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

import level_cache
import levels


def order(folder: str) -> list[str]:
    """The .bze files of the folder that the menu opens, in menu order."""
    try:
        on_disc = {os.path.splitext(f)[0].upper(): os.path.join(folder, f)
                   for f in os.listdir(folder) if f.lower().endswith(".bze")}
    except OSError:
        return []
    seen, output = set(), []
    for item in levels.all_entries():
        name = item[1].upper()
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
    import textures as texmod
    from viewer import Level
    for file_path in order(folder):
        if not parent_alive(parent_pid):
            return
        name = os.path.splitext(os.path.basename(file_path))[0]
        signature = level_cache.signature(file_path)
        if level_cache.is_current(cache, name, signature):
            continue
        pieces = {}
        try:
            table = texmod.construct(folder, name, cache)
            Level(file_path, cache, table, None, pieces, families=set())
        except Exception:  # noqa: BLE001
            continue   # a level that does not build: the viewer will say so when opened
        # the viewer may have opened and saved it meanwhile, maybe with more
        # pieces (the flags): that copy stays
        if not level_cache.is_current(cache, name, signature):
            level_cache.store(cache, name, signature, pieces)


def start(folder: str | None, cache: str):
    """Launches run() in a process of its own; returns it, or None."""
    if not folder:
        return None
    if getattr(sys, "frozen", False):
        command = [sys.executable]
    else:
        command = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.py")]
    command += ["--warm-cache", folder, "--cache", cache, "--parent", str(os.getpid())]
    flags = 0
    if os.name == "nt":
        flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    try:
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, creationflags=flags)
    except OSError:
        return None
