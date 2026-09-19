"""The collision heightmap reader (tools/collision.py) against two things
that share nothing with it.

    .venv/Scripts/python tools/diagnostics/check_collision.py [L03A ...]

1. The record shape (finding 110): cells x 320 == extent on both axes, in
   every record.
2. The visible terrain (finding 112): at the centre of every upward-facing
   terrain face (game coordinates: vertex + block offset), the heightmap
   height must be close to the face's height. It is compared against the
   null hypothesis of a random cell of the same block: the correct reading
   must win by a wide margin (Ombelll: median 4 units vs 15).

Exits with 1 if the shape does not match or if the reading does not beat
the null hypothesis.
"""
import os
import random
import statistics
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import collision  # noqa: E402
import export_obj as geo  # noqa: E402
import levels  # noqa: E402
import loadscript  # noqa: E402
import paths  # noqa: E402
from viewer import sections  # noqa: E402


def upward_face_center(vertices, vl, shift):
    """The centre of the face in game coordinates, if it faces upward
    (in the game Y grows downward)."""
    p = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners[:3]]
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    if ln == 0 or abs(n[1]) / ln < 0.7:
        return None
    q = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners]
    return tuple(sum(c[k] for c in q) / len(q) for k in range(3))


rnd = random.Random(1)
name_list = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
record = shape_ok = 0
diff, null_diffs = [], []
n_outside_block = n_without_ground = 0
for entry_name in name_list:
    file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
    if not os.path.exists(file_path):
        continue
    sec = sections(file_path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    try:
        grid_blocks = collision.read_level_blocks(sec[4], lvl)
    except Exception as e:  # noqa: BLE001
        print(f"{entry_name}: heightmap unreadable ({type(e).__name__})")
        continue
    for b in grid_blocks:
        record += 1
        shape_ok += b.width_units * collision.CELL_UNITS == b.ext_x and b.height_units * collision.CELL_UNITS == b.ext_z
    for t in lvl["terrain"]:
        try:
            vertices, faces, _ = geo.read_terrain(sec[4], t["offset"])
        except Exception:  # noqa: BLE001
            continue
        for vl in faces[::7]:     # a sample, for speed
            c = upward_face_center(vertices, vl, t["translation"])
            if c is None:
                continue
            x, y, z = c
            inside = [b for b in grid_blocks if b.ground_height(x, z) is not None]
            if not any(0 <= x - b.ox < b.ext_x and 0 <= z - b.oz < b.ext_z for b in grid_blocks):
                n_outside_block += 1
                continue
            if not inside:
                n_without_ground += 1
                continue
            d = min(abs(b.ground_height(x, z) - y) for b in inside)
            diff.append(d)
            b = rnd.choice(inside)
            for _ in range(20):     # a random cell of the same block, with terrain
                rx = b.ox + rnd.random() * b.ext_x
                rz = b.oz + rnd.random() * b.ext_z
                g = b.ground_height(rx, rz)
                if g is not None:
                    null_diffs.append(abs(g - y))
                    break
print(f"record shape: {shape_ok} of {record} with cells x 320 == extent")
print(f"upward faces sampled: {len(diff)} above collision terrain, "
      f"{n_without_ground} above sub-cells without terrain, {n_outside_block} outside every block")
if diff and null_diffs:
    m, mn = statistics.median(diff), statistics.median(null_diffs)
    print(f"median face-heightmap difference: {m:.1f} units, null hypothesis (random cell): {mn:.1f}")
    ok = shape_ok == record and m * 3 < mn
else:
    ok = False
sys.exit(0 if ok else 1)
