#!/usr/bin/env python3
"""Paints the Stand-In's flat artwork: the dead screen (warm static, scanlines and NO SIGNAL),
the brand badge on the monitor's bezel, and the property sticker on its side.

Usage: python3 standin_textures.py OUT_DIR
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import standin_common as C  # noqa: E402

SANS = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"


def font(path, size):
    return ImageFont.truetype(path, int(size))


def screen(w=640, h=480):
    """The dead CRT: static tinted by the screen's warm glow, scanlines, a NO SIGNAL box, and the
    tube's dark corners."""
    rng = random.Random(7)
    dead, glow = C.PALETTE["dead_screen"], C.PALETTE["screen_glow"]
    img = Image.new("RGB", (w, h), dead)
    px = img.load()
    for y in range(h):
        band = 0.5 + 0.5 * rng.random() if rng.random() < 0.04 else 1.0  # rolling interference
        for x in range(w):
            n = rng.random() ** 2.2 * 0.75 * band
            px[x, y] = tuple(int(d + (g - d) * n) for d, g in zip(dead, glow))
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    d = ImageDraw.Draw(img)
    for y in range(0, h, 3):
        d.line([(0, y), (w, y)], fill=tuple(int(c * 0.55) for c in dead))
    bw, bh = w * 0.5, h * 0.17
    d.rectangle([w / 2 - bw / 2, h / 2 - bh / 2, w / 2 + bw / 2, h / 2 + bh / 2], fill=dead, outline=glow, width=4)
    d.text((w / 2, h / 2), "NO SIGNAL", font=font(MONO, h * 0.085), fill=glow, anchor="mm")
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).rounded_rectangle([w * 0.04, h * 0.05, w * 0.96, h * 0.95], radius=h * 0.2, fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(h * 0.08))
    return Image.composite(img, Image.new("RGB", (w, h), (4, 2, 1)), vig)


def badge():
    """The brand on the bezel: the Orange Court sun and name, printed in dark brown."""
    w, h = 640, 128
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = (110, 44, 12, 255)
    r = h * 0.36
    d.ellipse([h * 0.14, h / 2 - r, h * 0.14 + 2 * r, h / 2 + r], fill=c)
    for k, y in enumerate((0.58, 0.7, 0.82)):  # the sun's three bars
        hh = h * (0.035 + 0.012 * k)
        d.rectangle([0, h * y - hh / 2, h, h * y + hh / 2], fill=(0, 0, 0, 0))
    d.text((h * 1.05, h / 2), "ORANGE COURT", font=font(SANS.format("ExtraBold"), h * 0.42), fill=c, anchor="lm")
    return img


def sticker():
    """A property tag stuck on the side of the monitor, with a barcode and an asset number."""
    rng = random.Random(11)
    w, h = 512, 256
    img = Image.new("RGB", (w, h), (232, 228, 214))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h * 0.24], fill=(150, 56, 18))
    d.text((w / 2, h * 0.12), "PROPERTY OF ORANGE COURT", font=font(SANS.format("Bold"), h * 0.12), fill=(250, 240, 226),
           anchor="mm")
    x = w * 0.08
    while x < w * 0.92:
        bw = rng.choice((2, 3, 5))
        d.rectangle([x, h * 0.32, x + bw, h * 0.72], fill=(20, 18, 16))
        x += bw + rng.choice((2, 3, 4))
    d.text((w / 2, h * 0.84), "ASSET 2-0417  ·  DO NOT REMOVE", font=font(MONO, h * 0.085), fill=(40, 36, 30),
           anchor="mm")
    d.rectangle([2, 2, w - 3, h - 3], outline=(180, 170, 150), width=3)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(w * 0.86, h), (w, h * 0.55), (w, h)], fill=(120, 100, 70, 90))  # a peeling, dirty corner
    return img


def build(out):
    os.makedirs(out, exist_ok=True)
    screen().save(os.path.join(out, "screen_nosignal.png"))
    badge().save(os.path.join(out, "print_badge.png"))
    sticker().save(os.path.join(out, "sticker.png"))
    print("textures written to", out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "textures"))
