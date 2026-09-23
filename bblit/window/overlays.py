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
from game import walls  # noqa: E402
from game import zones  # noqa: E402

# the steps (flag Steps): a pink the game does not use
COLOR_STEP_WALLS = (255, 40, 200)
# the edges of a floor over the void (flag Steps -> edges over holes): a
# teal the game does not use, and the word EDGE on them, because the colour
# alone is never enough (the user is colour-blind). What the data says is
# that the heightmap has no ground on the free side (0x7E), so the rise the
# step rule measures there is not a rise between two floors: that is why it
# is neither a step nor a wall. What the game does at that rim is another
# question, and it has been tested in the game that the plank's own edge --
# the panel drawn here -- does stop him
COLOR_EDGE = (0, 220, 200)
# what you go through (flag No collision): white covering about 75%, with
# the triangle edges in black over it, so it stands out on light textures
COLOR_NO_COLLISION = (255, 255, 255)
COLOR_NO_COLLISION_EDGES = (0, 0, 0)
# the outline of the walls' panels and of the game's faces they colour
COLOR_WALL_EDGES = (0, 0, 0)
# the blend code of an overlay covering 75% (Viewer.on_draw, set_blend)
OVERLAY_BLEND = 4
# and of a collision box, so the model inside it can be seen (set_blend)
BOX_BLEND = 5
BOX_ALPHA = 0.30
# and of a wall (Hard walls, Steps): the fill nearly transparent, the edges
# and the names full, so a wall reads as a block and the level stays
# visible through it (chosen on the photos of the proposal).
# 25%, chosen with two measures in front of us.
# `tools/stripe_count.py`: the stripes that were two layers adding their
# alpha are gone at either fill now that the fills are stencilled, but on a
# framing whose own scene makes 14 boundaries, 25% adds 8 and 44% adds 64 --
# a stronger fill carries every faint boundary of the scene over the
# threshold. `tools/fill_contrast.py`: at 25% a tinted surface still moves
# 23-30 levels of luminance (of 255) away from the same surface untinted,
# about twice what it takes to read, so the fill is paler than the old two
# layers and still plain. If it ever has to be made stronger, the COLOUR goes
# lighter, not this: the alpha is what brings the boundaries back.
WALL_BLEND = 6
WALL_ALPHA = 0.25
# a wall's name no taller than this (game units, 2 m): a hard wall is as
# tall as its block, up to 250 m
# a collision box is filled at BOX_ALPHA so the model inside it can be seen
# (the user chose it on the photos: opaque buried the pirates, edges only
# lost the colour of the kind under the red outline of what hurts)
# overlays drawn on the terrain face itself, pulled forward in the depth
# test: the edges more than the fill, so they stay over it
PULLED_FORWARD = {"no_collision": (-1.0, -4.0), "no_collision_label": (-2.0, -8.0),
                  "no_collision_lines": (-2.0, -8.0),
                  # the names on the zone boxes' tops, over the box's own fill
                  "death_zones_label": (-2.0, -8.0), "teleport_zones_label": (-2.0, -8.0),
                  "faces_1000_label": (-2.0, -8.0), "shared_zones_label": (-2.0, -8.0)}
# the walls (Hard walls, Steps) are drawn on the game's faces (`_faces`) or
# on the collision plane a face may lie on: fills pulled a little, outlines
# and names more
WALL_PREFIXES = ("hard_walls", "invisible_walls",
                 "step_walls", "step_walls_covered", "hole_steps", "hole_steps_covered")
for _prefix in WALL_PREFIXES:
    for _suffix in ("", "_outside", "_faces", "_faces_outside"):
        PULLED_FORWARD[_prefix + _suffix] = (-1.0, -4.0)
    for _suffix in ("_label", "_outside_label", "_lines", "_all_lines"):
        PULLED_FORWARD[_prefix + _suffix] = (-2.0, -8.0)
