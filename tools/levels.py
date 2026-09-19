"""The levels by era, with the LevID and the game's names.

Two sources that match row by row (check in
`tools/diagnostics/check_levels.py`):

* the **level table** in `bugs.exe`: 111 entries of 24 bytes, starting at
  `..\\BZE\\TITLE.BZE;1`; the index is the **LevID** (`+10000` in memory);
* a LevID spreadsheet (optional, not in the repository): row r describes
  LevID r + 1. The names and the notes in brackets are its own, verbatim.

The eras follow the file prefix (L01..L05), like the loading screens in
Ombelll's `LEVELS.md`; the spreadsheet also assigns the three bonus levels
to an era. **Nowhere** is in Load level below Dimension X (`NOWHERE`).
**Extra**: the Era selector (`LS01`) and the `_8` variants that
are on the disc but not in the executable's table, in every build.
**Cutscenes**, inside Extra and only in the Debug build: what has a 3D
environment but is not a playable level (menus, credits, cutscenes). In
the other builds Cutscenes stays hidden for now.

Each entry: (LevID or None, file without extension, part or None, note), plus
an optional dictionary (`extra_of`): for LS01 the five era cameras.
"""

from __future__ import annotations

# (era key in texts.py, [(title, [entries]), ...], bonus)
ERAS = [
    ("era.stone_age", [
        ("Wabbit On The Run", [(4, "L01A", 1, "Dinos"), (5, "L01B", 2, "Pterodaptyl")]),
        ("Guess Who Needs A Kick Starts", [(6, "L01C", None, "Taddeo Bossfight")]),
        ("Night Stone Age", [(7, "L01D1", 1, "Dinos"), (8, "L01D2", 2, "Pterodaptyls")]),
    ], [
        ("Duck Vs Bunny", [(52, "LB01", None, "")]),
    ]),
    ("era.medieval", [
        ("What's Cooking, Doc", [
            (9, "L02A1", 1, "Main Spawn, Outside Lake"),
            (13, "L02A5", 2, "Remote Forests, Merlin Tower"),
            (10, "L02A2", 3, "Piazza del Re, Birb Area + Drakes"),
            (11, "L02A3", 4, "Apple Session"),
            (12, "L02A4", 5, "The Walls, Cannons + Drakes"),
            (14, "L02A6", 6, "Lava Rooms + Bob & Brian")]),
        ("Witch Way To Albuquerque", [
            (15, "L02B1", 1, "Hazel Hill + Forest"),
            (16, "L02B2", 2, "Strada Mulino a Vento + Fattoria")]),
        ("Carrot Henge Mystery", [
            (17, "L02C1", 1, "Merlin Tower + Lake"),
            (18, "L02C2", 2, "Main Area Outside + Top Mountain"),
            (19, "L02C3", 3, "Duffy/Robin Minigame Room + Timer Ice Room Downhill Minigame"),
            (20, "L02C4", 4, "Geometrical Shapes Minigame Room + Racchette Minigame Room")]),
    ], [
        ("Ski", [(53, "LB02", None, "")]),
    ]),
    ("era.pirates", [
        ("What's Up Dock", [
            (21, "L03A", 1, "Pirates"),
            (23, "L03A2", 2, "Pirates"),
            (22, "L03ACOM", 3, "Sam Bossfight")]),
        ("When Sam Met Bunny", [(24, "L03B", None, "Boss Nave Cannoni")]),
        ("Mine Or Mine", [
            (25, "L03C", 1, "Outside"),
            (26, "L03C1", 2, "Minecart 1+2"),
            (27, "L03C2", 3, "Minecart 3 + Bossfight")]),
        ("Follow The Red Pirate Road", [(28, "L03D1", None, "Magic Door")]),
    ], []),
    ("era.1930s", [
        ("Big Bank Withdrawal", [
            (29, "L04A1", 1, "Dog Room"),
            (30, "L04A2", 2, "4 GC Doors + Bank Upstairs"),
            (31, "L04A3", 3, "Rocky & Mugsy Bossfight on Bank Rooftop")]),
        ("Condominio", [
            (32, "L04B1", 1, "Ground Floor + Floor 3"),
            (33, "L04B2", 2, "Floor 1 + Floor 2"),
            (34, "L04B3", 3, "Mugsy Bossfight on Hotel Rooftop")]),
        ("Carrot Factory", [
            (35, "L04C1", 1, "Main Spawn"),
            (38, "L04D1", 2, "Magazzino Nr.1"),
            (36, "L04C2", 3, "Factory"),
            (39, "L04D2", 4, "Magazzino Nr.2"),
            (37, "L04C3", 5, "Rock & Mugsy Bossfight")]),
        ("Objects In The Mirror Are Closer Than They Appear", [
            (40, "L04E", 1, "Car + Motorcycle"),
            (41, "L04E2", 2, "Bicycle + Sheep")]),
    ], [
        ("La Corrida", [(54, "LB04", None, "")]),
    ]),
    ("era.dimx", [
        ("Planet X File", [
            (42, "L05A1", 1, ""),
            (43, "L05A2", 2, "Robot"),
            (48, "L05A5", 3, "Marvin Bossfight")]),
        ("Mens Sana In Corpore Sano", [
            (44, "L05A3A", 1, "Simon Says"),
            (45, "L05A3B", 2, "Hare Dance"),
            (46, "L05A3C", 3, "Mastermind"),
            (47, "L05A4", 4, "Final Race")]),
        ("The Conquest For Planet X", [(49, "L05B1", None, "")]),
        ("Vort X Room", [(50, "L05C", None, "")]),
    ], []),
]

