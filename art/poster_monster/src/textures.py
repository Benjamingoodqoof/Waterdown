#!/usr/bin/env python3
"""Paints the poster monster's textures.

paper atlas (2048): water-damaged promo posters for the building's eco-tech company,
plus wet paper backs, papier-mache pulp, packing tape and a near-black void.
mask (1024): the cracked plastic droplet-mascot mask.

Writes color/roughness/normal maps at authoring size and 1024px copies for Roblox.
Usage: python3 textures.py OUT_DIR
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

FONT_DIR = "/usr/share/fonts/opentype/inter/"
SS = 2  # supersampling for the vector art


def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}Inter-{weight}.otf", max(6, int(size)))


# ---------------------------------------------------------------- noise / filters
def fbm(rng, h, w, base=4, octaves=5, gain=0.5, stretch=(1.0, 1.0)):
    """Fractal value noise in 0..1. stretch=(sy, sx) scales the cell count per axis."""
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        f = base * 2 ** o
        gy = max(2, int(f * stretch[0]))
        gx = max(2, int(f * stretch[1] * w / h))
        g = rng.random((gy, gx)).astype(np.float32)
        out += amp * np.asarray(Image.fromarray(g, "F").resize((w, h), Image.BICUBIC))
        tot += amp
        amp *= gain
    out -= out.min()
    return out / (out.max() + 1e-6)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _box1d(a, k, axis):
    a = np.moveaxis(a, axis, 0)
    p = np.concatenate([np.repeat(a[:1], k, 0), a, np.repeat(a[-1:], k, 0)], 0)
    c = np.cumsum(p, 0, dtype=np.float64)
    c = np.concatenate([np.zeros_like(c[:1]), c], 0)
    n = a.shape[0]
    return np.moveaxis(((c[2 * k + 1:2 * k + 1 + n] - c[:n]) / (2 * k + 1)).astype(np.float32), 0, axis)


def blur(a, r):
    """Approximate gaussian blur (three box passes) of a 2D or 3D float array."""
    k = int(round(r))
    if k < 1:
        return a.astype(np.float32)
    out = a.astype(np.float32)
    for _ in range(3):
        out = _box1d(_box1d(out, k, 0), k, 1)
    return out


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def to_arr(img):
    return np.asarray(img.convert("RGB"), np.float32) / 255.0


# ---------------------------------------------------------------- drawing helpers
def new_layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def vgrad(size, y0, y1, c0, c1, gamma=1.0):
    w, h = size
    t = np.clip((np.arange(h, dtype=np.float32) - y0) / max(1.0, y1 - y0), 0, 1) ** gamma
    col = np.array(c0, np.float32)[None] * (1 - t[:, None]) + np.array(c1, np.float32)[None] * t[:, None]
    arr = np.empty((h, w, 4), np.uint8)
    arr[..., :3] = col[:, None, :].astype(np.uint8)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def vgrad_multi(size, stops):
    w, h = size
    ys = np.linspace(0, 1, h)
    pos = [s[0] for s in stops]
    col = np.stack([np.interp(ys, pos, [s[1][c] for s in stops]) for c in range(3)], -1)
    arr = np.empty((h, w, 4), np.uint8)
    arr[..., :3] = col[:, None, :].astype(np.uint8)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def radial(size, cx, cy, r, color, alpha=255, power=2.0):
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (np.clip(1 - d, 0, 1) ** power * alpha).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def masked(layer, mask):
    """Multiply a layer's alpha by an L mask."""
    r, g, b, a = layer.split()
    a = Image.fromarray((np.asarray(a, np.float32) * np.asarray(mask, np.float32) / 255).astype(np.uint8))
    return Image.merge("RGBA", (r, g, b, a))


def place(img, tile, x, y):
    """Composite an RGBA tile at (x, y); the tile may hang off the canvas."""
    lay = new_layer(img.size)
    lay.paste(tile, (int(round(x)), int(round(y))))
    img.alpha_composite(lay)


def crescent(cx, cy, r, a0, a1, shift, n=40):
    """Glossy highlight: an arc band thinning toward both ends."""
    outer = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]
    sx, sy = shift
    inner = [(cx + sx + r * 0.9 * math.cos(math.radians(a)), cy + sy + r * 0.9 * math.sin(math.radians(a)))
             for a in np.linspace(a1, a0, n)]
    return outer + inner


def draw_bubble(img, cx, cy, r):
    lay = new_layer(img.size)
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 26), outline=(235, 250, 255, 175),
              width=max(2, int(r * 0.06)))
    d.ellipse([cx - r * 0.9, cy - r * 0.9, cx + r * 0.9, cy + r * 0.9], outline=(120, 220, 255, 70),
              width=max(1, int(r * 0.05)))
    d.polygon(crescent(cx, cy, r * 0.78, 195, 265, (r * 0.08, r * 0.08)), fill=(255, 255, 255, 190))
    d.ellipse([cx + r * 0.35, cy + r * 0.35, cx + r * 0.55, cy + r * 0.55], fill=(255, 255, 255, 110))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(max(1.0, r * 0.03))))


def sparkle(d, x, y, r, col=(255, 255, 255, 235)):
    pts = []
    for i in range(8):
        a = i * math.pi / 4
        rr = r if i % 2 == 0 else r * 0.22
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def clouds(img, rng, n, y_range, scale):
    w, h = img.size
    lay = new_layer(img.size)
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        cx, cy = rng.uniform(0, w), rng.uniform(*y_range) * h
        r = rng.uniform(0.6, 1.2) * scale * w
        for _ in range(7):
            ox, oy = rng.normal(0, r * 0.45), rng.normal(0, r * 0.15)
            rr = r * rng.uniform(0.35, 0.6)
            d.ellipse([cx + ox - rr, cy + oy - rr * 0.6, cx + ox + rr, cy + oy + rr * 0.6], fill=(255, 255, 255, 210))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(scale * w * 0.12)))


def hills(img, rng, y_frac, amp, c_top, c_bot, highlight=True):
    w, h = img.size
    xs = np.linspace(0, w, 60)
    ph, k = rng.uniform(0, 6.28), rng.uniform(1.2, 2.2)
    ys = y_frac * h - amp * h * np.sin(xs / w * np.pi * k + ph)
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(list(zip(xs, ys)) + [(w, h), (0, h)], fill=255)
    img.alpha_composite(masked(vgrad(img.size, ys.min(), h, c_top, c_bot), m))
    if highlight:
        hl = new_layer(img.size)
        ImageDraw.Draw(hl).line(list(zip(xs, ys + 0.007 * h)), fill=(220, 255, 170, 200), width=int(0.008 * h))
        img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(0.004 * h)))


