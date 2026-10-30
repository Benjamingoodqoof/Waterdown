#!/usr/bin/env python3
"""Paints the Receiver's textures, all 1024 px so Roblox takes them as they are:

- cord_*: coiled phone cord that tiles along the cord (4 coils per repeat), black on the left
  half and smoke grey on the right; the coil runs as a helix, so the ridges line up all round.
- props_*: the phone parts atlas (glossy black plastic, chrome, the out-of-order number plate,
  the finger wheel, plugs, copper and gold), with a metalness map.
- glass_*: the smoked glass shell, with cracks running out of the torn-out dial socket and a
  glossy highlight. Its alpha is the glass's opacity.
- water_*: the dirty water inside, with an oily rainbow film just under the surface.

Usage: python3 receiver_textures.py OUT_DIR
"""
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import receiver_common as C  # noqa: E402
from textures import blur, fbm, font, height_to_normal, smoothstep, to_img  # noqa: E402

N = 1024


def rgb(c):
    return np.array(c, np.float32) / 255.0


def periodic_noise(rng, h, w, freqs=(2, 3, 5, 8, 13), n=6):
    """Noise in 0..1 that tiles in both directions (a sum of whole-period waves)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((h, w), np.float32)
    for f in freqs:
        for _ in range(n):
            fx, fy = rng.integers(-f, f + 1), rng.integers(-f, f + 1)
            if fx == 0 and fy == 0:
                continue
            out += math.sqrt(1.0 / f) * np.sin(2 * math.pi * (fx * xx / w + fy * yy / h) + rng.uniform(0, 2 * math.pi))
    out -= out.min()
    return out / (out.max() + 1e-6)


def wrap_normal(height, strength):
    """Normal map (OpenGL, green up) from a height map that tiles."""
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    n = np.stack([-gx * strength, gy * strength, np.ones_like(height)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


# ---------------------------------------------------------------- cord
def paint_cord(rng):
    h, w = N, N // 2
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v, u = 1 - yy / h, xx / w
    phase = C.COILS_PER_TILE * v + u  # one coil further on for each turn around: a helix
    f = phase % 1.0
    wire = np.sqrt(np.clip(1 - (2 * f - 1) ** 2, 0, 1))  # each coil is a round wire
    noise = periodic_noise(rng, h, w)
    scuff = smoothstep(0.72, 0.9, periodic_noise(rng, h, w, freqs=(8, 13, 21)))
    cols, roughs, normals = [], [], []
    for name in C.CORD_VARIANTS:
        if name == "black":
            base, top, groove = rgb(C.PALETTE["cord"]), rgb(C.PALETTE["ridge"]), rgb((2, 3, 4))
        else:
            base, top, groove = rgb(C.PALETTE["smoke"]) * 0.45, rgb((120, 126, 134)), rgb((14, 15, 17))
        k = wire ** 6
        col = base + (top - base) * (0.55 * k)[..., None]
        col = col * (0.35 + 0.65 * wire)[..., None] + groove * (1 - wire)[..., None] * 0.6
        col *= (0.9 + 0.2 * noise)[..., None]
        col = col + (rgb((70, 66, 60)) - col) * (0.25 * scuff * (1 - wire))[..., None]  # grime in the grooves
        rough = 0.2 + 0.4 * (1 - wire) + 0.1 * noise + 0.15 * scuff
        cols.append(np.clip(col, 0, 1))
        roughs.append(np.clip(rough, 0.05, 1))
        normals.append(wrap_normal(wire * 6.0, 2.0))
    return np.concatenate(cols, 1), np.concatenate(roughs, 1), np.concatenate(normals, 1)


# ---------------------------------------------------------------- props atlas
def region_px(name):
    return C.PROPS[name]


def paint_props(rng):
    col = np.zeros((N, N, 3), np.float32)
    rough = np.full((N, N), 0.5, np.float32)
    metal = np.zeros((N, N), np.float32)
    height = np.zeros((N, N), np.float32)

    def put(name, c, r, m=0.0, hgt=None):
        x0, y0, x1, y1 = region_px(name)
        col[y0:y1, x0:x1] = c
        rough[y0:y1, x0:x1] = r
        metal[y0:y1, x0:x1] = m
        if hgt is not None:
            height[y0:y1, x0:x1] = hgt

    def size(name):
        x0, y0, x1, y1 = region_px(name)
        return x1 - x0, y1 - y0

    def scratches(w, h, n, length=(6, 40)):
        img = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(img)
        for _ in range(n):
            x, y, a, L = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, math.pi), rng.uniform(*length)
            d.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], fill=int(rng.uniform(40, 160)), width=1)
        return np.asarray(img, np.float32) / 255

    # glossy black plastic (phone base, prongs, handset)
    w, h = size("plastic")
    sc = scratches(w, h, 70)
    c = np.ones((h, w, 3), np.float32) * rgb((14, 15, 18)) * (0.9 + 0.2 * fbm(rng, h, w, base=3))[..., None]
    c = c + (rgb((90, 94, 100)) - c) * (0.35 * sc)[..., None]
    put("plastic", c, 0.14 + 0.25 * sc + 0.06 * fbm(rng, h, w, base=6), 0.0, -0.3 * sc)
    # chrome
    w, h = size("chrome")
    streak = fbm(rng, h, w, base=6, octaves=3, stretch=(0.1, 1.0))
    c = rgb(C.PALETTE["chrome"]) * (0.75 + 0.35 * streak)[..., None]
    put("chrome", c, 0.12 + 0.12 * fbm(rng, h, w, base=8), 1.0)
    # rubber
    w, h = size("rubber")
    put("rubber", np.ones((h, w, 3), np.float32) * rgb((24, 24, 26)) * (0.85 + 0.3 * fbm(rng, h, w, base=10))[..., None],
        0.75)
    # the empty socket where the dial was
    w, h = size("socket")
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot(xx / w - 0.5, yy / h - 0.5) * 2
    put("socket", np.ones((h, w, 3), np.float32) * rgb((6, 6, 7)) * (0.6 + 0.6 * rr)[..., None], 0.55)
    # copper wire
    w, h = size("copper")
    strands = fbm(rng, h, w, base=48, octaves=2, stretch=(1.0, 0.05))
    c = rgb(C.PALETTE["copper"]) * (0.7 + 0.5 * strands)[..., None]
    put("copper", c, 0.28 + 0.15 * strands, 1.0, strands)
    # gold contacts
    w, h = size("gold")
    put("gold", np.ones((h, w, 3), np.float32) * rgb((214, 168, 70)), 0.22, 1.0)
    # the finger wheel: smoked black glass
    w, h = size("wheel")
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rr = np.hypot(xx / w - 0.5, yy / h - 0.5) * 2
    c = np.ones((h, w, 3), np.float32) * rgb(C.PALETTE["glass"]) * (0.6 + 0.4 * np.exp(-((rr - 0.85) / 0.08) ** 2))[..., None]
    put("wheel", c, 0.05, 0.0)
    # the handset caps: black plastic with rings of holes
    w, h = size("cap")
    img = Image.new("RGB", (w, h), (16, 17, 20))
    d = ImageDraw.Draw(img)
    for ring, n in ((0, 1), (0.16, 6), (0.3, 12), (0.42, 18)):
        for k in range(n):
            a = 2 * math.pi * k / n
            x, y = w / 2 + math.cos(a) * ring * w, h / 2 + math.sin(a) * ring * h
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(2, 2, 3))
    put("cap", np.asarray(img, np.float32) / 255, 0.25)
    # plugs: clear plastic, with the gold contacts showing at the front
    w, h = size("plug")
    c = np.ones((h, w, 3), np.float32) * rgb((186, 196, 204)) * (0.85 + 0.2 * fbm(rng, h, w, base=5))[..., None]
    m = np.zeros((h, w), np.float32)
    for k in range(4):
        x = int(w * (0.3 + 0.13 * k))
        c[int(h * 0.04):int(h * 0.3), x - 3:x + 3] = rgb((214, 168, 70))
        m[int(h * 0.04):int(h * 0.3), x - 3:x + 3] = 1.0
    put("plug", c, 0.08, m)
    # hub: chrome with a crack through it
    w, h = size("hub")
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    pts, x, y = [], w * 0.42, h * 0.12
    for k in range(7):
        pts.append((x, y))
        x += rng.uniform(-14, 14) + (8 if k % 2 else -8)
        y += h * 0.12
    d.line(pts, fill=255, width=3)
    crack = blur(np.asarray(img, np.float32) / 255, 0.8)
    streak = fbm(rng, h, w, base=4, octaves=3)
    c = rgb(C.PALETTE["chrome"]) * (0.8 + 0.25 * streak)[..., None] * (1 - 0.85 * crack)[..., None]
    put("hub", c, 0.1 + 0.4 * crack, 1.0 - crack, -crack)
    # the number plate behind the wheel: off-white enamel with the digits out of order
    w, h = size("plate")
    img = Image.new("RGB", (w, h), (196, 200, 204))
    d = ImageDraw.Draw(img)
    R = C.DIAL["plate"]
    for clock, digit in C.DIAL_DIGITS:
        a = math.radians(clock)
        cx = w * (0.5 + math.sin(a) * C.DIAL["holes_at"] / (2 * R))
        cy = h * (0.5 - math.cos(a) * C.DIAL["holes_at"] / (2 * R))
        rr = w * C.DIAL["hole"] / (2 * R) * 0.95
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(236, 232, 222), outline=(120, 120, 124), width=2)
        d.text((cx, cy + 1), digit, font=font("Bold", rr * 1.25), fill=(24, 26, 30), anchor="mm")
    c = np.asarray(img, np.float32) / 255
    c *= (0.85 + 0.2 * fbm(rng, h, w, base=4))[..., None]
    put("plate", c, 0.3, 0.0)
    nrm = height_to_normal(height, 2.0)
    return col, rough, metal, nrm


# ---------------------------------------------------------------- glass shell
def crack_lines(rng, d, cx, cy, rx, ry, n, w, h):
    for k in range(n):
        a = 2 * math.pi * (k + rng.uniform(-0.3, 0.3)) / n
        x, y = cx + math.cos(a) * rx, cy + math.sin(a) * ry
        length = rng.uniform(0.6, 1.4) * max(rx, ry)
        steps = 6
        pts = [(x, y)]
        for s in range(steps):
            a += rng.uniform(-0.35, 0.35)
            x += math.cos(a) * length / steps
            y += math.sin(a) * length / steps
            pts.append((x, y))
            if rng.random() < 0.35:  # a branch
                b = a + rng.choice([-1, 1]) * rng.uniform(0.5, 1.0)
                bl = length * rng.uniform(0.15, 0.3)
                d.line([(x, y), (x + math.cos(b) * bl, y + math.sin(b) * bl)], fill=200, width=2)
        d.line(pts, fill=255, width=3)
    # a ring of chipped glass around the rim
    d.ellipse([cx - rx * 1.06, cy - ry * 1.06, cx + rx * 1.06, cy + ry * 1.06], outline=170, width=3)


def paint_glass(rng):
    u0, v0 = 0.5, C.SOCKET["z"] / 0.24
    cx, cy = u0 * N, (1 - v0) * N
    rx = C.SOCKET["r"] / 0.44 * N
    ry = C.SOCKET["r"] * math.cos(math.radians(30)) / 0.24 * N
    cr = Image.new("L", (N, N), 0)
    crack_lines(rng, ImageDraw.Draw(cr), cx, cy, rx, ry, 9, N, N)
    crack = blur(np.asarray(cr, np.float32) / 255, 1.0)
    # the glossy highlight across the upper left, and two screw rings
    hl = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(hl)
    d.polygon([(N * 0.12, N * 0.06), (N * 0.3, N * 0.06), (N * 0.16, N * 0.4), (N * 0.08, N * 0.4)], fill=255)
    for x, y in ((0.18, 0.62), (0.84, 0.66), (0.8, 0.22)):
        d.ellipse([N * x - 9, N * y - 9, N * x + 9, N * y + 9], outline=150, width=3)
    hl = hl.filter(ImageFilter.GaussianBlur(6))
    high = np.asarray(hl, np.float32) / 255
    smoke = fbm(rng, N, N, base=3)
    col = rgb((74, 78, 86)) * (0.8 + 0.4 * smoke)[..., None]  # the sheet's smoked glass, as seen with light behind it
    col = col + (rgb((215, 222, 230)) - col) * np.clip(0.8 * crack + 0.75 * high, 0, 1)[..., None]
    alpha = np.clip(0.42 + 0.5 * crack + 0.4 * high, 0, 1)
    rough = np.clip(0.04 + 0.4 * crack, 0, 1)
    rgba = np.concatenate([np.clip(col, 0, 1), alpha[..., None]], -1)
    return rgba, rough, height_to_normal(-crack, 3.0)


# ---------------------------------------------------------------- water
def paint_water(rng):
    col = np.ones((N, N, 3), np.float32) * rgb(C.PALETTE["water"])
    murk = fbm(rng, N, N, base=3)
    col = col * (0.8 + 0.6 * murk)[..., None] + rgb((40, 46, 20)) * (0.35 + 0.65 * smoothstep(0.4, 0.9, murk))[..., None]
    specks = (fbm(rng, N, N, base=90, octaves=1) > 0.93).astype(np.float32)
    col = col + rgb((70, 64, 50)) * (0.5 * blur(specks, 0.8))[..., None]
    # an oily rainbow film just under the surface (the water stops at v = C.SHELL_H * 0.71 / 0.24)
    v = 1 - np.arange(N, dtype=np.float32)[:, None] / N
    top = C.SHELL_H * 0.71 / 0.24
    band = np.exp(-((v - (top - 0.012)) / 0.008) ** 2) * np.ones((1, N), np.float32)
    hue = np.linspace(0, 1, N, dtype=np.float32)[None, :] * 3 + 0.15 * fbm(rng, N, N, base=4)
    rainbow = np.stack([0.5 + 0.5 * np.cos(2 * math.pi * (hue + k / 3)) for k in range(3)], -1)
    col = col + (rainbow * 0.8 - col) * (0.85 * band)[..., None]
    rough = np.clip(0.06 + 0.1 * murk, 0, 1)
    img = to_img(np.clip(col, 0, 1)).convert("RGB")
    d = ImageDraw.Draw(img)
    # the bubbles use the corner square, the leaf the one next to it
    d.rectangle([N - 64, N - 64, N, N], fill=(150, 156, 160))
    d.rectangle([N - 128, N - 64, N - 64, N], fill=(60, 120, 50))
    d.line([(N - 128, N - 32), (N - 64, N - 32)], fill=(120, 170, 80), width=4)
    return np.asarray(img, np.float32) / 255, rough


def save_rgb(a, path):
    to_img(np.clip(a, 0, 1)).save(path)


def build(out):
    rbx = os.path.join(out, "roblox")
    os.makedirs(rbx, exist_ok=True)
    rng = np.random.default_rng(41)
    c, r, n = paint_cord(rng)
    save_rgb(c, os.path.join(out, "cord_color.png"))
    save_rgb(r, os.path.join(out, "cord_roughness.png"))
    save_rgb(n, os.path.join(out, "cord_normal.png"))
    c, r, m, n = paint_props(rng)
    save_rgb(c, os.path.join(out, "props_color.png"))
    save_rgb(r, os.path.join(out, "props_roughness.png"))
    save_rgb(m, os.path.join(out, "props_metalness.png"))
    save_rgb(n, os.path.join(out, "props_normal.png"))
    rgba, r, n = paint_glass(rng)
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(out, "glass_color.png"))
    save_rgb(r, os.path.join(out, "glass_roughness.png"))
    save_rgb(n, os.path.join(out, "glass_normal.png"))
    c, r = paint_water(rng)
    save_rgb(c, os.path.join(out, "water_color.png"))
    save_rgb(r, os.path.join(out, "water_roughness.png"))
    for f in os.listdir(out):  # all 1024 already, so Roblox gets the same files
        if f.endswith(".png"):
            shutil.copy(os.path.join(out, f), os.path.join(rbx, f))
    print("textures written to", out)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "textures"))
