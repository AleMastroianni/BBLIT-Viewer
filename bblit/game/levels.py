"""The levels by era, with the LevID and the game's names.

Two sources that match row by row (check in
`tools/diagnostics/check_levels.py`):

* the **level table** in `bugs.exe`: 111 entries of 24 bytes, starting at
  `..\\BZE\\TITLE.BZE;1`; the index is the **LevID** (`+10000` in memory);
* a LevID spreadsheet (optional, not in the repository): row r describes
  LevID r + 1. The names and the notes in brackets were its own, verbatim.

The titles and notes are the level names as read in the game, where
they were filled in (BBLIT_Level_IDs, from the Stone Age
to the 1930s); the spreadsheet's are kept in `sheet_name` and `sheet_note`
for check_levels.py, and the Debug build shows the old note in the
description (user: for now).

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

Titles and notes are the game's own names where it has them (finding
291: in the interface language, written exactly as in the game): {"en": ..., "it": ...} read from the disc by game_texts.py. A title
carries the index of its LS01 text ("ls01") and, for a `_8` variant, the
suffix; a note the indices of the area cards it is made of ("cards"),
chosen where the user confirmed the name in the game: a card can also be a
sign or a hint ("Garbage Storage..."), so the game alone does not say which
names a sub-level. Where the game has no name, the note is the user's, in
both languages when it needs a translation ({"en", "it"} without "cards":
"Boss: Elmer" / "Boss: Taddeo"). `name()` gives the one to show. check_official_names.py compares them with the disc.
"""

from __future__ import annotations

from ui import texts