def flare(img, x, y, r):
    w, h = img.size
    img.alpha_composite(radial(img.size, x, y, r, (255, 255, 235), 235, 1.8))
    lay = new_layer(img.size)
    d = ImageDraw.Draw(lay)
    for t, rr, a in ((0.35, 0.05, 60), (0.55, 0.025, 80), (0.8, 0.07, 40)):
        gx, gy = x + (w / 2 - x) * t * 2, y + (h / 2 - y) * t * 2
        d.ellipse([gx - rr * w, gy - rr * w, gx + rr * w, gy + rr * w], fill=(200, 240, 255, a))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))


def title(d, xy, s, size, weight="Black", fill=(255, 255, 255), stroke=(0, 70, 160), sw=0.08):
    d.text(xy, s, font=font(weight, size), fill=fill + (255,), anchor="mm",
           stroke_width=max(1, int(size * sw)) if stroke else 0, stroke_fill=(stroke + (255,)) if stroke else None)


def fine_print(d, x, y, lines, size, fill, anchor="mm", spacing=1.4, weight="Medium"):
    f = font(weight, size)
    for i, s in enumerate(lines):
        d.text((x, y + i * size * spacing), s, font=f, fill=fill, anchor=anchor)


# ---------------------------------------------------------------- the mascot
def droplet_pts(cx, cy, height, n=200, wratio=0.74, m=1.1):
    ts = np.linspace(0, 2 * np.pi, n, endpoint=False)
    xs = np.sin(ts) * np.abs(np.sin(ts / 2)) ** m
    xs = xs / np.abs(xs).max() * wratio
    ys = np.cos(ts)
    return [(cx + x * height / 2, cy - y * height / 2) for x, y in zip(xs, ys)]


def mascot_tile(H, eyes="happy", seed=0):
    """The company's droplet mascot, H px tall, on its own RGBA tile. Face center is at
    (tile.width / 2, tile.height / 2 + 0.17 * H)."""
    W, Ht = int(H * 0.8) + 8, int(H) + 8
    cx, cy = W / 2, Ht / 2
    size = (W, Ht)
    pts = droplet_pts(cx, cy, H)
    body = Image.new("L", size, 0)
    ImageDraw.Draw(body).polygon(pts, fill=255)
    tile = new_layer(size)
    tile.alpha_composite(masked(vgrad(size, cy - H / 2, cy + H / 2, (140, 228, 255), (8, 88, 200), 0.9), body))
    tile.alpha_composite(masked(radial(size, cx - 0.10 * H, cy + 0.12 * H, 0.42 * H, (215, 248, 255), 150, 1.6), body))
    tile.alpha_composite(masked(radial(size, cx + 0.25 * H, cy + 0.42 * H, 0.45 * H, (0, 40, 120), 110, 1.4), body))
    fx, fy = cx, cy + 0.17 * H
    hl = new_layer(size)
    hd = ImageDraw.Draw(hl)
    hd.polygon(crescent(fx, fy - 0.02 * H, 0.30 * H, 195, 265, (0.05 * H, 0.05 * H)), fill=(255, 255, 255, 215))
    hd.ellipse([cx - 0.05 * H, cy - 0.30 * H, cx + 0.005 * H, cy - 0.18 * H], fill=(255, 255, 255, 170))
    tile.alpha_composite(hl.filter(ImageFilter.GaussianBlur(max(1.0, H * 0.006))))
    d = ImageDraw.Draw(tile)
    d.line(pts + [pts[0]], fill=(0, 52, 135, 255), width=max(2, int(H * 0.018)), joint="curve")
    ck = new_layer(size)
    for s in (-1, 1):
        x, y = fx + s * 0.25 * H, fy + 0.05 * H
        ImageDraw.Draw(ck).ellipse([x - 0.055 * H, y - 0.03 * H, x + 0.055 * H, y + 0.03 * H], fill=(255, 130, 165, 120))
    tile.alpha_composite(ck.filter(ImageFilter.GaussianBlur(max(1.0, H * 0.012))))
    erx, ery = 0.05 * H, 0.078 * H
    rng = np.random.default_rng(seed)
    for s in (-1, 1):
        ex, ey = fx + s * 0.125 * H, fy - 0.045 * H
        d.ellipse([ex - erx, ey - ery, ex + erx, ey + ery], fill=(14, 18, 34, 255))
        if eyes == "happy":
            d.ellipse([ex + 0.05 * erx, ey - 0.70 * ery, ex + 0.62 * erx, ey - 0.25 * ery], fill=(255, 255, 255, 245))
            d.ellipse([ex - 0.55 * erx, ey + 0.25 * ery, ex - 0.25 * erx, ey + 0.45 * ery], fill=(255, 255, 255, 200))
        else:  # scribbled out with marker
            for _ in range(2):
                sc = [(ex + rng.uniform(-1.5, 1.5) * erx, ey + rng.uniform(-1.3, 1.3) * ery) for _ in range(26)]
                d.line(sc, fill=(8, 8, 10, 235), width=max(2, int(H * 0.016)), joint="curve")
    mx, my, mw, mh = fx, fy + 0.085 * H, 0.17 * H, 0.12 * H
    xs = np.linspace(-mw, mw, 30)
    mouth = [(mx + x, my - 0.035 * H * (x / mw) ** 2) for x in xs]
    mouth += [(mx + x, my - 0.035 * H * (x / mw) ** 2 + mh * (1 - (x / mw) ** 2) ** 0.85) for x in xs[::-1]]
    mm = Image.new("L", size, 0)
    ImageDraw.Draw(mm).polygon(mouth, fill=255)
    ml = new_layer(size)
    mld = ImageDraw.Draw(ml)
    mld.polygon(mouth, fill=(105, 14, 34, 255))
    mld.ellipse([mx - 0.09 * H, my + 0.06 * H, mx + 0.09 * H, my + 0.17 * H], fill=(240, 95, 125, 255))
    tile.alpha_composite(masked(ml, mm))
    d.line(mouth + [mouth[0]], fill=(55, 8, 22, 255), width=max(2, int(H * 0.012)), joint="curve")
    return tile


def place_mascot(img, H, x, y, eyes="happy", seed=0):
    """Mascot centered on its droplet at (x, y)."""
    t = mascot_tile(H, eyes, seed)
    place(img, t, x - t.width / 2, y - t.height / 2)


# ---------------------------------------------------------------- poster designs
def poster_tomorrow(W, H, rng):
    img = vgrad_multi((W, H), [(0, (18, 98, 200)), (0.55, (110, 200, 250)), (1, (170, 230, 255))])
    clouds(img, rng, 5, (0.25, 0.55), 0.18)
    flare(img, W * 0.82, H * 0.2, W * 0.35)
    hills(img, rng, 0.78, 0.04, (150, 215, 140), (90, 170, 110), highlight=False)
    hills(img, rng, 0.86, 0.05, (90, 200, 60), (25, 110, 40))
    for _ in range(9):
        draw_bubble(img, rng.uniform(0, W), rng.uniform(0.25, 0.8) * H, rng.uniform(0.02, 0.07) * W)
    place_mascot(img, H * 0.46, W / 2, H * 0.5)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.085), "A CLEANER", H * 0.065, "ExtraBold")
    title(d, (W / 2, H * 0.165), "TOMORROW", H * 0.092)
    fine_print(d, W / 2, H * 0.915, ["Clean water. Clean energy. A clean future", "for every family, starting today."],
               H * 0.02, (255, 255, 255, 235))
    return img


