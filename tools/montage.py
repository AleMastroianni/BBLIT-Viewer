"""Finds the rig and pose of an object and returns the transforms of its parts.

An object carries several resources (docs finding 6): the model (role 7), the rig
(role 4) and a series of animations. Each animation holds its own complete
opening pose (finding 34), so to assemble a static object any one of them
is enough — the rest pose is preferred when there is one.
"""

from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig as rigmod  # noqa: E402

# roles that count as a "static" animation, in order of preference:
# 8 is the default animation the player picks on its own, 11 is standing
PREFERRED_ROLES = (8, 11, 13)


END_MARKER = 0xFFF0   # ends the slot list of a state


def start_key(obj: dict | None) -> int | None:
    """The key of the step the object starts with: slot 0 of state 2 (or 1).

    An object's rules run only for the current step (docs finding
    192): for a freshly cloned template they are the ones with this key.
    """
    if not obj or not obj.get("states"):
        return None
    by_number = {t["number"]: t for t in obj["states"]}
    state_rec = by_number.get(2) or by_number.get(1)
    if state_rec is None:
        return None
    return next((x for x in state_rec["slots"][:1] if x != END_MARKER), None)


def start_role(obj: dict | None) -> int | None:
    """The role of the animation the game starts the object with.

    This is the chain of the type 14 object handler (`FUN_00440120`,
    docs finding 188): the initial state is 2, and 1 only if 2 is missing; slot
    0 of its playlist is a KEY (finding 89), looked up among the object's
    steps; the step found carries the role at +2 (finding 84).
    """
    if not obj or not obj.get("states"):
        return None
    by_number = {t["number"]: t for t in obj["states"]}
    state_rec = by_number.get(2) or by_number.get(1)
    if state_rec is None:
        return None
    lookup_key = next((x for x in state_rec["slots"][:1] if x != END_MARKER), None)
    if lookup_key is None:
        return None
    step = next((st for st in obj["steps"] if st["key"] == lookup_key), None)
    return step["role"] if step else None


def choose_sources(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None,
                 stat: dict | None = None, role: int | None = None) -> tuple:
    """Returns (rig resource, pose resource) for an object, or (None, None).

    With `obj` the pose is the one the game starts (see `start_role`);
    only if the chain does not lead to an animation of the object does it fall back
    on counting TRS records, and `stat` counts how often that happens.
    """
    rigs, poses = [], []
    for i in resources:
        r = res.get(i)
        if not r or r["data_kind"] != "stream" or r["offset"] is None:
            continue
        category = rigmod.is_stream(sec4, r["offset"])
        if category == 1:
            rigs.append(r)
        elif category in (2, 4):
            # type 4 is an animation too: same block chain, which
            # ends on the last byte in 205 streams out of 205 (L01A, MERLIN and the
            # three pier sections), and usually carries one bounding box (type 9)
            # per block. Discarding it left 35 pier objects without a pose.
            poses.append(r)
    if not rigs:
        return None, None

    # Not all streams open with a pose: some hold only "create part"
    # records and would leave the object stacked on the origin. So the one
    # that transforms the most parts is chosen, not the one with the nicest
    # role; the role is only a tie-breaker.
    def points(p):
        trs = 0
        for _anim_time, records in rigmod.read_blocks(sec4, p["offset"], p["size"], 2):
            trs += sum(1 for _d, category, _v, _l in records if category == rigmod.T_TRS)
        pref_score = len(PREFERRED_ROLES) - PREFERRED_ROLES.index(p["role"]) if p["role"] in PREFERRED_ROLES else 0
        return (trs, pref_score)

    if role is None:
        role = start_role(obj)       # forced `role`: a choice made by the user (preferences.py)
    pose = next((p for p in poses if p["role"] == role), None) if role is not None else None
    if pose is not None and points(pose)[0] == 0:
        pose = None       # the chain leads to an animation without transforms
    if stat is not None:
        stat["from_game" if pose is not None else "fallback"] =             stat.get("from_game" if pose is not None else "fallback", 0) + 1
    if pose is None:
        pose = max(poses, key=points) if poses else None
    if pose is not None and points(pose)[0] == 0:
        pose = None       # no usable pose: better to say so than to assemble at random
    return rigs[0], pose


def parts_of(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None,
              role: int | None = None):
    """The parts of the object's rig in its starting pose, or {} without a rig."""
    r, pose = choose_sources(sec4, resources, res, obj, role=role)
    if r is None:
        return {}
    return rigmod.construct(sec4, r["offset"], r["size"],
                       pose["offset"] if pose else None, pose["size"] if pose else 0)


def transforms(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None,
                   stat: dict | None = None, role: int | None = None):
    """Transforms by TMD part index, or None if the object has no rig."""
    r, pose = choose_sources(sec4, resources, res, obj, stat, role=role)
    if r is None:
        return None
    parts = rigmod.construct(sec4, r["offset"], r["size"],
                        pose["offset"] if pose else None, pose["size"] if pose else 0)
    if not parts:
        return None
    return rigmod.transforms(parts)


def animation(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None,
             role: int | None = None):
    """The transforms of every frame of the starting animation.

    Same choice of rig and pose as `transforms`; returns a list with
    one element per tick (finding 278), or None if the object has no rig or
    pose.
    """
    r, pose = choose_sources(sec4, resources, res, obj, role=role)
    if r is None or pose is None:
        return None
    frames = rigmod.animation(sec4, r["offset"], r["size"], pose["offset"], pose["size"])
    return frames or None


def collision_box(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None,
             role: int | None = None) -> tuple[int, ...] | None:
    """The object's collision box in the starting pose: the first
    type 9 record of the pose stream (the same one as `transforms`).

    Six `s16` in object space, (min x, min y, min z, max x, max y,
    max z) with Y pointing down: the game copies them to `object+0x48` and
    tests them rotated with the object (`FUN_004313a0`, docs finding 123). The box
    changes from one animation block to the next: here only the first.
    """
    _r, pose = choose_sources(sec4, resources, res, obj, role=role)
    if pose is None:
        return None
    for _anim_time, records in rigmod.read_blocks(sec4, pose["offset"], pose["size"], 1):
        for _d, category, _v, payload in records:
            if category == rigmod.T_BOX and len(payload) >= 12:
                return struct.unpack_from("<6h", payload, 0)
    return None


def attach_points(sec4: bytes, resources: list[int], res: dict, obj: dict | None = None) -> list[int]:
    """The parts marked by a type 0xA record in the starting animation,
    in the order they appear (finding 279).

    They are the points a clone starts from: the tip of the torch (part 3), the hand
    of the throwing pirate, the three spots of the blue chests.
    """
    _r, pose = choose_sources(sec4, resources, res, obj)
    if pose is None:
        return []
    output = []
    for _anim_time, records in rigmod.read_blocks(sec4, pose["offset"], pose["size"], 600):
        for part_id, category, _v, _l in records:
            if category == rigmod.T_CHAIN and part_id not in output:
                output.append(part_id)
    return output