# (era key in texts.py, [(title, [entries]), ...], bonus)
ERAS = [
    ("era.stone_age", [
        ({"en": "Wabbit on the run!", "it": "Coniglio in arrivo!", "ls01": 222}, [
            (4, "L01A", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}, {"sheet_note": "Dinos", "sheet_name": "Wabbit On The Run"}),
            (5, "L01B", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]}, {"sheet_note": "Pterodaptyl", "sheet_name": "Wabbit On The Run"})]),
        ({"en": "Guess who needs a kick start", "it": "Indovina A Chi Serve Una Spintarella", "ls01": 223}, [(6, "L01C", None, {"en": "Boss: Elmer", "it": "Boss: Taddeo"}, {"sheet_name": "Guess Who Needs A Kick Starts", "sheet_note": "Taddeo Bossfight"})]),
        ({"en": "Magic Hare Blower", "it": "I Ventilatori Magici", "ls01": 224}, [
            (7, "L01D1", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}, {"sheet_note": "Dinos", "sheet_name": "Night Stone Age"}),
            (8, "L01D2", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]}, {"sheet_note": "Pterodaptyls", "sheet_name": "Night Stone Age"})]),
    ], [
        ({"en": "Wabbit or Duck Season?", "it": "Anatra O Coniglio?", "ls01": 239}, [(52, "LB01", None, "", {"sheet_name": "Duck Vs Bunny"})]),
    ]),
    ("era.medieval", [
        ({"en": "What's cookin', Doc?", "it": "Cosa Bolle In Pentola, Amico?", "ls01": 225}, [
            (9, "L02A1", 1, {"en": "King's Fields", "it": "I Campi del Re", "cards": [219]}, {"sheet_note": "Main Spawn, Outside Lake", "sheet_name": "What's Cooking, Doc"}),
            (13, "L02A5", 2, {"en": "Forgotten Woods", "it": "Foreste Remote", "cards": [221]}, {"sheet_note": "Remote Forests, Merlin Tower", "sheet_name": "What's Cooking, Doc"}),
            (10, "L02A2", 3, {"en": "Royal Square + Spiral Tower", "it": "Piazza del Re + Torre Spiralidosa.", "cards": [224, 230]}, {"sheet_note": "Piazza del Re, Birb Area + Drakes", "sheet_name": "What's Cooking, Doc"}),
            (11, "L02A3", 4, {"en": "Royal Apple tree Gardens", "it": "I Giardini dei Meli Reali", "cards": [232]}, {"sheet_note": "Apple Session", "sheet_name": "What's Cooking, Doc"}),
            (12, "L02A4", 5, {"en": "Ramparts", "it": "Le Mura", "cards": [233]}, {"sheet_note": "The Walls, Cannons + Drakes", "sheet_name": "What's Cooking, Doc"}),
            (14, "L02A6", 6, {"en": "Lava Rooms + Boss", "it": "Lava Rooms + Boss"}, {"sheet_note": "Lava Rooms + Bob & Brian", "sheet_name": "What's Cooking, Doc"})]),
        ({"en": "\"Witch\" way to Albuquerque?", "it": "Mi Indichi l'\"Autostrega\" per Albuquerque?", "ls01": 226}, [
            (15, "L02B1", 1, {"en": "Hazel's Hill", "it": "La Collina di Hazel.", "cards": [234]}, {"sheet_note": "Hazel Hill + Forest", "sheet_name": "Witch Way To Albuquerque"}),
            (16, "L02B2", 2, {"en": "Windmill Road", "it": "Strada del mulino a vento", "cards": [236]}, {"sheet_note": "Strada Mulino a Vento + Fattoria", "sheet_name": "Witch Way To Albuquerque"})]),
        ({"en": "The Carrot-henge Mystery", "it": "Il Mistero Della Carota Di Stone Edge", "ls01": 227}, [
            (17, "L02C1", 1, {"en": "Frozen Duck valley", "it": "La Valle dell'Anatra Surgelata.", "cards": [238]}, {"sheet_note": "Merlin Tower + Lake", "sheet_name": "Carrot Henge Mystery"}),
            (18, "L02C2", 2, {"en": "Carrot-henge", "it": "La Carota di Stone Hendge", "cards": [241]}, {"sheet_note": "Main Area Outside + Top Mountain", "sheet_name": "Carrot Henge Mystery"}),
            (19, "L02C3", 3, {"en": "Robin Duck's Lair + Slide Hare", "it": "Il Rifugio di Robin + La Lepre sdrucciolona", "cards": [245, 246]}, {"sheet_note": "Duffy/Robin Minigame Room + Timer Ice Room Downhill Minigame", "sheet_name": "Carrot Henge Mystery"}),
            (20, "L02C4", 4, {"en": "Zee Cavern + Raquette hare!", "it": "La Caverna + Racchette da lepre!", "cards": [247, 248]}, {"sheet_note": "Geometrical Shapes Minigame Room + Racchette Minigame Room", "sheet_name": "Carrot Henge Mystery"})]),
    ], [
        ({"en": "Downhill Duck!", "it": "Anatra In Pista!", "ls01": 240}, [(53, "LB02", None, "", {"sheet_name": "Ski"})]),
    ]),
    ("era.pirates", [
        ({"en": "Hey... What's up, Dock?", "it": "Ehi... Che Succede, Amico?", "ls01": 228}, [
            (21, "L03A", 1, {"en": "The Docks", "it": "I Moli", "cards": [212]}, {"sheet_note": "Pirates", "sheet_name": "What's Up Dock"}),
            (23, "L03A2", 2, {"en": "Shark Islands", "it": "Le Isole degli Squali", "cards": [211]}, {"sheet_note": "Pirates", "sheet_name": "What's Up Dock"}),
            (22, "L03ACOM", 3, {"en": "Boss: Yosemite Sam", "it": "Boss: Sam"}, {"sheet_name": "What's Up Dock", "sheet_note": "Sam Bossfight"})]),
        ({"en": "When Sam met Bunny", "it": "Quando Sam Conobbe Bunny", "ls01": 229}, [(24, "L03B", None, {"en": "Boss: Sam's Ship", "it": "Boss: Nave di Sam"}, {"sheet_note": "Boss Nave Cannoni", "sheet_name": "When Sam Met Bunny"})]),
        ({"en": "Mine or mine?", "it": "La Mia Miniera?", "ls01": 230}, [
            (25, "L03C", 1, {"en": "Pirate's Cove", "it": "Il Covo dei Pirati", "cards": [221]}, {"sheet_note": "Outside", "sheet_name": "Mine Or Mine"}),
            (26, "L03C1", 2, {"en": "Sam' S Mine. No Trespassers!", "it": "Miniera di Sam. Ingresso vietato!", "cards": [222]}, {"sheet_note": "Minecart 1+2", "sheet_name": "Mine Or Mine"}),
            (27, "L03C2", 3, {"en": "Minecart 3 + Boss", "it": "Carrello 3 + Boss"}, {"sheet_name": "Mine Or Mine", "sheet_note": "Minecart 3 + Bossfight"})]),
        ({"en": "Follow the Red Pirate Road", "it": "Sulle Orme Del Pirata Rosso", "ls01": 231}, [(28, "L03D1", None, {"en": "Sam's Lair", "it": "Il Covo di Sam", "cards": [219]}, {"sheet_note": "Magic Door", "sheet_name": "Follow The Red Pirate Road"})]),
    ], []),
    ("era.1930s", [
        ({"en": "The Big Bank Withdrawal", "it": "Il Colpaccio di Bug Capone", "ls01": 232}, [
            (29, "L04A1", 1, {"en": "Bank Basement", "it": "Le Fondamenta della Banca", "cards": [211]}, {"sheet_note": "Dog Room", "sheet_name": "Big Bank Withdrawal"}),
            (30, "L04A2", 2, {"en": "Inside the Bank", "it": "In Banca", "cards": [212]}, {"sheet_note": "4 GC Doors + Bank Upstairs", "sheet_name": "Big Bank Withdrawal"}),
            (31, "L04A3", 3, {"en": "Bank Rooftop", "it": "Il Tetto della Banca", "cards": [213]}, {"sheet_note": "Rocky & Mugsy Bossfight on Bank Rooftop", "sheet_name": "Big Bank Withdrawal"})]),
        ({"en": "The Greatest Escape", "it": "La Grande Fuga", "ls01": 233}, [
            (32, "L04B1", 1, {"en": "Hotel Hall", "it": "La Hall dell'Hotel", "cards": [214]}, {"sheet_note": "Ground Floor + Floor 3", "sheet_name": "Condominio"}),
            (33, "L04B2", 2, {"en": "First Floor + Second Floor", "it": "Primo Piano + Secondo Piano", "cards": [215, 216]}, {"sheet_note": "Floor 1 + Floor 2", "sheet_name": "Condominio"}),
            (34, "L04B3", 3, {"en": "Hotel Rooftop", "it": "Il Tetto dell'Hotel", "cards": [217]}, {"sheet_note": "Mugsy Bossfight on Hotel Rooftop", "sheet_name": "Condominio"})]),
        ({"en": "The Carrot Factory", "it": "La Fabbrica Di Carote", "ls01": 234}, [
            (35, "L04C1", 1, {"en": "Carrot Steamer", "it": "Carote al Vapore", "cards": [218]}, {"sheet_note": "Main Spawn", "sheet_name": "Carrot Factory"}),
            (38, "L04D1", 2, {"en": "Warehouse #1", "it": "Magazzino No.1", "cards": [221]}, {"sheet_note": "Magazzino Nr.1", "sheet_name": "Carrot Factory"}),
            (36, "L04C2", 3, {"en": "Carrot Packers", "it": "I Confezionatori di Carote", "cards": [219]}, {"sheet_note": "Factory", "sheet_name": "Carrot Factory"}),
            (39, "L04D2", 4, {"en": "Warehouse #2", "it": "Magazzino No.2", "cards": [222]}, {"sheet_note": "Magazzino Nr.2", "sheet_name": "Carrot Factory"}),
            (37, "L04C3", 5, {"en": "Expedition room", "it": "Stanza Spedizioni", "cards": [220]}, {"sheet_note": "Rock & Mugsy Bossfight", "sheet_name": "Carrot Factory"})]),
        ({"en": "Objects in the mirror are closer than they appear!", "it": "Gli Oggetti Nello Specchio Sono Molto, Molto Vicini!", "ls01": 235}, [
            (40, "L04E", 1, {"en": "Chicago Chase", "it": "Caccia a Chicago", "cards": [223]}, {"sheet_note": "Car + Motorcycle", "sheet_name": "Objects In The Mirror Are Closer Than They Appear"}),
            (41, "L04E2", 2, {"en": "Bicycle + Sheep", "it": "Bicicletta + Pecore"}, {"sheet_name": "Objects In The Mirror Are Closer Than They Appear"})]),
    ], [
        ({"en": "La Corrida", "it": "La Corrida", "ls01": 241}, [(54, "LB04", None, "", {"sheet_name": "La Corrida"})]),
    ]),
    ("era.dimx", [
        ({"en": "The Planet X File!", "it": "Il Pianeta X File!", "ls01": 236}, [
            (42, "L05A1", 1, {"en": "Space Base, AREA 1", "it": "Base Spaziale, AREA 1", "cards": [227]}, {"sheet_name": "Planet X File"}),
            (43, "L05A2", 2, {"en": "Space Base, AREA 4", "it": "Base Spaziale, AREA 4", "cards": [239]}, {"sheet_name": "Planet X File", "sheet_note": "Robot"}),
            (48, "L05A5", 3, {"en": "Space Modulator", "it": "Modulatore Spaziale", "cards": [244]}, {"sheet_name": "Planet X File", "sheet_note": "Marvin Bossfight"})]),
        ({"en": "Train your Brain!", "it": "Mens Sana In Corpore Sano!", "ls01": 243}, [
            (44, "L05A3A", 1, {"en": "Neuronal Synaptal Network", "it": "Sistema Neuronale Sinaptico", "cards": [240]}, {"sheet_name": "Mens Sana In Corpore Sano", "sheet_note": "Simon Says"}),
            (45, "L05A3B", 2, {"en": "Hare Dance", "it": "La Danza della Lepre", "cards": [241]}, {"sheet_name": "Mens Sana In Corpore Sano"}),
            (46, "L05A3C", 3, {"en": "ACME Mind", "it": "ACME Mind", "cards": [242]}, {"sheet_name": "Mens Sana In Corpore Sano", "sheet_note": "Mastermind"}),
            (47, "L05A4", 4, {"en": "Final Race", "it": "Gara finale"}, {"sheet_name": "Mens Sana In Corpore Sano"})]),
        ({"en": "The Conquest for Planet X!", "it": "Alla Conquista Del Pianeta X!", "ls01": 237}, [(49, "L05B1", None, {"en": "Planet X", "it": "Il Pianeta X", "cards": [245]}, {"sheet_name": "The Conquest For Planet X"})]),
        ({"en": "Vort \"X\" Room", "it": "La \"X\" Stanza", "ls01": 238}, [(50, "L05C", None, "", {"sheet_name": "Vort X Room"})]),
    ], []),
]

