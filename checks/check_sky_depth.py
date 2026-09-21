"""The objects carried with the camera: does the viewer resolve them by depth,
as the game does (finding 346)?

    .venv/Scripts/python checks/check_sky_depth.py
    .venv/Scripts/python checks/check_sky_depth.py L02B2 LS01

Finding 346: the game has no path of its own for a sky. Every opaque face of
every object carried with the camera is drawn with the depth test (GL_LEQUAL)
and the depth written; the cut-out and semi-transparent ones come after all
the opaque ones, farthest first, blended, without alpha test. So between two
domes the nearer face wins, pixel by pixel. The reverse measured it on the
models (`BBLIT_Decomp_Ale/docs/lists/sky_layers.md`): for each object, the
share of the sphere where the game shows it ("by depth") and where a viewer
painting the skies one over the other would ("in list order").

This measures the VIEWER, with its own drawing code: it opens the level, keeps
only the sky pieces, and draws the six faces of a cube around the camera
(90 degrees each). An object is seen where taking it away changes the pixel;
each pixel counts with its solid angle, so the shares are of the sphere. A
level with one sky per area (Era selector) is measured area by area.

The rows compared are those of `sky_layers.md` whose object the viewer draws
(a template no rule clones is not drawn) and that the game shows somewhere or
a list-order painting would (either share at least 1%).

Threshold, fixed before the change: at least 90% of the
rows within 5 points of the "by depth" share. Exits with 1 below it.

Measured, the bar MISSED: 12 of 30 rows before the
change (40.0%), 16 of 30 after (53.3%). Not in the full run for that reason.
The rows that stay off, by cause: 4 of Era selector, whose shares depend on
template 12, which no rule clones and the viewer does not draw; 7 of objects
with only blended faces, mostly transparent texels (the reverse counts a
face met, this counts a pixel changed); 3 in the three levels with two
domes, which are not two domes at once in the game: a rule deletes one sky
(effect 0x4000000 naming its role) and clones the other (L02B1 object 102,
L02B2 object 123, L02C3 objects 88, 124 and template 125).

`--rings` adds a diagnostic outside the threshold, on the core of the rule:
only the OPAQUE faces are drawn, a pixel belongs to the object whose removal
changes it (with opaque faces only, the nearest), and each ring of elevation
the reverse names ("by elevation": the object whose opaque face is the
nearest) is compared with the viewer's owner of that ring, 2.5 degrees in
from its edges. 20 of 35 rings before, 29 of 35 after; the six off are the
five of Era selector that name template 12, and the nadir of L02B1, where
both domes are black and taking one away changes nothing.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
import pyglet  # noqa: E402
from pyglet.gl import GL_RGB, GL_UNSIGNED_BYTE, glReadPixels, glViewport  # noqa: E402
import viewer  # noqa: E402
from game import levels  # noqa: E402
from support import level_cache  # noqa: E402
from support import paths  # noqa: E402
from window.scene import Level  # noqa: E402

SKY_LAYERS = os.path.join(PROJECT_DIR, "..", "BBLIT_Decomp_ALE", "docs", "lists", "sky_layers.md")
SIZE = 192              # pixels on a side of a cube face (the window)
TOLERANCE = 5.0         # points of the sphere
BAR = 0.90              # share of the rows that must be within the tolerance
MEANINGFUL = 1.0        # a row counts if either share is at least this

# yaw, pitch of the six faces; straight up and down a hair off the pole,
# or the look-at matrix with a fixed up vector would have no side
CUBE = [(0, 0), (90, 0), (180, 0), (270, 0), (0, 89.99), (0, -89.99)]


def in_prose(code):
    name = levels.official_name(code)
    return f"{name} ({code})" if name else code


def read_sky_layers(path):
    """(level code, area or None) -> {object: (by depth, in list order)}."""
    head = re.compile(r"^## .*\(`([^`]+)`\)")
    area = re.compile(r"^In area (\d+)")
    row = re.compile(r"^- object (\d+)[ ,].*\*\*by depth ([\d.]+)%\*\*, in list order ([\d.]+)%")
    out, code, where = {}, None, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = head.match(line)
            if m:
                code, where = m.group(1), None
                continue
            m = area.match(line)
            if m:
                where = int(m.group(1))
                continue
            m = row.match(line)
            if m and code:
                out.setdefault((code, where), {})[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    return out


def read_rings(path):
    """(level code, area or None) -> [(low, high, object or None)] from the
    "by elevation" lines; None for "mixed" and "nothing"."""
    head = re.compile(r"^## .*\(`([^`]+)`\)")
    area = re.compile(r"^In area (\d+)")
    ring = re.compile(r"([+-]\d+)\u2026([+-]\d+) (object (\d+)|mixed|nothing)")
    out, code, where = {}, None, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = head.match(line)
            if m:
                code, where = m.group(1), None
                continue
            m = area.match(line)
            if m:
                where = int(m.group(1))
                continue
            if line.startswith("- by elevation:") and code:
                out[(code, where)] = [(int(a), int(b), int(n) if n else None)
                                      for a, b, _w, n in ring.findall(line)]
    return out


# --- which object each piece is: the pieces are built from nothing (no piece
# cache) and every piece is tagged as it is built
OWNER = {}      # id(piece) -> object index
MOUNTS = []     # (piece, area, keep_area), in the order the level mounts them
_piece, _clone, _mount = Level._piece, Level._clone, Level._mount


def _tagged_piece(self, item_key, build_items, mount=True, area=None):
    outer = getattr(self, "_owner_note", None)
    self._owner_note = None
    piece = _piece(self, item_key, build_items, mount, area)
    if item_key[0] == "object":
        OWNER[id(piece)] = item_key[1]
    elif item_key[0] == "clone" and self._owner_note is not None:
        OWNER[id(piece)] = self._owner_note
    self._owner_note = outer
    return piece


def _tagged_clone(self, t, n_t, *args, **kwargs):
    self._owner_note = n_t
    return _clone(self, t, n_t, *args, **kwargs)


def _logged_mount(self, piece, area=None, keep_area=False):
    MOUNTS.append((piece, area, keep_area))
    return _mount(self, piece, area, keep_area)


Level._piece, Level._clone, Level._mount = _tagged_piece, _tagged_clone, _logged_mount
level_cache.fetch = lambda *a, **k: None
level_cache.store = lambda *a, **k: None


def is_sky(piece):
    return any(meta[1] == "sky_dome" for meta, _d, _f, _t in piece[0].values())


def weights(size):
    """The solid angle of each pixel of a 90-degree cube face."""
    w = []
    for j in range(size):
        v = (2 * (j + 0.5) / size) - 1
        for i in range(size):
            u = (2 * (i + 0.5) / size) - 1
            w.append(1.0 / (1 + u * u + v * v) ** 1.5)
    return w


def remount(v, mounts):
    """The level's groups again, from the given sky pieces only."""
    level = v.current_level
    v._free_gpu(texture=False)
    level.face_groups = {}
    for piece, area, keep_area in mounts:
        _mount(level, piece, area, keep_area)
    if hasattr(v, "_prepare_groups"):
        v._prepare_groups()
    else:
        # the viewer before finding 346: the groups only uploaded
        for face_group in level.face_groups.values():
            v._upload(face_group)


