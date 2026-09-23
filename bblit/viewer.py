"""Native level viewer for Lost in Time. Reads the .bze files directly.

    .venv/Scripts/python tools/viewer.py L03A
    .venv/Scripts/python tools/viewer.py L03A --screenshot out.png  (one screenshot, then exits)

Controls:
    mouse (right button held)     look
    W A S D                       move, Q/E up and down
    Shift                         faster, Ctrl slower
    wheel                         change base speed
    T                             textures on/off
    F                             wireframe
    O                             props on/off
    P                             stop / restart all animations
    - +                           animation ticks per second
    L                             bilinear filter (like the PC) / sharp texels
    N                             animated textures on/off
    H                             sky dome on/off
    M                             semi-transparent blending on/off
    G                             cloned templates: off / at startup / all
    [ ]                           previous / next level
    R                             back to the starting point
    Esc                           menu (Backspace or M back, arrows and Enter)
    Alt+Enter                     fullscreen

The menu (tools/menu.py, texts in tools/texts.py) follows the layout of the CTR
viewer: Load level, Level options (with Flags), Video options, General
options, Help. Settings persist from one run to the next
(tools/settings.py); entity states and flags chosen from the menu last
only for the session.

There is no intermediate format: the .bze files are decompressed, the load
script read and the geometry built in memory. The decompressed sections go
into an on-disk cache, because decompressing in Python takes a few seconds.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse  # noqa: E402
import ctypes  # noqa: E402

import pyglet  # noqa: E402

# pyglet checks for errors after EVERY OpenGL call: loading L03A meant
# 104 thousand checks, 0.9 s. It is only useful for debugging rendering, and must
# be turned off before importing pyglet.gl (menu.py imports it too).
pyglet.options["debug_gl"] = False

from support import cache_warmer  # noqa: E402
from support import paths  # noqa: E402
from ui import texts  # noqa: E402
from pyglet.math import Vec3  # noqa: E402

# the parts of the viewer, and the names the diagnostics ask this module for
from window.app import Viewer  # noqa: E402,F401
from window.drawing import (BlendSorter, SIGNATURE, WIRE_GRID, WIRE_OFF,  # noqa: E402,F401
                            WIRE_SKELETON)
from window.overlays import FAMILIES, ONE_SIDED, OVERLAYS, SHOWN_WHEN  # noqa: E402,F401
from window.scene import (FaceGroup, Level, RULE_PASSES_PER_TICK, TICKS_PER_SECOND,
                   levels_in, resolve_levels_folder, sections)  # noqa: E402,F401


def main() -> None:
    p = argparse.ArgumentParser(description="level viewer")
    p.add_argument("level", nargs="?", help="level to open (without: the main menu)")
    p.add_argument("--data", help="folder of the .bze files (if missing: the one in the settings, "
                                   "bze_levels/, then the BBLIT_DATA game folder)")
    p.add_argument("--cache", default=os.path.join(paths.APP_DIR, "extracted"))
    p.add_argument("--screenshot", help="write a PNG and exit")
    p.add_argument("--camera", help="fixed framing: x,y,z,yaw,pitch")
    p.add_argument("--no-blend", action="store_true", help="draw semi-transparent faces as opaque")
    p.add_argument("--sky", action="store_true", help="show the sky dome")
    p.add_argument("--invisible-walls", action="store_true",
                   help="the old flag: the same as --hardwalls unseen --steps all")
    p.add_argument("--nocollision", action="store_true",
                   help="show the faces without collision")
    p.add_argument("--boxes", action="store_true", help="show the collision boxes")
    p.add_argument("--deathzones", action="store_true",
                   help="show the zones that kill or hurt, the death floor included")
    # the three flags before they became one: the same flag
    p.add_argument("--damagezones", "--deathfloor", dest="deathzones", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--teleportzones", action="store_true", help="show the zones that respawn you at a fixed point")
    p.add_argument("--ground", action="store_true", help="show the collision ground")
    p.add_argument("--hardwalls", nargs="?", const="all", choices=("all", "unseen"),
                   help="show the heightmap's hard walls: all, or only the invisible ones")
    p.add_argument("--steps", nargs="?", const="all", choices=("all", "unseen"),
                   help="show the steps that stop you: all, or only those with nothing drawn over them")
    p.add_argument("--areaboxes", action="store_true", help="show the area boxes")
    p.add_argument("--movers", action="store_true", help="move the characters the game moves")
    p.add_argument("--gates", choices=("open", "shut", "game"),
                   help="the state the gates are shown in (default: open)")
    p.add_argument("--sky-choice", type=int, metavar="ROLE",
                   help="where two skies take turns, the role of the one to show (Level options -> Sky)")
    p.add_argument("--gatelinks", choices=("gates", "all"),
                   help="show who opens which gate, or every link")
    p.add_argument("--faces1000", action="store_true", help="show the 0x1000 terrain faces")
    p.add_argument("--no-walls-outside", action="store_true",
                   help="hide the sides of the walls that do not stop you (OUTSIDE)")
    p.add_argument("--hole-steps", action="store_true",
                   help="with the invisible walls, also the steps seen from a 0x7E hole")
    p.add_argument("--area-visibility", action="store_true",
                   help="draw only the areas the game would draw (findings 293-295)")
    p.add_argument("--camera-shadow", action="store_true", help="show the shadow point under the camera")
    p.add_argument("--wireframe", type=int, choices=(0, 1, 2), help="0 off, 1 skeleton, 2 grid")
    p.add_argument("--clones", type=int, choices=(0, 1, 2),
                   help="cloned templates: 0 off, 1 at startup, 2 all (key G)")
    p.add_argument("--albedo", type=float, help="texture x vertex color factor (default 1; 2 is the PlayStation)")
    p.add_argument("--uv-rule", choices=("pc", "pc_amd", "psx"),
                   help="texture coordinates: pc (the PC, clamped and repeated), pc_amd, psx (findings 328, 341)")
    p.add_argument("--fov", type=float,
                   help="vertical field of view in degrees (default 65; 51 is the game's, finding 327)")
    p.add_argument("--backface", action="store_true",
                   help="cull the one-sided faces as the game does (finding 307)")
    p.add_argument("--tick", type=int, help="freeze all animations on this tick (for screenshots)")
    p.add_argument("--tps", type=float, help="animation ticks per second (default 15, measured on the PSX)")
    p.add_argument("--scale-factor", type=int,
                   help="upscale the textures with scale2x/scale3x: 1, 2, 3, 4, 6 or 8")
    p.add_argument("--language", choices=texts.LANGUAGES, help="interface language")
    p.add_argument("--menu", help="open a menu page at startup (main, load, level, flags, video, "
                                  "general, help, extra): for verification screenshots")
    p.add_argument("--warm-cache", metavar="FOLDER", help=argparse.SUPPRESS)
    p.add_argument("--warm-flags", metavar="FILE", help=argparse.SUPPRESS)
    p.add_argument("--parent", type=int, help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.warm_flags:
        # the flag families of one level, in the background (cache_warmer.py)
        try:
            cache_warmer.run_flags(args.warm_flags, args.cache, args.parent)
        except Exception:  # noqa: BLE001
            pass
        return
    if args.warm_cache:
        # the background process that fills the piece cache (cache_warmer.py):
        # no window, and no error box if something goes wrong
        try:
            cache_warmer.run(args.warm_cache, args.cache, args.parent)
        except Exception:  # noqa: BLE001
            pass
        return

    v = Viewer(None, args.cache, screenshot=args.screenshot, scale_factor=args.scale_factor, language=args.language,
               data=args.data, level=args.level)
    # not while taking screenshots: those are verification runs
    v.warm_cache = not args.screenshot
    v.start_warmer()
    if args.menu:
        v.menu.show("main")
        if args.menu != "main":
            v.menu.open_page(args.menu)
    if args.no_blend:
        v.show_blending = False
    if args.sky:
        v.show_sky = True
    if args.invisible_walls:
        v.show_hard_walls, v.show_steps = "unseen", "all"
    if args.nocollision:
        v.show_no_collision = True
    if args.boxes:
        v.show_collision_boxes = True
    if args.deathzones:
        v.show_death_zones = True
    if args.teleportzones:
        v.show_teleport_zones = True
    if args.ground:
        v.show_ground = True
    if args.hardwalls:
        v.show_hard_walls = args.hardwalls
    if args.steps:
        v.show_steps = args.steps
    if args.areaboxes:
        v.show_area_boxes = True
    if args.faces1000:
        v.show_faces_1000 = True
    if args.no_walls_outside:
        v.show_walls_outside = False
    if args.hole_steps:
        v.show_hole_steps = True
    if args.area_visibility:
        v.show_area_visibility = True
        if v.current_level is not None:
            v.load_level(v.level_files[v.index], camera=False)
    if args.gatelinks:
        v.show_gate_links = args.gatelinks
    if args.gates:
        v.gate_state = args.gates
        if v.current_level is not None:
            v.load_level(v.level_files[v.index], camera=False)
    if args.movers:
        v.show_movers = True
        if v.current_level is not None:
            v.load_level(v.level_files[v.index], camera=False)
    if args.sky_choice is not None and v.current_level is not None:
        v.session_sky[v.current_level.name] = args.sky_choice
        v.load_level(v.level_files[v.index], camera=False)
    if args.camera_shadow:
        v.show_camera_shadow = True
    if args.wireframe is not None:
        v.wireframe = args.wireframe
    v.ensure_overlays()
    if args.clones is not None:
        v.show_clones = args.clones
    if args.albedo is not None:
        v.albedo = args.albedo
    if args.uv_rule is not None:
        v.uv_rule = args.uv_rule
    if args.fov is not None:
        v.fov = args.fov
    if args.backface:
        v.backface_culling = True
    if args.tick is not None:
        v.fixed_tick = args.tick
    if args.tps:
        v.tps = args.tps
    if args.camera:
        x, y, z, yaw, pitch = (float(w) for w in args.camera.split(","))
        v.pos, v.yaw, v.pitch = Vec3(x, y, z), yaw, pitch
    pyglet.app.run()


def main_guarded() -> None:
    """For the console-less executable: an error ends up in errors.txt next
    to the viewer and in a message box, instead of vanishing (like the
    fatal_errors.txt of the CTR viewer)."""
    try:
        main()
    except Exception:  # noqa: BLE001
        import traceback
        label_text = traceback.format_exc()
        file_path = os.path.join(paths.APP_DIR, "errors.txt")
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(label_text + "\n")
        except OSError:
            pass
        if paths.IS_FROZEN:
            ctypes.windll.user32.MessageBoxW(None, label_text[-1500:], "BBLIT Viewer", 0x10)
        raise


if __name__ == "__main__":
    main_guarded()
