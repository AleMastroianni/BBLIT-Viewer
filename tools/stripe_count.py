"""How many bright columns a framing has: the measure of the walls' stripes.

    .venv/Scripts/python tools/stripe_count.py LS01 --camera 109.8,-120.2,-198.1,90,-15

Regular vertical stripes used to show where the wall flags paint: two
see-through surfaces of the same wall adding their alpha on the same pixel.
The count below is the measure used then and kept since, so
that any later number can be compared with the ones in the commits instead
of being eyeballed:

    in a window of the frame, a COLUMN counts when the average absolute
    difference between it and the column to its left, over the window's
    height, is more than THRESHOLD (6 of 255).

It always renders three frames from the same camera: the wall flags OFF (the
reference: whatever the scene itself has), and the fills at each alpha
asked for. Nothing else changes between them.

    --window x0,y0,x1,y1   the part of the frame measured (default: the one
                           the first measurements used, 430,270,620,370)
    --alpha 0.25,0.44      the fills to try (default: those two)
    --size 1280x760        the window, which decides where the pixels fall
    --save FOLDER          also write the frames

The numbers to compare with, from Era selector, after the stencil and the
real extent of the runs (two framings):

    camera 109.8,-120.2,-198.1   yaw 90 pitch -15   window 430,270,620,370
        walls off 0      fill 25% 0      fill 44% 0
    the same camera, window 400,240,720,400
        walls off 4      fill 25% 12     fill 44% 11
    camera 109.8,-120.2,-198.1   yaw 0 pitch 10     window 0,380,640,560
        walls off 14     fill 25% 22     fill 44% 78

Before the stencil the first window counted 41 with everything on. The
stripes that were the doubling are gone at either fill; what the third
framing measures is that a stronger fill carries every faint boundary of
the scene over the threshold, which is why 44% counts more there.
"""

from __future__ import annotations

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

THRESHOLD = 6.0          # of 255: how big a jump between two columns counts
DEFAULT_WINDOW = (430, 270, 620, 370)


def columns(image, window):
    """The columns of `window` that jump from the one on their left."""
    x0, y0, x1, y1 = window
    grey = image.convert("L").crop((x0, y0, x1, y1))
    width, height = grey.size
    pixels = grey.load()
    return sum(1 for x in range(1, width)
               if sum(abs(pixels[x, y] - pixels[x - 1, y]) for y in range(height)) / height > THRESHOLD)


def main():
    import pyglet
    from PIL import Image
    from pyglet.math import Vec3
    from support import paths
    from window import drawing
    import viewer

    argv = sys.argv[1:]
    def option(name, fallback=None):
        return argv[argv.index(name) + 1] if name in argv else fallback
    taken = {i + 1 for i, a in enumerate(argv) if a.startswith("--")}
    names = [a for i, a in enumerate(argv) if not a.startswith("--") and i not in taken]
    level = names[0] if names else "LS01"
    camera = [float(w) for w in option("--camera", "109.8,-120.2,-198.1,90,-15").split(",")]
    window = tuple(int(w) for w in option("--window", ",".join(str(v) for v in DEFAULT_WINDOW)).split(","))
    alphas = [float(w) for w in option("--alpha", "0.25,0.44").split(",")]
    width, height = (int(w) for w in option("--size", "1280x760").lower().split("x"))
    save = option("--save")
    if save:
        os.makedirs(save, exist_ok=True)

    v = viewer.Viewer([os.path.join(paths.DATA_BZE, level + ".bze")], "extracted", 0,
                      screenshot="none.png")
    v.screenshot = None
    # the flags of the user's framing: everything the walls share the frame
    # with, so the count is of the same picture as the first measurements
    v.show_area_boxes = v.show_collision_boxes = v.show_ground = True
    v.show_hard_walls = v.show_steps = "all"
    v.show_hole_steps = True
    v.ensure_overlays()
    v.set_size(width, height)
    for _ in range(6):
        v.dispatch_events()
    v.pos, v.yaw, v.pitch = Vec3(camera[0], camera[1], camera[2]), camera[3], camera[4]

    def shot(tag):
        v.on_draw()
        path = os.path.join(save or ".", f"stripe_{tag}.png")
        pyglet.image.get_buffer_manager().get_color_buffer().save(path)
        image = Image.open(path)
        n = columns(image, window)
        if not save:
            os.remove(path)
        return n

    print(f"{level}, camera {camera}, finestra {window}, soglia {THRESHOLD:.0f}/255")
    rows = []
    walls_before = (v.show_hard_walls, v.show_steps)
    v.show_hard_walls = v.show_steps = False
    rows.append(("flag dei muri SPENTE", shot("walls_off")))
    v.show_hard_walls, v.show_steps = walls_before
    kept = drawing.WALL_ALPHA
    for alpha in alphas:
        drawing.WALL_ALPHA = alpha
        rows.append((f"riempimento {alpha * 100:.0f}%", shot(f"alpha{int(alpha * 100)}")))
    drawing.WALL_ALPHA = kept
    for label, n in rows:
        print(f"   {label:24s} {n:4d} colonne")
    v.close()


if __name__ == "__main__":
    main()
