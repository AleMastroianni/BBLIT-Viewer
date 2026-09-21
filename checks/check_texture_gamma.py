"""The gamma the PC's OpenGL renderer puts every texture through
(findings 306 and 310).

    .venv/Scripts/python checks/check_texture_gamma.py [L03A L01A ...]

The game runs every colour of every texture through
c' = int(256 * (c/256) ** (1/1.2)) when it loads it, and leaves the vertex
colours alone. That the game really does it was measured by the reverse on
screenshots of the PC game (finding 310: on the galleon's hull the exponent
comes out 0.856, against 1.011 on the same measurement of the viewer
without the gamma). This check is about the viewer doing it right:

* the table is the formula, and it matches the four numbers the finding
  quotes;
* on every texture of the disc the alpha comes back byte for byte, no
  channel ever darkens, and 0 and 255 stay where they are;
* the exponent measured on the texels the way the finding measured it on
  the screen -- the slope of ln(R/B) -- comes out 1/1.2, and that window is
  narrow enough to tell it apart from the software renderer's 1/1.7, which
  measures 0.59.

Exits with 1 if anything differs.
"""
import math
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


# --------------------------------------------------------------- the table
by_formula = [min(255, int(256.0 * (c / 256.0) ** (1.0 / 1.2))) for c in range(256)]
probe("the table is c' = int(256 * (c/256) ** (1/1.2)) on all 256 values",
      list(tim.GAMMA_TABLE) == by_formula)
quoted = {32: 45, 64: 80, 128: 143, 200: 208}
probe(f"and it gives the numbers finding 306 quotes ({quoted})",
      all(tim.GAMMA_TABLE[c] == v for c, v in quoted.items()))
probe("black stays black and white stays white",
      tim.GAMMA_TABLE[0] == 0 and tim.GAMMA_TABLE[255] == 255)
probe("no colour is ever darkened, and the dark ones are lifted the most",
      all(tim.GAMMA_TABLE[c] >= c for c in range(256))
      and tim.GAMMA_TABLE[32] - 32 > tim.GAMMA_TABLE[200] - 200)

# ------------------------------------------------- every texture on the disc
names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
n_textures = 0
alpha_kept = True
sum_before = sum_after = 0.0
n_pairs = 0
for name in names:
    path = os.path.join(paths.DATA_BZE, name + ".bze")
    if not os.path.exists(path):
        continue
    sec = sections(path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    for t in lvl["textures"]:
        try:
            _b, _h, rgba = tim.read_tim(sec[3], t["offset"])
        except Exception:  # noqa: BLE001
            continue
        n_textures += 1
        lit = tim.with_gamma(rgba)
        if bytes(lit[3::4]) != bytes(rgba[3::4]):
            alpha_kept = False
        # the slope of ln(R/B), the way finding 310 measured it on the
        # screen: only the texels that are visible and have both channels
        for i in range(0, len(rgba), 4):
            r, b, a = rgba[i], rgba[i + 2], rgba[i + 3]
            if a < 128 or r < 8 or b < 8 or r == b:
                continue
            before = math.log(r / b)
            sum_before += before * before
            sum_after += math.log(lit[i] / lit[i + 2]) * before
            n_pairs += 1

print(f"{n_textures} textures, {n_pairs} texels with both channels")
probe("there are textures to look at", n_textures > 1000 and n_pairs > 100000)
probe("the alpha comes back byte for byte", alpha_kept)

measured = sum_after / sum_before if sum_before else 0.0
probe(f"the exponent measured on the texels is 1/1.2 = 0.833 (got {measured:.3f})",
      0.80 <= measured <= 0.87)
# the window has to tell the two renderers apart: the software one uses
# 1/1.7 at 24 bit (finding 306), and that must NOT pass for the OpenGL one
software = bytes(min(255, int(256.0 * (c / 256.0) ** (1.0 / 1.7))) for c in range(256))
software_slope = 0.0
for c in range(8, 256):
    for d in range(8, 256):
        if c != d:
            before = math.log(c / d)
            software_slope += before * math.log(software[c] / software[d]) / (before * before)
software_slope /= sum(1 for c in range(8, 256) for d in range(8, 256) if c != d)
probe(f"and the window tells it apart from the software renderer's 1/1.7 "
      f"(that one measures {software_slope:.3f})", not 0.80 <= software_slope <= 0.87)
print(f"   for comparison, finding 310 measured 0.856 on the game's screen "
      f"and 1.011 on the viewer without the gamma")

print(f"\n{len(failures)} failed" if failures else "\nall consistent")
sys.exit(1 if failures else 0)
