#!/usr/bin/env python3
"""Builds the Stand-in, the floor-2 monster: an 8.3 ft faceless shop mannequin in a faded
Orange Court uniform, as 15 Roblox R15 body parts plus her hair and a swappable badge photo,
with an R15 rig. Saves a .blend.

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


# ================================================================ head, neck and hair
HEAD_R = (0.097, 0.11, 0.14)
WIG_R = (HEAD_R[0] + 0.01, HEAD_R[1] + 0.01, HEAD_R[2] + 0.011)


def head_shape(p, d):
    """A smooth egg that narrows to a soft jaw and chin. No face at all."""
    z = p.z
    taper = 1 - 0.22 * smooth(-0.03, -0.14, z)
    chin = 0.012 * smooth(-0.05, -0.14, z) * smooth(0.2, -0.6, d.y)
    return V(p.x * taper, p.y * taper - chin, z)


def polar(phi, lam):
    return V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))


def scalp(d, extra=0.0):
    """Point on the wig cap, a shell just over the head, in direction d from the head center."""
    return J["head_c"] + V(d.x * (WIG_R[0] + extra), d.y * (WIG_R[1] + extra), d.z * (WIG_R[2] + extra))


def hairline(phi):
    """Polar latitude (radians) where the wig ends, by azimuth (front is -Y)."""
    front = max(0.0, -math.sin(phi))
    back = max(0.0, math.sin(phi))
    return math.radians(-5 + 43 * front ** 1.2 - 25 * back)


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
        q = p - J["head_c"]
        r = (WIG_R[0] + 0.012, WIG_R[1] + 0.012, WIG_R[2] + 0.012)
        k = (q.x / r[0]) ** 2 + (q.y / r[1]) ** 2 + (q.z / r[2]) ** 2
        if k < 1:
            p = J["head_c"] + q / math.sqrt(k)
        # neck
        if 2.1 < p.z < 2.32:
            h = V(p.x, p.y, 0)
            if h.length < 0.066:
                p = V(*(h.normalized() * 0.066)[:2], p.z) if h.length > 1e-6 else V(0, 0.066, p.z)
        # shoulders, puffed by the sleeves
        for side, sx in S.SIDES:
            c = J[f"shoulder_{side}"] + V(0, 0, 0.02)
            q = p - c
            if q.length < 0.095:
                p = c + q.normalized() * 0.095
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


def drape(p, z_end, d=None, step=0.01):
    """Lets a strand fall from p to z_end, sliding over the head, neck, shoulders and back."""
    if d is None:
        nrm = (p - J["head_c"]).normalized()
        d = (V(0, 0, -1) - nrm * nrm.dot(V(0, 0, -1))).normalized()
    pts = [p]
    while p.z > z_end and len(pts) < 400:
        d = (d * 0.75 + V(0, 0, -1) * 0.25).normalized()
        q = collide(p + d * step)
        d = (q - p).normalized()
        p = q
        pts.append(p)
    return pts


def resample(pts, n):
    """n + 1 points evenly spaced along a polyline."""
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    out = []
    for k in range(n + 1):
        s = acc[-1] * k / n
        j = next((m for m in range(1, len(acc)) if acc[m] >= s), len(acc) - 1)
        f = (s - acc[j - 1]) / max(1e-9, acc[j] - acc[j - 1])
        out.append(pts[j - 1].lerp(pts[j], f))
    return out


def build_head():
    mb = MB("Head")
    hw = rigid("Head")
    ellipsoid(mb, J["head_c"], HEAD_R, "skin", hw, 36, 24, disp=head_shape)
    # short seamed neck, with the metal connector at the back
    loft(mb, V(0, 0.005, 2.14), V(0, 0.004, 2.29), lambda t, th: 0.054 - 0.0025 * g((t - 0.33) / 0.04), "skin", hw,
         20, 16, cap0=False, cap1=False)
    loft(mb, V(0, 0.05, 2.19), V(0, 0.066, 2.19), lambda t, th: 0.011, "metal", hw, 10, 1)
    return mb


LOCKS = 12  # per side, in the top layer; the layer under it has one fewer, filling the gaps
LOCK_GAP = math.radians((177 - 62) / (LOCKS - 1))
LOCK_SIDES = 6


def build_lock(mb, pts, layer, col):
    """One clump of hair along pts: a flattened ribbon, curved to hug what it lies on, narrow at
    the part, tapering to a point at the tip."""
    n, m = len(pts) - 1, LOCK_SIDES
    rows, centers, prev_b = [], [], None
    for k, p in enumerate(pts):
        t = k / n
        T = (pts[min(k + 1, n)] - pts[max(k - 1, 0)]).normalized()
        flat = V(p.x, p.y, 0)
        reach = min(0.03, max(0.013, flat.length * LOCK_GAP))  # wide enough to overlap its neighbours
        flat = flat.normalized() if flat.length > 1e-6 else V(0, 1, 0)
        N = flat.lerp((p - J["head_c"]).normalized(), smooth(2.18, 2.3, p.z))
        N = (N - T * N.dot(T)).normalized()
        B = T.cross(N).normalized()
        if prev_b is not None and B.dot(prev_b) < 0:
            B = -B
        prev_b = B
        hw = reach * (0.4 + 0.6 * smooth(0.0, 0.2, t)) * (1 - 0.9 * smooth(0.55, 1.0, t) ** 1.4)
        ht = 0.0075 * (1 - 0.6 * smooth(0.6, 1.0, t))
        c = p + N * (ht + layer)
        ring = []
        for j in range(m):
            psi = TAU * j / m
            x, y = math.cos(psi), math.sin(psi)
            q = c + B * (x * hw) + N * (y * ht - 0.25 * hw * x * x)
            ring.append((mb.vert(q, hair_weights), in_region("hair", (col + 0.08 + 0.42 * (x + 1)) / 4, 1 - t)))
        rows.append(ring)
        centers.append(c)
    for k in range(n):
        for j in range(m):
            q = [rows[k][j], rows[k][(j + 1) % m], rows[k + 1][(j + 1) % m], rows[k + 1][j]]
            ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
            mb.face(q, ctr - (centers[k] + centers[k + 1]) / 2)
    T0, T1 = (pts[1] - pts[0]).normalized(), (pts[-1] - pts[-2]).normalized()
    fan(mb, rows[0], centers[0] - T0 * 0.004, in_region("hair", (col + 0.5) / 4, 1.0), hair_weights, -T0)
    fan(mb, rows[-1], centers[-1] + T1 * 0.006, in_region("hair", (col + 0.5) / 4, 0.0), hair_weights, T1)


def build_hair():
    """A neat wig: a cap with a center part, locks that start at the part and fall in front of
    the shoulders and down the back, over a dark under-layer that hides any gaps between them."""
    mb = MB("Hair")
    hw = rigid("Head")

    def cap(u, v):
        phi = TAU * u
        lam = math.pi / 2 - v * (math.pi / 2 - hairline(phi))
        return scalp(polar(phi, lam)), in_region("scalp", u, 1 - v)

    grid(mb, 36, 10, cap, hw, lambda q: q - J["head_c"], wrap=True)

    # the under-layer, behind the shoulders: two-sided, so it also reads from the front
    ncol, nrow = 22, 12
    a0, a1 = math.radians(10), math.radians(170)
    outer, inner = {}, {}
    for i in range(ncol + 1):
        phi = lerp(a0, a1, i / ncol)
        start = scalp(polar(phi, hairline(phi)), 0.002)
        z_end = lerp(1.84, 1.92, abs(math.cos(phi)))
        for k, p in enumerate(resample(drape(start, z_end), nrow)):
            h = V(p.x, p.y, 0)
            radial = (p - J["head_c"]).normalized() if p.z > 2.25 else h.normalized()
            uv = in_region("hair_under", i / ncol, 1 - k / nrow)
            outer[i, k] = (mb.vert(p, hair_weights), uv)
            inner[i, k] = (mb.vert(p - radial * 0.006, hair_weights), uv)

    def axis_out(c):
        return (c - J["head_c"]) if c.z > 2.25 else V(c.x, c.y, 0)

    for i in range(ncol):
        for k in range(nrow):
            for side, sign in ((outer, 1), (inner, -1)):
                q = [side[i, k], side[i + 1, k], side[i + 1, k + 1], side[i, k + 1]]
                ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
                mb.face(q, axis_out(ctr) * sign)
    for i in range(ncol):
        mb.face([outer[i, nrow], outer[i + 1, nrow], inner[i + 1, nrow], inner[i, nrow]], V(0, 0, -1))

    # the locks: each starts on the part (front ones at the forehead, back ones at the crown),
    # runs over the cap to the side of the head and falls from there. Two layers: the lower one
    # sits between the locks of the top one.
    for layer, count in ((0, LOCKS - 1), (1, LOCKS)):
        for sgn in (1, -1):
            for i in range(count):
                f = (i + 0.5 * (layer == 0)) / (LOCKS - 1)
                fall = math.radians(62 + 115 * f ** 1.2)  # where it leaves the head, from the front
                alpha = math.radians(lerp(50, 128, f))  # where it starts on the part, from the forehead
                root = V(sgn * 0.02, -math.cos(alpha), math.sin(alpha)).normalized()
                leave = V(sgn * math.sin(fall), -math.cos(fall), -0.12).normalized()
                pts = [scalp(root.lerp(leave, smooth(0, 1, k / 12)).normalized(), lerp(0.002, 0.014, k / 12))
                       for k in range(13)]
                z_end = lerp(1.93, 1.79, smooth(0.2, 1.0, f)) + rng.uniform(-0.015, 0.015) + 0.02 * (layer == 0)
                pts += drape(pts[-1], z_end, (pts[-1] - pts[-2]).normalized())[1:]
                build_lock(mb, resample(pts, 12), 0.0035 * layer + 0.001 * (i % 2), (i + 2 * layer + (sgn > 0)) % 4)
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
    across = up.cross(n).normalized()  # toward the viewer's right, so the text reads
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
# radii by distance (m) along the limb from its top joint: outward, inward, front, back
UPPER_ARM = [
    (0.00, 0.060, 0.055, 0.060, 0.060), (0.10, 0.061, 0.055, 0.059, 0.062), (0.21, 0.055, 0.052, 0.055, 0.056),
    (0.32, 0.053, 0.049, 0.055, 0.053), (0.42, 0.048, 0.046, 0.049, 0.048), (0.50, 0.044, 0.043, 0.042, 0.048),
]
FOREARM = [  # from the elbow; the wrist is wider front to back, the way the palm faces
    (0.00, 0.044, 0.043, 0.042, 0.048), (0.07, 0.048, 0.047, 0.046, 0.048), (0.15, 0.044, 0.043, 0.042, 0.042),
    (0.26, 0.036, 0.035, 0.037, 0.035), (0.33, 0.029, 0.028, 0.035, 0.034), (0.36, 0.027, 0.027, 0.034, 0.033),
]
THIGH = [
    (0.00, 0.080, 0.090, 0.100, 0.105), (0.15, 0.092, 0.098, 0.102, 0.104), (0.33, 0.095, 0.087, 0.094, 0.090),
    (0.50, 0.082, 0.076, 0.082, 0.074), (0.60, 0.070, 0.067, 0.074, 0.064), (0.665, 0.062, 0.060, 0.070, 0.058),
]
SHIN = [  # from the knee; the calf swells at the back and inside
    (0.00, 0.062, 0.060, 0.070, 0.058), (0.06, 0.060, 0.059, 0.060, 0.064), (0.17, 0.070, 0.077, 0.058, 0.084),
    (0.30, 0.063, 0.068, 0.052, 0.074), (0.44, 0.047, 0.049, 0.044, 0.050), (0.55, 0.038, 0.038, 0.038, 0.040),
    (0.62, 0.036, 0.036, 0.036, 0.040),
]


def seam(d, at, depth=0.0016, width=0.0022):
    """A fine line cut around a limb, where the shop would take the part off."""
    return depth * g((d - at) / width)


def stations(d0, d1, step, dense=(), seams=()):
    """Where a limb's rings go: every step, twice as often within 2 steps of the dense points
    (bending joints), and bunched tightly around seam lines."""
    n = max(1, round((d1 - d0) / step))
    ds = [d0 + (d1 - d0) * k / n for k in range(n + 1)]
    for c in dense:
        ds += [c + step / 2 * k for k in range(-4, 5)]
    for c in seams:
        ds += [c + o for o in (-0.007, -0.0035, 0.0, 0.0035, 0.007)]
    ds = sorted(d for d in ds if d0 <= d <= d1)
    out = [ds[0]]
    for d in ds[1:]:
        if d - out[-1] > 0.0015:
            out.append(d)
    return out


def limb(path, ds, radii, owner, weights, sx, n_around=20):
    """A smooth limb along the polyline path, with rings at the distances ds (negative ones go
    back past the first point, for a rounded top). radii(d) -> (outward, inward, front, back).
    owner(d) picks the part each stretch belongs to; the ring where it changes is built in both
    parts, with the same blended weights(d), so the joint bends without a crack."""
    segs = list(zip(path, path[1:]))
    lens = [(b - a).length for a, b in segs]
    starts = [sum(lens[:k]) for k in range(len(segs))]
    dirs = [(b - a).normalized() for a, b in segs]

    def frame_at(d):
        k = next((k for k in range(len(segs)) if d < starts[k] + lens[k]), len(segs) - 1)
        c = segs[k][0] + dirs[k] * (d - starts[k])
        w = dirs[0]
        for j in range(1, len(segs)):  # turn smoothly through the joints
            w = w.lerp(dirs[j], smooth(starts[j] - 0.06, starts[j] + 0.06, d))
        w = w.normalized()
        out = (V(sx, 0, 0) - w * w.dot(V(sx, 0, 0))).normalized()
        fwd = w.cross(out)
        if fwd.y > 0:
            fwd = -fwd
        return c, w, out, fwd

    def ring_points(d):
        c, w, out, fwd = frame_at(d)
        ro, ri, rf, rb = radii(d)
        pts = []
        for j in range(n_around + 1):
            psi = TAU * j / n_around
            cs, sn = math.cos(psi), math.sin(psi)
            pts.append(c + out * (cs * (ro if cs > 0 else ri)) + fwd * (sn * (rf if sn > 0 else rb)))
        return c, w, pts

    rings = [ring_points(d) for d in ds]
    span = ds[-1] - ds[0]
    built = {}

    def ring(mb, r):
        if (mb.name, r) not in built:
            wts = weights(ds[r])
            built[mb.name, r] = [(mb.vert(p, wts), in_region("skin", j / n_around, (ds[r] - ds[0]) / span))
                                 for j, p in enumerate(rings[r][2])]
        return built[mb.name, r]

    for r in range(len(ds) - 1):
        mb = owner((ds[r] + ds[r + 1]) / 2)
        a, b = ring(mb, r), ring(mb, r + 1)
        axis = (rings[r][0] + rings[r + 1][0]) / 2
        for j in range(n_around):
            q = [a[j], a[j + 1], b[j + 1], b[j]]
            ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
            mb.face(q, ctr - axis)
    for r, sign, mb in ((0, -1, owner(ds[0])), (len(ds) - 1, 1, owner(ds[-1]))):
        c, w, _ = rings[r]
        tip = c + w * sign * (0.002 if sign < 0 else -0.004)  # rounded top; the bottom end is tucked in
        fan(mb, ring(mb, r), tip, in_region("skin", 0.5, 0.5), weights(ds[r]), w * sign)


def build_arm(side, sx):
    up, lo, hd = MB(f"{side}UpperArm"), MB(f"{side}LowerArm"), MB(f"{side}Hand")
    sh, el, wr = J[f"shoulder_{side}"], J[f"elbow_{side}"], J[f"wrist_{side}"]
    Lu, Lf = (el - sh).length, (wr - el).length
    arm_seam = 0.205  # where the arm comes off, just below the sleeve
    end = Lu + Lf - 0.002  # the forearm stops at the wrist seam
    upper, lower = f"{side}UpperArm", f"{side}LowerArm"

    def radii(d):
        r = table(UPPER_ARM, d) if d < Lu else table(FOREARM, d - Lu)
        k = math.sqrt(max(0.0, 1 - (d / 0.05) ** 2)) if d < 0 else 1.0  # rounded shoulder, inside the sleeve
        cut = seam(d, arm_seam) + 0.001 * smooth(end - 0.004, end, d)  # and a rounded rim at the wrist
        return tuple(x * k - cut for x in r)

    def weights(d):
        wl = smooth(-0.07, 0.07, d - Lu)
        return {upper: 1 - wl, lower: wl}

    ds = stations(-0.048, end, 0.03, dense=(Lu, -0.02), seams=(arm_seam,))
    limb([sh, el, wr], ds, radii, lambda d: up if d < Lu else lo, weights, sx)

    # puffed short sleeve, gathered at the shoulder, with a cuff and a lining
    wu = rigid(upper)

    def puff(t, th):
        d = t * Lu
        if d < 0.008:  # a round dome over the shoulder
            base = 0.072 * math.sqrt(max(0.0, 1 - ((0.008 - d) / 0.066) ** 2))
        else:
            base = table([(0.008, 0.072), (0.08, 0.073), (0.142, 0.070), (0.166, 0.069)], d)[0]
        return base + 0.0012 * math.sin(9 * th) * smooth(0.166, 0.04, d) * smooth(-0.058, -0.03, d)

    loft(up, sh, el, puff, "sleeve", wu, 28, 24, -0.055 / Lu, 0.166 / Lu, cap0=True, cap1=False,
         uv_v=lambda t: (t * Lu + 0.058) / 0.224, cap_lift=0.14)
    loft(up, sh, el, lambda t, th: 0.064, "lining", wu, 28, 1, 0.142 / Lu, 0.166 / Lu, cap0=False, cap1=False)
    build_hand(hd, side, sx, wr, (wr - el).normalized())
    return up, lo, hd


HAND = [  # t, half width (across the palm), half thickness
    (0.00, 0.032, 0.0245), (0.06, 0.031, 0.022), (0.15, 0.037, 0.021), (0.28, 0.045, 0.0195), (0.45, 0.048, 0.018),
    (0.55, 0.047, 0.0145), (0.75, 0.043, 0.012), (0.90, 0.037, 0.0105), (0.97, 0.030, 0.0085), (1.0, 0.014, 0.0045),
]
FINGERS = (-0.5, 0.0, 0.5)  # where the grooves between the four fingers run, across the hand


def build_hand(mb, side, sx, wr, along):
    """A shop-mannequin hand: the fingers moulded together, with fine grooves between them and
    gently curled, and the thumb resting against the index finger. It plugs into the wrist."""
    wh = rigid(f"{side}Hand")
    across = (V(0, -1, 0) - along * along.dot(V(0, -1, 0))).normalized()  # toward the index finger
    back = along.cross(across).normalized()
    if back.x * sx < 0:
        back = -back  # the back of the hand faces out, the palm toward the thigh
    palm = -back
    L = 0.215
    # the plug that sits in the end of the forearm
    loft(mb, wr - along * 0.018, wr + along * 0.004,
         lambda t, th: 1 / math.sqrt((math.cos(th) / 0.025) ** 2 + (math.sin(th) / 0.0325) ** 2), "skin", wh, 16, 3,
         cap0=False, cap1=False)

    def length(s):  # s = -1 index side .. 1 little finger side
        return 1.0 - 0.05 * (s + 0.25) ** 2 - 0.07 * max(0.0, s) ** 2 - sum(0.02 * g((s - k) / 0.06) for k in FINGERS)

    def pt(u, v):
        t, psi = v, TAU * u
        hw, ht = table(HAND, t)
        s, c = math.cos(psi), math.sin(psi)
        tt = t if t <= 0.55 else 0.55 + (t - 0.55) * length(s)
        grooves = sum(0.003 * g((s - k) / 0.07) for k in FINGERS) * smooth(0.5, 0.6, t)
        knuckles = 0.002 * sum(g((s - k) / 0.15) for k in (-0.75, -0.25, 0.25, 0.75)) * g((t - 0.47) / 0.04)
        thick = (ht - grooves * abs(c)) * c + (knuckles if c > 0 else 0.0)
        center = wr + along * (0.002 + L * tt) + palm * (0.045 * smooth(0.45, 1.0, t) ** 2)
        return center - across * (hw * s) + back * thick, in_region("skin", u, v)

    def out(c):
        d = c - wr
        return d - along * d.dot(along)

    rows = grid(mb, 24, 18, pt, wh, out, wrap=True)
    fan(mb, rows[-1], wr + along * (0.002 + L * 0.99) + palm * 0.045, in_region("skin", 0.5, 1.0), wh, along)
    fan(mb, rows[0], wr - along * 0.004, in_region("skin", 0.5, 0.0), wh, -along)
    # the ball of the thumb, and the thumb in two pieces lying along the index finger
    ellipsoid(mb, wr + along * 0.06 + across * 0.018 + palm * 0.008, (0.014, 0.018, 0.03), "skin", wh, 12, 8)
    base = wr + along * 0.05 + across * 0.026 + palm * 0.006
    d1 = (along * 0.78 + across * 0.35 + palm * 0.35).normalized()
    mid = base + d1 * 0.055
    d2 = (along * 0.9 + across * 0.1 + palm * 0.35).normalized()
    loft(mb, base, mid, lambda t, th: lerp(0.0145, 0.0125, t), "skin", wh, 12, 4, cap0=False, cap1=False)
    ellipsoid(mb, mid, (0.0125, 0.0125, 0.0125), "skin", wh, 12, 6)
    loft(mb, mid, mid + d2 * 0.045, lambda t, th: lerp(0.0125, 0.0095, t), "skin", wh, 12, 5, cap0=False)


FOOT = [  # t (heel to toe), center height, half width, half height
    (0.00, 0.040, 0.007, 0.020), (0.03, 0.044, 0.025, 0.036), (0.08, 0.049, 0.035, 0.045),
    (0.18, 0.052, 0.039, 0.050), (0.33, 0.046, 0.043, 0.044), (0.52, 0.035, 0.047, 0.034),
    (0.70, 0.028, 0.046, 0.027), (0.86, 0.022, 0.040, 0.021), (0.95, 0.018, 0.030, 0.016), (1.0, 0.014, 0.011, 0.009),
]


def build_leg(side, sx):
    up, lo, ft = MB(f"{side}UpperLeg"), MB(f"{side}LowerLeg"), MB(f"{side}Foot")
    hp, kn, an = J[f"hip_{side}"], J[f"knee_{side}"], J[f"ankle_{side}"]
    Lt, Ls = (kn - hp).length, (an - kn).length
    end = Lt + Ls * (kn.z - 0.135) / (kn.z - an.z)  # the shin stops at the ankle seam
    upper, lower = f"{side}UpperLeg", f"{side}LowerLeg"

    def radii(d):
        r = table(THIGH, d) if d < Lt else table(SHIN, d - Lt)
        k = math.sqrt(max(0.0, 1 - (d / 0.1) ** 2)) if d < 0 else 1.0  # rounded hip, under the skirt
        lip = 0.001 * smooth(end - 0.004, end, d)
        return tuple(x * k - lip for x in r)

    def weights(d):
        wl = smooth(-0.075, 0.075, d - Lt)
        return {upper: 1 - wl, lower: wl}

    ds = stations(-0.096, end, 0.035, dense=(Lt, -0.04))
    limb([hp, kn, an], ds, radii, lambda d: up if d < Lt else lo, weights, sx, 22)
    build_foot(ft, side, sx, an)
    return up, lo, ft


def build_foot(ft, side, sx, an):
    """The foot, in a Mary Jane flat: a leather shell with a strap and button, the instep bare."""
    wf = rigid(f"{side}Foot")
    # the plug that sits in the end of the shin
    loft(ft, V(an.x, an.y, 0.16), V(an.x, an.y + 0.004, 0.06), lambda t, th: 0.0345 + 0.003 * max(0.0, -math.sin(th)),
         "skin", wf, 16, 4, cap0=False, cap1=False)
    fwd = V(0.05 * sx, -1, 0).normalized()  # toes turned out a little
    lat = V(0, 0, 1).cross(fwd).normalized()
    if lat.x * sx < 0:
        lat = -lat
    heel = V(an.x, an.y + 0.058, 0)
    LF = 0.31

    def at(t, psi, off=0.0, floor=0.006):
        cz, hw, hh = table(FOOT, t)
        p = heel + fwd * (LF * t) + lat * ((hw + off) * math.cos(psi)) + V(0, 0, cz + (hh + off) * math.sin(psi))
        p.z = max(floor, p.z)
        return p

    def out(c):
        d = c - heel
        a = d - fwd * d.dot(fwd)
        return V(a.x, a.y, a.z - 0.04)

    rows = grid(ft, 20, 20, lambda u, v: (at(v, TAU * u), in_region("skin", u, v)), wf, out, wrap=True)
    fan(ft, rows[0], heel + V(0, 0, 0.04) - fwd * 0.003, in_region("skin", 0.5, 0.0), wf, -fwd)
    fan(ft, rows[-1], heel + fwd * (LF + 0.003) + V(0, 0, 0.014), in_region("skin", 0.5, 1.0), wf, fwd)

    def cut(t):
        """Angle around the foot of the shoe's top edge (pi/2: closed over the top)."""
        cz, hw, hh = table(FOOT, t)
        top = lerp(0.068, 0.05, smooth(0.1, 0.3, t))
        a = math.asin(max(-1.0, min(1.0, (top - cz) / hh)))
        return lerp(a, math.pi / 2, smooth(0.42, 0.52, t))

    nc, nr, off = 22, 22, 0.0028
    shell = []
    for r in range(nr + 1):
        t, a = r / nr, cut(r / nr)
        shell.append([(ft.vert(at(t, lerp(math.pi - a, TAU + a, i / nc), off, 0.0), wf), (i / nc, t))
                      for i in range(nc + 1)])
    for r in range(nr):
        for i in range(nc):
            q = [shell[r][i], shell[r][i + 1], shell[r + 1][i + 1], shell[r + 1][i]]
            ctr = sum((ft.co[x] for x, _ in q), Vector()) / 4
            region = "sole" if ctr.z < 0.011 else "shoe"
            ft.face([(x, in_region(region, *uv)) for x, uv in q], out(ctr))
    fan(ft, [(x, in_region("shoe", *uv)) for x, uv in shell[0]], heel + V(0, 0, 0.04) - fwd * (0.003 + off),
        in_region("shoe", 0.5, 0.0), wf, -fwd)
    fan(ft, [(x, in_region("shoe", *uv)) for x, uv in shell[-1]], heel + fwd * (LF + 0.003 + off) + V(0, 0, 0.014),
        in_region("shoe", 0.5, 1.0), wf, fwd)
    # the thickness of the leather along the top edge, where the shoe is open
    for r in range(nr):
        t0, t1 = r / nr, (r + 1) / nr
        if cut(t0) > math.pi / 2 - 0.01:
            continue
        for psi_of in (lambda a: math.pi - a, lambda a: TAU + a):
            p0, p1 = psi_of(cut(t0)), psi_of(cut(t1))
            q = [at(t0, p0, off, 0.0), at(t1, p1, off, 0.0), at(t1, p1, 0.0), at(t0, p0, 0.0)]
            items = [(ft.vert(p, wf), in_region("shoe", k / 4, 0.5)) for k, p in enumerate(q)]
            ft.face(items, V(0, 0, 1))
    # the strap over the instep, buttoned on the outside
    ts, a = 0.40, cut(0.40)
    top = [[at(ts + dt, lerp(a - 0.05, math.pi - a + 0.05, i / 12), 0.0045) for i in range(13)] for dt in (-0.02, 0.02)]
    low = [[at(ts + dt, lerp(a - 0.05, math.pi - a + 0.05, i / 12), 0.0) for i in range(13)] for dt in (-0.02, 0.02)]
    for i in range(12):
        uv = [in_region("shoe", i / 12, 0.2), in_region("shoe", (i + 1) / 12, 0.2),
              in_region("shoe", (i + 1) / 12, 0.4), in_region("shoe", i / 12, 0.4)]
        q = [top[0][i], top[0][i + 1], top[1][i + 1], top[1][i]]
        ft.face([(ft.vert(p, wf), u) for p, u in zip(q, uv)], out(sum(q, Vector()) / 4))
        for k, sgn in ((0, -1), (1, 1)):
            q = [top[k][i], top[k][i + 1], low[k][i + 1], low[k][i]]
            ft.face([(ft.vert(p, wf), u) for p, u in zip(q, uv)], fwd * sgn)
    ellipsoid(ft, at(ts, a + 0.12, 0.007), (0.0055, 0.0055, 0.0055), "metal", wf, 10, 6)


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
    parts = [build_head(), build_hair()]
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