def poster_pure(W, H, rng):
    img = vgrad_multi((W, H), [(0, (0, 55, 150)), (0.5, (20, 140, 220)), (1, (0, 60, 150))])
    img.alpha_composite(radial((W, H), W * 0.5, H * 0.55, W * 0.75, (160, 240, 255), 200, 1.3))
    lay = new_layer((W, H))
    d = ImageDraw.Draw(lay)
    for i in range(5):
        rx, ry = W * (0.18 + 0.11 * i), H * (0.025 + 0.014 * i)
        d.ellipse([W / 2 - rx, H * 0.78 - ry, W / 2 + rx, H * 0.78 + ry], outline=(225, 250, 255, 170 - 25 * i), width=4)
    for _ in range(14):
        a = math.radians(rng.uniform(200, 340))
        L = rng.uniform(0.12, 0.3) * H
        x0, y0 = W / 2 + math.cos(a) * W * 0.18, H * 0.76
        x1, y1 = x0 + math.cos(a) * L * 0.6, y0 + math.sin(a) * L
        d.line([(x0, y0), (x1, y1)], fill=(220, 248, 255, 200), width=int(rng.uniform(6, 14)))
        r = rng.uniform(8, 18)
        d.ellipse([x1 - r, y1 - r * 1.3, x1 + r, y1 + r], fill=(235, 252, 255, 230))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))
    place_mascot(img, H * 0.36, W / 2, H * 0.47)
    d = ImageDraw.Draw(img)
    for _ in range(7):
        sparkle(d, rng.uniform(0.1, 0.9) * W, rng.uniform(0.25, 0.7) * H, rng.uniform(10, 26))
    for i, s in enumerate(["PURE.", "CLEAN.", "FOREVER."]):
        title(d, (W / 2, H * (0.07 + 0.075 * i)), s, H * 0.07, stroke=(0, 50, 130))
    fine_print(d, W / 2, H * 0.9, ["Every drop filtered seven times.", "Taste the future."], H * 0.022, (230, 250, 255, 235))
    return img


def poster_tower(W, H, rng):
    img = vgrad_multi((W, H), [(0, (25, 110, 210)), (0.7, (150, 215, 250)), (1, (190, 235, 255))])
    clouds(img, rng, 6, (0.12, 0.5), 0.16)
    bmask = Image.new("L", (W, H), 0)
    for sx, top in ((0.16, 0.46), (0.84, 0.42)):
        box = [W * (sx - 0.11), H * top, W * (sx + 0.11), H * 0.8]
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).rounded_rectangle(box, radius=int(W * 0.03), fill=255)
        ImageDraw.Draw(bmask).rounded_rectangle(box, radius=int(W * 0.03), fill=255)
        img.alpha_composite(masked(vgrad((W, H), H * top, H * 0.8, (120, 190, 235), (30, 90, 160)), m))
    x0, x1, top = W * 0.3, W * 0.7, H * 0.2
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).rounded_rectangle([x0, top, x1, H * 0.8], radius=int(W * 0.2), fill=255)
    ImageDraw.Draw(bmask).rounded_rectangle([x0, top, x1, H * 0.8], radius=int(W * 0.2), fill=255)
    img.alpha_composite(masked(vgrad((W, H), top, H * 0.8, (190, 235, 255), (35, 110, 190)), m))
    lay = new_layer((W, H))
    d = ImageDraw.Draw(lay)
    for x in np.arange(0, W, W * 0.035):
        d.line([(x, 0), (x, H)], fill=(235, 250, 255, 110), width=2)
    for y in np.arange(top, H * 0.8, H * 0.028):
        d.line([(0, y), (W, y)], fill=(235, 250, 255, 90), width=2)
    for _ in range(4):
        xx = x0 + (x1 - x0) * rng.uniform(-0.2, 0.8)
        d.polygon([(xx, H * 0.8), (xx + W * 0.05, H * 0.8), (xx + W * 0.16, top), (xx + W * 0.11, top)], fill=(255, 255, 255, 45))
    img.alpha_composite(masked(lay, bmask))
    hills(img, rng, 0.82, 0.015, (110, 210, 80), (40, 130, 50))
    lay = new_layer((W, H))
    d = ImageDraw.Draw(lay)
    d.ellipse([W * 0.22, H * 0.85, W * 0.62, H * 0.92], fill=(60, 170, 230, 255), outline=(220, 250, 255, 220), width=4)
    d.ellipse([W * 0.3, H * 0.865, W * 0.42, H * 0.878], fill=(255, 255, 255, 120))
    for _ in range(3):
        kx, ky = rng.uniform(0.28, 0.56) * W, rng.uniform(0.872, 0.9) * H
        d.ellipse([kx - 10, ky - 4, kx + 10, ky + 4], fill=(255, 120, 40, 230))
    img.alpha_composite(lay)
    place_mascot(img, H * 0.17, W * 0.82, H * 0.83)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.07), "THE FUTURE", H * 0.068, stroke=(0, 60, 150))
    title(d, (W / 2, H * 0.14), "IS CLEAR", H * 0.068, stroke=(0, 60, 150))
    d.rounded_rectangle([W * 0.1, H * 0.935, W * 0.9, H * 0.985], radius=int(H * 0.02), fill=(0, 90, 190, 255),
                        outline=(200, 240, 255, 255), width=3)
    d.text((W / 2, H * 0.96), "GRAND OPENING · SPRING 2001", font=font("ExtraBold", H * 0.026),
           fill=(255, 255, 255, 255), anchor="mm")
    return img


def poster_flow(W, H, rng):
    img = vgrad_multi((W, H), [(0, (235, 250, 255)), (1, (150, 225, 240))])
    tile = mascot_tile(H * 0.085)
    for r in range(10):
        y = H * (0.03 + r * 0.105)
        for c in range(-1, 8):
            x = c * W * 0.15 + (r % 2) * W * 0.075
            place(img, tile, x - tile.width / 2, y - tile.height / 2)
    R = W * 0.36
    lay = new_layer((W, H))
    ImageDraw.Draw(lay).ellipse([W / 2 - R, H * 0.48 - R, W / 2 + R, H * 0.48 + R], fill=(255, 255, 255, 235),
                                outline=(80, 200, 240, 255), width=8)
    img.alpha_composite(lay)
    draw_bubble(img, W / 2, H * 0.48, R)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.43), "JOIN", H * 0.075, fill=(0, 90, 190), stroke=None)
    title(d, (W / 2, H * 0.51), "THE FLOW", H * 0.075, fill=(0, 90, 190), stroke=None)
    d.text((W / 2, H * 0.575), "Everyone is welcome.", font=font("SemiBold", H * 0.024), fill=(30, 120, 200, 255), anchor="mm")
    return img


