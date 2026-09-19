"""The game's own texts (section 3 of a level): the official level and
area names, in the six languages.

Section 3 carries six text tables, one per language in the order English,
French, German, Spanish, Italian, Dutch; each is a `u16` offset table
followed by its strings, the offsets counted from the table's start (the
table the game reads through `DAT_004b3a04`, finding 93). A string ends
with a zero and carries formatting codes (`>CC0 >CY50 ... >W120`).

Where the names are (finding 291):

* the level titles are in the Era selector (`LS01`), texts 213-219 (eras)
  and 222-243 (levels): "Wabbit on the run!" / "Coniglio in arrivo!";
* the area names are the cards shown for 120 ticks (`>W120`) when you enter
  an area: a zone rule (block 0x09, opcode 0x33, action byte +11 = 0x31,
  text index u16 at +12) or an object rule (blocks 0x07/0x08/0x0A, opcode
  0x31, action byte +15 = 0x31, text index at +16) shows them. Not every
  card names the sub-level (signs such as "Garbage Storage...", hints, the
  way to another area), and not every sub-level has one: the cards are
  candidates, and levels.py keeps the ones confirmed in the game.
"""

from __future__ import annotations

import re
import struct

LANGUAGES = ("en", "fr", "de", "es", "it", "nl")

# the Era selector's texts for the level titles, per menu group
# (levels.py): the LS01 text index
TITLE_TEXTS = {
    "wabbit": 222, "kick_start": 223, "magic_hare": 224,
    "cookin": 225, "witch": 226, "carrot_henge": 227,
    "dock": 228, "sam_met": 229, "mine": 230, "red_road": 231,
    "bank": 232, "escape": 233, "factory": 234, "mirror": 235,
    "planet_x_file": 236, "conquest": 237, "vort": 238,
    "duck_season": 239, "downhill": 240, "corrida": 241, "brain": 243,
    "nowhere": 218,
}

# 120-tick cards that are messages, not the name of an area (English text)
MESSAGES = {
    "Kick the one with the treasure...",
    "Overboard",
    "Hey! You really should think about shutting down the security system...",
    "YOU LOOSE...",
}


def language_blocks(sec3: bytes) -> dict[str, list[str]]:
    """The six text tables: {language: [raw strings]}, or {} if the section
    has none (cutscenes, menus). A table is found from its first string, the
    pause title (`>CC0 >CY-66 >CP1 `): its first offset points exactly
    there, past the table itself, and the offsets grow."""
    tables = []
    for m in re.finditer(rb">CC0 >CY-66 >CP1 ", sec3):
        first = m.start()
        for base in range(first - 2, max(0, first - 4000), -2):
            offset0 = struct.unpack_from("<H", sec3, base)[0]
            if base + offset0 != first or offset0 % 2:
                continue
            n = offset0 // 2
            table = struct.unpack_from(f"<{n}H", sec3, base)
            if all(table[i] < table[i + 1] for i in range(n - 1)):
                tables.append([sec3[base + o: sec3.index(b"\0", base + o)].decode("latin1") for o in table])
                break
    return dict(zip(LANGUAGES, tables)) if len(tables) == len(LANGUAGES) else {}


def clean(raw: str) -> str:
    """The text as the player reads it: formatting codes and line breaks
    out, spaces collapsed, nothing else touched (typos included)."""
    text = re.sub(r">(CC|CY|CX|CP|W|ID|D|J)[^ \r\n]*", " ", raw)
    return re.sub(r"\s+", " ", text).strip()


def card_indices(blocks, table: list[str]) -> list[int]:
    """The 120-tick cards a level's rules show, in script order: zone rules
    first, then object rules, each index once. `blocks`: loadscript.parse."""
    zone, obj = [], []
    for block in blocks:
        for op, p in block.ops:
            if block.category == 0x09 and op == 0x33 and p[11] == 0x31:
                target, i = zone, struct.unpack_from("<H", p, 12)[0]
            elif block.category in (0x07, 0x08, 0x0A) and op == 0x31 and p[15] == 0x31:
                target, i = obj, struct.unpack_from("<H", p, 16)[0]
            else:
                continue
            if i < len(table) and ">W120" in table[i] and i not in zone and i not in obj:
                target.append(i)
    return zone + obj


def names_of(texts: dict[str, list[str]], indices) -> dict[str, str]:
    """The cards joined by " + " (a file with more areas, as agreed with the
    user), in English and Italian."""
    return {lang: " + ".join(clean(texts[lang][i]) for i in indices) for lang in ("en", "it")}


def candidates(blocks, texts: dict[str, list[str]]) -> list[int]:
    """The level's cards that could name an area: all but the MESSAGES."""
    return [i for i in card_indices(blocks, texts["en"]) if clean(texts["en"][i]) not in MESSAGES]
