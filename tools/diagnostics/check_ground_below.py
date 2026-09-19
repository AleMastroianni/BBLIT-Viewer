"""The game's ground query (collision.block_at, collision.ground_below: the
camera's shadow point) against built cases and against the visible terrain.

    .venv/Scripts/python tools/diagnostics/check_ground_below.py [L03A ...]

1. Built blocks, where the answer is known: the slab bounds (top excluded,
   base included), the area tried first, the fall through a 0x7E sub-cell
   into the block below, a point in the air above every slab, a point
   outside every block.
2. The visible terrain, where slabs are stacked: at the centre of every
   upward-facing terrain face with ground in at least two blocks at that
   spot, a point 64 units above the face falls on the ground of the face's
   own layer. Bar set before the run: within 20 units (the median face to
   heightmap gap is 7, finding 283) in at least 90% of the faces, and at
   least 20 points better than the null hypothesis (the ground of the first
   block with ground there, ignoring height, as a query without the slabs
   would read it).

Exits with 1 if a built case fails or the bar is missed.
"""
import os
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

results = []


def upward_face_center(vertices, vl, shift):
    """The centre of the face in game coordinates, if it faces upward
    (as in check_collision.py, which runs on import)."""
    p = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners[:3]]
    u = [p[1][k] - p[0][k] for k in range(3)]
    v = [p[2][k] - p[0][k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
    if ln == 0 or abs(n[1]) / ln < 0.7:
        return None
    q = [tuple(vertices[h][k] + shift[k] for k in range(3)) for h in vl.corners]
    return tuple(sum(c[k] for c in q) / len(q) for k in range(3))


def probe(label, cond):
    results.append(bool(cond))
    print(("OK   " if cond else "FAIL ") + label)


def block(area, ox, oz, top, base, byte, cells=1, scale=10):
    """A built block: `cells` x `cells` cells of 320 units, every sub-cell
    with the same height byte."""
    b = collision.HeightmapBlock()
    b.area, b.height_scale = area, scale
    b.width_units = b.height_units = cells
    b.ext_x = b.ext_z = cells * collision.CELL_UNITS
    b.ox, b.oz, b.y_floor, b.y_ceiling = ox, oz, base, top
    b.grid = (0,) * (cells * cells)
    b.tiles = bytes([byte & 0xFF]) * 64
    return b


# 1. built cases (Y down: top < base)
upper = block(1, 0, 0, -2000, -1000, 10)          # ground at -1000 - 100 = -1100
lower = block(2, 0, 0, -1000, 0, 5)               # ground at 0 - 50 = -50
hole = block(3, 0, 0, -2000, -1000, 0x7E)         # no ground: fall through
probe("the slab's top is outside, its base inside",
      collision.block_at([upper], 10, -2000, 10) is None
      and collision.block_at([upper], 10, -1000, 10) is upper)
probe("x and z: origin inside, origin + extent outside",
      collision.block_at([upper], 0, -1500, 0) is upper
      and collision.block_at([upper], 320, -1500, 10) is None
      and collision.block_at([upper], 10, -1500, 320) is None)
twin = block(9, 0, 0, -2000, -1000, 20)
probe("the area of the last frame is tried first, then file order",
      collision.block_at([upper, twin], 10, -1500, 10, area=9) is twin
      and collision.block_at([upper, twin], 10, -1500, 10) is upper)
probe("a point in the air falls on the top slab's ground",
      collision.ground_below([upper, lower], 10, -5000, 10) == (-1100, upper))
probe("a point in the lower slab lands on the lower ground",
      collision.ground_below([upper, lower], 10, -500, 10) == (-50, lower))
probe("through a 0x7E sub-cell into the block below",
      collision.ground_below([hole, lower], 10, -5000, 10) == (-50, lower))
probe("inside a slab under its ground: that ground, above the point",
      collision.ground_below([upper], 10, -1050, 10) == (-1100, upper))
probe("outside every block: nothing",
      collision.ground_below([upper, lower], 400, -500, 10) is None
      and collision.ground_below([hole], 10, -5000, 10) is None)

# 2. the visible terrain where slabs are stacked
name_list = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
n = hits = null_hits = 0
for entry_name in name_list:
    file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
    if not os.path.exists(file_path):
        continue
    sec = sections(file_path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    try:
        grid_blocks = collision.read_level_blocks(sec[4], lvl)
    except Exception:  # noqa: BLE001
        continue
    for t in lvl["terrain"]:
        try:
            vertices, faces, _ = geo.read_terrain(sec[4], t["offset"])
        except Exception:  # noqa: BLE001
            continue
        for vl in faces[::3]:
            c = upward_face_center(vertices, vl, t["translation"])
            if c is None:
                continue
            x, y, z = (int(round(w)) for w in c)
            with_ground = [b for b in grid_blocks if b.ground_height(x, z) is not None]
            if len(with_ground) < 2 or not any(abs(b.ground_height(x, z) - y) <= 20 for b in with_ground):
                continue
            n += 1
            landed = collision.ground_below(grid_blocks, x, y - 64, z)
            hits += landed is not None and abs(landed[0] - y) <= 20
            null_hits += abs(with_ground[0].ground_height(x, z) - y) <= 20
print(f"faces over stacked ground: {n}; the fall lands on the face's layer in {hits}, "
      f"the null hypothesis (first block with ground) in {null_hits}")
probe("stacked slabs: the fall finds the face's layer in 90% or more",
      n > 0 and hits >= 0.9 * n and hits - null_hits >= 20)
sys.exit(0 if all(results) else 1)
