"""The flags: the colours, the names written on the faces and which group
is shown when, and how each overlay is built (`OverlayBuilder`, the part of
`scene.Level` that builds them).

A flag has its own groups: the level draws them only when its flag is on
(`SHOWN_WHEN`), and a family is built only when one of its flags is on, so a
level opened with the flags off costs nothing.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import collision  # noqa: E402
from game import geometry as geo  # noqa: E402
from game import entrances  # noqa: E402
from game import gates  # noqa: E402
from game import hazards  # noqa: E402
from game import levels  # noqa: E402
from ui import flag_labels  # noqa: E402
from game import montage  # noqa: E402
from game import zones  # noqa: E402

# the invisible walls (0x1000 sectors), when shown: a magenta the game
# does not use, at half transparency (blend 0)
COLOR_INVISIBLE_WALLS = (255, 40, 200)
# what you go through (flag No collision): white covering about 75%, with
# the triangle edges in black over it, so it stands out on light textures
COLOR_NO_COLLISION = (255, 255, 255)
COLOR_NO_COLLISION_EDGES = (0, 0, 0)
# the blend code of an overlay covering 75% (Viewer.on_draw, set_blend)
OVERLAY_BLEND = 4
# and of a collision box, so the model inside it can be seen (set_blend)
BOX_BLEND = 5
BOX_ALPHA = 0.30
# a collision box is filled at BOX_ALPHA so the model inside it can be seen
# (the user chose it on the photos: opaque buried the pirates, edges only
# lost the colour of the kind under the red outline of what hurts)
# overlays drawn on the terrain face itself, pulled forward in the depth
# test: the edges more than the fill, so they stay over it
PULLED_FORWARD = {"no_collision": (-1.0, -4.0), "no_collision_label": (-2.0, -8.0),
                  "no_collision_lines": (-2.0, -8.0),
                  # the names on the zone boxes' tops, over the box's own fill
                  "death_zones_label": (-2.0, -8.0), "teleport_zones_label": (-2.0, -8.0),
                  "faces_1000_label": (-2.0, -8.0),
                  # and on the heightmap's wall panels
                  "hard_walls_label": (-2.0, -8.0), "hard_walls_label_unseen": (-2.0, -8.0),
                  "invisible_walls_label": (-2.0, -8.0), "invisible_hard_walls_label": (-2.0, -8.0),
                  "step_walls_label": (-2.0, -8.0), "step_walls_outside_label": (-2.0, -8.0),
                  "hole_steps_label": (-2.0, -8.0), "hole_steps_outside_label": (-2.0, -8.0), "shared_zones_label": (-2.0, -8.0)}
# the texture with a flag's name, painted inside its faces (flag_labels.py):
# a texture id of its own; the names are always in English
LABEL_NO_COLLISION = "label:NO COLLISION"
LABEL_HARD_WALL = "label:HARD WALL"
LABEL_INVISIBLE_WALL = "label:INVISIBLE WALL"
LABEL_INVISIBLE_HARD_WALL = "label:" + flag_labels.combined(("INVISIBLE WALL", "HARD WALL"))
LABEL_STEP_WALL = "label:STEP WALL"
LABEL_STEP_WALL_OUTSIDE = "label:STEP WALL · OUTSIDE"
LABEL_AREA_WALL = "label:AREA WALL"
LABEL_AREA_WALL_OUTSIDE = "label:AREA WALL · OUTSIDE"
LABEL_JUMP_CEILING = "label:JUMP CEILING"
LABEL_JUMP_CEILING_OUTSIDE = "label:JUMP CEILING · OUTSIDE"
# the area a portal leads to (flag Portals): "AREA 12"
LABEL_AREA = "label:AREA "
# the area boxes are large: their names no taller than this (game units, 2 m)
AREA_LABEL_HEIGHT = 256
# the objects' collision boxes (flag Collision boxes), by what they do to
# Bugs (finding 300): a bit of SOLID_MASK in the first word of opcode 0x16
# stops him (orange, SOLID), with bit 0x8 he can also stand on it (green,
# PLATFORM); the others are only touched: pickups, triggers (blue, TOUCH)
COLOR_COLLISION_BOXES = (255, 150, 20)
COLOR_PLATFORM_BOXES = (70, 220, 90)
COLOR_TOUCH_BOXES = (90, 170, 255)
# and what hurts (finding 318): the same box, its edges red. Bright red when
# the object is dangerous in the state being shown, dark red when it is
# dangerous only in another of its states (the pirates and crabs of
# *Hey... What's up, Dock? 1* (`L03A`) hurt in state 199, the attack)
COLOR_HURTS_NOW = (255, 40, 40)
COLOR_HURTS_OTHER = (150, 25, 25)
SOLID_MASK = 0x9A690A
STAND_ON = 0x8
# a hard box (`+8 & 0x20000`) stops the camera too: said in the name, not in
# the colour, which is there to say what the box does to Bugs
HARD_BOX = 0x20000
# the names float above the box's top, this far up (game units: 128 = 1 m),
# and are this tall in the world
LABEL_LIFT = 80.0
LABEL_HEIGHT = 90.0
# nearer than this (metres along the view direction) a name stops growing and
# keeps the size it has here, or standing next to an object would fill the
# screen with its name
LABEL_NEAR = 14.0
# the zones (flag Death zones): all red, where you die, where the death
# floor is and where you get hurt (action 0x48), told apart by the name on
# the top of each box; purple where you are put back at a fixed point
# (flag Teleport zones)
COLOR_DEATH = (235, 25, 25)
COLOR_TELEPORT = (170, 70, 255)
# a teleport that can never fire (finding 337: its addressee is an id no
# object can have): grey, and DEAD in its name. It stays on screen, because
# what the game has but does not work is marked, not dropped
COLOR_DEAD = (150, 150, 150)
# the line from a switch to the gate it opens (flag Who opens what): the name
# on the gate's box says it too ("GATE <- #78"), so the colour is never the
# only thing that tells you
COLOR_GATE_LINK = (255, 120, 40)
# and the line to an object that only REACTS to a byte somebody writes: a
# different colour, and REACTS instead of GATE in its name
COLOR_REACTS_LINK = (90, 200, 255)
# What joins two points -- a teleport, the way in from another level, and
# (flag Boxes) who opens which gate -- is ONE line and nothing else: a bit thicker than a normal edge, ending exactly on the
# destination point, drawn through the geometry so it can be followed to where
# it goes even behind a wall. The old head and the cross on the point are
# gone: small, frayed and ugly, in the user's words.
LINK_WIDTH = 4.0          # how thick a link's line is drawn
# the heightmap (flags Ground, Hard walls) and the fake walls (Fake walls)
COLOR_GROUND = (60, 170, 80)              # covered by a visible face
COLOR_INVISIBLE_GROUND = (140, 255, 60)  # no visible face above
COLOR_PIXEL = (255, 255, 255)              # isolated sub-cells, with the ray
COLOR_HARD_WALLS = (60, 120, 255)
# the collision volume of each mini area (flag Area boxes)
COLOR_AREA_BOXES = (255, 170, 60)
# their sides and tops, seen from both sides: half as bright, the layers add up
COLOR_AREA_FILL = (128, 85, 30)
# the 0x1000 terrain faces (flag 0x1000 faces): not walls (tested in the game)
COLOR_FACES_1000 = (150, 150, 150)
# group -> viewer attribute that turns it on (the menu flags)
OVERLAYS = {
    "faces_1000": "show_faces_1000", "faces_1000_label": "show_faces_1000",
    "invisible_walls": "show_invisible_walls",
    "invisible_walls_label": "show_invisible_walls",
    "step_walls": "show_invisible_walls", "step_walls_label": "show_invisible_walls",
    "step_walls_outside": "show_invisible_walls", "step_walls_outside_label": "show_invisible_walls",
    "hole_steps": "show_invisible_walls", "hole_steps_label": "show_invisible_walls",
    "hole_steps_outside": "show_invisible_walls", "hole_steps_outside_label": "show_invisible_walls",
    "no_collision": "show_no_collision",
    "no_collision_lines": "show_no_collision",
    "no_collision_label": "show_no_collision",
    "area_boxes": "show_area_boxes", "area_boxes_lines": "show_area_boxes",
    "area_walls": "show_area_boxes", "area_walls_label": "show_area_boxes",
    "jump_ceilings": "show_area_boxes", "jump_ceilings_label": "show_area_boxes",
    "area_walls_outside": "show_area_boxes", "area_walls_outside_label": "show_area_boxes",
    "jump_ceilings_outside": "show_area_boxes", "jump_ceilings_outside_label": "show_area_boxes",
    "collision_boxes": "show_collision_boxes", "collision_boxes_lines": "show_collision_boxes",
    # "Who opens what": the line from a switch to the gate it opens
    "gate_links_lines": "show_gate_links",
    # the red outline of what hurts: its own group, drawn with thicker lines
    "collision_boxes_hurt_lines": "show_collision_boxes",
    "death_zones": "show_death_zones", "death_zones_lines": "show_death_zones",
    "death_zones_label": "show_death_zones",
    "teleport_zones": "show_teleport_zones", "teleport_zones_lines": "show_teleport_zones",
    "teleport_zones_label": "show_teleport_zones", "shared_zones_label": "show_death_zones",
    "teleport_arrows_lines": "show_teleport_zones",
    "covered_ground": "show_ground", "invisible_ground": "show_ground",
    "pixel": "show_ground", "pixel_beam": "show_ground",
    "hard_walls": "show_hard_walls", "hard_walls_label": "show_hard_walls",
    "hard_walls_label_unseen": "show_hard_walls", "invisible_hard_walls_label": "show_hard_walls",
}
# the overlay families: each is built, as pieces of its own, only when one of
# its flags is on, so a level opened with the flags off skips them all (the
# heightmap alone was 80-93% of the first build of a level: L03A 4.0 of 4.9 s)
FAMILIES = {
    "terrain_overlays": ("show_faces_1000", "show_no_collision"),
    "heightmap": ("show_ground", "show_hard_walls", "show_invisible_walls", "show_area_boxes"),
    "zones": ("show_death_zones", "show_teleport_zones"),
    "collision_boxes": ("show_collision_boxes", "show_gate_links"),
}
assert set(OVERLAYS.values()) == {a for flags in FAMILIES.values() for a in flags}
# groups whose visibility depends on more than their own flag:
# (all of these on, at least one of these on, none of these on). Written for
# the flag names that merge: the same place in two flags
# gets one name, "INV + HRD", instead of two texts over each other
SHOWN_WHEN = {
    # an invisible wall is a hard wall too: HARD WALL, INVISIBLE WALL, or both
    "hard_walls_label_unseen": (("show_hard_walls",), (), ("show_invisible_walls",)),
    "invisible_walls_label": (("show_invisible_walls",), (), ("show_hard_walls",)),
    "invisible_hard_walls_label": (("show_invisible_walls", "show_hard_walls"), (), ()),
    # a zone that kills and teleports is in both zone flags: one name
    "shared_zones_label": ((), ("show_death_zones", "show_teleport_zones"), ()),
}
# the groups drawn with a thicker line (the red outline of what hurts, over
# the box's own edge in the same place)
THICK_LINES = {"collision_boxes_hurt_lines", "teleport_arrows_lines", "gate_links_lines"}
# drawn through the geometry (no depth test): a link's line, so it can be
# followed behind a wall to where it goes
THROUGH_WALLS = {"teleport_arrows_lines", "gate_links_lines"}
THICK_LINE_WIDTH = 4.0
# names written on both sides of a wall, each drawn only from its own side,
# so neither reads mirrored
ONE_SIDED = {"hard_walls", "invisible_walls", "hard_walls_label", "hard_walls_label_unseen",
             "invisible_walls_label", "invisible_hard_walls_label",
             "step_walls", "step_walls_label", "step_walls_outside", "step_walls_outside_label",
             "hole_steps", "hole_steps_label", "hole_steps_outside", "hole_steps_outside_label",
             "faces_1000_label",
             # the area walls stop you only from inside, a jump ceiling only from below:
             # each is drawn only from the side where it acts
             "area_walls", "area_walls_label", "jump_ceilings", "jump_ceilings_label",
             "area_walls_outside", "area_walls_outside_label", "jump_ceilings_outside",
             "jump_ceilings_outside_label"}
# groups that also need a second setting on: the outside side of the area
# boxes (Flags -> Area boxes: outside side, on at every start)
# the sides where a wall does not stop you: with Walls: outside side (on at every start)
for _c in ("area_walls_outside", "area_walls_outside_label", "jump_ceilings_outside",
           "jump_ceilings_outside_label"):
    SHOWN_WHEN[_c] = (("show_area_boxes", "show_walls_outside"), (), ())
for _c in ("step_walls_outside", "step_walls_outside_label"):
    SHOWN_WHEN[_c] = (("show_invisible_walls", "show_walls_outside"), (), ())
# the steps from a 0x7E hole: with Walls: edges over holes (off at every start)
for _c in ("hole_steps", "hole_steps_label"):
    SHOWN_WHEN[_c] = (("show_invisible_walls", "show_hole_steps"), (), ())
for _c in ("hole_steps_outside", "hole_steps_outside_label"):
    SHOWN_WHEN[_c] = (("show_invisible_walls", "show_hole_steps", "show_walls_outside"), (), ())


def _box_kind(obj) -> str:
    """What an object's collision box does to Bugs (finding 300): "SOLID"
    (a bit of SOLID_MASK in the first word of opcode 0x16: it stops him),
    "PLATFORM" (solid, and bit 0x8: he can stand on it) or "TOUCH"."""
    word = (obj.get("static_flags") or [0])[0]
    if not word & SOLID_MASK:
        return "TOUCH"
    return "PLATFORM" if word & STAND_ON else "SOLID"


# steps closer than this to each other, facing the same way, are one
# staircase and get one name (game units, about 3 m)
# steps this close to each other, parallel and stopping you the same way,
# are one staircase and get one name (game units, 3.75 m)
STEP_GROUP_DISTANCE = 480


def _named_steps(steps):
    """The steps that carry the name, one per staircase: steps that stop you
    the same way, run along the same axis and are within
    STEP_GROUP_DISTANCE of each other, step after step, are one group, and
    only its largest panel is named (the one where the name reads best).
    Returns their places in `steps`. A name on every step of a flight came
    out as a smudge (the stairs of L04E)."""
    centres, buckets = [], {}
    for i, (xa, za, xb, zb, high, low, _visible, side, _hole) in enumerate(steps):
        axis = "x" if xa == xb else "z"
        centre = ((xa + xb) / 2, (high + low) / 2, (za + zb) / 2)
        centres.append(centre)
        cell = tuple(int(c // STEP_GROUP_DISTANCE) for c in centre)
        buckets.setdefault((axis, side) + cell, []).append(i)

    group_of = list(range(len(steps)))

    def root(i):
        while group_of[i] != i:
            group_of[i] = group_of[group_of[i]]
            i = group_of[i]
        return i

    for key, here in buckets.items():
        (axis, side), cell = key[:2], key[2:]
        near = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    near += buckets.get((axis, side, cell[0] + dx, cell[1] + dy, cell[2] + dz), ())
        for i in here:
            for j in near:
                if j <= i:
                    continue
                if all(abs(centres[i][k] - centres[j][k]) <= STEP_GROUP_DISTANCE for k in range(3)):
                    group_of[root(j)] = root(i)

    largest = {}
    for i, (xa, za, xb, zb, high, low, _visible, _side, _hole) in enumerate(steps):
        area = (abs(xb - xa) + abs(zb - za)) * (low - high)
        chosen = largest.get(root(i))
        if chosen is None or area > chosen[1]:
            largest[root(i)] = (i, area)
    return sorted(i for i, _area in largest.values())


class OverlayBuilder:
    """The overlay part of a level (`scene.Level` inherits it): every flag's
    groups, built only when its family is asked for."""

    def _terrain_overlays(self, t):
        """A terrain block's overlays (one piece, family terrain_overlays):
        the 0x1000 faces and the faces without collision."""
        invisible_walls, portal_areas = [], []
        vertices, faces, _stat = geo.read_terrain(self.sec4, t["offset"], invisible_walls, portal_areas)
        if invisible_walls:
            # the 0x1000 faces (flag 0x1000 faces): two triangles per quad, in
            # a separate group, semi-transparent and in a color the
            # game does not have; off by default, as in the game
            face_list = []
            for a, b, c, d in invisible_walls:
                face_list.append(geo.Face((a, b, c), None, None, [COLOR_FACES_1000] * 3, 0))
                face_list.append(geo.Face((a, c, d), None, None, [COLOR_FACES_1000] * 3, 0))
            self._add_faces(vertices, face_list, "faces_1000", pos=tuple(t["translation"]), counted=False)
            self.stat["walls_drawn"] = self.stat.get("walls_drawn", 0) + len(invisible_walls)
            # the area each portal leads to, on both sides of the quad
            sp = t["translation"]
            points, labels = [], []
            for quad, area in zip(invisible_walls, portal_areas):
                # the quad's corners come round the quad; a face of the
                # viewer is Z-ordered (0, 1, 3, 2 around)
                c = [tuple(vertices[h][k] + sp[k] for k in range(3)) for h in quad]
                for q in ([c[0], c[1], c[3], c[2]], [c[1], c[0], c[2], c[3]]):
                    uvs = flag_labels.label_uvs(q, max_height=AREA_LABEL_HEIGHT)
                    if uvs is None:
                        continue
                    first_idx = len(points)
                    points.extend(q)
                    labels.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3),
                                           LABEL_AREA + str(area), uvs, [(255, 255, 255)] * 4, None))
            if labels:
                self._add_faces(points, labels, "faces_1000_label", counted=False)
        # what you go through (flag No collision): the walkable faces with
        # no collision ground under them and the walls joined to them that
        # the sweep lets through, in white, 4 units up, with their triangle
        # edges in black over it. What is under them (death, damage, death
        # floor) is told by the zone flags, not here
        if self.collision_blocks:
            sp = t["translation"]
            corners_of = [[tuple(vertices[h][k] + sp[k] for k in range(3)) for h in vl.corners] for vl in faces]
            through = {i for i in range(len(faces))
                       if collision.no_collision_kind(self.collision_blocks, corners_of[i])}
            # the walls of such a piece (finding 298: the sweep stops only on
            # 0x7F, ground over 100 units higher, or leaving every block): a
            # vertical face the sweep lets through, joined face to face to a
            # top without collision. Only joined walls: the rule alone
            # missed its bars on the whole disc (298)
            by_vertex = {}
            for i, vl in enumerate(faces):
                for h in vl.corners:
                    by_vertex.setdefault(h, []).append(i)
            crossable = {}
            queue = sorted(through)
            while queue:
                i = queue.pop()
                for h in faces[i].corners:
                    for j in by_vertex[h]:
                        if j in through:
                            continue
                        if j not in crossable:
                            crossable[j] = collision.wall_crossable(self.collision_blocks, corners_of[j])
                        if crossable[j]:
                            through.add(j)
                            queue.append(j)
            if through:
                chosen = [faces[i] for i in sorted(through)]
                for category, draw_color, blend in (("no_collision", COLOR_NO_COLLISION, OVERLAY_BLEND),
                                                    ("no_collision_lines", COLOR_NO_COLLISION_EDGES, None)):
                    face_list = [geo.Face(vl.corners, None, None, [draw_color] * len(vl.corners), blend)
                                 for vl in chosen]
                    self._add_faces(vertices, face_list, category, pos=(sp[0], sp[1] - 4, sp[2]), counted=False)
                # the flag's name inside each face large enough to read it
                # (a face the block holds twice, 478 in L03A2: named once)
                labels, named = [], set()
                for i in sorted(through):
                    place = frozenset(corners_of[i])
                    if place in named:
                        continue
                    named.add(place)
                    uvs = flag_labels.label_uvs(corners_of[i])
                    if uvs is not None:
                        labels.append(geo.Face(faces[i].corners, LABEL_NO_COLLISION, uvs,
                                               [(255, 255, 255)] * len(uvs), None))
                if labels:
                    self._add_faces(vertices, labels, "no_collision_label", pos=(sp[0], sp[1] - 4, sp[2]),
                                    counted=False)
                self.stat["no_collision"] = self.stat.get("no_collision", 0) + len(chosen)

    def _object_collision_box(self, o, role, diagonal):
        """A placed object's collision box (one piece, family collision_boxes)."""
        rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
        scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
        self._add_collision_box(o, role, rot, scale_factor, diagonal)

    def _add_collision_box(self, o, role, rot, scale_factor, diagonal):
        """The object's collision box (flag Collision boxes), with the object's position,
        rotation and scale (montage.collision_box), as in the CTR
        viewer: sharp edges and a barely visible fill (blend
        B + F/4). The edges are degenerate triangles (a, b, b)
        drawn as lines: no diagonals. Touches neither bounds nor counters."""
        try:
            box = montage.collision_box(self.sec4, o["resources"], self.res, o, role=role)
        except Exception:  # noqa: BLE001
            return
        if not box:
            return
        x0, y0, z0, x1, y1, z1 = box
        # a box whose footprint is as large as the level (sky dome, sea)
        # would cover everything; one that is only tall (the star column of
        # L05A3C, 150 m) stays: it really is an invisible wall
        if max(abs(x1 - x0), abs(z1 - z0)) * scale_factor / geo.UNITS_PER_METER > 0.8 * diagonal:
            return
        kind = _box_kind(o)
        draw_color = {"SOLID": COLOR_COLLISION_BOXES, "PLATFORM": COLOR_PLATFORM_BOXES}.get(kind, COLOR_TOUCH_BOXES)
        # what hurts, on the box that is already there (finding 318): only the
        # edges change colour, bright when the object hurts in the state being
        # shown, dark when only in another of its states
        hurt = hazards.hazard(o, role)
        edge_color = {"now": COLOR_HURTS_NOW, "other": COLOR_HURTS_OTHER}.get(hurt[0]) if hurt else None
        self._add_box(box, "collision_boxes", draw_color, rot=rot, scale_factor=scale_factor,
                      pos=tuple(o["position"]), edge_color=edge_color,
                      edge_category="collision_boxes_hurt_lines" if edge_color else None,
                      blend=BOX_BLEND)
        self.stat["collision_boxes"] = self.stat.get("collision_boxes", 0) + 1
        self.stat["boxes_" + kind.lower()] = self.stat.get("boxes_" + kind.lower(), 0) + 1
        if hurt:
            self.stat["boxes_hurt_" + hurt[0]] = self.stat.get("boxes_hurt_" + hurt[0], 0) + 1

    def _clone_collision_box(self, template, n_template, n_parent, pos, rot, frame=None, n_frames=0,
                             counted=True, label=True):
        """The collision box of a clone (flag Collision boxes).

        A clone has no object number of its own, so its name says the template
        and whose it is: "T74 of #117 SOLID · HURT 1".
        `frame` puts it on one frame of the parent's animation, for a
        child held at the marker that follows its bone (finding 317).
        """
        try:
            box = montage.collision_box(self.sec4, template["resources"], self.res, template)
        except Exception:  # noqa: BLE001
            return
        if not box:
            return
        kind = _box_kind(template)
        draw_color = {"SOLID": COLOR_COLLISION_BOXES,
                      "PLATFORM": COLOR_PLATFORM_BOXES}.get(kind, COLOR_TOUCH_BOXES)
        hurt = hazards.hazard(template, self.pref["pose"].get(
            next((r for r in template["resources"] if r in self._models), None)))
        edge_color = {"now": COLOR_HURTS_NOW, "other": COLOR_HURTS_OTHER}.get(hurt[0]) if hurt else None
        scale_factor = (template["scale_factor"][0] / 4096.0) if template["scale_factor"] else 1.0
        anim = (("clone_box", n_template, n_parent), frame, n_frames) if frame is not None else None
        self._add_box(box, "collision_boxes", draw_color, rot=rot, scale_factor=scale_factor, pos=pos,
                      edge_color=edge_color, blend=BOX_BLEND, anim=anim,
                      edge_category="collision_boxes_hurt_lines" if edge_color else None)
        if counted:
            self.stat["clone_boxes"] = self.stat.get("clone_boxes", 0) + 1
        # the name floats above the middle of the box's top, as for an object
        x0, y0, z0, x1, y1, z1 = box
        top = min(y0, y1)
        middle = ((x0 + x1) / 2.0, top, (z0 + z1) / 2.0)
        if rot is not None:
            middle = tuple(sum(rot[i][k] * middle[k] for k in range(3)) for i in range(3))
        place = (middle[0] * scale_factor + pos[0], middle[1] * scale_factor + pos[1] - LABEL_LIFT,
                 middle[2] * scale_factor + pos[2])
        if not label:
            return
        self._clone_label(template, n_template, n_parent, place, frame, n_frames)

    def _clone_label(self, template, n_template, n_parent, place, frame=None, n_frames=0):
        """The name that floats above a clone's box: "T74 of #117 SOLID · HURT 1".

        Kept out of the pieces, like the objects' names: a piece taken from the
        cache would not build them again.
        """
        kind = _box_kind(template)
        hurt = hazards.hazard(template, self.pref["pose"].get(
            next((r for r in template["resources"] if r in self._models), None)))
        text = flag_labels.clone_label(n_template, n_parent, {kind}, [hurt] if hurt else [],
                                       bool((template["static_flags"] or (0, 0))[0] & HARD_BOX))
        if frame is None:
            self.box_labels.append({"pos": place, "text": text})
            return
        entry = self._label_frames.get((n_template, n_parent))
        if entry is None:
            entry = self._label_frames[(n_template, n_parent)] = {
                "text": text, "frames": [None] * n_frames, "pos": place}
            self.box_labels.append(entry)
        entry["frames"][frame] = place

    def _clone_box_place(self, template, pos, rot):
        """Where a clone's name floats: above the middle of its box's top, or
        None if the template has no box."""
        try:
            box = montage.collision_box(self.sec4, template["resources"], self.res, template)
        except Exception:  # noqa: BLE001
            return None
        if not box:
            return None
        scale_factor = (template["scale_factor"][0] / 4096.0) if template["scale_factor"] else 1.0
        x0, y0, z0, x1, y1, z1 = box
        middle = ((x0 + x1) / 2.0, min(y0, y1), (z0 + z1) / 2.0)
        if rot is not None:
            middle = tuple(sum(rot[i][k] * middle[k] for k in range(3)) for i in range(3))
        return (middle[0] * scale_factor + pos[0], middle[1] * scale_factor + pos[1] - LABEL_LIFT,
                middle[2] * scale_factor + pos[2])

    def _clone_labels(self):
        """The names of every clone box built in this level (scene: the jobs
        collected while the clones were built, in or out of the piece cache).
        A child held at the marker gets one place per frame of its parent's
        animation (finding 317)."""
        for role_id, n_parent, pos, rot, span in self._clone_label_jobs:
            template = self.templates.get(role_id)
            if template is None:
                continue
            n_template = self._idx.get(id(template))
            if n_template is None:
                continue
            if span is None:
                place = self._clone_box_place(template, pos, rot)
                if place is not None:
                    self._clone_label(template, n_template, n_parent, place)
                continue
            parent_ref = self.lvl["objects"][n_parent]
            bones = montage.marker_animation(self.sec4, parent_ref["resources"], self.res, parent_ref,
                                             role=self.pref["pose"].get(
                                                 next((r for r in parent_ref["resources"]
                                                       if r in self._models), None)))
            markers = montage.attach_points(self.sec4, parent_ref["resources"], self.res, parent_ref)
            if not bones or not markers:
                continue
            marker, first, last = markers[0], span[0], span[1]
            for f in range(len(bones)):
                alive = first <= f < last if first <= last else (f >= first or f < last)
                if not alive or marker not in bones[f]:
                    continue
                m, translation = bones[f][marker]
                if rot is not None:
                    matrix = tuple(tuple(sum(rot[i][k] * m[k][j] for k in range(3)) for j in range(3))
                                   for i in range(3))
                    offset = tuple(sum(rot[i][k] * translation[k] for k in range(3)) for i in range(3))
                else:
                    matrix, offset = m, translation
                place = self._clone_box_place(
                    template, (pos[0] + offset[0], pos[1] + offset[1], pos[2] + offset[2]), matrix)
                if place is not None:
                    self._clone_label(template, n_template, n_parent, place, f, len(bones))

    def _collision_box_labels(self, models, diagonal):
        """The names of the collision boxes, floating above each object
        (`Level.box_labels`, drawn every frame facing the camera:
        `drawing._draw_box_labels`): the object's number, SOLID, PLATFORM or
        TOUCH, HARD when the box stops the camera too, and what it does to Bugs
        when it hurts ("#109 SOLID · BLOW 1", in brackets when only another of
        its states hurts: finding 318). Boxes of several objects in the same
        place get one name (the one case on the disc, a SOLID and a TOUCH box:
        "SLD + TCH"). The same boxes as _object_collision_box."""
        places = {}
        for number, o in enumerate(self.lvl["objects"]):
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None or models[mid]["size"] <= 12:
                continue
            role = self.pref["pose"].get(mid)
            try:
                box = montage.collision_box(self.sec4, o["resources"], self.res, o, role=role)
            except Exception:  # noqa: BLE001
                continue
            if not box:
                continue
            scale_factor = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            x0, y0, z0, x1, y1, z1 = box
            if max(abs(x1 - x0), abs(z1 - z0)) * scale_factor / geo.UNITS_PER_METER > 0.8 * diagonal:
                continue
            rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
            px, py, pz = o["position"]
            top = min(y0, y1)             # Y down
            corners = []
            for x, y, z in ((x0, top, z0), (x0, top, z1), (x1, top, z0), (x1, top, z1)):
                if rot is not None:
                    x, y, z = (rot[0][0] * x + rot[0][1] * y + rot[0][2] * z,
                               rot[1][0] * x + rot[1][1] * y + rot[1][2] * z,
                               rot[2][0] * x + rot[2][1] * y + rot[2][2] * z)
                corners.append((x * scale_factor + px, y * scale_factor + py, z * scale_factor + pz))
            place = tuple(tuple(round(c, 1) for c in p) for p in corners)
            entry = places.setdefault(place, (corners, set(), [], [], [], []))
            entry[1].add(gates.ability_of(o) or _box_kind(o))
            entry[2].append(number)
            info = self.gates.get(number)
            if info is not None:
                if info["opened_by"]:
                    entry[5].append(flag_labels.gate_text(info["opened_by"]))
                elif self.gate_links == "all" and info["reacts_to"]:
                    entry[5].append(flag_labels.reacts_text(info["reacts_to"]))
                else:
                    entry[5].append(flag_labels.gate_text(()))
            hurt = hazards.hazard(o, role)
            if hurt:
                entry[3].append(hurt)
            if (o["static_flags"] or (0, 0))[0] & HARD_BOX:
                entry[4].append(number)
        self.box_labels = []
        for corners, kinds, numbers, hurts, hard, gate in places.values():
            # the point the name floats above: the middle of the box's top,
            # raised by LABEL_LIFT so it does not touch the box
            middle = tuple(sum(p[k] for p in corners) / len(corners) for k in range(3))
            self.box_labels.append({"pos": (middle[0], middle[1] - LABEL_LIFT, middle[2]),
                                    "text": flag_labels.box_label(numbers, kinds, hurts, bool(hard),
                                                                  gate[0] if gate else None)})

    def _gate_links(self):
        """The line from every switch to the gate it opens (flag Who opens
        what, findings 323 and 331): one line each, the same shape as the
        teleports', drawn through the geometry."""
        for number, info in sorted(self.gates.items()):
            gate_object = info["gate"]["object"]
            if not gate_object["position"]:
                continue
            opens = info["opened_by"]
            others = [n for n in info["reacts_to"] if n not in opens] if self.gate_links == "all" else []
            for switch, colour in ([(n, COLOR_GATE_LINK) for n in opens]
                                   + [(n, COLOR_REACTS_LINK) for n in others]):
                if switch >= len(self.lvl["objects"]):
                    continue
                other = self.lvl["objects"][switch]
                if not other["position"]:
                    continue
                self._link(tuple(other["position"]), tuple(gate_object["position"]),
                           "gate_links_lines", colour)
                self.stat["gate_links"] = self.stat.get("gate_links", 0) + 1

    def _add_box(self, box, category, draw_color, rot=None, scale_factor=1.0, pos=(0, 0, 0), filled=True,
                 edge_color=None, edge_category=None, blend=3, anim=None):
        """A box as in the CTR viewer: barely visible fill
        (blend B + F/4, group `category`) and sharp edges (group
        `category + "_lines"`: degenerate triangles (a, b, b) drawn as lines, no
        diagonals). `edge_color` paints only the edges and `edge_category` puts
        them in a group of their own (the red outline of what hurts).
        Touches neither bounds nor counters."""
        x0, y0, z0, x1, y1, z1 = box
        box_corners = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        self._add_hexahedron(box_corners, category, draw_color, rot, scale_factor, pos, filled, edge_color,
                             edge_category, blend, anim)

    def _add_hexahedron(self, box_corners, category, draw_color, rot=None, scale_factor=1.0, pos=(0, 0, 0),
                        filled=True, edge_color=None, edge_category=None, blend=3, anim=None):
        """As _add_box, from 8 corners (a turned zone): index = 4*ix + 2*iy + iz."""
        # each face with its 4 corners in Z order
        face_list = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 4, 5), (2, 3, 6, 7), (0, 2, 4, 6), (1, 3, 5, 7)]
        if filled:
            faces = [geo.Face(f, None, None, [draw_color] * 4, blend) for f in face_list]
            self._add_faces(box_corners, faces, category, rot=rot, scale_factor=scale_factor, pos=pos,
                            counted=False, anim=anim)
        edges = [(a, b) for a in range(8) for b in range(a + 1, 8)
                   if bin(a ^ b).count("1") == 1]          # 12: differ in one axis
        edge_faces = [geo.Face((a, b, b), None, None, [edge_color or draw_color] * 3, None) for a, b in edges]
        self._add_faces(box_corners, edge_faces, edge_category or (category + "_lines"), rot=rot,
                        scale_factor=scale_factor, pos=pos, counted=False,
                        anim=(anim[0] + ("lines",), anim[1], anim[2]) if anim else None)

    def _object_faces(self, diagonal):
        """The faces of the placed objects in game coordinates, in their
        starting pose (no animation, no clones): what the invisible-walls
        test counts as visible besides the terrain (a gate, a fence). Sky
        domes as large as the level are left out."""
        out = []
        models = {r["id"]: r for r in self.lvl["resources"] if r["data_kind"] == "model"}
        for o in self.lvl["objects"]:
            if not o["position"] or o["block_type"] == 0x08:
                continue
            mid = next((r for r in o["resources"] if r in models), None)
            if mid is None or models[mid]["size"] <= 12:
                continue
            try:
                role = self.pref["pose"].get(mid)
                trans = montage.transforms(self.sec4, o["resources"], self.res, o, {}, role=role)
                vertices, faces, _ = geo.read_model(self.sec4, models[mid]["offset"], trans)
            except Exception:  # noqa: BLE001
                continue
            if not faces:
                continue
            rot = geo._rotation_matrix(o["rotation"]) if o["rotation"] else None
            scale = (o["scale_factor"][0] / 4096.0) if o["scale_factor"] else 1.0
            px, py, pz = o["position"]
            pts = []
            for x, y, z in vertices:
                if rot is not None:
                    x, y, z = (rot[0][0] * x + rot[0][1] * y + rot[0][2] * z,
                               rot[1][0] * x + rot[1][1] * y + rot[1][2] * z,
                               rot[2][0] * x + rot[2][1] * y + rot[2][2] * z)
                pts.append((x * scale + px, y * scale + py, z * scale + pz))
            span = max(max(q[k] for q in pts) - min(q[k] for q in pts) for k in range(3)) / geo.UNITS_PER_METER
            if span > 0.8 * diagonal:
                continue
            out += [[pts[h] for h in vl.corners] for vl in faces]
        return out

    def _heightmap(self):
        """The overlays from the collision heightmap for the whole level:
        Ground (collision.surfaces), Hard walls and Invisible walls
        (collision.hard_walls, split by visibility) and Area boxes
        (collision.volumes)."""
        if not self.collision_blocks:
            return
        face_list = []
        for t in self.lvl["terrain"]:
            try:
                vs, vl_, _ = geo.read_terrain(self.sec4, t["offset"])
            except Exception:  # noqa: BLE001
                continue
            sp = t["translation"]
            face_list += [[tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners] for vl in vl_]
        covered, invisible, pixel = collision.surfaces(self.collision_blocks, collision.raster_faces(face_list))

        def add_planes(rects, category, draw_color, blend, lift=16):
            # 16 units over the heightmap (Y down): above the visible surface
            # it matches (median 7 units apart, finding 283), not under it
            corner_points, vl = [], []
            for x0, z0, x1, z1, y in rects:
                y -= lift
                first_idx = len(corner_points)
                corner_points += [(x0, y, z0), (x1, y, z0), (x0, y, z1), (x1, y, z1)]
                vl.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), None, None,
                                   [draw_color] * 4, blend))
            if vl:
                self._add_faces(corner_points, vl, category, counted=False)

        add_planes(covered, "covered_ground", COLOR_GROUND, 3)
        add_planes(invisible, "invisible_ground", COLOR_INVISIBLE_GROUND, 0)
        add_planes(pixel, "pixel", COLOR_PIXEL, None, lift=20)
        # a beam over every pixel, to find it from afar
        corner_points, vl = [], []
        for x0, z0, x1, z1, y in pixel:
            for (xa, za), (xb, zb) in (((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)),
                                       ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))):
                first_idx = len(corner_points)
                corner_points += [(xa, y, za), (xb, y, zb), (xa, y - 2000, za), (xb, y - 2000, zb)]
                vl.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), None, None,
                                   [COLOR_PIXEL] * 4, 0))
        if vl:
            self._add_faces(corner_points, vl, "pixel_beam", counted=False)
        # the heightmap's walls, each drawn only from the side where it acts
        # (findings 298, 299, 309) and named there; from the side where it
        # does not act, if it has one, the same name with OUTSIDE (the
        # "_outside" groups, shown with Walls: outside side)
        lo, hi = self.terrain_lo, self.terrain_hi
        diagonal = max(h - l for h, l in zip(hi, lo)) or 1.0
        vertical_heights = collision.raster_vertical(face_list + self._object_faces(diagonal))

        def facing(quad, look):
            # a Z-ordered quad is drawn from the side opposite to
            # (p1 - p0) x (p2 - p0) (ONE_SIDED): turn it to face `look`
            n = flag_labels._cross(flag_labels._sub(quad[1], quad[0]), flag_labels._sub(quad[2], quad[0]))
            return [quad[1], quad[0], quad[3], quad[2]] if flag_labels._dot(n, look) > 0 else quad

        def upright(xa, za, xb, zb, y_low, y_high):
            return [(xa, y_low, za), (xb, y_low, zb), (xa, y_high, za), (xb, y_high, zb)]

        def mount(category, quads, draw_color=None, blend=None, label=None, max_height=None, from_below=False):
            # one group of quads: a fill in `draw_color`, or the name `label`
            # on each quad large enough to read it
            points, faces = [], []
            for q in quads:
                uvs = None
                if label is not None:
                    uvs = flag_labels.label_uvs(q, from_below=from_below, max_height=max_height)
                    if uvs is None:
                        continue
                first_idx = len(points)
                points.extend(q)
                faces.append(geo.Face((first_idx, first_idx + 1, first_idx + 2, first_idx + 3), label, uvs,
                                      [draw_color or (255, 255, 255)] * 4, blend))
            if faces:
                self._add_faces(points, faces, category, counted=False)
            return len(faces)

        # hard walls (blue), and those with nothing drawn next to them,
        # neither terrain nor objects (magenta: the invisible walls). A 0x7F
        # sub-cell stops whoever enters it, and Bugs from every side (he is
        # put back if he ends up in one): drawn only from the free sub-cell,
        # no OUTSIDE side. The same panel from two blocks that share the edge
        # is drawn once; two facing each other (0x7F on both sides of the
        # block border) are none
        panels = list(dict.fromkeys(collision.hard_walls(self.collision_blocks, vertical_heights)))
        sides = {}
        for panel in panels:
            sides.setdefault(panel[:7], set()).add(panel[7])
        hard = [(facing(upright(xa, za, xb, zb, base, top), (fx, 0, fz)), visible)
                for xa, za, xb, zb, base, top, visible, (fx, fz) in panels
                if len(sides[(xa, za, xb, zb, base, top, visible)]) == 1]
        seen_quads = [q for q, v in hard if v]
        unseen_quads = [q for q, v in hard if not v]
        self.stat["hard_walls"] = mount("hard_walls", [q for q, _v in hard], COLOR_HARD_WALLS, 0)
        self.stat["invisible_walls"] = mount("invisible_walls", unseen_quads, COLOR_INVISIBLE_WALLS, 0)
        # a hard wall with nothing drawn is in both wall flags: HARD WALL,
        # INVISIBLE WALL or "INV + HRD", by which flags are on (SHOWN_WHEN)
        mount("hard_walls_label", seen_quads, label=LABEL_HARD_WALL)
        mount("hard_walls_label_unseen", unseen_quads, label=LABEL_HARD_WALL)
        mount("invisible_walls_label", unseen_quads, label=LABEL_INVISIBLE_WALL)
        mount("invisible_hard_walls_label", unseen_quads, label=LABEL_INVISIBLE_HARD_WALL)
        # the steps of more than 100 units with nothing drawn (flag
        # Invisible walls, magenta): a step stops you only going up, from its
        # low side (STEP WALL); from the high side you just go down (OUTSIDE).
        # They never share a panel with the hard walls
        # The steps from a 0x7E hole (the hole's ground is the slab's base:
        # a platform edge seen from the void) count too, but are mostly
        # noise: in their own groups, behind Walls: edges over holes
        all_steps = [s for s in collision.step_walls(self.collision_blocks, vertical_heights) if not s[6]]
        for prefix, steps in (("step_walls", [s for s in all_steps if not s[8]]),
                              ("hole_steps", [s for s in all_steps if s[8]])):
            low_side = [facing(upright(xa, za, xb, zb, low, high), (sx, 0, sz))
                        for xa, za, xb, zb, high, low, _v, (sx, sz), _hole in steps]
            high_side = [facing(q, (-sx, 0, -sz))
                         for q, (_xa, _za, _xb, _zb, _high, _low, _v, (sx, sz), _hole) in zip(low_side, steps)]
            self.stat[prefix] = mount(prefix, low_side, COLOR_INVISIBLE_WALLS, 0)
            mount(prefix + "_outside", high_side, COLOR_INVISIBLE_WALLS, 0)
            # one name per staircase: a name on every step of a flight came
            # out as a smudge (the stairs of L04E)
            named = _named_steps(steps)
            mount(prefix + "_label", [low_side[i] for i in named], label=LABEL_STEP_WALL)
            mount(prefix + "_outside_label", [high_side[i] for i in named], label=LABEL_STEP_WALL_OUTSIDE)
        # the collision volume of each mini area, as a box
        volumes = collision.volumes(self.collision_blocks)
        for x0, y0, z0, x1, y1, z1 in volumes:
            # edges only: a filled box this large would tint the whole view
            self._add_box((x0, y0, z0, x1, y1, z1), "area_boxes", COLOR_AREA_BOXES, filled=False)
        self.stat["area_boxes"] = len(volumes)
        # the area boxes: a side stops only who is inside (AREA WALL; from
        # outside AREA WALL · OUTSIDE), a slab top the head of a jump from
        # below (JUMP CEILING; from above JUMP CEILING · OUTSIDE)
        walls = list(dict.fromkeys(collision.area_walls(self.collision_blocks)))
        inside = [facing(upright(xa, za, xb, zb, base, top), (dx, 0, dz))
                  for xa, za, xb, zb, top, base, (dx, dz) in walls]
        outside = [facing(q, (-dx, 0, -dz)) for q, (*_rest, (dx, dz)) in zip(inside, walls)]
        mount("area_walls", inside, COLOR_AREA_FILL, 3)
        mount("area_walls_outside", outside, COLOR_AREA_FILL, 3)
        mount("area_walls_label", inside, label=LABEL_AREA_WALL, max_height=AREA_LABEL_HEIGHT)
        mount("area_walls_outside_label", outside, label=LABEL_AREA_WALL_OUTSIDE, max_height=AREA_LABEL_HEIGHT)
        self.stat["area_walls"] = len(walls)
        ceilings = list(dict.fromkeys(collision.jump_ceilings(self.collision_blocks)))
        # Y down: "below" is +Y
        below = [facing([(x0, y, z0), (x0, y, z1), (x1, y, z0), (x1, y, z1)], (0, 1, 0))
                 for x0, z0, x1, z1, y in ceilings]
        above = [facing(q, (0, -1, 0)) for q in below]
        mount("jump_ceilings", below, COLOR_AREA_FILL, 3)
        mount("jump_ceilings_outside", above, COLOR_AREA_FILL, 3)
        mount("jump_ceilings_label", below, label=LABEL_JUMP_CEILING, max_height=AREA_LABEL_HEIGHT, from_below=True)
        mount("jump_ceilings_outside_label", above, label=LABEL_JUMP_CEILING_OUTSIDE, max_height=AREA_LABEL_HEIGHT)
        self.stat["jump_ceilings"] = len(ceilings)
        self.stat["invisible_ground"] = len(invisible)
        self.stat["pixel"] = len(pixel)

    def _link(self, start, end, category, draw_color):
        """One line from `start` to `end`, ending exactly on the destination:
        a degenerate triangle (a, b, b) in a `_lines` group, drawn thicker than
        an edge and through the geometry. Touches neither bounds nor counters:
        a destination outside the terrain must not move the opening camera."""
        direction = flag_labels._sub(end, start)
        if flag_labels._dot(direction, direction) < 1.0:
            return
        self._add_faces([tuple(start), tuple(end)],
                        [geo.Face((0, 1, 1), None, None, [draw_color] * 3, None)],
                        category, counted=False)

    def _zone_text(self, names, goes, changes):
        """What is written on a zone: what it does, then where you come from
        and where it takes you, by NAME and not by file code: "LEVEL Wabbit on the run! 1", "ENTRANCE from
        Wabbit on the run! 2". The flag names are always English."""
        def shown(file_name):
            return levels.official_name(file_name, in_english=True) or file_name

        from_levels = []
        for _label, _point, rule in goes:
            for source in entrances.sources_of(rule, self.name, self.bze_folder,
                                               self.cache_folder):
                if shown(source) not in from_levels:
                    from_levels.append(shown(source))
        to_levels = []
        for levid in changes:
            destination = levels.file_of_levid(levid)
            entry = shown(destination) if destination else ("LEVID %d" % levid)
            if entry not in to_levels:
                to_levels.append(entry)
        tails = []
        if from_levels:
            tails.append("from " + " / ".join(from_levels))
        if to_levels:
            # "LEVEL Wabbit on the run! 1" alone; "to ..." only when the zone
            # also says where you came from, or the two would run together
            tails.append(("to " if from_levels else "") + " / ".join(to_levels))
        text = flag_labels.combined(names)
        return text + " " + " \u00b7 ".join(tails) if tails else text

    def _death_zones(self):
        """The zones (zones.py), each a box with its rotation, as the game
        tests it (zones.ZoneShape), and on its top face the names of all it
        does, from all its rules: DEATH (DEATH FLOOR when at least half the
        size of the terrain footprint: the sea, the abyss), DAMAGE (action
        0x48), and the ones that send somebody somewhere (finding 326):
        TELEPORT (Bugs goes to a point), RECOVER (the object inside the zone
        goes there: the recovery nets), RESTART (where Bugs comes back after
        a death) and LEVEL with the file it leads to. Several as "DTH + DMG"
        (flag_labels.combined).

        Flag Death and damage zones, red: the zones that kill or hurt; flag
        Teleport zones, purple: those that send somebody somewhere, each with
        a purple arrow from the zone to the point (a level change has no point
        in this file: it says the file instead). A zone that does both is in
        both flags, with one name."""
        lo, hi = self.terrain_lo, self.terrain_hi
        footprint = (hi[0] - lo[0]) * (hi[2] - lo[2]) * geo.UNITS_PER_METER ** 2
        for z in self.lvl["zones"]:
            hazard = zones.kills(z) or zones.hurts(z)
            goes = zones.destinations(z)
            changes = zones.level_changes(z)
            if not (hazard or goes or changes):
                continue
            shape = zones.shape_of(z)
            if shape is None:
                continue
            names = []
            if zones.kills(z):
                floor = footprint and shape.area >= zones.FLOOR_FRACTION * footprint
                names.append("DEATH FLOOR" if floor else "DEATH")
            if zones.hurts(z):
                names.append("DAMAGE")
            # one name per kind: a zone can have five restart points, one per
            # condition, and each gets its own arrow but not its own word
            names.extend(label for label, _point, _rule in goes if label not in names)
            if changes:
                names.append("LEVEL")
            corners = shape.corners()
            # a zone whose only destinations can never fire: grey, not purple
            dead_only = bool(goes) and not changes and all(
                label.startswith("DEAD") for label, _point, _rule in goes)
            categories = []
            if hazard:
                categories.append(("death_zones", COLOR_DEATH))
            if goes or changes:
                categories.append(("teleport_zones", COLOR_DEAD if dead_only else COLOR_TELEPORT))
            for category, draw_color in categories:
                self._add_hexahedron(corners, category, draw_color)
                self.stat[category] = self.stat.get(category, 0) + 1
            centre = tuple(sum(c[i] for c in corners) / 8.0 for i in range(3))
            for label, point, _rule in goes:
                dead = label.startswith("DEAD")
                self._link(centre, point, "teleport_arrows_lines",
                           COLOR_DEAD if dead else COLOR_TELEPORT)
                self.stat["teleport_arrows"] = self.stat.get("teleport_arrows", 0) + 1
                if dead:
                    self.stat["dead_teleports"] = self.stat.get("dead_teleports", 0) + 1
            # the top face (Y down: the corners with iy = 0), in Z order
            top = (0, 1, 4, 5)
            uvs = flag_labels.label_uvs([corners[i] for i in top])
            if uvs is not None:
                self._add_faces(corners, [geo.Face(top, "label:" + self._zone_text(names, goes, changes),
                                                   uvs, [(255, 255, 255)] * 4, None)],
                                categories[0][0] + "_label" if len(categories) == 1 else "shared_zones_label",
                                counted=False)