# the texture with a flag's name, painted inside its faces (flag_labels.py):
# a texture id of its own; the names are always in English
LABEL_NO_COLLISION = "label:NO COLLISION"
LABEL_HARD_WALL = "label:HARD WALL"
LABEL_HARD_WALL_OUTSIDE = "label:HARD WALL · OUTSIDE"
LABEL_STEP_WALL = "label:STEP WALL"
LABEL_STEP_WALL_OUTSIDE = "label:STEP WALL · OUTSIDE"
LABEL_EDGE = "label:EDGE"
LABEL_EDGE_OUTSIDE = "label:EDGE · OUTSIDE"
LABEL_AREA_WALL = "label:AREA WALL"
LABEL_AREA_WALL_OUTSIDE = "label:AREA WALL · OUTSIDE"
LABEL_JUMP_CEILING = "label:JUMP CEILING"
LABEL_JUMP_CEILING_OUTSIDE = "label:JUMP CEILING · OUTSIDE"
# the area a portal leads to (flag Portals): "AREA 12"
LABEL_AREA = "label:AREA "
# the area boxes are large: their names no taller than this (game units, 2 m)
AREA_LABEL_HEIGHT = 256
WALL_LABEL_HEIGHT = 256
# a wall run this long or shorter (game units, 2 sub-cells) is a step of a
# curve: no outline at the corner where it meets another short run
SHORT_RUN = 80
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
# the hard walls (flag Hard walls), blue, the invisible ones too: which ones
# are invisible is the flag's "only the invisible ones" choice, not a colour
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
}
# the walls (OverlayBuilder._wall_overlays): Hard walls and Steps are
# three-way flags, "off", "all" or "unseen" (only the ones with nothing
# drawn), so their groups are chosen by value in SHOWN_WHEN below
WALL_SUFFIXES = ("", "_outside", "_faces", "_faces_outside", "_label", "_outside_label")
for _prefix in ("hard_walls", "invisible_walls"):
    for _suffix in WALL_SUFFIXES + ("_lines",):
        OVERLAYS[_prefix + _suffix] = "show_hard_walls"
for _prefix in ("step_walls", "step_walls_covered", "hole_steps", "hole_steps_covered"):
    for _suffix in WALL_SUFFIXES:
        OVERLAYS[_prefix + _suffix] = "show_steps"
for _prefix in ("step_walls", "hole_steps"):
    OVERLAYS[_prefix + "_lines"] = OVERLAYS[_prefix + "_all_lines"] = "show_steps"
# the overlay families: each is built, as pieces of its own, only when one of
# its flags is on, so a level opened with the flags off skips them all (the
# heightmap alone was 80-93% of the first build of a level: L03A 4.0 of 4.9 s)
FAMILIES = {
    "terrain_overlays": ("show_faces_1000", "show_no_collision"),
    "heightmap": ("show_ground", "show_hard_walls", "show_steps", "show_area_boxes"),
    "zones": ("show_death_zones", "show_teleport_zones"),
    "collision_boxes": ("show_collision_boxes", "show_gate_links"),
}
assert set(OVERLAYS.values()) == {a for flags in FAMILIES.values() for a in flags}
# groups whose visibility depends on more than their own flag:
# (all of these on, at least one of these on, none of these on). A name
# alone means the flag is on; "name=value" means the flag has that value
# (Hard walls and Steps: "all" or "unseen"). Written for the flag names
# that merge: the same place in two flags gets one name instead of two
# texts over each other
SHOWN_WHEN = {
    # a zone that kills and teleports is in both zone flags: one name
    "shared_zones_label": ((), ("show_death_zones", "show_teleport_zones"), ()),
}
# the walls: `hard_walls*` with Hard walls "all", `invisible_walls*` with
# "all" or "unseen"; the outline of everything with "all", of the invisible
# ones alone with "unseen"; the `_outside` groups also need Walls -> Outside
# side. The steps the same, with the covered ones only in "all" and the
# steps seen from a hole also behind Edges over holes
for _prefix, _flag, _seen in (("hard_walls", "show_hard_walls", True), ("invisible_walls", "show_hard_walls", False),
                              ("step_walls_covered", "show_steps", True), ("step_walls", "show_steps", False),
                              ("hole_steps_covered", "show_steps", True), ("hole_steps", "show_steps", False)):
    _hole = ("show_hole_steps",) if _prefix.startswith("hole") else ()
    _when = ((_flag + "=all",) + _hole, ()) if _seen else (_hole, (_flag + "=all", _flag + "=unseen"))
    for _suffix in WALL_SUFFIXES:
        _outside = ("show_walls_outside",) if "outside" in _suffix else ()
        SHOWN_WHEN[_prefix + _suffix] = (_when[0] + _outside, _when[1], ())
