"""The overlays (the flags Invisible walls, No collision, Collision boxes,
Death and damage zones, Teleport zones and the heightmap's) change nothing else.

    .venv/Scripts/python checks/check_walls.py [L03A ...]
    .venv/Scripts/python checks/check_walls.py --one-at-a-time   (no workers)

Exits with 1 if a level does not build, too. For each level: builds it
normally and without overlays (walls removed when
reading the terrain, no face judged to be without collision). Every group
that is not an overlay must have the same bytes, and bounds, terrain bounds
(the initial camera) and triangle count must stay the same. Then it counts
the drawn walls: on the menu levels the first probe found 1527 of them.
Exits with 1 if anything differs.

The levels are independent, so they go one per worker process (as many as
the machine has processors, at most 8: more of them only fight over the
disc). The answers are put back in the order of the names, so the lines
printed and every number are the same as one at a time; `--one-at-a-time`
brings the old way back, to check exactly that.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import montage  # noqa: E402
from game import zones  # noqa: E402
from support import paths  # noqa: E402
from game import textures as texmod  # noqa: E402
import viewer  # noqa: E402

original = geo.read_terrain
original_judge = collision.no_collision_kind
collision_box = montage.collision_box
original_kind_of = zones.kind_of
original_hurts = zones.hurts
# the zone overlay asks zones.py these four (finding 326): all of them have to
# be silenced, or the bare level still gets its zone boxes and arrows
original_zone_readers = (zones.kills, zones.destinations, zones.level_changes)
originals = (collision.surfaces, collision.hard_walls, collision.volumes, collision.area_walls, collision.jump_ceilings,
             collision.step_walls)
OVERLAYS = tuple(viewer.OVERLAYS)


def terrain_without_walls(sec4, offset, invisible_walls=None, portal_areas=None):
    return original(sec4, offset)


def fingerprint(built_level):
    groups_by_key = {k: (g.data.tobytes(), [b.tobytes() for b in g.frames])
              for k, g in built_level.face_groups.items() if g.category not in OVERLAYS}
    return groups_by_key, built_level.lo, built_level.hi, built_level.terrain_lo, built_level.terrain_hi, built_level.stat["triangles"]


COUNTERS = ("no_collision", "collision_boxes", "death_zones", "teleport_zones",
            "invisible_walls", "invisible_ground", "pixel", "walls_drawn")


def one_level(entry_name):
    """Builds a level twice and says how it went: (name, ok, why it broke,
    counters). Everything this touches is inside this call, so it can run in
    a process of its own."""
    file_path = os.path.join(paths.DATA_BZE, entry_name + ".bze")
    if not os.path.exists(file_path):
        return None
    table = texmod.construct(paths.DATA_BZE, entry_name, "extracted")
    try:
        geo.read_terrain = original
        full = viewer.Level(file_path, "extracted", table, None, {})
        geo.read_terrain = terrain_without_walls
        collision.no_collision_kind = lambda *a: None
        montage.collision_box = lambda *a, **k: None
        zones.kind_of = lambda z: None
        zones.hurts = lambda z: False
        zones.kills = lambda z: False
        zones.destinations = lambda z: []
        zones.level_changes = lambda z: []
        collision.surfaces = lambda *a: ([], [], [])
        collision.hard_walls = lambda *a: []
        collision.volumes = lambda *a: []
        collision.area_walls = lambda *a: []
        collision.jump_ceilings = lambda *a: []
        collision.step_walls = lambda *a: []
        bare = viewer.Level(file_path, "extracted", table, None, {})
    except Exception as e:  # noqa: BLE001
        return (entry_name, False, f"{entry_name} ({type(e).__name__})", {})
    finally:
        geo.read_terrain = original
        collision.no_collision_kind = original_judge
        montage.collision_box = collision_box
        zones.kind_of = original_kind_of
        zones.hurts = original_hurts
        zones.kills, zones.destinations, zones.level_changes = original_zone_readers
        (collision.surfaces, collision.hard_walls, collision.volumes, collision.area_walls,
         collision.jump_ceilings, collision.step_walls) = originals
    n = full.stat.get("walls_drawn", 0)
    has_wall_group = any(g.category == "faces_1000" for g in full.face_groups.values())
    ok = (fingerprint(full) == fingerprint(bare) and has_wall_group == (n > 0)
          and not any(g.category in OVERLAYS for g in bare.face_groups.values()))
    return (entry_name, ok, None, {k: full.stat.get(k, 0) for k in COUNTERS})


def main():
    name_list = [a for a in sys.argv[1:] if not a.startswith("--")]
    one_at_a_time = "--one-at-a-time" in sys.argv
    name_list = name_list or sorted({v[1] for v in levels.all_entries()})
    if one_at_a_time or len(name_list) < 2:
        answers = [one_level(entry_name) for entry_name in name_list]
    else:
        import concurrent.futures
        workers = max(1, min(8, (os.cpu_count() or 2)))
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            # in the order of the names, whatever order they come back in:
            # the lines printed must not depend on the machine
            answers = list(pool.map(one_level, name_list))
    n_identical, different_levels, walls_total, levels_with_walls, broken = 0, [], 0, 0, []
    totals = dict.fromkeys(COUNTERS, 0)
    for answer in answers:
        if answer is None:
            continue
        entry_name, ok, why, counters = answer
        if why:
            broken.append(why)
            continue
        for k, v in counters.items():
            totals[k] += v
        walls_total += counters["walls_drawn"]
        levels_with_walls += counters["walls_drawn"] > 0
        if ok:
            n_identical += 1
        else:
            different_levels.append(entry_name)
            print(f"DIFFERENT: {entry_name}")
    n_no_collision, box = totals["no_collision"], totals["collision_boxes"]
    zm, pm = totals["death_zones"], totals["teleport_zones"]
    mf, ti, px = totals["invisible_walls"], totals["invisible_ground"], totals["pixel"]
    print(f"{n_identical} levels with everything else identical, {len(different_levels)} different")
    print(f"drawn walls: {walls_total} in {levels_with_walls} levels; faces without collision: {n_no_collision}; "
          f"collision boxes: {box}; death and damage zones: {zm}; teleport zones: {pm}")
    print(f"invisible wall panels: {mf}; invisible ground rectangles: {ti}; pixels: {px}")
    print(f"not buildable: {', '.join(broken) or 'none'}")
    # a level that does not build at all is a failure too: before, it was only
    # printed and the check still passed
    return 1 if different_levels or broken else 0


if __name__ == "__main__":
    sys.exit(main())