def poster_hydrated(W, H, rng):
    img = vgrad_multi((W, H), [(0, (60, 190, 240)), (1, (10, 110, 210))])
    for _ in range(12):
        draw_bubble(img, rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.02, 0.06) * W)
    Hm = H * 1.55
    t = mascot_tile(Hm, "scribbled", seed=5)
    place(img, t, W / 2 - t.width / 2, H * 0.55 - (t.height / 2 + 0.17 * Hm))
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.08), "STAY HAPPY!", H * 0.07, stroke=(0, 60, 150))
    title(d, (W / 2, H * 0.93), "STAY HYDRATED!", H * 0.062, stroke=(0, 60, 150))
    return img


def poster_green(W, H, rng):
    img = vgrad_multi((W, H), [(0, (215, 245, 160)), (0.6, (90, 190, 90)), (1, (30, 120, 60))])
    img.alpha_composite(radial((W, H), W * 0.5, H * 0.42, W * 0.6, (255, 255, 220), 140, 1.5))
    lay = new_layer((W, H))
    d = ImageDraw.Draw(lay)
    for _ in range(7):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.25, 0.4) * W
        bx, by = W * 0.5 + math.cos(a) * W * 0.18, H * 0.42 + math.sin(a) * W * 0.18
        tx, ty = bx + math.cos(a) * L, by + math.sin(a) * L
        nx, ny = -math.sin(a), math.cos(a)
        side1, side2 = [], []
        for t in np.linspace(0, 1, 20):
            px, py = bx + (tx - bx) * t, by + (ty - by) * t
            wd = math.sin(t * math.pi) * L * 0.28
            side1.append((px + nx * wd, py + ny * wd))
            side2.append((px - nx * wd, py - ny * wd))
        d.polygon(side1 + side2[::-1], fill=(60, 170, 50, 255), outline=(30, 110, 30, 255))
        d.line([(bx, by), (tx, ty)], fill=(190, 240, 140, 255), width=4)
    img.alpha_composite(lay)
    R, gx, gy = W * 0.22, W * 0.5, H * 0.42
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([gx - R, gy - R, gx + R, gy + R], fill=255)
    img.alpha_composite(masked(vgrad((W, H), gy - R, gy + R, (120, 210, 255), (10, 80, 180)), m))
    cont = new_layer((W, H))
    cd = ImageDraw.Draw(cont)
    for _ in range(6):
        cx, cy = gx + rng.uniform(-0.8, 0.8) * R, gy + rng.uniform(-0.8, 0.8) * R
        cd.polygon([(cx + math.cos(a) * R * rng.uniform(0.12, 0.3), cy + math.sin(a) * R * rng.uniform(0.12, 0.3))
                    for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], fill=(80, 190, 70, 255))
    img.alpha_composite(masked(cont.filter(ImageFilter.GaussianBlur(2)), m))
    hl = new_layer((W, H))
    ImageDraw.Draw(hl).polygon(crescent(gx, gy, R * 0.92, 190, 270, (R * 0.08, R * 0.08)), fill=(255, 255, 255, 190))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(3)))
    ImageDraw.Draw(img).ellipse([gx - R, gy - R, gx + R, gy + R], outline=(230, 255, 255, 220), width=5)
    place_mascot(img, H * 0.2, W * 0.22, H * 0.78)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.07), "GROWING GREEN", H * 0.06, stroke=(20, 90, 40))
    title(d, (W / 2, H * 0.135), "TOGETHER", H * 0.06, stroke=(20, 90, 40))
    fine_print(d, W * 0.66, H * 0.75, ["Every rooftop a garden.", "Every office a forest.", "Every family", "a little greener."],
               H * 0.022, (255, 255, 255, 235))
    return img


def header_band(img, H, h_frac, c0=(40, 170, 240), c1=(0, 95, 200)):
    W = img.size[0]
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rectangle([0, 0, W, H * h_frac], fill=255)
    img.alpha_composite(masked(vgrad(img.size, 0, H * h_frac, c0, c1), m))


def flyer_funday(W, H, rng):
    img = Image.new("RGBA", (W, H), (246, 248, 250, 255))
    header_band(img, H, 0.17)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.06), "FAMILY", H * 0.06, stroke=None)
    title(d, (W / 2, H * 0.125), "FUN DAY!", H * 0.075, fill=(255, 230, 80), stroke=(0, 60, 150), sw=0.05)
    for i, c in enumerate([(240, 60, 70), (255, 200, 40), (40, 190, 240), (90, 200, 80), (170, 90, 220)]):
        bx, by, r = W * (0.12 + 0.19 * i) + rng.uniform(-10, 10), H * (0.25 + 0.04 * (i % 2)), W * 0.07
        d.line([(bx, by + r * 1.2), (bx + rng.uniform(-20, 20), by + r * 4.2)], fill=(120, 120, 120, 255), width=2)
        d.ellipse([bx - r, by - r * 1.2, bx + r, by + r * 1.2], fill=c + (255,))
        d.ellipse([bx - r * 0.55, by - r * 0.85, bx - r * 0.15, by - r * 0.3], fill=(255, 255, 255, 170))
    place_mascot(img, H * 0.25, W / 2, H * 0.47)
    d = ImageDraw.Draw(img)
    y = H * 0.64
    for s, wt, sz, col in (("SATURDAY · JUNE 14", "ExtraBold", 0.034, (0, 80, 170)),
                           ("Atrium Lobby · 10 AM – 4 PM", "SemiBold", 0.026, (40, 40, 50)),
                           ("Bubble show • Water tasting • Face painting", "Medium", 0.021, (40, 40, 50)),
                           ("Bring the whole family!", "SemiBold", 0.024, (0, 120, 200))):
        d.text((W / 2, y), s, font=font(wt, H * sz), fill=col + (255,), anchor="mm")
        y += H * sz * 1.7
    ty0 = H * 0.86
    d.line([(0, ty0), (W, ty0)], fill=(150, 150, 150, 255), width=2)
    for i in range(9):
        if i:
            d.line([(W * i / 9, ty0), (W * i / 9, H)], fill=(170, 170, 170, 255), width=2)
        t = new_layer((int(H * 0.13), int(W / 9)))
        ImageDraw.Draw(t).text((t.width / 2, t.height / 2), "555-0142", font=font("SemiBold", H * 0.016),
                               fill=(30, 30, 40, 255), anchor="mm")
        t = t.rotate(90, expand=True)
        place(img, t, W * (i + 0.5) / 9 - t.width / 2, ty0 + (H - ty0) / 2 - t.height / 2)
    return img