# Nowhere, in Load level below Dimension X
# the game calls it "Da nessuna parte" in Italian: "Nowhere" in both, by choice
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
        ({"en": "Magic Hare Blower _8", "it": "I Ventilatori Magici _8", "ls01": 224, "suffix": " _8"}, [
            (None, "L01D1_8", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}, {"sheet_name": "Magic Hare Blower _8"}),
            (None, "L01D2_8", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]}, {"sheet_name": "Magic Hare Blower _8"})]),
        ({"en": "Hey... What's up, Dock? _8", "it": "Ehi... Che Succede, Amico? _8", "ls01": 228, "suffix": " _8"}, [
            (None, "L03A_8", 1, {"en": "The Docks", "it": "I Moli", "cards": [212]}, {"sheet_name": "What's Up Dock _8"}),
            (None, "L03A2_8", 2, {"en": "Shark Islands", "it": "Le Isole degli Squali", "cards": [211]}, {"sheet_name": "What's Up Dock _8"}),
            (None, "L03ACOM_8", 3, "", {"sheet_name": "What's Up Dock _8"})]),
        ({"en": "When Sam met Bunny _8", "it": "Quando Sam Conobbe Bunny _8", "ls01": 229, "suffix": " _8"}, [(None, "L03B_8", None, "", {"sheet_name": "When Sam Met Bunny _8"})]),
        ({"en": "Mine or mine? _8", "it": "La Mia Miniera? _8", "ls01": 230, "suffix": " _8"}, [(None, "L03C_8", 1, {"en": "Pirate's Cove", "it": "Il Covo dei Pirati", "cards": [221]}, {"sheet_name": "Mine Or Mine _8"})]),
        ({"en": "The Greatest Escape _8", "it": "La Grande Fuga _8", "ls01": 233, "suffix": " _8"}, [(None, "L04B3_8", 3, {"en": "Hotel Rooftop", "it": "Il Tetto dell'Hotel", "cards": [217]}, {"sheet_name": "The Greatest Escape _8"})]),
        ({"en": "La Corrida _8", "it": "La Corrida _8", "ls01": 241, "suffix": " _8"}, [(None, "LB04_8", None, "", {"sheet_name": "La Corrida _8"})]),
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


