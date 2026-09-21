"""The decompressed-section cache follows its `.bze`.

    .venv/Scripts/python checks/check_section_cache.py

In a temporary folder: a level file `TEST.bze` (a copy of L03A) is read
through the cache, then replaced by another level under the same name (a
copy of L01A). The sections read afterwards must be those of the new file,
byte for byte, and not the ones cached for the old one; a third read, with
nothing changed, must come from the cache (the files are not rewritten).
Checked for both readers: `textures.sections` and `viewer.sections`.
Exits with 1 if anything differs.
"""
import os
import shutil
import sys
import tempfile
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
from game import bze  # noqa: E402
from support import paths  # noqa: E402
from game import textures  # noqa: E402
import viewer  # noqa: E402


def direct(bze_path):
    """The sections decompressed straight from the file, no cache."""
    entries, data = bze.open_bze(bze_path)
    return {s.id: bze.section_bytes(data, s) for s in entries if s.id in (1, 3, 4)}


errors = 0
for label, reader in (("textures.sections", textures.sections), ("viewer.sections", viewer.sections)):
    with tempfile.TemporaryDirectory() as tmp:
        level = os.path.join(tmp, "TEST.bze")
        cache = os.path.join(tmp, "cache")
        shutil.copyfile(os.path.join(paths.DATA_BZE, "L03A.bze"), level)
        first = reader(level, cache)
        ok_first = first == direct(level)
        time.sleep(0.05)                      # a different modification time
        shutil.copyfile(os.path.join(paths.DATA_BZE, "L01A.bze"), level)
        second = reader(level, cache)
        ok_second = second == direct(level) and second != first
        cached = os.path.join(cache, "TEST", "TEST_id04.bin")
        before = os.stat(cached).st_mtime_ns
        third = reader(level, cache)
        ok_third = third == second and os.stat(cached).st_mtime_ns == before
    print(f"{label}: first read {'ok' if ok_first else 'WRONG'}; after replacing the file "
          f"{'the new sections' if ok_second else 'the OLD sections (stale cache)'}; "
          f"unchanged file {'from the cache' if ok_third else 'rewritten or different'}")
    errors += (not ok_first) + (not ok_second) + (not ok_third)
print("all consistent" if not errors else f"{errors} failures")
sys.exit(1 if errors else 0)