def flyer_visitor(W, H, rng):
    img = Image.new("RGBA", (W, H), (242, 246, 248, 255))
    header_band(img, H, 0.15)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.05), "WELCOME", H * 0.045, "ExtraBold", stroke=None)
    title(d, (W / 2, H * 0.105), "VISITORS", H * 0.06, stroke=None)
    y = H * 0.22
    for name, lvl, col in (("ARRIVAL ATRIUM", "Level 1", (40, 170, 240)), ("GREENHOUSE", "Level 2", (90, 190, 70)),
                           ("THE HOTEL", "Levels 3–7", (240, 150, 40)), ("OFFICES", "Levels 8–12", (150, 150, 170)),
                           ("LOWER LEVEL", "Staff only", (60, 90, 140))):
        d.ellipse([W * 0.08, y - H * 0.018, W * 0.08 + H * 0.036, y + H * 0.018], fill=col + (255,))
        d.text((W * 0.08 + H * 0.05, y), name, font=font("ExtraBold", H * 0.028), fill=(30, 40, 60, 255), anchor="lm")
        d.text((W * 0.92, y), lvl, font=font("Medium", H * 0.022), fill=(90, 100, 120, 255), anchor="rm")
        d.line([(W * 0.08, y + H * 0.035), (W * 0.92, y + H * 0.035)], fill=(200, 210, 220, 255), width=2)
        y += H * 0.072
    mx0, my0, mx1, my1 = W * 0.08, H * 0.6, W * 0.92, H * 0.86
    d.rounded_rectangle([mx0, my0, mx1, my1], radius=12, outline=(120, 170, 210, 255), width=3, fill=(225, 240, 250, 255))
    for _ in range(8):
        x0, y0 = rng.uniform(mx0 + 10, mx1 - 120), rng.uniform(my0 + 10, my1 - 80)
        d.rectangle([x0, y0, x0 + rng.uniform(60, 160), y0 + rng.uniform(40, 90)], outline=(120, 170, 210, 255), width=3)
    hx, hy = rng.uniform(mx0 + 60, mx1 - 60), rng.uniform(my0 + 40, my1 - 40)
    d.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=(230, 40, 50, 255))
    d.text((hx + 18, hy), "YOU ARE HERE", font=font("ExtraBold", H * 0.017), fill=(200, 30, 40, 255), anchor="lm")
    place_mascot(img, H * 0.1, W * 0.86, H * 0.925)
    fine_print(d, W * 0.08, H * 0.905, ["Please keep this area tidy.", "Thank you for visiting!"], H * 0.02,
               (60, 70, 90, 255), anchor="lm")
    return img


def flyer_smile(W, H, rng):
    img = vgrad_multi((W, H), [(0, (210, 245, 255)), (1, (120, 210, 240))])
    lay = new_layer((W, H))
    d = ImageDraw.Draw(lay)
    cx, cy = W / 2, H * 0.5
    for i in range(16):
        a0 = i * 2 * math.pi / 16
        a1 = a0 + math.pi / 16
        d.polygon([(cx, cy), (cx + math.cos(a0) * H, cy + math.sin(a0) * H), (cx + math.cos(a1) * H, cy + math.sin(a1) * H)],
                  fill=(255, 255, 255, 70))
    img.alpha_composite(lay)
    for _ in range(10):
        draw_bubble(img, rng.uniform(0, W), rng.uniform(0.15, 0.85) * H, rng.uniform(0.02, 0.06) * W)
    place_mascot(img, H * 0.46, cx, cy)
    d = ImageDraw.Draw(img)
    title(d, (W / 2, H * 0.1), "SMILE!", H * 0.11, stroke=(0, 110, 200), sw=0.06)
    d.text((W / 2, H * 0.86), "Tomorrow is looking bright.", font=font("ExtraBold", H * 0.034), fill=(0, 80, 170, 255), anchor="mm")
    fine_print(d, W / 2, H * 0.915, ["Ask a team member about our", "Bright Family membership."], H * 0.019, (0, 90, 170, 220))
    return img


PAINTERS = {
    "tomorrow": poster_tomorrow, "pure": poster_pure, "tower": poster_tower, "flow": poster_flow,
    "hydrated": poster_hydrated, "green": poster_green, "funday": flyer_funday, "visitor": flyer_visitor,
    "smile": flyer_smile,
}


# ---------------------------------------------------------------- weathering
def drips(rng, h, w, n):
    """Dirty water that ran down the sheet: n wobbly streaks fading toward their ends."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for _ in range(n):
        x, y0 = rng.uniform(0, w), rng.uniform(-0.1, 0.6) * h
        L, wd, ph = rng.uniform(0.2, 0.7) * h, rng.uniform(2, 7), rng.uniform(0, 6)
        pts = [(x + 2.5 * math.sin(i * 0.7 + ph), y0 + L * i / 20) for i in range(21)]
        for i in range(20):
            d.line([pts[i], pts[i + 1]], fill=int(255 * (1 - i / 20) ** 0.7), width=max(1, int(wd * (1 - 0.5 * i / 20))))
    return blur(np.asarray(m, np.float32) / 255, 1.2)


def creases(rng, h, w, n):
    """Fold lines: returns (ridge, shadow) arrays."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    for _ in range(n):
        if rng.random() < 0.6:  # full fold across the sheet
            if rng.random() < 0.5:
                p0, p1 = (0, rng.uniform(0, h)), (w, rng.uniform(0, h))
            else:
                p0, p1 = (rng.uniform(0, w), 0), (rng.uniform(0, w), h)
        else:  # short crumple crease
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            a, L = rng.uniform(0, math.pi), rng.uniform(0.15, 0.4) * w
            p0, p1 = (x, y), (x + math.cos(a) * L, y + math.sin(a) * L)
        pts = [p0]
        for t in np.linspace(0.2, 0.8, 4):
            pts.append((p0[0] + (p1[0] - p0[0]) * t + rng.normal(0, 3), p0[1] + (p1[1] - p0[1]) * t + rng.normal(0, 3)))
        pts.append(p1)
        d.line(pts, fill=255, width=1)
    ridge = blur(np.asarray(m, np.float32) / 255, 1)
    shadow = np.roll(np.roll(ridge, 2, 0), 2, 1)
    return ridge / (ridge.max() + 1e-6), shadow / (shadow.max() + 1e-6)


