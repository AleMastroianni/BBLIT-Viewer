"""Which level an entrance comes from (finding 326).

A level change carries no entrance number. The zone rule that changes level
also writes a byte of the save with its action (`0x13` sets it, `0x0c` adds
bits), and in the new level a zone rule with effect `0x800` reads that byte
and puts Bugs at its three parameters. So:

* a `0x800` rule **with a condition on a byte** is the way in from another
  level, not a teleport you can use while playing: the viewer writes
  ENTRANCE on it;
* a `0x800` rule **with no condition at all** fires whenever Bugs is in the
  zone: that is a real teleport, and the viewer writes TELEPORT.

The level an entrance comes from is the one whose level change leads here
and writes that byte with a bit the condition tests. Finding it means
reading every level's zones once, about 1.2 s with the section cache warm;
it is done once per run, and only when a level that has an entrance is
built with the Teleport zones flag on.
"""

from __future__ import annotations

import os

from game import levels
from game import loadscript
from game import textures
from game import zones

# the actions a level change writes the byte with: 0x13 sets it, 0x0c adds bits
SET_BYTE, ADD_BITS = 0x13, 0x0C

# {folder: [(source file, destination file, byte, value), ...]}: read once
_changes: dict[str, list[tuple[str, str, int, int]]] = {}


def _level_changes(folder: str, cache: str) -> list[tuple[str, str, int, int]]:
    """Every level change on the disc, as (source file, destination file,
    byte written, value written). Read once per folder."""
    key = os.path.abspath(folder)
    if key in _changes:
        return _changes[key]
    output = []
    for entry in sorted(os.listdir(folder)):
        if not entry.lower().endswith(".bze"):
            continue
        source = os.path.splitext(entry)[0]
        if source.lower().endswith("_8"):
            # the variants on the disc that the game's level table does not
            # list: they are a copy of the file beside them, and naming them
            # as the level you came from would only be confusing
            continue
        try:
            sec = textures.sections(os.path.join(folder, entry), cache, ids=(1,))
            lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
        except Exception:  # noqa: BLE001
            continue          # a file we cannot read simply says nothing
        for z in lvl["zones"]:
            for r in z.get("rules", []):
                if not r["effect"] & zones.LEVEL_CHANGE:
                    continue
                destination = levels.file_of_levid(r["parameters"][0])
                action, value, byte = r["action"]
                if destination and action in (SET_BYTE, ADD_BITS):
                    output.append((source, destination, byte, value))
    _changes[key] = output
    return output


def sources_of(rule: dict, level_name: str, folder: str, cache: str) -> list[str]:
    """The files of the levels an entrance rule can be entered from: those
    whose level change leads to `level_name` and writes the byte the rule's
    condition reads, with a bit the condition tests. Sorted, without
    repeats; empty when nothing on the disc writes that byte."""
    if not zones.is_entrance(rule):
        return []
    _op, mask, byte = rule["condition"]
    found = {source for source, destination, written_byte, value
             in _level_changes(folder, cache)
             if destination.lower() == level_name.lower() and written_byte == byte and value & mask}
    return sorted(found)


def forget() -> None:
    """Drops what was read: for the checks, which change folder."""
    _changes.clear()
