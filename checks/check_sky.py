"""The sky and the sea when they arrive as a cloned template.

    .venv/Scripts/python checks/check_sky.py

The game draws the sky and the sea by putting an object wherever the camera
is, at every tick, ignoring the position in its file. Its test, read in the
game's code by the reverse (note N39): **type 9**, or type 14 with bit
0x20000000 in the second dword of opcode 0x16.

`Level._placed_object` has long had the same effect for a PLACED object, but
by a guess -- "a prop as large as the whole level". `Level._clone` had
nothing: a sky arriving as a cloned TEMPLATE was drawn as an ordinary clone,
standing still inside the level -- the black cones and the block the user
photographed in The Carrot-henge Mystery 3 (`L02C3`) -- and with Cloned
templates off, which is the default, the level had no sky at all.

The proof is independent and level by level: the reverse's
`..\\BBLIT_Decomp_ALE\\docs\\lists\\placement.md` lists, for every level, the
objects the game places at the camera. This check reads that file and
compares it with what the viewer now does, so it fails if either side moves.

It also holds down the two readings that were tried and dropped:

* **size** would be wrong. When Sam met Bunny (`L03B`) is 56 m across and has
  eight cloned templates bigger than that; Mine or mine? 3 (`L03C2`) has two
  more. None of the ten is a sky, and placement.md gives neither level a
  camera object among them.
* **bit 0x02000000** would be wrong. Every sky of the Carrot-henge family
  carries it, but so do hundreds of ordinary small objects.
"""
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import textures as texmod  # noqa: E402
from support import paths  # noqa: E402
from window.scene import FOLLOWS_CAMERA, Level, levels_in  # noqa: E402

PLACEMENT = os.path.join(os.path.dirname(paths.PROJECT_DIR), "BBLIT_Decomp_ALE",
                         "docs", "lists", "placement.md")
NOT_A_SKY_BIT = 0x02000000        # the dropped hypothesis
NO_CLONE_SKY = ("L03B", "L03B_8", "L03C2")   # big clones that are not skies
results = []


def probe(entry_name, cond):
    results.append((entry_name, bool(cond)))
    print(("OK   " if cond else "FAIL ") + entry_name)


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code.upper()})" if name else code.upper()


def read_placement(path):
    """{level code: {object number the game puts at the camera: its Y offset}}.

    An item reads `91 (template 849) [type 9; Y -3500]`: the number, maybe
    the template, maybe notes in brackets; the offset of opcode 0x1E is
    written only when it is not zero."""
    by_level, code = {}, None
    item = re.compile(r"(\d+)(?:\s*\(template \d+\))?\s*(?:\[([^\]]*)\])?")
    for line in open(path, encoding="utf-8"):
        heading = re.match(r"^##\s+.*?`([^`]+)`\s*\)?\s*$", line)
        if heading:
            code = heading.group(1).upper()
            by_level.setdefault(code, {})
            continue
        if code and line.startswith("- **camera**:"):
            rest = line.split(":", 1)[1]
            found = {}
            for number, notes in item.findall(rest):
                y = re.search(r"\bY ([+-]?\d+)", notes or "")
                found[int(number)] = int(y.group(1)) if y else 0
            by_level[code] = found
    return by_level


def at_the_camera(level):
    """The objects this level would put at the camera, by the game's test."""
    found = set()
    for n, o in enumerate(level.lvl["objects"]):
        if o.get("category") == 9:
            found.add(n)
        elif o.get("category") == 14 and ((o.get("static_flags") or [0, 0])[1] & FOLLOWS_CAMERA):
            found.add(n)
    return found


def build(code, pieces=None):
    path = os.path.join(paths.DATA_BZE, code + ".bze")
    textures = texmod.construct(paths.DATA_BZE, code, "extracted")
    return Level(path, "extracted", textures, None, {} if pieces is None else pieces)


