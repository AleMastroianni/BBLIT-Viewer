"""The name of a flag written inside its faces, as in the CTR viewer's FLAG
tiles: one texture per flag and language (black letters on transparent),
painted on each face with its own texture coordinates, not one text label
per face (No collision alone has 32 thousand faces).

`label_uvs` places the text on a face: along its longest edge on a floor,
level and upright on a wall, centred on the face and as large as fits;
None where the text would be too small to read.
"""

from __future__ import annotations

import os

TEXTURE_SIZE = (512, 128)       # the text box: 4 : 1
MIN_HEIGHT = 48                 # game units (about 37 cm): smaller text is left out
FILL = 0.8                      # of the face's inner size

_FONTS = ("segoeuib.ttf", "arialbd.ttf")

# the names and, in this order, their three-letter forms for combined names
# (a fixed list): a name alone is written in full, several are joined as
# "DTH + DMG"
ABBREVIATIONS = {
    "NO COLLISION": "NOC",
    "INVISIBLE WALL": "INV",
    "HARD WALL": "HRD",
    "DEATH": "DTH",
    "DEATH FLOOR": "DFL",
    "DAMAGE": "DMG",
    "ENTRANCE": "ENT",
    "TELEPORT": "TLP",
    "DEAD TELEPORT": "DEAD",
    "DEAD RECOVER": "DEAD",
    "DEAD RESTART": "DEAD",
    "RECOVER": "RCV",
    "RESTART": "RST",
    "LEVEL": "LVL",
    "STEP WALL": "STP",
    # the rim of a floor over the void (overlays.COLOR_EDGE)
    "EDGE": "EDG",
    # the four abilities a magic device asks for (finding 336): on its box the
    # ability is written instead of what the box does
    "FAN": "FAN",
    "MUSIC": "MUS",
    "SUPER JUMP": "JMP",
    "OPEN SESAME": "SES",
    "SOLID": "SLD",
    "PLATFORM": "PLT",
    "TOUCH": "TCH",
}


def combined(names) -> str:
    """The text for a thing that is all of `names`: the full name if one,
    otherwise the three-letter forms in ABBREVIATIONS order."""
    names = [n for n in ABBREVIATIONS if n in set(names)]
    if len(names) == 1:
        return names[0]
    return " + ".join(ABBREVIATIONS[n] for n in names)


def gate_text(opened_by) -> str:
    """"GATE" for a box that changes with the object's state, "GATE <- #78"
    when the data say who opens it (findings 323, 331). More than three
    switches are cut with an ellipsis: the whole chain is in the list."""
    if not opened_by:
        return "GATE"
    shown = ["#%d" % n for n in sorted(opened_by)[:3]]
    if len(opened_by) > 3:
        shown.append("...")
    return "GATE <- " + "+".join(shown)


def reacts_text(writers) -> str:
    """"REACTS <- #78": this object waits on a byte that one writes, but it is
    not a gate that opens (flag Who opens what, "All the links")."""
    shown = ["#%d" % n for n in sorted(writers)[:3]]
    if len(writers) > 3:
        shown.append("...")
    return "REACTS <- " + "+".join(shown)


def box_label(numbers, kinds, hurts=(), hard=False, gate=None) -> str:
    """The name written above a collision box: the object's number, what the
    box does to Bugs, whether it is hard (`+8 & 0x20000`: it stops the camera
    too), and what hurts about it (finding 318).

    "#109 SOLID", "#37 SOLID · HARD", "#109 SOLID · BLOW 1" when the object
    hurts in the state being shown, "#109 SOLID · (BLOW 1)" when only another
    of its states does. Several objects sharing a box: "#64+#65 SLD + TCH",
    with their hazards joined, the worst state winning.
    """
    text = "+".join("#%d" % n for n in sorted(numbers)) + " " + combined(kinds)
    if hard:
        text += " · HARD"
    if gate is not None:
        text += " · " + gate
    if not hurts:
        return text
    when = "now" if any(h[0] == "now" for h in hurts) else "other"
    chosen = [h for h in hurts if h[0] == when]
    names = []
    for _when, how, _damage in chosen:
        names += [n for n in how if n not in names]
    danger = "+".join(names) + " " + str(max(h[2] for h in chosen))
    return text + " · " + (danger if when == "now" else "(%s)" % danger)


FLOATING_HEIGHT = 128            # rows of a floating label's texture
FLOATING_OUTLINE = 6             # the black outline around the white letters