SHOWN_WHEN["hard_walls_lines"] = (("show_hard_walls=all",), (), ())
SHOWN_WHEN["invisible_walls_lines"] = (("show_hard_walls=unseen",), (), ())
for _prefix in ("step_walls", "hole_steps"):
    _hole = ("show_hole_steps",) if _prefix.startswith("hole") else ()
    SHOWN_WHEN[_prefix + "_all_lines"] = (("show_steps=all",) + _hole, (), ())
    SHOWN_WHEN[_prefix + "_lines"] = (("show_steps=unseen",) + _hole, (), ())
# the groups drawn with a thicker line (the red outline of what hurts, over
# the box's own edge in the same place)
THICK_LINES = {"collision_boxes_hurt_lines", "teleport_arrows_lines", "gate_links_lines"}
# drawn through the geometry (no depth test): a link's line, so it can be
# followed behind a wall to where it goes
THROUGH_WALLS = {"teleport_arrows_lines", "gate_links_lines"}
THICK_LINE_WIDTH = 4.0
# names written on both sides of a wall, each drawn only from its own side,
# so neither reads mirrored
ONE_SIDED = {"faces_1000_label",
             # the area walls stop you only from inside, a jump ceiling only from below:
             # each is drawn only from the side where it acts
             "area_walls", "area_walls_label", "jump_ceilings", "jump_ceilings_label",
             "area_walls_outside", "area_walls_outside_label", "jump_ceilings_outside",
             "jump_ceilings_outside_label"}
# the walls: fills, coloured faces and names each from its own side (the
# outlines from both)
for _prefix in WALL_PREFIXES:
    for _suffix in WALL_SUFFIXES:
        ONE_SIDED.add(_prefix + _suffix)
