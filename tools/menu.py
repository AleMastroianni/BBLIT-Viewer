"""CTR viewer-style menu, drawn over the scene with pyglet.

A page is a list of items; pages open on top of each other and Back
(Backspace, M or right button) returns to the previous one. Esc is handled by
the viewer: it opens and closes the menu.

Items: `YesNo`, `Choice` (cycling values, left and right arrows), `Number`,
`Action`, `Submenu`, `Back`; `Section` and `Info` are not selectable.
Labels are computed on every draw with `texts.t`, so changing language
rebuilds nothing.

Compared with the CTR viewer: fixed-width panel on the left, page title,
sections, label on the left and value on the right, description of the
selected item at the bottom of the panel.
"""

from __future__ import annotations

import pyglet
from pyglet.gl import (GL_BLEND, GL_DEPTH_TEST, GL_FUNC_ADD, GL_ONE_MINUS_SRC_ALPHA, GL_SRC_ALPHA,
                       glBlendEquation, glBlendFunc, glDisable, glEnable)

from texts import t

FONT = ["Segoe UI", "Arial"]

# colours (r, g, b, a)
BACKGROUND_COLOR = (20, 20, 20, 215)
HIGHLIGHT_COLOR = (168, 96, 26, 255)
TEXT_COLOR = (242, 214, 75, 255)
VALUE_COLOR = (255, 244, 176, 255)
SELECTED_TEXT_COLOR = (255, 255, 255, 255)
SECTION_COLOR = (138, 160, 184, 255)
DESCRIPTION_COLOR = (240, 162, 74, 255)
TITLE_COLOR = (232, 232, 232, 255)
LINE_COLOR = (80, 80, 80, 255)
INFO_LEFT_COLOR = (255, 244, 176, 255)
INFO_RIGHT_COLOR = (220, 220, 220, 255)
DISABLED_COLOR = (125, 125, 125, 255)


def wrap_lines(label_text, width_units, font_size):
    """Split the text into lines that fit in `width_units` pixels.

    We wrap by hand, measuring with single-line labels: pyglet 2.1's multiline
    layout widens the space before the last word ("Tasto T." became
    "Tasto   T."), at any width.
    """
    def text_width(row):
        return pyglet.text.Label(row, font_name=FONT, font_size=font_size).content_width

    lines, current = [], ""
    for word in label_text.split():
        probe = f"{current} {word}" if current else word
        if current and text_width(probe) > width_units:
            lines.append(current)
            current = word
        else:
            current = probe
    if current:
        lines.append(current)
    return lines


def ellipsize(label_text, width_units, font_size):
    """The text, shortened with "…" if it does not fit in `width_units` pixels."""
    def text_width(t):
        return pyglet.text.Label(t, font_name=FONT, font_size=font_size).content_width

    if text_width(label_text) <= width_units:
        return label_text
    low, high = 0, len(label_text)
    while low < high:
        middle = (low + high + 1) // 2
        if text_width(label_text[:middle].rstrip() + "…") <= width_units:
            low = middle
        else:
            high = middle - 1
    return label_text[:low].rstrip() + "…"


# ------------------------------------------------------------------ items

class Item:
    selectable = True

    def __init__(self, item_key, desc=None, label_text=None):
        self.item_key = item_key
        self.desc = desc
        self._text_fn = label_text          # computed text, instead of the key
        # greyed out: selectable (to read its description) but does nothing
        self.disabled = False

    def label(self) -> str:
        return self._text_fn() if self._text_fn else t(self.item_key)

    def value_text(self) -> str:
        return ""

    def change(self, increment: int, menu: "Menu") -> None:
        pass

    def confirm(self, menu: "Menu") -> None:
        self.change(1, menu)


class YesNo(Item):
    def __init__(self, item_key, fetch, store, desc=None):
        super().__init__(item_key, desc)
        self.fetch, self.store = fetch, store

    def value_text(self):
        return t("menu.yes") if self.fetch() else t("menu.no")

    def change(self, increment, menu):
        self.store(not self.fetch())


