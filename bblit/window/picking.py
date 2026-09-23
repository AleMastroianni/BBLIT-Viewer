"""The selector: Alt+click on a pixel and read what is there.

Why it exists: without it a point can only be reported as a red circle on a
screenshot, the camera has to be rebuilt from it by correlation, and the two
sides end up looking at two different things.

Alt+click casts a ray through that pixel and collects **everything drawn
there**, nearest first; clicking again on the same pixel steps down the
stack. Only what is DRAWN is picked (a flag whose group is off is not
there), but a run with nothing drawn on it -- an invisible wall -- is
picked, because its panel is drawn and that is exactly what is being looked
for.

For a wall the card says which group draws it, the run's plane and ends, its
top and base, the drop in units and in metres, whether it is an edge over a
hole or a real step, the free side, whether the game draws anything on it,
and up to what height it stops Bugs. For a coloured face it adds the face's
distance from the collision plane, its slant in degrees, how much of it
falls in the run's strip and how many of the run's cells it holds.
"""

from __future__ import annotations

import ctypes
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyglet.gl import (GL_ARRAY_BUFFER, glBindBuffer,  # noqa: E402
                       glGetBufferSubData)

from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import walls  # noqa: E402
from ui.texts import t  # noqa: E402

FLOATS = 8          # floats per vertex in a group's buffer
SAME_PIXEL = 6      # clicking within this many pixels means "the same spot"
# how high Bugs gets from standing (the reverse's figure): a rise he can
# clear is a step, one he cannot is a wall
JUMP = collision.JUMP_HEIGHT


def _triangles(group):
    """A group's triangles in world coordinates. After a group is uploaded
    its `data` is freed to keep RAM down (`scene._upload`), so they are read
    back from the buffer on the card: it happens on a click, not per frame."""
    data = group.data
    if not len(data):
        if not group.vbo or not group.item_count:
            return []
        buf = (ctypes.c_float * (group.item_count * FLOATS))()
        glBindBuffer(GL_ARRAY_BUFFER, group.vbo)
        glGetBufferSubData(GL_ARRAY_BUFFER, 0, ctypes.sizeof(buf), buf)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        data = buf
    return [(tuple(data[i:i + 3]), tuple(data[i + FLOATS:i + FLOATS + 3]),
             tuple(data[i + 2 * FLOATS:i + 2 * FLOATS + 3]))
            for i in range(0, len(data), FLOATS * 3)]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _ray_triangle(origin, direction, tri):
    """Moller-Trumbore: the distance along the ray, or None."""
    a, b, c = tri
    e1 = [b[k] - a[k] for k in range(3)]
    e2 = [c[k] - a[k] for k in range(3)]
    h = _cross(direction, e2)
    det = sum(e1[k] * h[k] for k in range(3))
    if abs(det) < 1e-9:
        return None
    s = [origin[k] - a[k] for k in range(3)]
    u = sum(s[k] * h[k] for k in range(3)) / det
    if u < 0.0 or u > 1.0:
        return None
    q = _cross(s, e1)
    v = sum(direction[k] * q[k] for k in range(3)) / det
    if v < 0.0 or u + v > 1.0:
        return None
    dist = sum(e2[k] * q[k] for k in range(3)) / det
    return dist if dist > 0.0 else None