if not os.path.exists(PLACEMENT):
    print(f"placement.md not found at {PLACEMENT}: the reverse's list is the proof of this check")
    sys.exit(1)
placement = read_placement(PLACEMENT)
print(f"placement.md: {len(placement)} levels, "
      f"{sum(len(v) for v in placement.values())} objects placed at the camera, "
      f"{sum(1 for v in placement.values() for y in v.values() if y)} with a height of their own")
probe("placement.md gives the 97 camera objects of the disc",
      sum(len(v) for v in placement.values()) == 97)

# ---- the viewer's reading is the reverse's, level by level

disagree, missing_from_list, promoted, skyless = [], [], {}, []
wrong_y, wrong_sky, y_checked = [], [], 0
for path in levels_in(paths.DATA_BZE):
    code = os.path.splitext(os.path.basename(path))[0]
    try:
        level = build(code)
    except Exception as error:  # noqa: BLE001
        disagree.append(f"{in_prose(code)}: {type(error).__name__}: {error}")
        continue
    mine = at_the_camera(level)
    theirs = placement.get(code.upper())
    if theirs is None:
        missing_from_list.append(code)
    elif mine != set(theirs):
        disagree.append(f"{in_prose(code)}: the viewer reads {sorted(mine)}, "
                        f"placement.md says {sorted(theirs)}")
    else:
        # the height of opcode 0x1E, object by object
        for n in mine:
            y_checked += 1
            if (level.lvl["objects"][n]["camera_y"] or 0) != theirs[n]:
                wrong_y.append(f"{in_prose(code)} object {n}: the viewer reads "
                               f"{level.lvl['objects'][n]['camera_y']}, placement.md {theirs[n]}")
    # the PLACED objects drawn as sky must be exactly the camera objects
    # among them: no more guessing by size
    for key, piece in level._pieces.items():
        if not (isinstance(key, tuple) and key and key[0] == "object"):
            continue
        as_sky = any(meta[1] == "sky_dome" for meta in piece[0])
        if as_sky != (key[1] in mine):
            wrong_sky.append(f"{in_prose(code)} object {key[1]}: "
                             f"{'sky' if as_sky else 'not sky'} in the viewer, "
                             f"{'at' if key[1] in mine else 'not at'} the camera in the game")
    sky = level.stat.get("sky_dome", 0)
    if not sky:
        skyless.append(code)
    # how many sky parts came from a clone: the templates among the camera
    # objects are not placed, so they can only arrive that way
    from_clone = sum(1 for n in mine if not level.lvl["objects"][n]["position"]
                     or level.lvl["objects"][n]["block_type"] == 0x08)
    if from_clone:
        promoted[code] = from_clone
for line in disagree[:12]:
    print("  " + line)
probe("the viewer reads the camera objects exactly as placement.md does", not disagree)
for line in wrong_y[:12]:
    print("  " + line)
probe(f"the height of opcode 0x1E is placement.md's for all {y_checked} camera objects", not wrong_y)
for line in wrong_sky[:12]:
    print("  " + line)
probe("the placed objects drawn as sky are exactly the camera objects", not wrong_sky)
print(f"levels of placement.md not on the disc folder: {len(missing_from_list)}")
print(f"levels whose sky arrives as a cloned template: {len(promoted)} "
      f"({', '.join(sorted(promoted))})")
print(f"levels with no sky at all after the change: {len(skyless)}")
probe("the sky of The Carrot-henge Mystery 3 arrives as a clone", "L02C3" in promoted)

# ---- and the viewer really draws it as sky: the probe that fails without the
# repair, because `_clone` used to leave it in the clones group.
# Era selector (`LS01`) is not here on purpose: its camera object 12 is a
# template that nothing clones in the state the viewer shows, and the same
# model is also placed there as object 165, which is sky already.

