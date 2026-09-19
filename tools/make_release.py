"""The release: the folder and the zip to publish, without any game data.

    python tools/build_exe.py
    python tools/make_release.py [--out FOLDER]

Starts from the executable built by `tools/build_exe.py` and writes FOLDER
(default `release/BBLIT Viewer/`, outside git) with `BBLIT Viewer.exe`,
`_internal/`, `portable.flag` (settings in `userdata/` next to the viewer,
nothing written to Documents), README.md, README_Ita.md, LICENSE and
`bze_levels/` with only its README. Inside it, `<FOLDER name>.zip` with the
same things under one folder, ready to attach to a release; its SHA-256 is
printed, for the release notes.

Only these parts are replaced: `userdata/`, `extracted/` and `errors.txt` of
whoever tried the folder stay, and never go into the zip.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import stat
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

EXECUTABLE = "BBLIT Viewer.exe"
DEFAULT_DIR = os.path.join(paths.PROJECT_DIR, "release", "BBLIT Viewer")
DOCUMENTS = ("README.md", "README_Ita.md", "LICENSE")
LEVELS_README = os.path.join("bze_levels", "README.txt")
# the generated parts: only these are replaced and go into the zip
PARTS = (EXECUTABLE, "_internal", "portable.flag", *DOCUMENTS, "bze_levels")


def _clear_readonly(func, file_path, _error):
    os.chmod(file_path, stat.S_IWRITE)
    func(file_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=DEFAULT_DIR, help="the release folder")
    output_folder = os.path.abspath(parser.parse_args().out)
    name = os.path.basename(output_folder)
    zip_path = os.path.join(output_folder, name + ".zip")

    if not (os.path.exists(os.path.join(paths.PROJECT_DIR, EXECUTABLE))
            and os.path.isdir(os.path.join(paths.PROJECT_DIR, "_internal"))):
        print("no executable in the project folder: run tools/build_exe.py first")
        return 1
    missing = [d for d in (*DOCUMENTS, LEVELS_README)
               if not os.path.exists(os.path.join(paths.PROJECT_DIR, d))]
    if missing:
        print("missing: " + ", ".join(missing))
        return 1

    os.makedirs(output_folder, exist_ok=True)
    internal_dir = os.path.join(output_folder, "_internal")
    if os.path.isdir(internal_dir):
        # if the release is open Windows refuses to rename: nothing touched
        try:
            os.rename(internal_dir, internal_dir + "_test")
            os.rename(internal_dir + "_test", internal_dir)
        except OSError:
            print("the release is open: close it and run again (nothing was touched)")
            return 1
    for part_label in PARTS:
        full_path = os.path.join(output_folder, part_label)
        if os.path.isdir(full_path):
            shutil.rmtree(full_path, onerror=_clear_readonly)
        elif os.path.exists(full_path):
            os.chmod(full_path, stat.S_IWRITE)
            os.remove(full_path)
    shutil.copy2(os.path.join(paths.PROJECT_DIR, EXECUTABLE), output_folder)
    shutil.copytree(os.path.join(paths.PROJECT_DIR, "_internal"), internal_dir)
    open(os.path.join(output_folder, "portable.flag"), "w").close()
    for document in DOCUMENTS:
        shutil.copyfile(os.path.join(paths.PROJECT_DIR, document), os.path.join(output_folder, document))
    os.makedirs(os.path.join(output_folder, "bze_levels"))
    shutil.copyfile(os.path.join(paths.PROJECT_DIR, LEVELS_README),
                    os.path.join(output_folder, LEVELS_README))

    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for part_label in PARTS:
            full_path = os.path.join(output_folder, part_label)
            if os.path.isfile(full_path):
                z.write(full_path, os.path.join(name, part_label))
                continue
            for root, _dirs, files in os.walk(full_path):
                for entry_name in sorted(files):
                    f = os.path.join(root, entry_name)
                    z.write(f, os.path.join(name, os.path.relpath(f, output_folder)))
    os.replace(tmp, zip_path)
    mb = os.path.getsize(zip_path) / 2**20
    # the executable is not signed: the zip's SHA-256 goes into the release
    # notes, so whoever downloads it can check it
    digest = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    print(f"release in {output_folder}\nzip {zip_path} ({mb:.0f} MB)\nSHA-256 {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
