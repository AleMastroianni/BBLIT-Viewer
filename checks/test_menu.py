"""Test of the menu logic, without touching the user's settings.

    .venv/Scripts/python checks/test_menu.py

Opens the viewer in photo mode (settings off), re-enables the keyboard and
drives the menu from code: navigation, yes/no, per-session group states,
animations, ticks, language, Esc reopening where it was left, Load level by
era, Extra and Era selector, drawing of every page. Does not call app.run.
"""
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
import pyglet
from game import geometry as geo
from support import paths
from support import preferences
from support.version import VERSION
from ui import settings as settings_mod
from ui import menu as menumod
from ui import texts
import viewer

try:
    from support import private_export
except ImportError:
    private_export = None

k = pyglet.window.key
file_paths = [os.path.join(paths.DATA_BZE, f) for f in ("L03A.bze", "L03A2.bze", "CC3A.bze", "LS01.bze")]
v = viewer.Viewer(file_paths, "extracted", 0, screenshot="nessuna.png")
v.screenshot = None   # the keyboard becomes active again; settings stay off
results = []


def probe(entry_name, cond):
    results.append((entry_name, bool(cond)))
    print(("OK   " if cond else "FAIL ") + entry_name)


def press(s, mod=0):
    return v.on_key_press(s, mod)


# the kind of copy is in the title: "Debug" here, the folder's kind in the
# other copies (Current, Development, Portable)
probe("title with the build", v.build == settings_mod.build() and v.build != ""
      and v.caption.endswith(v.build))
probe("flags off at startup: no overlay family built",
      not v.current_level.families
      and not any(g.category in viewer.OVERLAYS for g in v.current_level.face_groups.values()))
probe("English by default", texts.language() == "en")
texts.set_language("it")   # the test uses the Italian labels
probe("menu closed at startup", not v.menu.is_open)
press(k.ESCAPE)
probe("Esc opens the menu", v.menu.is_open and v.menu.stack[-1][0] == "main")
v.signature_drawn = False
v.on_draw()
probe("main menu: signature on the background, no Credits",
      v.signature_drawn and v.signature.text == "BBLIT Viewer by AleMastroianni"
      and not any("redit" in x.label() for x in v.menu.stack[-1][1]))
# down to Level options (entry 2) and Enter
press(k.DOWN); press(k.DOWN); press(k.ENTER)
probe("Level options open", v.menu.stack[-1][0] == "level")
v.signature_drawn = False
v.on_draw()
probe("no signature on the other pages", not v.signature_drawn)
menu_items = v.menu.stack[-1][1]
labels = [x.label() for x in menu_items]
i_sky = labels.index("Cielo")
v.menu.stack[-1][2] = i_sky
before = v.show_sky
press(k.ENTER)
probe("Enter on Cielo toggles it", v.show_sky == (not before))
press(k.LEFT)
probe("arrow on Cielo restores it", v.show_sky == before)
probe("key H with the menu open does NOT reach the scene", (press(k.H), v.show_sky == before)[1])

probe("Flags is the first entry of Level options", labels[0] == "Flags")
v.menu.stack[-1][2] = 0
press(k.ENTER)
flag = [x.label() for x in v.menu.stack[-1][1]]
probe("Flags: All off first, then in groups (walls and ground, zones, boxes), all off by default",
      v.menu.stack[-1][0] == "flags"
      and [x for x in flag if x] == ["Spegni tutte le flag", "Muri", "Terreno di collisione",
                                     "Senza collisione", "Portali", "Zone di morte e danno",
                                     "Zone di teletrasporto", "Box di collisione", "Chi apre cosa",
                                     "Etichette flag", "Indietro"]
      and v.show_hard_walls == "off" and v.show_steps == "off"
      and not (v.show_no_collision or v.show_collision_boxes
               or v.show_death_zones or v.show_teleport_zones))
# Flags -> Muri: Hard walls and Steps three-way, edges over holes, area
# boxes, outside side
v.menu.stack[-1][2] = flag.index("Muri")
press(k.ENTER)
walls_labels = [x.label() for x in v.menu.stack[-1][1]]
probe("Muri: Muri duri, Gradini, bordi sui buchi, Box delle aree, Lato di fuori",
      v.menu.stack[-1][0] == "walls"
      and walls_labels == ["Muri duri", "Gradini", "Gradini: bordi sui buchi", "Box delle aree",
                           "Lato di fuori", "Indietro"])
i_outside = walls_labels.index("Lato di fuori")
probe("Muri: the walls' outside side, on by default", v.show_walls_outside)
v.menu.stack[-1][2] = i_outside
press(k.ENTER)
probe("Enter hides the outside side", not v.show_walls_outside)
press(k.ENTER)
probe("Muri: edges over holes, off by default", not v.show_hole_steps)
v.menu.stack[-1][2] = 0
press(k.RIGHT)
probe("Muri duri -> Tutti, and the heightmap family is built",
      v.show_hard_walls == "all" and "heightmap" in v.current_level.families)
hard_groups = {g.category for g in v.current_level.face_groups.values() if g.category.startswith(("hard_walls", "invisible_walls"))}
probe("hard walls: panels, coloured faces, outlines and names, from both sides",
      {"hard_walls", "hard_walls_faces", "hard_walls_lines", "hard_walls_label", "hard_walls_outside",
       "invisible_walls", "invisible_walls_lines"} <= hard_groups)
shown_all = {c for c in hard_groups if v._overlay_shown(c)}
press(k.RIGHT)
shown_unseen = {c for c in hard_groups if v._overlay_shown(c)}
probe("Muri duri -> Solo invisibili: only the invisible_walls groups and their outline",
      v.show_hard_walls == "unseen" and "hard_walls" in shown_all and "invisible_walls" in shown_all
      and "hard_walls_lines" in shown_all and "invisible_walls_lines" not in shown_all
      and shown_unseen and all(c.startswith("invisible_walls") for c in shown_unseen)
      and "invisible_walls_lines" in shown_unseen)
press(k.RIGHT)
probe("Muri duri -> No", v.show_hard_walls == "off" and not any(v._overlay_shown(c) for c in hard_groups))
v.menu.stack[-1][2] = 1
press(k.RIGHT)
step_groups = {g.category for g in v.current_level.face_groups.values() if g.category.startswith(("step_walls", "hole_steps"))}
shown_steps = {c for c in step_groups if v._overlay_shown(c)}
probe("Gradini -> Tutti: the uncovered and the covered steps, no hole steps without the option",
      v.show_steps == "all" and "step_walls" in shown_steps and "step_walls_covered" in shown_steps
      and "step_walls_all_lines" in shown_steps and not any(c.startswith("hole") for c in shown_steps))
v.show_hole_steps = True
probe("with edges over holes the hole steps show too", v._overlay_shown("hole_steps"))
v.show_hole_steps = False
press(k.RIGHT)
shown_steps = {c for c in step_groups if v._overlay_shown(c)}
probe("Gradini -> Solo invisibili: the covered steps go", v.show_steps == "unseen"
      and "step_walls" in shown_steps and "step_walls_lines" in shown_steps
      and "step_walls_covered" not in shown_steps and "step_walls_all_lines" not in shown_steps)
