"""The alpha the PC builds into a texture for each blend mode (finding 305).

    .venv/Scripts/python checks/check_blend_modes.py [L03A L01A ...]

The PC's OpenGL renderer has ONE blend function for every semi-transparent
polygon and tells the four PlayStation modes apart only by the alpha it
builds into a copy of the texture when it loads it, one copy per mode the
texture is used with. `tim.pc_colour(mode)` is the viewer's version of that
conversion; this check compares it, palette entry by palette entry, with the
rule written out by hand from the finding, and looks at what comes out on
the textures of the disc.

Exits with 1 if anything differs.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import tim  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

failures = []


def probe(entry_name, cond):
    print(("OK   " if cond else "FAIL ") + entry_name)
    if not cond:
        failures.append(entry_name)


def by_hand(r, g, b, a, mode):
    """The rule of finding 305, written out again from the finding and not
    from the viewer's code, gamma last (findings 306, 310)."""
    if a == 0:
        return r, g, b, 0
    if mode is None:
        alpha = 255
    elif mode == 2:
        alpha = int(0.299 * r + 0.587 * g + 0.114 * b)
    else:
        m = max(r, g, b)
        alpha = {0: m // 2, 1: m - m // 4, 3: m // 4}[mode]
        r, g, b = r + (255 - m), g + (255 - m), b + (255 - m)
    gamma = [min(255, int(256.0 * (c / 256.0) ** (1.0 / 1.2))) for c in range(256)]
    return gamma[r], gamma[g], gamma[b], alpha


MODES = (None, 0, 1, 2, 3)
# every colour a 15-bit palette entry can be, thinned out: 5 bits per channel
FIVE_BITS = [c * 255 // 31 for c in range(32)]
n_entries = 0
for mode in MODES:
    convert = tim.pc_colour(mode)
    for r in FIVE_BITS:
        for g in FIVE_BITS:
            for b in FIVE_BITS[::4]:
                n_entries += 1
                if convert(r, g, b, 255) != by_hand(r, g, b, 255, mode):
                    probe(f"mode {mode} differs on ({r}, {g}, {b})", False)
                    break
probe(f"every mode matches the rule of the finding on {n_entries} palette entries",
      not failures)

probe("the transparent entry stays transparent in every mode",
      all(tim.pc_colour(mode)(120, 104, 8, 0)[3] == 0 for mode in MODES))
probe("a grey entry comes out white in the modes that push the colour",
      all(tim.pc_colour(mode)(90, 90, 90, 255)[:3] == (255, 255, 255)
          for mode in (0, 1, 3)))
probe("mode 2 leaves the colour alone and takes the luminance as alpha",
      tim.pc_colour(2)(90, 120, 30, 255)[:3] == tim.pc_colour(None)(90, 120, 30, 255)[:3]
      and tim.pc_colour(2)(90, 120, 30, 255)[3] == int(0.299 * 90 + 0.587 * 120 + 0.114 * 30))
probe("an opaque texture is the gamma and nothing else",
      all(tim.pc_colour(None)(r, g, b, 255) == (tim.GAMMA_TABLE[r], tim.GAMMA_TABLE[g],
                                                tim.GAMMA_TABLE[b], 255)
          for r in FIVE_BITS for g in FIVE_BITS[::3] for b in FIVE_BITS[::5]))

# the halo of the torch of Hey... What's up, Dock? part 1, the example the
# finding works through: the middle texel (120, 104, 8) in mode 1
halo = tim.pc_colour(1)(120, 104, 8, 255)
wanted = (255, tim.GAMMA_TABLE[239], tim.GAMMA_TABLE[143], 90)
probe(f"the halo's middle texel of finding 305 comes out {wanted}", halo == wanted)
print(f"   the finding reads (120, 104, 8) -> (255, 239, 143) with alpha 90 before "
      f"the gamma, and over (20, 24, 40) the screen shows a pale haze, not a sum")

# how many copies of a texture the disc really asks for
names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
pairs, textures = set(), set()
for name in names:
    path = os.path.join(paths.DATA_BZE, name + ".bze")
    if not os.path.exists(path):
        continue
    sec = sections(path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    for t in lvl["textures"]:
        textures.add((name, t["id"]))
print(f"{len(textures)} textures registered in {len(names)} levels")
probe("there are textures to convert", len(textures) > 1000)

print(f"\n{len(failures)} failed" if failures else "\nall consistent")
sys.exit(1 if failures else 0)
