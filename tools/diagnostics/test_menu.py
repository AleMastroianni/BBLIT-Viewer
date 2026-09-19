"""Test of the menu logic, without touching the user's settings.

    .venv/Scripts/python tools/diagnostics/test_menu.py

Opens the viewer in photo mode (settings off), re-enables the keyboard and
drives the menu from code: navigation, yes/no, per-session group states,
animations, ticks, language, Esc reopening where it was left, Load level by
era, Extra and Era selector, drawing of every page. Does not call app.run.
"""
import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
os.chdir(os.path.dirname(TOOLS))
import pyglet
import paths
import viewer

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


probe("title with the build", v.caption.endswith("Debug"))
probe("flags off at startup: no overlay family built",
      not v.current_level.families
      and not any(g.category in viewer.OVERLAYS for g in v.current_level.face_groups.values()))
probe("English by default", viewer.texts.language() == "en")
viewer.texts.set_language("it")   # the test uses the Italian labels
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
probe("Flags: the five overlays, all off by default",
      v.menu.stack[-1][0] == "flags"
      and flag[:5] == ["Muri invisibili", "Senza collisione", "Box di collisione",
                       "Zone di morte", "Pavimento della morte"]
      and not (v.show_invisible_walls or v.show_no_collision or v.show_collision_boxes
               or v.show_death_zones or v.show_death_floor))
flag_attrs = ["show_invisible_walls", "show_no_collision", "show_collision_boxes", "show_death_zones", "show_death_floor"]
turned_on = []
for i_f, attr in enumerate(flag_attrs):
    v.menu.stack[-1][2] = i_f
    press(k.ENTER)
    turned_on.append(getattr(v, attr))
    press(k.ENTER)
probe("Enter turns each flag on and off again", all(turned_on)
      and not any(getattr(v, a) for a in flag_attrs))
probe("turning a flag on builds its family; off only hides it",
      v.current_level.families == set(viewer.FAMILIES)
      and {g.category for g in v.current_level.face_groups.values()} >= {
          "invisible_walls", "no_collision", "collision_boxes", "death_floor"})   # L03A: sea only
press(k.BACKSPACE)
probe("Backspace from Flags returns to Level options", v.menu.stack[-1][0] == "level")
v.menu.hide()
for sym in (k.I, k.C, k.B, k.Z, k.K):
    press(sym)
probe("the flags have no keys", not any(getattr(v, a) for a in flag_attrs))
v.menu.reopen()

i_bridges = labels.index("Ponti levatoi")
v.menu.stack[-1][2] = i_bridges
probe("bridges lowered by default (121)", v.current_level.pref["pose"][217] == 121)
press(k.RIGHT)   # 121 is the last one: wraps to the first, 118 raised
probe("bridges raised for the session (118)", v.current_level.pref["pose"][217] == 118
      and v.session_poses["L03A"][217] == 118)
probe("preferences.py not touched", viewer.preferences.for_level("L03A")["pose"][217] == 121)
probe("menu still on Level options after the rebuild", v.menu.stack[-1][0] == "level")

i_anim = labels.index("Animazioni")
v.menu.stack[-1][2] = i_anim
press(k.RIGHT)
probe("Animazioni -> Ferme (frozen)", v.paused and v.fixed_tick is None)
press(k.RIGHT)
probe("Animazioni -> Posa iniziale (initial pose)", v.fixed_tick == 0 and not v.paused)
press(k.RIGHT)
probe("Animazioni -> In movimento (moving)", v.fixed_tick is None and not v.paused)

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
probe("English language", viewer.texts.language() == "en" and v.menu.stack[-1][1][0].label().startswith("Language"))
probe("title translated, with build", v.caption == "BBLIT Viewer — Debug")
press(k.LEFT)
probe("Italian language", viewer.texts.language() == "it")
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
probe("Load level: the five eras, Nowhere below Dimensione X, then Extra",
      era_labels[:6] == ["Età della pietra", "Medioevo", "Pirati", "Anni '30", "Dimensione X", "Nowhere"]
      and "Extra" in era_labels)