class Choice(Item):
    """`option_list`: pairs (value, text key) or (value, function that returns the text)."""

    def __init__(self, item_key, option_list, fetch, store, desc=None, label_text=None):
        super().__init__(item_key, desc, label_text)
        self.option_list, self.fetch, self.store = option_list, fetch, store

    def _idx(self):
        current = self.fetch()
        for i, (v, _e) in enumerate(self.option_list):
            if v == current:
                return i
        return 0

    def value_text(self):
        _v, e = self.option_list[self._idx()]
        return f"‹ {e() if callable(e) else t(e)} ›"

    def change(self, increment, menu):
        i = (self._idx() + (1 if increment > 0 else -1)) % len(self.option_list)
        self.store(self.option_list[i][0])


class Number(Item):
    def __init__(self, item_key, fetch, store, minimum, maximum, increment=1, number_format="{:.0f}", desc=None):
        super().__init__(item_key, desc)
        self.fetch, self.store = fetch, store
        self.minimum, self.maximum, self.increment, self.number_format = minimum, maximum, increment, number_format

    def value_text(self):
        return f"‹ {self.number_format.format(self.fetch())} ›"

    def change(self, increment, menu):
        new = self.fetch() + increment * self.increment
        self.store(max(self.minimum, min(self.maximum, new)))


class Action(Item):
    """`right_text`: optional text on the right (for example a level's file)."""

    def __init__(self, item_key, fn, desc=None, label_text=None, right_text=None):
        super().__init__(item_key, desc, label_text)
        self.fn = fn
        self.right_text = right_text

    def value_text(self):
        return self.right_text() if self.right_text else ""

    def change(self, increment, menu):
        pass

    def confirm(self, menu):
        if not self.disabled:
            self.fn()


class Submenu(Item):
    def __init__(self, item_key, page, desc=None, label_text=None):
        super().__init__(item_key, desc, label_text)
        self.page = page

    def value_text(self):
        return "›"

    def change(self, increment, menu):
        pass

    def confirm(self, menu):
        menu.open_page(self.page)


class Back(Item):
    def __init__(self):
        super().__init__("menu.back")

    def change(self, increment, menu):
        pass

    def confirm(self, menu):
        menu.go_back()


class Section(Item):
    selectable = False


class Info(Item):
    """An information line: text on the left and on the right (strings or functions)."""
    selectable = False

    def __init__(self, left_text, right_text=""):
        super().__init__(None)
        self.left_text, self.right_text = left_text, right_text

    def label(self):
        return self.left_text() if callable(self.left_text) else self.left_text

    def value_text(self):
        return self.right_text() if callable(self.right_text) else self.right_text


class Page:
    """`menu_items` is a function: the pages that depend on the level (level list,
    entity groups) are rebuilt every time they open."""

    def __init__(self, title_text, menu_items, width_units=440):
        self.title_text = title_text         # function that returns the title
        self.build_items = menu_items
        self.width_units = width_units


# ------------------------------------------------------------------ menu

