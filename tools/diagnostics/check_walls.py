"""The overlays (the flags Invisible walls, No collision, Collision boxes,
Death and damage zones, Teleport zones and the heightmap's) change nothing else.

    .venv/Scripts/python tools/diagnostics/check_walls.py [L03A ...]

For each level: builds it normally and without overlays (walls removed when
reading the terrain, no face judged to be without collision). Every group
that is not an overlay must have the same bytes, and bounds, terrain bounds
(the initial camera) and triangle count must stay the same. Then it counts
the drawn walls: on the menu levels the first probe found 1527 of them.
Exits with 1 if anything differs.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import collision  # noqa: E402
import export_obj as geo  # noqa: E402
import levels  # noqa: E402
import montage  # noqa: E402
import zones  # noqa: E402
import paths  # noqa: E402
import textures as texmod  # noqa: E402
import viewer  # noqa: E402

original = geo.read_terrain
original_judge = collision.no_collision_kind
collision_box = montage.collision_box
original_kind_of = zones.kind_of
original_hurts = zones.hurts
originals = (collision.surfaces, collision.hard_walls, collision.volumes, collision.area_walls, collision.jump_ceilings,
             collision.step_walls)
OVERLAYS = tuple(viewer.OVERLAYS)


def terrain_without_walls(sec4, offset, invisible_walls=None):
    return original(sec4, offset)


def fingerprint(built_level):
    groups_by_key = {k: (g.data.tobytes(), [b.tobytes() for b in g.frames])
              for k, g in built_level.face_groups.items() if g.category not in OVERLAYS}
    return groups_by_key, built_level.lo, built_level.hi, built_level.terrain_lo, built_level.terrain_hi, built_level.stat["triangles"]


name_list = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
n_identical, different_levels, walls_total, levels_with_walls, broken, n_no_collision, box, zm, pm = 0, [], 0, 0, [], 0, 0, 0, 0
mf = ti = px = 0
for entry_name in name_list:
    file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
    if not os.path.exists(file_path):
        continue
    table = texmod.construct(paths.DATA_BZE, entry_name, "extracted")
    try:
        geo.read_terrain = original
        full = viewer.Level(file_path, "extracted", table, None, {})
        geo.read_terrain = terrain_without_walls
        collision.no_collision_kind = lambda *a: None
        montage.collision_box = lambda *a, **k: None
        zones.kind_of = lambda z: None
        zones.hurts = lambda z: False
        collision.surfaces = lambda *a: ([], [], [])
        collision.hard_walls = lambda *a: []
        collision.volumes = lambda *a: []
        collision.area_walls = lambda *a: []
        collision.jump_ceilings = lambda *a: []
        collision.step_walls = lambda *a: []
        bare = viewer.Level(file_path, "extracted", table, None, {})
    except Exception as e:  # noqa: BLE001
        broken.append(f"{entry_name} ({type(e).__name__})")
        continue
    finally:
        geo.read_terrain = original
        collision.no_collision_kind = original_judge
        montage.collision_box = collision_box
        zones.kind_of = original_kind_of
        zones.hurts = original_hurts
        (collision.surfaces, collision.hard_walls, collision.volumes, collision.area_walls,
         collision.jump_ceilings, collision.step_walls) = originals
    n = full.stat.get("walls_drawn", 0)
    walls_total += n
    levels_with_walls += n > 0
    has_wall_group = any(g.category == "faces_1000" for g in full.face_groups.values())
    ok = (fingerprint(full) == fingerprint(bare) and has_wall_group == (n > 0)
          and not any(g.category in OVERLAYS for g in bare.face_groups.values()))
    n_no_collision += full.stat.get("no_collision", 0)
    box += full.stat.get("collision_boxes", 0)
    zm += full.stat.get("death_zones", 0)
    pm += full.stat.get("teleport_zones", 0)
    mf += full.stat.get("invisible_walls", 0)
    ti += full.stat.get("invisible_ground", 0)
    px += full.stat.get("pixel", 0)
    if ok:
        n_identical += 1
    else:
        different_levels.append(entry_name)
        print(f"DIFFERENT: {entry_name}")
print(f"{n_identical} levels with everything else identical, {len(different_levels)} different")
print(f"drawn walls: {walls_total} in {levels_with_walls} levels; faces without collision: {n_no_collision}; "
      f"collision boxes: {box}; death and damage zones: {zm}; teleport zones: {pm}")
print(f"invisible wall panels: {mf}; invisible ground rectangles: {ti}; pixels: {px}")
print(f"not buildable: {', '.join(broken) or 'none'}")
sys.exit(1 if different_levels else 0)
