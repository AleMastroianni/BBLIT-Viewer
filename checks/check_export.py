"""Level options -> Export (bblit/support/export.py), measured on a few
levels, into a temporary folder:

1. every texture slot gives a PNG, and each PNG read back has the size
   and the exact bytes `tim.read_tim` decodes from the disc;
2. `collision.obj` has as many squares as the heightmap has sub-cells
   with ground, counted another way: the game's own ground query
   (`HeightmapBlock.ground_height`) at the centre of every sub-cell of
   every block. A copy of the file with one square fewer must fail;
3. `level.obj`: the group "Bugs" is there, no group of a cloned template,
   every image the MTL files name is in the folder;
4. the sky's textures are the ones `sky.obj` draws, and `sky_textures\\`
   holds exactly those.

    .venv/Scripts/python checks/check_export.py [L03A MERLIN ...]

Exits with 1 if anything differs.
"""
import os
import re
import sys
import tempfile
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from PIL import Image  # noqa: E402
from game import collision  # noqa: E402
from game import textures as texmod  # noqa: E402
from game import tim  # noqa: E402
from support import export  # noqa: E402
from support import paths  # noqa: E402

LEVELS = sys.argv[1:] or ["L03A", "MERLIN", "LS01", "L05A1"]
CACHE = os.path.join(PROJECT_DIR, "extracted")
failures = []


def fail(text):
    failures.append(text)
    print("FAIL", text)


def squares_by_query(grid_blocks) -> int:
    """Sub-cells with ground by the game's ground query, not by the tiles'
    bytes: an independent count."""
    n = 0
    for b in grid_blocks:
        for sz in range(0, b.ext_z, collision.SUBCELL):
            for sx in range(0, b.ext_x, collision.SUBCELL):
                if b.ground_height(b.ox + sx + collision.SUBCELL / 2, b.oz + sz + collision.SUBCELL / 2) \
                        is not None:
                    n += 1
    return n


def faces_in(path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.startswith("f "))


folder = paths.find_levels_folder()
if folder is None:
    print("no levels folder")
    sys.exit(1)
files = {os.path.splitext(f)[0].upper(): os.path.join(folder, f) for f in os.listdir(folder)
         if f.lower().endswith(".bze")}
with tempfile.TemporaryDirectory() as root:
    for code in LEVELS:
        start = time.time()
        file_path = files[code.upper()]
        summary = export.export_3d(file_path, CACHE, root)
        out = export.level_folder(file_path, root)
        table = texmod.construct(folder, code, CACHE)

        # 1. one PNG per slot, the disc's bytes
        pngs = {f for f in os.listdir(out) if re.fullmatch(r"t\d+\.png", f)}
        decoded = same = 0
        for tex_id, (data, offset) in table.slots.items():
            try:
                w, h, rgba = tim.read_tim(data, offset)
            except Exception:  # noqa: BLE001
                continue
            decoded += 1
            name = f"t{tex_id}.png"
            if name not in pngs:
                fail(f"{code}: {name} missing")
                continue
            img = Image.open(os.path.join(out, name)).convert("RGBA")
            if img.size == (w, h) and img.tobytes() == bytes(rgba):
                same += 1
            else:
                fail(f"{code}: {name} differs from the disc")
        if len(pngs) != decoded:
            fail(f"{code}: {len(pngs)} PNG for {decoded} slots")

        # 2. the collision squares, and a null that must fail
        level, _captured = export.game_start(file_path, CACHE, table)
        expected = squares_by_query(level.collision_blocks)
        written = faces_in(os.path.join(out, "collision.obj"))
        if written != expected:
            fail(f"{code}: collision.obj {written} squares, the heightmap {expected}")
        with open(os.path.join(out, "collision.obj"), encoding="utf-8") as f:
            lines = f.readlines()
        last = max(i for i, line in enumerate(lines) if line.startswith("f "))
        null = os.path.join(root, "null.obj")
        with open(null, "w", encoding="utf-8") as f:
            f.writelines(lines[:last] + lines[last + 1:])
        if faces_in(null) == expected:
            fail(f"{code}: the null (one square fewer) passed")

        # 3. level.obj: Bugs, no clones, every image named is there
        with open(os.path.join(out, "level.obj"), encoding="utf-8") as f:
            groups = [line[2:].strip() for line in f if line.startswith("g ")]
        if "Bugs" not in groups:
            fail(f"{code}: no group Bugs")
        if any(g.startswith("clone") for g in groups):
            fail(f"{code}: a cloned template in level.obj")
        for mtl in ("level.mtl", "sky.mtl"):
            path = os.path.join(out, mtl)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as f:
                named = {line.split(None, 1)[1].strip() for line in f if line.startswith(("map_Kd", "map_d"))}
            for image in named:
                if not os.path.exists(os.path.join(out, image)):
                    fail(f"{code}: {mtl} names {image}, not in the folder")

        # 4. the sky's textures
        sky_ids = set()
        if os.path.exists(os.path.join(out, "sky.mtl")):
            with open(os.path.join(out, "sky.mtl"), encoding="utf-8") as f:
                sky_ids = {int(m.group(1)) for line in f if (m := re.match(r"map_Kd t(\d+)\.png", line))}
        sky_dir = os.path.join(out, "sky_textures")
        in_dir = {int(f[1:-4]) for f in os.listdir(sky_dir)} if os.path.isdir(sky_dir) else set()
        if sky_ids != in_dir:
            fail(f"{code}: sky.obj draws {sorted(sky_ids)}, sky_textures has {sorted(in_dir)}")

        print(f"OK   {code}: {same}/{decoded} PNG identical to the disc, {written} collision squares "
              f"= {expected} by the ground query, {len(groups)} groups with Bugs, "
              f"{len(sky_ids)} sky textures, {time.time() - start:.1f} s")