press(k.RIGHT)
probe("Gradini -> No", v.show_steps == "off")
press(k.BACKSPACE)
probe("Backspace from Muri returns to Flags", v.menu.stack[-1][0] == "flags")
flag_attrs = ["show_no_collision", "show_collision_boxes", "show_death_zones", "show_teleport_zones"]
flag_rows = ["Senza collisione", "Box di collisione", "Zone di morte e danno", "Zone di teletrasporto"]
turned_on = []
for row, attr in zip(flag_rows, flag_attrs):
    v.menu.stack[-1][2] = flag.index(row)
    press(k.ENTER)
    turned_on.append(getattr(v, attr))
    press(k.ENTER)
probe("Enter turns each flag on and off again", all(turned_on)
      and not any(getattr(v, a) for a in flag_attrs))
# Spegni tutte le flag: every flag back off, Flag labels untouched
v.show_no_collision, v.show_death_zones, v.show_hard_walls = True, True, "all"
v.ensure_overlays()
v.show_flag_labels = False
v.menu.stack[-1][2] = flag.index("Spegni tutte le flag")
press(k.ENTER)
probe("All flags off: the flags and Walls back off, Flag labels as it was",
      not v.show_no_collision and not v.show_death_zones and v.show_hard_walls == "off"
      and not v.show_flag_labels)
v.show_flag_labels = True
probe("turning a flag on builds its family; off only hides it",
      v.current_level.families == set(viewer.FAMILIES)
      and {g.category for g in v.current_level.face_groups.values()} >= {
          "invisible_walls", "no_collision", "collision_boxes", "death_zones", "death_zones_label"})   # L03A: sea only
# Flags -> Flag labels: last, after an empty row; off hides only the words
flags_items = v.menu.stack[-1][1]
probe("Flag labels is the last entry of Flags, after an empty row",
      flags_items[-2].label() == "Etichette flag" and isinstance(flags_items[-3], menumod.Section)
      and v.show_flag_labels)
v.show_no_collision = True
v.ensure_overlays()
label_groups = [g for g in v.current_level.face_groups.values() if isinstance(g.tex_id, str)]
v.menu.stack[-1][2] = len(flags_items) - 2
press(k.ENTER)
probe("Flag labels off: the flags stay on, their words are texture groups of their own",
      not v.show_flag_labels and v.show_no_collision and label_groups
      and all(g.category.endswith("_label") for g in label_groups))
press(k.ENTER)
v.show_no_collision = False
press(k.BACKSPACE)
probe("Backspace from Flags returns to Level options", v.menu.stack[-1][0] == "level")
v.menu.hide()
for sym in (k.I, k.C, k.B, k.Z, k.K):
    press(sym)
probe("the flags have no keys", not any(getattr(v, a) for a in flag_attrs)
      and v.show_hard_walls == "off" and v.show_steps == "off")
v.menu.reopen()

i_bridges = labels.index("Ponti levatoi")
v.menu.stack[-1][2] = i_bridges
probe("bridges lowered by default (121)", v.current_level.pref["pose"][217] == 121)
press(k.RIGHT)   # 121 is the last one: wraps to the first, 118 raised
probe("bridges raised for the session (118)", v.current_level.pref["pose"][217] == 118
      and v.session_poses["L03A"][217] == 118)
probe("preferences.py not touched", preferences.for_level("L03A")["pose"][217] == 121)
probe("menu still on Level options after the rebuild", v.menu.stack[-1][0] == "level")

# the animations of the whole level moved into Level options -> Animations
# (one place to change a thing, not two)
probe("Level options: Animations is a submenu now, not a choice",
      isinstance(v.menu.stack[-1][1][labels.index("Animazioni")], menumod.Submenu))
v.menu.stack[-1][2] = labels.index("Animazioni")
press(k.ENTER)
anim_labels = [x.label() for x in v.menu.stack[-1][1]]
probe("the Animations page opens", v.menu.stack[-1][0] == "animations")
v.menu.stack[-1][2] = anim_labels.index("Tutte le animazioni")
press(k.RIGHT)
probe("Tutte le animazioni -> Ferme (frozen)", v.paused and v.fixed_tick is None)
press(k.RIGHT)
probe("Tutte le animazioni -> Posa iniziale (initial pose)", v.fixed_tick == 0 and not v.paused)
press(k.RIGHT)
probe("Tutte le animazioni -> In movimento (moving)", v.fixed_tick is None and not v.paused)
press(k.BACKSPACE)
probe("back on Level options", v.menu.stack[-1][0] == "level")

i_tps = labels.index("Tick al secondo")
v.menu.stack[-1][2] = i_tps
press(k.RIGHT, k.MOD_SHIFT)
probe("Shift+right: tick +10", v.tps == 25)
press(k.RIGHT, k.MOD_SHIFT); press(k.RIGHT, k.MOD_SHIFT); press(k.RIGHT, k.MOD_SHIFT)
probe("three more times: 55", v.tps == 55)
press(k.RIGHT, k.MOD_SHIFT)
probe("tick capped at 60", v.tps == 60)

press(k.BACKSPACE)
probe("Backspace returns to the main menu", v.menu.stack[-1][0] == "main")
v.menu.stack[-1][2] = 4   # General options
press(k.ENTER)
press(k.RIGHT)           # Lingua -> English
probe("English language", texts.language() == "en" and v.menu.stack[-1][1][0].label().startswith("Language"))
probe("title translated, with version and build", v.caption == f"BBLIT Viewer {VERSION} — {v.build}")
press(k.LEFT)
probe("Italian language", texts.language() == "it")
press(k.M)
press(k.ESCAPE)
probe("Esc closes the menu", not v.menu.is_open)
press(k.H)
probe("with the menu closed H reaches the scene again", v.show_sky == (not before))

# load level: Pirati -> Parte 2 (L03A2)
press(k.ESCAPE)
v.menu.stack[-1][2] = 1
press(k.ENTER)
era_labels = [x.label() for x in v.menu.stack[-1][1]]
# Extra (the cutscenes, the `_8` variants) is in the Debug build only: the
# other copies hide it on purpose, and there the Extra probes are skipped
debug_build = v.build == "Debug"
probe("Load level: Ere first, the five eras, Nowhere below Dimensione X, then Extra (Debug build only)",
      era_labels[:7] == ["Ere", "Età della pietra", "Medioevo", "Pirati", "Anni '30", "Dimensione X", "Nowhere"]
      and ("Extra" in era_labels) == debug_build)