def face_size(v):
    """The side of the square the faces are drawn in: the whole framebuffer,
    or the 90 degrees would not reach the edges of what is read."""
    width, height = v.get_framebuffer_size()
    return min(width, height)


def shoot(v):
    """The six faces, as one list of pixels (3 bytes each)."""
    size = face_size(v)
    out = []
    for yaw, pitch in CUBE:
        v.yaw, v.pitch = yaw, pitch
        v.switch_to()
        glViewport(0, 0, size, size)
        v.on_draw()
        buf = (pyglet.gl.GLubyte * (size * size * 3))()
        glReadPixels(0, 0, size, size, GL_RGB, GL_UNSIGNED_BYTE, buf)
        out.append(bytes(buf))
    return out


def measure(v, sky_mounts, area):
    """Object -> share of the sphere (percent) where taking it away changes
    the picture."""
    if area is not None:
        v.sky_area = lambda: area
    owners = sorted({OWNER.get(id(p)) for p, _a, _k in sky_mounts} - {None})
    remount(v, sky_mounts)
    full = shoot(v)
    size = face_size(v)
    w = weights(size)
    total = 6 * sum(w)
    shares = {}
    for n in owners:
        remount(v, [m for m in sky_mounts if OWNER.get(id(m[0])) != n])
        without = shoot(v)
        seen = 0.0
        for a, b in zip(full, without):
            if a == b:
                continue
            for k in range(size * size):
                if a[3 * k:3 * k + 3] != b[3 * k:3 * k + 3]:
                    seen += w[k]
        shares[n] = 100.0 * seen / total
    return shares


def elevations(size):
    """The elevation (degrees) of every pixel of the six faces, in the order
    `shoot` reads them (rows from the bottom)."""
    out = []
    for yaw, pitch in CUBE:
        j, p = math.radians(yaw), math.radians(pitch)
        f = (math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        # look_at with the world's up: side = f x up, up' = side x f
        s_ = (-f[2], 0.0, f[0])
        n = math.sqrt(s_[0] ** 2 + s_[2] ** 2)
        s_ = (s_[0] / n, 0.0, s_[2] / n)
        u_ = (s_[1] * f[2] - s_[2] * f[1], s_[2] * f[0] - s_[0] * f[2], s_[0] * f[1] - s_[1] * f[0])
        face = []
        for row in range(size):
            b = (2 * (row + 0.5) / size) - 1
            for col in range(size):
                a = (2 * (col + 0.5) / size) - 1
                d = [f[k] + a * s_[k] + b * u_[k] for k in range(3)]
                face.append(math.degrees(math.asin(d[1] / math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2))))
        out.append(face)
    return out


