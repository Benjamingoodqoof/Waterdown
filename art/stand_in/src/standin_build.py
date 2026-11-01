#!/usr/bin/env python3
"""Builds the Stand-In, the floor-2 monster, from his monster sheet: a very tall, thin man in
a long orange suit, with a chunky 90s CRT monitor where his head should be. The screen shows
static and NO SIGNAL (a separate part, so the game can put a copied player's face on it).
A thick cable comes up out of his collar instead of a neck, and another hangs down his back.

Body, suit and cables are fitted meshes on a custom rig; every part's materials are baked into
SurfaceAppearance maps. Saves a .blend.

Usage: python3 standin_build.py OUT.blend
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "props", "src")))
import standin_common as C  # noqa: E402
import props_lib as L  # noqa: E402
from standin_common import CABLE, J, MONITOR, SIDES, V  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
L.TEX = TEX  # the props helpers load images from here
TAU = 2 * math.pi


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def g(t):
    return math.exp(-t * t)


def table(rows, x):
    x = min(rows[-1][0], max(rows[0][0], x))
    for r0, r1 in zip(rows, rows[1:]):
        if x <= r1[0]:
            k = (x - r0[0]) / (r1[0] - r0[0])
            return tuple(lerp(a, b, k) for a, b in zip(r0[1:], r1[1:]))
    return rows[-1][1:]


def lin(c):
    """sRGB 0..255 to linear 0..1, for material colors."""
    return tuple(((v / 255) ** 2.2) for v in c)


# ================================================================ mesh builder with weights
class MB:
    def __init__(self, name):
        self.name = name
        self.co, self.w, self.faces, self.mats, self.slots = [], [], [], [], []

    def vert(self, co, weights):
        self.co.append(Vector(co))
        self.w.append(weights(Vector(co)) if callable(weights) else weights)
        return len(self.co) - 1

    def face(self, ids, want, mat):
        if want is not None:
            a, b, c = (self.co[i] for i in ids[:3])
            if (b - a).cross(c - a).dot(want) < 0:
                ids = ids[::-1]
        if mat not in self.slots:
            self.slots.append(mat)
        self.faces.append(ids)
        self.mats.append(self.slots.index(mat))

    def grid(self, rows, mat, outward, wrap=False, flip=False):
        """Quads between rows of vertex ids; outward(point) is the side they face."""
        for a, b in zip(rows, rows[1:]):
            n = len(a) if wrap else len(a) - 1
            for j in range(n):
                q = [a[j], a[(j + 1) % len(a)], b[(j + 1) % len(b)], b[j]]
                c = sum((self.co[i] for i in q), Vector()) / 4
                want = outward(c)
                self.face(q, -want if flip else want, mat)

    def fan(self, ring, tip, weights, want, mat, wrap=True):
        t = self.vert(tip, weights)
        n = len(ring) if wrap else len(ring) - 1
        for j in range(n):
            self.face([ring[j], ring[(j + 1) % len(ring)], t], want, mat)

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(c) for c in self.co], [], self.faces)
        for m in self.slots:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.mats):
            poly.material_index = mi
        me.validate()
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(40))
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def rigid(bone):
    return {bone: 1.0}


def blend(a, b, k):
    if k <= 0.0:
        return {a: 1.0}
    if k >= 1.0:
        return {b: 1.0}
    return {a: 1.0 - k, b: k}


# ================================================================ materials (baked later)
M = {}


def materials():
    M["suit"] = L.plastic("Suit", lin(C.PALETTE["suit"]), 0.82, scuff=0.06, texture="weave", tex_scale=420,
                          tex_strength=0.12)
    M["lining"] = L.plastic("Lining", lin(C.PALETTE["suit_shade"]), 0.6, scuff=0.04)
    M["button"] = L.plastic("Button", lin(C.PALETTE["tie"]), 0.3, scuff=0.05)
    M["shirt"] = L.plastic("Shirt", lin(C.PALETTE["shirt"]), 0.75, scuff=0.04, texture="weave", tex_scale=900,
                           tex_strength=0.06)
    M["tie"] = L.plastic("Tie", lin(C.PALETTE["tie"]), 0.45, scuff=0.03, texture="ridges", tex_scale=500, tex_strength=0.05)
    M["collar_in"] = L.plastic("CollarInside", (0.004, 0.003, 0.002), 0.9, scuff=0.0)
    M["skin"] = L.plastic("Skin", lin(C.PALETTE["hands"]), 0.5, scuff=0.05, grain=0.03)
    M["leather"] = L.plastic("Leather", lin((70, 26, 6)), 0.32, scuff=0.12, grain=0.04)
    M["sole"] = L.plastic("Sole", (0.01, 0.008, 0.006), 0.7, scuff=0.04)
    M["case"] = L.plastic("MonitorCase", lin(C.PALETTE["monitor"]), 0.42, scuff=0.14, grain=0.03)
    M["case_dark"] = L.plastic("MonitorDark", lin((150, 70, 34)), 0.5, scuff=0.08)
    M["recess"] = L.plastic("ScreenSurround", lin((40, 18, 8)), 0.55, scuff=0.04)
    M["rubber"] = L.plastic("CableRubber", (0.008, 0.008, 0.009), 0.55, scuff=0.06, grain=0.03)
    M["vga"] = L.plastic("VgaBlue", lin((40, 76, 170)), 0.4, scuff=0.06)
    M["metal"] = L.plastic("Metal", (0.6, 0.6, 0.62), 0.25, metal=1.0, scuff=0.05)


# ================================================================ the suit coat
COAT = [  # z, center y, half width, half depth (outside of the cloth)
    (0.6, 0.025, 0.215, 0.165), (0.8, 0.025, 0.2, 0.152), (1.0, 0.025, 0.185, 0.142), (1.2, 0.025, 0.172, 0.132),
    (1.36, 0.025, 0.16, 0.12), (1.5, 0.022, 0.15, 0.11), (1.62, 0.02, 0.146, 0.104), (1.8, 0.016, 0.163, 0.11),
    (1.95, 0.012, 0.183, 0.116), (2.06, 0.012, 0.21, 0.114), (2.13, 0.015, 0.245, 0.105), (2.175, 0.018, 0.24, 0.09),
]
NECK = (V(0, -0.015, 2.252), 0.078)  # the neck hole: centre and radius
WAIST_BUTTON = 1.5


def opening(z):
    """Half the angle (degrees) the coat is open at the front: a V up to the collar above the
    waist button, closed round the buttons, and parting below them over the trousers."""
    if z >= WAIST_BUTTON:
        return 36 * smooth(WAIST_BUTTON, 2.2, z) ** 0.8
    if z >= 1.32:
        return 0.0
    return 24 * smooth(1.32, 0.6, z)


def coat_at(theta, z, off=0.0):
    cy, rx, ry = table(COAT, z)
    a = math.radians(theta)
    drape = 0.005 * math.sin(7 * a + 2 * z) * smooth(1.4, 0.7, z)  # soft folds in the skirt of the coat
    return V((rx + off + drape) * math.cos(a), cy + (ry + off + drape) * math.sin(a), z)


def yoke_at(theta, f, off=0.0):
    """Over the shoulders, from the top of the coat (f = 0) in to the neck hole (f = 1)."""
    a = math.radians(theta)
    p0 = coat_at(theta, 2.175, off)
    c, r = NECK
    p1 = V(c.x + (r + off) * math.cos(a), c.y + (r + off) * math.sin(a), c.z)
    p = p0.lerp(p1, f)
    p.z += 0.03 * math.sin(math.pi * f) * (1 - abs(math.sin(a)) * 0.5)  # the rounded shoulder
    return p


def coat_weights(p):
    k = smooth(1.5, 1.72, p.z)
    w = {"LowerTorso": 1 - k, "UpperTorso": k} if 0 < k < 1 else ({"UpperTorso": 1.0} if k >= 1 else {"LowerTorso": 1.0})
    legs = 0.55 * smooth(1.36, 0.7, p.z)  # the skirt of the coat follows the thighs a little
    if legs > 0:
        left = legs * min(1.0, max(0.0, (p.x + 0.05) / 0.1))
        w = {b: v * (1 - legs) for b, v in w.items()}
        if left > 0:
            w["LeftUpperLeg"] = left
        if legs - left > 0:
            w["RightUpperLeg"] = legs - left
    arm = 0.6 * smooth(0.15, 0.23, abs(p.x)) * smooth(1.95, 2.12, p.z)  # the shoulders follow the arms
    if arm > 0:
        w = {b: v * (1 - arm) for b, v in w.items()}
        w["LeftUpperArm" if p.x > 0 else "RightUpperArm"] = arm
    return w


def build_coat(mb):
    zs = [0.6 + (2.175 - 0.6) * k / 30 for k in range(31)]
    nu = 48
    outer, inner = [], []
    for z in zs:
        gz = opening(z)
        ths = [(-90 + gz) + (360 - 2 * gz) * u / nu for u in range(nu + 1)]
        outer.append([mb.vert(coat_at(t, z), coat_weights) for t in ths])
        inner.append([mb.vert(coat_at(t, z, -0.007), coat_weights) for t in ths])
    gz = opening(2.2)
    for f in [k / 6 for k in range(1, 7)]:
        ths = [(-90 + gz) + (360 - 2 * gz) * u / nu for u in range(nu + 1)]
        outer.append([mb.vert(yoke_at(t, f), coat_weights) for t in ths])
        inner.append([mb.vert(yoke_at(t, f, -0.007), coat_weights) for t in ths])

    def axis_out(c):
        return V(c.x, c.y - 0.02, 0) if c.z < 2.17 else V(c.x, c.y, 0.6)

    mb.grid(outer, M["suit"], axis_out)
    mb.grid(inner, M["lining"], axis_out, flip=True)
    for i in range(len(outer) - 1):  # front edges and hem: the cloth's thickness
        for j in (0, nu):
            q = [outer[i][j], outer[i + 1][j], inner[i + 1][j], inner[i][j]]
            mb.face(q, V(1 if j == 0 else -1, -1, 0), M["suit"])
    for j in range(nu):
        mb.face([outer[0][j], outer[0][j + 1], inner[0][j + 1], inner[0][j]], V(0, 0, -1), M["lining"])
    # lapels: folded back along the V, notched near the top
    lap_w = [(WAIST_BUTTON, 0.012), (1.62, 0.03), (1.85, 0.055), (2.04, 0.068), (2.085, 0.07), (2.1, 0.03),
             (2.125, 0.05), (2.2, 0.045)]
    for s in (1, -1):
        rows = []
        for k in range(23):
            z = lerp(WAIST_BUTTON + 0.002, 2.2, k / 22)
            gz = opening(z)
            cy, rx, ry = table(COAT, min(z, 2.175))
            r = (rx + ry) / 2
            w = table(lap_w, z)[0]
            th0 = -90 + s * gz
            row = []
            for u in range(4):
                th = th0 + s * math.degrees(w / r) * u / 3
                p = coat_at(th, min(z, 2.175), 0.004 + 0.002 * u / 3) if z <= 2.175 else yoke_at(th, 0.0, 0.004)
                if z > 2.175:
                    p.z = z
                row.append(mb.vert(p, coat_weights))
            rows.append(row)
        mb.grid(rows, M["suit"], lambda c: V(c.x, c.y - 0.05, 0))
    # the coat's collar, turned down round the back of the neck
    rows = []
    c, r = NECK
    for f, (dr, dz) in enumerate(((0.002, 0.035), (0.03, 0.02), (0.052, -0.02))):
        row = []
        for u in range(41):
            th = math.radians((-90 + 30) + 300 * u / 40)
            row.append(mb.vert(V(c.x + (r + dr) * math.cos(th), c.y + (r + dr) * math.sin(th), c.z + dz), rigid("UpperTorso")))
        rows.append(row)
    mb.grid(rows, M["suit"], lambda p: V(p.x - c.x, p.y - c.y, 0.5))
    # buttons, pocket flaps and a breast pocket
    for z in (1.39, WAIST_BUTTON - 0.01):
        p = coat_at(-88, z, 0.004)
        L_cyl(mb, p, p + V(0, -0.006, 0), 0.012, M["button"], coat_weights)
    for th in (-48, -132):
        flap(mb, th, 1.31, 0.13, 0.045, coat_weights)
    flap(mb, -62, 1.97, 0.085, 0.014, coat_weights)


def flap(mb, theta, z, w, h, weights):
    cy, rx, ry = table(COAT, z)
    r = (rx + ry) / 2
    dth = math.degrees(w / r) / 2
    rows = []
    for k in range(3):
        zz = z - h * k / 2
        rows.append([mb.vert(coat_at(theta + dth * (2 * u / 6 - 1), zz, 0.004), weights) for u in range(7)])
    mb.grid(rows, M["suit"], lambda c: V(c.x, c.y, 0) - V(0, 0.02, 0))


def L_cyl(mb, a, b, r, mat, weights, n=12):
    """A short closed cylinder from a to b."""
    W = (b - a).normalized()
    ref = V(1, 0, 0) if abs(W.x) < 0.9 else V(0, 1, 0)
    U = (ref - W * ref.dot(W)).normalized()
    Vv = W.cross(U)
    ra = [mb.vert(a + (U * math.cos(TAU * j / n) + Vv * math.sin(TAU * j / n)) * r, weights) for j in range(n)]
    rb = [mb.vert(b + (U * math.cos(TAU * j / n) + Vv * math.sin(TAU * j / n)) * r, weights) for j in range(n)]
    mb.grid([ra, rb], mat, lambda c: c - (a + b) / 2, wrap=True)
    mb.fan(rb, b, weights, W, mat)
    mb.fan(ra, a, weights, -W, mat)


# ================================================================ limbs: sleeves and trousers
def tube(mb, path, ds, radius, weights, mat, sx, n=20, cap0=True, cap1=False, inner=None):
    """A tube along a polyline (joints in between), rings at distances ds (negative ones go back
    past the start). radius(d, phi) with phi 0 outward, 90 forward. inner: a lining material for
    an open end."""
    segs = list(zip(path, path[1:]))
    lens = [(b - a).length for a, b in segs]
    starts = [sum(lens[:k]) for k in range(len(segs))]
    dirs = [(b - a).normalized() for a, b in segs]

    def frame(d):
        k = next((k for k in range(len(segs)) if d < starts[k] + lens[k]), len(segs) - 1)
        c = segs[k][0] + dirs[k] * (d - starts[k])
        w = dirs[0]
        for j in range(1, len(segs)):
            w = w.lerp(dirs[j], smooth(starts[j] - 0.07, starts[j] + 0.07, d))
        w = w.normalized()
        out = (V(sx, 0, 0) - w * w.dot(V(sx, 0, 0))).normalized()
        fwd = w.cross(out)
        if fwd.y > 0:
            fwd = -fwd
        return c, w, out, fwd

    rings = []
    for d in ds:
        c, w, out, fwd = frame(d)
        wt = weights(d)
        ring = []
        for j in range(n):
            phi = TAU * j / n
            r = radius(d, math.degrees(phi))
            ring.append(mb.vert(c + (out * math.cos(phi) + fwd * math.sin(phi)) * r, wt))
        rings.append((ring, c, w))
    mb.grid([r for r, _, _ in rings], mat, lambda p: p - nearest_axis(p, rings), wrap=True)
    r0, c0, w0 = rings[0]
    r1, c1, w1 = rings[-1]
    if cap0:
        mb.fan(r0, c0 - w0 * 0.01, weights(ds[0]), -w0, mat)
    if cap1:
        mb.fan(r1, c1 + w1 * 0.01, weights(ds[-1]), w1, mat)
    elif inner is not None:  # an open end: fold the cloth in so it has thickness
        ring_in = [mb.vert(c1 + (mb.co[i] - c1) * 0.86 - w1 * 0.02, weights(ds[-1])) for i in r1]
        mb.grid([r1, ring_in], inner, lambda p: c1 - p, wrap=True)
    return rings


def nearest_axis(p, rings):
    best = min(rings, key=lambda r: (r[1] - p).length)
    c, w = best[1], best[2]
    return c + w * (p - c).dot(w)


def stations(d0, d1, step, dense=()):
    n = max(1, round((d1 - d0) / step))
    ds = [d0 + (d1 - d0) * k / n for k in range(n + 1)]
    for c in dense:
        ds += [c + step / 2 * k for k in range(-3, 4)]
    ds = sorted(d for d in ds if d0 <= d <= d1)
    out = [ds[0]]
    for d in ds[1:]:
        if d - out[-1] > 0.004:
            out.append(d)
    return out


def build_sleeves(coat, shirt):
    for side, sx in SIDES:
        sh, el, wr = J[f"shoulder_{side}"], J[f"elbow_{side}"], J[f"wrist_{side}"]
        Lu, Lf = (el - sh).length, (wr - el).length
        end = Lu + Lf - 0.035
        up, lo = f"{side}UpperArm", f"{side}LowerArm"

        def radius(d, phi, base=0.0):
            r = table([(-0.05, 0.03), (-0.02, 0.055), (0.05, 0.06), (0.3, 0.055), (Lu, 0.052), (Lu + 0.2, 0.049),
                       (end, 0.047)], d)[0]
            fold = 0.003 * math.sin(math.radians(phi) * 3 + d * 40) * g((d - Lu) / 0.08)  # bunching at the elbow
            return r + fold + base

        def weights(d):
            return blend(up, lo, smooth(Lu - 0.08, Lu + 0.08, d))

        tube(coat, [sh, el, wr], stations(-0.05, end, 0.045, (Lu,)), radius, weights, M["suit"], sx, n=16,
             inner=M["lining"])
        # the shirt cuff showing past the sleeve
        tube(shirt, [sh, el, wr], stations(end - 0.05, end + 0.018, 0.02), lambda d, phi: 0.04, lambda d: rigid(lo),
             M["shirt"], sx, n=16, cap0=False, inner=M["shirt"])


def build_trousers(mb):
    p = J["root"] + V(0, 0, 0.0)
    seat = L_ellipsoid(mb, V(0, 0.025, 1.36), (0.155, 0.118, 0.12), M["suit"], rigid("LowerTorso"))
    del seat
    for side, sx in SIDES:
        hp, kn, an = J[f"hip_{side}"], J[f"knee_{side}"], J[f"ankle_{side}"]
        Lt, Ls = (kn - hp).length, (an - kn).length
        end = Lt + Ls - 0.015
        up, lo = f"{side}UpperLeg", f"{side}LowerLeg"

        def radius(d, phi):
            r = table([(-0.08, 0.06), (0.0, 0.074), (0.25, 0.068), (Lt, 0.06), (Lt + 0.3, 0.057), (end, 0.056)], d)[0]
            crease = 0.004 * g(((phi - 90 + 180) % 360 - 180) / 12)  # the pressed crease down the front
            return r + crease

        def weights(d):
            if d < 0.05:
                return blend("LowerTorso", up, smooth(-0.08, 0.05, d))
            return blend(up, lo, smooth(Lt - 0.08, Lt + 0.08, d))

        tube(mb, [hp, kn, an], stations(-0.08, end, 0.05, (Lt,)), radius, weights, M["suit"], sx, inner=M["lining"])
    return p


def L_ellipsoid(mb, c, radii, mat, weights, n=20, m=10):
    rows = []
    for i in range(m + 1):
        lam = -math.pi / 2 + math.pi * i / m
        rows.append([mb.vert(c + V(math.cos(lam) * math.cos(TAU * j / n) * radii[0],
                                   math.cos(lam) * math.sin(TAU * j / n) * radii[1], math.sin(lam) * radii[2]), weights)
                     for j in range(n)])
    mb.grid(rows, mat, lambda p: p - c, wrap=True)
    return rows


# ================================================================ shirt, collar and tie
def build_shirt(mb):
    w = rigid("UpperTorso")
    rows = []
    for k in range(21):  # the shirt front showing in the V of the coat
        z = lerp(WAIST_BUTTON - 0.04, 2.24, k / 20)
        gz = opening(min(z, 2.2)) + 8
        row = []
        for u in range(9):
            th = -90 - gz + 2 * gz * u / 8
            p = coat_at(th, min(z, 2.175), -0.009) if z <= 2.175 else yoke_at(th, (z - 2.175) / 0.077, -0.009)
            row.append(mb.vert(p, w))
        rows.append(row)
    mb.grid(rows, M["shirt"], lambda c: V(c.x, c.y + 0.5, 0) * -1)
    c, r = NECK
    band = []  # the collar band round the neck, and the dark inside of the collar
    for dz in (-0.012, 0.03):
        band.append([mb.vert(V(c.x + (r - 0.006) * math.cos(TAU * j / 32), c.y + (r - 0.006) * math.sin(TAU * j / 32),
                               c.z + dz), w) for j in range(32)])
    mb.grid(band, M["shirt"], lambda p: V(p.x - c.x, p.y - c.y, 0), wrap=True)
    mb.fan(band[0], c + V(0, 0, -0.01), w, V(0, 0, 1), M["collar_in"])
    for s in (1, -1):  # the collar's two points, folded down over the tie
        a0 = math.radians(-90 + s * 6)
        a1 = math.radians(-90 + s * 55)
        p0 = V(c.x + r * math.cos(a0), c.y + r * math.sin(a0) - 0.004, c.z + 0.03)
        p1 = V(c.x + (r + 0.008) * math.cos(a1), c.y + (r + 0.008) * math.sin(a1), c.z + 0.025)
        tip = V(s * 0.045, coat_at(-90 + s * 25, 2.17, -0.004).y, 2.165)
        ids = [mb.vert(p0, w), mb.vert(p1, w), mb.vert(tip, w)]
        mb.face(ids, V(0, -1, 0.3), M["shirt"])
        ids_b = [mb.vert(p0 + V(0, 0.004, 0), w), mb.vert(p1 + V(0, 0.004, 0), w), mb.vert(tip + V(0, 0.004, 0), w)]
        mb.face(ids_b, V(0, 1, -0.3), M["shirt"])
    # the tie: a small knot at the collar and a narrow blade down to behind the button
    knot_c = V(0, coat_at(-90, 2.175, -0.004).y - 0.012, 2.235)
    L_box(mb, knot_c, (0.034, 0.022, 0.034), M["tie"], w, taper=0.7)
    rows = []
    for k in range(17):
        z = lerp(2.215, WAIST_BUTTON - 0.06, k / 16)
        half = lerp(0.013, 0.021, smooth(2.215, 1.7, z))
        if z < WAIST_BUTTON - 0.02:
            half *= max(0.05, (z - (WAIST_BUTTON - 0.06)) / 0.04)  # the pointed tip
        y = coat_at(-90, min(z, 2.175), -0.0045).y if z <= 2.175 else knot_c.y + 0.01
        rows.append([mb.vert(V(x, y, z), w) for x in (-half, 0.0, half)])
    mb.grid(rows, M["tie"], lambda c: V(0, -1, 0))


def L_box(mb, c, size, mat, weights, taper=1.0):
    sx, sy, sz = (s / 2 for s in size)
    top = [V(-sx, -sy, sz), V(sx, -sy, sz), V(sx, sy, sz), V(-sx, sy, sz)]
    bot = [V(-sx * taper, -sy, -sz), V(sx * taper, -sy, -sz), V(sx * taper, sy, -sz), V(-sx * taper, sy, -sz)]
    t = [mb.vert(c + p, weights) for p in top]
    b = [mb.vert(c + p, weights) for p in bot]
    mb.grid([b, t], mat, lambda p: p - c, wrap=True)
    mb.face(t, V(0, 0, 1), mat)
    mb.face(b, V(0, 0, -1), mat)


# ================================================================ hands: long, thin fingers
def finger_tube(mb, pts, radii, weights_at, mat, n=10):
    rings = []
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        ref = V(0, 0, 1) if abs(T.z) < 0.9 else V(1, 0, 0)
        U = (ref - T * ref.dot(T)).normalized()
        W = T.cross(U)
        wt = weights_at(i / (len(pts) - 1))
        rings.append(([mb.vert(p + (U * math.cos(TAU * j / n) + W * math.sin(TAU * j / n)) * radii[i], wt)
                       for j in range(n)], p, T, wt))
    mb.grid([r for r, _, _, _ in rings], mat, lambda q: q - min(rings, key=lambda r: (r[1] - q).length)[1], wrap=True)
    r, p, T, wt = rings[-1]
    mb.fan(r, p + T * radii[-1] * 0.9, wt, T, mat)
    r, p, T, wt = rings[0]
    mb.fan(r, p - T * radii[0] * 0.5, wt, -T, mat)


def build_hands(mb):
    for side, sx in SIDES:
        w, d, pn, a = C.hand_frame(side, sx)
        hand = f"{side}Hand"
        back = -pn
        # the palm: a flattened box narrowing at the wrist
        rows = []
        for k in range(7):
            t = k / 6
            c = w + d * (0.005 + 0.11 * t)
            half_w = lerp(0.021, 0.034, smooth(0, 0.6, t))
            half_t = lerp(0.016, 0.011, t)
            row = []
            for j in range(14):
                ang = TAU * j / 14
                e = 2 / 3.5
                cx, cy = math.cos(ang), math.sin(ang)
                p = c + a * (half_w * math.copysign(abs(cx) ** e, cx)) + back * (half_t * math.copysign(abs(cy) ** e, cy))
                row.append(mb.vert(p, rigid(hand)))
            rows.append(row)
        mb.grid(rows, M["skin"], lambda q: q - (w + d * d.dot(q - w)), wrap=True)
        mb.fan(rows[0], w - d * 0.008, rigid(hand), -d, M["skin"])
        mb.fan(rows[-1], w + d * 0.12, rigid(hand), d, M["skin"])
        # the wrist, up into the cuff
        finger_tube(mb, [w - d * 0.06, w + d * 0.01], [0.02, 0.02],
                    lambda t: blend(f"{side}LowerArm", hand, t), M["skin"])
        for f, (k, m, t) in C.hand_layout(side, sx).items():
            fb1, fb2 = f"{side}{f}1", f"{side}{f}2"
            r0 = 0.0105 if f != "Thumb" else 0.012
            pts, radii = [], []
            for i in range(9):
                u = i / 8
                p = k.lerp(m, u * 2) if u <= 0.5 else m.lerp(t, (u - 0.5) * 2)
                knuckle = 0.0015 * (g((u - 0.0) / 0.08) + g((u - 0.5) / 0.07) + g((u - 0.78) / 0.06))
                pts.append(p)
                radii.append(lerp(r0, r0 * 0.68, u) + knuckle)
            finger_tube(mb, pts, radii, lambda u, fb1=fb1, fb2=fb2: blend(fb1, fb2, smooth(0.42, 0.58, u))
                        if u > 0.05 else blend(hand, fb1, u / 0.05), M["skin"])


# ================================================================ shoes
FOOT = [  # t (heel to toe), centre height, half width, half height
    (0.0, 0.045, 0.012, 0.03), (0.04, 0.05, 0.03, 0.045), (0.12, 0.055, 0.04, 0.052), (0.3, 0.05, 0.044, 0.048),
    (0.5, 0.04, 0.048, 0.036), (0.72, 0.032, 0.046, 0.028), (0.88, 0.026, 0.04, 0.022), (0.97, 0.022, 0.028, 0.017),
    (1.0, 0.02, 0.012, 0.01),
]


def build_shoes(mb):
    for side, sx in SIDES:
        an, toe = J[f"ankle_{side}"], J[f"toe_{side}"]
        fwd = V(toe.x - an.x, toe.y - an.y, 0).normalized()
        lat = V(0, 0, 1).cross(fwd).normalized()
        heel = V(an.x, an.y + 0.06, 0)
        Lf = 0.34
        foot = rigid(f"{side}Foot")
        rows = []
        for k in range(17):
            t = k / 16
            cz, hw, hh = table(FOOT, t)
            c = heel + fwd * (Lf * t)
            row = []
            for j in range(20):
                ang = TAU * j / 20
                p = c + lat * (hw * math.cos(ang)) + V(0, 0, cz + hh * math.sin(ang))
                p.z = max(0.018, p.z)
                row.append(mb.vert(p, foot))
            rows.append(row)
        mb.grid(rows, M["leather"], lambda q: V(*(q - heel - fwd * fwd.dot(q - heel))[:2], q.z - 0.04), wrap=True)
        mb.fan(rows[0], heel + V(0, 0, 0.045) - fwd * 0.004, foot, -fwd, M["leather"])
        mb.fan(rows[-1], heel + fwd * (Lf + 0.004) + V(0, 0, 0.02), foot, fwd, M["leather"])
        # the sole and heel block
        sole = []
        for z in (0.0, 0.019):
            ring = []
            for k in range(17):
                t = k / 16
                hw = table(FOOT, t)[1] + 0.004
                ring.append((heel + fwd * (Lf * t) + lat * hw + V(0, 0, z), heel + fwd * (Lf * t) - lat * hw + V(0, 0, z)))
            outline = [p for p, _ in ring] + [q for _, q in ring[::-1]]
            sole.append([mb.vert(p, foot) for p in outline])
        mb.grid(sole, M["sole"], lambda q: V(*(q - heel - fwd * fwd.dot(q - heel))[:2], 0), wrap=True)
        mb.face(list(sole[0]), V(0, 0, -1), M["sole"])
        L_box(mb, heel + fwd * 0.05 + V(0, 0, -0.012), (0.075, 0.07, 0.024), M["sole"], foot)
        for k in range(4):  # laces
            c = heel + fwd * (0.15 + 0.03 * k) + V(0, 0, table(FOOT, (0.15 + 0.03 * k) / Lf)[0] +
                                                    table(FOOT, (0.15 + 0.03 * k) / Lf)[2] - 0.004)
            L_box(mb, c, (0.05, 0.006, 0.006), M["sole"], foot)


# ================================================================ the monitor head
def monitor_matrix():
    return (Matrix.Translation(V(0, MONITOR["y"], MONITOR["bottom"]))
            @ Matrix.Rotation(math.radians(MONITOR["tilt"]), 4, "X"))


def build_monitor():
    """The CRT, as separate rigid objects joined into Monitor, plus the Screen and the Light.
    Local frame: x right, y back, z up, origin under the middle of the monitor."""
    w, h, bd, depth = MONITOR["w"], MONITOR["h"], MONITOR["bezel_d"], MONITOR["depth"]
    yf = -depth / 2  # the front face
    case, dark = M["case"], M["case_dark"]
    bezel = L.rbox("bezel", (w, bd, h), (0, yf + bd / 2, h / 2), 0.028, case, segs=4)
    sc = (0, yf, h / 2 + 0.022)  # the screen's centre on the front face
    L.cut(bezel, L.rbox("c", (0.335, 0.05, 0.26), sc, 0.012, case))
    parts = [bezel]
    surround = L.rbox("surround", (0.33, 0.004, 0.255), (0, yf + 0.024, sc[2]), 0.01, M["recess"])
    parts.append(surround)
    # the tube housing behind, tapering back
    rings = []
    for k in range(9):
        t = k / 8
        y = lerp(yf + bd - 0.01, depth / 2, t)
        rx, rz = lerp(w / 2 - 0.02, 0.125, t ** 1.1), lerp(h / 2 - 0.02, 0.1, t ** 1.1)
        cz = lerp(h / 2, h / 2 + 0.02, t)
        rings.append([V(x, y, cz + z) for x, z in L.superellipse(rx, rz, 32, 5.0)])
    housing = L.sweep("housing", [sum(r, Vector()) / len(r) for r in rings], None, case) if False else None
    import bmesh  # noqa: E402
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in r] for r in rings]
    for a, b in zip(vr, vr[1:]):
        for j in range(32):
            bm.faces.new([a[j], a[(j + 1) % 32], b[(j + 1) % 32], b[j]])
    bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    housing = L.from_bm("housing", bm, case)
    for k in range(9):  # vents across the top of the housing
        L.cut(housing, L.rbox("c", (0.15, 0.009, 0.06), (0, 0.0 + 0.022 * k - 0.04, h / 2 + 0.16), 0.002, case))
    parts.append(housing)
    parts.append(L.rbox("backplate", (0.2, 0.012, 0.16), (0, depth / 2, h / 2 + 0.02), 0.01, dark))
    # controls under the screen: four buttons, the power button; the light is its own part
    for k in range(4):
        parts.append(L.rbox("btn", (0.016, 0.008, 0.008), (0.015 + 0.022 * k, yf - 0.001, 0.034), 0.002, dark))
    parts.append(L.cyl("power", 0.013, 0.008, (0.16, yf - 0.002, 0.034), dark, axis="Y", segs=24, bevel=0.002))
    parts.append(L.cyl("ledring", 0.007, 0.004, (0.125, yf - 0.0005, 0.034), dark, axis="Y", segs=16))
    parts.append(L.plane("badge", 0.12, 0.024, (-0.1, yf - 0.0012, 0.034), (0, -1, 0), (0, 0, 1),
                         L.printed("Badge", lin(C.PALETTE["monitor"]), "print_badge.png", 0.42)))
    # the property sticker on his left side of the housing
    ys = 0.02
    t = (ys - (yf + bd - 0.01)) / (depth / 2 - (yf + bd - 0.01))
    hx = lerp(w / 2 - 0.02, 0.125, t ** 1.1)
    slope = (0.125 - (w / 2 - 0.02)) / (depth / 2 - (yf + bd - 0.01))
    parts.append(L.plane("sticker", 0.1, 0.05, (hx + 0.002, ys, h / 2 + 0.01), (1, -slope, 0), (0, 0, 1),
                         L.textured("Sticker", "sticker.png", 0.6)))
    # where the cables go in: a socket underneath and a port at the back
    parts.append(L.cyl("socket", 0.055, 0.02, (0, -0.02, 0.0), dark, segs=32, bevel=0.004))
    parts.append(L.rbox("port", (0.05, 0.03, 0.035), (0.06, depth / 2 + 0.008, 0.09), 0.006, dark))
    mon = L.join(parts, "Monitor")
    # the screen: curved CRT glass filling the bezel's window
    import bmesh as bm_  # noqa: E402
    bm = bm_.new()
    uvl = bm.loops.layers.uv.new("Decal")
    nx, nz = 16, 12
    sw, shh = 0.31, 0.235
    vs = []
    for i in range(nz + 1):
        row = []
        for j in range(nx + 1):
            u, v = j / nx, i / nz
            x, z = (u - 0.5) * sw, (v - 0.5) * shh
            bulge = 0.012 * (1 - (2 * u - 1) ** 2) * (1 - (2 * v - 1) ** 2)
            row.append(bm.verts.new(V(x, yf + 0.022 - bulge, sc[2] + z)))
        vs.append(row)
    for i in range(nz):
        for j in range(nx):
            f = bm.faces.new([vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]])
            for loop, (a_, b_) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))):
                loop[uvl].uv = (a_ / nx, b_ / nz)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    screen = L.from_bm("Screen", bm, L.textured("M_Screen", "screen_nosignal.png", 0.08, emit=2.0))
    for f in screen.data.polygons:  # face the viewer
        pass
    if screen.data.polygons[0].normal.y > 0:
        screen.data.flip_normals()
    light = L.sphere("Light", 0.0045, (0.125, yf - 0.002, 0.034), L.light("M_Light", (0.15, 1.0, 0.3), 5.0))
    Mx = monitor_matrix()
    for ob in (mon, screen, light):
        ob.data.transform(Mx)
        ob.data.shade_smooth()
        ob.data.set_sharp_from_angle(angle=math.radians(35))
    return mon, screen, light


# ================================================================ cables
def cable_tube(mb, pts, r, weights_at, mat, n=10):
    rings = []
    T_prev = None
    U = None
    for i, p in enumerate(pts):
        T = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if U is None:
            ref = V(1, 0, 0) if abs(T.x) < 0.9 else V(0, 1, 0)
            U = (ref - T * ref.dot(T)).normalized()
        else:
            U = (U - T * U.dot(T)).normalized()
        W = T.cross(U)
        wt = weights_at(i / (len(pts) - 1), p)
        rings.append(([mb.vert(p + (U * math.cos(TAU * j / n) + W * math.sin(TAU * j / n)) * r, wt) for j in range(n)],
                      p, T, wt))
        T_prev = T
    del T_prev
    mb.grid([x[0] for x in rings], mat, lambda q: q - min(rings, key=lambda x: (x[1] - q).length)[1], wrap=True)
    for idx, sign in ((0, -1), (-1, 1)):
        ring, p, T, wt = rings[idx]
        mb.fan(ring, p + T * sign * r * 0.3, wt, T * sign, mat)
    return rings


def spline(points, per=10):
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(per):
            t = k / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def build_cables(mb):
    Mx = monitor_matrix()
    # the neck: two thick cables twisting up out of the collar into the socket under the monitor
    for k, (r, phase) in enumerate(((0.024, 0.0), (0.019, math.pi))):
        pts = []
        for i in range(13):
            t = i / 12
            z = lerp(2.15, MONITOR["bottom"] + 0.008, t)
            a = phase + 2.2 * t
            pts.append(V(0.022 * math.cos(a), -0.018 + 0.016 * math.sin(a), z))
        top = Mx @ V(pts[-1].x, -0.02, 0.0)
        pts[-1] = top
        cable_tube(mb, pts, r, lambda t, p: blend("UpperTorso", "Head", smooth(2.2, 2.32, p.z)), M["rubber"])
    # the cable that hangs down his back, from the port behind the monitor
    port = Mx @ V(0.06, MONITOR["depth"] / 2 + 0.024, 0.09)
    path = spline([port, port + V(0.0, 0.05, -0.05)] + CABLE[1:], per=12)

    def cable_weights(t, p):
        if p.z > 2.25:
            return blend("Head", "Cable1", smooth(2.36, 2.25, p.z))
        if p.z > CABLE[2].z:
            return blend("Cable1", "Cable2", smooth(CABLE[2].z + 0.08, CABLE[2].z - 0.08, p.z))
        return blend("Cable2", "Cable3", smooth(CABLE[3].z + 0.1, CABLE[3].z - 0.1, p.z))

    cable_tube(mb, path, 0.016, cable_weights, M["rubber"])
    # its plug, hanging off the end: a blue VGA plug with two thumbscrews
    end, before = path[-1], path[-2]
    T = (end - before).normalized()
    wplug = rigid("Cable3")
    body_c = end + T * 0.03
    L_box(mb, body_c, (0.045, 0.022, 0.05), M["vga"], wplug, taper=0.75)
    L_box(mb, body_c + T * 0.033, (0.04, 0.012, 0.018), M["metal"], wplug, taper=0.8)
    for sx in (1, -1):
        a = body_c + V(sx * 0.026, 0, 0.012)
        L_cyl(mb, a, a + T * 0.04, 0.0035, M["metal"], wplug, n=8)


# ================================================================ rig and assembly
def build_armature():
    arm = bpy.data.armatures.new("StandIn_Rig")
    ob = bpy.data.objects.new("StandIn_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    L.activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, (h, t, parent) in C.bones().items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = h, t
        ebs[name] = eb
    for name, (h, t, parent) in C.bones().items():
        if parent:
            ebs[name].parent = ebs[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def skin(ob, weights, rig):
    groups = {}
    for vi, ws in enumerate(weights):
        tot = sum(ws.values())
        for b, wt in ws.items():
            if wt / tot < 0.01:
                continue
            if b not in groups:
                groups[b] = ob.vertex_groups.new(name=b)
            groups[b].add([vi], wt / tot, "REPLACE")
    ob.parent = rig
    ob.modifiers.new("Armature", "ARMATURE").object = rig


def main(out):
    L.reset()
    materials()
    coat, shirt, trousers, hands, shoes, cables = (MB(n) for n in ("Coat", "Shirt", "Trousers", "Hands", "Shoes", "Cable"))
    build_coat(coat)
    build_sleeves(coat, shirt)
    build_shirt(shirt)
    build_trousers(trousers)
    build_hands(hands)
    build_shoes(shoes)
    build_cables(cables)
    rig = build_armature()
    bake_dir = os.path.join(TEX, "baked")
    sizes = {"Coat": 1024, "Shirt": 512, "Trousers": 512, "Hands": 512, "Shoes": 512, "Cable": 512}
    obs = {}
    for mb in (coat, shirt, trousers, hands, shoes, cables):
        ob = mb.build()
        L.bake(ob, sizes[mb.name], f"standin_{mb.name.lower()}", bake_dir)
        skin(ob, mb.w, rig)
        obs[mb.name] = ob
    mon, screen, light = build_monitor()
    L.bake(mon, 1024, "standin_monitor", bake_dir)
    for ob in (mon, screen, light):
        skin(ob, [{"Head": 1.0}] * len(ob.data.vertices), rig)
        obs[ob.name] = ob
    total = 0
    for name, ob in obs.items():
        n = L.tris(ob)
        total += n
        print(f"{name:10s} tris {n:6d}")
    print("total tris", total)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "stand_in.blend"))