# groups that also need a second setting on: the outside side of the area
# boxes (Flags -> Area boxes: outside side, on at every start)
# the sides where a wall does not stop you: with Walls: outside side (on at every start)
for _c in ("area_walls_outside", "area_walls_outside_label", "jump_ceilings_outside",
           "jump_ceilings_outside_label"):
    SHOWN_WHEN[_c] = (("show_area_boxes", "show_walls_outside"), (), ())


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
                            if crossable[j] is None:
                                # neither a floor nor a wall (a steep slope, a
                                # short wall, an overhang, a ceiling): the rim
                                # under the mushroom's top in Wabbit on the
                                # run! 2 stayed brown while Bugs fell through
                                crossable[j] = collision.joined_face_crossable(self.collision_blocks,
                                                                               corners_of[j])
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

    def _object_faces(self, diagonal, solid_only=False):
        """The faces of the placed objects in game coordinates, in their
        starting pose (no animation, no clones): what the invisible-walls
        test counts as visible besides the terrain (a gate, a fence). Sky
        domes as large as the level are left out. With `solid_only` the
        cut-out and semi-transparent faces (ropes, leaves) are left out too:
        they do not hide a wall."""
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
            out += [[pts[h] for h in vl.corners] for vl in faces
                    if not (solid_only and (vl.blend is not None or vl.tex_id in self.cut_outs))]
        return out

    def _heightmap(self):
        """The overlays from the collision heightmap for the whole level:
        Ground (collision.surfaces), Hard walls and Invisible walls
        (collision.hard_walls, split by visibility) and Area boxes
        (collision.volumes)."""
        if not self.collision_blocks:
            return
        face_list, solid_faces = [], []
        for t in self.lvl["terrain"]:
            try:
                vs, vl_, _ = geo.read_terrain(self.sec4, t["offset"])
            except Exception:  # noqa: BLE001
                continue
            sp = t["translation"]
            for vl in vl_:
                corners = [tuple(vs[h][k] + sp[k] for k in range(3)) for h in vl.corners]
                face_list.append(corners)
                # what hides a wall: an opaque face. A cut-out or blended one
                # (the ropes of the boat in Era selector) does not, and used
                # to open a gap in the STEP WALL in front of the mast where
                # the game stops you (tools/skipped_steps.py)
                if vl.blend is None and vl.tex_id not in self.cut_outs:
                    solid_faces.append(corners)
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
        object_faces = self._object_faces(diagonal, solid_only=True)
        vertical_heights = collision.raster_vertical(solid_faces + object_faces)

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

        # the hard walls and the steps, on the game's own faces where it has
        # one on the wall, panels where it has none (walls.py)
        self._wall_overlays(walls.ParallelFaces(solid_faces + object_faces), vertical_heights)
        # the collision volume of each mini area, as a box
        volumes = collision.volumes(self.collision_blocks)
        for x0, y0, z0, x1, y1, z1 in volumes:
            # edges only: a filled box this large would tint the whole view
            self._add_box((x0, y0, z0, x1, y1, z1), "area_boxes", COLOR_AREA_BOXES, filled=False)
        self.stat["area_boxes"] = len(volumes)
        # the area boxes: a side stops only who is inside (AREA WALL; from
        # outside AREA WALL · OUTSIDE), a slab top the head of a jump from
        # below (JUMP CEILING; from above JUMP CEILING · OUTSIDE)
        area_wall_runs = list(dict.fromkeys(collision.area_walls(self.collision_blocks)))
        inside = [facing(upright(xa, za, xb, zb, base, top), (dx, 0, dz))
                  for xa, za, xb, zb, top, base, (dx, dz) in area_wall_runs]
        outside = [facing(q, (-dx, 0, -dz)) for q, (*_rest, (dx, dz)) in zip(inside, area_wall_runs)]
        mount("area_walls", inside, COLOR_AREA_FILL, 3)
        mount("area_walls_outside", outside, COLOR_AREA_FILL, 3)
        mount("area_walls_label", inside, label=LABEL_AREA_WALL, max_height=AREA_LABEL_HEIGHT)
        mount("area_walls_outside_label", outside, label=LABEL_AREA_WALL_OUTSIDE, max_height=AREA_LABEL_HEIGHT)
        self.stat["area_walls"] = len(area_wall_runs)
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

    def _wall_overlays(self, parallel, vertical_heights):
        """The hard walls (flag Hard walls) and the steps (flag Steps) of the
        heightmap: a hard wall from the floor to the ceiling of ITS block,
        where the game stops (three
        recordings), and every wall drawn like No collision: where the game
        has a face on the wall, that face coloured and clipped to the run,
        with its outline; where it has none, a panel; the fill nearly
        transparent (WALL_ALPHA), edges and names full. One outline goes
        round the whole uncovered region of a plane (walls.WallCover), not
        one per run.

        Groups, by run: `hard_walls*` for the hard walls a face shows,
        `invisible_walls*` for those with nothing drawn (Hard walls: only
        the invisible ones), each with `_faces` (the game's faces coloured),
        `_label`, and the same from the side where the wall does not stop
        you (`_outside`, `_faces_outside`, `_outside_label`: Walls ->
        Outside side); `hard_walls_lines` the outline of everything,
        `invisible_walls_lines` of the invisible ones alone. The steps the
        same, in `step_walls` (nothing drawn over them), `step_walls_covered`
        (an opaque face covers them: Steps: all), `hole_steps` and
        `hole_steps_covered` (seen from a 0x7E hole: Edges over holes), with
        `step_walls_lines` / `hole_steps_lines` the outline of the uncovered
        ones and `_all_lines` of all.
        """
        pending = {}

        def put(category, ring, tex_id=None, uvs=None, colour=(255, 255, 255), blend=None):
            pts, faces = pending.setdefault(category, ([], []))
            first = len(pts)
            pts.extend(ring)
            faces.append(geo.Face(tuple(range(first, first + len(ring))), tex_id, uvs, [colour] * len(ring), blend))

        def put_line(category, a, b):
            pts, faces = pending.setdefault(category, ([], []))
            first = len(pts)
            pts.extend([a, b])
            faces.append(geo.Face((first, first + 1, first + 1), None, None, [COLOR_WALL_EDGES] * 3, None))

        def oriented(ring, look):
            # drawn from the side opposite to (p1 - p0) x (p2 - p0) (ONE_SIDED)
            n = flag_labels._cross(flag_labels._sub(ring[1], ring[0]), flag_labels._sub(ring[2], ring[0]))
            return ring[::-1] if flag_labels._dot(n, look) > 0 else ring

        def z_order(ring):
            # a quad for geo.Face is Z-ordered; anything else is a fan
            return [ring[0], ring[1], ring[3], ring[2]] if len(ring) == 4 else list(ring)

        def rect_ring(cover, a0, a1, y_top, y_base):
            return [cover.to_3d((a0, y_base)), cover.to_3d((a1, y_base)),
                    cover.to_3d((a1, y_top)), cover.to_3d((a0, y_top))]

        def label(category, ring, look, text, max_height=None):
            quad = z_order(oriented(ring, look))
            uvs = flag_labels.label_uvs(quad, max_height=max_height)
            if uvs is not None:
                put(category, quad, tex_id=text, uvs=uvs)

        def fill_and_faces(cover, wanted, prefix, colour, look, back, lines_all, lines_unseen, unseen,
                           face_label):
            """The panels and the coloured faces of the runs `wanted`, from
            both sides; their outlines into `lines_all` and, for the runs
            with nothing drawn, into `lines_unseen`."""
            n_panels = 0
            for a0, a1, y_top, y_base in cover.panels(wanted):
                ring = rect_ring(cover, a0, a1, y_top, y_base)
                put(prefix, z_order(oriented(ring, look)), colour=colour, blend=WALL_BLEND)
                put(prefix + "_outside", z_order(oriented(ring, back)), colour=colour, blend=WALL_BLEND)
                n_panels += 1
            n_faces = 0
            self.stat["wall_runs_with_faces"] = (self.stat.get("wall_runs_with_faces", 0)
                                                 + len({r for r, _piece in cover.clipped
                                                        if wanted(cover.runs[r][4])}))
            for piece, key in cover.face_pieces(wanted):
                # on the game's face itself: every corner carries its own
                # distance from the plane, so a slanted face keeps its slant
                ring = [cover.to_3d(p) for p in piece]
                put(prefix + "_faces", z_order(oriented(ring, look)), colour=colour, blend=WALL_BLEND)
                put(prefix + "_faces_outside", z_order(oriented(ring, back)), colour=colour, blend=WALL_BLEND)
                slant = max(p[2] for p in piece) - min(p[2] for p in piece)
                if slant > walls.FLATNESS:
                    self.stat["wall_faces_slanted"] = self.stat.get("wall_faces_slanted", 0) + 1
                for i in range(len(ring)):
                    put_line(lines_all, ring[i - 1], ring[i])
                    if unseen(key):
                        put_line(lines_unseen, ring[i - 1], ring[i])
                # the name goes on a face lying on the plane: on a slanted
                # one a rectangle built from the bounding box would float off it
                if face_label is not None and slant <= walls.FLATNESS and walls.is_rectangle(piece):
                    d = sum(p[2] for p in piece) / len(piece)
                    a0, a1 = min(p[0] for p in piece), max(p[0] for p in piece)
                    y_top, y_base = min(p[1] for p in piece), max(p[1] for p in piece)
                    box = [cover.to_3d(p, d) for p in ((a0, y_base), (a1, y_base), (a1, y_top), (a0, y_top))]
                    label(prefix + "_label", box, look, face_label[0], WALL_LABEL_HEIGHT)
                    label(prefix + "_outside_label", box, back, face_label[1], WALL_LABEL_HEIGHT)
                n_faces += 1
            return n_panels, n_faces

        def keep_vertical(cover, a, y_high, y_low, ends):
            """Whether a vertical outline line at `a` is drawn: always at a
            free end of a wall; at a corner where another wall meets it only
            when both are longer than SHORT_RUN. On a curved wall the
            collision grid turns every sub-cell, and a line at every corner
            made a curtain (seen on the photos of the proposal)."""
            here = [length for a0, a1, length in cover.run_ends if a in (a0, a1)]
            if not here:
                return True         # inside the region: a face's edge next to a panel
            x, _y, z = cover.to_3d((a, y_low))
            others = [length for length, top, base, owner in ends.get((x, z), ())
                      if owner is not cover and top < y_low and base > y_high]
            return not others or (min(here) > SHORT_RUN and min(others) > SHORT_RUN)

        def register_ends(covers, ends):
            for cover in covers:
                cover.run_ends = []
                for a0, a1, y_top, y_base, _key in cover.runs:
                    cover.run_ends.append((a0, a1, a1 - a0))
                    for a in (a0, a1):
                        x, _y, z = cover.to_3d((a, y_base))
                        ends.setdefault((x, z), []).append((a1 - a0, y_top, y_base, cover))

        def outlines(cover, ends, categories):
            for category, wanted in categories:
                for a, b in cover.outline(wanted):
                    if a[0] == b[0] and not keep_vertical(cover, a[0], min(a[1], b[1]), max(a[1], b[1]), ends):
                        continue
                    put_line(category, cover.to_3d(a), cover.to_3d(b))

        # --- hard walls: drawn from the free sub-cell (finding 309: the
        # sweep stops whoever enters a 0x7F sub-cell, Bugs is put back if he
        # ends up in one) and, with Outside side, from the 0x7F side, where
        # nothing stops you. The same run from two blocks that share the
        # edge is drawn once; two facing each other (0x7F on both sides of
        # the block border) are none. Told apart by the ground next to them,
        # as before the walls went up to the block's ceiling, so the set of
        # runs is the one the old flag drew (tools/wall_flag_proof.py)
        panels = list(dict.fromkeys(collision.hard_walls(self.collision_blocks, vertical_heights)))
        sides = {}
        for panel in panels:
            sides.setdefault(panel[:4] + panel[6:7] + panel[8:10], set()).add(panel[7])
        hard = [p for p in panels if len(sides[p[:4] + p[6:7] + p[8:10]]) == 1]
        covers = {}
        for xa, za, xb, zb, base, top, visible, (fx, fz), _g_low, g_high in hard:
            axis = "x" if xa == xb else "z"
            plane = xa if axis == "x" else za
            a0, a1 = (min(za, zb), max(za, zb)) if axis == "x" else (min(xa, xb), max(xa, xb))
            covers.setdefault((axis, plane, base, top, (fx, fz)), []).append((a0, a1, top, base, (visible, g_high)))
        self.stat["hard_walls"], self.stat["invisible_walls"] = len(hard), sum(1 for p in hard if not p[6])
        self.stat["wall_panels"] = self.stat["wall_faces"] = 0
        hard_covers = [(walls.WallCover(axis, plane, runs, parallel, free=fx if axis == "x" else fz),
                        (fx, 0, fz), (-fx, 0, -fz))
                       for (axis, plane, _base, _top, (fx, fz)), runs in covers.items()]
        # what the selector (Alt+click, picking.py) reads back: one plain
        # record per run. It rides in the piece cache with the geometry
        # (`self._pieces`), or a level mounted from the cache would have no
        # records at all and the card would only name the group
        self.wall_picks = []
        for (axis, plane, c_base, c_top, (fx, fz)), runs in covers.items():
            for r, (a0, a1, y_top, y_base, (visible, _g_high)) in enumerate(runs):
                self.wall_picks.append(dict(group="hard_walls" if visible else "invisible_walls",
                                            kind="hard", axis=axis, plane=plane, a0=a0, a1=a1,
                                            y_top=y_top, y_base=y_base, visible=bool(visible),
                                            hole=False, free=(fx, fz), floor=c_base, ceiling=c_top))
        ends = {}
        register_ends([c[0] for c in hard_covers], ends)
        for cover, look, back in hard_covers:
            runs = cover.runs
            for visible in (True, False):
                prefix = "hard_walls" if visible else "invisible_walls"
                wanted = (lambda key, v=visible: key[0] == v)
                n_panels, n_faces = fill_and_faces(
                    cover, wanted, prefix, COLOR_HARD_WALLS, look, back, "hard_walls_lines",
                    "invisible_walls_lines", lambda key: not key[0], (LABEL_HARD_WALL, LABEL_HARD_WALL_OUTSIDE))
                self.stat["wall_panels"] += n_panels
                self.stat["wall_faces"] += n_faces
            # the name of a panel: in the band just over the highest ground
            # next to its run, WALL_LABEL_HEIGHT tall, where the panel
            # reaches it (a block can be 250 m tall: a name centred on the
            # panel would float unreadable; a strip of panel over a coloured
            # face gets none, the face has the name)
            for visible in (True, False):
                prefix = "hard_walls" if visible else "invisible_walls"
                for a0, a1, y_top, y_base in cover.panels(lambda key, v=visible: key[0] == v):
                    r = cover.cells.get((int(round(a0 / walls.CELL)), int((y_base - walls.EPS) // walls.CELL)))
                    if r is None:
                        r = next((rr for (i, _j), rr in cover.cells.items() if i == int(round(a0 / walls.CELL))), None)
                    if r is None:
                        continue
                    g_high = runs[r][4][1]
                    low = min(y_base, g_high - 16)
                    high = max(y_top, low - WALL_LABEL_HEIGHT)
                    if low - high < flag_labels.MIN_HEIGHT:
                        continue
                    ring = rect_ring(cover, a0, a1, high, low)
                    label(prefix + "_label", ring, look, LABEL_HARD_WALL, WALL_LABEL_HEIGHT)
                    label(prefix + "_outside_label", ring, back, LABEL_HARD_WALL_OUTSIDE, WALL_LABEL_HEIGHT)
            outlines(cover, ends, (("hard_walls_lines", None), ("invisible_walls_lines", lambda key: not key[0])))
        # --- the steps of more than 100 units (findings 298, 309): a step
        # stops you only going up, from its low side (STEP WALL); from the
        # high side you just go down (OUTSIDE). A step stops you whether or
        # not something is drawn over it, so every step is drawn whole
        # (around the palisade of the Pirates in Era selector the game's step
        # goes all the way round); those an opaque
        # face covers are the "_covered" groups (Steps: all), the steps from
        # a 0x7E hole (the hole's ground is the slab's base: a platform edge
        # seen from the void) are mostly noise and stay behind Edges over
        # holes. One name per staircase (_named_steps): a name on every step
        # of a flight came out as a smudge (the stairs of L04E)
        all_steps = collision.step_walls(self.collision_blocks, vertical_heights)
        named = set(_named_steps(all_steps))
        covers = {}
        for i, (xa, za, xb, zb, high, low, visible, (sx, sz), hole) in enumerate(all_steps):
            axis = "x" if xa == xb else "z"
            plane = xa if axis == "x" else za
            a0, a1 = (min(za, zb), max(za, zb)) if axis == "x" else (min(xa, xb), max(xa, xb))
            # the class is the DROP, not the hole byte: 101 to 383 units he
            # clears with a jump, so it is a step;
            # over 383 it just stops him, so it is a wall, drawn and named as
            # one. The run itself is untouched: only its colour, its name and
            # the flag that shows it change
            covers.setdefault((axis, plane, (sx, sz), hole), []).append(
                (a0, a1, high, low, (visible, i, not hole and low - high > collision.JUMP_HEIGHT)))
        for prefix in ("step_walls", "step_walls_covered", "hole_steps", "hole_steps_covered"):
            self.stat[prefix] = 0
        self.stat["drop_walls"] = 0
        step_covers = [(walls.WallCover(axis, plane, runs, parallel, free=sx if axis == "x" else sz),
                        (sx, 0, sz), (-sx, 0, -sz), hole)
                       for (axis, plane, (sx, sz), hole), runs in covers.items()]
        for (axis, plane, (sx, sz), hole), runs in covers.items():
            base_name = "hole_steps" if hole else "step_walls"
            for r, (a0, a1, y_top, y_base, (visible, _i, is_wall)) in enumerate(runs):
                group = (("hard_walls" if visible else "invisible_walls") if is_wall
                         else base_name + ("_covered" if visible else ""))
                self.wall_picks.append(dict(group=group, kind="drop" if is_wall else "step",
                                            axis=axis, plane=plane, a0=a0, a1=a1,
                                            y_top=y_top, y_base=y_base, visible=bool(visible),
                                            hole=bool(hole), free=(sx, sz), floor=None, ceiling=None))
        ends = {}
        register_ends([c[0] for c in step_covers], ends)
        for cover, look, back, hole in step_covers:
            runs = cover.runs
            base_name = "hole_steps" if hole else "step_walls"
            for visible in (True, False):
                # the steps he can clear: pink, STEP WALL. An edge over the
                # void: teal, EDGE, and never a wall whatever its drop
                prefix = base_name + ("_covered" if visible else "")
                self.stat[prefix] += sum(1 for run in runs if run[4][0] == visible and not run[4][2])
                fill_and_faces(cover, (lambda key, v=visible: key[0] == v and not key[2]),
                               prefix, COLOR_EDGE if hole else COLOR_STEP_WALLS, look, back,
                               base_name + "_all_lines", base_name + "_lines",
                               lambda key: not key[0], None)
                # and the drops he cannot: blue, HARD WALL, behind Hard walls,
                # in the very groups of the walls
                wall_prefix = "hard_walls" if visible else "invisible_walls"
                self.stat["drop_walls"] += sum(1 for run in runs if run[4][0] == visible and run[4][2])
                fill_and_faces(cover, (lambda key, v=visible: key[0] == v and key[2]),
                               wall_prefix, COLOR_HARD_WALLS, look, back,
                               "hard_walls_lines", "invisible_walls_lines", lambda key: not key[0],
                               (LABEL_HARD_WALL, LABEL_HARD_WALL_OUTSIDE))
            for a0, a1, y_top, y_base, (visible, i, is_wall) in runs:
                if is_wall:
                    # a drop's name in a band over its low side, as a hard
                    # wall's: a 12 m drop named in the middle floats
                    # unreadable. One name per stretch, like the steps
                    # (_named_steps): a name on every run of a dock edge came
                    # out as a row of small HARD WALLs
                    if i not in named:
                        continue
                    prefix = "hard_walls" if visible else "invisible_walls"
                    high = max(y_top, y_base - WALL_LABEL_HEIGHT)
                    if y_base - high < flag_labels.MIN_HEIGHT:
                        continue
                    ring = rect_ring(cover, a0, a1, high, y_base)
                    label(prefix + "_label", ring, look, LABEL_HARD_WALL, WALL_LABEL_HEIGHT)
                    label(prefix + "_outside_label", ring, back, LABEL_HARD_WALL_OUTSIDE, WALL_LABEL_HEIGHT)
                    continue
                if i not in named:
                    continue
                prefix = base_name + ("_covered" if visible else "")
                ring = rect_ring(cover, a0, a1, y_top, y_base)
                name, name_out = ((LABEL_EDGE, LABEL_EDGE_OUTSIDE) if hole
                                  else (LABEL_STEP_WALL, LABEL_STEP_WALL_OUTSIDE))
                label(prefix + "_label", ring, look, name)
                label(prefix + "_outside_label", ring, back, name_out)
            outlines(cover, ends, ((base_name + "_all_lines", lambda key: not key[2]),
                                   (base_name + "_lines", lambda key: not key[0] and not key[2]),
                                   ("hard_walls_lines", lambda key: key[2]),
                                   ("invisible_walls_lines", lambda key: not key[0] and key[2])))
        self.stat["step_walls"] += self.stat["step_walls_covered"]
        self.stat["hole_steps"] += self.stat["hole_steps_covered"]
        # the records ride in the piece cache: a level mounted from disk gets
        # them back without rebuilding the walls
        self._pieces[("wall_picks",)] = self.wall_picks
        for category, (pts, faces) in pending.items():
            self._add_faces(pts, faces, category, counted=False)

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