SKY_FROM_A_CLONE = {"L02A6": 1, "L02B1": 1, "L02B2": 1, "L02C3": 3, "L02C4": 1,
                    "L04A2": 1, "L04B1": 1, "L04E": 2, "L04E2": 1}
wrong = []
for code in sorted({c.upper() for c in promoted} | set(SKY_FROM_A_CLONE)):
    level = build(code)
    from_clone = sum(1 for key, piece in level._pieces.items()
                     if isinstance(key, tuple) and key and key[0] == "clone"
                     and any(meta[1] == "sky_dome" for meta in piece[0]))
    want = SKY_FROM_A_CLONE.get(code.upper(), 0)
    print(f"  {in_prose(code)[:52]:52s} {from_clone} sky pieces from a clone, {want} expected, "
          f"{level.stat.get('sky_dome', 0)} sky parts in all")
    if from_clone != want:
        wrong.append(f"{in_prose(code)}: {from_clone} instead of {want}")
probe("every sky built from a template is drawn as sky, not as a clone", not wrong)

# ---- one sky at a time where the level has one per area (Era selector)

level = build("LS01")
by_area = sorted({g.area for g in level.face_groups.values() if g.category == "sky_dome"},
                 key=str)
print(f"{in_prose('LS01')}: sky groups by area {by_area}")
probe("Era selector keeps its five skies apart, one per area (1 to 5)",
      [a for a in by_area if a is not None] == [1, 2, 3, 4, 5])

# ---- size would have been wrong: the levels that must NOT gain a sky

for code in NO_CLONE_SKY:
    level = build(code)
    big = 0
    models = {r["id"]: r for r in level.lvl["resources"] if r["data_kind"] == "model"}
    diagonal = max(h - l for h, l in zip(level.terrain_hi, level.terrain_lo))
    at_camera_all = at_the_camera(level)
    for n, o in enumerate(level.lvl["objects"]):
        if n in at_camera_all:
            continue          # the game does place this one at the camera
        mid = next((r for r in o["resources"] if r in models), None)
        if mid is None or models[mid]["size"] <= 12:
            continue
        try:
            vertices, faces, _ = geo.read_model(level.sec4, models[mid]["offset"], None)
        except Exception:  # noqa: BLE001
            continue
        if vertices and faces and max(max(p[k] for p in vertices) - min(p[k] for p in vertices)
                                      for k in range(3)) / geo.UNITS_PER_METER > 0.8 * diagonal:
            big += 1
    print(f"{in_prose(code)}: {big} objects larger than the level that the game does NOT "
          f"put at the camera; it puts {len(at_camera_all)} there")
    probe(f"size alone would have been wrong in {code}: big objects, none of them a sky", big > 0)

# ---- the bit that was dropped

carries = ordinary = 0
for code in ("L01A", "L01B", "L02C3", "L03A", "L04E"):
    level = build(code)
    models = {r["id"]: r for r in level.lvl["resources"] if r["data_kind"] == "model"}
    diagonal = max(h - l for h, l in zip(level.terrain_hi, level.terrain_lo))
    for o in level.lvl["objects"]:
        mid = next((r for r in o["resources"] if r in models), None)
        if mid is None or models[mid]["size"] <= 12:
            continue
        try:
            vertices, faces, _ = geo.read_model(level.sec4, models[mid]["offset"], None)
        except Exception:  # noqa: BLE001
            continue
        if not (vertices and faces):
            continue
        span = max(max(p[k] for p in vertices) - min(p[k] for p in vertices)
                   for k in range(3)) / geo.UNITS_PER_METER
        if (o.get("static_flags") or [0, 0])[1] & NOT_A_SKY_BIT:
            carries += 1
            if span < 0.2 * diagonal:
                ordinary += 1
print(f"bit 0x02000000 over five levels: {carries} objects carry it, {ordinary} of them "
      f"smaller than a fifth of the level")
probe("bit 0x02000000 is not a sky marker: ordinary small objects carry it", ordinary > 20)

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
