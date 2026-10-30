#!/usr/bin/env python3
"""Paints the Stand-in's textures: one atlas (satin orange fiberglass, the faded Orange Court
uniform, cream apron, wig, shoes, joints, badge) plus a separate badge photo the game can
swap for the copied player's picture, and the Orange Court logo.

Usage: python3 standin_textures.py OUT_DIR
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import standin_common as S  # noqa: E402
from textures import blur, downscale_normal, fbm, font, height_to_normal, smoothstep, to_arr, to_img  # noqa: E402

ORANGE = (232, 118, 44)
RUST = (178, 74, 28)


def rgb(c):
    return np.array(c, np.float32) / 255.0


def lines_layer(w, h, segments, width=1):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for seg in segments:
        d.line(seg, fill=255, width=width)
    return np.asarray(m, np.float32) / 255


# ---------------------------------------------------------------- materials
def paint_skin(rng, w, h):
    """Glossy orange fiberglass, like a shop mannequin: smooth, with faint scuffs and a few chips."""
    col = np.ones((h, w, 3), np.float32) * rgb((238, 128, 58))
    col *= (0.96 + 0.06 * fbm(rng, h, w, base=3))[..., None]
    height = 0.02 * fbm(rng, h, w, base=30, octaves=2)
    rough = 0.22 + 0.05 * fbm(rng, h, w, base=8)
    sc = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(sc)
    for _ in range(90):
        x, y, a, L = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, math.pi), rng.uniform(4, 18)
        d.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], fill=int(rng.uniform(40, 140)), width=1)
    scr = blur(np.asarray(sc, np.float32) / 255, 0.6)
    col = col + (rgb((250, 205, 165)) - col) * (0.25 * scr)[..., None]
    rough += 0.15 * scr
    height -= 0.2 * scr
    grime = smoothstep(0.6, 0.9, fbm(rng, h, w, base=5))
    col *= (1 - 0.1 * grime)[..., None]
    rough += 0.12 * grime
    chips = blur((fbm(rng, h, w, base=26, octaves=3) > 0.985).astype(np.float32), 0.8)
    col = col * (1 - chips[..., None]) + rgb((236, 226, 206)) * chips[..., None]
    height -= 0.4 * chips
    return col, np.clip(rough, 0.05, 1), height


def paint_plastic(rng, w, h, color, rough_v=0.28):
    col = np.ones((h, w, 3), np.float32) * rgb(color)
    col *= (0.92 + 0.12 * fbm(rng, h, w, base=4))[..., None]
    rough = np.full((h, w), rough_v, np.float32) + 0.1 * fbm(rng, h, w, base=10)
    height = 0.1 * fbm(rng, h, w, base=20, octaves=2)
    wear = smoothstep(0.6, 0.9, fbm(rng, h, w, base=6))
    col *= (1 - 0.18 * wear)[..., None]
    return col, np.clip(rough, 0.05, 1), height


def paint_fabric(rng, w, h, color, dust_top=0.0, seams_u=(), hem=False, placket=None, tear=None, stripe=None):
    """Woven uniform fabric: weave, fading, dust settled on top, stains, stitched seams."""
    col = np.ones((h, w, 3), np.float32) * rgb(color)
    wx = fbm(rng, h, w, base=64, octaves=2, stretch=(0.15, 1.0))
    wy = fbm(rng, h, w, base=64, octaves=2, stretch=(1.0, 0.15))
    weave = 0.5 * wx + 0.5 * wy
    col *= (0.9 + 0.16 * weave)[..., None]
    col *= (0.93 + 0.1 * fbm(rng, h, w, base=3))[..., None]
    height = 0.6 * weave
    rough = np.full((h, w), 0.86, np.float32)
    yy = np.linspace(1, 0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)  # 1 at the top
    fade = 0.05 * yy + 0.04 * fbm(rng, h, w, base=4)
    col = col + (rgb((235, 220, 200)) - col) * fade[..., None]
    if dust_top:
        dust = smoothstep(1 - dust_top, 1.0, yy) * (0.5 + 0.5 * fbm(rng, h, w, base=8))
        col = col + (rgb((200, 192, 182)) - col) * (0.55 * dust)[..., None]
    sn = fbm(rng, h, w, base=4, octaves=6)
    stains = smoothstep(0.7, 0.78, sn)
    ring = np.exp(-((sn - 0.7) / 0.006) ** 2)
    col *= (1 - 0.08 * stains)[..., None]
    col *= (1 - 0.1 * ring)[..., None]
    segs = []
    for u in seams_u:
        x = int(u * (w - 1))
        segs.append([(x, 0), (x, h)])
    if hem:
        segs += [[(0, h - 10), (w, h - 10)], [(0, 8), (w, 8)]]
    if placket is not None:
        x = int(placket * w)
        segs += [[(x - 14, 0), (x - 14, h)], [(x + 14, 0), (x + 14, h)]]
    if stripe is not None:
        y0, y1 = int(stripe[0] * h), int(stripe[1] * h)
        segs += [[(0, y0), (w, y0)], [(0, y1), (w, y1)]]
    if segs:
        st = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(st)
        for (x0, y0), (x1, y1) in segs:  # dashed stitching
            n = int(math.hypot(x1 - x0, y1 - y0) / 6)
            for k in range(0, n, 2):
                t0, t1 = k / n, (k + 1) / n
                d.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0), (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)],
                       fill=255, width=2)
        stitch = blur(np.asarray(st, np.float32) / 255, 0.6)
        seam = blur(lines_layer(w, h, [[s[0], s[1]] for s in segs], 3), 2)
        col *= (1 - 0.25 * seam)[..., None]
        col = col * (1 - 0.35 * stitch[..., None]) + rgb((90, 40, 18)) * 0.35 * stitch[..., None]
        height += 1.2 * stitch - 0.6 * seam
    if tear is not None:  # a small torn hole near the hem
        tx, ty = tear
        t = Image.new("L", (w, h), 0)
        pts = [(tx * w + math.cos(a) * rng.uniform(6, 16) * (1.6 if k % 2 else 1), ty * h + math.sin(a) * rng.uniform(5, 12))
               for k, a in enumerate(np.linspace(0, 2 * math.pi, 14, endpoint=False))]
        ImageDraw.Draw(t).polygon(pts, fill=255)
        hole = blur(np.asarray(t, np.float32) / 255, 1.0)
        col = col * (1 - hole[..., None]) + rgb((25, 12, 6)) * hole[..., None]
    return np.clip(col, 0, 1), np.clip(rough, 0.05, 1), height


HAIR = (62, 34, 20)
HAIR_LIGHT = (150, 92, 52)


def paint_hair(rng, w, h, columns=1, part=None, shade=1.0):
    """Dark brown hair strands running down the texture (v), roots at the top. With columns, each
    column is one lock: darker toward its edges, where it tucks under its neighbours, with a soft
    sheen down the middle. part: u of a center part, where the orange scalp shows."""
    strands = fbm(rng, h, w, base=128, octaves=2, stretch=(0.015, 1.0))
    clumps = fbm(rng, h, w, base=16, octaves=2, stretch=(0.06, 1.0))
    v = np.linspace(1, 0, h, dtype=np.float32)[:, None] * np.ones((1, w), np.float32)  # 1 at the roots
    x = (np.arange(w, dtype=np.float32)[None, :] * columns / w) % 1.0 * np.ones((h, 1), np.float32)
    across = np.cos((x - 0.5) * math.pi) ** 0.6 if columns > 1 else np.ones_like(x)  # 1 mid-lock, 0 at the edges
    col = rgb(HAIR) * (0.7 + 0.45 * strands + 0.2 * clumps)[..., None]
    sheen = across * np.exp(-((v - 0.68) / 0.12) ** 2) * (0.5 + 0.5 * strands)
    col = col + (rgb(HAIR_LIGHT) - col) * (0.45 * sheen)[..., None]
    col *= (0.72 + 0.28 * across)[..., None] * shade
    height = 0.9 * strands + 0.4 * clumps + 0.6 * across
    rough = 0.42 - 0.14 * sheen + 0.08 * strands
    if part is not None:  # the center part shows the orange head underneath
        line = np.zeros((h, w), np.float32)
        xp = int(part * w)
        line[: int(h * 0.6), xp - 2:xp + 3] = 1.0
        line = blur(line, 1.5)
        col = col * (1 - line[..., None]) + rgb((210, 110, 55)) * line[..., None]
        height -= line
    return np.clip(col, 0, 1), np.clip(rough, 0.05, 1), height


def logo(size):
    """The Orange Court mark: a flat orange sun cut by three bars, in Frutiger Metro style."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.42
    c = size / 2
    d.ellipse([c - r, c - r, c + r, c + r], fill=ORANGE + (255,))
    for k, y in enumerate((0.58, 0.7, 0.82)):
        hh = size * (0.035 + 0.012 * k)
        d.rectangle([0, size * y - hh / 2, size, size * y + hh / 2], fill=(0, 0, 0, 0))
    return img