def name(value) -> str:
    """A title or note to show: a plain string as it is, a game name in the
    interface language (English if that language is missing)."""
    if isinstance(value, dict):
        return value.get(texts.language(), value["en"])
    return value


def extra_of(item) -> dict:
    """The optional fifth element of an entry: `label` (texts.py key
    instead of the part), `camera` (x, y, z, yaw, pitch in viewer metres),
    `sheet_name` and `sheet_note` (the title and note in the LevID
    spreadsheet, if they differ)."""
    return item[4] if len(item) > 4 else {}


def official_name(file_name: str, in_english: bool = False) -> str | None:
    """The level's name as the game writes it: the mission title and, when
    the mission has more than one part, the part number ("Wabbit on the
    run! 2"). The rule: the viewer and its
    documents name levels, not file codes; the code goes in brackets at
    most. `in_english` forces English, for the flag names, which are never
    translated. None if the file is not in the table."""
    for _levid, entry_file, _era, title_text, part, _note, _extra in all_entries():
        if entry_file.lower() == file_name.lower():
            title = (title_text.get("en", "") if in_english and isinstance(title_text, dict)
                     else name(title_text))
            return f"{title} {part}" if part is not None else title
    return None


_by_levid: dict[int, str] | None = None


def file_of_levid(levid: int) -> str | None:
    """The file a LevID names (`L03C1`), from the executable's level table,
    or None if no entry carries it. A level change carries a LevID and
    nothing else (finding 326)."""
    global _by_levid
    if _by_levid is None:
        _by_levid = {}
        for entry_levid, entry_file, *_rest in all_entries():
            if entry_levid is not None:
                _by_levid.setdefault(entry_levid, entry_file)
    return _by_levid.get(levid)


def is_film(file_name: str) -> bool:
    """Whether a file is one of the cutscenes (the Films of the Cutscenes
    page): not a level you play, its placed Bugs is an actor."""
    return any(item[1].lower() == file_name.lower()
               for section, titles in CUTSCENES if section == "extra.films"
               for _title, menu_items in titles for item in menu_items)


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
