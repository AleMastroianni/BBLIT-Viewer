"""The names of the Animations menu: what a thing is, for the title of the
page ("Merlin" instead of "Model 229"). Decided by the user, never guessed:
where nothing is written here the page shows the model's number, and the
table is filled as the things are recognised.

A model number is a resource number of that level only (`game/catalog.py`),
so every entry is keyed by the level too. A name is looked for, in order:

1. for the exemplar itself (`EXEMPLARS`, by `catalog.exemplar_id`): Merlin
   at his table in Nowhere is the placed object 40;
2. for the other exemplars of the model, numbered in the family's order
   (`NUMBERED`): the other eight of model 229 are "Merlin-Trial(1)",
   "Merlin-Trial(2)"...;
3. for the model (`MODELS`), which is also the family's name.

Bugs is not in the tables: the player family is named by its category.
The words are texts.py keys, in both languages like the other texts.
"""

from __future__ import annotations

from game import catalog

# {(level code in capitals, model): texts.py key}: the family's name
MODELS = {
    ("MERLIN", 229): "names.merlin",            # 31 parts
    ("MERLIN", 272): "names.merlin_helper",     # 28 parts, the helpers of the trials
    ("L03A", 112): "names.pirate",              # 24 parts
    ("L03A", 276): "names.crab",                # 11 parts
    ("MERLIN", 83): "names.time_machine",       # 11 parts, object 122 at the start
}
# {(level, exemplar id): texts.py key}: one exemplar's own name
EXEMPLARS = {
    ("MERLIN", ("placed", 40)): "names.merlin",  # at his table
}
# {(level, model): texts.py key with {n}}: the exemplars of the model without
# a name of their own, numbered from 1 in the family's order
NUMBERED = {
    ("MERLIN", 229): "names.merlin_trial",
}
PLAYER = "names.bugs"


def family_name(level_code: str, family) -> str | None:
    """The texts.py key of a family's name, or None when it has none yet.
    `family` is a (key, exemplars, record) of `catalog.menu_families`."""
    key, _exemplars, record = family
    if record is not None and record.get("why") == "the player":
        return PLAYER
    if len(key) > 2 and key[1] == "model":
        return MODELS.get((level_code.upper(), key[2]))
    return None


def exemplar_name(level_code: str, family, exemplar_id, index: int) -> tuple[str, dict] | None:
    """(texts.py key, fields) of the name of the family's exemplar number
    `index` (from 0), whose id is `exemplar_id` (None for one no rule
    makes); None when neither it nor its model has a name."""
    level = level_code.upper()
    own = EXEMPLARS.get((level, exemplar_id)) if exemplar_id is not None else None
    if own is not None:
        return own, {}
    key, exemplars, _record = family
    model = key[2] if len(key) > 2 and key[1] == "model" else None
    numbered = NUMBERED.get((level, model)) if model is not None else None
    if numbered is not None:
        n = 0
        for i, e in enumerate(exemplars):
            ident = catalog.exemplar_id(e)
            if ident is not None and (level, ident) in EXEMPLARS:
                continue
            n += 1
            if i == index:
                return numbered, {"n": n}
    name = family_name(level_code, family)
    return (name, {}) if name is not None else None