def paint_pocket(rng, w, h):
    col, rough, height = paint_fabric(rng, w, h, (246, 212, 176), seams_u=(0.004, 0.996), hem=True)
    img = to_img(col).convert("RGBA")
    lg = logo(int(w * 0.5))
    img.alpha_composite(lg, (int(w * 0.25), int(h * 0.12)))
    d = ImageDraw.Draw(img)
    d.text((w / 2, h * 0.76), "orange court", font=font("SemiBold", h * 0.11), fill=RUST + (255,), anchor="mm")
    faded = to_arr(img)
    faded = faded + (rgb((240, 225, 205)) - faded) * 0.18
    return faded, rough, height


def paint_badge(rng, w, h):
    """White plastic name tag: orange header, a photo window, names crossed out one after another."""
    img = Image.new("RGBA", (w, h), (238, 234, 226, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h * 0.26], fill=ORANGE + (255,))
    lg = logo(int(h * 0.22))
    img.alpha_composite(lg, (int(w * 0.03), int(h * 0.02)))
    d.text((w * 0.2, h * 0.13), "ORANGE COURT", font=font("ExtraBold", h * 0.13), fill=(255, 255, 255, 255), anchor="lm")
    d.rectangle([w * 0.04, h * 0.33, w * 0.34, h * 0.93], fill=(70, 70, 74, 255))  # where the photo sits
    d.text((w * 0.38, h * 0.37), "HELLO, MY NAME IS", font=font("SemiBold", h * 0.07), fill=(120, 110, 100, 255),
           anchor="lm")
    names = ("Ashley", "Marcus", "Dev", "Jen")
    for k, name in enumerate(names):
        y = h * (0.5 + 0.11 * k)
        x = w * (0.4 + 0.03 * (k % 2))
        f = font("SemiBoldItalic" if k % 2 else "MediumItalic", h * 0.1)
        d.text((x, y), name, font=f, fill=(30, 40, 90, 255), anchor="lm")
        tw = f.getlength(name)
        d.line([(x - 4, y + rng.uniform(-3, 3)), (x + tw + 6, y + rng.uniform(-3, 3))], fill=(190, 30, 30, 255), width=3)
    col = to_arr(img)
    col *= (0.94 + 0.08 * fbm(rng, h, w, base=4))[..., None]
    scr = fbm(rng, h, w, base=40, octaves=2)
    rough = 0.25 + 0.2 * scr
    return col, rough, 0.1 * scr