v.menu.stack[-1][2] = era_labels.index("Pirati")
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
i = next(i for i, x in enumerate(menu_items) if x.selectable and x.value_text().startswith("L03A2"))
v.menu.stack[-1][2] = i
probe("description with LevID 23", "LevID 23" in menu_items[i].desc())
press(k.ENTER)
probe("Pirati -> Parte 2: L03A2 loaded, and the menu open by itself on its main page with Level options",
      v.current_level.name.upper() == "L03A2" and v.menu.is_open
      and [x[0] for x in v.menu.stack] == ["main"]
      and "Opzioni livello" in [x.label() for x in v.menu.stack[-1][1]])
press(k.ESCAPE)
probe("Esc closes it", not v.menu.is_open)
press(k.ESCAPE)
probe("Esc reopens where it was left (the main page)", v.menu.is_open and [x[0] for x in v.menu.stack] == ["main"])
if debug_build:
    v.menu.open_page("load")
    v.menu.stack[-1][2] = [x.label() for x in v.menu.stack[-1][1]].index("Extra")
    press(k.ENTER)
    menu_items = v.menu.stack[-1][1]
    page_labels = [x.label() for x in menu_items]
    probe("Extra: _8 variants and Cutscenes, no Era selector and no Nowhere (Debug build)",
          "Nowhere" not in page_labels and "Era selector" not in page_labels
          and "Vista d'insieme" not in page_labels and
          "Filmati" in page_labels and any((x.value_text() or "").startswith("L03A_8") for x in menu_items)
          and not any(x.selectable and (x.value_text() or "")[:2] in ("CC", "TI", "CR") for x in menu_items))
    v.menu.stack[-1][2] = page_labels.index("Filmati")
    press(k.ENTER)
    menu_items = v.menu.stack[-1][1]
    v.menu.stack[-1][2] = next(i for i, x in enumerate(menu_items)
                               if x.selectable and x.value_text().startswith("CC3A"))
    press(k.ENTER)
    probe("Extra -> Cutscenes -> CC3A cutscene loaded, the menu on its main page",
          v.current_level.name.upper() == "CC3A" and [x[0] for x in v.menu.stack] == ["main"])
v.menu.open_page("load")
v.menu.stack[-1][2] = [x.label() for x in v.menu.stack[-1][1]].index("Ere")
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
page_labels = [x.label() for x in menu_items]
probe("Ere: the Era selector, with the title only once, the overview and the five eras",
      v.menu.stack[-1][0] == "eras" and page_labels.count("Era selector") == 1
      and [x.label() for x in menu_items if x.selectable][:6] == [
          "Vista d'insieme", "Età della pietra", "Medioevo", "Pirati", "Anni '30", "Dimensione X"])
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Pirati"][0]
press(k.ENTER)
# the pirate island is collision block 3 (its camera used to be the Stone
# Age's)
probe("Ere -> Pirati: LS01 with the camera on the pirate island",
      v.current_level.name.upper() == "LS01" and (round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1)) == (62.1, 164.4, -116.2))
before = v.current_level
probe("Ere -> Pirati loaded LS01: the menu on its main page", [x[0] for x in v.menu.stack] == ["main"])
v.menu.open_page("load"); v.menu.open_page("eras")
menu_items = v.menu.stack[-1][1]
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Età della pietra"][0]
press(k.ENTER)
probe("Ere -> Età della pietra: the camera on the canyon (block 0)",
      (round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1)) == (20.0, 23.8, 17.5))
press(k.ESCAPE)
menu_items = v.menu.stack[-1][1]
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Dimensione X"][0]
press(k.ENTER)
probe("Ere -> Dimensione X: the camera over the walkable ground of block 5",
      (round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1)) == (135.2, -100.6, -141.2))
press(k.ESCAPE)
menu_items = v.menu.stack[-1][1]
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Medioevo"][0]
press(k.ENTER)
probe("Ere -> Medioevo with LS01 already open: only moves the camera",
      v.current_level is before and round(v.pos.z, 1) == -4.7 and not v.menu.is_open)
build = v.build
v.build = "Portable"
v.menu.show("main"); v.menu.open_page("extra")
probe("in another build Extra does not show Cutscenes but keeps the _8 variants",
      "Filmati" not in [x.label() for x in v.menu.stack[-1][1]]
      and any((x.value_text() or "").startswith("L03A_8") for x in v.menu.stack[-1][1]))
v.build = build