def weather(img, rng, wet, n_creases=None):
    """Age a printed sheet. Returns (color, roughness, height)."""
    H, W, _ = img.shape
    img = img.copy()
    lum = img @ np.array([0.299, 0.587, 0.114], np.float32)
    k = 0.24 + 0.24 * wet
    img = img * (1 - k) + lum[..., None] * k
    paper = np.array([0.93, 0.90, 0.80], np.float32)
    img = img * 0.9 + paper * 0.1
    yel = fbm(rng, H, W, base=2, octaves=4)
    img *= 1 - (0.10 + 0.10 * wet) * yel[..., None] * np.array([0.0, 0.25, 0.9], np.float32)
    height = 0.6 * fbm(rng, H, W, base=12, octaves=4) + 0.3 * fbm(rng, H, W, base=40, octaves=2)
    rough = np.full((H, W), 0.40 - 0.16 * wet, np.float32)
    # water stains with tide lines
    ns = fbm(rng, H, W, base=3, octaves=6)
    for th in ([0.58, 0.68] if wet < 0.5 else [0.42, 0.52, 0.6, 0.68]):
        inside = smoothstep(th, th + 0.02, ns)
        ring = np.exp(-((ns - th) / 0.007) ** 2)
        img *= 1 - 0.10 * inside[..., None] * np.array([0.5, 0.75, 1.0], np.float32)
        img *= 1 - 0.32 * ring[..., None] * np.array([0.45, 0.65, 1.0], np.float32)
        height += 0.25 * ring
        rough += 0.10 * inside * (1 - wet)
    # ink running down a soaked sheet
    if wet > 0:
        streak = smoothstep(0.55, 0.8, fbm(rng, H, W, base=3, stretch=(1.0, 5.0))) * wet
        out = img.copy()
        for y in range(1, H):
            kk = (0.9 * streak[y])[:, None]
            out[y] = out[y - 1] * kk + img[y] * (1 - kk)
        img = out
    # mold and grime specks in clusters
    cluster = smoothstep(0.55, 0.85, fbm(rng, H, W, base=4))
    sp = (rng.random((H, W)) < (0.004 + 0.012 * wet) * cluster).astype(np.float32)
    sp = np.clip(blur(sp, 1) * 6, 0, 1)
    img = img * (1 - 0.75 * sp[..., None]) + np.array([0.05, 0.07, 0.04], np.float32) * 0.75 * sp[..., None]
    # fold creases: the ink cracks white along the ridge
    ridge, shadow = creases(rng, H, W, n_creases if n_creases is not None else int(2 + 5 * wet + rng.integers(0, 3)))
    img = img + (paper - img) * (0.45 * ridge)[..., None]
    img *= (1 - 0.18 * shadow)[..., None]
    height += 1.2 * ridge
    rough += 0.25 * ridge
    # paper fiber
    fiber = blur(rng.normal(0, 1, (H, W)).astype(np.float32), 0.6)
    img *= (1 + 0.035 * fiber)[..., None]
    img *= 1 - 0.22 * wet
    # grime from the flooded building: darker, brown-green, with dirty runs
    g = fbm(rng, H, W, base=3, octaves=5)
    img *= (0.78 - 0.14 * wet + 0.16 * g)[..., None] * np.array([0.98, 0.96, 0.88], np.float32)
    runs = drips(rng, H, W, int(rng.integers(3, 6) + 8 * wet))
    img *= 1 - (0.38 * runs)[..., None] * np.array([0.8, 0.9, 1.0], np.float32)
    rough -= 0.15 * runs
    rough += 0.08 * fbm(rng, H, W, base=8, octaves=3) - 0.04
    return np.clip(img, 0, 1), np.clip(rough, 0.05, 1), height


# ---------------------------------------------------------------- misc atlas regions
def paint_back(w, h, rng, poster):
    base = np.array([0.67, 0.66, 0.62], np.float32)
    p = to_arr(to_img(poster).resize((w, h)).transpose(Image.FLIP_LEFT_RIGHT).filter(ImageFilter.GaussianBlur(5)))
    ink = 1 - p.mean(2, keepdims=True)
    col = base * (1 - 0.28 * ink) + (p - p.mean(2, keepdims=True)) * 0.08
    return weather(col, rng, 0.8, n_creases=6)


def paint_pulp(w, h, rng):
    f1 = fbm(rng, h, w, base=5, stretch=(0.12, 1.0))
    f2 = fbm(rng, h, w, base=5, stretch=(1.0, 0.12))
    clumps = fbm(rng, h, w, base=3)
    v = 0.4 * f1 + 0.4 * f2 + 0.2 * clumps
    col = np.array([0.045, 0.05, 0.058], np.float32) * (0.55 + 0.9 * v)[..., None]
    # shredded poster flecks
    fl = (rng.random((h, w)) < 0.0035).astype(np.float32)
    fl = blur(fl, 1.2) > 0.05
    palette = np.array([[0.10, 0.30, 0.55], [0.12, 0.40, 0.48], [0.18, 0.36, 0.14], [0.42, 0.42, 0.40], [0.40, 0.10, 0.12]],
                       np.float32)
    idx = (fbm(rng, h, w, base=12, octaves=2) * 4.99).astype(int)
    col = np.where(fl[..., None], palette[idx] * 0.55, col)
    height = 0.6 * v + 0.4 * fl
    rough = np.clip(0.22 + 0.25 * clumps - 0.1 * f1, 0.08, 1)
    return col, rough, height


def paint_tape(w, h, rng):
    streak = fbm(rng, h, w, base=3, stretch=(1.0, 0.06))
    wrink = fbm(rng, h, w, base=4, stretch=(0.05, 1.0))
    col = np.array([0.50, 0.41, 0.25], np.float32) * (0.78 + 0.3 * streak - 0.14 * wrink)[..., None]
    col *= (0.75 + 0.25 * fbm(rng, h, w, base=4))[..., None]
    yy = np.abs(np.linspace(-1, 1, h))[:, None] * np.ones((1, w), np.float32)
    col *= (1 - 0.35 * smoothstep(0.82, 1.0, yy))[..., None]
    sp = blur((rng.random((h, w)) < 0.0006).astype(np.float32), 1) > 0.04
    col = np.where(sp[..., None], col * 0.45, col)
    height = 0.8 * wrink + 0.2 * streak
    rough = np.clip(0.16 + 0.2 * wrink + 0.3 * sp, 0.05, 1)
    return col, rough, height


def paint_void(w, h, rng):
    n = fbm(rng, h, w, base=4)
    col = np.array([0.004, 0.004, 0.005], np.float32) * (0.7 + 0.6 * n)[..., None]
    return col, np.full((h, w), 1.0, np.float32), 0.0 * n


