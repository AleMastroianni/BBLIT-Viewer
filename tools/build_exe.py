"""Builds `BBLIT Viewer.exe` with PyInstaller.

    .venv/Scripts/python tools/build_exe.py

The executable ends up in the project folder, next to the sources:
`BBLIT Viewer.exe` and the `_internal` folder with Python and the libraries,
both outside git. It finds the levels like the sources (`tools/paths.py`).
PyInstaller's work stays in `build/`. A folder and not a single file, like
the CTR viewer's Portable copy: it starts at once, without unpacking itself
at every launch.

Inside the executable are the icon and background from `resources/` and
the sources hash (`code_hash.txt`, for the piece cache); the game's files
are not. The packages to hand out start from here.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(PROJECT_DIR, "tools")
NAME = "BBLIT Viewer"
WORK_DIR = os.path.join(PROJECT_DIR, "build")


def _work_around_dis_310() -> None:
    """Python 3.10.0 (the .venv's) has a bug in `dis`: with certain
    EXTENDED_ARG it reads a constant index outside the table, and PyInstaller's
    module analysis stops with IndexError (fixed in 3.10.1).
    Here an unreadable constant becomes a placeholder: it only affects the
    import search during the build, and the executable is tested by
    launching it. Not needed with a more recent Python."""
    import dis
    if sys.version_info[:3] != (3, 10, 0):
        return
    original = dis._get_const_info

    def safe_const_info(const_index, const_list):
        try:
            return original(const_index, const_list)
        except IndexError:
            return None, ""

    dis._get_const_info = safe_const_info


def _clear_readonly(func, file_path, _error):
    os.chmod(file_path, stat.S_IWRITE)
    func(file_path)


def main() -> None:
    _work_around_dis_310()
    import PyInstaller.__main__
    sys.path.insert(0, TOOLS)
    import level_cache

    os.makedirs(WORK_DIR, exist_ok=True)
    fingerprint = os.path.join(WORK_DIR, level_cache.FINGERPRINT_FILE)
    with open(fingerprint, "w", encoding="ascii") as f:
        f.write(level_cache.sources_fingerprint(TOOLS))

    pyi_dist = os.path.join(WORK_DIR, "dist")
    resources = os.path.join(PROJECT_DIR, "resources")
    pyi_args = [
        os.path.join(TOOLS, "viewer.py"),
        "--name", NAME,
        "--windowed",                 # no console: errors go to errors.txt
        "--noconfirm",
        "--paths", TOOLS,
        "--distpath", pyi_dist,
        "--workpath", WORK_DIR,
        "--specpath", WORK_DIR,
        "--add-data", f"{fingerprint}{os.pathsep}.",
    ]
    if os.path.isdir(resources):
        pyi_args += ["--add-data", f"{resources}{os.pathsep}resources"]
        icon_path = os.path.join(resources, "icon.ico")
        if os.path.exists(icon_path):
            pyi_args += ["--icon", icon_path]
    PyInstaller.__main__.run(pyi_args)

    # in the project folder: only the executable and _internal are replaced.
    # The old _internal is renamed first: if the viewer is open Windows
    # refuses and nothing has been deleted (a direct rmtree once removed
    # half the files of the running executable before stopping)
    built_dir = os.path.join(pyi_dist, NAME)
    internal_dir = os.path.join(PROJECT_DIR, "_internal")
    if os.path.exists(internal_dir):
        old_dir = internal_dir + "_old"
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir, onerror=_clear_readonly)
        try:
            os.rename(internal_dir, old_dir)
        except OSError:
            print(f"\n{NAME}.exe is open: close it and run again (nothing was touched)")
            return 1
        shutil.rmtree(old_dir, onerror=_clear_readonly)
    shutil.copytree(os.path.join(built_dir, "_internal"), internal_dir)
    shutil.copy2(os.path.join(built_dir, NAME + ".exe"), PROJECT_DIR)
    print(f"\nexecutable in {os.path.join(PROJECT_DIR, NAME + '.exe')}")


if __name__ == "__main__":
    sys.exit(main())
