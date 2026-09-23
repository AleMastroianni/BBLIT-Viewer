"""The chosen state in which to show a level.

These are not readings of the format: the game decides these things at runtime
(switches, conditions, object states). Here we fix the state needed for the
custom track.
Each entry says which measurement the number comes from.

* `pose`: model -> role of the animation to use instead of the one the game
  starts the object with (finding 272), clones included.
* `always_cloned`: template roles to always show, whatever the condition of
  the rule that clones them (except conditions on a variable fixed in
  `table1`, which are evaluated); they show even with clones off (key G),
  and so do the clones they request themselves (the torch flame).
* `table1`: fixed values of variables of the game's table 1 (finding
  161), to pick a state the game picks at runtime.
* `sky`: the role of the sky to show where two skies take turns (finding
  314, `Level._read_sky_choices`) and none of them is there when the level
  starts; elsewhere the default is the starting sky and needs no entry.
"""

PREFERENCES = {
    "L03A": {
        "pose": {
            # drawbridge (objects 85 and 127-130): still stages 118 raised,
            # 119 one third, 120 two thirds, 121 lowered (measured: depth
            # 2.6 / 6.2 / 9.4 / 12.0 m); the game starts from 118
            217: 121,
            # barrel in the water (model 239, templates 89 and 211): the game
            # starts it from 199, the rise (the top goes from 0 to 1.85 m above
            # the water); active it is in 202, floating in a loop with the top
            # at about 1.96 m
            239: 202,
            # falling crates (model 311, 8 templates): the game starts them
            # from 348, the fall (from 13 m to the ground in 22 frames); they
            # stay on the ground until Bugs throws them in the water: 131,
            # still on the ground
            311: 131,
        },
        "always_cloned": {
            # barrels in the water (model 239): 4 unconditional triggers and 7
            # that make them rise after a switch (tables 122/141/180)
            73, 663,
            # torches (model 165), cloned by two triggers; the flame is their
            # clone on the top (finding 279)
            671, 861,
            # blue crates (templates 764-766, finding 274): three rules
            # each, one per value of table1[114]; one is fixed below
            764, 765, 766,
            # the 8 crates that fall when Bugs gets close (model 311, 274)
            193, 194, 324, 509, 510, 511, 512, 513,
            # the 4 anchors (model 168, finding 280), cloned by 4 triggers
            # with a bit of table1[124] cleared: in the air at 15.6 m, spinning,
            # shadow on the ground; they fall when Bugs walks under (not simulated)
            533,
        },
        "table1": {
            # the order of the blue crates, which the game picks at random (1, 2 or 3)
            114: 1,
        },
        # the states the menu (Level options -> Entities) lets you pick
        # for the session; the starting value is the one in `pose` above
        "entity_groups": [
            {"name": "bridges", "model": 217,
             "states": [(118, "raised"), (119, "one_third"), (120, "two_thirds"), (121, "lowered")]},
            {"name": "water_barrels", "model": 239,
             "states": [(199, "rising"), (202, "floating")]},
            {"name": "green_crates", "model": 311,
             "states": [(348, "falling"), (131, "on_ground")]},
        ],
    },
    "L02C3": {
        # The Carrot-henge Mystery 3 starts in a cave with no sky. The rocks
        # (object 91, role 849) are what the game shows first (the big block
        # follows the camera and does not block the ice passage); the snowy
        # sky (object 132, role 446, the
        # model of parts 1, 2 and 4 of the mission) comes from the chain of
        # level byte 81 at the first portal and stays a menu choice
        # (tools/sky_rules.py)
        "sky": 849,
    },
}


def for_level(name: str) -> dict:
    pref = {"pose": {}, "always_cloned": set(), "table1": {}, "entity_groups": [], "sky": None}
    pref.update(PREFERENCES.get(name.upper(), {}))
    return pref
