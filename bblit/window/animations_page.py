"""Level options -> Animations: the catalogue of the level (`game/catalog.py`)
as one page of horizontal selectors, narrow, over the level.

Step 2 of the agreed order: the page reads, it does not change anything
yet but the animations of the whole level (the entry moved here from Level
options, not duplicated). From the top:

- All animations (playing / paused / starting pose);
- Category and Family, with the number of positions of the selector in
  grey on the right (7 categories, so many families): how many exemplars
  there are, and why a thing is in its category, go in the description;
- the title of the page is the name of the exemplar chosen ("Merlin",
  "Merlin-Trial(3)"), else of its family, from `game/family_names.py`,
  with the model and the parts of its skeleton small under it (the line of
  "whoever has a head" has to stay open to proof); where the tables have
  no name yet, the model's number;
- Which one, "3 of 10", Shift + arrow jumps ten;
- Provenance (what the data says), Spawn (what is seen while playing,
  confirmed in the game, "to be asked" where it is not known yet), When it is there,
  Animations;
- Follow with the camera: the SELECTED row frames its thing (keys, pad and
  mouse all move the selection), and it can be turned off.

When the chosen thing is not there, the description under the list says
why, from the rule that makes it.
"""

from __future__ import annotations

import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyglet.math import Vec3  # noqa: E402

from game import catalog  # noqa: E402
from game import family_names  # noqa: E402
from game import montage  # noqa: E402
from game import geometry as geo  # noqa: E402
from ui import menu as menumod  # noqa: E402
from ui.texts import t  # noqa: E402

# how the selected thing is framed: this far, from above
FRAME_DISTANCE, FRAME_PITCH, FRAME_RAISE = 6.0, -20.0, 1.0
PAGE_WIDTH = 380

# what the helpers of Nowhere do while playing, as seen in the game: Spawn
# is what is seen while playing, never deduced. {(level, model): text key}
SPAWN = {
    ("MERLIN", 272): "anim.spawn.merlin_helpers",
}


# the catalogue's reasons for a category (catalog.category_of), in words
_WHY = {
    "the player": "anim.because.player",
    "a touch by Bugs takes it away": "anim.because.touch_gone",
    "a touch by Bugs adds to a counter": "anim.because.touch_counts",
    "the pushable crate (type 5)": "anim.because.crate",
    "Bugs can pick it up": "anim.because.pick_up",
    "it waits on being held, let go or put down": "anim.because.held",
    "its box changes with its state": "anim.because.box",
    "a looping sprite": "anim.because.sprite_loop",
    "a bullet": "anim.because.bullet",
    "a text": "anim.because.text",
    "a sprite": "anim.because.sprite",
    "a checkpoint": "anim.because.checkpoint",
    "more than one state": "anim.because.states",
    "scenery": "anim.because.scenery",
    "invisible logic": "anim.because.logic",
}


def _why_words(why: str) -> str:
    if why in _WHY:
        return t(_WHY[why])
    m = re.fullmatch(r"a skeleton of (\d+) parts", why)
    if m:
        return t("anim.because.skeleton", n=int(m.group(1)))
    m = re.fullmatch(r"a platform \(type (\d+)\)", why)
    if m:
        return t("anim.because.platform", n=int(m.group(1)))
    return why


class _Which(menumod.Number):
    """"3 of 10": which exemplar of the family. Shift + arrow jumps ten (the
    menu repeats a Number's step), for the big families."""

    def __init__(self, item_key, fetch, store, count, desc=None):
        super().__init__(item_key, fetch, store, 1, max(1, count), desc=desc)
        self.count = count

    def value_text(self):
        return f"‹ {t('anim.which_of', k=self.fetch(), n=self.count)} ›"


