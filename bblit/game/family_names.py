"""The names of the families of the Animations menu: what a thing is, by
level and model, for the title of the page ("Merlin" instead of "Model
229"). A model number is a resource number of that level only
(`game/catalog.py`), so the table is keyed by both; where a family is not
here the page shows its number, and the user fills the table as the things
are recognised.

Bugs is not in the table: the player family is named by its category.
"""

from __future__ import annotations

# {(level code in capitals, model): texts.py key}
NAMES = {
    ("MERLIN", 229): "names.merlin",            # 31 parts
    ("MERLIN", 272): "names.merlin_helper",     # 28 parts, the helpers of the trials
    ("L03A", 112): "names.pirate",              # 24 parts
    ("L03A", 276): "names.crab",                # 11 parts
}
PLAYER = "names.bugs"


def name_key(level_code: str, family) -> str | None:
    """The texts.py key of a family's name, or None when it has none yet.
    `family` is a (key, exemplars, record) of `catalog.menu_families`."""
    key, _exemplars, record = family
    if record is not None and record.get("why") == "the player":
        return PLAYER
    if len(key) > 2 and key[1] == "model":
        return NAMES.get((level_code.upper(), key[2]))
    return None
