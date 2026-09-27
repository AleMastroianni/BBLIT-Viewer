"""The levels by era, with the LevID and the game's names.

The **LevID** is the index in the level table of `bugs.exe`: 111 entries of
24 bytes, starting at `..\\BZE\\TITLE.BZE;1` (`+10000` in memory);
`checks/check_levels.py` checks every entry against it.

The eras follow the file prefix (L01..L05), like the loading screens in
Ombelll's `LEVELS.md`; each of the three bonus levels is listed under an
era too. **Nowhere** is in Load level below Dimension X (`NOWHERE`).
**Eras** (`HUB`), the first entry of Load level: the Era selector (`LS01`)
as the overview and at the centre of each era. **Extra**: the `_8`
variants that are on the disc but not in the executable's table.
**Cutscenes**, inside Extra: what has a 3D environment but is not a
playable level (menus, credits, cutscenes). Extra is in every build.

Each entry: (LevID or None, file without extension, part or None, note), plus
an optional dictionary (`extra_of`): for LS01 the five era cameras.

Titles and notes are the game's own names where it has them (finding
291: in the interface language, written exactly as in the game): {"en": ..., "it": ...} read from the disc by game_texts.py. A title
carries the index of its LS01 text ("ls01") and, for a `_8` variant, the
suffix; a note the indices of the area cards it is made of ("cards"),
chosen where the name was confirmed in the game: a card can also be a
sign or a hint ("Garbage Storage..."), so the game alone does not say which
names a sub-level. Where the game has no name, the note is written by hand, in
both languages when it needs a translation ({"en", "it"} without "cards":
"Boss: Elmer" / "Boss: Taddeo"). `name()` gives the one to show. check_official_names.py compares them with the disc.
"""

from __future__ import annotations

import os

from ui import texts