class AnimationsPage:
    """Mixed into the viewer window, next to MenuPages."""

    def _anim_reset(self):
        """A new level: the selection goes back to the top, and what was set
        by hand goes (as every option does at a level change)."""
        self.anim_sel = {"category": catalog.CATEGORIES[0], "family": 0, "which": 1}
        self._anim_catalogue_of = None
        self._anim_framed = None
        # what the user set by hand: the roles chosen, the clones shown and
        # hidden (scene.Level, `exceptions`), and the objects held on a
        # frame {anim key: frame}
        self.anim_exceptions = {"roles": {}, "shown": set(), "hidden": set()}
        self.anim_holds = {}

    def _anim_catalogue(self):
        level = self.current_level
        if level is None:
            return None
        cached = getattr(self, "_anim_catalogue_of", None)
        if cached is None or cached[0] is not level:
            cat = catalog.Catalogue(level.lvl, level.sec4, getattr(level, "clone_kinds", None))
            self._anim_catalogue_of = (level, cat)
        return self._anim_catalogue_of[1]

    # ---- the selection

    def _anim_families(self):
        cat = self._anim_catalogue()
        return catalog.menu_families(cat, self.anim_sel["category"]) if cat else []

    def _anim_family(self):
        fams = self._anim_families()
        if not fams:
            return None
        i = max(0, min(self.anim_sel["family"], len(fams) - 1))
        return fams[i]

    def _anim_exemplar(self):
        fam = self._anim_family()
        if fam is None:
            return None
        ex = fam[1]
        return ex[max(0, min(self.anim_sel["which"], len(ex)) - 1)]

    def _anim_set(self, **changes):
        self.anim_sel.update(changes)
        if "category" in changes:
            self.anim_sel["family"], self.anim_sel["which"] = 0, 1
        if "family" in changes:
            self.anim_sel["which"] = 1
        if "which" in changes and self._anim_choose_in_set():
            self._anim_rebuild()
        self.menu.rebuild()

    # ---- what the user sets by hand

    def _anim_rebuild(self):
        """The level again, with the exceptions (the pieces not touched come
        from memory)."""
        level = self.current_level
        path = next((p for p in self.level_files
                     if os.path.splitext(os.path.basename(p))[0] == level.name),
                    os.path.join(level.bze_folder, level.name + ".bze"))
        self.load_level(path, camera=False)

    def _anim_choose_in_set(self) -> bool:
        """Where the game keeps one alive at a time (finding 368: Nowhere's helpers),
        choosing an exemplar is choosing which one is alive: it is shown,
        the others of its set are not built. True when that changed."""
        e = self._anim_exemplar()
        ident = catalog.exemplar_id(e) if e else None
        cat = self._anim_catalogue()
        for members in catalog.one_at_a_time(cat):
            if ident in members:
                ex = self.anim_exceptions
                before = (set(ex["shown"]), set(ex["hidden"]))
                ex["shown"] = (ex["shown"] - members) | {ident}
                ex["hidden"] = (ex["hidden"] - members) | (members - {ident})
                return before != (ex["shown"], ex["hidden"])
        return False

    def _anim_touch(self, e):
        """An exemplar the user has touched is shown whatever Cloned
        templates says (a clone: its route goes to "shown")."""
        ident = catalog.exemplar_id(e)
        if ident is not None and ident[0] != "placed":
            self.anim_exceptions["shown"].add(ident)
        return ident

    def _anim_object_roles(self, e):
        """The animation roles the object plays, in the order of its states
        (the start state first) and of their steps, without repeats."""
        obj = self.current_level.lvl["objects"][e["object"]]
        steps = {s["key"]: s for s in obj.get("steps", ())}
        states = sorted(obj.get("states", ()), key=lambda s: (s["number"] not in (2, 1), s["number"] != 2,
                                                              s["number"]))
        roles = []
        for st in states:
            for k in st["slots"]:
                step = steps.get(k)
                if step is not None and step["role"] not in roles:
                    roles.append(step["role"])
        return roles

    def _anim_current_role(self, e):
        ident = catalog.exemplar_id(e)
        chosen = self.anim_exceptions["roles"].get(ident)
        if chosen is not None:
            return chosen
        obj = self.current_level.lvl["objects"][e["object"]]
        return montage.start_role(obj)

    def _anim_set_role(self, e, role):
        ident = self._anim_touch(e)
        if ident is None:
            return
        self.anim_exceptions["roles"][ident] = role
        key = self._anim_key(e)
        self.anim_holds.pop(key, None)
        self._anim_rebuild()
        self.menu.rebuild()

    def _anim_key(self, e):
        """The anim key of the exemplar's groups, or None when it does not
        animate (or is not built)."""
        ident = catalog.exemplar_id(e)
        if ident is None:
            return None
        level = self.current_level
        key = ("anim", e["object"]) if ident[0] == "placed" else level.clone_anim_keys.get(ident)
        if key is None or not any(g.anim_key == key for g in level.face_groups.values()):
            return None
        return key

    def _anim_frames(self, e):
        key = self._anim_key(e) if e else None
        if key is None:
            return 1
        # the frames' buffers on the card: the lists are freed after the upload
        return max([len(g.vaos) for g in self.current_level.face_groups.values()
                    if g.anim_key == key] + [1])

    def _anim_frame_now(self, e):
        key = self._anim_key(e)
        n = self._anim_frames(e)
        if key is None:
            return 0
        hold = self.anim_holds.get(key)
        return (self.anim_frame(key, n) if hold is None else hold) % n

    def _anim_set_flow(self, e, flow):
        key = self._anim_key(e)
        if key is None:
            return
        if flow == "still":
            self.anim_holds[key] = self._anim_frame_now(e)
        else:
            self.anim_holds.pop(key, None)

    def _anim_set_frame(self, e, k):
        key = self._anim_key(e)
        if key is not None:
            self.anim_holds[key] = (k - 1) % self._anim_frames(e)

    # ---- words

    def _anim_count_words(self, exemplars):
        total, at_start, by_itself, by_bugs, never = catalog.numbers(exemplars)
        parts = [t("anim.n_at_start", n=at_start)]
        if by_itself:
            parts.append(t("anim.n_by_itself", n=by_itself))
        if by_bugs:
            parts.append(t("anim.n_by_bugs", n=by_bugs))
        if never:
            parts.append(t("anim.n_never", n=never))
        how_many = t("anim.n_exemplar" if total == 1 else "anim.n_exemplars", n=total)
        text = how_many + ", " + ", ".join(parts) + "."
        if self.anim_sel["category"] == "collectables":
            text += " " + t("anim.new_game")
        return text

    def _anim_family_label(self, key, exemplars, fam):
        """The family's name (`family_names`), else what it is by number."""
        name = family_names.family_name(self.current_level.name, (key, exemplars, fam))
        if name is not None:
            return t(name)
        return self._anim_family_number(key)

    def _anim_family_number(self, key):
        if key[0] == "rest":
            return t(f"anim.fam.{key[1]}")
        kind, number = key[1], key[2]
        if kind == "model":
            return t("anim.fam.model", n=number)
        if kind == "sprite":
            return t("anim.fam.sprite", n=number)
        return t("anim.fam.type", n=number)

    def _anim_title(self):
        """The title of the page: the name of what is being looked at, the
        exemplar's own, else its family's."""
        fam = self._anim_family() if self.current_level is not None else None
        if fam is None:
            return t("menu.anim")
        e = self._anim_exemplar()
        index = max(0, min(self.anim_sel["which"], len(fam[1])) - 1)
        name = family_names.exemplar_name(self.current_level.name, fam,
                                          catalog.exemplar_id(e) if e else None, index)
        if name is not None:
            return t(name[0], **name[1])
        return self._anim_family_label(*fam)

    def _anim_subtitle(self):
        """Under the title, small: the page, and for a named family its
        number; for a character the parts of its skeleton."""
        fam = self._anim_family() if self.current_level is not None else None
        if fam is None:
            return ""
        key, exemplars, record = fam
        bits = [t("menu.anim")]
        if family_names.family_name(self.current_level.name, fam) is not None and key[0] != "rest":
            bits.append(self._anim_family_number(key))
        if key[0] == "characters" and record is not None:
            level = self.current_level
            obj = level.lvl["objects"][record["objects"][0]]
            parts = catalog.skeleton_parts(obj, level.res, level.sec4)
            if parts:
                bits.append(t("anim.parts", n=parts))
        return " · ".join(bits)

    def _anim_provenance(self, e):
        if e is None:
            return "—"
        p = e["provenance"]
        if p in (catalog.CLONED, catalog.HELD_AT_BONE):
            return t(f"anim.prov.{p}", n=e["parent"])
        return t(f"anim.prov.{p}")

    def _anim_when(self, e):
        if e is None:
            return "—"
        if e["at_start"]:
            return t("anim.when.start")
        reason = catalog.why_not(self._anim_catalogue(), e)
        code = reason[0] if reason else "later"
        return t({"never_made": "anim.when.never", "passing": "anim.when.moment",
                  "by_itself": "anim.when.by_itself",
                  "gone_first_tick": "anim.when.gone"}.get(code, "anim.when.later"))

    def _anim_why(self, e):
        """The sentence under the list for the chosen exemplar: what it is,
        and when it is not there, why."""
        if e is None:
            return t("anim.none")
        cat = self._anim_catalogue()
        lines = []
        category, why = cat.category[e["object"]]
        if category == "rest" and why == "invisible logic":
            lines.append(t("anim.why.invisible"))
        reason = catalog.why_not(cat, e)
        if reason is None:
            if e["provenance"] in (catalog.CLONED, catalog.HELD_AT_BONE) and self.show_clones < 1:
                lines.append(t("anim.why.clones_off"))
            else:
                lines.append(t("anim.why.there"))
        else:
            code, numbers = reason
            if code == "chain":
                steps = " → ".join(t(f"anim.step.{kind}", **nums) for kind, nums in numbers["steps"])
                lines.append(t("anim.why.chain", steps=steps, parent=numbers["parent"]))
            elif code == "byte":
                writers = ", ".join(f"#{n}" for n in numbers["writers"][:6]) or t("anim.why.nobody")
                lines.append(t(f"anim.why.byte_{numbers['table']}", index=numbers["index"],
                               writers=writers))
            else:
                lines.append(t(f"anim.why.{code}", **numbers))
            if self.show_clones >= 2 and code not in ("never_made",):
                lines.append(t("anim.why.all_on"))
        if category == "collectables":
            lines.append(t("anim.new_game"))
        lines.append(t("anim.object", n=e["object"]))
        return " ".join(lines)

    def _anim_spawn(self, fam):
        level = self.current_level
        if fam is None or fam[2] is None or level is None:
            return t("anim.spawn.ask")
        key = SPAWN.get((level.name.upper(), fam[2]["model"]))
        return t(key) if key else t("anim.spawn.ask")

    # ---- the page

    def _anim_items(self):
        M = menumod
        if self.current_level is None or self._anim_catalogue() is None:
            return [M.Info(lambda: t("level.no_level")), M.Back()]
        cat = self._anim_catalogue()
        # the grey number beside a selector whose value is a name: how many
        # positions it has (where the value says "3 of 10" there is none)
        every = M.Choice("anim.all", [("playing", "level.anim.playing"), ("paused", "level.anim.paused"),
                                      ("pose", "level.anim.pose")],
                         self._animation_state, self._set_animation_state, "desc.animations")
        every.note = lambda: "3"
        items = [every]
        category = M.Choice("anim.category",
                            [(c, lambda c=c: t(f"anim.cat.{c}")) for c in catalog.CATEGORIES],
                            lambda: self.anim_sel["category"],
                            lambda c: self._anim_set(category=c),
                            desc=lambda: self._anim_category_desc(cat))
        category.note = lambda: str(len(catalog.CATEGORIES))
        items.append(category)
        fams = self._anim_families()
        if not fams:
            items.append(M.Info(lambda: t("anim.family"), lambda: t("anim.none_here")))
        else:
            family = M.Choice("anim.family",
                              [(i, lambda f=f: self._anim_family_label(*f)) for i, f in enumerate(fams)],
                              lambda: min(self.anim_sel["family"], len(fams) - 1),
                              lambda i: self._anim_set(family=i),
                              desc=lambda: self._anim_family_desc())
            family.note = lambda n=len(fams): str(n)
            items.append(family)
            count = len(self._anim_family()[1])
            items.append(_Which("anim.which", lambda: min(self.anim_sel["which"], count),
                                lambda k: self._anim_set(which=k), count,
                                desc=lambda: self._anim_why(self._anim_exemplar())))
            items.append(M.Info(lambda: t("anim.provenance"),
                                lambda: self._anim_provenance(self._anim_exemplar())))
            items.append(M.Info(lambda: t("anim.spawn"), lambda: self._anim_spawn(self._anim_family())))
            items.append(M.Info(lambda: t("anim.when"), lambda: self._anim_when(self._anim_exemplar())))
            items.extend(self._anim_play_items())
        items.append(M.YesNo("anim.follow", lambda: self.anim_follow,
                             lambda v: setattr(self, "anim_follow", v), "desc.anim_follow"))
        items.append(M.Back())
        return items

    def _anim_category_desc(self, cat):
        """Who ends up in the category and why, then how many."""
        c = self.anim_sel["category"]
        exemplars = [e for f in cat.families[c] for e in f["exemplars"]]
        return t(f"anim.cat_rule.{c}", parts=catalog.HEAD_PARTS) + " " + self._anim_count_words(exemplars)

    def _anim_family_desc(self):
        fam = self._anim_family()
        if fam is None:
            return ""
        key, exemplars, record = fam
        why = _why_words(record["why"]) if record else t(f"anim.because.{key[1]}")
        return why + " " + self._anim_count_words(exemplars)

    def _anim_play_items(self):
        """Animation, How it runs, Frame: for the chosen exemplar."""
        M = menumod
        e = self._anim_exemplar()
        if e is None or catalog.exemplar_id(e) is None:
            return [M.Info(lambda: t("anim.anim"), lambda: t("anim.cannot"))]
        roles = self._anim_object_roles(e)
        items = []
        if roles:
            items.append(M.Choice("anim.anim",
                                  [(r, lambda i=i, r=r: t("anim.which_of", k=i + 1, n=len(roles)))
                                   for i, r in enumerate(roles)],
                                  lambda: self._anim_current_role(e) if self._anim_current_role(e) in roles
                                  else roles[0],
                                  lambda r: self._anim_set_role(e, r),
                                  desc=lambda: t("anim.desc_anim", r=self._anim_current_role(e))))
        else:
            items.append(M.Info(lambda: t("anim.anim"), lambda: t("anim.none_here")))
        flow = M.Choice("anim.flow", [("loop", "anim.flow.loop"), ("still", "anim.flow.still")],
                        lambda: "still" if self._anim_key(e) in self.anim_holds else "loop",
                        lambda v: self._anim_set_flow(e, v), desc="desc.anim_flow")
        flow.note = lambda: "2"
        items.append(flow)
        frames = _Which("anim.frame", lambda: self._anim_frame_now(e) + 1,
                        lambda k: self._anim_set_frame(e, k), self._anim_frames(e), desc="desc.anim_frame")
        frames.live = True          # it moves while the animation plays
        items.append(frames)
        return items

    # ---- following the selection with the camera

    def anim_follow_tick(self):
        """Called every frame: when the Animations page is on top and the
        selection changed, the camera frames the chosen thing."""
        menu = self.menu
        if not (menu.is_open and menu.stack and menu.stack[-1][0] == "animations"):
            self._anim_framed = None
            return
        if not self.anim_follow or self.current_level is None:
            return
        e = self._anim_exemplar()
        key = (id(self.current_level), self.anim_sel["category"], self.anim_sel["family"],
               self.anim_sel["which"])
        if key == self._anim_framed:
            return
        self._anim_framed = key
        place = catalog.place_of(self._anim_catalogue(), e) if e is not None else None
        if place is None:
            return
        target = Vec3(*geo._transform((0, 0, 0), pos=place)) + Vec3(0.0, FRAME_RAISE, 0.0)
        j, p = math.radians(self.yaw), math.radians(FRAME_PITCH)
        forward = Vec3(math.cos(j) * math.cos(p), math.sin(p), math.sin(j) * math.cos(p))
        self.pos = target - forward * FRAME_DISTANCE
        self.pitch = FRAME_PITCH
