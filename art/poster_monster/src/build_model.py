#!/usr/bin/env python3
"""Builds the poster monster in Blender and saves a .blend.

A gaunt 9 ft figure made of wet promo posters wrapped over a papier-mache core, with a
wadded-paper head behind a cracked droplet-mascot mask, rolled-poster fingers, loose
sheets that flap, packing tape and a torn-open chest. Includes the rig and skin weights.

Usage: python3 build_model.py OUT.blend
"""
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before bmesh/mathutils)
import bmesh
from mathutils import Matrix, Vector, noise
from mathutils.geometry import delaunay_2d_cdt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import skeleton as SK  # noqa: E402
from skeleton import J, V  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
rng = random.Random(1337)


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ================================================================ surfaces
class Tube:
    """Elliptic tube from p0 (bottom) to p1 (top); radii = [(t, rx, ry), ...]."""

    def __init__(self, p0, p1, radii, side=V(1, 0, 0)):
        self.p0, self.p1 = Vector(p0), Vector(p1)
        self.L = (self.p1 - self.p0).length
        self.W = (self.p1 - self.p0).normalized()
        self.U = (side - self.W * side.dot(self.W)).normalized()
        self.Vv = self.W.cross(self.U)
        self.radii = radii

    def r(self, t):
        rs = self.radii
        t = min(rs[-1][0], max(rs[0][0], t))
        for (t0, a0, b0), (t1, a1, b1) in zip(rs, rs[1:]):
            if t <= t1:
                k = smooth(t0, t1, t)
                return lerp(a0, a1, k), lerp(b0, b1, k)
        return rs[-1][1], rs[-1][2]

    def rmean(self, b):
        rx, ry = self.r(b / self.L)
        return 0.5 * (rx + ry)

    def center(self, b):
        return self.p0 + self.W * b

    def pos_theta(self, th, b, off):
        rx, ry = self.r(b / self.L)
        p = self.center(b) + self.U * ((rx + off) * math.cos(th)) + self.Vv * ((ry + off) * math.sin(th))
        n = (self.U * (math.cos(th) / rx) + self.Vv * (math.sin(th) / ry)).normalized()
        return p, n

    def pos(self, a, b, off):
        return self.pos_theta(a / self.rmean(b), b, off)

    def theta_b(self, p):
        b = (p - self.p0).dot(self.W)
        d = p - self.center(b)
        rx, ry = self.r(b / self.L)
        return math.atan2(d.dot(self.Vv) / ry, d.dot(self.U) / rx), b

    @property
    def circ(self):
        return 2 * math.pi * self.rmean(self.L * 0.5)


class Torso(Tube):
    """Vertical torso with an elliptic profile: (z, center y, rx, ry)."""
    PROFILE = [
        (1.16, 0.000, 0.080, 0.066), (1.21, 0.000, 0.128, 0.090), (1.27, 0.000, 0.146, 0.100),
        (1.34, 0.008, 0.150, 0.104), (1.42, 0.012, 0.128, 0.090), (1.50, 0.014, 0.104, 0.080),
        (1.58, 0.010, 0.112, 0.086), (1.66, 0.002, 0.136, 0.100), (1.74, -0.004, 0.152, 0.112),
        (1.82, -0.004, 0.160, 0.115), (1.89, 0.002, 0.164, 0.108), (1.95, 0.012, 0.150, 0.092),
        (2.00, 0.016, 0.110, 0.074), (2.05, 0.016, 0.050, 0.046),
    ]

    def __init__(self):
        self.z0, self.z1 = self.PROFILE[0][0], self.PROFILE[-1][0]
        self.L = self.z1 - self.z0
        self.p0, self.p1 = V(0, 0, self.z0), V(0, 0, self.z1)
        self.W, self.U, self.Vv = V(0, 0, 1), V(1, 0, 0), V(0, 1, 0)

    def prof(self, z):
        P = self.PROFILE
        z = min(P[-1][0], max(P[0][0], z))
        for a, b in zip(P, P[1:]):
            if z <= b[0]:
                k = (z - a[0]) / (b[0] - a[0])
                return lerp(a[1], b[1], k), lerp(a[2], b[2], k), lerp(a[3], b[3], k)
        return P[-1][1:]

    def r(self, t):
        _, rx, ry = self.prof(self.z0 + t * self.L)
        return rx, ry

    def center(self, b):
        return V(0, self.prof(self.z0 + b)[0], self.z0 + b)


class Blob:
    """Ellipsoid. Cards sit at the equator of a per-card frame, which avoids pole pinching."""

    def __init__(self, center, radii, frame=None):
        self.c = Vector(center)
        self.rad = Vector(radii)
        self.F = frame if frame is not None else Matrix.Identity(3)
        self.Rm = sum(radii) / 3

    def at_dir(self, d, off):
        d = d.normalized()
        pl = V(d.x * self.rad.x, d.y * self.rad.y, d.z * self.rad.z)
        n = (self.F @ V(d.x / self.rad.x, d.y / self.rad.y, d.z / self.rad.z)).normalized()
        return self.c + self.F @ pl + n * off, n

    def local_dir(self, world_dir):
        return (self.F.transposed() @ world_dir).normalized()

    def placer(self, R):
        def place(a, b, off):
            phi, lam = a / self.Rm, b / self.Rm
            d0 = V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))
            return self.at_dir(R @ d0, off)
        return place


def frame_to(d, twist=0.0):
    """Rotation taking +X to d (twisted about d), with +Z kept roughly up."""
    d = d.normalized()
    up = V(0, 0, 1) if abs(d.z) < 0.95 else V(0, 1, 0)
    y = up.cross(d).normalized()
    z = d.cross(y)
    return Matrix((d, y, z)).transposed() @ Matrix.Rotation(twist, 3, "X")


def basis(x, y, z):
    return Matrix((x, y, z)).transposed()


# ================================================================ mesh builder
class MB:
    """Collects verts/faces/uvs plus a skinning hint per vertex (part name or fixed weights)."""

    def __init__(self, name):
        self.name = name
        self.co, self.part, self.fixed = [], [], []
        self.faces, self.fuv = [], []

    def add_vert(self, co, part, fixed=None):
        co = Vector(co)
        self.co.append(co)
        self.part.append(part(co) if callable(part) else part)
        self.fixed.append(fixed(co) if callable(fixed) else fixed)
        return len(self.co) - 1

    def add_face(self, ids, uvs):
        self.faces.append(list(ids))
        self.fuv.append(list(uvs))

    def add_oriented(self, items, want):
        """items: [(vert, uv)]; flips the winding so the face normal follows `want`."""
        ids = [k for k, _ in items]
        uvs = [uv for _, uv in items]
        a, b, c = (self.co[i] for i in ids[:3])
        if (b - a).cross(c - a).dot(want) < 0:
            ids.reverse()
            uvs.reverse()
        self.add_face(ids, uvs)

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