def badge_photo(rng, w=256, h=320):
    """Default 'last copy' photo: a flash snapshot of a blocky avatar. The game can replace it."""
    img = Image.new("RGB", (w, h), (238, 236, 228))
    pic = Image.new("RGB", (w - 24, h - 70), (20, 52, 58))
    pd = ImageDraw.Draw(pic)
    pw, ph = pic.size
    pd.ellipse([pw * 0.55, -ph * 0.2, pw * 1.3, ph * 0.5], fill=(160, 80, 30))
    pd.rectangle([pw * 0.18, ph * 0.62, pw * 0.82, ph], fill=(40, 90, 200))
    pd.rectangle([pw * 0.28, ph * 0.18, pw * 0.72, ph * 0.62], fill=(245, 205, 120))
    pd.rectangle([pw * 0.26, ph * 0.14, pw * 0.74, ph * 0.26], fill=(70, 40, 20))
    for sx in (0.4, 0.6):
        pd.ellipse([pw * sx - 6, ph * 0.36, pw * sx + 6, ph * 0.42], fill=(20, 20, 20))
    pd.arc([pw * 0.4, ph * 0.42, pw * 0.6, ph * 0.54], 20, 160, fill=(20, 20, 20), width=4)
    pic = pic.filter(ImageFilter.GaussianBlur(1.6))
    a = to_arr(pic)
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
    flash = np.exp(-(((xx - pw * 0.5) / (pw * 0.45)) ** 2 + ((yy - ph * 0.4) / (ph * 0.45)) ** 2))
    a = a * (0.45 + 0.75 * flash)[..., None]
    a += rng.normal(0, 0.035, a.shape).astype(np.float32)
    pic = to_img(np.clip(a, 0, 1))
    pd = ImageDraw.Draw(pic)
    pd.text((pw - 8, ph - 8), "10 29 '03", font=font("Bold", 16), fill=(255, 140, 40), anchor="rd")
    img.paste(pic, (12, 12))
    return img


