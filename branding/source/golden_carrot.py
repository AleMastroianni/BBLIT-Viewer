"""The golden carrot: the BBLIT viewer's icon, drawn from scratch.

    python branding/source/golden_carrot.py

Writes icon_goldcarrot_{256,128,64,32,16}.png and icon_goldcarrot.ico into
branding/. `carrot()` is also used by logo.py."""
import math
import os

from PIL import Image, ImageDraw, ImageFilter

D = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # branding/
OUT = D
S = 1024


def carrot():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # the carrot runs diagonally: top at the upper right, tip at the lower left
    top = (650, 360)
    tip = (215, 860)
    ax, ay = tip[0] - top[0], tip[1] - top[1]
    ln = math.hypot(ax, ay)
    ux, uy = ax / ln, ay / ln            # along the carrot
    nx, ny = -uy, ux                     # across
    half = 150                           # half width at the top

    def at(t, s):
        """Point at fraction t along the carrot (0 top, 1 tip), s across (-1..1)."""
        w = half * (1 - t) ** 0.85 * (1 + 0.25 * math.sin(t * math.pi))
        return (top[0] + ax * t + nx * w * s, top[1] + ay * t + ny * w * s)

    # leaves behind the carrot, green
    leaves = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaves)
    base = at(0.0, 0)
    for ang, length in ((-58, 300), (-32, 340), (-5, 300), (22, 250)):
        a = math.radians(ang)
        dx, dy = -ux * math.cos(a) + nx * math.sin(a), -uy * math.cos(a) + ny * math.sin(a)
        end = (base[0] + dx * length, base[1] + dy * length)
        mid = (base[0] + dx * length * 0.55 - nx * 30, base[1] + dy * length * 0.55 - ny * 30)
        pts = [base, (mid[0] + nx * 45, mid[1] + ny * 45), end, (mid[0] - nx * 45, mid[1] - ny * 45)]
        ld.polygon(pts, fill=(60, 165, 55, 255), outline=(25, 90, 30, 255))
        ld.line([base, end], fill=(35, 120, 40, 255), width=10)
    img.alpha_composite(leaves)

    # body: polygon along the outline, filled with a gold gradient across it
    outline = [at(t / 60, 1) for t in range(61)] + [at(t / 60, -1) for t in range(60, -1, -1)]
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    body = Image.new("RGBA", (S, S))
    bp = body.load()
    for y in range(S):
        for x in range(S):
            # position across the carrot, -1..1, gives the shading
            s = ((x - top[0]) * nx + (y - top[1]) * ny) / half
            t = max(0, min(1, (-s + 1) / 2))
            light = 1 - abs(t - 0.28) * 1.4
            light = max(0.0, min(1.0, light))
            r = int(190 + 65 * light)
            g = int(125 + 110 * light)
            b = int(10 + 90 * light ** 3)
            bp[x, y] = (r, g, b, 255)
    img.paste(body, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.polygon(outline, outline=(120, 70, 5, 255))
    d.line(outline + [outline[0]], fill=(120, 70, 5, 255), width=12, joint="curve")
    # grooves
    for t, s0, s1 in ((0.18, -0.9, 0.3), (0.33, -0.2, 0.85), (0.48, -0.85, 0.2), (0.63, -0.1, 0.8),
                      (0.77, -0.7, 0.2)):
        d.line([at(t, s0), at(t + 0.035, s1)], fill=(150, 90, 10, 255), width=10)
    # a sparkle
    sx, sy = at(0.22, -0.35)
    for k, r in ((0, 70), (1, 38)):
        pts = []
        for i in range(8):
            a = math.radians(i * 45 + 22.5 * k)
            rr = r if i % 2 == 0 else r * 0.22
            pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
        d.polygon(pts, fill=(255, 255, 235, 255 if k == 0 else 200))
    # soft shadow
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(p[0] + 18, p[1] + 26) for p in outline], fill=(0, 0, 0, 110))
    sh = sh.filter(ImageFilter.GaussianBlur(22))
    return Image.alpha_composite(sh, img)


def main():
    big = carrot()
    for n in (256, 128, 64, 32, 16):
        big.resize((n, n), Image.LANCZOS).save(os.path.join(OUT, f"icon_goldcarrot_{n}.png"))
    big.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "icon_goldcarrot.ico"), sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
