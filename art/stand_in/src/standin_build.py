#!/usr/bin/env python3
"""Builds the Stand-in, the floor-2 monster: a 8.3 ft faceless shop mannequin in a faded
Orange Court uniform, as 15 Roblox R15 body parts plus a swappable badge photo, with an
R15 rig. Saves a .blend.

Usage: python3 standin_build.py OUT.blend
"""
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import standin_common as S  # noqa: E402
from standin_common import J, V, in_region  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
rng = random.Random(8)
TAU = 2 * math.pi


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def g(t):
    return math.exp(-t * t)


def table(rows, x):
    """Linear interpolation in a table of (x, a, b, ...) rows."""
    x = min(rows[-1][0], max(rows[0][0], x))
    for r0, r1 in zip(rows, rows[1:]):
        if x <= r1[0]:
            k = (x - r0[0]) / (r1[0] - r0[0])
            return tuple(lerp(a, b, k) for a, b in zip(r0[1:], r1[1:]))
    return rows[-1][1:]


# ================================================================ mesh builder
class MB:
    def __init__(self, name):
        self.name = name
        self.co, self.w, self.faces, self.fuv = [], [], [], []

    def vert(self, co, weights):
        self.co.append(Vector(co))
        self.w.append(weights(Vector(co)) if callable(weights) else weights)
        return len(self.co) - 1

    def face(self, items, want=None):
        ids = [i for i, _ in items]
        uvs = [uv for _, uv in items]
        if want is not None:
            a, b, c = (self.co[i] for i in ids[:3])
            if (b - a).cross(c - a).dot(want) < 0:
                ids.reverse()
                uvs.reverse()
        self.faces.append(ids)
        self.fuv.append(uvs)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def build(self, material):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(c) for c in self.co], [], self.faces)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, uvs in zip(me.polygons, self.fuv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
        me.materials.append(material)
        me.shade_smooth()
        me.validate()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def grid(mb, nu, nv, fn, weights, outward, wrap=False, flip=False):
    """Quad grid from fn(u, v) -> (point, (uu, vv)). outward(point) gives the side the faces
    should face (flip=True faces them the other way). wrap repeats u=0 at u=1 for a UV seam."""
    rows = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            p, uv = fn(u, v)
            if wrap and i == nu:
                p = fn(0.0, v)[0]
            row.append((mb.vert(p, weights), uv))
        rows.append(row)
    for j in range(nv):
        for i in range(nu):
            q = [rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]]
            ctr = sum((mb.co[k] for k, _ in q), Vector()) / 4
            want = outward(ctr)
            mb.face(q, -want if flip else want)
    return rows


def fan(mb, ring, tip, tip_uv, weights, want):
    t = (mb.vert(tip, weights), tip_uv)
    for a, b in zip(ring, ring[1:]):
        mb.face([a, b, t], want)


def frame(axis):
    w = axis.normalized()
    side = V(1, 0, 0)
    u = (side - w * side.dot(w)).normalized()
    return u, w.cross(u), w


def loft(mb, p0, p1, radius, region, weights, n_around=16, n_along=12, t0=0.0, t1=1.0, cap0=True, cap1=True,
         uv_v=None, cap_lift=0.6):
    """Tube from p0 to p1 between parameters t0..t1; radius(t, th) may vary around. The end caps
    are fans whose tips stand cap_lift x the end radius past the end ring."""
    p0, p1 = Vector(p0), Vector(p1)
    U, Vv, W = frame(p1 - p0)
    L = (p1 - p0).length

    def pt(u, v):
        t = lerp(t0, t1, v)
        th = TAU * u
        r = radius(t, th)
        p = p0 + W * (L * t) + (U * math.cos(th) + Vv * math.sin(th)) * r
        return p, in_region(region, u, uv_v(t) if uv_v else v)

    def out(c):
        d = c - p0
        return d - W * d.dot(W)

    rows = grid(mb, n_around, n_along, pt, weights, out, wrap=True)
    if cap0:
        r0 = radius(t0, 0.0)
        fan(mb, rows[0], p0 + W * (L * t0 - cap_lift * r0), in_region(region, 0.5, 0.0), weights, -W)
    if cap1:
        r1 = radius(t1, 0.0)
        fan(mb, rows[-1], p0 + W * (L * t1 + cap_lift * r1), in_region(region, 0.5, 1.0), weights, W)
    return rows