# ---------------------------------------------------------------- normals
def height_to_normal(height, strength):
    gy, gx = np.gradient(height.astype(np.float32))
    n = np.stack([-gx * strength, gy * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def downscale_normal(nrm_img, size):
    a = to_arr(nrm_img.resize((size, size), Image.LANCZOS)) * 2 - 1
    a /= np.linalg.norm(a, axis=-1, keepdims=True) + 1e-6
    return to_img(a * 0.5 + 0.5)


# ---------------------------------------------------------------- atlas
def build_atlas(rng):
    S = C.ATLAS
    col = np.zeros((S, S, 3), np.float32)
    rough = np.full((S, S), 0.5, np.float32)
    height = np.zeros((S, S), np.float32)
    clean = {}
    for i, (design, wet) in enumerate(C.CELLS):
        x0, y0, x1, y1 = C.cell_rect(i)
        if design not in clean:
            big = PAINTERS[design](C.CELL_W * SS, C.CELL_H * SS, np.random.default_rng(100 + C.DESIGNS.index(design)))
            clean[design] = to_arr(big.resize((C.CELL_W, C.CELL_H), Image.LANCZOS))
        c, r, h = weather(clean[design], rng, 1.0 if wet else 0.0)
        c = c * (0.84 if not wet else 0.78)
        g = 2
        col[y0 - g:y1 + g, x0 - g:x1 + g] = np.pad(c, ((g, g), (g, g), (0, 0)), mode="edge")
        rough[y0 - g:y1 + g, x0 - g:x1 + g] = np.pad(r, g, mode="edge")
        height[y0 - g:y1 + g, x0 - g:x1 + g] = np.pad(h, g, mode="edge")
    for name, (x0, y0, x1, y1) in C.REGIONS.items():
        w, h = x1 - x0, y1 - y0
        if name == "back":
            c, r, hh = paint_back(w, h, rng, clean["tomorrow"])
        elif name == "pulp":
            c, r, hh = paint_pulp(w, h, rng)
        elif name == "tape":
            c, r, hh = paint_tape(w, h, rng)
        else:
            c, r, hh = paint_void(w, h, rng)
        col[y0:y1, x0:x1], rough[y0:y1, x0:x1], height[y0:y1, x0:x1] = c, r, hh
    return col, rough, height, clean


# ---------------------------------------------------------------- mask
def paint_mask(rng, S=1024):
    px_per_m = S / C.MASK_UV_SCALE

    def m2p(x, y):
        u, v = C.mask_uv(x, y)
        return u * S, (1 - v) * S

    outline = [m2p(*p) for p in C.mask_outline()]
    ins_img = Image.new("L", (S, S), 0)
    ImageDraw.Draw(ins_img).polygon(outline, fill=255)
    ins = np.asarray(ins_img, np.float32) / 255
    edge = np.clip(1 - blur(ins, 10) * 1.0, 0, 1) * ins  # 0 deep inside, rises toward the rim
    edge = np.clip(edge * 2.5, 0, 1)
    v = 1 - np.mgrid[0:S, 0:S][0] / S
    base = np.array([0.12, 0.40, 0.70], np.float32)
    faded = np.array([0.40, 0.55, 0.66], np.float32)
    col = base + (faded - base) * (0.6 * smoothstep(0.45, 1.0, v))[..., None]
    col *= (0.93 + 0.12 * fbm(rng, S, S, base=3))[..., None]
    rough = np.full((S, S), 0.2, np.float32)
    height = 0.05 * fbm(rng, S, S, base=40, octaves=2)  # orange-peel plastic
    img = to_img(col).convert("RGBA")

    # painted gloss highlight, half scratched away
    hl = new_layer((S, S))
    fx, fy = m2p(0.0, -0.03)
    R = 0.15 * px_per_m
    hd = ImageDraw.Draw(hl)
    hd.polygon(crescent(fx, fy, R, 196, 266, (R * 0.07, R * 0.07)), fill=(232, 246, 255, 235))
    tx, ty = m2p(-0.022, 0.16)
    hd.ellipse([tx - 0.012 * px_per_m, ty - 0.03 * px_per_m, tx + 0.012 * px_per_m, ty + 0.03 * px_per_m], fill=(232, 246, 255, 200))
    keep = (fbm(rng, S, S, base=14) > 0.38).astype(np.float32)
    a = np.asarray(hl.split()[3], np.float32) * blur(keep, 1)
    hl.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(1)))

    d = ImageDraw.Draw(img)
    ck = new_layer((S, S))
    for s in (-1, 1):
        x, y = m2p(s * 0.106, -0.072)
        ImageDraw.Draw(ck).ellipse([x - 0.026 * px_per_m, y - 0.014 * px_per_m, x + 0.026 * px_per_m, y + 0.014 * px_per_m],
                                   fill=(225, 135, 140, 45))
    img.alpha_composite(ck.filter(ImageFilter.GaussianBlur(6)))
    for k in range(2):
        d.polygon([m2p(*p) for p in C.eye_outline(k, 48, grow=0.006)], fill=(14, 16, 22, 255))
    grin = [m2p(*p) for p in C.grin_outline()]
    d.polygon(grin, fill=(88, 10, 22, 255))
    d.line(grin + [grin[0]], fill=(176, 26, 38, 255), width=int(0.0035 * px_per_m), joint="curve")

    # paint ran down from the grin
    drip = new_layer((S, S))
    dd = ImageDraw.Draw(drip)
    for _ in range(7):
        x = rng.uniform(-0.075, 0.075)
        f = max(0.0, 1 - (x / 0.1) ** 2)
        y0 = C.smile_y(x * C.SMILE_HW / 0.1) - 0.006 - 0.026 * f ** 0.9
        L, wd = rng.uniform(0.012, 0.055), rng.uniform(0.0022, 0.004)
        pts = [m2p(x + 0.0012 * math.sin(t * 9 + x * 50), y0 - L * t) for t in np.linspace(0, 1, 12)]
        dd.line(pts, fill=(105, 12, 24, 245), width=max(2, int(wd * px_per_m)), joint="curve")
        ex, ey = pts[-1]
        r = wd * px_per_m * 0.85
        dd.ellipse([ex - r, ey - r, ex + r, ey + r * 1.3], fill=(105, 12, 24, 245))
    img.alpha_composite(drip)

    # black tears from both eye holes
    tears = new_layer((S, S))
    td = ImageDraw.Draw(tears)
    for k in range(2):
        (cx, cy), (rx, ry), _ = C.EYES[k]
        for _ in range(3):
            x = cx + rng.uniform(-0.6, 0.6) * rx
            y = cy - ry * math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2)) * 0.9
            L, w0 = rng.uniform(0.04, 0.12), rng.uniform(0.003, 0.006)
            ph = rng.uniform(0, 6)
            for t in np.linspace(0, 1, 40):
                xx, yy = m2p(x + 0.003 * math.sin(t * 7 + ph), y - L * t)
                r = max(0.6, w0 * (1 - 0.8 * t) * px_per_m / 2)
                td.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(18, 14, 12, int(225 * (1 - 0.5 * t))))
    img.alpha_composite(tears.filter(ImageFilter.GaussianBlur(1.2)))
    tear_a = np.asarray(tears.split()[3], np.float32) / 255

    col = to_arr(img)
    # flaking paint near the rim and along the break
    crack, crack_end = C.crack_path()
    cr_img = Image.new("L", (S, S), 0)
    ImageDraw.Draw(cr_img).line([m2p(*p) for p in crack], fill=255, width=3)
    near_crack = blur(np.asarray(cr_img, np.float32) / 255, 10) * 8
    fl_n = fbm(rng, S, S, base=22, octaves=4)
    flake = (fl_n > 0.80 - 0.30 * np.clip(edge + near_crack, 0, 1)).astype(np.float32) * ins
    flake = blur(flake, 0.8)
    rim = np.clip(blur(flake, 2) - flake, 0, 1) * 3
    plastic = np.array([0.66, 0.65, 0.60], np.float32) * (0.85 + 0.3 * fbm(rng, S, S, base=30, octaves=2))[..., None]
    col = col * (1 - flake[..., None]) + plastic * flake[..., None]
    col *= (1 - 0.5 * np.clip(rim, 0, 1))[..., None]
    height += 0.6 * (1 - flake)
    rough = rough * (1 - flake) + 0.55 * flake
    # scuffs and scratches, mostly on the protruding middle
    sc = Image.new("L", (S, S), 0)
    sd = ImageDraw.Draw(sc)
    for _ in range(140):
        x, y = rng.normal(0, 0.06), rng.normal(0.0, 0.08)
        a, L = rng.uniform(0, math.pi), rng.uniform(0.003, 0.02)
        p0, p1 = m2p(x, y), m2p(x + math.cos(a) * L, y + math.sin(a) * L)
        sd.line([p0, p1], fill=int(rng.uniform(60, 200)), width=1)
    scr = blur(np.asarray(sc, np.float32) / 255, 0.6)
    col = col + (np.array([0.70, 0.78, 0.85], np.float32) - col) * (0.35 * scr)[..., None]
    dirt = fbm(rng, S, S, base=5, octaves=5)
    col *= (1 - 0.22 * smoothstep(0.45, 0.9, dirt))[..., None] * np.array([1.0, 0.97, 0.92], np.float32)
    rough += 0.15 * smoothstep(0.45, 0.9, dirt)
    height -= 0.5 * scr
    rough += 0.3 * scr
    # grime toward the rim and the bottom, wet streaks
    grime = np.clip(0.55 * edge + 0.35 * smoothstep(0.35, 0.0, v) * fbm(rng, S, S, base=6), 0, 1)
    col *= 1 - grime[..., None] * np.array([0.42, 0.48, 0.58], np.float32)
    film = fbm(rng, S, S, base=4, octaves=6)
    col *= (0.82 + 0.16 * film)[..., None] * np.array([0.97, 0.96, 0.92], np.float32)
    rough += 0.18 * smoothstep(0.4, 0.8, film)
    rough += 0.3 * grime
    streak = smoothstep(0.6, 0.9, fbm(rng, S, S, base=3, stretch=(1.0, 10.0))) * 0.12
    col = col + (np.array([0.8, 0.82, 0.8], np.float32) - col) * streak[..., None]
    rough = rough * (1 - 0.6 * tear_a) + 0.32 * tear_a
    # cracks: the main break plus hairlines
    ck_img = Image.new("L", (S, S), 0)
    kd = ImageDraw.Draw(ck_img)
    kd.line([m2p(*p) for p in crack], fill=255, width=3)
    for _ in range(5):  # branches off the break
        p = crack[rng.integers(0, len(crack) - 1)]
        pts, x, y, a = [m2p(*p)], p[0], p[1], rng.uniform(0, 2 * math.pi)
        for _ in range(int(rng.integers(3, 7))):
            a += rng.normal(0, 0.6)
            x, y = x + math.cos(a) * 0.006, y + math.sin(a) * 0.006
            pts.append(m2p(x, y))
        kd.line(pts, fill=200, width=1)
    for path in (
        [(0.072, 0.050), (0.068, 0.075), (0.074, 0.098), (0.061, 0.128), (0.064, 0.152), (0.045, 0.188)],
        [(0.090, -0.090), (0.104, -0.115), (0.099, -0.140), (0.112, -0.170), (0.108, -0.192)],
        [(-0.020, 0.232), (-0.012, 0.205), (-0.024, 0.182), (-0.018, 0.160)],
    ):
        kd.line([m2p(*p) for p in path], fill=230, width=2)
    ckr = np.asarray(ck_img, np.float32) / 255
    col *= (1 - 0.85 * ckr)[..., None]
    height -= 1.2 * ckr
    rough += 0.3 * ckr

    # fill outside the mask with the paint color so mips stay blue at the edge
    mean = (col * ins[..., None]).sum((0, 1)) / ins.sum()
    col = col * ins[..., None] + mean * (1 - ins[..., None])
    return np.clip(col, 0, 1), np.clip(rough, 0.05, 1), height


