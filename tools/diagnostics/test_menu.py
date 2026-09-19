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
probe("Flags: the first five overlays, all off by default",
      v.menu.stack[-1][0] == "flags"
      and flag[:5] == ["Muri invisibili", "Senza collisione", "Box di collisione",
                       "Zone di morte e danno", "Zone di teletrasporto"]
      and not (v.show_invisible_walls or v.show_no_collision or v.show_collision_boxes
               or v.show_death_zones or v.show_teleport_zones))
i_outside = flag.index("Box delle aree: lato di fuori") if "Box delle aree: lato di fuori" in flag else None
probe("Flags: the area boxes' outside side, on by default", i_outside is not None and v.show_area_outside)
if i_outside is not None:
    v.menu.stack[-1][2] = i_outside
    press(k.ENTER)
    probe("Enter hides the outside side", not v.show_area_outside)
    press(k.ENTER)
flag_attrs = ["show_invisible_walls", "show_no_collision", "show_collision_boxes", "show_death_zones",
              "show_teleport_zones"]
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
          "invisible_walls", "no_collision", "collision_boxes", "death_zones", "death_zones_label"})   # L03A: sea only
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

# Camera and points (glitch hunting, stage 3): bookmarks, shadow point, export
import re  # noqa: E402
import collision  # noqa: E402
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
u = viewer.geo.UNITS_PER_METER
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
if viewer.private_export is not None:      # the private copies only
    v.menu.stack[-1][2] = labels.index(viewer.texts.t("camera.copy_ce"))
    press(k.ENTER)
    m = re.match(r"BBLIT L03A x=(-?\d+) y=(-?\d+) z=(-?\d+)", clipboard[-1] if clipboard else "")
    probe("private copy: the line of private_export, with the shadow point",
          m is not None and tuple(int(w) for w in m.groups()) == (gx, g, gz))
else:
    probe("public copy: no private entry", viewer.texts.t("camera.copy_ce") == "camera.copy_ce")
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
      and viewer.settings_mod.DEFAULTS["bookmarks"] == {})
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
import keybinds  # noqa: E402
kbp = v.keyboard_page
v.menu.show("main")
v.menu.stack[-1][2] = [x.label() for x in v.menu.stack[-1][1]].index("Aiuto")
press(k.ENTER)
probe("Aiuto: Tastiera, Gamepad, Indietro",
      [x.label() for x in v.menu.stack[-1][1]] == ["Tastiera", "Gamepad", "Indietro"])
v.menu.show("main"); v.menu.open_page("general")
glabels = [x.label() for x in v.menu.stack[-1][1]]
probe("Opzioni generali: Tasti e gamepad (to the same page) and Gamepad yes/no",
      "Tasti e gamepad" in glabels and "Gamepad" in glabels
      and v.menu.stack[-1][1][glabels.index("Tasti e gamepad")].page == "help")
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
probe("descriptions name the key bound now", "Tasto K." in viewer.texts.t("desc.texture"))
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

# drawing: every page is laid out without errors
v._bookmark_i = 0
for page in ("main", "load", "level", "video", "general", "help", "extra", "cutscenes", "flags",
               "era:era.pirates", "era:era.medieval", "era:era.dimx", "camera", "bookmark",
               "help", "keyboard", "gamepad"):
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
sys.exit(1 if failed else 0)