# (era key in texts.py, [(title, [entries]), ...], bonus)
ERAS = [
    ("era.stone_age", [
        ({"en": "Wabbit on the run!", "it": "Coniglio in arrivo!", "ls01": 222}, [
            (4, "L01A", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}),
            (5, "L01B", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]})]),
        ({"en": "Guess who needs a kick start", "it": "Indovina A Chi Serve Una Spintarella", "ls01": 223}, [(6, "L01C", None, {"en": "Boss: Elmer", "it": "Boss: Taddeo"})]),
        ({"en": "Magic Hare Blower", "it": "I Ventilatori Magici", "ls01": 224}, [
            (7, "L01D1", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}),
            (8, "L01D2", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]})]),
    ], [
        ({"en": "Wabbit or Duck Season?", "it": "Anatra O Coniglio?", "ls01": 239}, [(52, "LB01", None, "")]),
    ]),
    ("era.medieval", [
        ({"en": "What's cookin', Doc?", "it": "Cosa Bolle In Pentola, Amico?", "ls01": 225}, [
            (9, "L02A1", 1, {"en": "King's Fields", "it": "I Campi del Re", "cards": [219]}),
            (13, "L02A5", 2, {"en": "Forgotten Woods", "it": "Foreste Remote", "cards": [221]}),
            (10, "L02A2", 3, {"en": "Royal Square + Spiral Tower", "it": "Piazza del Re + Torre Spiralidosa.", "cards": [224, 230]}),
            (11, "L02A3", 4, {"en": "Royal Apple tree Gardens", "it": "I Giardini dei Meli Reali", "cards": [232]}),
            (12, "L02A4", 5, {"en": "Ramparts", "it": "Le Mura", "cards": [233]}),
            (14, "L02A6", 6, "")]),
        ({"en": "\"Witch\" way to Albuquerque?", "it": "Mi Indichi l'\"Autostrega\" per Albuquerque?", "ls01": 226}, [
            (15, "L02B1", 1, {"en": "Hazel's Hill", "it": "La Collina di Hazel.", "cards": [234]}),
            (16, "L02B2", 2, {"en": "Windmill Road", "it": "Strada del mulino a vento", "cards": [236]})]),
        ({"en": "The Carrot-henge Mystery", "it": "Il Mistero Della Carota Di Stone Edge", "ls01": 227}, [
            (17, "L02C1", 1, {"en": "Frozen Duck valley", "it": "La Valle dell'Anatra Surgelata.", "cards": [238]}),
            (18, "L02C2", 2, {"en": "Carrot-henge", "it": "La Carota di Stone Hendge", "cards": [241]}),
            (19, "L02C3", 3, {"en": "Robin Duck's Lair + Slide Hare", "it": "Il Rifugio di Robin + La Lepre sdrucciolona", "cards": [245, 246]}),
            (20, "L02C4", 4, {"en": "Zee Cavern + Raquette hare!", "it": "La Caverna + Racchette da lepre!", "cards": [247, 248]})]),
    ], [
        ({"en": "Downhill Duck!", "it": "Anatra In Pista!", "ls01": 240}, [(53, "LB02", None, "")]),
    ]),
    ("era.pirates", [
        ({"en": "Hey... What's up, Dock?", "it": "Ehi... Che Succede, Amico?", "ls01": 228}, [
            (21, "L03A", 1, {"en": "The Docks", "it": "I Moli", "cards": [212]}),
            (23, "L03A2", 2, {"en": "Shark Islands", "it": "Le Isole degli Squali", "cards": [211]}),
            (22, "L03ACOM", 3, {"en": "Boss: Yosemite Sam", "it": "Boss: Sam"})]),
        ({"en": "When Sam met Bunny", "it": "Quando Sam Conobbe Bunny", "ls01": 229}, [(24, "L03B", None, {"en": "Boss: Sam's Ship", "it": "Boss: Nave di Sam"})]),
        ({"en": "Mine or mine?", "it": "La Mia Miniera?", "ls01": 230}, [
            (25, "L03C", 1, {"en": "Pirate's Cove", "it": "Il Covo dei Pirati", "cards": [221]}),
            (26, "L03C1", 2, {"en": "Sam' S Mine. No Trespassers!", "it": "Miniera di Sam. Ingresso vietato!", "cards": [222]}),
            (27, "L03C2", 3, "")]),
        ({"en": "Follow the Red Pirate Road", "it": "Sulle Orme Del Pirata Rosso", "ls01": 231}, [(28, "L03D1", None, {"en": "Sam's Lair", "it": "Il Covo di Sam", "cards": [219]})]),
    ], []),
    ("era.1930s", [
        ({"en": "The Big Bank Withdrawal", "it": "Il Colpaccio di Bug Capone", "ls01": 232}, [
            (29, "L04A1", 1, {"en": "Bank Basement", "it": "Le Fondamenta della Banca", "cards": [211]}),
            (30, "L04A2", 2, {"en": "Inside the Bank", "it": "In Banca", "cards": [212]}),
            (31, "L04A3", 3, {"en": "Bank Rooftop", "it": "Il Tetto della Banca", "cards": [213]})]),
        ({"en": "The Greatest Escape", "it": "La Grande Fuga", "ls01": 233}, [
            (32, "L04B1", 1, {"en": "Hotel Hall", "it": "La Hall dell'Hotel", "cards": [214]}),
            (33, "L04B2", 2, {"en": "First Floor + Second Floor", "it": "Primo Piano + Secondo Piano", "cards": [215, 216]}),
            (34, "L04B3", 3, {"en": "Hotel Rooftop", "it": "Il Tetto dell'Hotel", "cards": [217]})]),
        ({"en": "The Carrot Factory", "it": "La Fabbrica Di Carote", "ls01": 234}, [
            (35, "L04C1", 1, {"en": "Carrot Steamer", "it": "Carote al Vapore", "cards": [218]}),
            (38, "L04D1", 2, {"en": "Warehouse #1", "it": "Magazzino No.1", "cards": [221]}),
            (36, "L04C2", 3, {"en": "Carrot Packers", "it": "I Confezionatori di Carote", "cards": [219]}),
            (39, "L04D2", 4, {"en": "Warehouse #2", "it": "Magazzino No.2", "cards": [222]}),
            (37, "L04C3", 5, {"en": "Expedition room", "it": "Stanza Spedizioni", "cards": [220]})]),
        ({"en": "Objects in the mirror are closer than they appear!", "it": "Gli Oggetti Nello Specchio Sono Molto, Molto Vicini!", "ls01": 235}, [
            (40, "L04E", 1, {"en": "Chicago Chase", "it": "Caccia a Chicago", "cards": [223]}),
            (41, "L04E2", 2, "")]),
    ], [
        ({"en": "La Corrida", "it": "La Corrida", "ls01": 241}, [(54, "LB04", None, "")]),
    ]),
    ("era.dimx", [
        ({"en": "The Planet X File!", "it": "Il Pianeta X File!", "ls01": 236}, [
            (42, "L05A1", 1, {"en": "Space Base, AREA 1", "it": "Base Spaziale, AREA 1", "cards": [227]}),
            (43, "L05A2", 2, {"en": "Space Base, AREA 4", "it": "Base Spaziale, AREA 4", "cards": [239]}),
            (48, "L05A5", 3, {"en": "Space Modulator", "it": "Modulatore Spaziale", "cards": [244]})]),
        ({"en": "Train your Brain!", "it": "Mens Sana In Corpore Sano!", "ls01": 243}, [
            (44, "L05A3A", 1, {"en": "Neuronal Synaptal Network", "it": "Sistema Neuronale Sinaptico", "cards": [240]}),
            (45, "L05A3B", 2, {"en": "Hare Dance", "it": "La Danza della Lepre", "cards": [241]}),
            (46, "L05A3C", 3, {"en": "ACME Mind", "it": "ACME Mind", "cards": [242]}),
            (47, "L05A4", 4, "")]),
        ({"en": "The Conquest for Planet X!", "it": "Alla Conquista Del Pianeta X!", "ls01": 237}, [(49, "L05B1", None, {"en": "Planet X", "it": "Il Pianeta X", "cards": [245]})]),
        ({"en": "Vort \"X\" Room", "it": "La \"X\" Stanza", "ls01": 238}, [(50, "L05C", None, "")]),
    ], []),
]

