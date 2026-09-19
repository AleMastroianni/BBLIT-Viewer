"""The logo: our own blue background, the golden carrot, the title in
Luckiest Guy (Apache 2.0, branding/fonts).

    python branding/source/logo.py

Writes banner_background.png, logo.png, social_preview.png (1280 x 640, for
GitHub) and background.png (the viewer's background without levels, 1920 x
1080) into branding/."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # branding/
FONTS = os.path.join(D, "fonts")
OUT = D
W, H = 1280, 400


def background(w, h):
    """A deep blue vertical gradient with a soft light in the upper left and
    a few faint rings: ours, in the spirit of the CTR viewer's blue."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = y / h
            base = (int(12 + 18 * (1 - t)), int(34 + 40 * (1 - t)), int(88 + 70 * (1 - t)))
            glow = max(0.0, 1 - math.hypot(x - w * 0.22, y - h * 0.25) / (w * 0.55))
            px[x, y] = tuple(min(255, int(c + g)) for c, g in zip(base, (30 * glow, 60 * glow, 90 * glow)))
    rings = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(rings)
    for r in range(140, 1400, 120):          # clock-face rings, very faint
        d.ellipse([w * 0.18 - r, h * 0.5 - r, w * 0.18 + r, h * 0.5 + r], outline=(255, 255, 255, 14), width=3)
    return Image.alpha_composite(img.convert("RGBA"), rings)


def title(img, text, font_path, size, y, fill_top, fill_bottom, outline, x0):
    font = ImageFont.truetype(font_path, size)
    d = ImageDraw.Draw(img)
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=10)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # shadow
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x0 + 8, y + 10), text, font=font, fill=(0, 0, 0, 160), stroke_width=10,
                            stroke_fill=(0, 0, 0, 160))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    # outline
    ImageDraw.Draw(img).text((x0, y), text, font=font, fill=outline, stroke_width=10, stroke_fill=outline)
    # gold gradient fill through a mask
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text((x0, y), text, font=font, fill=255)
    grad = Image.new("RGBA", img.size)
    gp = grad.load()
    top, bottom = y + bbox[1], y + bbox[3]
    for yy in range(img.size[1]):
        t = min(1, max(0, (yy - top) / max(1, bottom - top)))
        col = tuple(int(fill_top[i] + (fill_bottom[i] - fill_top[i]) * t) for i in range(3)) + (255,)
        for xx in range(img.size[0]):
            gp[xx, yy] = col
    img.paste(grad, (0, 0), mask)
    return tw, th


def logo_on(img, carrot, dy=0):
    """Carrot, title and subtitle of the logo, moved down by `dy`."""
    img.alpha_composite(carrot.resize((330, 330), Image.LANCZOS), (30, 35 + dy))
    font = os.path.join(FONTS, "LuckiestGuy-Regular.ttf")
    title(img, "BBLIT Viewer", font, 132, 60 + dy, (255, 236, 140), (230, 150, 20), (60, 25, 5, 255), 370)
    sub = ImageFont.truetype(font, 40)
    ImageDraw.Draw(img).text((376, 60 + 132 + 58 + dy), "a level viewer for Bugs Bunny: Lost in Time", font=sub,
                             fill=(220, 232, 255, 255), stroke_width=3, stroke_fill=(10, 25, 60, 255))
    return img


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from golden_carrot import carrot
    background(1920, 1080).convert("RGB").save(os.path.join(OUT, "background.png"))
    bg = background(W, H)
    bg.save(os.path.join(OUT, "banner_background.png"))
    logo_on(bg.copy(), carrot()).convert("RGB").save(os.path.join(OUT, "logo.png"))
    # GitHub's social preview wants 2:1 (1280 x 640): the same logo, centred
    # on a taller background
    logo_on(background(W, 640), carrot(), dy=120).convert("RGB").save(os.path.join(OUT, "social_preview.png"))


if __name__ == "__main__":
    main()
