"""Changing level must leave nothing of the level before behind.

    .venv/Scripts/python checks/test_level_change.py

Two things are checked, both of which used to fail:

1. **the drawing.** A level reached from another one must come out pixel for
   pixel like the same level opened from cold. It did not: the animation
   clock (`anim_time`) carried on across the change, so poses, bones and the
   movers' simulation started at the tick of the level before.
2. **the menu.** A page rebuilt shorter (the level page has one line per group
   of entities, and another level has fewer) left the cursor past the end of
   the list, and the mouse could still put it there through the clickable
   areas of the page before. `ui/menu.py` then failed with an IndexError
   while drawing, which took the whole viewer with it: the level change was
   interrupted halfway and what stayed on screen was the level before, in
   pieces.

`Hey... What's up, Dock? 1` (L03A, 24 lines on the level page) and
`Nowhere` (MERLIN, 33): the change is tried in both directions, because only
one of them shortens the page.
"""
import hashlib
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)
import pyglet
from support import paths
import viewer

k = pyglet.window.key
FIRST, SECOND = "L03A.bze", "Merlin.bze"
file_paths = [os.path.join(paths.DATA_BZE, f) for f in (FIRST, SECOND)]
v = viewer.Viewer(file_paths, "extracted", 0, screenshot="nessuna.png")
v.screenshot = None   # the keyboard becomes active again; settings stay off
results = []


def probe(entry_name, cond):
    results.append((entry_name, bool(cond)))
    print(("OK   " if cond else "FAIL ") + entry_name)


def press(symbol, modifiers=0):
    return v.on_key_press(symbol, modifiers)


def frame():
    """The drawn frame, as a fingerprint of its pixels."""
    v.on_draw()
    colours = pyglet.image.get_buffer_manager().get_color_buffer().get_image_data()
    return hashlib.sha1(colours.get_data("RGB", 3 * v.width)).hexdigest()


def run_animations(seconds=0.5):
    """The animations run, as they do with the viewer open."""
    for _ in range(int(seconds * 60)):
        v.update(1 / 60.0)


def open_level(i):
    v.index = i
    v.load_level(file_paths[i])


# ---- 1. the drawing: coming back to a level is opening it from cold

cold_first = frame()
run_animations()
open_level(1)
cold_second = frame()
run_animations()
open_level(0)
probe("the animation clock goes back to zero when the level changes", v.anim_time == 0.0)
probe("there and back: the first level is the one opened from cold", frame() == cold_first)
run_animations()
open_level(1)
probe("the other way round too: the second level is the one opened from cold", frame() == cold_second)

# ---- 2. the menu: the cursor never leaves the list

# on the longer of the two (Nowhere), down to the last line of the level page
press(k.ESCAPE)
press(k.DOWN); press(k.DOWN); press(k.ENTER)          # main -> Level options
probe("the level page is open", v.menu.stack[-1][0] == "level")
for _ in range(8):
    press(k.PAGEDOWN)      # PageDown stops at the last line, Down would wrap round
frame()                                                # the clickable areas are laid out
long_page = len(v.menu.stack[-1][1])
deep_cursor = v.menu.stack[-1][2]
areas = list(v.menu._areas)
lowest_row = max(i for _y0, _y1, i in areas)
y_of_lowest = next((y0 + y1) / 2 for y0, y1, i in areas if i == lowest_row)
probe("the cursor is deep in the page", deep_cursor > 20)

press(k.ESCAPE)                                        # the menu closes
open_level(0)                                          # to the level with the shorter page
short_page = len(v.menu.stack[-1][1])
probe("the open page was rebuilt with the level", short_page < long_page)
probe("and the cursor came back inside it", v.menu.stack[-1][2] < short_page)
probe("on a line that can be selected", v.menu.stack[-1][1][v.menu.stack[-1][2]].selectable)

press(k.ESCAPE)                                        # reopened where it was left
# the mouse moves before the next frame: the clickable areas are still those
# of the page of the level before, and following them put the cursor out
v.on_mouse_motion(10, y_of_lowest, 0, 0)
probe("the mouse does not take the cursor out of the list", v.menu.stack[-1][2] < short_page)
try:
    frame()
    drawn = True
except Exception as error:  # noqa: BLE001
    print(error)
    drawn = False
probe("the menu draws after the change", drawn)

# a click on the same spot must not take it out either
v.on_mouse_press(10, y_of_lowest, pyglet.window.mouse.LEFT, 0)
probe("a click does not take it out either", v.menu.stack[-1][2] < len(v.menu.stack[-1][1]))

v.close()
failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