# ---------------------------------------------------------------- main
def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rbx = os.path.join(out_dir, "roblox")
    os.makedirs(rbx, exist_ok=True)
    rng = np.random.default_rng(7)

    col, rough, height, clean = build_atlas(rng)
    nrm = to_img(height_to_normal(height, 4.0))
    to_img(col).save(os.path.join(out_dir, "paper_color.png"))
    to_img(rough).save(os.path.join(out_dir, "paper_roughness.png"))
    nrm.save(os.path.join(out_dir, "paper_normal.png"))
    to_img(col).resize((1024, 1024), Image.LANCZOS).save(os.path.join(rbx, "paper_color.png"))
    to_img(rough).resize((1024, 1024), Image.LANCZOS).save(os.path.join(rbx, "paper_roughness.png"))
    downscale_normal(nrm, 1024).save(os.path.join(rbx, "paper_normal.png"))

    mcol, mrough, mheight = paint_mask(np.random.default_rng(11))
    mnrm = to_img(height_to_normal(mheight, 3.0))
    for d in (out_dir, rbx):
        to_img(mcol).save(os.path.join(d, "mask_color.png"))
        to_img(mrough).save(os.path.join(d, "mask_roughness.png"))
        mnrm.save(os.path.join(d, "mask_normal.png"))

    # clean poster art, handy for in-game decals
    sheet = Image.new("RGB", (C.CELL_W * 3, C.CELL_H * 3))
    for i, name in enumerate(C.DESIGNS):
        sheet.paste(to_img(clean[name]), ((i % 3) * C.CELL_W, (i // 3) * C.CELL_H))
    sheet.save(os.path.join(out_dir, "posters_clean_sheet.png"))
    print("textures written to", out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "textures"))
