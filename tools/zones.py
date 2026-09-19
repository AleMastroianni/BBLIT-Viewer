"""The zones (load script block 0x09) that kill or recover the
player: for the viewer's "Death zones" and "Death floor" flags.

A zone is a box (finding 103): origin (x, y, z), extent
in X and in Z, and in Y from its floor up to "Y limit" higher up (the game's
Y grows downwards; the limit is negative). Its rules (0x33)
carry an effects word at +16 (finding 169):

* 0x200000: the player goes into a series of animations and the lives
  counter drops to zero: death, and you restart from the checkpoint;
* 0x40000000: teleport to the three parameters: the zone catches you and puts
  you back at a fixed point, like CTR's mask pickup (the recovery net of
  L04A2: six zones over the whole floor, all towards (7900, -15520, 5000)).

On the menu levels: 165 zones with 0x200000 in 46 levels, 15 with
teleport in 4. The rules' conditions are not evaluated: you see
where the zone CAN act. Only one death zone is rotated: the rotation
(finding 105) is not applied yet.
"""

from __future__ import annotations

DEATH = 0x200000
TELEPORT = 0x40000000
# a zone covering at least this fraction of the ground's plan is the
# level's "death floor" (the sea of L03A, the abyss of L05A5)
FLOOR_FRACTION = 0.5


def kind_of(z: dict) -> str | None:
    """"death" or "teleport" or None."""
    effects = 0
    for r in z.get("rules", []):
        effects |= r["effect"]
    if effects & DEATH:
        return "death"
    if effects & TELEPORT:
        return "teleport"
    return None


def zone_box(z: dict) -> tuple[int, int, int, int, int, int] | None:
    """(x0, y0, z0, x1, y1, z1) in game coordinates, or None if the zone
    has no origin or size, or has a negative extent (a disabled zone:
    the game's test `0 <= x <= extent` never finds it)."""
    if not z.get("origin") or not z.get("size"):
        return None
    ox, oy, oz = z["origin"]
    ex, y_limit, ez, _radius = z["size"]
    if ex < 0 or ez < 0:
        return None
    return (ox, min(oy, oy + y_limit), oz, ox + ex, max(oy, oy + y_limit), oz + ez)


DAMAGE = 0x48      # action: damage (finding 158)


def trap_box(z: dict):
    """The box of a zone that catches you when you fall into it: it kills,
    teleports or hurts (action 0x48). None otherwise. Used by the
    no-collision flag: falling into one of these is not a safe fall."""
    if kind_of(z) or any(r["action"][0] == DAMAGE for r in z.get("rules", [])):
        return zone_box(z)
    return None