def ray(viewer, px, py):
    """The ray through a pixel (pyglet's coordinates: y from the bottom)."""
    fov = math.radians(float(viewer.fov))
    j, p = math.radians(viewer.yaw), math.radians(viewer.pitch)
    forward = (math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
    right = _cross(forward, (0.0, 1.0, 0.0))
    length = sum(c * c for c in right) ** 0.5
    right = tuple(c / length for c in right)
    up = _cross(right, forward)
    half = math.tan(fov / 2.0)
    ndc_x = 2.0 * px / viewer.width - 1.0
    ndc_y = 2.0 * py / viewer.height - 1.0
    d = [forward[k] + right[k] * ndc_x * half * (viewer.width / viewer.height) + up[k] * ndc_y * half
         for k in range(3)]
    length = sum(c * c for c in d) ** 0.5
    return tuple(c / length for c in d)


def _game(point):
    """A viewer point (metres) back into game units."""
    u = geo.UNITS_PER_METER
    return (point[0] * u, -point[1] * u, -point[2] * u)


def _run_at(level, category, spot):
    """The wall run a picked point belongs to: the record whose plane, ends
    and heights hold it. None when the group is not a wall's."""
    best = None
    for info in getattr(level, "wall_picks", ()):
        if info["group"] != category.replace("_outside", "").replace("_faces", "").replace("_label", ""):
            continue
        c = 0 if info["axis"] == "x" else 2
        a = 2 if info["axis"] == "x" else 0
        off = abs(spot[c] - info["plane"])
        if off > walls.PLANE_TOLERANCE + 8:
            continue
        if not (info["a0"] - 4 <= spot[a] <= info["a1"] + 4):
            continue
        if not (info["y_top"] - 4 <= spot[1] <= info["y_base"] + 4):
            continue
        if best is None or off < best[0]:
            best = (off, info)
    return best[1] if best else None


def stack(viewer, px, py):
    """Everything drawn on that pixel, nearest first."""
    level = viewer.current_level
    if level is None:
        return []
    direction = ray(viewer, px, py)
    origin = (viewer.pos.x, viewer.pos.y, viewer.pos.z)
    found = []
    for group in viewer.groups_on_screen():
        if group.mover is not None or group.spin or group.frames:
            continue            # placed by the simulation when drawing
        if group.category.endswith("_lines"):
            continue            # edges, not a surface
        for tri in _triangles(group):
            dist = _ray_triangle(origin, direction, tri)
            if dist is not None:
                found.append((dist, group.category, tri))
    found.sort(key=lambda row: row[0])
    out, seen = [], []
    for dist, category, tri in found:
        # the same surface met twice is one entry: the two triangles of a
        # quad, and a group with its `_outside` twin, which is the same
        # rectangle seen from the other side
        base = category.replace("_outside_label", "_label")
        base = base[:-8] if base.endswith("_outside") else base
        if any(abs(dist - d) < 0.05 and c == base for d, c, _ in seen):
            continue
        seen.append((dist, base, tri))
        category = base
        point = tuple(origin[k] + dist * direction[k] for k in range(3))
        spot = _game(point)
        entry = dict(distance=dist, category=category, at=spot,
                     normal=_normal(tri), tri=tri)
        info = _run_at(level, category, spot)
        if info is not None:
            entry["run"] = info
            entry["on_face"] = category.endswith(("_faces", "_faces_outside"))
        out.append(entry)
    return out


def _normal(tri):
    a, b, c = tri
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - a[k] for k in range(3)]
    n = _cross(u, v)
    length = sum(x * x for x in n) ** 0.5
    return None if length == 0 else tuple(x / length for x in n)


def card(entry, level=None):
    """The selected thing, as lines of text for the panel and the clipboard."""
    u = geo.UNITS_PER_METER
    x, y, z = entry["at"]
    lines = [t("pick.group", name=entry["category"]),
             t("pick.point", x=x, y=y, z=z, m=entry["distance"])]
    info = entry.get("run")
    if info is not None:
        ends = (f"x = {info['plane']:.0f}, z {info['a0']:.0f} .. {info['a1']:.0f}"
                if info["axis"] == "x" else
                f"z = {info['plane']:.0f}, x {info['a0']:.0f} .. {info['a1']:.0f}")
        drop = info["y_base"] - info["y_top"]
        lines.append(t("pick.run", ends=ends))
        lines.append(t("pick.height", top=info["y_top"], base=info["y_base"],
                       drop=drop, metres=drop / u))
        if info["kind"] == "hard":
            lines.append(t("pick.block", floor=info["floor"], ceiling=info["ceiling"]))
            lines.append(t("pick.stops_wall", ceiling=info["ceiling"], m=(info["floor"] - info["ceiling"]) / u))
        elif info["kind"] == "drop":
            lines.append(t("pick.drop_wall", m=drop / u, jump=JUMP))
            lines.append(t("pick.step_real"))
        elif info["hole"]:
            lines.append(t("pick.edge", m=drop / u))
        else:
            lines.append(t("pick.step_real"))
            lines.append(t("pick.climbable", m=drop / u, jump=JUMP))
        lines.append(t("pick.free", dx=info["free"][0], dz=info["free"][1]))
        lines.append(t("pick.seen") if info["visible"] else t("pick.unseen"))
    n = entry.get("normal")
    if entry.get("on_face") and info is not None and n is not None:
        c = 0 if info["axis"] == "x" else 2
        tilt = math.degrees(math.asin(min(1.0, abs(n[1]))))
        off = math.degrees(math.acos(min(1.0, abs(n[c]))))
        lines.append(t("pick.face", d=entry["at"][c] - info["plane"], tilt=tilt, off=off))
    return lines