# ================================================================ uv helpers
def poster_uv(cell, w, h, frac=(0.5, 1.0), focus=None):
    """A sub-rect of a poster cell with the card's aspect ratio (u0, v0, u1, v1)."""
    x0, y0, x1, y1 = C.cell_rect(cell)
    m = 8
    cw, ch = (x1 - x0) - 2 * m, (y1 - y0) - 2 * m
    asp = w / h
    hp = min(ch, cw / asp) * rng.uniform(*frac)
    wp = hp * asp
    if focus:
        px = x0 + m + min(max(focus[0] * cw - wp / 2, 0), cw - wp)
        py = y0 + m + min(max(focus[1] * ch - hp / 2, 0), ch - hp)
    else:
        px = x0 + m + rng.uniform(0, cw - wp)
        py = y0 + m + rng.uniform(0, ch - hp)
    u0, v1 = C.px_to_uv(px, py)
    u1, v0 = C.px_to_uv(px + wp, py + hp)
    return u0, v0, u1, v1


def region_uv(name):
    return C.rect_uv(C.REGIONS[name])


FLYERS = [i for i, (d, _) in enumerate(C.CELLS) if d in ("funday", "visitor", "smile")]


def pick_cell(z):
    wet_p = 0.8 if z < 0.9 else (0.45 if z < 1.4 else 0.2)
    if rng.random() < wet_p:
        cells = C.WET_CELLS
    elif rng.random() < 0.15:
        cells = FLYERS  # the white flyers stay rare so they don't read as clean paper
    else:
        cells = [c for c in C.DRY_CELLS if c not in FLYERS]
    return rng.choice(cells)


def back_uv():
    return region_uv("back")


# ================================================================ geometry pieces
def add_card(mb, place, a0, b0, w, h, psi, off, uv, part, crumple=0.004, freq=24.0, seg=(0.03, 0.05),
             peel=0.010, cut=None, lift=None, fixed=None, max_n=8):
    """A torn, crumpled sheet conforming to a surface. place(a, b, off) -> (point, normal)."""
    nu = max(2, min(max_n, math.ceil(w / seg[0])))
    nv = max(2, min(max_n, math.ceil(h / seg[1])))
    u0, v0, u1, v1 = uv
    cs, sn = math.cos(psi), math.sin(psi)
    corner = (rng.choice((-1, 1)), rng.choice((-1, 1)))
    seed = rng.uniform(0, 1000)
    missing_corner = rng.random() < 0.5
    ids = {}
    for j in range(nv + 1):
        for i in range(nu + 1):
            s, q = i / nu - 0.5, j / nv - 0.5
            if i in (0, nu) or j in (0, nv):  # torn edge
                jit = noise.noise(V(s * 9.1 + seed, q * 9.7, seed * 0.37)) * 0.08
                s, q = s * (1 + jit), q * (1 + jit)
                if missing_corner and i in (0, nu) and j in (0, nv) and \
                        (math.copysign(1, s), math.copysign(1, q)) == corner:
                    s, q = s * 0.62, q * 0.62
            lx, ly = s * w, q * h
            p, n = place(a0 + lx * cs - ly * sn, b0 + lx * sn + ly * cs, off)
            d = crumple * (noise.noise(p * freq) + 0.6 * noise.noise(p * freq * 2.3 + V(3, 1, 7)))
            d += crumple * 0.8 * (abs(noise.noise(p * freq * 0.6 + V(9, 4, 2))) - 0.3)
            c = max(0.0, s * corner[0] + q * corner[1] - 0.3)
            d += peel * c * c * 4.0
            if lift:
                d += lift(p)
            p = p + n * d
            uv_ = (min(max(u0 + (s + 0.5) * (u1 - u0), u0 - 0.003), u1 + 0.003),
                   min(max(v0 + (q + 0.5) * (v1 - v0), v0 - 0.003), v1 + 0.003))
            ids[i, j] = (mb.add_vert(p, part, fixed), uv_)
    for j in range(nv):
        for i in range(nu):
            quad = [ids[i, j], ids[i + 1, j], ids[i + 1, j + 1], ids[i, j + 1]]
            if cut and any(cut(mb.co[k]) for k, _ in quad):
                continue
            mb.add_face([k for k, _ in quad], [uv for _, uv in quad])


def add_grid_tube(mb, surf, n_around, n_along, off, part, uv="pulp", b0=None, b1=None, caps=(True, True),
                  push=None, void=None, fixed=None):
    """Core tube sampled from a surface, optionally capped; faces where void(p) is true use the void region."""
    b0 = 0.0 if b0 is None else b0
    b1 = surf.L if b1 is None else b1
    ru, rv = region_uv(uv), region_uv("void")
    grid = []
    for j in range(n_along + 1):
        b = lerp(b0, b1, j / n_along)
        row = []
        for i in range(n_around + 1):
            th = 2 * math.pi * i / n_around
            p, _ = surf.pos_theta(th, b, off + (push(th, b) if push else 0.0))
            part_ = part(p) if callable(part) else part
            row.append((mb.add_vert(p, part_, fixed), (i / n_around, j / n_along)))
        grid.append(row)

    def to_uv(f, r):
        return r[0] + (r[2] - r[0]) * f[0], r[1] + (r[3] - r[1]) * f[1]

    for j in range(n_along):
        for i in range(n_around):
            quad = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            ctr = sum((mb.co[k] for k, _ in quad), Vector()) / 4
            r = rv if (void and void(ctr)) else ru
            mb.add_face([k for k, _ in quad], [to_uv(f, r) for _, f in quad])
    for end, b, row in ((0, b0, grid[0]), (1, b1, grid[-1])):
        if not caps[end]:
            continue
        rr = surf.r(b / surf.L)
        tip = surf.center(b) + surf.W * ((0.6 * min(rr)) * (1 if end else -1))
        part_ = part(tip) if callable(part) else part
        t = (mb.add_vert(tip, part_, fixed), (0.5, 0.5))
        for i in range(n_around):
            tri = [row[i], row[i + 1], t]
            mb.add_oriented([(k, to_uv(f, ru)) for k, f in tri], surf.W * (1 if end else -1))


def add_blob_core(mb, blob, n_lon, n_lat, off, part, fixed=None, uv="pulp"):
    u0, v0, u1, v1 = region_uv(uv)
    rows = []
    for j in range(1, n_lat):
        lam = -math.pi / 2 + math.pi * j / n_lat
        row = []
        for i in range(n_lon + 1):
            phi = 2 * math.pi * i / n_lon
            d = V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))
            p, _ = blob.at_dir(d, off)
            row.append((mb.add_vert(p, part, fixed), (u0 + (u1 - u0) * i / n_lon, v0 + (v1 - v0) * j / n_lat)))
        rows.append(row)
    for j in range(len(rows) - 1):
        for i in range(n_lon):
            quad = [rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]]
            ctr = sum((mb.co[k] for k, _ in quad), Vector()) / 4
            mb.add_oriented(quad, ctr - blob.c)
    for pole, row in ((-1, rows[0]), (1, rows[-1])):
        p, _ = blob.at_dir(V(0, 0, pole), off)
        t = (mb.add_vert(p, part, fixed), ((u0 + u1) / 2, (v0 + v1) / 2))
        for i in range(n_lon):
            tri = [row[i], row[i + 1], t]
            ctr = sum((mb.co[k] for k, _ in tri), Vector()) / 3
            mb.add_oriented(tri, ctr - blob.c)