# 5-10. the limit cases, in a folder of their own with a cache of their own
# (a broken level must not touch the viewer's cache)
import ctypes  # noqa: E402
import errno  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    cache = os.path.join(tmp, "cache")
    source = os.path.join(tmp, "levels")
    os.makedirs(source)
    for code in ("L03A", "MERLIN", "CC3A", "L_PDOCK_0", "SCREEN1"):
        shutil.copy2(files[code], source)
    with open(os.path.join(source, "L05A1.bze"), "wb") as f:
        f.write(b"\x01\x00\x00\x00" + bytes(996))          # a level that does not read
    root = os.path.join(tmp, "Export")
    stray = os.path.join(root, export.WHOLE_GAME, "unique", "16x16_deadbeef.png")
    os.makedirs(os.path.dirname(stray))
    open(stray, "wb").close()
    dock = export.level_folder(files["L03A"], root)
    os.makedirs(dock)
    for name in ("t9999.png", "my_notes.txt"):
        open(os.path.join(dock, name), "wb").close()
    progress = os.path.join(tmp, "progress.json")

    # 5. the whole disc on a small folder
    r = export.whole_disc(source, cache, None, root, progress)
    with open(os.path.join(root, export.WHOLE_GAME, "info.txt"), encoding="utf-8") as f:
        info = f.read()
    expected = {"level": 2, "extra": 1, "loading": 2}
    if r["done"] != expected:
        fail(f"whole disc: {r['done']}, expected {expected}")
    if [c for _k, c, _w in r["unreadable"]] != ["L05A1"] or len(r["missing"]["level"]) != 49 \
            or len(r["missing"]["extra"]) != 26:
        fail(f"whole disc: unreadable {r['unreadable']}, missing {[len(v) for v in r['missing'].values()]}")
    for words in ("Levels: 2 of 52 exported.", "Unreadable: L05A1", "Missing from the folder:",
                  "Screen1 (10 pixels)", "_4 Italian", "Exporting again replaces"):
        if words not in info:
            fail(f"whole disc: info.txt without '{words}'")
    if os.path.exists(stray) or os.path.exists(os.path.join(dock, "t9999.png")):
        fail("whole disc: a file of an older export is still there")
    if not os.path.exists(os.path.join(dock, "my_notes.txt")):
        fail("whole disc: a file the export does not write was deleted")
    if not os.path.exists(os.path.join(root, export.LOADING, "L_Pdock", "L_Pdock_0.png")) \
            or not os.path.exists(os.path.join(root, export.LOADING, "Other", "Screen1.png")):
        fail("whole disc: a loading screen not where it belongs")
    state = json.load(open(progress, encoding="utf-8"))
    if state["state"] != "done" or state["missing"] != {"level": 49, "extra": 26}:
        fail(f"whole disc: the progress says {state}")
    if not any(f.startswith("whole disc") for f in failures):
        print(f"OK   whole disc on a small folder: {r['done']}, 1 unreadable, 49 + 26 missing, "
              f"older files gone, the user's file kept, info.txt complete")

    # 6. a file another program holds open: skipped and said
    obj = os.path.join(dock, "level.obj")
    export.export_3d(files["L03A"], cache, root)
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateFileW.restype = ctypes.c_void_p
    handle = kernel32.CreateFileW(obj, 0x80000000, 0, None, 3, 0x80, None)   # read, no sharing
    try:
        job = export.Job()
        export.export_3d(files["L03A"], cache, root, job=job)
    finally:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
    if [os.path.basename(p) for p in job.skipped] != ["level.obj"] \
            or not os.path.exists(os.path.join(dock, "collision.obj")):
        fail(f"file held open: skipped {job.skipped}")
    else:
        print("OK   level.obj held open by another program: skipped and named, the rest written")

    # 7. disk full, a folder that cannot be written, a path too long
    if export.classify(OSError(errno.ENOSPC, "No space left on device"))[0] != "disk_full":
        fail("a full disk is not recognised")
    blocker = os.path.join(tmp, "a file")
    open(blocker, "wb").close()
    for label, bad_root in (("a file where the folder should be", os.path.join(blocker, "Export")),
                            ("a path too long", os.path.join(tmp, *["x" * 60] * 5, "Export"))):
        export.run("3d", files["L03A"], cache, os.getpid(), root=bad_root)
        state = export.read_progress(export.progress_path(cache, os.getpid()))
        written = state.get("state") == "done" and os.path.exists(os.path.join(state["folder"], "level.obj"))
        if state.get("state") == "failed" and state.get("error") == "not_writable":
            print(f"OK   {label}: 'cannot write in ...{state['where'][-40:]}'")
        elif label == "a path too long" and written:
            # Windows with long paths turned on writes it: also right
            print(f"OK   {label}: written ({len(state['folder'])} characters; long paths are on here)")
        else:
            fail(f"{label}: {state}")

    # 8. two windows: a live export of another window stops this one; a dead one does not
    lock = os.path.join(root, export.LOCK)
    with open(lock, "w") as f:
        json.dump({"pid": os.getpid(), "viewer": 1}, f)
    export.run("3d", files["L03A"], cache, os.getpid(), root=root)
    busy = export.read_progress(export.progress_path(cache, os.getpid())).get("state") == "busy"
    with open(lock, "w") as f:
        json.dump({"pid": 999999, "viewer": 1}, f)
    stale = export.running_elsewhere(os.getpid(), root)
    if not busy or stale:
        fail(f"two windows: busy {busy}, a dead lock counted {stale}")
    else:
        print("OK   another window exporting: this one does not start; a lock left by a dead process is ignored")
    os.remove(lock)

    # 9. the longest name, under a folder as long as a user's Documents
    deep = os.path.join(tmp, "Users", "a-rather-long-user-name", "Documents", "BBLIT Viewer", "Export")
    export.export_3d(files["CC4D"], cache, deep)
    longest = max((os.path.join(d, f) for d, _s, fs in os.walk(deep) for f in fs), key=len)
    print(f"OK   the longest name (CC4D): {len(longest)} characters at most, "
          f"{len(longest) - len(tmp)} below the root")

    # 10. a level without a sky: no empty sky.obj, info.txt says so
    export.export_3d(files["L04A1"], cache, root)
    no_sky = export.level_folder(files["L04A1"], root)
    with open(os.path.join(no_sky, "info.txt"), encoding="utf-8") as f:
        said = "no sky.obj" in f.read()
    if os.path.exists(os.path.join(no_sky, "sky.obj")) or not said:
        fail("a level without a sky: sky.obj written or not said")
    else:
        print("OK   The Big Bank Withdrawal 1 has no sky: no sky.obj, info.txt says so")

print()
print("everything as expected" if not failures else f"{len(failures)} failures")
sys.exit(1 if failures else 0)