def ellipsoid(mb, c, radii, region, weights, n_lon=24, n_lat=14, disp=None, rot=None):
    c = Vector(c)
    R = rot or Matrix.Identity(3)

    def pt(u, v):
        phi, lam = TAU * u, -math.pi / 2 + math.pi * v
        d = V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))
        p = V(d.x * radii[0], d.y * radii[1], d.z * radii[2])
        if disp:
            p = disp(p, d)
        return c + R @ p, in_region(region, u, v)

    return grid(mb, n_lon, n_lat, pt, weights, lambda q: q - c, wrap=True)


def rigid(bone):
    return {bone: 1.0}


# ================================================================ head, neck and wig
HEAD_R = (0.092, 0.104, 0.132)


def head_shape(p, d):
    """Egg head with only a ghost of a face: brow, nose ridge, shallow sockets, a hint of lips."""
    z = p.z
    taper = 1 - 0.24 * smooth(-0.03, -0.13, z)
    p = V(p.x * taper, p.y * taper - 0.01 * smooth(-0.05, -0.13, z) * (d.y < 0), z)
    if d.y < -0.2:
        f = smooth(-0.2, -0.7, d.y)
        x = p.x
        bump = (0.013 * g(x / 0.011) * g((z + 0.012) / 0.028)
                + 0.004 * g((z - 0.032) / 0.012) * smooth(0.075, 0.04, abs(x))
                - 0.006 * g((abs(x) - 0.032) / 0.016) * g((z - 0.014) / 0.016)
                + 0.003 * g(x / 0.022) * g((z + 0.058) / 0.008)
                + 0.004 * g(x / 0.02) * g((z + 0.10) / 0.015))
        p = p + V(0, -1, 0) * (bump * f)
    return p


def hairline(phi):
    """Polar latitude (radians) where the wig ends, by azimuth (front is -Y)."""
    front = max(0.0, -math.sin(phi))
    back = max(0.0, math.sin(phi))
    return math.radians(-5 + 43 * front ** 1.2 - 25 * back)


WIG_TILT = Matrix.Rotation(math.radians(4.0), 3, "Y")
WIG_OFF = V(0.005, 0.0, 0.002)
WIG_R = (HEAD_R[0] + 0.011, HEAD_R[1] + 0.011, HEAD_R[2] + 0.012)


def wig_point(phi, lam, extra=0.0):
    d = V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))
    side = 0.006 * (1 - abs(math.sin(lam)))  # a little volume at the sides
    part = -0.003 * g((phi % TAU - 1.5 * math.pi) / 0.05) * smooth(0.6, 1.2, lam)
    p = V(d.x * (WIG_R[0] + side + extra), d.y * (WIG_R[1] + side + extra), d.z * (WIG_R[2] + extra)) + d * part
    return J["head_c"] + WIG_OFF + WIG_TILT @ p


def hair_weights(p):
    k = smooth(2.12, 2.24, p.z)
    return {"Head": k, "UpperTorso": 1 - k} if k < 1 else {"Head": 1.0}


# colliders the hair drapes over: head, neck, shoulders, the bodice
BODICE = [  # z, center y, rx, ry
    (1.705, 0.0, 0.112, 0.084), (1.78, 0.0, 0.118, 0.090), (1.86, -0.004, 0.130, 0.100),
    (1.94, -0.008, 0.140, 0.108), (2.01, -0.002, 0.152, 0.104), (2.07, 0.004, 0.170, 0.092),
    (2.12, 0.006, 0.150, 0.080), (2.165, 0.008, 0.075, 0.060),
]