def add_band(mb, surf, b, width, off, part, segs=14, tilt=0.012, fixed=None):
    """Packing tape wrapped around a tube."""
    u0, v0, u1, v1 = region_uv("tape")
    ph = rng.uniform(0, 2 * math.pi)
    rows = []
    for r in range(3):
        row = []
        for k in range(segs + 1):
            th = 2 * math.pi * k / segs
            bb = b + (r / 2 - 0.5) * width + tilt * math.sin(th + ph)
            p, _ = surf.pos_theta(th, bb, off + 0.0015 * noise.noise(V(th * 3, r, b * 10)))
            row.append((mb.add_vert(p, part, fixed), (u0 + (u1 - u0) * k / segs, v0 + (v1 - v0) * r / 2)))
        rows.append(row)
    for r in range(2):
        for k in range(segs):
            q = [rows[r][k], rows[r][k + 1], rows[r + 1][k + 1], rows[r + 1][k]]
            mb.add_face([i for i, _ in q], [uv for _, uv in q])


def add_ribbon(mb, pts, nrms, width, uv, part, fixed=None):
    u0, v0, u1, v1 = uv
    n = len(pts)
    rows = []
    for k in range(n):
        t = (pts[min(k + 1, n - 1)] - pts[max(k - 1, 0)]).normalized()
        side = t.cross(nrms[k]).normalized()
        f = k / (n - 1)
        rows.append(((mb.add_vert(pts[k] - side * width / 2, part, fixed), (u0 + (u1 - u0) * f, v0)),
                     (mb.add_vert(pts[k] + side * width / 2, part, fixed), (u0 + (u1 - u0) * f, v1))))
    for k in range(n - 1):
        mb.add_oriented([rows[k][0], rows[k + 1][0], rows[k + 1][1], rows[k][1]], nrms[k])


def add_strip(mb, top, length, width, out, uv, fixed, curl=0.12, n=6):
    """A thin double-sided strip of wet paper hanging from a point."""
    seed = rng.uniform(0, 100)
    out = V(out.x, out.y, 0).normalized()
    side = V(0, 0, 1).cross(out).normalized()
    pts = [top + V(0, 0, -1) * (length * k / n) + out * (curl * length * (k / n) ** 2)
           + side * (0.02 * (k / n) * noise.noise(V(seed, k / n * 3, 0.5))) for k in range(n + 1)]
    add_ribbon(mb, pts, [out] * len(pts), width, uv, None, fixed)
    add_ribbon(mb, [p - out * 0.001 for p in pts], [-out] * len(pts), width, back_uv(), None, fixed)


def add_path_tube(mb, pts, radii, n_around, uv, part, fixed=None, tip=None, tip_uv=None, saw=0.0):
    """Tube along a polyline (fingers, ribs). The uv rect wraps around (u) and runs along (v)."""
    u0, v0, u1, v1 = uv
    total = sum((b - a).length for a, b in zip(pts, pts[1:]))
    rings, N, acc = [], None, 0.0
    for k, p in enumerate(pts):
        if k:
            acc += (pts[k] - pts[k - 1]).length
        T = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
        if N is None:
            N = V(0, 0, 1) if abs(T.z) < 0.9 else V(1, 0, 0)
        N = (N - T * N.dot(T)).normalized()
        B = T.cross(N)
        ring = []
        for i in range(n_around + 1):
            th = 2 * math.pi * i / n_around
            rr = radii[k] * (1 + saw * (((th + acc * 25) % (2 * math.pi)) / (2 * math.pi) - 0.5))
            q = p + (N * math.cos(th) + B * math.sin(th)) * rr
            ring.append((mb.add_vert(q, part, fixed), (u0 + (u1 - u0) * i / n_around, v0 + (v1 - v0) * acc / total)))
        rings.append((ring, p))
    for k in range(len(rings) - 1):
        (ra, pa), (rb, pb) = rings[k], rings[k + 1]
        for i in range(n_around):
            quad = [ra[i], ra[i + 1], rb[i + 1], rb[i]]
            ctr = sum((mb.co[x] for x, _ in quad), Vector()) / 4
            mb.add_oriented(quad, ctr - (pa + pb) / 2)
    if tip is not None:
        ring, p = rings[-1]
        t = (mb.add_vert(tip, part, fixed), tip_uv or (u0, v1))
        for i in range(n_around):
            tri = [ring[i], ring[i + 1], t]
            ctr = sum((mb.co[x] for x, _ in tri), Vector()) / 3
            mb.add_oriented(tri, ctr - p)