# ---------------------------------------------------------------- atlas
def build(out):
    os.makedirs(os.path.join(out, "roblox"), exist_ok=True)
    rng = np.random.default_rng(23)
    A = S.ATLAS
    col = np.zeros((A, A, 3), np.float32)
    rough = np.full((A, A), 0.5, np.float32)
    height = np.zeros((A, A), np.float32)
    painters = {
        "skin": lambda w, h: paint_skin(rng, w, h),
        "sole": lambda w, h: paint_plastic(rng, w, h, (34, 21, 14), 0.7),
        "shoe": lambda w, h: paint_plastic(rng, w, h, (74, 40, 24), 0.36),
        "metal": lambda w, h: paint_plastic(rng, w, h, (142, 140, 136), 0.35),
        "button": lambda w, h: paint_plastic(rng, w, h, (240, 228, 206), 0.3),
        "belt": lambda w, h: paint_fabric(rng, w, h, (246, 212, 176), stripe=(0.12, 0.88)),
        "skirt": lambda w, h: paint_fabric(rng, w, h, RUST, seams_u=(0.002, 0.5, 0.998), hem=True, tear=(0.62, 0.9)),
        "bodice": lambda w, h: paint_fabric(rng, w, h, RUST, dust_top=0.25, seams_u=(0.002, 0.5, 0.998), placket=0.75),
        "sleeve": lambda w, h: paint_fabric(rng, w, h, RUST, dust_top=0.3, stripe=(0.82, 0.9)),
        "collar": lambda w, h: paint_fabric(rng, w, h, (244, 238, 226), stripe=(0.08, 0.92)),
        "apron": lambda w, h: paint_fabric(rng, w, h, (246, 212, 176), hem=True),
        "pocket": lambda w, h: paint_pocket(rng, w, h),
        "hair": lambda w, h: paint_hair(rng, w, h, columns=4),
        "hair_under": lambda w, h: paint_hair(rng, w, h, shade=0.55),
        "scalp": lambda w, h: paint_hair(rng, w, h, part=0.75),
        "badge": lambda w, h: paint_badge(rng, w, h),
        "lining": lambda w, h: paint_plastic(rng, w, h, (92, 38, 16), 0.9),
    }
    for name, (x0, y0, x1, y1) in S.REGIONS.items():
        c, r, hh = painters[name](x1 - x0, y1 - y0)
        col[y0:y1, x0:x1], rough[y0:y1, x0:x1], height[y0:y1, x0:x1] = c, r, hh
    nrm = to_img(height_to_normal(height, 3.0))
    to_img(col).save(os.path.join(out, "standin_color.png"))
    to_img(rough).save(os.path.join(out, "standin_roughness.png"))
    nrm.save(os.path.join(out, "standin_normal.png"))
    to_img(col).resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, "roblox", "standin_color.png"))
    to_img(rough).resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, "roblox", "standin_roughness.png"))
    downscale_normal(nrm, 1024).save(os.path.join(out, "roblox", "standin_normal.png"))
    photo = badge_photo(rng)
    photo.save(os.path.join(out, "badge_photo.png"))
    photo.save(os.path.join(out, "roblox", "badge_photo.png"))
    logo(512).save(os.path.join(out, "orange_court_logo.png"))
    print("textures written to", out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "textures"))