# Camera and points (glitch hunting, stage 3): bookmarks, shadow point, export
import re  # noqa: E402
from game import collision  # noqa: E402
from pyglet.math import Vec3  # noqa: E402
clipboard = []
v.set_clipboard_text = clipboard.append       # the user's clipboard is not touched
v._open_level(0)
level = v.current_level
# a camera 100 units above the ground at the centre of a block, inside its slab
b, g = next((b, g) for b in level.collision_blocks
            if (g := b.ground_height(b.ox + b.ext_x // 2, b.oz + b.ext_z // 2)) is not None
            and g - 100 > b.y_ceiling)
gx, gz = b.ox + b.ext_x // 2, b.oz + b.ext_z // 2
u = geo.UNITS_PER_METER
v.pos, v.yaw, v.pitch = Vec3(gx / u, -(g - 100) / u, -gz / u), 12.5, -80.0
v.menu.show("main"); v.menu.open_page("level")
probe("Camera e punti is the second entry of Level options", v.menu.stack[-1][1][1].label() == "Camera e punti")
v.menu.stack[-1][2] = 1
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
labels = [x.label() for x in menu_items]
probe("Camera e punti: camera, shadow point, shadow off, no bookmarks yet",
      v.menu.stack[-1][0] == "camera" and labels[:3] == ["Camera", "Punto ombra", "Mostra l'ombra"]
      and not v.show_camera_shadow and "Nessun segnalibro" in labels)
probe("the shadow point is the ground of the block under the camera",
      v._shadow_of(v.pos) == ((gx, g, gz), b) and menu_items[1].value_text().startswith(f"{gx}, {g}, {gz}"))
if private_export is not None:      # the private copies only
    v.menu.stack[-1][2] = labels.index(texts.t("camera.copy_ce"))
    press(k.ENTER)
    m = re.match(r"BBLIT L03A x=(-?\d+) y=(-?\d+) z=(-?\d+)", clipboard[-1] if clipboard else "")
    probe("private copy: the line of private_export, with the shadow point",
          m is not None and tuple(int(w) for w in m.groups()) == (gx, g, gz))
else:
    probe("public copy: no private entry", texts.t("camera.copy_ce") == "camera.copy_ce")
v.menu.stack[-1][2] = labels.index("Copia il punto per BizHawk (Lua)")
press(k.ENTER)
probe("copy for BizHawk: a Lua table entry, and 'copiato'",
      clipboard[-1].startswith(f"{{ X = {gx}, Y = {g}, Z = {gz} }}, -- BBLIT L03A")
      and v.menu.stack[-1][1][v.menu.stack[-1][2]].value_text() == "copiato ✓")
all_item = menu_items[labels.index("Copia tutti i segnalibri per BizHawk")]
probe("copy every bookmark is greyed out without bookmarks", all_item.disabled)
v.menu.stack[-1][2] = labels.index("Aggiungi segnalibro qui")
press(k.ENTER)
v.pos = Vec3(v.pos.x + 1.0, v.pos.y, v.pos.z)
press(k.ENTER)
marks = v.user_settings["bookmarks"].get("L03A", [])
labels = [x.label() for x in v.menu.stack[-1][1]]
probe("two bookmarks added, saved per level in game units, listed on the page",
      [mk["n"] for mk in marks] == [1, 2] and marks[0]["y"] == g - 100 and marks[0]["pitch"] == -80.0
      and "Segnalibro 1" in labels and "Segnalibro 2" in labels
      and settings_mod.DEFAULTS["bookmarks"] == {})
v.menu.stack[-1][2] = labels.index("Copia tutti i segnalibri per BizHawk")
press(k.ENTER)
lua_lines = clipboard[-1].splitlines()
probe("copy every bookmark: a Lua table with both",
      lua_lines[1] == "local punti_L03A = {" and len(lua_lines) == 5 and lua_lines[-1] == "}"
      and "Segnalibro 2" in lua_lines[3])
v.menu.stack[-1][2] = labels.index("Segnalibro 1")
press(k.ENTER)
probe("a bookmark opens its page", v.menu.stack[-1][0] == "bookmark"
      and v.menu.pages["bookmark"].title_text() == "Segnalibro 1 — L03A")
v.pos, v.yaw, v.pitch = Vec3(0.0, 50.0, 0.0), 0.0, 0.0
labels = [x.label() for x in v.menu.stack[-1][1]]
v.menu.stack[-1][2] = labels.index("Vai qui")
press(k.ENTER)
probe("Vai qui: camera back at the bookmark, menu closed",
      v._game_point(v.pos) == (gx, g - 100, gz) and (v.yaw, v.pitch) == (12.5, -80.0) and not v.menu.is_open)
press(k.ESCAPE)
probe("Esc reopens the bookmark page", v.menu.stack[-1][0] == "bookmark")
v.pos = Vec3(v.pos.x, v.pos.y + 2.0, v.pos.z)
v.menu.stack[-1][2] = labels.index("Sostituisci con la camera attuale")
press(k.ENTER)
marks = v.user_settings["bookmarks"]["L03A"]
probe("Sostituisci: same number, new position",
      marks[0]["n"] == 1 and marks[0]["y"] == g - 100 - 256
      and v.menu.stack[-1][1][v.menu.stack[-1][2]].value_text() == "sostituito ✓")
v.menu.stack[-1][2] = labels.index("Elimina")
press(k.ENTER)
probe("Elimina asks first", len(v.user_settings["bookmarks"]["L03A"]) == 2
      and v.menu.stack[-1][1][v.menu.stack[-1][2]].label() == "Conferma: elimina")
press(k.ENTER)
labels = [x.label() for x in v.menu.stack[-1][1]]
probe("Conferma: elimina removes it and goes back to the list",
      [mk["n"] for mk in v.user_settings["bookmarks"]["L03A"]] == [2] and v.menu.stack[-1][0] == "camera"
      and "Segnalibro 1" not in labels and "Segnalibro 2" in labels)
probe("a bookmark written by hand with a wrong value is left out, not an error",
      (v.user_settings.__setitem__("bookmarks", {"L03A": [{"n": 1, "x": "a"}, *v.user_settings["bookmarks"]["L03A"]]}),
       [mk["n"] for mk in v._bookmarks()] == [2])[1])

# F1: the interface covered; the open menu takes nothing
v.menu.stack[-1][2] = 2        # Mostra l'ombra
v.on_draw()      # the rows' areas of this page
press(k.F1)
press(k.ENTER); press(k.DOWN)
row = next(a for a in v.menu._areas if a[2] == 3)
v.on_mouse_motion(10, (row[0] + row[1]) // 2, 0, 0)
v.on_mouse_press(10, (row[0] + row[1]) // 2, pyglet.window.mouse.LEFT, 0)
v.on_mouse_scroll(10, (row[0] + row[1]) // 2, 0, 1)
probe("F1 covers: Enter, arrows, mouse over, click and wheel do nothing to the menu",
      v.ui_hidden and v.menu.is_open and v.menu.stack[-1][2] == 2 and not v.show_camera_shadow
      and len(v.user_settings["bookmarks"]["L03A"]) == 2)
before = v._game_point(v.pos)
v.held_keys.add(k.W); v.update(0.1); v.held_keys.clear()
probe("covered: the camera moves even with the menu open", v._game_point(v.pos) != before)
v.menu.show("main")
v.signature_drawn = False
v.on_draw()
probe("covered: nothing drawn over the scene (no signature on the main page)", not v.signature_drawn)
v.menu.open_page("level"); v.menu.open_page("camera")
press(k.ESCAPE)
probe("Esc while covered only uncovers", not v.ui_hidden and v.menu.is_open and v.menu.stack[-1][0] == "camera")
press(k.ENTER)
probe("uncovered: Enter works again (Mostra l'ombra on)", v.show_camera_shadow)
try:
    v.on_draw()
    ok = True
except Exception as e:  # noqa: BLE001
    print(e)
    ok = False
probe("the shadow circle draws", ok)
v.show_camera_shadow = False

# Keys and gamepad (as in the CTR viewer): Help -> Keyboard / Gamepad
from ui import keybinds  # noqa: E402
kbp = v.keyboard_page
v.menu.show("main")
v.menu.stack[-1][2] = [x.label() for x in v.menu.stack[-1][1]].index("Aiuto")
press(k.ENTER)
probe("Aiuto: Tastiera, Gamepad, Informazioni, Indietro",
      [x.label() for x in v.menu.stack[-1][1]] == ["Tastiera", "Gamepad", "Informazioni", "Indietro"])
v.menu.show("main"); v.menu.open_page("general")
glabels = [x.label() for x in v.menu.stack[-1][1]]
probe("Opzioni generali: Tastiera and Gamepad straight to their pages, Gamepad yes/no, "
      "the cache and the defaults",
      v.menu.stack[-1][1][glabels.index("Tastiera")].page == "keyboard"
      and any(getattr(x, "page", None) == "gamepad" for x in v.menu.stack[-1][1])
      and "Pulisci la cache" in glabels and "Ripristina i predefiniti" in glabels)
defaults = keybinds.defaults()
probe("default keys by position on the active layout: E Q T M, levels on VK_OEM_4 / VK_OEM_6",
      v.bindings.key("camera_up") == k.E and v.bindings.key("camera_down") == k.Q
      and v.bindings.key("textures") == k.T and v.bindings.key("blending") == k.M == v.bindings.key("menu_back")
      and v.bindings.key("level_prev") == keybinds.symbol_of_vk(0xDB)
      and v.bindings.key("level_next") == keybinds.symbol_of_vk(0xDD))
v.menu.show("main"); v.menu.open_page("help"); v.menu.open_page("keyboard")
v.on_draw()
probe("Keyboard page open, first row selected, nothing captured",
      v.menu.stack[-1][0] == "keyboard" and kbp.selection == 0 and kbp.capturing is None)
press(k.ENTER)
probe("Enter on 'Camera su': waiting for a key", kbp.capturing == "camera_up" and v.menu.capturing())
press(k.T)
probe("T refused: already used by Texture (same context), still waiting",
      v.bindings.key("camera_up") == k.E and kbp.capturing == "camera_up" and "Texture" in kbp.status[0])
press(k.W)
probe("W refused: locked", v.bindings.key("camera_up") == k.E and "bloccato" in kbp.status[0])
press(k.ESCAPE)
probe("Esc cancels the capture and leaves the menu open",
      kbp.capturing is None and v.menu.is_open and v.menu.stack[-1][0] == "keyboard")
press(k.ENTER); press(k.J)
probe("J assigned to Camera su and saved in the settings",
      v.bindings.key("camera_up") == k.J and v.user_settings["key_bindings"]["camera_up"] == k.J)
i_tex = keybinds.ACTION_IDS.index("textures")
kbp.selection = keybinds.ACTION_IDS.index("menu_back")
press(k.ENTER); press(k.T)
probe("T accepted for Menu indietro: menu and scene are different contexts",
      v.bindings.key("menu_back") == k.T and v.bindings.key("textures") == k.T)
v.on_draw()
row = next(r for r in kbp._row_rects if r[4] == i_tex)
v.on_mouse_press(row[0] + 5, row[1] + 5, pyglet.window.mouse.RIGHT, 0)
probe("right click on Texture: key removed, set incomplete, not saved",
      v.bindings.key("textures") is None and v.user_settings["key_bindings"]["textures"] == k.T)
press(k.BACKSPACE)
probe("leaving with an action without key: the last saved set comes back",
      v.menu.stack[-1][0] == "help" and v.bindings.key("textures") == k.T)
v.menu.open_page("keyboard")
kbp.selection = keybinds.ACTION_IDS.index("textures")
press(k.ENTER); press(k.K)
press(k.BACKSPACE)       # the Back key is T now, but only while the menu is open... here: Backspace
v.menu.hide()
before_tex = v.show_textures
press(k.K)
probe("with the menu closed K toggles the textures, T no longer does",
      v.show_textures == (not before_tex) and (press(k.T), v.show_textures == (not before_tex))[1])
probe("descriptions name the key bound now", "Tasto K." in texts.t("desc.texture"))
before = v._game_point(v.pos)
v.held_keys.add(k.J); v.update(0.1); v.held_keys.clear()
after = v._game_point(v.pos)
probe("J held moves the camera up (Y down in game units)", after[1] < before[1] and after[0] == before[0])
index_before = v.index
press(v.bindings.key("level_next"))
probe("the next-level key loads the next file", v.index == (index_before + 1) % len(v.level_files))
press(v.bindings.key("level_prev"))
v.menu.show("main"); v.menu.open_page("help"); v.menu.open_page("keyboard")
kbp.selection = [i for i, r in enumerate(kbp.rows()) if r[0] == "reset"][0]
press(k.ENTER)
probe("Ripristina tasti predefiniti: every key back, saved",
      v.bindings.current == defaults and v.user_settings["key_bindings"] == v.bindings.stored())
b2 = keybinds.Bindings({"textures": k.W, "sky": k.T, "camera_up": "x"})
probe("stored keys: locked, clashing or wrong ones give the defaults",
      b2.current == defaults)
b3 = keybinds.Bindings({"sky": k.J})
probe("a valid stored key is kept", b3.key("sky") == k.J and b3.key("textures") == k.T)

# the gamepad, with a pad made up here
class FakePad:
    connected, name = True, "Test pad"
    def __init__(self):
        from pyglet.math import Vec2
        self.left, self.right, self.held, self.dpad = Vec2(), Vec2(), set(), (0, 0)
        self.left_trigger = self.right_trigger = 0.0
    def release(self):
        pass
v.gamepad = FakePad()
v.menu.hide()
v._on_pad_button("start")
probe("pad Start opens the menu", v.menu.is_open)
v.menu.show("main")
v._on_pad_button("dpdown"); v._on_pad_button("dpdown")
probe("pad d-pad moves in the menu", v.menu.stack[-1][2] == 2)
v._on_pad_button("a")
probe("pad Cross confirms (Opzioni livello)", v.menu.stack[-1][0] == "level")
v._on_pad_button("b")
probe("pad Circle goes back", v.menu.stack[-1][0] == "main")
v._on_pad_button("start")
from pyglet.math import Vec2  # noqa: E402
v.gamepad.left = Vec2(0.0, 1.0)
v.yaw, v.pitch = 0.0, 0.0
before = v.pos
v.update(0.1)
probe("pad left stick forward moves the camera forward (yaw 0: +x)", v.pos.x > before.x)
v.focused = False
before = v.pos
v.update(0.1)
v._on_pad_button("start")
probe("out of focus the pad does nothing (it is the emulator's)", v.pos == before and not v.menu.is_open)
v.focused = True
v.gamepad.left = Vec2()
v._on_pad_button("back")
probe("pad Select covers the interface", v.ui_hidden)
v._on_pad_button("back")
v.gamepad = None

# the flags go back to how they start when another level is loaded, and stay
# put when the same level is rebuilt for a state chosen from the menu
v.show_hard_walls, v.show_death_zones = "unseen", True
v.show_area_visibility = v.show_camera_shadow = True
v.show_walls_outside = False
v.load_level(v.level_files[v.index], camera=False)
probe("rebuilding the same level leaves the flags where they are",
      v.show_hard_walls == "unseen" and v.show_death_zones and not v.show_walls_outside
      and v.show_area_visibility and v.show_camera_shadow)
other = next(f for f in v.level_files if f != v.level_files[v.index])
v.load_level(other)
probe("another level puts every flag back to how it starts",
      v.show_hard_walls == "off" and not v.show_death_zones
      and not v.show_area_visibility and not v.show_camera_shadow)
probe("and the ones that start ON come back on, not off", v.show_walls_outside)
# Moving characters: on at every start and at every level
probe("Moving characters on after another level", v.show_movers)
v.show_movers = False
v.load_level(v.level_files[0])
probe("Moving characters back on at the next level", v.show_movers)
probe("Cloned templates \"in the level\" by default (settings.py)", settings_mod.DEFAULTS["clones_shown"] == 1)

# the wheel scrolls the list and nothing else: Level options of L03A is
# longer than the window (a row per gate group)
v.menu.show("main"); v.menu.open_page("level")
v.on_draw()
scroll_items = v.menu.stack[-1][1]
scroll_labels = [x.label() for x in scroll_items]
v.menu.stack[-1][2] = scroll_labels.index("Cielo")
sky_was, start_was = v.show_sky, v.menu._start_lines[id(scroll_items)]
v.on_mouse_scroll(10, 300, 0, -1)
probe("wheel down: the list scrolls 3 rows and Cielo does not change",
      v.menu._start_lines[id(scroll_items)] == start_was + 3 and v.show_sky == sky_was)
v.on_draw()
v.on_mouse_scroll(10, 300, 0, -1)
probe("the cursor stays inside the visible part, on a selectable row",
      v.menu._start_lines[id(scroll_items)] <= v.menu.stack[-1][2]
      and scroll_items[v.menu.stack[-1][2]].selectable)
for _ in range(50):
    v.on_mouse_scroll(10, 300, 0, -1)
end_start = v.menu._start_lines[id(scroll_items)]
v.on_draw()
probe("wheel down to the end: the last row is visible and the list is not scrolled past it",
      0 < end_start < len(scroll_items) and any(a[2] == len(scroll_items) - 1 for a in v.menu._areas))
for _ in range(50):
    v.on_mouse_scroll(10, 300, 0, 1)
probe("wheel up: back to the top", v.menu._start_lines[id(scroll_items)] == 0)
v.menu.hide()
speed_was = v.speed
v.on_mouse_scroll(10, 300, 0, 1); v.on_mouse_scroll(10, 300, 0, -1)
probe("with the menu closed the wheel leaves the camera speed alone", v.speed == speed_was)
# Camera speed is an entry of Camera and points
v.menu.show("main"); v.menu.open_page("level"); v.menu.open_page("camera")
cam_labels = [x.label() for x in v.menu.stack[-1][1]]
probe("Camera e punti: Velocità camera after Mostra l'ombra",
      cam_labels.index("Velocità camera") == cam_labels.index("Mostra l'ombra") + 1)
v.menu.stack[-1][2] = cam_labels.index("Velocità camera")
v.speed = 26.0
press(k.RIGHT)
probe("right: the next stop, 30 m/s", v.speed == 30)
press(k.LEFT); press(k.LEFT)
probe("left twice: 20 then 15 m/s", v.speed == 15)
press(k.RIGHT, k.MOD_SHIFT)
probe("Shift + right: ten stops up, 500 m/s", v.speed == 500)
v.speed = speed_was
v.menu.hide()

# Video options: distant textures, like the PC (no mipmaps) or smooth
v.menu.show("main"); v.menu.open_page("video")
video_items = v.menu.stack[-1][1]
# Backface culling (finding 307): off by default, no key, saved with the settings
cull_item = video_items[[x.label() for x in video_items].index("Backface culling")]
probe("Video options: Backface culling off by default", not v.backface_culling and not settings_mod.DEFAULTS["backface_culling"])
cull_item.change(1, v.menu)
probe("Backface culling on: the two-sided faces of L03A are in groups of their own",
      v.backface_culling and any(g.two_sided for g in v.current_level.face_groups.values())
      and any(not g.two_sided for g in v.current_level.face_groups.values()))
v.on_draw()
cull_item.change(1, v.menu)
probe("Backface culling off again", not v.backface_culling)
far_item = video_items[[x.label() for x in video_items].index("Texture lontane")]
probe("distant textures: like the PC at startup, so no mipmaps", v.mipmaps is False)
far_item.change(1, v.menu)
probe("the other value is the smooth ones", v.mipmaps is True)
far_item.change(1, v.menu)
probe("and it goes back round", v.mipmaps is False)

# Video options: the three texture coordinate rules (findings 328, 341). The
# first, the default, is the PC's: byte / 255 clamped to [0.01, 0.99], repeated
v.menu.show("main"); v.menu.open_page("video")
video_items = v.menu.stack[-1][1]
uv_item = video_items[[x.label() for x in video_items].index("Coordinate texture")]
probe("texture coordinates: the PC's rule at startup", v.uv_rule == "pc")
wrap_pc = v.uv_wrap()
uv_item.change(1, v.menu)
probe("the second value is the AMD card", v.uv_rule == "pc_amd")
probe("which repeats the texture too, like every OpenGL profile", v.uv_wrap() == wrap_pc)
uv_item.change(1, v.menu)
probe("the third is the PlayStation", v.uv_rule == "psx")
probe("which alone clamps at the edge", v.uv_wrap() != wrap_pc)
uv_item.change(1, v.menu)
probe("and it goes back round to the PC's", v.uv_rule == "pc")
probe("a flag's name is never touched by the rule",
      geo.uv_transform(geo.UV_RAW, None) == geo.uv_transform("psx", None)
      and geo.uv_transform(geo.UV_RAW, None)[0][0] < -1.0)

# Video options: the field of view has a 51 degree stop, the game's own (finding 327)
v.menu.show("main"); v.menu.open_page("video")
video_items = v.menu.stack[-1][1]
fov_item = video_items[[x.label() for x in video_items].index("Campo visivo")]
fov_was = v.fov
v.fov = 50
fov_item.change(1, v.menu)
probe("field of view: 51 comes after 50", v.fov == 51)
probe("51 is named after the PC", "come il PC" in fov_item.value_text())
fov_item.change(1, v.menu)
probe("after 51 the round values come back", v.fov == 55)
fov_item.change(-1, v.menu); fov_item.change(-1, v.menu)
probe("going back passes through 51 again", v.fov == 50)
v.fov = 100
fov_item.change(1, v.menu)
probe("the field of view stops at 100", v.fov == 100)
v.fov = 40
fov_item.change(-1, v.menu)
probe("the field of view stops at 40", v.fov == 40)
v.fov = fov_was

# drawing: every page is laid out without errors
v._bookmark_i = 0
# Gates in a submenu: one row on Level options whatever the number of
# switches, and on its page the general choice plus one per switch
dock = next(p for p in v.level_files if os.path.basename(p).upper() == "L03A.BZE")
v.load_level(dock)
v.menu.show("main"); v.menu.open_page("level")
level_labels = [x.label() for x in v.menu.stack[-1][1]]
probe("Level options: a single Gates row, no row per switch",
      level_labels.count("Cancelli") == 1 and not any(str(x).startswith("Cancelli di #") for x in level_labels))
v.menu.stack[-1][2] = level_labels.index("Cancelli")
press(k.ENTER)
gate_items = v.menu.stack[-1][1]
gate_labels = [x.label() for x in gate_items]
switches = sorted(v.current_level.gate_groups)
probe("Gates page: All gates, By switch, then one row per switch of the level",
      v.menu.stack[-1][0] == "gates" and gate_labels[0] == "Tutti i cancelli"
      and "Per interruttore" in gate_labels
      and [x for x in gate_labels if x.startswith("Cancelli di #")] == [f"Cancelli di #{n}" for n in switches]
      and len(switches) > 0)
row = gate_labels.index(f"Cancelli di #{switches[0]}")
v.menu.stack[-1][2] = row
press(k.RIGHT)
probe("a per-switch choice still holds for the session", v.session_gate_choices.get(switches[0]) == "shut")
v.session_gate_choices = {}
v.load_level(dock, camera=False)
v.menu.hide()

# Level options -> Animations, step 2 (read only): the catalogue of the
# level as horizontal selectors, a count beside each, the selected row framed
from game import catalog as catalogmod  # noqa: E402
nowhere = os.path.join(paths.DATA_BZE, "Merlin.bze")
v.load_level(nowhere)
v.menu.show("main"); v.menu.open_page("level"); v.menu.open_page("animations")
anim_items = v.menu.stack[-1][1]
anim_labels = [x.label() for x in anim_items]
cat_row = anim_items[anim_labels.index("Categoria")]
cat = v._anim_catalogue()
fam_row = anim_items[anim_labels.index("Famiglia")]
probe("Animations: the grey number is the selector's positions (7 categories, the families of Characters)",
      cat_row.note() == "7"
      and fam_row.note() == str(len(catalogmod.menu_families(cat, "characters")))
      and anim_items[anim_labels.index("Esemplare")].note is None)
probe("the Category row's description says who is in it and how many",
      cat_row.desc().startswith("Entità: chi ha una testa")
      and f"{sum(len(f['exemplars']) for f in cat.families['characters'])} esemplari" in cat_row.desc())
merlin = next(i for i, f in enumerate(catalogmod.menu_families(cat, "characters")) if f[2]["model"] == 229)
v.anim_sel = {"category": "characters", "family": merlin, "which": 1}
v.menu.rebuild()
probe("the page's title is the family's name, the model and the parts under it",
      v._anim_title() == "Merlino" and v._anim_subtitle() == "Animazioni · Modello 229 · 31 parti")
v.anim_sel["which"] = 2
second = v._anim_title()
v.anim_sel["which"] = 10
tenth = v._anim_title()
v.anim_sel["which"] = 1
probe("an exemplar's own name: Merlin at his table (object 40), the others Merlin-Trial(1)...(9)",
      catalogmod.exemplar_id(v._anim_exemplar()) == ("placed", 40)
      and second == "Merlino-Prova(1)" and tenth == "Merlino-Prova(9)")
machine = next(i for i, f in enumerate(catalogmod.menu_families(cat, "characters")) if f[2]["model"] == 83)
v.anim_sel = {"category": "characters", "family": machine, "which": 1}
probe("object 122 of Nowhere (model 83) is the time machine", v._anim_title() == "Macchina del tempo"
      and catalogmod.exemplar_id(v._anim_exemplar()) == ("placed", 122))
v.anim_sel = {"category": "characters", "family": merlin, "which": 1}
# a click on the value's left arrow goes back, on the right one goes on
v.menu.stack[-1][2] = anim_labels.index("Famiglia")
v.on_draw()
row = anim_labels.index("Famiglia")
y0, y1, _i = next(a for a in v.menu._areas if a[2] == row)
left, middle = v.menu._value_middles[row]
v.menu.click(left + 2, (y0 + y1) / 2, pyglet.window.mouse.LEFT)
went_back = v.anim_sel["family"] == (merlin - 1) % len(catalogmod.menu_families(cat, "characters"))
v.on_draw()
y0, y1, _i = next(a for a in v.menu._areas if a[2] == row)
left, middle = v.menu._value_middles[row]
v.menu.click(middle + 4, (y0 + y1) / 2, pyglet.window.mouse.LEFT)
probe("a click on ‹ goes back, a click on › goes on", went_back and v.anim_sel["family"] == merlin)
v.menu.stack[-1][2] = anim_labels.index("Categoria")
while v.anim_sel["category"] != "collectables":
    press(k.RIGHT)
probe("changing category starts its families from the first, exemplar 1",
      v.anim_sel["family"] == 0 and v.anim_sel["which"] == 1
      and v.menu.stack[-1][1][anim_labels.index("Categoria")].note() == "7")
v.anim_sel = {"category": "rest", "family": 0, "which": 1}
v.menu.rebuild()
anim_items = v.menu.stack[-1][1]
anim_labels = [x.label() for x in anim_items]
probe("The rest has the two families Scenery and Invisible logic",
      [f[0] for f in catalogmod.menu_families(cat, "rest")] == [("rest", "scenery"), ("rest", "logic")])
v.menu.stack[-1][2] = anim_labels.index("Esemplare")
press(k.RIGHT, k.MOD_SHIFT)
probe("Shift + arrow on Which one jumps ten", v.anim_sel["which"] == 11)
helpers = next(i for i, f in enumerate(catalogmod.menu_families(cat, "characters")) if f[2]["model"] == 272)
v.anim_sel = {"category": "characters", "family": helpers, "which": 1}
v.menu.rebuild()
v.anim_follow = True
v.anim_follow_tick()
e = v._anim_exemplar()
target = Vec3(*geo._transform((0, 0, 0), pos=catalogmod.place_of(cat, e))) + Vec3(0.0, 1.0, 0.0)
probe("the selected thing is framed: the camera 6 m from the first helper's place, 1 m up",
      abs((v.pos - target).length() - 6.0) < 0.01)
probe("a helper is not there at the start, and the why goes back to Merlin's sign (#58, zone 3: N75)",
      not e["at_start"] and "#58" in v._anim_why(e) and "zona 3" in v._anim_why(e))
# step 3: where the game keeps one alive at a time (N75, trigger 101's
# helpers) choosing an exemplar shows it and hides the other two
sets = catalogmod.one_at_a_time(cat)
probe("Nowhere: one 'one at a time' set, trigger 101's three helpers (N75)",
      len(sets) == 1 and {r[0][0][1] for r in sets[0]} == {101} and len(sets[0]) == 3)
second = next(i for i, x in enumerate(catalogmod.menu_families(cat, "characters")[helpers][1])
              if x["route"] == ((("placed", 101), 6),)) + 1
v._anim_set(which=second)
shown, hidden = v.anim_exceptions["shown"], v.anim_exceptions["hidden"]
probe("choosing the second helper shows it and hides the other two",
      shown == {((("placed", 101), 6),)} and hidden == set(sets[0]) - shown
      and any(g.category == "chosen" for g in v.current_level.face_groups.values()))
e = v._anim_exemplar()
roles = v._anim_object_roles(e)
v._anim_set_role(e, roles[2])
e = v._anim_exemplar()
frames = v._anim_frames(e)
probe("Animation: the helper plays its third role, with its frames", v._anim_current_role(e) == roles[2] and frames > 1)
v._anim_set_frame(e, 10)
probe("Frame 10: the helper is held on frame index 9", v.anim_holds.get(v._anim_key(e)) == 9)
v._anim_set_flow(e, "loop")
probe("How it runs -> loop: the hold goes", v._anim_key(e) not in v.anim_holds)
v.anim_sel = {"category": "characters", "family": helpers, "which": 1}
v.menu.rebuild()
pos_before = Vec3(*v.pos)
v.anim_follow = False
v.anim_sel["which"] = 2
v.anim_follow_tick()
probe("with Follow off the camera stays", v.pos == pos_before)
v.anim_follow = True
drawn = True
for c in catalogmod.CATEGORIES:
    v.anim_sel = {"category": c, "family": 0, "which": 1}
    v.menu.rebuild()
    try:
        v.on_draw()
    except Exception as error:  # noqa: BLE001
        print(error)
        drawn = False
probe("the page draws on every category of Nowhere", drawn)
mine = os.path.join(paths.DATA_BZE, "L03C1.bze")
v.load_level(mine)
probe("another level: the selection back to the top", v.anim_sel["category"] == "characters")
v.anim_sel = {"category": "carried", "family": 0, "which": 1}
v.menu.rebuild()
try:
    v.on_draw()
    drawn = True
except Exception as error:  # noqa: BLE001
    print(error)
    drawn = False
probe("an empty category (Carried and pushed in Mine or mine? 2) says none and draws",
      drawn and any(isinstance(x, menumod.Info) and x.value_text() == "nessuna" for x in v.menu.stack[-1][1]))
v.menu.hide()
v.load_level(dock)

# the selector: Alt+click again on the same pixel steps down the stack and,
# after the last, passes through "nothing selected"; a right click clears
v.picked, v.picked_i, v._pick_at = [{"group": "a"}, {"group": "b"}], 0, (10, 10)
steps = []
for _ in range(4):
    v.pick_at(10, 10)
    steps.append(v.picked_i if v.picked_entry() is not None else None)
probe("Alt+click round: second, nothing, first, second", steps == [1, None, 0, 1])
v.picked_i = 2
probe("on the nothing step there is no card", v.picked_card() == [] and v.picked_entry() is None)
v.picked_i = 0
v.looking, v._looked = True, False
v.on_mouse_release(10, 10, pyglet.window.mouse.RIGHT, 0)
probe("a right click clears the selection", not v.picked and v.picked_entry() is None)
v.picked, v.picked_i = [{"group": "a"}], 0
v.looking, v._looked = True, False
shot, v.screenshot = v.screenshot, None
v.on_mouse_motion(10, 10, 5, 0)
v.screenshot = shot
v.on_mouse_release(10, 10, pyglet.window.mouse.RIGHT, 0)
probe("the right button held to turn the camera keeps the selection", v.picked_entry() is not None)
v.yaw -= 5 * 0.15
v.clear_pick()

for page in ("main", "load", "level", "gates", "video", "general", "help", "eras", "extra", "cutscenes", "flags",
               "era:era.pirates", "era:era.medieval", "era:era.dimx", "camera", "bookmark",
               "help", "keyboard", "gamepad", "about"):
    v.menu.show("main")
    if page != "main":
        v.menu.open_page(page)
    try:
        v.on_draw()
        ok = True
    except Exception as e:  # noqa: BLE001
        print(e)
        ok = False
    probe(f"page {page} draws", ok)
for language in ("en", "it"):
    texts.set_language(language)
    v.menu.show("main"); v.menu.open_page("help")
    v.on_draw()
v.menu.show("main"); v.menu.open_page("help"); v.menu.open_page("about")
probe("About shows the version of support/version.py",
      any(i.value_text() == VERSION for i in v.menu.stack[-1][1] if hasattr(i, "value_text")))
probe("settings off in photo mode", not v.user_settings.enabled)
v.close()

# startup with no level requested: no level, main menu over space
w = viewer.Viewer(None, "extracted", screenshot="nessuna.png")
w.signature_drawn = False
w.on_draw()
probe("startup without a level: nothing loaded, main menu and signature",
      w.current_level is None and w.level_files and w.menu.is_open
      and w.menu.stack[-1][0] == "main" and w.signature_drawn)
menu_items = w.menu.stack[-1][1]
probe("without a level Resume is greyed out and the cursor starts on Load level",
      menu_items[0].disabled and w.menu.stack[-1][2] == 1)
w.close()
w = viewer.Viewer(None, "extracted", screenshot="nessuna.png", level="L03A2")
probe("startup with a requested level: that one", w.current_level is not None and w.current_level.name.upper() == "L03A2")
w.close()
# Camera and points: a bookmark's name written from the keyboard, and a point
# pasted from the clipboard
w = viewer.Viewer([os.path.join(paths.DATA_BZE, "L03A.bze")], "extracted", 0, screenshot="nessuna.png")
w.screenshot = None   # the keyboard works again; the settings stay off
texts.set_language("it")
w.user_settings["bookmarks"] = {}
w._add_bookmark()
w._bookmark_i = 0
w.menu.show("main"); w.menu.open_page("level"); w.menu.open_page("camera"); w.menu.open_page("bookmark")
blabels = [x.label() for x in w.menu.stack[-1][1]]
w.menu.stack[-1][2] = blabels.index("Nome")
w.on_key_press(k.ENTER, 0)
w.on_text("Porto")
w.on_key_press(k.BACKSPACE, 0)
w.on_text("i")
w.on_key_press(k.ENTER, 0)
named = w._mark_name(w._bookmarks()[0])
w.menu.stack[-1][2] = blabels.index("Nome")
w.on_key_press(k.ENTER, 0)
w.on_text("xyz")
w.on_key_press(k.ESCAPE, 0)
probe("a bookmark's name: typed, Backspace, Enter saves; Esc leaves it as it was, the menu still open",
      named == "Porti" and w._mark_name(w._bookmarks()[0]) == "Porti" and w.menu.is_open
      and w.menu.editing is None)
w.set_clipboard_text("{ X = 20000, Y = -1500, Z = 16000 }, -- BBLIT L03A, test")
w._go_to_clipboard_point()
at = (round(w.pos.x * 128), round(-(w.pos.y - 1.6) * 128), round(-w.pos.z * 128))
w.set_clipboard_text("BBLIT L01A x=1 y=2 z=3")
before_other = (w.pos.x, w.pos.y, w.pos.z)
w._go_to_clipboard_point()
probe("Go to the point in the clipboard: 1.6 m above it; a point of another level is said, not used",
      at == (20000, -1500, 16000) and (w.pos.x, w.pos.y, w.pos.z) == before_other
      and w._paste_result[0] == "camera.paste.other")
w.close()
# a value too long for its row gives way, not the label: shortened with its
# arrows kept
long_value = menumod.fit_value("‹ " + "NVIDIA/Intel " * 8 + "›", 120, 16)
probe("a value too long is shortened with its arrows kept, to the room it has",
      long_value.startswith("‹ ") and long_value.endswith("… ›")
      and menumod.text_width(long_value, 16) <= 120
      and menumod.fit_value("‹ PC ›", 120, 16) == "‹ PC ›")
from window import app as appmod  # noqa: E402
probe("the saved window size is taken back; a broken or too small one gives 1280 x 760",
      appmod._window_size([1500, 900]) == (1500, 900) and appmod._window_size([300, 200]) == (1280, 760)
      and appmod._window_size("x") == (1280, 760) and appmod._window_size(None) == (1280, 760)
      and settings_mod.DEFAULTS["window_size"] == [1280, 760]
      and appmod._window_size([2500, 1400], (1366, 768)) == (1326, 668))
failed =[n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
