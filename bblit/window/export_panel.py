"""The panel of Level options -> Export (support/export.py): at the top
centre of the window, over the menu and whatever the status bar shows,
while an export runs and after it, until it is closed. The viewer stays
usable: the panel takes no key, only the clicks on its own buttons.

While it runs: a progress bar with the percentage written next to it (a
number, not the bar's colour alone), what is being exported, the time
left, and that closing the viewer would stop it. At the end: the outcome,
"Open the folder" and "Close". Where the window is too narrow for the
panel beside the menu, it moves to the menu's right or under it.
"""

from __future__ import annotations

import os

import pyglet

from ui.menu import (BACKGROUND_COLOR, FONT, HIGHLIGHT_COLOR, LINE_COLOR, SELECTED_TEXT_COLOR,
                     TEXT_COLOR, TITLE_COLOR, wrap_lines)
from ui.texts import t

WIDTH_UNITS = 560
BAR_COLOR = (168, 96, 26, 255)
BAR_BACK = (60, 60, 60, 255)


def eta_words(seconds) -> str:
    """", circa 1 min 40 rimasti" / ", about 1 min 40 left"; nothing
    while there is no measure yet."""
    if seconds is None:
        return ""
    seconds = int(round(seconds))
    words = f"{seconds // 60} min {seconds % 60:02d}" if seconds >= 60 else f"{max(1, seconds)} s"
    return t("export.panel.eta", t=words)


def outcome(status: dict) -> str:
    """The sentence of an export that ended."""
    state = status.get("state")
    if state == "busy":
        return t("export.busy")
    if state == "failed":
        kind = status.get("error")
        if kind == "disk_full":
            return t("export.fail.disk")
        if kind == "not_writable":
            return t("export.fail.folder", folder=status.get("where") or status.get("folder", ""))
        return t("export.fail.other")
    skipped = status.get("skipped") or []
    if status.get("job") == "all":
        counts, totals = status.get("counts", {}), status.get("totals", {})
        missing = sum((status.get("missing") or {}).values()) + (status.get("unreadable") or 0)
        n, total = counts.get("level", 0), totals.get("level", 0)
        if missing or skipped or n != total:
            return t("export.done.some", n=n, total=total)
        return t("export.done.all", n=n)
    if len(skipped) == 1:
        return t("export.done.except", file=os.path.basename(skipped[0]))
    if skipped:
        return t("export.done.except_many", n=len(skipped))
    return t("export.done.one", level=status.get("level", ""))


def running_lines(status: dict, current_folder: str | None) -> tuple[list[str], float | None]:
    """The panel's sentences while the export runs, and how far it is (0..1,
    None for one level)."""
    if status.get("job") != "all":
        return [t("export.panel.one", level=status.get("level", "")), t("export.panel.keep")], None
    phase = status.get("phase", "level")
    eta = eta_words(status.get("eta"))
    n = min(status.get("phase_done", 0) + 1, status.get("phase_total", 0) or 1)
    total = status.get("phase_total", 0)
    words = {"level": "export.panel.levels", "extra": "export.panel.extra", "loading": "export.panel.loading"}
    lines = [t(words.get(phase, "export.panel.levels"), n=n, total=total, eta=eta)]
    source = status.get("source")
    if source and current_folder and os.path.normcase(os.path.abspath(source)) != \
            os.path.normcase(os.path.abspath(current_folder)):
        lines.append(t("export.panel.from", folder=source))
    lines.append(t("export.panel.keep"))
    done, whole = status.get("done", 0), status.get("total", 0)
    return lines, (done / whole if whole else 0.0)