def bust(th, z):
    out = 0.0
    for c in (-math.pi / 2 - 0.45, -math.pi / 2 + 0.45):
        dth = math.atan2(math.sin(th - c), math.cos(th - c))
        out += 0.022 * g(dth / 0.32) * g((z - 1.935) / 0.05)
    return out


def bodice_point(th, z, off=0.0):
    cy, rx, ry = table(BODICE, z)
    b = bust(th, z)
    return V((rx + b + off) * math.cos(th), cy + (ry + b + off) * math.sin(th), z)


def collide(p):
    for _ in range(3):
        # head (with the wig on it)
        q = p - (J["head_c"] + WIG_OFF)
        r = (WIG_R[0] + 0.012, WIG_R[1] + 0.012, WIG_R[2] + 0.012)
        k = (q.x / r[0]) ** 2 + (q.y / r[1]) ** 2 + (q.z / r[2]) ** 2
        if k < 1:
            p = J["head_c"] + WIG_OFF + q / math.sqrt(k)
        # neck
        if 2.1 < p.z < 2.32:
            h = V(p.x, p.y, 0)
            if h.length < 0.06:
                p = V(*(h.normalized() * 0.06)[:2], p.z) if h.length > 1e-6 else V(0, 0.06, p.z)
        # shoulders, puffed by the sleeves
        for side, sx in S.SIDES:
            c = J[f"shoulder_{side}"] + V(0, 0, 0.02)
            q = p - c
            if q.length < 0.085:
                p = c + q.normalized() * 0.085
        # the bodice, with the collar on it
        if 1.6 < p.z < 2.19:
            cy, rx, ry = table(BODICE, min(p.z, 2.165))
            rx, ry = rx + 0.024, ry + 0.024
            dx, dy = p.x, p.y - cy
            k = (dx / rx) ** 2 + (dy / ry) ** 2
            if k < 1:
                s = 1 / math.sqrt(k)
                p = V(dx * s, cy + dy * s, p.z)
    return p


def build_head():
    mb = MB("Head")
    hw = rigid("Head")
    ellipsoid(mb, J["head_c"], HEAD_R, "skin", hw, 40, 26, disp=head_shape)
    # short seamed neck with a metal connector at the back
    neck_p0, neck_p1 = V(0, 0.005, 2.14), V(0, 0.004, 2.31)
    loft(mb, neck_p0, neck_p1, lambda t, th: 0.041 - 0.003 * g((t - 0.42) / 0.05), "skin", hw, 20, 10,
         cap0=False, cap1=False)
    loft(mb, V(0, 0.038, 2.215), V(0, 0.054, 2.215), lambda t, th: 0.011, "metal", hw, 10, 1)
    # the wig cap: sits a little crooked, so the scalp seam shows on one side
    def cap(u, v):
        phi = TAU * u
        lam = math.pi / 2 - v * (math.pi / 2 - hairline(phi))
        return wig_point(phi, lam), in_region("scalp", u, 1 - v)
    grid(mb, 48, 16, cap, hw, lambda q: q - J["head_c"], wrap=True)

    # long hair: columns start at the hairline and fall, draping over the shoulders
    a0, a1 = math.radians(-30), math.radians(210)  # the face stays clear: hair starts 60 degrees off the front
    ncol, nrow = 30, 20
    paths = []
    for i in range(ncol + 1):
        phi = lerp(a0, a1, i / ncol)
        p = wig_point(phi, hairline(phi), 0.004)
        front = max(0.0, -math.sin(phi))
        z_end = 1.86 + 0.06 * front + 0.025 * math.sin(5 * phi + 1.3)
        nrm = (p - J["head_c"]).normalized()
        d = (V(0, 0, -1) - nrm * nrm.dot(V(0, 0, -1))).normalized()
        pts = [p]
        while p.z > z_end and len(pts) < 200:
            d = (d * 0.75 + V(0, 0, -1) * 0.25).normalized()
            q = collide(p + d * 0.015)
            d = (q - p).normalized()
            p = q
            pts.append(p)
        # resample to nrow+1 points by arc length
        acc = [0.0]
        for a, b in zip(pts, pts[1:]):
            acc.append(acc[-1] + (b - a).length)
        res = []
        for k in range(nrow + 1):
            s = acc[-1] * k / nrow
            j = next((m for m in range(1, len(acc)) if acc[m] >= s), len(acc) - 1)
            f = (s - acc[j - 1]) / max(1e-9, acc[j] - acc[j - 1])
            res.append(pts[j - 1].lerp(pts[j], f))
        paths.append(res)

    outer, inner = {}, {}
    for i, col in enumerate(paths):
        for k, p in enumerate(col):
            h = V(p.x, p.y, 0)
            radial = (p - J["head_c"]).normalized() if p.z > 2.25 else (h.normalized() if h.length > 1e-6 else V(0, 1, 0))
            uv = in_region("hair", i / ncol, 1 - k / nrow)
            outer[i, k] = (mb.vert(p, hair_weights), uv)
            inner[i, k] = (mb.vert(p - radial * 0.012, hair_weights), uv)

    def axis_out(c):
        return (c - J["head_c"]) if c.z > 2.25 else V(c.x, c.y, 0)

    for i in range(ncol):
        for k in range(nrow):
            for side, sign in ((outer, 1), (inner, -1)):
                q = [side[i, k], side[i + 1, k], side[i + 1, k + 1], side[i, k + 1]]
                ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
                mb.face(q, axis_out(ctr) * sign)
    for i in range(ncol):  # the cut ends
        q = [outer[i, nrow], outer[i + 1, nrow], inner[i + 1, nrow], inner[i, nrow]]
        mb.face(q, V(0, 0, -1))
    for i, tang in ((0, -1), (ncol, 1)):  # the two edges framing the face
        for k in range(nrow):
            q = [outer[i, k], outer[i, k + 1], inner[i, k + 1], inner[i, k]]
            ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
            mb.face(q, V(-ctr.y, ctr.x, 0) * tang)
    return mb


