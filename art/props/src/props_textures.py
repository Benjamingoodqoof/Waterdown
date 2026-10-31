#!/usr/bin/env python3
"""Paints the flat artwork the props use: tape labels (one written on in marker, one blank for
the game to write on), the camcorder's playback screen, and the small printed markings.

Usage: python3 props_textures.py OUT_DIR
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SANS = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
MARKER = "/usr/share/fonts/truetype/freefont/FreeSansBoldOblique.ttf"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, int(size))


def paper(w, h, rng):
    img = Image.new("RGB", (w, h), (236, 232, 220))
    px = img.load()
    for _ in range(w * h // 30):  # paper grain
        x, y = rng.randrange(w), rng.randrange(h)
        c = px[x, y]
        d = rng.randint(-10, 6)
        px[x, y] = (c[0] + d, c[1] + d, c[2] + d)
    return img


def marker(img, text, x, y, size, rng, color=(22, 30, 70)):
    """Hand-written-looking text: each letter tilted and nudged a little, ink slightly uneven."""
    f = font(MARKER, size)
    for ch in text:
        layer = Image.new("RGBA", (int(size * 1.6), int(size * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((size * 0.3, size * 0.15), ch, font=f, fill=color + (rng.randint(215, 245),))
        layer = layer.rotate(rng.uniform(-7, 7), resample=Image.BICUBIC)
        img.alpha_composite(layer, (int(x), int(y + rng.uniform(-size * 0.06, size * 0.06))))
        x += f.getlength(ch) * rng.uniform(0.93, 1.03)
    return x


def label(lines, rng, w=1024, h=512):
    """The cassette label: printed rules and a header, then whatever the explorer wrote."""
    img = paper(w, h, rng).convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h * 0.17], fill=(196, 40, 36, 255))
    d.text((w * 0.03, h * 0.085), "COMPACT VIDEO CASSETTE", font=font(SANS.format("Bold"), h * 0.075), fill=(250, 246, 236),
           anchor="lm")
    d.text((w * 0.97, h * 0.085), "TC-30  SP", font=font(SANS.format("Black"), h * 0.08), fill=(250, 246, 236), anchor="rm")
    for k in range(4):
        y = h * (0.42 + 0.17 * k)
        d.line([(w * 0.04, y), (w * 0.96, y)], fill=(150, 160, 190, 255), width=3)
    d.text((w * 0.04, h * 0.25), "TITLE", font=font(SANS.format("SemiBold"), h * 0.05), fill=(120, 120, 130))
    d.text((w * 0.72, h * 0.25), "DATE", font=font(SANS.format("SemiBold"), h * 0.05), fill=(120, 120, 130))
    for i, (text, x, size) in enumerate(lines):
        marker(img, text, w * x, h * (0.27 + 0.17 * i), h * size, rng)
    # handling: dirt at the edges, a coffee ring
    img = img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([w * 0.62, h * 0.5, w * 0.92, h * 1.1], outline=(140, 100, 60, 40), width=10)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def screen(w=512, h=384):
    """What the flip-out screen shows: a dark, grainy hallway, with the camcorder's playback overlay."""
    rng = random.Random(3)
    img = Image.new("RGB", (w, h), (10, 14, 16))
    d = ImageDraw.Draw(img)
    vx, vy = w * 0.52, h * 0.48  # a corridor in one-point perspective
    for k in range(9, 0, -1):
        f = k / 9
        x0, x1 = vx - w * 0.62 * f, vx + w * 0.62 * f
        y0, y1 = vy - h * 0.55 * f, vy + h * 0.6 * f
        g = int(14 + 34 * (1 - f))
        d.rectangle([x0, y0, x1, y1], fill=(g, g + 6, g + 4))
    d.rectangle([vx - w * 0.05, vy - h * 0.1, vx + w * 0.05, vy + h * 0.08], fill=(4, 5, 6))  # the far doorway
    d.rectangle([vx - w * 0.012, vy - h * 0.06, vx + w * 0.012, vy + h * 0.07], fill=(28, 30, 30))  # someone in it
    px = img.load()
    for _ in range(w * h // 3):
        x, y = rng.randrange(w), rng.randrange(h)
        c = px[x, y]
        n = rng.randint(-14, 14)
        px[x, y] = tuple(max(0, min(255, v + n)) for v in c)
    for y in range(0, h, 3):  # scanlines
        d.line([(0, y), (w, y)], fill=(0, 0, 0))
    ov = font(MONO, h * 0.075)
    d.text((w * 0.05, h * 0.06), "▶ PLAY", font=ov, fill=(235, 240, 240))
    d.text((w * 0.95, h * 0.06), "SP", font=ov, fill=(235, 240, 240), anchor="ra")
    d.text((w * 0.05, h * 0.86), "0:01:23", font=ov, fill=(235, 240, 240))
    d.text((w * 0.95, h * 0.86), "OCT 29 2003", font=ov, fill=(240, 200, 90), anchor="ra")
    return img


def printed(text, size, color=(220, 222, 226), weight="Bold", pad=0.25):
    """White-ish printing on a transparent background, for the body markings."""
    f = font(SANS.format(weight), size)
    w = int(f.getlength(text) + size * pad * 2)
    h = int(size * (1 + pad * 2))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((w / 2, h / 2), text, font=f, fill=color + (255,), anchor="mm")
    return img


def build(out):
    os.makedirs(out, exist_ok=True)
    rng = random.Random(29)
    label([("STAIRWELL B", 0.05, 0.13), ("10/29/03", 0.73, 0.1)], rng).save(os.path.join(out, "label_stairwell.png"))
    label([], rng).save(os.path.join(out, "label_blank.png"))
    screen().save(os.path.join(out, "screen_playback.png"))
    printed("DIGITAL VIDEO CAMERA", 64).save(os.path.join(out, "print_camcorder.png"))
    printed("40x OPTICAL ZOOM", 64, (200, 205, 212)).save(os.path.join(out, "print_zoom.png"))
    printed("REC", 64, (230, 60, 50), "Black").save(os.path.join(out, "print_rec.png"))
    printed("▶ PLAY", 64, (200, 205, 212), "Black").save(os.path.join(out, "print_play.png"))
    printed("TC-30", 64, (210, 210, 214), "Black").save(os.path.join(out, "print_tape.png"))
    print("textures written to", out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "textures"))
