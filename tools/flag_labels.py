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
# (the user's list): a name alone is written in full, several are joined as
# "DTH + DMG"
ABBREVIATIONS = {
    "NO COLLISION": "NOC",
    "INVISIBLE WALL": "INV",
    "HARD WALL": "HRD",
    "DEATH": "DTH",
    "DEATH FLOOR": "DFL",
    "DAMAGE": "DMG",
    "RESPAWN": "RSP",
    "STEP WALL": "STP",
}


def combined(names) -> str:
    """The text for a thing that is all of `names`: the full name if one,
    otherwise the three-letter forms in ABBREVIATIONS order."""
    names = [n for n in ABBREVIATIONS if n in set(names)]
    if len(names) == 1:
        return names[0]
    return " + ".join(ABBREVIATIONS[n] for n in names)


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
