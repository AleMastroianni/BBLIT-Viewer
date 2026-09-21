"""The three texture coordinate rules (findings 328, 341), against the formula the
viewer used before and the one the PC's code applies.

    .venv/Scripts/python checks/check_uv_rules.py [L03A L01A ...]

The viewer now stores byte / 255 in its buffers (the rule of the PC's OpenGL
renderer) and applies the chosen rule while drawing, as
clamp(uv, low, high) * scale + offset. This check asks the PlayStation rule
for the same number the old closed formula gave, byte for byte and for every
texture size of the levels, and checks the edges of the other two.

The PC's rule (finding 341) is byte / 255 clamped to [0.01, 0.99] on both
axes, then GL_REPEAT. Bar fixed before the change: the
default rule draws exactly that for all 65,536 byte pairs. Before the change
the default was the provisional "pc_edge" (byte / 255, unclamped): 62,500 of
65,536 pairs (95.4%), the bytes 3..252 on both axes.

Exits with 1 if anything differs.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
from game import geometry as geo  # noqa: E402
from game import levels  # noqa: E402
from game import loadscript  # noqa: E402
from game import tim  # noqa: E402
from support import paths  # noqa: E402
from viewer import sections  # noqa: E402

TOLERANCE = 1e-12
failures = []


def probe(entry_name, cond):
    print(("OK   " if cond else "FAIL ") + entry_name)
    if not cond:
        failures.append(entry_name)


def old_rule(u, v, measure):
    """`uv_to_texture` as it was before finding 328: the software
    renderer's (size - 1), sampled at the texel centre."""
    b, h = measure
    x = u / 255.0 * (b - 1)
    y = (255 - v) / 255.0 * (h - 1)
    return ((x + 0.5) / b, (y + 0.5) / h)


def drawn_pair(rule, measure, pair):
    """What the graphics card computes: clamp(uv, low, high) * scale + offset
    on the uv stored in the buffer."""
    low, high, scale, offset = geo.uv_transform(rule, measure)
    return tuple(min(max(pair[i], low[i]), high[i]) * scale[i] + offset[i] for i in (0, 1))


def drawn(rule, measure, u, v):
    """The same, starting from the two bytes of the face."""
    return drawn_pair(rule, measure, geo.uv_to_unit(u, v))


# the texture sizes really on the disc, from the levels asked for
names = sys.argv[1:] or sorted({v[1] for v in levels.all_entries()})
sizes = set()
for name in names:
    path = os.path.join(paths.DATA_BZE, name + ".bze")
    if not os.path.exists(path):
        continue
    sec = sections(path, "extracted")
    lvl = loadscript.export_level(loadscript.parse(sec[1])[0])
    sizes.update(tim.sizes(sec[3], lvl["textures"]).values())
print(f"{len(names)} levels, {len(sizes)} different texture sizes")
probe("the levels give some texture size", len(sizes) > 0)

worst = 0.0
for measure in sorted(sizes):
    for u in range(256):
        for v in (0, 1, 127, 128, 254, 255):
            a = drawn(geo.UV_PSX, measure, u, v)
            b = old_rule(u, v, measure)
            worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
probe(f"PlayStation rule: the same number as before on every size (worst {worst:.2e})", worst < TOLERANCE)
probe("and uv_to_texture, the one the OBJ export bakes in, is still that rule",
      all(abs(x - y) < TOLERANCE for measure in sorted(sizes)[:8] for u in (0, 37, 255)
          for x, y in zip(geo.uv_to_texture(u, u, measure), old_rule(u, u, measure))))

# the PC's OpenGL renderer (finding 341): byte / 255, clamped to [0.01, 0.99]
measure = (32, 32)


def pc_formula(byte):
    return min(max(byte / 255.0, 0.01), 0.99)


pairs_ok = sum(1 for u in range(256) for v in range(256)
               if drawn(geo.UV_PC, measure, u, v) == (pc_formula(u), pc_formula(255 - v)))
probe(f"PC: clamp(byte / 255, 0.01, 0.99) for {pairs_ok} of 65536 byte pairs (bar: all)", pairs_ok == 65536)
probe("PC: bytes 0, 1, 2 give 0.01 and 253, 254, 255 give 0.99",
      all(drawn(geo.UV_PC, measure, u, 255 - u) == (0.01, 0.01) for u in (0, 1, 2))
      and all(drawn(geo.UV_PC, measure, u, 255 - u) == (0.99, 0.99) for u in (253, 254, 255)))
probe("PC: the texture's size does not enter into it",
      all(drawn(geo.UV_PC, m, 91, 91) == drawn(geo.UV_PC, (4, 4), 91, 91) for m in sorted(sizes)))
probe("PC: the default of the settings, and the rule a saved 'pc_edge' falls back to",
      geo.UV_RULES[0] == geo.UV_PC and "pc_edge" not in geo.UV_RULES)

# an AMD card: the outer strip is never seen
low_edge, high_edge = 4.5 / 255.0, 250.5 / 255.0
probe("AMD: byte 0 and byte 255 stop at 4.5/255 and 250.5/255",
      drawn(geo.UV_PC_AMD, measure, 0, 255) == (low_edge, low_edge)
      and drawn(geo.UV_PC_AMD, measure, 255, 0) == (high_edge, high_edge))
probe("AMD: between 5 and 250 nothing changes from the PC rule",
      all(drawn(geo.UV_PC_AMD, measure, u, u) == drawn(geo.UV_PC, measure, u, u) for u in range(5, 251)))
probe("AMD: its strip is narrower than the PC's clamp, so the PC's changes nothing on it",
      low_edge > 0.01 and high_edge < 0.99)
probe("AMD: 3.53% of every texture, the outer strip, is never seen",
      abs((2 * low_edge) - 0.0353) < 0.0005)

# a flag's name runs OUTSIDE 0..1 (flag_labels.label_uvs): it is drawn with
# the raw rule, which clamps nothing, or the text would be stretched
probe("a flag's name (the raw rule) is left alone",
      all(drawn_pair(geo.UV_RAW, None, uv) == uv for uv in ((-3.2, 4.7), (0.5, 0.5), (1.0, 0.0))))
probe("and the PC's and the AMD rule do clamp a coordinate outside 0..1",
      drawn_pair(geo.UV_PC, (32, 32), (-3.2, 4.7)) == (0.01, 0.99)
      and drawn_pair(geo.UV_PC_AMD, (32, 32), (-3.2, 4.7)) == (low_edge, high_edge))
probe("the three rules are the ones the menu and the settings name, the PC's first",
      geo.UV_RULES == ("pc", "pc_amd", "psx"))

print(f"\n{len(failures)} failed" if failures else "\nall rules agree")
sys.exit(1 if failures else 0)