def floating_texture_rgba(text: str) -> tuple[int, int, bytes]:
    """A label that floats above an object (the collision boxes' names): white
    letters with a black outline, on a transparent strip only as wide as the
    text, so the letters are the same size whatever the text says.

    (width, height, RGBA bytes, first row at the top). The outline is what
    makes it readable over the sky, the sea and the wood alike.
    """
    from PIL import Image, ImageDraw, ImageFont

    height = FLOATING_HEIGHT
    size = height - 2 * FLOATING_OUTLINE - 8
    font = None
    for name in _FONTS:
        try:
            font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name), size)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    measure = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    box = measure.textbbox((0, 0), text, font=font, stroke_width=FLOATING_OUTLINE)
    width = max(8, box[2] - box[0] + 2 * FLOATING_OUTLINE)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((FLOATING_OUTLINE - box[0], (height - (box[3] - box[1])) / 2 - box[1]), text,
                             font=font, fill=(255, 255, 255, 255),
                             stroke_width=FLOATING_OUTLINE, stroke_fill=(0, 0, 0, 255))
    return width, height, img.tobytes()


def clone_label(n_template, n_parent, kinds, hurts=(), hard=False) -> str:
    """The name of a clone's box: "T74 of #117 SOLID · HURT 1".
    A clone has no object number of its own, so it says which
    template it is and whose clone it is."""
    return "T%d of #%d %s" % (n_template, n_parent,
                              box_label([], kinds, hurts, hard).lstrip(" "))


def texture_rgba(text: str) -> tuple[int, int, bytes]:
    """(width, height, RGBA bytes, first row at the top): black letters on
    transparent, a transparent border so clamped texture coordinates
    outside the text stay empty."""
    from PIL import Image, ImageDraw, ImageFont

    width, height = TEXTURE_SIZE
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = None
    for name in _FONTS:
        try:
            font = ImageFont.truetype(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name), 80)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    scale = min((width - 16) / max(1, tw), (height - 16) / max(1, th), 1.0)
    if scale < 1.0 and hasattr(font, "font_variant"):
        font = font.font_variant(size=max(8, int(80 * scale)))
        box = draw.textbbox((0, 0), text, font=font)
        tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((width - tw) / 2 - box[0], (height - th) / 2 - box[1]), text, font=font, fill=(0, 0, 0, 255))
    return width, height, img.tobytes()


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    ln = _dot(a, a) ** 0.5
    return (a[0] / ln, a[1] / ln, a[2] / ln) if ln else None


def label_uvs(points, from_below=False, max_height=None):
    """Texture coordinates (0..1 inside the text box) for the corners of a
    face in game coordinates (Y down; a quad in Z order), or None if the
    text would be smaller than MIN_HEIGHT. A floor's text reads right seen
    from above, or from below with `from_below` (a ceiling). `max_height`
    (game units) caps the text on large faces."""
    n = _unit(_cross(_sub(points[1], points[0]), _sub(points[2], points[0])))
    if n is None:
        return None
    if abs(n[1]) < 0.7:
        # a wall: the text level, its rows going down the wall (+Y is down)
        e1 = _unit(_cross((0.0, 1.0, 0.0), n))
        if e1 is None:
            return None
        e2 = _cross(n, e1)
        if e2[1] < 0:
            e2 = (-e2[0], -e2[1], -e2[2])
    else:
        # a floor: along the longest edge, always pointing the same way
        # (+X first), and not mirrored seen from above: e1 x e2 points down
        # (+Y), as right x down points into the screen
        # a quad is Z-ordered (0, 1, 3, 2 around), as the viewer draws it:
        # taken in order, two of its "edges" would be the diagonals
        ring = [points[0], points[1], points[3], points[2]] if len(points) == 4 else points
        edges = [_sub(ring[(i + 1) % len(ring)], ring[i]) for i in range(len(ring))]
        e1 = _unit(max(edges, key=lambda e: _dot(e, e)))
        if e1 is None:
            return None
        if e1[0] < 0 or (e1[0] == 0 and e1[2] < 0):
            e1 = (-e1[0], -e1[1], -e1[2])
        down = n if n[1] > 0 else (-n[0], -n[1], -n[2])
        if from_below:
            down = (-down[0], -down[1], -down[2])
        e2 = _cross(down, e1)
    s = [_dot(p, e1) for p in points]
    t = [_dot(p, e2) for p in points]
    sc, tc = sum(s) / len(s), sum(t) / len(t)
    aspect = TEXTURE_SIZE[0] / TEXTURE_SIZE[1]
    inner = 1.0 if len(points) >= 4 else 0.5         # a triangle holds less
    w = FILL * inner * min(max(s) - min(s), (max(t) - min(t)) * aspect)
    h = w / aspect
    if h < MIN_HEIGHT:
        return None
    if max_height is not None and h > max_height:
        h = max_height
        w = h * aspect
    return [((si - sc) / w + 0.5, (ti - tc) / h + 0.5) for si, ti in zip(s, t)]