# ================================================================ torso, collar, badge
def build_upper_torso():
    mb = MB("UpperTorso")
    w = rigid("UpperTorso")

    def bod(u, v):
        th = TAU * u
        z = lerp(1.705, 2.165, v)
        return bodice_point(th, z), in_region("bodice", u, v)

    grid(mb, 56, 22, bod, w, lambda c: V(c.x, c.y - 0.0, 0), wrap=True)
    # neck socket ring
    loft(mb, V(0, 0.008, 2.148), V(0, 0.008, 2.185), lambda t, th: lerp(0.052, 0.045, t), "skin", w, 20, 2,
         cap0=False, cap1=False)
    # Peter Pan collar, two rounded flaps meeting at the front
    for side in (1, -1):
        def col(u, v, side=side):
            dth = 0.07 + u * (math.pi - 0.07)  # angle from the front center, toward the back
            th = -math.pi / 2 + side * dth
            width = lerp(0.066, 0.052, min(1.0, dth / 1.6))
            if dth < 0.32:  # rounded front tip
                width *= math.sqrt(max(0.0, 1 - ((0.32 - dth) / 0.32) ** 2)) * 0.9 + 0.1
            z = 2.163 - width * v
            return bodice_point(th, z, 0.007 + 0.004 * v), in_region("collar", u, v)

        grid(mb, 26, 3, col, w, lambda c: V(c.x, c.y, 0.6))
    # buttons down the placket
    for z in (2.09, 2.0, 1.91, 1.82):
        p = bodice_point(-math.pi / 2, z, 0.0)
        loft(mb, p, p + V(0, -0.006, 0), lambda t, th: 0.008, "button", w, 10, 1)
    # name badge, pinned a little crooked
    th = -math.pi / 2 + 0.42
    p = bodice_point(th, 2.0, 0.004)
    n = V(math.cos(th), math.sin(th), 0).normalized()
    up = V(0, 0, 1)
    across = up.cross(n).normalized() * -1
    rot = Matrix.Rotation(math.radians(-7), 3, n)
    across, up = rot @ across, rot @ up
    bw, bh, bt = 0.075, 0.046, 0.004
    corners = [p + across * (sx * bw / 2) + up * (sy * bh / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    front = [c + n * bt for c in corners]
    uvs = [in_region("badge", 0, 0), in_region("badge", 1, 0), in_region("badge", 1, 1), in_region("badge", 0, 1)]
    mb.face([(mb.vert(c, w), uv) for c, uv in zip(front, uvs)], n)
    for a in range(4):
        b = (a + 1) % 4
        q = [(mb.vert(corners[a], w), in_region("button", 0, 0)), (mb.vert(corners[b], w), in_region("button", 1, 0)),
             (mb.vert(front[b], w), in_region("button", 1, 1)), (mb.vert(front[a], w), in_region("button", 0, 1))]
        mid = (corners[a] + corners[b]) / 2 - p
        mb.face(q, mid)
    photo = MB("BadgePhoto")
    x0, x1, y0, y1 = -0.5 + 0.04, -0.5 + 0.34, 0.5 - 0.93, 0.5 - 0.33
    pc = [p + n * (bt + 0.0006) + across * (x * bw) + up * (y * bh) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    photo.face([(photo.vert(c, w), uv) for c, uv in zip(pc, ((0, 0), (1, 0), (1, 1), (0, 1)))], n)
    return mb, photo


SKIRT = [  # z, center y, rx, ry
    (0.95, 0.0, 0.228, 0.192), (1.10, 0.0, 0.215, 0.180), (1.30, 0.004, 0.195, 0.160),
    (1.50, 0.006, 0.172, 0.135), (1.60, 0.004, 0.150, 0.118), (1.712, 0.0, 0.117, 0.087),
]


def pleat(th, z, k=1.0):
    a = lerp(0.010, 0.002, smooth(0.95, 1.6, z)) * k
    return a * math.sin(16 * th + 0.3) + 0.6 * a * math.sin(5 * th + 1.7) + 0.4 * a * math.sin(9 * th + 0.4)


def skirt_point(th, z, off=0.0, k=1.0):
    cy, rx, ry = table(SKIRT, z)
    r = pleat(th, z, k) + off
    return V((rx + r) * math.cos(th), cy + (ry + r) * math.sin(th), z)


def skirt_weights(p):
    """Below the hips the skirt follows the thighs a little, so legs swing inside it."""
    wl = 0.45 * smooth(1.45, 0.95, p.z)
    left = wl * min(1.0, max(0.0, (p.x + 0.04) / 0.08))
    out = {"LowerTorso": 1 - wl}
    if left > 0:
        out["LeftUpperLeg"] = left
    if wl - left > 0:
        out["RightUpperLeg"] = wl - left
    return out


def hem(th):
    return 0.95 + 0.012 * math.sin(9 * th + 0.4)


def build_lower_torso():
    mb = MB("LowerTorso")

    def sk(u, v, off=0.0):
        th = TAU * u
        z = lerp(hem(th), 1.712, v)
        return skirt_point(th, z, off), in_region("skirt", u, v)

    outer = grid(mb, 56, 18, sk, skirt_weights, lambda c: V(c.x, c.y, 0), wrap=True)
    inner = grid(mb, 56, 18, lambda u, v: (sk(u, v, -0.004)[0], in_region("lining", u, v)), skirt_weights,
                 lambda c: V(c.x, c.y, 0), wrap=True, flip=True)
    for i in range(56):  # hem thickness
        q = [outer[0][i], outer[0][i + 1], inner[0][i + 1], inner[0][i]]
        mb.face([(k, in_region("lining", 0.5, 0.5)) for k, _ in q], V(0, 0, -1))
    ellipsoid(mb, V(0, 0.005, 1.47), (0.14, 0.11, 0.1), "skin", rigid("LowerTorso"), 24, 12)
    # waistband and apron strings
    def band(u, v):
        return skirt_point(TAU * u, lerp(1.695, 1.745, v), 0.007, 0.0), in_region("belt", u, v)

    grid(mb, 48, 2, band, rigid("LowerTorso"), lambda c: V(c.x, c.y, 0), wrap=True)
    # the half apron, rounded at the bottom corners, with its pocket
    span = 1.05

    def apron(u, v):
        th = -math.pi / 2 + lerp(-span, span, u)
        s = abs(lerp(-1, 1, u))
        bottom = 1.03 + (0.08 * (1 - math.sqrt(max(0.0, 1 - ((s - 0.8) / 0.2) ** 2))) if s > 0.8 else 0.0)
        z = lerp(bottom, 1.70, v)
        p = skirt_point(th, z, 0.007, 0.5)
        p += V(math.cos(th), math.sin(th), 0) * (0.003 * math.sin(30 * th))
        return p, in_region("apron", u, v)

    grid(mb, 36, 18, apron, skirt_weights, lambda c: V(c.x, c.y, 0))
    pc = -math.pi / 2 + 0.26

    def pocket(u, v):
        th = pc + lerp(-0.3, 0.3, u)
        z = lerp(1.30, 1.44, v)
        return skirt_point(th, z, 0.011, 0.5), in_region("pocket", u, v)

    grid(mb, 8, 4, pocket, skirt_weights, lambda c: V(c.x, c.y, 0))
    # the apron bow at the back
    back = skirt_point(math.pi / 2, 1.72, 0.012, 0.0)
    for sx in (-1, 1):
        rot = Matrix.Rotation(math.radians(30 * sx), 3, "Y")
        ellipsoid(mb, back + V(0.045 * sx, 0.012, 0.0), (0.045, 0.014, 0.026), "belt", rigid("LowerTorso"), 12, 6,
                  rot=rot)
        tail_top = back + V(0.02 * sx, 0.012, -0.01)
        loft(mb, tail_top, tail_top + V(0.03 * sx, 0.02, -0.17), lambda t, th: lerp(0.012, 0.016, t), "belt",
             rigid("LowerTorso"), 8, 6)
    return mb


# ================================================================ limbs
def limb_radius(r0, r1, bulge=0.0, back_bulge=0.0, round_ends=True):
    def r(t, th):
        base = lerp(r0, r1, t) + bulge * math.sin(math.pi * t)
        base += back_bulge * g((t - 0.3) / 0.2) * max(0.0, math.sin(th))  # calf at the back (+Y side)
        if round_ends:
            e = min(t, 1 - t)
            base *= math.sqrt(max(0.0, 1 - max(0.0, 0.08 - e) ** 2 / 0.0064)) if e < 0.08 else 1.0
        return base
    return r


def build_arm(side, sx):
    up, lo, hd = MB(f"{side}UpperArm"), MB(f"{side}LowerArm"), MB(f"{side}Hand")
    sh, el, wr = J[f"shoulder_{side}"], J[f"elbow_{side}"], J[f"wrist_{side}"]
    wu, wl, wh = rigid(f"{side}UpperArm"), rigid(f"{side}LowerArm"), rigid(f"{side}Hand")
    ellipsoid(up, sh, (0.05, 0.05, 0.05), "joint", wu, 16, 10)
    loft(up, sh, el, limb_radius(0.05, 0.039, 0.004), "skin", wu, 16, 12, 0.06, 0.9)

    # puffed short sleeve, gathered at the shoulder, with a cuff and a lining
    def puff(t, th):
        # a round dome gathered at the shoulder seam, a soft puff, then the cuff
        if t < 0.02:
            base = 0.058 * math.sqrt(max(0.0, 1 - ((0.02 - t) / 0.15) ** 2))
        else:
            base = table([(0.02, 0.058), (0.2, 0.059), (0.36, 0.056), (0.42, 0.055)], t)[0]
        return base + 0.0025 * math.sin(9 * th) * smooth(0.42, 0.1, t) * smooth(-0.13, -0.05, t)

    loft(up, sh, el, puff, "sleeve", wu, 28, 24, -0.122, 0.42, cap0=True, cap1=False,
         uv_v=lambda t: (t + 0.13) / 0.55, cap_lift=0.17)
    loft(up, sh, el, lambda t, th: 0.051, "lining", wu, 28, 1, 0.36, 0.42, cap0=False, cap1=False)
    ellipsoid(lo, el, (0.043, 0.043, 0.043), "joint", wl, 14, 8)
    loft(lo, el, wr, limb_radius(0.039, 0.029, 0.005), "skin", wl, 14, 12, 0.1, 0.92)
    ellipsoid(hd, wr, (0.03, 0.03, 0.03), "joint", wh, 12, 8)
    build_hand(hd, side, sx, wr, wh)
    return up, lo, hd


HAND = [  # t, half width (across the palm), half thickness
    (0.0, 0.022, 0.017), (0.12, 0.030, 0.017), (0.35, 0.038, 0.016), (0.52, 0.040, 0.014),
    (0.75, 0.036, 0.011), (0.92, 0.030, 0.010), (1.0, 0.016, 0.008),
]


def build_hand(mb, side, sx, wr, wh):
    """A mitten hand: fingers moulded together with shallow grooves, the thumb lying along it."""
    along = V(0.004 * sx, -0.004, -1.0).normalized()
    across = V(0, 1, 0)  # index at the front (-Y), pinky at the back
    thick = V(sx, 0, 0)  # back of the hand faces outward, palm toward the thigh
    L = 0.2

    def pt(u, v):
        t, psi = v, TAU * u
        hw, ht = table(HAND, t)
        s = math.cos(psi)
        length = 1.0
        if t > 0.55:
            length = 1 - 0.12 * (s + 0.15) ** 2 - 0.06 * max(0.0, s)
        dist = 0.02 + L * (0.55 + (t - 0.55) * length) if t > 0.55 else 0.02 + L * t
        c = wr + along * dist - thick * (0.03 * smooth(0.55, 1.0, t) ** 2)
        groove = 0.0
        if t > 0.55:
            groove = sum(0.0025 * g((s - k) / 0.08) for k in (-0.5, 0.0, 0.5)) * abs(math.sin(psi))
        p = c + across * (hw * s) + thick * ((ht - groove) * math.sin(psi))
        return p, in_region("skin", u, v)

    def out(c):
        d = c - wr
        return d - along * d.dot(along)

    rows = grid(mb, 18, 14, pt, wh, out, wrap=True)
    tip = wr + along * (0.02 + L * 1.0) - thick * 0.03
    fan(mb, rows[-1], tip, in_region("skin", 0.5, 1.0), wh, along)
    fan(mb, rows[0], wr + along * 0.012, in_region("skin", 0.5, 0.0), wh, -along)
    base = wr + along * 0.07 - across * 0.03 - thick * 0.006
    d = (along * 0.75 - across * 0.45 - thick * 0.25).normalized()
    loft(mb, base, base + d * 0.075, lambda t, th: lerp(0.0135, 0.0095, t), "skin", wh, 10, 6)


FOOT = [  # t, center height, half width, half height
    (0.0, 0.050, 0.032, 0.045), (0.12, 0.055, 0.040, 0.050), (0.35, 0.060, 0.042, 0.055),
    (0.62, 0.042, 0.047, 0.038), (0.85, 0.032, 0.042, 0.028), (1.0, 0.026, 0.020, 0.018),
]


def build_leg(side, sx):
    up, lo, ft = MB(f"{side}UpperLeg"), MB(f"{side}LowerLeg"), MB(f"{side}Foot")
    hp, kn, an = J[f"hip_{side}"], J[f"knee_{side}"], J[f"ankle_{side}"]
    wu, wl, wf = rigid(f"{side}UpperLeg"), rigid(f"{side}LowerLeg"), rigid(f"{side}Foot")
    ellipsoid(up, hp, (0.07, 0.07, 0.07), "joint", wu, 16, 10)
    loft(up, hp, kn, limb_radius(0.08, 0.054, 0.007), "skin", wu, 18, 14, 0.08, 0.93)
    ellipsoid(lo, kn, (0.056, 0.056, 0.056), "joint", wl, 16, 10)
    loft(lo, kn, an, limb_radius(0.052, 0.034, 0.002, 0.01), "skin", wl, 16, 16, 0.09, 0.93)
    ellipsoid(ft, an, (0.036, 0.036, 0.036), "joint", wf, 12, 8)
    # a moulded flat shoe
    fwd = V(0.01 * sx, -1, 0).normalized()
    heel = V(an.x, an.y + 0.065, 0)

    def pt(u, v):
        t, psi = v, TAU * u
        cz, hw, hh = table(FOOT, t)
        c = heel + fwd * (0.265 * t)
        p = c + V(sx * hw * math.cos(psi), 0, cz + hh * math.sin(psi))
        p.z = max(0.006, p.z)
        return p, in_region("shoe", u, 1 - min(1.0, (p.z - 0.006) / 0.11))

    def out(c):
        d = c - heel
        a = d - fwd * d.dot(fwd)
        return V(a.x, a.y, a.z - 0.045)

    rows = grid(ft, 20, 12, pt, wf, out, wrap=True)
    fan(ft, rows[0], heel + V(0, 0.012, 0.05), in_region("shoe", 0.5, 0.5), wf, -fwd)
    fan(ft, rows[-1], heel + fwd * 0.272 + V(0, 0, 0.026), in_region("shoe", 0.5, 0.5), wf, fwd)
    # skin shows where the shoe opens over the instep
    for k, (ids, uvs) in enumerate(zip(ft.faces, ft.fuv)):
        ctr = sum((ft.co[i] for i in ids), Vector()) / len(ids)
        if ctr.z > 0.088 and (ctr - heel).dot(fwd) < 0.15:
            ft.fuv[k] = [in_region("skin", (j + 1) / 5, 0.5) for j in range(len(ids))]
    return up, lo, ft


# ================================================================ rig, materials
def build_armature():
    arm = bpy.data.armatures.new("StandIn_Rig")
    ob = bpy.data.objects.new("StandIn_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, (joint, parent) in S.BONES.items():
        eb = arm.edit_bones.new(name)
        eb.head = J[joint]
        eb.tail = J[joint] + V(0, 0, 0.12 if name in ("Root", "HumanoidRootNode", "LowerTorso", "UpperTorso", "Head")
                                else 0.08)
        eb.roll = 0.0
        ebs[name] = eb
    for name, (joint, parent) in S.BONES.items():
        if parent:
            ebs[name].parent = ebs[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def make_material(name, prefix):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(fname, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = "Non-Color"
        return n

    col = tex(f"{prefix}_color.png" if prefix != "badge_photo" else "badge_photo.png", False)
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    if prefix == "badge_photo":
        bsdf.inputs["Roughness"].default_value = 0.35
        return m
    rough = tex(f"{prefix}_roughness.png", True)
    nrm = tex(f"{prefix}_normal.png", True)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def skin(ob, mb, rig):
    groups = {name: ob.vertex_groups.new(name=name) for name in S.BONES}
    for vi, ws in enumerate(mb.w):
        tot = sum(ws.values())
        for b, w in ws.items():
            if w / tot > 0.01:
                groups[b].add([vi], w / tot, "REPLACE")
    ob.parent = rig
    ob.modifiers.new("Armature", "ARMATURE").object = rig


def main(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    atlas = make_material("M_StandIn", "standin")
    photo_mat = make_material("M_BadgePhoto", "badge_photo")
    parts = [build_head()]
    ut, photo = build_upper_torso()
    parts += [ut, build_lower_torso()]
    for side, sx in S.SIDES:
        parts += list(build_arm(side, sx)) + list(build_leg(side, sx))
    rig = build_armature()
    total = 0
    for mb in parts + [photo]:
        ob = mb.build(photo_mat if mb is photo else atlas)
        skin(ob, mb, rig)
        total += mb.tris()
        print(f"{mb.name:14s} tris {mb.tris():6d}")
    print("total tris", total)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "stand_in.blend"))