def opaque_only(piece, cut_outs):
    """A copy of a piece with only its opaque groups."""
    groups, lo, hi, delta = piece
    kept = {k: g for k, g in groups.items() if g[0][2] is None and g[0][0] not in cut_outs}
    return (kept, lo, hi, delta)


def ring_owners(v, sky_mounts, area):
    """With opaque faces only: object -> the set of (face, pixel) it owns."""
    if area is not None:
        v.sky_area = lambda: area
    cut_outs = v.current_level.cut_outs
    mounts = [(opaque_only(p, cut_outs), a, k) for p, a, k in sky_mounts]
    owner_of = {id(m[0]): OWNER.get(id(o[0])) for m, o in zip(mounts, sky_mounts)}
    owners = sorted({n for n in owner_of.values() if n is not None})
    remount(v, mounts)
    full = shoot(v)
    size = face_size(v)
    owned = {}
    for n in owners:
        remount(v, [m for m in mounts if owner_of[id(m[0])] != n])
        without = shoot(v)
        mine = set()
        for f, (a, b) in enumerate(zip(full, without)):
            if a == b:
                continue
            for k in range(size * size):
                if a[3 * k:3 * k + 3] != b[3 * k:3 * k + 3]:
                    mine.add((f, k))
        owned[n] = mine
    return owned, size


def check_rings(v, sky_mounts, area, rings, code):
    owned, size = ring_owners(v, sky_mounts, area)
    elev = elevations(size)
    w = weights(size)
    for low, high, n in rings:
        if n is None:
            continue
        a, b = low - 1 + 2.5, high - 2.5
        if a >= b:
            continue
        total = mine = 0.0
        for f in range(6):
            for k in range(size * size):
                if a <= elev[f][k] <= b:
                    total += w[k]
                    if (f, k) in owned.get(n, ()):
                        mine += w[k]
        share = 100.0 * mine / total if total else 0.0
        print(f"  rings {in_prose(code)[:36]:36s} area {area!s:>4s} {low:+4d}..{high:+4d} object {n:4d}: "
              f"viewer owns {share:5.1f}%  {'ok' if share >= 75 else 'OFF'}")


def open_viewer(code):
    path = os.path.join(paths.DATA_BZE, code + ".bze")
    if not os.path.exists(path):
        match = [f for f in os.listdir(paths.DATA_BZE) if f.lower() == code.lower() + ".bze"]
        path = os.path.join(paths.DATA_BZE, match[0])
    OWNER.clear()
    MOUNTS.clear()
    v = viewer.Viewer([path], "extracted", 0, screenshot="none.png")
    v.screenshot = None
    pyglet.clock.unschedule(v._screenshot)
    v.ui_hidden = True
    v.show_sky = True
    v.fov = 90
    v.set_size(SIZE, SIZE)
    return v


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", help="level codes; all those of sky_layers.md by default")
    parser.add_argument("--rings", action="store_true", help="also the opaque-only rings of elevation")
    args = parser.parse_args(argv)
    expected = read_sky_layers(SKY_LAYERS)
    rings = read_rings(SKY_LAYERS) if args.rings else {}
    codes = sorted({code for code, _a in expected}, key=str.lower)
    if args.levels:
        wanted = {c.lower() for c in args.levels}
        codes = [c for c in codes if c.lower() in wanted]
    rows = []
    for code in codes:
        v = open_viewer(code)
        sky_mounts = [m for m in MOUNTS if is_sky(m[0])]
        for (c, area), objects in sorted(expected.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
            if c != code:
                continue
            mounts = [m for m in sky_mounts if m[1] is None or m[1] == area] if area else sky_mounts
            shares = measure(v, mounts, area)
            for n, (by_depth, in_order) in sorted(objects.items()):
                if n not in shares:
                    print(f"  {in_prose(code)[:40]:40s} area {area!s:>4s} object {n:4d}: "
                          f"not drawn by the viewer (by depth {by_depth:5.1f}%)")
                    continue
                if max(by_depth, in_order) < MEANINGFUL:
                    continue
                ok = abs(shares[n] - by_depth) <= TOLERANCE
                rows.append(ok)
                print(f"  {in_prose(code)[:40]:40s} area {area!s:>4s} object {n:4d}: "
                      f"viewer {shares[n]:5.1f}%  by depth {by_depth:5.1f}%  in list order {in_order:5.1f}%"
                      f"  {'ok' if ok else 'OFF'}")
            if (c, area) in rings:
                check_rings(v, mounts, area, rings[(c, area)], code)
        v.close()
    held = sum(rows)
    share = held / len(rows) if rows else 0.0
    print(f"\n{held} of {len(rows)} rows within {TOLERANCE:.0f} points of 'by depth': "
          f"{100 * share:.1f}% (bar {100 * BAR:.0f}%)")
    return 0 if share >= BAR else 1


if __name__ == "__main__":
    sys.exit(main())
