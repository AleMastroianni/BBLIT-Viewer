"""How far a wall's tinted surface moves away from the same surface untinted.

    .venv/Scripts/python tools/fill_contrast.py LS01 --camera 109.8,-120.2,-198.1,90,-15

`stripe_count.py` counts the boundaries a fill adds to a framing: it says
whether the fill flickers, never whether it can be READ. This is the other
number. It renders the SAME frame twice, with only `drawing.WALL_ALPHA`
changed -- the outlines and the names are drawn at full alpha either way, so
they are identical in both -- and measures, over the pixels the fill actually
covers, how much the picture moved:

    dL   the average |difference| in LUMINANCE (0.299 R + 0.587 G + 0.114 B),
         in levels of 255. This is the number that matters here: the user is
         colour-blind, so a tint that only moves the hue does not exist for
         him.
    dRGB the same average over the three channels, for comparison.
    weak the share of the covered pixels whose |dL| is under WEAK (8 of 255).

The criterion used to judge, stated so a later run can disagree with it: on a
textured surface, under a camera that moves, a tint reads when dL is at least
GOOD (12 of 255, about 5% of the range) and fewer than a third of its pixels
are weak. Under that, the tint has to be made LIGHTER -- the colour, not the
alpha, because the alpha is what brings the boundaries back (stripe_count).

    --alpha 0.25,0.44   the fills to measure (default: those two)
    --window x0,y0,x1,y1  only this part of the frame (default: all of it)
    --save FOLDER       also write the frames and a map of the covered pixels

The numbers the choice of 25% was made on: 1280x760, the whole frame, with
Hard walls and Steps on "all":

    level and camera                      fill   dL    weak    covered
    Era selector 109.8,-120.2,-198.1,90,-15   25%  28.6   0.1%   44.9%
                                              44%  50.0   0.0%   44.9%
    the same, yaw 0 pitch 10                  25%  30.0   0.5%   85.5%
                                              44%  51.3   0.2%   85.5%
    Hey... What's up, Dock? 1  268,12,-130,160,-15
                                              25%  22.8   5.7%   72.5%
                                              44%  38.8   2.2%   72.5%
    the same, 245.9,20.1,-39.7,180,-15        25%  24.1   2.3%   17.4%
                                              44%  42.1   0.5%   17.4%

So 25% keeps dL between 23 and 30 -- about twice GOOD -- and leaves at most
5.7% of its pixels weak: the fill is paler than the two layers that used to
overlap, and still reads. The colour was left as it is.
"""

from __future__ import annotations

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_DIR, "bblit"))
os.chdir(PROJECT_DIR)

WEAK = 8.0        # of 255: under this a covered pixel did not really move
GOOD = 12.0       # of 255: the average a fill needs to read (see above)
LUMA = (0.299, 0.587, 0.114)


def luminance(image):
    """One list of floats per pixel, the luminance of the frame."""
    px = image.convert("RGB").load()
    w, h = image.size
    return [[sum(c * k for c, k in zip(px[x, y], LUMA)) for x in range(w)] for y in range(h)]


def channels(image):
    px = image.convert("RGB").load()
    w, h = image.size
    return [[px[x, y] for x in range(w)] for y in range(h)]


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
    alphas = [float(w) for w in option("--alpha", "0.25,0.44").split(",")]
    width, height = (int(w) for w in option("--size", "1280x760").lower().split("x"))
    save = option("--save")
    if save:
        os.makedirs(save, exist_ok=True)
    win = option("--window")
    window = tuple(int(w) for w in win.split(",")) if win else (0, 0, width, height)

    v = viewer.Viewer([os.path.join(paths.DATA_BZE, level + ".bze")], "extracted", 0,
                      screenshot="none.png")
    v.screenshot = None
    v.show_hard_walls = v.show_steps = "all"
    v.show_hole_steps = True
    v.ensure_overlays()
    v.set_size(width, height)
    for _ in range(6):
        v.dispatch_events()
    v.pos, v.yaw, v.pitch = Vec3(camera[0], camera[1], camera[2]), camera[3], camera[4]

    def shot(tag):
        v.on_draw()
        path = os.path.join(save or ".", f"contrast_{tag}.png")
        pyglet.image.get_buffer_manager().get_color_buffer().save(path)
        image = Image.open(path).convert("RGB")
        if not save:
            os.remove(path)
        return image

    kept = drawing.WALL_ALPHA
    drawing.WALL_ALPHA = 0.0
    flat = shot("alpha00")          # the same surface, NOT tinted
    flat_l, flat_c = luminance(flat), channels(flat)
    x0, y0, x1, y1 = window
    print(f"{level}, camera {camera}, {width}x{height}, finestra {window}")
    print(f"   criterio: dL medio >= {GOOD:.0f}/255 e meno di un terzo di pixel deboli (<{WEAK:.0f})")
    for alpha in alphas:
        drawing.WALL_ALPHA = alpha
        tinted = shot(f"alpha{int(round(alpha * 100))}")
        t_l, t_c = luminance(tinted), channels(tinted)
        d_l, d_rgb, weak = [], [], 0
        for y in range(y0, y1):
            for x in range(x0, x1):
                if t_c[y][x] == flat_c[y][x]:
                    continue                      # the fill does not cover it
                dl = abs(t_l[y][x] - flat_l[y][x])
                d_l.append(dl)
                d_rgb.append(sum(abs(a - b) for a, b in zip(t_c[y][x], flat_c[y][x])) / 3.0)
                weak += dl < WEAK
        if not d_l:
            print(f"   riempimento {alpha * 100:4.0f}%   nessun pixel coperto")
            continue
        d_l.sort()
        mean = sum(d_l) / len(d_l)
        median = d_l[len(d_l) // 2]
        share = 100.0 * len(d_l) / ((x1 - x0) * (y1 - y0))
        print(f"   riempimento {alpha * 100:4.0f}%   dL medio {mean:5.1f}   mediano {median:5.1f}"
              f"   dRGB {sum(d_rgb) / len(d_rgb):5.1f}"
              f"   deboli {100.0 * weak / len(d_l):4.1f}%"
              f"   copre {share:4.1f}% della finestra ({len(d_l)} px)")
    drawing.WALL_ALPHA = kept
    v.close()


if __name__ == "__main__":
    main()
