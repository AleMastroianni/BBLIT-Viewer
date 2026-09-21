"""The safety net: every check that can fail, in one run, with a summary;
then a fixed set of viewer photos compared byte for byte with a reference.

    .venv/Scripts/python checks/run_checks.py
    .venv/Scripts/python checks/run_checks.py --only test_menu,check_zones
    .venv/Scripts/python checks/run_checks.py --no-photos
    .venv/Scripts/python checks/run_checks.py --photos-only
    .venv/Scripts/python checks/run_checks.py --photos-only --photo L03A_plain
    .venv/Scripts/python checks/run_checks.py --make-baseline

Each check runs as its own process, as it would by hand, and counts as
passed only if it exits with 0. Its whole output goes to
`reference/baseline/logs/<check>.log`; a failed one also prints its last lines.

The photos (PHOTOS below: some levels and cameras, `--tick 0`, the flags and
the wireframe on and off, a few menu pages) are taken with the viewer's
`--screenshot`, one at a time, and must have the same bytes as those in
`reference/baseline/` (git-ignored: they are made from the game's data).
A photo that differs is kept next to it as `<name>.new.png`, with the count
of pixels that changed. `--make-baseline` writes the reference: only when
the current state has been checked by eye and approved.

Exits with 1 if a check fails, a photo differs or a reference photo is
missing.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKS_DIR = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(PROJECT, "bblit", "viewer.py")
BASELINE = os.path.join(PROJECT, "reference", "baseline")
LOGS = os.path.join(BASELINE, "logs")

# the checks that test something and can fail, in the order they run (the
# fast ones first). Not here: census.py and inventory_placement.py (counts,
# nothing to pass), the old diag_* scripts (one-off measures).
CHECKS = [
    "check_levels",
    "check_official_names",
    "check_section_cache",
    "check_zones",
    "check_teleports",
    "check_uv_rules",
    "check_texture_gamma",
    "check_blend_modes",
    "check_area_visibility",
    "check_hazards",
    "check_movers",
    "check_part_meshes",
    "check_ground_snap",
    "check_gates",
    "check_sky",
    "check_collision",
    "check_ground_below",
    "check_tim",
    "check_bze",
    "test_menu",
    "test_level_change",
    "check_level_cache",
    "check_cache_warmer",
    "check_walls",
]

# (name, viewer arguments): all with --tick 0, or the animations change the bytes
PHOTOS = [
    ("L03A_plain", ["L03A"]),
    ("L03A_all_flags", ["L03A", "--invisible-walls", "--nocollision", "--boxes", "--deathzones",
                        "--teleportzones", "--ground", "--hardwalls", "--areaboxes", "--faces1000"]),
    ("L03A_skeleton", ["L03A", "--wireframe", "1"]),
    ("L03A_grid", ["L03A", "--wireframe", "2"]),
    ("L03A_clones_psx", ["L03A", "--clones", "2", "--albedo", "2"]),
    ("L03A_walls_close", ["L03A", "--camera", "268,12,-130,160,-15", "--invisible-walls", "--hardwalls"]),
    ("L01B_no_collision", ["L01B", "--camera", "116,40,-45,-90,-50", "--nocollision"]),
    ("L01D2_death_hole", ["L01D2", "--camera", "142,120,60,-90,-55", "--deathzones"]),
    ("L04A2_teleport", ["L04A2", "--camera", "64,133,-25,180,-45", "--teleportzones", "--deathzones"]),
    ("L01B_level_change", ["L01B", "--camera", "182.1,19.1,3.8,-90,-39", "--teleportzones", "--deathzones"]),
    ("L01A_teleport_arrows", ["L01A", "--camera", "132.7,176.0,102.5,-90,-39", "--teleportzones", "--deathzones"]),
    ("L03A_teleport_arrow", ["L03A", "--camera", "172.8,113.0,26.1,-90,-39", "--teleportzones", "--deathzones"]),
    ("L03D1_heightmap", ["L03D1", "--ground", "--hardwalls", "--areaboxes"]),
    ("L03D1_area_inside", ["L03D1", "--camera", "90,24,-24,-20,12", "--areaboxes"]),
    ("L03D1_area_no_outside", ["L03D1", "--areaboxes", "--no-walls-outside"]),
    ("L03D1_lava_names", ["L03D1", "--camera", "33.6,19.5,-2.3,-90,-35", "--deathzones"]),
    ("L04E_step_walls", ["L04E", "--camera", "168,54,-97.3,0,-8", "--invisible-walls"]),
    ("LS01_step_both_sides", ["LS01", "--camera", "64.38,153,-142.5,-90,-68", "--invisible-walls"]),
    ("L05A1_hole_steps", ["L05A1", "--invisible-walls", "--hole-steps"]),
    ("L02A4_boxes_zones", ["L02A4", "--boxes", "--deathzones"]),
    ("L03A_box_kinds", ["L03A", "--camera", "158,40,-112,-60,-60", "--boxes"]),
    # the gates: the default (open), the state the game starts them in, and
    # the lines from the switches (findings 323, 331)
    ("L03D1_gates_open", ["L03D1", "--camera", "152,20,-22,-72,-27", "--boxes"]),
    ("L03D1_gates_game", ["L03D1", "--camera", "152,20,-22,-72,-27", "--boxes", "--gates", "game"]),
    ("L03D1_gate_links", ["L03D1", "--camera", "152,20,-22,-72,-27", "--boxes",
                          "--gatelinks", "gates", "--gates", "game"]),
    ("L03D1_all_links", ["L03D1", "--camera", "152,20,-22,-72,-27", "--boxes",
                         "--gatelinks", "all", "--gates", "game"]),
    ("LS01_plain", ["LS01"]),
    ("LS01_area_visibility", ["LS01", "--sky", "--area-visibility"]),
    ("LS01_all_islands", ["LS01", "--sky"]),
    ("LS01_portals", ["LS01", "--faces1000"]),
    ("L05A5_plain", ["L05A5", "--sky"]),
    ("L03A_fov_pc", ["L03A", "--fov", "51"]),
    ("L03A_uv_amd", ["L03A", "--camera", "158,40,-112,-60,-60", "--uv-rule", "pc_amd"]),
    ("L03A_uv_psx", ["L03A", "--camera", "158,40,-112,-60,-60", "--uv-rule", "psx"]),
    ("L03A_uv_pc", ["L03A", "--camera", "158,40,-112,-60,-60", "--uv-rule", "pc"]),
    ("menu_main_empty", []),
    ("menu_flags", ["L03A", "--menu", "flags"]),
    ("menu_load_it", ["L03A", "--menu", "load", "--language", "it"]),
    ("menu_video", ["L03A", "--menu", "video"]),
]


def run_checks(names):
    os.makedirs(LOGS, exist_ok=True)
    results = []
    for name in names:
        start = time.time()
        proc = subprocess.run([sys.executable, os.path.join(CHECKS_DIR, name + ".py")], cwd=PROJECT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.stdout.decode("utf-8", "replace").replace("\r\n", "\n")
        with open(os.path.join(LOGS, name + ".log"), "w", encoding="utf-8") as f:
            f.write(output)
        lines = [ln for ln in output.splitlines() if ln.strip()]
        last = lines[-1] if lines else "(no output)"
        ok = proc.returncode == 0
        results.append((name, ok))
        print(f"{'OK  ' if ok else 'FAIL'} {name:22s} {time.time() - start:6.1f} s   {last[:90]}", flush=True)
        if not ok:
            for ln in lines[-12:]:
                print(f"       | {ln[:150]}")
    return results


def _pixels_changed(a, b):
    try:
        from PIL import Image
    except ImportError:
        return None
    # RGBA: a blended overlay can change only the alpha the photo keeps
    ia, ib = Image.open(a).convert("RGBA"), Image.open(b).convert("RGBA")
    if ia.size != ib.size:
        return ia.size[0] * ia.size[1]
    da, db = ia.tobytes(), ib.tobytes()
    return sum(1 for i in range(0, len(da), 4) if da[i:i + 4] != db[i:i + 4])


def take_photos(make_baseline, wanted=None):
    os.makedirs(BASELINE, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="bblit_photos_") as tmp:
        for name, args in PHOTOS:
            if wanted and name not in wanted:
                continue
            start = time.time()
            shot = os.path.join(tmp, name + ".png")
            proc = subprocess.run([sys.executable, VIEWER] + args
                                  + ["--tick", "0", "--screenshot", shot], cwd=PROJECT,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            reference = os.path.join(BASELINE, name + ".png")
            new_copy = os.path.join(BASELINE, name + ".new.png")
            if proc.returncode != 0 or not os.path.exists(shot):
                results.append((name, False))
                print(f"FAIL photo {name:20s} the viewer did not write it (exit {proc.returncode})")
                for ln in proc.stdout.decode("utf-8", "replace").splitlines()[-8:]:
                    print(f"       | {ln[:150]}")
                continue
            if make_baseline:
                shutil.copyfile(shot, reference)
                if os.path.exists(new_copy):
                    os.remove(new_copy)
                results.append((name, True))
                print(f"SAVED photo {name:20s} {time.time() - start:5.1f} s")
                continue
            if not os.path.exists(reference):
                results.append((name, False))
                shutil.copyfile(shot, new_copy)
                print(f"FAIL photo {name:20s} no reference photo (run with --make-baseline)")
                continue
            with open(shot, "rb") as f1, open(reference, "rb") as f2:
                same = f1.read() == f2.read()
            results.append((name, same))
            if same:
                if os.path.exists(new_copy):
                    os.remove(new_copy)
                print(f"OK   photo {name:20s} {time.time() - start:5.1f} s   identical")
            else:
                shutil.copyfile(shot, new_copy)
                changed = _pixels_changed(reference, shot)
                print(f"FAIL photo {name:20s} {time.time() - start:5.1f} s   differs"
                      + (f": {changed} pixels changed" if changed is not None else "")
                      + f" (kept as {name}.new.png)")
    return results


def main():
    p = argparse.ArgumentParser(description="all the checks and the reference photos")
    p.add_argument("--only", help="comma-separated check names (no photos unless --photos)")
    p.add_argument("--no-photos", action="store_true")
    p.add_argument("--photos", action="store_true", help="with --only: take the photos too")
    p.add_argument("--photos-only", action="store_true")
    p.add_argument("--photo", help="comma-separated photo names, for these only (also with --make-baseline)")
    p.add_argument("--make-baseline", action="store_true",
                   help="write the photos as the new reference (after checking them by eye)")
    args = p.parse_args()

    start = time.time()
    checks, photos = [], []
    if not (args.photos_only or args.make_baseline):
        names = CHECKS
        if args.only:
            names = [n.strip() for n in args.only.split(",") if n.strip()]
            unknown = [n for n in names if n not in CHECKS]
            if unknown:
                p.error(f"unknown checks: {', '.join(unknown)}")
        checks = run_checks(names)
    if args.make_baseline or args.photos_only or not (args.no_photos or (args.only and not args.photos)):
        wanted = [n.strip() for n in args.photo.split(",") if n.strip()] if args.photo else None
        if wanted:
            unknown = [n for n in wanted if n not in {name for name, _a in PHOTOS}]
            if unknown:
                p.error(f"unknown photos: {', '.join(unknown)}")
        photos = take_photos(args.make_baseline, wanted)

    failed = [n for n, ok in checks + photos if not ok]
    print()
    print(f"checks: {sum(ok for _, ok in checks)}/{len(checks)} passed; "
          f"photos: {sum(ok for _, ok in photos)}/{len(photos)} "
          f"{'saved' if args.make_baseline else 'identical'}; {time.time() - start:.0f} s")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