def add_flap(mb, name, place, a, b, w, length, off, parent, uv, curl=0.35, nu=4, nv=6):
    """A loose wet sheet hanging from the body, double sided, driven by two flap bones."""
    _, nc = place(a, b, off)
    pl, _ = place(a - w / 2, b, off)
    pr, _ = place(a + w / 2, b, off)
    out = V(nc.x, nc.y, 0)
    out = out.normalized() if out.length > 1e-4 else V(0, 1, 0)
    across = (pr - pl).normalized()
    seed = rng.uniform(0, 100)
    pos = {}
    for j in range(nv + 1):
        d = j / nv
        for i in range(nu + 1):
            s = i / nu
            ln = length * (1 + (0.14 * noise.noise(V(s * 5 + seed, 0.5, 0.5)) if j == nv else 0.0))
            dd = d * ln / length
            p = pl.lerp(pr, s) + V(0, 0, -1) * (dd * length)
            p += out * (curl * length * dd ** 1.7 + 0.004 + 0.016 * dd * noise.noise(V(s * 3 + seed, dd * 3, seed)))
            p += across * (0.02 * dd * noise.noise(V(seed, dd * 2, s)))
            pos[i, j] = (p, (s, dd))
    mid = pos[nu // 2, nv // 2][0]
    bot = pos[nu // 2, nv][0]
    top = pl.lerp(pr, 0.5) + out * 0.004
    SK.add_flap_bones(name, top, mid, bot, parent, out)

    def wts(dd):
        w1 = smooth(0.0, 0.3, dd) * (1 - smooth(0.45, 0.8, dd))
        w2 = smooth(0.45, 0.8, dd)
        return {parent: 1 - w1 - w2, f"{name}1": w1, f"{name}2": w2}

    u0, v0, u1, v1 = uv
    b0, bv0, b1, bv1 = back_uv()
    front, back = {}, {}
    for (i, j), (p, (s, dd)) in pos.items():
        front[i, j] = (mb.add_vert(p, None, wts(dd)), (u0 + (u1 - u0) * s, v1 - (v1 - v0) * min(dd, 1.0)))
        back[i, j] = (mb.add_vert(p - out * 0.0012, None, wts(dd)), (b0 + (b1 - b0) * s, bv1 - (bv1 - bv0) * min(dd, 1.0)))
    for j in range(nv):
        for i in range(nu):
            want = out
            mb.add_oriented([front[i, j], front[i + 1, j], front[i + 1, j + 1], front[i, j + 1]], want)
            mb.add_oriented([back[i, j], back[i + 1, j], back[i + 1, j + 1], back[i, j + 1]], -want)
    # a strip of tape pins the top edge
    tpts = [pl.lerp(pr, f) + out * 0.006 for f in (0.15, 0.5, 0.85)]
    add_ribbon(mb, tpts, [out] * 3, 0.03, region_uv("tape"), None, {parent: 1.0})


# ================================================================ body layout
TORSO = Torso()
NECK = Tube(V(0, 0.014, 1.98), V(0, 0.0, 2.37), [(0, 0.038, 0.036), (1, 0.032, 0.030)])
HEAD_C = V(0, 0.02, 2.47)
HEAD = Blob(HEAD_C, (0.18, 0.175, 0.23))


def limb_tubes(side):
    return {
        "uarm": Tube(J[f"elbow_{side}"], J[f"shoulder_{side}"], [(0, 0.043, 0.040), (0.55, 0.050, 0.047), (1, 0.056, 0.052)]),
        "farm": Tube(J[f"wrist_{side}"], J[f"elbow_{side}"], [(0, 0.030, 0.026), (0.65, 0.042, 0.038), (1, 0.042, 0.039)]),
        "thigh": Tube(J[f"knee_{side}"], J[f"hip_{side}"], [(0, 0.050, 0.048), (0.6, 0.068, 0.066), (1, 0.078, 0.074)]),
        "shin": Tube(J[f"ankle_{side}"], J[f"knee_{side}"], [(0, 0.036, 0.034), (0.72, 0.054, 0.052), (1, 0.050, 0.048)]),
    }


LIMBS = {side: limb_tubes(side) for side, _ in SK.SIDES}

# torn-open chest: a hole on the front-left showing rolled-poster ribs
CAV = dict(th=-0.80, z=1.65, dth=0.42, dz=0.11)


def cavity_e(p):
    th, b = TORSO.theta_b(p)
    z = TORSO.z0 + b
    dth = math.atan2(math.sin(th - CAV["th"]), math.cos(th - CAV["th"]))
    return (dth / CAV["dth"]) ** 2 + ((z - CAV["z"]) / CAV["dz"]) ** 2 + 0.25 * noise.noise(V(th * 4, z * 20, 0.5))


def head_weights(p):
    return {"Head": 1.0} if p.z > 2.38 else {"Head": 0.7, "Neck": 0.3}


def torso_part(p):
    return "pelvis" if p.z < 1.36 else "torso"


# ---------------------------------------------------------------- mask geometry
MASK_TILT = Matrix.Rotation(math.radians(5.0), 3, "Y") @ Matrix.Rotation(math.radians(-4.0), 3, "X")
MASK_ORIGIN = V(0, -0.192, 2.455)
MASK_SCALE = 1.04


def dome(x, y):
    return -4.6 * x * x - (2.0 if y > 0 else 0.7) * y * y


def mask_world(x, y, z_extra=0.0):
    """Mask space (x right, y up, z toward the viewer) to world."""
    z = dome(x, y) + z_extra
    return HEAD_C + MASK_TILT @ (MASK_ORIGIN - HEAD_C + V(x, -z, y) * MASK_SCALE)


def mask_normal(x, y):
    fx = -9.2 * x
    fy = -(4.0 if y > 0 else 1.4) * y
    return (MASK_TILT @ V(-fx, -1.0, -fy)).normalized()


def point_in_poly(p, poly):
    x, y = p
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def dist_to_polyline(p, pts):
    best, best_t = 1e9, 0.0
    total = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        ax, ay = a
        dx, dy = b[0] - ax, b[1] - ay
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        d = math.hypot(ax + dx * t - p[0], ay + dy * t - p[1])
        if d < best:
            best, best_t = d, (acc + t * math.sqrt(L2)) / total
        acc += math.sqrt(L2)
    return best, best_t


def build_mask_object(material):
    outline = C.mask_outline(150)
    eyes = [C.eye_outline(0), C.eye_outline(1)]
    slit = C.smile_slit()
    crack, _ = C.crack_path()
    verts2, faces_in = [], []
    for poly in [outline] + eyes + [slit]:
        faces_in.append(list(range(len(verts2), len(verts2) + len(poly))))
        verts2.extend(Vector(p) for p in poly)
    crack_idx = []
    for p in crack:
        hit = next((i for i, q in enumerate(verts2) if (q - Vector(p)).length < 1e-9), None)
        if hit is None:
            hit = len(verts2)
            verts2.append(Vector(p))
        crack_idx.append(hit)
    edges_in = list(zip(crack_idx, crack_idx[1:]))
    boundary = [q for q in verts2]
    step = 0.016
    gy = -0.23
    while gy < 0.27:
        gx = -0.19 + (0.5 * step if int(round(gy / step)) % 2 else 0.0)
        while gx < 0.19:
            p = (gx, gy)
            if point_in_poly(p, outline) and not any(point_in_poly(p, h) for h in eyes + [slit]):
                if min((Vector(p) - q).length for q in boundary) > 0.0075:
                    verts2.append(Vector(p))
            gx += step
        gy += step * 0.866
    res = delaunay_2d_cdt(verts2, edges_in, faces_in, 2, 1e-7, True)
    out_v, out_f = res[0], res[2]

    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    bv = [bm.verts.new(mask_world(v.x, v.y)) for v in out_v]
    for f in out_f:
        a, b, c = (out_v[i] for i in f[:3])
        area = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
        idx = list(f) if area > 0 else list(f)[::-1]
        face = bm.faces.new([bv[i] for i in idx])
        for loop, i in zip(face.loops, idx):
            loop[uvl].uv = C.mask_uv(out_v[i].x, out_v[i].y)
    bm.verts.ensure_lookup_table()

    def v2d(v):
        u, w = v.link_loops[0][uvl].uv
        return (u - 0.5) * C.MASK_UV_SCALE, (w - 0.5) * C.MASK_UV_SCALE + C.MASK_YC

    # split the crack open and lift its outer side: a broken, bent piece of plastic
    crack_edges = []
    for e in bm.edges:
        a, b = v2d(e.verts[0]), v2d(e.verts[1])
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if all(dist_to_polyline(q, crack)[0] < 1e-6 for q in (a, b, m)):
            crack_edges.append(e)
    bmesh.ops.split_edges(bm, edges=crack_edges)
    (cx0, cy0), (cx1, cy1) = crack[0], crack[-1]
    for v in bm.verts:
        if not v.link_faces:
            continue
        fc = [sum(v2d(x)[k] for x in f.verts) / len(f.verts) for f in v.link_faces for k in (0, 1)]
        px = sum(fc[0::2]) / len(v.link_faces)
        py = sum(fc[1::2]) / len(v.link_faces)
        d, t = dist_to_polyline((px, py), crack)
        side = (cx1 - cx0) * (py - cy0) - (cy1 - cy0) * (px - cx0)
        if side < 0 and d < 0.05:
            x, y = v2d(v)
            v.co += mask_normal(x, y) * 0.0042 * lerp(1.0, 0.25, t) * (1 - d / 0.05)

    # rim walls
    edge_verts = {}
    bnd = [e for e in bm.edges if len(e.link_faces) == 1]
    for e in bnd:
        e.smooth = False
    src = {v: v2d(v) for e in bnd for v in e.verts}
    ret = bmesh.ops.extrude_edge_only(bm, edges=bnd)
    new_verts = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    new_faces = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMFace)]
    new_face_set = set(new_faces)
    by_pos = {tuple(round(c, 7) for c in v.co): v for v in src}
    for v in new_verts:
        o = by_pos.get(tuple(round(c, 7) for c in v.co))
        x, y = src[o] if o else (0.0, 0.0)
        edge_verts[v] = (x, y)
        v.co -= mask_normal(x, y) * 0.0045
    bm.normal_update()
    for f in new_faces:
        f.smooth = False
        for loop in f.loops:
            xy = edge_verts.get(loop.vert) or src.get(loop.vert) or (0.0, 0.0)
            loop[uvl].uv = C.mask_uv(*xy)
        orig = [v for v in f.verts if v not in edge_verts]
        if len(orig) == 2:
            shared = [g for g in orig[0].link_faces if g in orig[1].link_faces and g is not f]
            if shared:
                want = f.calc_center_median() - shared[0].calc_center_median()
                if f.normal.dot(want) < 0:
                    f.normal_flip()
    for f in bm.faces:
        if f not in new_face_set:
            f.smooth = True
    bm.normal_update()
    me = bpy.data.meshes.new("Mask")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new("Mask", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def add_cup(mb, cx, cy, rx, ry, depth, nphi=14, nalpha=4, curve=None):
    """Dark socket behind a hole in the mask, open toward the viewer. curve(x) bends it along a smile."""
    uv = region_uv("void")
    rings = []
    for ia in range(nalpha + 1):
        al = (math.pi / 2) * (1 - ia / nalpha)
        ring = []
        for ip in range(nphi + 1):
            ph = 2 * math.pi * ip / nphi
            x = cx + rx * math.sin(al) * math.cos(ph)
            y = (curve(x) if curve else cy) + ry * math.sin(al) * math.sin(ph)
            p = mask_world(x, y, -0.004 - depth * math.cos(al))
            ring.append((mb.add_vert(p, None, {"Head": 1.0}),
                         (uv[0] + (uv[2] - uv[0]) * ip / nphi, uv[1] + (uv[3] - uv[1]) * ia / nalpha)))
        rings.append(ring)
    front = mask_world(cx, cy, 0.08)
    for k in range(nalpha):
        for ip in range(nphi):
            quad = [rings[k][ip], rings[k][ip + 1], rings[k + 1][ip + 1], rings[k + 1][ip]]
            ctr = sum((mb.co[i] for i, _ in quad), Vector()) / 4
            mb.add_oriented(quad, front - ctr)


# ================================================================ assembly
def build_body():
    torso_mb, arms_mb, legs_mb = MB("Body_Torso"), MB("Body_Arms"), MB("Body_Legs")
    glow_mb = MB("EyeGlow")

    # ---- core: dark wet pulp under everything
    add_grid_tube(torso_mb, TORSO, 16, 14, -0.008, torso_part,
                  push=lambda th, b: -0.045 * max(0.0, 1.0 - cavity_e(TORSO.pos_theta(th, b, 0)[0])),
                  void=lambda p: cavity_e(p) < 0.85)
    add_grid_tube(torso_mb, NECK, 10, 8, 0.0, "neck", caps=(False, False))
    add_blob_core(torso_mb, HEAD, 14, 9, -0.004, None, head_weights)
    for side, sx in SK.SIDES:
        L = LIMBS[side]
        add_grid_tube(arms_mb, L["uarm"], 8, 6, -0.006, f"arm_{side}", caps=(False, False))
        add_grid_tube(arms_mb, L["farm"], 8, 6, -0.006, f"arm_{side}", caps=(False, False))
        add_grid_tube(legs_mb, L["thigh"], 8, 6, -0.006, f"leg_{side}", caps=(False, False))
        add_grid_tube(legs_mb, L["shin"], 8, 6, -0.006, f"leg_{side}", caps=(False, False))
        add_blob_core(torso_mb, Blob(J[f"shoulder_{side}"], (0.056, 0.052, 0.054)), 8, 6, 0, f"shoulder_{side}")
        add_blob_core(arms_mb, Blob(J[f"elbow_{side}"], (0.04, 0.038, 0.04)), 8, 6, 0, f"arm_{side}")
        add_blob_core(legs_mb, Blob(J[f"hip_{side}"], (0.074, 0.072, 0.074)), 8, 6, 0, f"leg_{side}")
        add_blob_core(legs_mb, Blob(J[f"knee_{side}"], (0.05, 0.048, 0.05)), 8, 6, 0, f"leg_{side}")
        add_blob_core(legs_mb, Blob(J[f"ankle_{side}"], (0.038, 0.038, 0.038)), 8, 6, 0, f"foot_{side}")

    # ---- torso posters
    def lift(p):  # torn edges curl outward around the hole
        e = cavity_e(p)
        return 0.03 * min(0.4, 1.3 - e) if 0.9 <= e < 1.3 else 0.0

    cut = lambda p: cavity_e(p) < 0.9  # noqa: E731
    rows, cols = 5, 6
    circ = 2 * math.pi * 0.128
    for r in range(rows):
        for c in range(cols):
            b = (r + 0.5 + rng.uniform(-0.25, 0.25)) / rows * TORSO.L
            a = (c + 0.5 + (r % 2) * 0.5 + rng.uniform(-0.25, 0.25)) / cols * circ
            pc, _ = TORSO.pos(a, b, 0)
            if cavity_e(pc) < 1.1:
                continue
            w, h = rng.uniform(0.18, 0.25), rng.uniform(0.21, 0.28)
            cell = pick_cell(pc.z)
            psi = rng.gauss(0, 0.22) + (math.pi if rng.random() < 0.15 else 0)
            add_card(torso_mb, TORSO.pos, a, b, w, h, psi, 0.004 + 0.0035 * ((r + c) % 3), poster_uv(cell, w, h),
                     torso_part, crumple=0.006, freq=22, seg=(0.035, 0.045), cut=cut, lift=lift)
    for _ in range(8):
        b = rng.uniform(0.05, TORSO.L - 0.05)
        a = rng.uniform(0, circ)
        pc, _ = TORSO.pos(a, b, 0)
        if cavity_e(pc) < 1.2:
            continue
        w, h = rng.uniform(0.14, 0.2), rng.uniform(0.16, 0.24)
        add_card(torso_mb, TORSO.pos, a, b, w, h, rng.gauss(0, 0.4), 0.0145, poster_uv(pick_cell(pc.z), w, h),
                 torso_part, crumple=0.006, freq=22, seg=(0.035, 0.045), cut=cut, lift=lift)
    # the mascot grinning from the middle of the chest, and the scribbled one on the back
    add_card(torso_mb, TORSO.pos, -0.62 * math.pi * 0.14, 1.84 - TORSO.z0, 0.22, 0.27, 0.14, 0.0175,
             poster_uv(C.CELLS.index(("tomorrow", 0)), 0.22, 0.27, (0.62, 0.62), focus=(0.5, 0.52)),
             torso_part, crumple=0.004, seg=(0.04, 0.05), peel=0.004, cut=cut, lift=lift)
    add_card(torso_mb, TORSO.pos, 0.5 * math.pi * 0.141, 1.72 - TORSO.z0, 0.26, 0.3, -0.2, 0.0175,
             poster_uv(C.CELLS.index(("hydrated", 1)), 0.26, 0.3, (0.75, 0.75), focus=(0.5, 0.48)),
             torso_part, seg=(0.04, 0.05))
    # ribs of rolled posters across the hole
    for zr in (1.555, 1.615, 1.675):
        pts, radii = [], []
        for k in range(11):
            th = CAV["th"] - 0.42 + 0.84 * k / 10
            z = zr + 0.022 * (th - CAV["th"]) / 0.42
            p, n = TORSO.pos_theta(th, z - TORSO.z0, -0.002)
            pts.append(p)
            radii.append(0.011 - 0.003 * abs(k - 5) / 5)
        cell = rng.choice(C.DRY_CELLS)
        add_path_tube(torso_mb, pts, radii, 6, poster_uv(cell, 0.06, 0.3), "torso", saw=0.25)

    # ---- neck: dark pulp stalk with a few strips and tape
    for k in range(3):
        a = k * NECK.circ / 3 + rng.uniform(0, 0.03)
        w, h = rng.uniform(0.05, 0.07), rng.uniform(0.16, 0.22)
        add_card(torso_mb, NECK.pos, a, rng.uniform(0.12, 0.22), w, h, 0.5 + rng.gauss(0, 0.2), 0.004,
                 poster_uv(pick_cell(2.1), w, h), "neck", seg=(0.025, 0.04), crumple=0.003)
    add_band(torso_mb, NECK, 0.10, 0.03, 0.008, "neck", segs=12, tilt=0.02)
    add_band(torso_mb, NECK, 0.27, 0.026, 0.007, "neck", segs=12, tilt=0.015)

    # ---- shoulders
    for side, sx in SK.SIDES:
        sb = Blob(J[f"shoulder_{side}"], (0.064, 0.06, 0.062))
        for d in (V(0.3 * sx, -0.3, 0.9), V(0.6 * sx, 0.35, 0.7), V(0.85 * sx, -0.1, 0.5), V(0.4 * sx, 0.5, 0.75)):
            w, h = rng.uniform(0.12, 0.16), rng.uniform(0.13, 0.17)
            add_card(torso_mb, sb.placer(frame_to(d, rng.gauss(0, 0.5))), 0, 0, w, h, 0, 0.006 + rng.uniform(0, 0.004),
                     poster_uv(pick_cell(1.95), w, h), f"shoulder_{side}", seg=(0.03, 0.04))

    # ---- limbs
    for side, sx in SK.SIDES:
        L = LIMBS[side]
        for key, mb, part, nr, nc, wr, hr in (
            ("uarm", arms_mb, f"arm_{side}", 4, 3, (0.12, 0.16), (0.18, 0.24)),
            ("farm", arms_mb, f"arm_{side}", 4, 3, (0.1, 0.13), (0.17, 0.22)),
            ("thigh", legs_mb, f"leg_{side}", 4, 3, (0.15, 0.19), (0.19, 0.25)),
            ("shin", legs_mb, f"leg_{side}", 4, 3, (0.12, 0.15), (0.18, 0.23)),
        ):
            surf = L[key]
            for r in range(nr):
                for c in range(nc):
                    b = -0.03 + (r + 0.5 + rng.uniform(-0.2, 0.2)) / nr * (surf.L + 0.06)
                    a = (c + 0.5 + (r % 2) * 0.5 + rng.uniform(-0.2, 0.2)) / nc * surf.circ
                    w, h = rng.uniform(*wr), rng.uniform(*hr)
                    pc, _ = surf.pos(a, b, 0)
                    psi = rng.gauss(0, 0.25) + (math.pi if rng.random() < 0.2 else 0)
                    add_card(mb, surf.pos, a, b, w, h, psi, 0.004 + 0.003 * ((r + c) % 3),
                             poster_uv(pick_cell(pc.z), w, h), part, crumple=0.0055, freq=28, seg=(0.024, 0.045),
                             max_n=7)
        # tape where it was needed, not in neat pairs
        if side == "Left":
            add_band(arms_mb, L["farm"], 0.05, 0.032, 0.016, f"arm_{side}", segs=12, tilt=0.015)
            add_band(arms_mb, L["uarm"], 0.36, 0.034, 0.018, f"arm_{side}", segs=12, tilt=0.03)
            add_band(legs_mb, L["thigh"], 0.30, 0.036, 0.018, f"leg_{side}", segs=14, tilt=0.03)
        else:
            add_band(arms_mb, L["farm"], 0.33, 0.03, 0.016, f"arm_{side}", segs=12, tilt=0.025)
            add_band(legs_mb, L["shin"], 0.5, 0.034, 0.017, f"leg_{side}", segs=12, tilt=0.03)

    # ---- hands: a crumpled wad with rolled-poster fingers
    for side, sx in SK.SIDES:
        along, across, palm = SK.hand_frame(side)
        F = basis(across.cross(-along), across, -along)  # Y across the palm, Z toward the wrist
        pb = Blob(J[f"wrist_{side}"] + (J[f"hand_{side}"] - J[f"wrist_{side}"]) * 0.55 + palm * 0.004,
                  (0.03, 0.042, 0.058), F)
        add_blob_core(arms_mb, pb, 8, 6, 0, f"hand_{side}")
        for d in (V(1, 0, 0.2), V(0.2, 1, 0), V(0.2, -1, 0), V(-0.9, 0, -0.2), V(0.5, 0.2, 0.8)):
            w, h = rng.uniform(0.07, 0.1), rng.uniform(0.08, 0.11)
            add_card(arms_mb, pb.placer(frame_to(d, rng.uniform(0, 6.28))), 0, 0, w, h, 0, 0.004,
                     poster_uv(pick_cell(0.9), w, h), f"hand_{side}", crumple=0.005, freq=40, seg=(0.025, 0.03))
        for fname, chain in SK.finger_chains(side).items():
            pts, radii = [], []
            r0 = 0.0155 if fname != "Thumb" else 0.017
            for k in range(3):
                for t in (0.0, 0.25, 0.5, 0.75):
                    pts.append(chain[k].lerp(chain[k + 1], t))
                    tt = (k + t) / 3
                    radii.append(lerp(r0, 0.0062, tt) * (1.08 if t == 0.0 and k else 1.0))
            pts.append(chain[3])
            radii.append(0.0055)
            tip = chain[3] + (chain[3] - chain[2]).normalized() * 0.014
            cell = pick_cell(0.6)
            add_path_tube(arms_mb, pts, radii, 8, poster_uv(cell, 0.09, 0.4), f"f_{side}{fname}",
                          tip=tip, tip_uv=C.px_to_uv(*[(a + b) / 2 for a, b in zip(C.REGIONS["pulp"][:2], C.REGIONS["pulp"][2:])]),
                          saw=0.22)
            if rng.random() < 0.5:  # a twist of tape where the roll meets the hand
                p0, p1 = chain[0], chain[1]
                ft = Tube(p0, p1, [(0, 0.0185, 0.0185), (1, 0.017, 0.017)], side=across)
                add_band(arms_mb, ft, ft.L * 0.3, 0.018, 0.0, f"f_{side}{fname}", segs=8, tilt=0.003)

    # ---- feet: soggy pulp clumps with sheets stuck to the floor
    for side, sx in SK.SIDES:
        fwd = (J[f"toe_{side}"] - J[f"ankle_{side}"])
        fwd = V(fwd.x, fwd.y, 0).normalized()
        F = basis(fwd.cross(V(0, 0, 1)).normalized(), fwd, V(0, 0, 1))
        fb = Blob(J[f"ankle_{side}"] + fwd * 0.07 + V(0, 0, -0.035), (0.068, 0.14, 0.05), F)
        add_blob_core(legs_mb, fb, 10, 6, 0, f"foot_{side}")
        for d in (V(0, 0.4, 1), V(0, 1, 0.3), V(1, 0.2, 0.3), V(-1, 0.2, 0.3), V(0, -0.8, 0.6)):
            w, h = rng.uniform(0.13, 0.18), rng.uniform(0.14, 0.2)
            add_card(legs_mb, fb.placer(frame_to(d, rng.uniform(0, 6.28))), 0, 0, w, h, 0, 0.005,
                     poster_uv(rng.choice(C.WET_CELLS), w, h), f"foot_{side}", crumple=0.007, freq=30, seg=(0.03, 0.04))
        for k in range(2):
            ctr = J[f"ankle_{side}"] + fwd * rng.uniform(0.0, 0.18) + V(sx * rng.uniform(0.02, 0.12), 0, 0)
            ang = rng.uniform(0, 6.28)
            def flat(a, b, off, ctr=ctr, ang=ang):
                x = a * math.cos(ang) - b * math.sin(ang)
                y = a * math.sin(ang) + b * math.cos(ang)
                return V(ctr.x + x, ctr.y + y, 0.004 + off * 0.2 + 0.006 * noise.noise(V(x * 9, y * 9, 1))), V(0, 0, 1)
            w, h = rng.uniform(0.16, 0.22), rng.uniform(0.2, 0.26)
            add_card(legs_mb, flat, 0, 0, w, h, 0, 0.0, poster_uv(rng.choice(C.WET_CELLS), w, h), f"foot_{side}",
                     crumple=0.003, seg=(0.05, 0.06), peel=0.02)

    # ---- head: crumpled sheets balled up behind the mask
    golden = math.pi * (3 - math.sqrt(5))
    n = 22
    for k in range(n):
        y = 1 - 2 * (k + 0.5) / n
        r = math.sqrt(1 - y * y)
        d = V(math.cos(golden * k) * r, math.sin(golden * k) * r, y)
        if d.dot(V(0, -1, 0)) > 0.35:  # hidden behind the mask, and keeps the eye sockets clear
            continue
        w, h = rng.uniform(0.18, 0.26), rng.uniform(0.18, 0.26)
        add_card(torso_mb, HEAD.placer(frame_to(d, rng.uniform(0, 6.28))), 0, 0, w, h, 0, 0.004 + rng.uniform(0, 0.006),
                 poster_uv(pick_cell(2.4), w, h), None, crumple=0.011, freq=14, seg=(0.03, 0.03), fixed=head_weights)

    # cover the forehead around the mask's top edge, keeping clear of the eye sockets
    for d, sz in ((V(0.45, -0.45, 0.75), 0.2), (V(-0.45, -0.45, 0.75), 0.2), (V(0.0, -0.4, 0.9), 0.2),
                  (V(0.72, -0.5, 0.45), 0.14), (V(-0.72, -0.5, 0.45), 0.14)):
        w, h = sz * rng.uniform(0.9, 1.1), sz * rng.uniform(0.9, 1.1)
        add_card(torso_mb, HEAD.placer(frame_to(d, rng.uniform(0, 6.28))), 0, 0, w, h, 0, 0.006,
                 poster_uv(pick_cell(2.4), w, h), None, crumple=0.01, freq=14, seg=(0.03, 0.03), fixed=head_weights)

    # ---- mask sockets, glints and the tape holding the mask on
    for k in range(2):
        (cx, cy), (rx, ry), _ = C.EYES[k]
        add_cup(torso_mb, cx, cy, rx * 1.25, ry * 1.2, 0.05)
        g = mask_world(cx + 0.007, cy + 0.012, -0.004 - 0.042)
        add_blob_core(glow_mb, Blob(g, (0.0042, 0.0042, 0.0042)), 8, 5, 0, None, {"Head": 1.0})
    add_cup(torso_mb, 0.0, 0.0, C.SMILE_HW * 1.12, 0.016, 0.03, nphi=18, curve=C.smile_y)
    tape = region_uv("tape")
    for ex, ey in ((0.168, -0.06), (-0.17, -0.025), (0.085, 0.15), (-0.09, -0.175)):
        # walk inward from the edge to find a point on the mask
        cx, cy = ex * 0.78, ey * 0.82 + 0.01
        pts, nrms = [], []
        for t in (0.0, 0.5, 1.0):
            x, y = lerp(cx, ex * 1.01, t), lerp(cy, ey * 1.01, t)
            pts.append(mask_world(x, y, 0.003))
            nrms.append(mask_normal(x, y))
        edge = pts[-1]
        d0 = (edge - HEAD_C).normalized()
        # wrap backward around the head: sideways for side strips, over or under for the others
        axis = V(0, 0, 1) if abs(ey) < 0.1 else V(1, 0, 0) * (-1 if ey > 0 else 1)
        sgn = 1 if ex > 0 else -1
        for ang in (14, 30, 46, 60):
            d = Matrix.Rotation(math.radians(ang * sgn if abs(ey) < 0.1 else ang), 3, axis) @ d0
            p, nrm = HEAD.at_dir(d, 0.014)
            pts.append(p)
            nrms.append(nrm)
        add_ribbon(torso_mb, pts, nrms, 0.034, tape, None, {"Head": 1.0})

    # ---- strings of wet paper: under the mask like drool, off the forearms and a thigh
    for x, y, ln, wd in ((-0.065, -0.185, 0.2, 0.022), (0.015, -0.2, 0.13, 0.018), (0.075, -0.175, 0.24, 0.026)):
        top = mask_world(x, y, -0.008)
        add_strip(torso_mb, top, ln, wd, -mask_normal(x, y) * -1, poster_uv(rng.choice(C.WET_CELLS), wd, ln),
                  {"Head": 1.0}, curl=0.05)
    for side, sx in SK.SIDES:
        farm = LIMBS[side]["farm"]
        for bf, th, ln in ((0.45, 0.4, 0.26), (0.2, -0.9, 0.17)):
            top, nrm = farm.pos_theta(th * sx + (0 if sx > 0 else math.pi), farm.L * bf, 0.01)
            add_strip(arms_mb, top, ln, rng.uniform(0.018, 0.028), nrm, poster_uv(rng.choice(C.WET_CELLS), 0.03, ln),
                      {f"{side}LowerArm": 1.0})
    th_r = LIMBS["Right"]["thigh"]
    top, nrm = th_r.pos_theta(math.pi * 0.9, th_r.L * 0.55, 0.012)
    add_strip(legs_mb, top, 0.24, 0.025, nrm, poster_uv(rng.choice(C.WET_CELLS), 0.03, 0.24), {"RightUpperLeg": 1.0})

    # ---- loose sheets
    flaps = [
        ("FlapBackL", TORSO.pos, 0.5 * math.pi * 0.135 - 0.05, 1.93 - TORSO.z0, 0.22, 0.48, 0.02, "UpperTorso"),
        ("FlapBackR", TORSO.pos, 0.62 * math.pi * 0.135 + 0.06, 1.80 - TORSO.z0, 0.2, 0.4, 0.022, "UpperTorso"),
        ("FlapHipF", TORSO.pos, -0.33 * math.pi * 0.135, 1.31 - TORSO.z0, 0.2, 0.34, 0.02, "LowerTorso"),
        ("FlapHipR", TORSO.pos, 1.1 * math.pi * 0.135, 1.33 - TORSO.z0, 0.22, 0.36, 0.02, "LowerTorso"),
        ("FlapHipB", TORSO.pos, 0.55 * math.pi * 0.135, 1.29 - TORSO.z0, 0.24, 0.4, 0.022, "LowerTorso"),
    ]
    for name, place, a, b, w, ln, off, parent in flaps:
        add_flap(torso_mb, name, place, a, b, w, ln, off, parent, poster_uv(rng.choice(C.WET_CELLS), w, ln, (0.8, 1.0)))
    hp = HEAD.placer(frame_to(V(0, 1, 0.25), 0.0))
    add_flap(torso_mb, "FlapHead", hp, 0, 0.02, 0.2, 0.38, 0.014, "Head",
             poster_uv(rng.choice(C.WET_CELLS), 0.2, 0.38, (0.8, 1.0)), curl=0.15)
    for side, sx in SK.SIDES:
        L = LIMBS[side]
        if side == "Left":
            add_flap(arms_mb, "FlapArmL", L["uarm"].pos, 0.0, L["uarm"].L * 0.75, 0.12, 0.22, 0.016, "LeftUpperArm",
                     poster_uv(rng.choice(C.WET_CELLS), 0.12, 0.22, (0.8, 1.0)), curl=0.25)
            add_flap(legs_mb, "FlapThighL", L["thigh"].pos, 0.5 * math.pi * 0.075, L["thigh"].L * 0.7, 0.14, 0.26,
                     0.016, "LeftUpperLeg", poster_uv(rng.choice(C.WET_CELLS), 0.14, 0.26, (0.8, 1.0)), curl=0.2)
        else:
            add_flap(arms_mb, "FlapForearmR", L["farm"].pos, math.pi * 0.045, L["farm"].L * 0.8, 0.1, 0.2, 0.014,
                     "RightLowerArm", poster_uv(rng.choice(C.WET_CELLS), 0.1, 0.2, (0.8, 1.0)), curl=0.25)
    return torso_mb, arms_mb, legs_mb, glow_mb


# ================================================================ materials
def load_image(name, noncolor):
    img = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    return img


def make_material(name, prefix, coat=0.0, coat_rough=0.2):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    col = nt.nodes.new("ShaderNodeTexImage")
    col.image = load_image(f"{prefix}_color.png", False)
    col.location = (-700, 300)
    rough = nt.nodes.new("ShaderNodeTexImage")
    rough.image = load_image(f"{prefix}_roughness.png", True)
    rough.location = (-700, 0)
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = load_image(f"{prefix}_normal.png", True)
    nrm.location = (-1000, -300)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-700, -300)
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = coat_rough
    return m