class Menu:
    def __init__(self, pages: dict[str, Page]):
        self.pages = pages
        self.is_open = False
        self.stack: list[list] = []       # [entry_name, menu_items, cursor]
        self._batch = None
        self._drawables = []
        self._areas = []                  # (y0, y1, item index)
        self._right_edge = 0                 # right edge of the panel
        self._desc_max = {}              # lines of the page's longest description
        self._start_lines = {}                # first visible line, per page
        self._draw_key = None
        self.dirty = True

    # ---- navigation

    @property
    def page(self):
        return self.stack[-1] if self.stack else None

    def show(self, entry_name="main"):
        self.stack = []
        self.open_page(entry_name)
        self.is_open = True

    def reopen(self):
        """Reopen where it was left (open pages and selected item): closing it
        with Esc must not lose the place. The items are rebuilt,
        because the level may have changed in the meantime."""
        if not self.stack:
            self.show()
            return
        self.rebuild()
        self.is_open = True

    def hide(self):
        self.is_open = False

    def open_page(self, entry_name):
        menu_items = self.pages[entry_name].build_items()
        # the first enabled item: with no level, "Resume" is greyed out
        cursor = next((i for i, v in enumerate(menu_items) if v.selectable and not v.disabled),
                       next((i for i, v in enumerate(menu_items) if v.selectable), 0))
        self.stack.append([entry_name, menu_items, cursor])
        self.dirty = True

    def go_back(self):
        self.stack.pop()
        if not self.stack:
            self.is_open = False
        self.dirty = True

    def rebuild(self):
        """After a level or language change: rebuild the items of the open pages."""
        for item in self.stack:
            item[1] = self.pages[item[0]].build_items()
            item[2] = min(item[2], len(item[1]) - 1)
        self.dirty = True

    def _move(self, increment):
        entry_name, menu_items, cursor = self.stack[-1]
        selectable_idx = [i for i, v in enumerate(menu_items) if v.selectable]
        if not selectable_idx:
            return
        if cursor not in selectable_idx:
            cursor = selectable_idx[0]
        pos = selectable_idx.index(cursor)
        if abs(increment) == 1:
            pos = (pos + increment) % len(selectable_idx)
        else:
            pos = max(0, min(len(selectable_idx) - 1, pos + increment))
        self.stack[-1][2] = selectable_idx[pos]
        self.dirty = True

    def _current_item(self):
        entry_name, menu_items, cursor = self.stack[-1]
        item = menu_items[cursor] if menu_items else None
        return item if item is not None and item.selectable else None

    # ---- input: return True if the event belongs to the menu

    def press(self, symbol, modifiers) -> bool:
        if not self.is_open or not self.stack:
            return False
        k = pyglet.window.key
        repeat = 10 if modifiers & k.MOD_SHIFT else 1
        item = self._current_item()
        if symbol in (k.UP, k.W):
            self._move(-1)
        elif symbol in (k.DOWN, k.S):
            self._move(1)
        elif symbol == k.PAGEUP:
            self._move(-10)
        elif symbol == k.PAGEDOWN:
            self._move(10)
        elif symbol in (k.LEFT, k.A, k.RIGHT, k.D) and item is not None:
            increment = -1 if symbol in (k.LEFT, k.A) else 1
            for _ in range(repeat if isinstance(item, Number) else 1):
                item.change(increment, self)
        elif symbol in (k.ENTER, k.NUM_ENTER, k.SPACE) and item is not None:
            item.confirm(self)
        elif symbol in (k.BACKSPACE, k.M):
            self.go_back()
        else:
            return True      # the menu is open: keys do not go to the camera
        self.dirty = True
        return True

    def _item_at(self, y):
        for y0, y1, i in self._areas:
            if y0 <= y < y1:
                return i
        return None

    def mouse_over(self, x, y) -> bool:
        if not self.is_open or not self.stack:
            return False
        i = self._item_at(y) if x <= self._right_edge else None
        if i is not None and i != self.stack[-1][2]:
            self.stack[-1][2] = i
            self.dirty = True
        return True

    def click(self, x, y, button) -> bool:
        if not self.is_open or not self.stack:
            return False
        if button == pyglet.window.mouse.RIGHT:
            self.go_back()
            return True
        i = self._item_at(y) if x <= self._right_edge else None
        if i is not None:
            self.stack[-1][2] = i
            item = self._current_item()
            if item is not None:
                item.confirm(self)
        self.dirty = True
        return True

    def wheel(self, x, y, sy) -> bool:
        if not self.is_open or not self.stack:
            return False
        item = self._current_item()
        if item is not None and isinstance(item, (Choice, Number, YesNo)):
            item.change(1 if sy > 0 else -1, self)
            self.dirty = True
        return True

    # ---- drawing

    def draw_menu(self, win):
        if not self.is_open or not self.stack:
            return
        item_key = (win.width, win.height, id(self.stack[-1][1]))
        if self.dirty or item_key != self._draw_key:
            self._layout(win)
            self._draw_key = item_key
            self.dirty = False
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendEquation(GL_FUNC_ADD)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        self._batch.draw()

    def _layout(self, win):
        entry_name, menu_items, cursor = self.stack[-1]
        page = self.pages[entry_name]
        s = max(0.75, min(1.6, win.height / 760.0))
        batch = pyglet.graphics.Batch()
        beneath = pyglet.graphics.Group(order=0)
        above = pyglet.graphics.Group(order=1)
        drawables = []

        x0 = round(28 * s)
        width_units = min(round(page.width_units * s), win.width - 2 * x0)
        padding = round(16 * s)
        row, section_row_height, info_row_height = round(32 * s), round(26 * s), round(25 * s)
        font, font_section, font_title, font_info = 16 * s, 11.5 * s, 14 * s, 13.5 * s
        # the panel is anchored top-left and does NOT change size when moving
        # from one item to another: centring it and sizing the description to
        # its text made it jump under the mouse
        y_top = win.height - round(60 * s)
        bottom_margin = round(40 * s)

        def description_of(v):
            if v is None or not v.selectable or not v.desc:
                return ""
            # a texts.py key, or a function for computed descriptions
            return v.desc() if callable(v.desc) else t(v.desc)

        selected_item = menu_items[cursor] if menu_items and menu_items[cursor].selectable else None
        desc_rows = wrap_lines(description_of(selected_item), width_units - 2 * padding, 12 * s)
        # description space: that of the page's longest one, fixed
        page_key = (entry_name, id(menu_items), win.width, win.height)
        if self._desc_max.get("key") != page_key:
            max_desc_rows = max((len(wrap_lines(description_of(v), width_units - 2 * padding, 12 * s)) for v in menu_items),
                            default=0)
            self._desc_max = {"key": page_key, "rows": max_desc_rows}
        desc_row_height = round(18 * s)
        max_desc_rows = self._desc_max["rows"]
        desc_height = round(max_desc_rows * desc_row_height + 22 * s) if max_desc_rows else 0

        # which lines fit: scroll only when the cursor leaves the visible part,
        # and the start stays where it was (per page)
        row_heights = [section_row_height if isinstance(v, Section) else info_row_height if isinstance(v, Info) else row
                   for v in menu_items]
        space_avail = y_top - bottom_margin - round(34 * s) - desc_height - round(10 * s)
        start_line = min(self._start_lines.get(id(menu_items), 0), cursor)
        # the section right above the cursor stays visible with its title
        while start_line > 0 and start_line == cursor and isinstance(menu_items[start_line - 1], Section):
            start_line -= 1
        while sum(row_heights[start_line:cursor + 1]) > space_avail and start_line < cursor:
            start_line += 1
        self._start_lines[id(menu_items)] = start_line
        end_line = start_line
        while end_line < len(menu_items) and sum(row_heights[start_line:end_line + 1]) <= space_avail:
            end_line += 1

        # a scrolling page always takes all the space: otherwise the panel
        # would change height with the visible lines
        content_height = space_avail if sum(row_heights) > space_avail else sum(row_heights[start_line:end_line])
        panel_height = round(34 * s) + content_height + desc_height + round(10 * s)
        drawables.append(pyglet.shapes.Rectangle(x0, y_top - panel_height, width_units, panel_height,
                                           color=BACKGROUND_COLOR, batch=batch, group=beneath))
        # title
        drawables.append(pyglet.text.Label(page.title_text(), font_name=FONT, font_size=font_title,
                                     x=x0 + padding, y=y_top - round(20 * s), anchor_y="center",
                                     color=TITLE_COLOR, batch=batch, group=above))
        y = y_top - round(34 * s)
        drawables.append(pyglet.shapes.Line(x0 + padding, y, x0 + width_units - padding, y, thickness=1,
                                      color=LINE_COLOR, batch=batch, group=above))
        if start_line > 0:
            drawables.append(pyglet.text.Label("▲", font_name=FONT, font_size=9 * s, x=x0 + width_units - padding,
                                         y=y - round(8 * s), anchor_x="right", anchor_y="center",
                                         color=SECTION_COLOR, batch=batch, group=above))
        self._areas = []
        for i in range(start_line, end_line):
            v = menu_items[i]
            h = row_heights[i]
            middle = y - h / 2
            if isinstance(v, Section):
                drawables.append(pyglet.text.Label(v.label(), font_name=FONT, font_size=font_section,
                                             x=x0 + padding, y=middle - round(2 * s), anchor_y="center",
                                             color=SECTION_COLOR, batch=batch, group=above))
            else:
                selected = i == cursor and v.selectable
                if selected:
                    drawables.append(pyglet.shapes.Rectangle(x0, y - h, width_units, h, color=(70, 70, 70, 255) if v.disabled else HIGHLIGHT_COLOR,
                                                       batch=batch, group=beneath))
                draw_color = SELECTED_TEXT_COLOR if selected else (INFO_LEFT_COLOR if isinstance(v, Info) else TEXT_COLOR)
                if v.disabled:
                    draw_color = (170, 170, 170, 255) if selected else DISABLED_COLOR
                dim = font_info if isinstance(v, Info) else font
                value_text = v.value_text()
                # the label must not overlap the value: shorten it with "…"
                text_space = width_units - 2 * padding
                if value_text:
                    value_width = pyglet.text.Label(value_text, font_name=FONT, font_size=dim).content_width
                    text_space -= value_width + round(18 * s)
                drawables.append(pyglet.text.Label(ellipsize(v.label(), text_space, dim),
                                             font_name=FONT, font_size=dim,
                                             x=x0 + padding, y=middle, anchor_y="center",
                                             color=draw_color, batch=batch, group=above))
                if value_text:
                    value_color = SELECTED_TEXT_COLOR if selected else (INFO_RIGHT_COLOR if isinstance(v, Info) else VALUE_COLOR)
                    if v.disabled:
                        value_color = DISABLED_COLOR
                    drawables.append(pyglet.text.Label(value_text, font_name=FONT, font_size=dim,
                                                 x=x0 + width_units - padding, y=middle, anchor_x="right",
                                                 anchor_y="center", color=value_color,
                                                 batch=batch, group=above))
                if v.selectable:
                    self._areas.append((y - h, y, i))
            y -= h
        # bottom of the list: fixed even when the visible lines are shorter
        y = y_top - round(34 * s) - content_height
        if end_line < len(menu_items):
            drawables.append(pyglet.text.Label("▼", font_name=FONT, font_size=9 * s, x=x0 + width_units - padding,
                                         y=y + round(8 * s), anchor_x="right", anchor_y="center",
                                         color=SECTION_COLOR, batch=batch, group=above))
        if max_desc_rows:
            # the line and the space are always there if the page has descriptions
            y -= round(6 * s)
            drawables.append(pyglet.shapes.Line(x0 + padding, y, x0 + width_units - padding, y, thickness=1,
                                          color=LINE_COLOR, batch=batch, group=above))
            for n, label_text in enumerate(desc_rows):
                drawables.append(pyglet.text.Label(label_text, font_name=FONT, font_size=12 * s,
                                             x=x0 + padding, y=y - round(8 * s) - n * desc_row_height,
                                             anchor_y="top", color=DESCRIPTION_COLOR,
                                             batch=batch, group=above))
        self._right_edge = x0 + width_units
        self._batch, self._drawables = batch, drawables
