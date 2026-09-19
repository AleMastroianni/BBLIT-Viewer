"""The zone shapes (tools/zones.py) against the game's own test.

    .venv/Scripts/python tools/diagnostics/check_zones.py [L02A4 ...]

The game's test (`0x434c70` in this build of bugs.exe, finding 290) is
emulated in integers: d = p - origin in 16 bits; y_limit <= d.y <= 0;
d turned by RotMatrixZYX of the negated angles (entries in Q12, products
>> 12, as ApplyMatrixSV), then 0 <= x' <= extent X and 0 <= z' <= extent Z;
flag bit 0 skips the rotation. For every zone that kills, teleports or
hurts, random points around it must be inside the emulated test exactly
when ZoneShape.vertical_span says so (a few points on the border may
differ by the game's rounding). For the rotated zones the same count with
the rotation ignored is the null: it must disagree much more.

Points farther than 32767 units from the origin on some axis are counted
apart: there the game's 16-bit distance wraps round, so every zone acts
again 65536 units (512 m) away on each axis, far outside every level
(finding 290). ZoneShape draws the zone once.
Exits with 1 if more than 0.01% of the other points disagree.
"""
import os
import random
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import levels  # noqa: E402
import loadscript  # noqa: E402
import paths  # noqa: E402
import zones  # noqa: E402
from viewer import sections  # noqa: E402

SAMPLES = 20000


def s16(v):
    return ((int(v) + 0x8000) & 0xFFFF) - 0x8000


def game_test(z):
    ex, y_limit, ez, _radius = z["size"]
    angles = [a % 4096 for a in (z.get("rotation") or (0, 0, 0))]
    rotated = any(angles) and not (z["flags"][0] & zones.NO_ROTATION)
    m = [[int(round(4096 * v)) for v in row] for row in zones._matrix(angles)] if rotated else None

    def inside(p):
        d = [s16(p[k] - z["origin"][k]) for k in range(3)]
        if d[1] > 0 or d[1] < y_limit:
            return False
        if m is not None:
            d = [s16((m[i][0] * d[0] + m[i][1] * d[1] + m[i][2] * d[2]) >> 12) for i in range(3)]
        return 0 <= d[0] <= ex and 0 <= d[2] <= ez
    return inside


def shape_test(shape):
    def inside(p):
        span = shape.vertical_span(p[0], p[2])
        return span is not None and span[0] <= p[1] <= span[1]
    return inside


def main():
    names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
    rng = random.Random(1)
    n_zones = n_rotated = total = disagree = wrapped = 0
    null_total = null_disagree = 0
    for name in names:
        files = [f for f in os.listdir(paths.DATA_BZE) if f.upper() == name.upper() + ".BZE"]
        if not files:
            continue
        sec = sections(os.path.join(paths.DATA_BZE, files[0]), os.path.join(paths.PROJECT_DIR, "extracted"))
        if 1 not in sec:
            continue
        for z in loadscript.export_level(loadscript.parse(sec[1])[0])["zones"]:
            if not (zones.kind_of(z) or zones.hurts(z)):
                continue
            shape = zones.shape_of(z)
            if shape is None:
                continue
            n_zones += 1
            game, mine = game_test(z), shape_test(shape)
            ex, y_limit, ez, _radius = z["size"]
            r = max(ex, ez) * 1.6
            ox, oy, oz = z["origin"]
            points = [(int(ox + rng.uniform(-r, r)), int(oy + rng.uniform(y_limit - 300, 300)),
                       int(oz + rng.uniform(-r, r))) for _ in range(SAMPLES)]
            near = [p for p in points if all(abs(p[k] - z["origin"][k]) <= 32767 for k in range(3))]
            wrapped += len(points) - len(near)
            points = near
            wrong = sum(game(p) != mine(p) for p in points)
            total += len(points)
            disagree += wrong
            if shape.m is not None:
                n_rotated += 1
                flat = shape_test(zones.ZoneShape(dict(z, flags=[zones.NO_ROTATION, 0])))
                null_total += len(points)
                null_disagree += sum(game(p) != flat(p) for p in points)
                print(f"{name}: rotated zone {z['rotation']}: {wrong} of {len(points)} points disagree")
    rate = disagree / total if total else 0.0
    print(f"{n_zones} zones that kill, teleport or hurt, {n_rotated} rotated: "
          f"{disagree} of {total} points disagree ({100 * rate:.4f}%); {wrapped} points beyond "
          f"the 16-bit range left out")
    if null_total:
        print(f"null, rotation ignored on the rotated ones: {100 * null_disagree / null_total:.2f}% disagree")
    ok = rate <= 0.0001
    print("all consistent" if ok else "TOO MANY DIFFERENCES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