def make_glow_material():
    m = bpy.data.materials.new("M_EyeGlow")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Emission Color"].default_value = (0.75, 0.85, 1.0, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.8
    return m


# ================================================================ rig + weights
def build_armature():
    arm = bpy.data.armatures.new("PosterMonster_Rig")
    ob = bpy.data.objects.new("PosterMonster_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, (h, t, parent, r, roll) in SK.BONES.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = h, t
        eb.align_roll(roll)
        ebs[name] = eb
    for name, (h, t, parent, r, roll) in SK.BONES.items():
        if parent:
            ebs[name].parent = ebs[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def part_bones():
    P = {
        "torso": [("LowerTorso", None), ("Spine", None), ("UpperTorso", None), ("LeftShoulder", None),
                  ("RightShoulder", None), ("Neck", 0.08)],
        "pelvis": [("LowerTorso", None), ("Spine", None), ("LeftUpperLeg", 0.05), ("RightUpperLeg", 0.05)],
        "neck": [("UpperTorso", 0.1), ("Neck", None), ("Head", 0.1)],
    }
    for s, _ in SK.SIDES:
        P[f"shoulder_{s}"] = [("UpperTorso", None), (f"{s}Shoulder", None), (f"{s}UpperArm", None)]
        P[f"arm_{s}"] = [(f"{s}Shoulder", 0.05), (f"{s}UpperArm", None), (f"{s}LowerArm", None), (f"{s}Hand", None)]
        P[f"hand_{s}"] = [(f"{s}LowerArm", None), (f"{s}Hand", None)]
        P[f"leg_{s}"] = [("LowerTorso", 0.1), (f"{s}UpperLeg", None), (f"{s}LowerLeg", None), (f"{s}Foot", None)]
        P[f"foot_{s}"] = [(f"{s}LowerLeg", None), (f"{s}Foot", None)]
        for f in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
            P[f"f_{s}{f}"] = [(f"{s}Hand", 0.02)] + [(f"{s}{f}{k}", None) for k in (1, 2, 3)]
    return P


def dseg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


def skin(ob, mb_parts, mb_fixed, co_list, rig):
    P = part_bones()
    groups = {}
    for name in SK.BONES:
        groups[name] = ob.vertex_groups.new(name=name)
    for vi, co in enumerate(co_list):
        ws = mb_fixed[vi]
        if not ws:
            ws = {}
            for bname, rad in P[mb_parts[vi]]:
                h, t, _, r0, _ = SK.BONES[bname]
                d = dseg(co, h, t) / (rad or r0)
                ws[bname] = 1.0 / (1e-4 + d ** 4)
        top = sorted(((b, w) for b, w in ws.items() if w > 0), key=lambda kv: -kv[1])[:4]
        tot = sum(w for _, w in top)
        top = [(b, w / tot) for b, w in top if w / tot > 0.02]
        tot = sum(w for _, w in top)
        for b, w in top:
            groups[b].add([vi], w / tot, "REPLACE")
    ob.parent = rig
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig


def main(out_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    paper = make_material("M_PaperAtlas", "paper")
    mask_mat = make_material("M_Mask", "mask", coat=0.15, coat_rough=0.2)
    glow = make_glow_material()

    torso_mb, arms_mb, legs_mb, glow_mb = build_body()
    rig = build_armature()
    stats = []
    for mb in (torso_mb, arms_mb, legs_mb):
        ob = mb.build(paper)
        skin(ob, mb.part, mb.fixed, mb.co, rig)
        stats.append((mb.name, len(mb.co), mb.tris()))
    gob = glow_mb.build(glow)
    skin(gob, glow_mb.part, glow_mb.fixed, glow_mb.co, rig)
    stats.append(("EyeGlow", len(glow_mb.co), glow_mb.tris()))
    mask = build_mask_object(mask_mat)
    mask_co = [v.co.copy() for v in mask.data.vertices]
    skin(mask, [None] * len(mask_co), [{"Head": 1.0}] * len(mask_co), mask_co, rig)
    mask_tris = sum(len(p.vertices) - 2 for p in mask.data.polygons)
    stats.append(("Mask", len(mask_co), mask_tris))

    for name, nv, nt in stats:
        print(f"{name:12s} verts {nv:6d}  tris {nt:6d}")
    print("total tris", sum(s[2] for s in stats), "bones", len(SK.BONES))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_path))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "poster_monster.blend"))
