"""The rules that clone or delete a sky, on the whole disc.

    .venv/Scripts/python tools/sky_rules.py [--level L02B1] [--all]

A sky is an object the game carries with the camera (`scene.carried_by_camera`:
type 9, or type 14 with bit 0x20000000) that has a model. For each one, placed
or template, the list says which rules of which objects clone it (effect 0x100
or 0x40000 naming its role in field +28, finding 314) and which delete it
(effect 0x4000000 naming its role), with the rule's condition and whether it
is true when the level starts (`scene._at_startup`).

Without `--all` only the levels where some rule deletes a sky are printed:
those are the levels where two skies take turns.
"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))

from game import levels  # noqa: E402
from game import montage  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from window import scene  # noqa: E402
from window.scene import Level, levels_in  # noqa: E402

CLONES, DELETES = 0x100 | 0x40000, 0x4000000


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def condition_text(rule, owner=None):
    op, val, index = rule["condition"]
    text = f"cond op 0x{op:02X} val {val} index {index}, effect 0x{rule['effect']:08X}"
    if owner is not None:
        start = montage.start_key(owner)
        steps = [st["key"] for st in owner.get("steps", ()) if st.get("rules") == rule["key"]]
        text += (", in the STARTING step" if rule["key"] == start or start in steps
                 else f", in rule group {rule['key']} (steps {steps}, start {start})")
    return text


def skies(level):
    """(index, object, width in units) of every camera follower with a model."""
    res = {r["id"]: r for r in level.lvl["resources"]}
    found = []
    for n, o in enumerate(level.lvl["objects"]):
        if not scene.carried_by_camera(o):
            continue
        mid = next((r for r in o["resources"] if res.get(r, {}).get("data_kind") == "model"), None)
        if mid is None or res[mid]["size"] <= 12:
            continue
        found.append((n, o))
    return found


def survey(code, file_path):
    table = texmod.construct(os.path.dirname(file_path), code, "extracted")
    level = Level(file_path, "extracted", table, None,
                  level_cache.fetch("extracted", code, level_cache.signature(file_path)) or {})
    objects = level.lvl["objects"]
    rows = []
    for n, o in skies(level):
        role = o["role"]
        clones, deletes = [], []
        for m, other in enumerate(objects):
            for r in other.get("rules", []):
                if r["field28"] != role or role <= 0:
                    continue
                if r["effect"] & CLONES:
                    clones.append((m, other, r))
                if r["effect"] & DELETES:
                    deletes.append((m, other, r))
        rows.append({"n": n, "object": o, "template": o["block_type"] == 0x08,
                     "clones": clones, "deletes": deletes})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--level")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    files = levels_in(paths.find_levels_folder(None))
    n_levels = n_with_delete = 0
    for file_path in files:
        code = os.path.splitext(os.path.basename(file_path))[0]
        if args.level and code.lower() != args.level.lower():
            continue
        try:
            rows = survey(code, file_path)
        except Exception as e:  # noqa: BLE001
            print(f"{code}: not built ({e})")
            continue
        n_levels += 1
        deleting = any(row["deletes"] for row in rows)
        n_with_delete += deleting
        if not (deleting or args.all or args.level):
            continue
        print(f"\n## {in_prose(code)}")
        for row in rows:
            o = row["object"]
            kind = "template" if row["template"] else "placed"
            print(f"- sky {row['n']} ({kind}), type {o.get('category')}, role {o['role']}, "
                  f"Y {o.get('camera_y') or 0:+d}")
            for m, other, r in row["clones"]:
                start = "AT START" if scene._at_startup(r) else "later"
                who = "template" if other["block_type"] == 0x08 else "placed"
                print(f"    cloned by {m} ({who}, role {other['role']}), {start}: {condition_text(r, other)}")
            for m, other, r in row["deletes"]:
                who = "template" if other["block_type"] == 0x08 else "placed"
                print(f"    DELETED by {m} ({who}, role {other['role']}): {condition_text(r, other)}")
    print(f"\n{n_levels} levels, {n_with_delete} with a rule that deletes a sky")
    return 0


if __name__ == "__main__":
    sys.exit(main())