# Nowhere, in Load level below Dimension X
# the game calls it "Da nessuna parte" in Italian: "Nowhere" in both, by choice
NOWHERE = [("Nowhere", [(51, "MERLIN", None, "")])]

# (section key in texts.py, [(title, [entries]), ...])
# Eras, the first entry of Load level (outside Extra)
HUB = [
    # the world of the eras (LS01, "Era selector" in the menu): the
    # overview and five entries that open LS01 at the centre of an era.
    # Cameras: centre of the era's terrain piece (measured), 18 m above
    # its top and 40 m back, facing the island (yaw -90, pitch -22).
    # Collision blocks by area: 1 (areas 1) Stone Age, 2 Medieval Period,
    # 3 Pirates, 4 the 1930s, 5 Dimension X (checked on the photos: Stone
    # Age and Pirates had each other's camera).
    # Dimension X: its piece holds the space backdrop too, so the camera
    # is centred on the block's walkable ground (X 12180..22420, Z
    # 17380..29020, top Y 15184), not on the piece.
    ("extra.hub", [
        ("Era selector", [
            (3, "LS01", None, "", {"label": "extra.overview"}),
            (3, "LS01", None, "", {"label": "era.stone_age",
                                   "camera": (20.0, 23.8, 17.5, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.medieval",
                                   "camera": (72.7, 171.9, -4.7, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.pirates",
                                   "camera": (62.1, 164.4, -116.2, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.1930s",
                                   "camera": (163.3, 27.8, 3.1, -90.0, -22.0)}),
            (3, "LS01", None, "", {"label": "era.dimx",
                                   "camera": (135.2, -100.6, -141.2, -90.0, -22.0)}),
        ]),
    ]),
]

# Extra: what is on the disc but not in the executable's table (no LevID)
EXTRA = [
    ("extra.variants", [
        ({"en": "Magic Hare Blower _8", "it": "I Ventilatori Magici _8", "ls01": 224, "suffix": " _8"}, [
            (None, "L01D1_8", 1, {"en": "Dinosaur Mountain", "it": "La Montagna del Dinosauro", "cards": [218]}),
            (None, "L01D2_8", 2, {"en": "Pterodactyl Cliff", "it": "La Scogliera dello Pterodattilo", "cards": [219]})]),
        ({"en": "Hey... What's up, Dock? _8", "it": "Ehi... Che Succede, Amico? _8", "ls01": 228, "suffix": " _8"}, [
            (None, "L03A_8", 1, {"en": "The Docks", "it": "I Moli", "cards": [212]}),
            (None, "L03A2_8", 2, {"en": "Shark Islands", "it": "Le Isole degli Squali", "cards": [211]}),
            (None, "L03ACOM_8", 3, "")]),
        ({"en": "When Sam met Bunny _8", "it": "Quando Sam Conobbe Bunny _8", "ls01": 229, "suffix": " _8"}, [(None, "L03B_8", None, "")]),
        ({"en": "Mine or mine? _8", "it": "La Mia Miniera? _8", "ls01": 230, "suffix": " _8"}, [(None, "L03C_8", 1, {"en": "Pirate's Cove", "it": "Il Covo dei Pirati", "cards": [221]})]),
        ({"en": "The Greatest Escape _8", "it": "La Grande Fuga _8", "ls01": 233, "suffix": " _8"}, [(None, "L04B3_8", 3, {"en": "Hotel Rooftop", "it": "Il Tetto dell'Hotel", "cards": [217]})]),
        ({"en": "La Corrida _8", "it": "La Corrida _8", "ls01": 241, "suffix": " _8"}, [(None, "LB04_8", None, "")]),
    ]),
]

# the Cutscenes page inside Extra
# `start_camera` (x, y, z, yaw, pitch in viewer metres): where the viewer opens
# the file. Chosen to see the scene well, not read from the game: the
# camera of a film is moved by a routine of the game that is not read yet
# (0x40a590), and these files have no Bugs to stand behind. An overview from
# above (35 degrees down, the whole terrain box in the frame) where it shows
# the scene, a view chosen by eye elsewhere (TITLE in front of the licence
# text, CCEND inside the dark shell around its island)
CUTSCENES = [
    ("extra.menu", [
        ({"en": "Main menu", "it": "Menu principale"}, [(0, "TITLE", None, "", {"start_camera": (0.39, 0.4, 1.8, -90.0, -3.0)})]),
        ({"en": "Credits", "it": "Crediti"}, [(72, "CREDITS", None, "", {"start_camera": (183.0, 117.0, -130.1, 180.0, -36.9)})]),
    ]),
    ("extra.films", [
        ({"en": "Opening cutscene", "it": "Filmato iniziale"}, [(56, "CCINTRO", None, "", {"start_camera": (99.0, 100.9, -88.7, 180.0, -23.2)})]),
        ({"en": "Cutscene CC1A", "it": "Filmato CC1A"}, [(57, "CC1A", None, "", {"start_camera": (181.0, 54.6, 13.0, -90.0, -35.0)})]),
        ({"en": "Cutscene CC2A", "it": "Filmato CC2A"}, [(58, "CC2A", None, "", {"start_camera": (80.2, 129.1, -225.1, 90.0, -36.9)})]),
        ({"en": "Cutscene CC2B", "it": "Filmato CC2B"}, [(59, "CC2B", None, "", {"start_camera": (119.9, 16.2, -47.6, 180.0, -36.9)})]),
        ({"en": "Cutscene CC2C", "it": "Filmato CC2C"}, [(60, "CC2C", None, "", {"start_camera": (44.2, 23.1, 7.8, -90.0, -36.9)})]),
        ({"en": "Cutscene CC3A", "it": "Filmato CC3A"}, [(61, "CC3A", None, "", {"start_camera": (148.6, 144.4, 4.3, -90.0, -35.0)})]),
        ({"en": "Cutscene CC3B", "it": "Filmato CC3B"}, [(62, "CC3B", None, "", {"start_camera": (165.3, 96.3, -74.6, -90.0, -35.0)})]),
        ({"en": "Cutscene CC3C", "it": "Filmato CC3C"}, [(63, "CC3C", None, "", {"start_camera": (48.9, 52.9, -109.3, -90.0, -35.0)})]),
        ({"en": "Cutscene CC3D", "it": "Filmato CC3D"}, [(64, "CC3D", None, "", {"start_camera": (72.9, 55.5, -120.1, 90.0, -36.9)})]),
        ({"en": "Cutscene CC4A", "it": "Filmato CC4A"}, [(65, "CC4A", None, "", {"start_camera": (15.6, 41.1, 14.0, -90.0, -35.0)})]),
        ({"en": "Cutscene CC4B", "it": "Filmato CC4B"}, [(66, "CC4B", None, "", {"start_camera": (38.3, 55.6, 19.2, -90.0, -35.0)})]),
        ({"en": "Cutscene CC4C", "it": "Filmato CC4C"}, [(67, "CC4C", None, "", {"start_camera": (184.1, 40.9, -186.2, 180.0, -23.2)})]),
        ({"en": "Cutscene CC4D", "it": "Filmato CC4D"}, [(68, "CC4D", None, "", {"start_camera": (38.3, 46.4, 15.3, -90.0, -35.0)})]),
        ({"en": "Cutscene CC5A", "it": "Filmato CC5A"}, [(69, "CC5A", None, "", {"start_camera": (63.4, 83.5, 18.8, -90.0, -35.0)})]),
        ({"en": "Cutscene CCMERLIN", "it": "Filmato CCMERLIN"}, [(70, "CCMERLIN", None, "", {"start_camera": (63.9, 109.3, 27.5, -90.0, -35.0)})]),
        ({"en": "Ending cutscene", "it": "Filmato finale"}, [(71, "CCEND", None, "", {"start_camera": (25.0, 40.0, -19.5, 180.0, -35.0)})]),
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
    `start_camera` (the same, where the viewer opens the file, chosen by
    eye: the Extra files without Bugs)."""
    return item[4] if len(item) > 4 else {}


def start_camera(file_name: str):
    """The chosen opening camera of a file (`start_camera`), or None."""
    for _levid, entry_file, _era, _title, _part, _note, extra in all_entries():
        if entry_file.lower() == file_name.lower() and extra.get("start_camera"):
            return extra["start_camera"]
    return None


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


_extra_files: frozenset[str] | None = None


def extra_files() -> frozenset[str]:
    """The file names under Extra, in lower case: the six `_8` variants
    (`extra.variants`), the menu and the credits (`extra.menu`) and the 16
    cutscenes (`extra.films`)."""
    global _extra_files
    if _extra_files is None:
        _extra_files = frozenset(item[1].lower()
                                 for _section, titles in EXTRA + CUTSCENES
                                 for _title, menu_items in titles for item in menu_items)
    return _extra_files


def is_extra(path_or_name: str) -> bool:
    """Whether a file is one of the Extra ones."""
    stem = os.path.splitext(os.path.basename(path_or_name))[0].lower()
    return stem in extra_files()


def playable(paths_or_names):
    """The same list without the Extra files.

    A run over the whole disc means the levels you play: 52 of the 79 files.
    The cutscenes have no drawn ground, so a census of the collision ground
    reads their whole grid as invisible floor (`CC3D` alone 518400 sub-cells
    out of 6.4 million), `TITLE` likewise, and the six `_8` variants are the
    same levels twice, with the same numbers. Filtering here, on the names,
    means those files are never opened, never built and never measured, not
    dropped from a table at the end."""
    return [p for p in paths_or_names if not is_extra(p)]


def all_entries():
    """(LevID, file, era or section, title, part, note, extra) of everything there is."""
    for era, titles, bonus in ERAS:
        for title_text, menu_items in titles + bonus:
            for item in menu_items:
                yield item[0], item[1], era, title_text, item[2], item[3], extra_of(item)
    for title_text, menu_items in NOWHERE:
        for item in menu_items:
            yield item[0], item[1], "era.nowhere", title_text, item[2], item[3], extra_of(item)
    for section, titles in HUB + EXTRA + CUTSCENES:
        for title_text, menu_items in titles:
            for item in menu_items:
                yield item[0], item[1], section, title_text, item[2], item[3], extra_of(item)