v.menu.stack[-1][2] = era_labels.index("Pirati")
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
i = next(i for i, x in enumerate(menu_items) if x.selectable and x.value_text().startswith("L03A2"))
v.menu.stack[-1][2] = i
probe("description with LevID 23", "LevID 23" in menu_items[i].desc())
press(k.ENTER)
probe("Pirati -> Parte 2: L03A2 loaded and menu closed", v.current_level.name.upper() == "L03A2" and not v.menu.is_open)
press(k.ESCAPE)
item = v.menu.stack[-1][1][v.menu.stack[-1][2]]
probe("Esc reopens where it was left (Pirati, on L03A2)", v.menu.stack[-1][0] == "era:era.pirates"
      and item.value_text().startswith("L03A2") and [x[0] for x in v.menu.stack] == ["main", "load", "era:era.pirates"])
press(k.BACKSPACE)
v.menu.stack[-1][2] = [x.label() for x in v.menu.stack[-1][1]].index("Extra")
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
page_labels = [x.label() for x in menu_items]
probe("Extra: Era selector, _8 variants and Cutscenes, no Nowhere (Debug build)",
      "Nowhere" not in page_labels and
      "Cutscenes" in page_labels and any((x.value_text() or "").startswith("L03A_8") for x in menu_items)
      and not any(x.selectable and (x.value_text() or "")[:2] in ("CC", "TI", "CR") for x in menu_items))
v.menu.stack[-1][2] = page_labels.index("Cutscenes")
press(k.ENTER)
menu_items = v.menu.stack[-1][1]
v.menu.stack[-1][2] = next(i for i, x in enumerate(menu_items) if x.selectable and x.value_text().startswith("CC3A"))
press(k.ENTER)
probe("Extra -> Cutscenes -> CC3A cutscene loaded", v.current_level.name.upper() == "CC3A")
press(k.ESCAPE)
probe("Esc reopens Cutscenes", v.menu.stack[-1][0] == "cutscenes")
press(k.BACKSPACE)
menu_items = v.menu.stack[-1][1]
page_labels = [x.label() for x in menu_items]
probe("Extra contains the Era selector, with the title only once",
      "Vista d'insieme" in page_labels and page_labels.count("Era selector") == 1)
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Pirati"][0]
press(k.ENTER)
probe("Era selector -> Pirati: LS01 with the camera on the pirate island",
      v.current_level.name.upper() == "LS01" and (round(v.pos.x, 1), round(v.pos.y, 1), round(v.pos.z, 1)) == (20.0, 23.8, 17.5))
before = v.current_level
press(k.ESCAPE)
menu_items = v.menu.stack[-1][1]
v.menu.stack[-1][2] = [i for i, x in enumerate(menu_items) if x.selectable and x.label() == "Medioevo"][0]
press(k.ENTER)
probe("Era selector -> Medioevo with LS01 already open: only moves the camera",
      v.current_level is before and round(v.pos.z, 1) == -4.7 and not v.menu.is_open)
build = v.build
v.build = "Portable"
v.menu.show("main"); v.menu.open_page("extra")
probe("in another build Extra does not show Cutscenes but keeps the _8 variants",
      "Cutscenes" not in [x.label() for x in v.menu.stack[-1][1]]
      and any((x.value_text() or "").startswith("L03A_8") for x in v.menu.stack[-1][1]))
v.build = build

# drawing: every page is laid out without errors
for page in ("main", "load", "level", "video", "general", "help", "extra", "cutscenes", "flags",
               "era:era.pirates", "era:era.medieval", "era:era.dimx"):
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
    viewer.texts.set_language(language)
    v.menu.show("main"); v.menu.open_page("help")
    v.on_draw()
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
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