# Nowhere, in Load level below Dimension X
NOWHERE = [("Nowhere", [(51, "MERLIN", None, "")])]

# (section key in texts.py, [(title, [entries]), ...])
EXTRA = [
    # the world of the eras (LS01, "Era selector" in the menu): the
    # overview and five entries that open LS01 at the centre of an era.
    # Cameras: centre of the era's terrain block (measured), 18 m above
    # and 40 m back, facing the island (yaw -90, pitch -22). Blocks:
    # 1 Stone Age, 0 Medieval Period, 5 Pirates, 2 1930s, 4 Dimension X.
    ("extra.hub", [
        ("Era selector", [
            (3, "LS01", None, "", {"label": "extra.overview", "sheet_name": "Eras (Last Visited)"}),
            (3, "LS01", None, "", {"label": "era.stone_age", "sheet_name": "Eras (Last Visited)",
                                   "camera": (62.1, 164.4, -116.2, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.medieval", "sheet_name": "Eras (Last Visited)",
                                   "camera": (72.7, 171.9, -4.7, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.pirates", "sheet_name": "Eras (Last Visited)",
                                   "camera": (20.0, 23.8, 17.5, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.1930s", "sheet_name": "Eras (Last Visited)",
                                   "camera": (163.3, 27.8, 3.1, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.dimx", "sheet_name": "Eras (Last Visited)",
                                   "camera": (102.6, -75.3, -112.8, -90.0, -22.0)}),
        ]),
    ]),
    # on the disc but not in the executable's table: no LevID
    ("extra.variants", [
        ("Night Stone Age _8", [(None, "L01D1_8", 1, ""), (None, "L01D2_8", 2, "")]),
        ("What's Up Dock _8", [(None, "L03A_8", 1, ""), (None, "L03A2_8", 2, ""),
                               (None, "L03ACOM_8", 3, "")]),
        ("When Sam Met Bunny _8", [(None, "L03B_8", None, "")]),
        ("Mine Or Mine _8", [(None, "L03C_8", 1, "")]),
        ("Condominio _8", [(None, "L04B3_8", 3, "")]),
        ("La Corrida _8", [(None, "LB04_8", None, "")]),
    ]),
]

# the Cutscenes page inside Extra (Debug build only)
CUTSCENES = [
    ("extra.menu", [
        ("Main Menu", [(0, "TITLE", None, "")]),
        ("Pismo Credits", [(72, "CREDITS", None, "")]),
    ]),
    ("extra.films", [
        ("Start Cutscene", [(56, "CCINTRO", None, "")]),
        ("WabbitOnTheRun Cutscene", [(57, "CC1A", None, "")]),
        ("What's Cookin, Doc - Cutscene", [(58, "CC2A", None, "")]),
        ("Witch Way To Albuquerque - Cutscene", [(59, "CC2B", None, "")]),
        ("Carrot Henge Mystery (Neve) - Cutscene", [(60, "CC2C", None, "")]),
        ("Hey, What's Up Dock (Pirates) - Cutscene", [(61, "CC3A", None, "")]),
        ("When Sam Met Bunny (Boss Nave Cannoni) - Cutscene", [(62, "CC3B", None, "")]),
        ("Mine Or Mine - Cutscene", [(63, "CC3C", None, "")]),
        ("Follow The Red Pirate Road (Magic Door) - Cutscene", [(64, "CC3D", None, "")]),
        ("Big Bank Withdrawal - Cutscene", [(65, "CC4A", None, "")]),
        ("Condominio - Cutscene", [(66, "CC4B", None, "")]),
        ("Carrot Factory - Cutscene", [(67, "CC4C", None, "")]),
        ("Objects In The Mirror Are Closer Than They Appear - Cutscene", [(68, "CC4D", None, "")]),
        ("Planet X File - Cutscene", [(69, "CC5A", None, "")]),
        ("Nowhere - Cutscene", [(70, "CCMERLIN", None, "")]),
        ("End Cutscene", [(71, "CCEND", None, "")]),
    ]),
]


def extra_of(item) -> dict:
    """The optional fifth element of an entry: `label` (texts.py key
    instead of the part), `camera` (x, y, z, yaw, pitch in viewer metres),
    `sheet_name` (the name in the LevID spreadsheet, if the title differs)."""
    return item[4] if len(item) > 4 else {}


def all_entries():
    """(LevID, file, era or section, title, part, note, extra) of everything there is."""
    for era, titles, bonus in ERAS:
        for title_text, menu_items in titles + bonus:
            for item in menu_items:
                yield item[0], item[1], era, title_text, item[2], item[3], extra_of(item)
    for title_text, menu_items in NOWHERE:
        for item in menu_items:
            yield item[0], item[1], "era.nowhere", title_text, item[2], item[3], extra_of(item)
    for section, titles in EXTRA + CUTSCENES:
        for title_text, menu_items in titles:
            for item in menu_items:
                yield item[0], item[1], section, title_text, item[2], item[3], extra_of(item)