class ExportPanel:
    def __init__(self):
        self.buttons = []        # (x0, y0, x1, y1, what) of the drawn buttons
        self._batch = None
        self._key = None
        self.rect = None         # where it was drawn (x, y, width, height), for the checks

    def content(self, win):
        """(lines, fraction or None, finished) of what to show, or None."""
        status = win.export_status
        if not status or win.export_panel_closed:
            return None
        if status.get("state") in ("starting", "running") and win._export_proc is not None:
            lines, fraction = running_lines(status, win.folder)
            return lines, fraction, False
        if win._export_proc is None and status.get("state") in ("starting", "running"):
            status = dict(status, state="failed", error="other")   # ended without saying so
        return [outcome(status)], None, True

    def draw(self, win):
        content = self.content(win)
        if content is None:
            self.buttons, self.rect = [], None
            return
        lines, fraction, finished = content
        s = max(0.75, min(1.6, win.height / 760.0))
        menu_rect = getattr(win.menu, "drawn_rect", None) if win.menu.is_open else None
        key = (tuple(lines), None if fraction is None else round(fraction, 3), finished,
               win.width, win.height, menu_rect)
        if key != self._key:
            self._layout(win, lines, fraction, finished, s, menu_rect)
            self._key = key
        pyglet.gl.glEnable(pyglet.gl.GL_BLEND)
        self._batch.draw()

    def _layout(self, win, lines, fraction, finished, s, menu_rect):
        batch = pyglet.graphics.Batch()
        beneath, above = pyglet.graphics.Group(order=0), pyglet.graphics.Group(order=1)
        margin, padding = round(16 * s), round(14 * s)
        width = min(round(WIDTH_UNITS * s), win.width - 2 * margin)
        font = 12.5 * s
        rows = [row for line in lines for row in wrap_lines(line, width - 2 * padding, font)]
        row_h = round(21 * s)
        bar_h = round(14 * s) if fraction is not None else 0
        button_h = round(28 * s) if finished else 0
        height = padding * 2 + len(rows) * row_h + (bar_h + round(10 * s) if bar_h else 0) \
            + (button_h + round(10 * s) if button_h else 0)
        x = (win.width - width) // 2
        top = win.height - round(12 * s)
        if menu_rect is not None:
            mx, my, mw, mh = menu_rect
            if x < mx + mw + margin:
                if mx + mw + margin + width <= win.width - margin:
                    x = mx + mw + margin                      # beside the menu
                else:
                    top = my - round(12 * s)                  # under it
        y = top - height
        self.rect = (x, y, width, height)
        keep = [pyglet.shapes.Rectangle(x, y, width, height, color=BACKGROUND_COLOR, batch=batch, group=beneath),
                pyglet.shapes.Box(x, y, width, height, thickness=1, color=LINE_COLOR, batch=batch, group=above)]
        cursor = top - padding
        for row in rows:
            keep.append(pyglet.text.Label(row, font_name=FONT, font_size=font, x=x + padding,
                                          y=cursor - row_h / 2, anchor_y="center",
                                          color=TITLE_COLOR if finished else TEXT_COLOR,
                                          batch=batch, group=above))
            cursor -= row_h
        if bar_h:
            cursor -= round(6 * s)
            percent = f"{int(fraction * 100)}%"
            label = pyglet.text.Label(percent, font_name=FONT, font_size=11 * s, x=x + width - padding,
                                      y=cursor - bar_h / 2, anchor_x="right", anchor_y="center",
                                      color=SELECTED_TEXT_COLOR, batch=batch, group=above)
            bar_w = width - 2 * padding - round(48 * s)
            keep += [label,
                     pyglet.shapes.Rectangle(x + padding, cursor - bar_h, bar_w, bar_h, color=BAR_BACK,
                                             batch=batch, group=beneath),
                     pyglet.shapes.Rectangle(x + padding, cursor - bar_h, max(1, round(bar_w * fraction)),
                                             bar_h, color=BAR_COLOR, batch=batch, group=above)]
            cursor -= bar_h + round(4 * s)
        self.buttons = []
        if button_h:
            cursor -= round(6 * s)
            bx = x + padding
            for what, words in (("open", t("export.open_folder")), ("close", t("export.close"))):
                label = pyglet.text.Label(words, font_name=FONT, font_size=12 * s, x=0, y=0)
                bw = label.content_width + round(24 * s)
                keep += [pyglet.shapes.Rectangle(bx, cursor - button_h, bw, button_h, color=HIGHLIGHT_COLOR,
                                                 batch=batch, group=beneath),
                         pyglet.text.Label(words, font_name=FONT, font_size=12 * s, x=bx + bw / 2,
                                           y=cursor - button_h / 2, anchor_x="center", anchor_y="center",
                                           color=SELECTED_TEXT_COLOR, batch=batch, group=above)]
                self.buttons.append((bx, cursor - button_h, bx + bw, cursor, what))
                bx += bw + round(10 * s)
        self._batch, self._keep = batch, keep

    def click(self, x, y) -> str | None:
        """What the click hit: "open", "close", "panel" (elsewhere on the
        panel: taken, so it does not reach the scene) or None."""
        for x0, y0, x1, y1, what in self.buttons:
            if x0 <= x <= x1 and y0 <= y <= y1:
                return what
        if self.rect is not None:
            px, py, pw, ph = self.rect
            if px <= x <= px + pw and py <= y <= py + ph:
                return "panel"
        return None
