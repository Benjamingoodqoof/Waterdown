"""Geometry helpers for the poster monster: body surfaces, a mesh builder that records
skinning hints per vertex, poster UV helpers and the primitive builders."""
import math
import random

import bpy  # noqa: F401,I001  (bpy must load before bmesh/mathutils)
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

import common as C
import skeleton as SK
from skeleton import V

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
        (1.82, -0.004, 0.160, 0.115), (1.89, 0.002, 0.170, 0.110), (1.95, 0.012, 0.176, 0.096),
        (2.00, 0.016, 0.130, 0.078), (2.05, 0.016, 0.050, 0.046),
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
        if material:
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


def add_band(mb, surf, b, width, off, part, segs=14, tilt=0.012, fixed=None, snap=None):
    """Packing tape wrapped around a tube, optionally laid onto the merged body."""
    u0, v0, u1, v1 = region_uv("tape")
    ph = rng.uniform(0, 2 * math.pi)
    rows = []
    for r in range(3):
        row = []
        for k in range(segs + 1):
            th = 2 * math.pi * k / segs
            bb = b + (r / 2 - 0.5) * width + tilt * math.sin(th + ph)
            p, n = surf.pos_theta(th, bb, 0.0)
            if snap:
                p, n = snap(p)
            p = p + n * (off + 0.0015 * noise.noise(V(th * 3, r, b * 10)))
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


class Snap:
    """Moves points onto the merged body: nearest surface point and its normal."""

    def __init__(self, mesh):
        self.bvh = BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices], [p.vertices[:] for p in mesh.polygons])

    def __call__(self, p):
        loc, nrm, _, _ = self.bvh.find_nearest(p)
        return loc, nrm


def add_sheet(mb, place, w, h, off, uv, part, psi=0.0, snap=None, seg=(0.03, 0.045), max_n=9, wave=0.0028,
              crumple=0.0, freq=14.0, edge_lift=0.004, torn=0.03, missing_corner=0.25, cut=None, lift=None,
              fixed=None, peel=None):
    """A poster laid onto the body. place(a, b) -> (point, normal) for sheet coordinates in meters
    from the sheet center (a across, b up); with snap the point is moved onto the merged body.
    The bottom edge lifts a little so overlapping rows read as shingles. The gentle waves are a
    world-space field, so overlapping sheets bend together instead of cutting through each other.
    peel=dict(name, parent, attach, amount): below `attach` (-0.5..0.5) the sheet comes away from
    the body, driven by two flap bones; peeling sheets are double sided."""
    nu = max(2, min(max_n, math.ceil(w / seg[0])))
    nv = max(2, min(max_n, math.ceil(h / seg[1])))
    if peel:
        nu += nu % 2  # an even count gives a middle column for the flap bones
        nv = max(nv, 6)
    u0, v0, u1, v1 = uv
    cs, sn = math.cos(psi), math.sin(psi)
    seed = V(rng.uniform(0, 100), rng.uniform(0, 100), rng.uniform(0, 100))
    corner = (rng.choice((-1, 1)), rng.choice((-1, 1))) if rng.random() < missing_corner else None
    if corner and peel:
        corner = (corner[0], 1)  # keep the hanging bottom edge whole

    def surface(s, q):
        lx, ly = s * w, q * h
        p, n = place(lx * cs - ly * sn, lx * sn + ly * cs)
        return snap(p) if snap else (p, n)

    # a peeling sheet pulls away as one piece, along the normal at its middle (pushing along
    # each vertex normal would fan it out into a cone around a thin limb)
    peel_dir = surface(0.0, peel["attach"])[1] if peel else None

    def displace(p, n, s, q):
        d = off + wave * (noise.noise(p * 6.0) + 0.5 * noise.noise(p * 17.0 + V(4.0, 2.0, 9.0)))
        if crumple:
            d += crumple * (noise.noise(p * freq + seed) + 0.5 * abs(noise.noise(p * freq * 2.1 + seed)) - 0.25)
        d += edge_lift * smooth(-0.32, -0.5, q)
        if lift:
            d += lift(p)
        p = p + n * d
        if peel and q < peel["attach"]:
            p = p + peel_dir * (peel["amount"] * ((peel["attach"] - q) / (peel["attach"] + 0.5)) ** 1.6)
        return p

    verts = {}
    for j in range(nv + 1):
        for i in range(nu + 1):
            s, q = i / nu - 0.5, j / nv - 0.5
            if i in (0, nu) or j in (0, nv):  # torn edge
                jit = noise.noise(V(s * 9.1, q * 9.7, 0) + seed) * torn
                s, q = s * (1 + jit), q * (1 + jit)
                if corner and i in (0, nu) and j in (0, nv) and (math.copysign(1, s), math.copysign(1, q)) == corner:
                    s, q = s * 0.6, q * 0.6
            p, n = surface(s, q)
            verts[i, j] = (displace(p, n, s, q), n, s, q)

    def flap_weights(q):
        t = (peel["attach"] - q) / (peel["attach"] + 0.5)
        w1 = smooth(0.0, 0.35, t) * (1 - smooth(0.5, 0.85, t))
        w2 = smooth(0.5, 0.85, t)
        return {peel["parent"]: 1 - w1 - w2, f"{peel['name']}1": w1, f"{peel['name']}2": w2}

    if peel:
        def at(q):
            p, n = surface(0.0, q)
            return displace(p, n, 0.0, q)
        a = peel["attach"]
        SK.add_flap_bones(peel["name"], at(a), at((a - 0.5) / 2), at(-0.5), peel["parent"], verts[nu // 2, nv][1])

    sides = [(1.0, uv)] + ([(-1.0, back_uv())] if peel else [])
    for sign, (a0, b0, a1, b1) in sides:
        ids = {}
        for (i, j), (p, n, s, q) in verts.items():
            fx = flap_weights(q) if (peel and q < peel["attach"]) else fixed
            uv_ = (min(max(a0 + (s + 0.5) * (a1 - a0), a0 - 0.003), a1 + 0.003),
                   min(max(b0 + (q + 0.5) * (b1 - b0), b0 - 0.003), b1 + 0.003))
            ids[i, j] = (mb.add_vert(p if sign > 0 else p - n * 0.0012, part if fx is None else None, fx), uv_, n)
        for j in range(nv):
            for i in range(nu):
                corners = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
                if cut and any(cut(verts[c][0]) for c in corners):
                    continue
                quad = [ids[c] for c in corners]
                mb.add_oriented([(x[0], x[1]) for x in quad], sum((x[2] for x in quad), Vector()) * sign)


def wrap_rows(mb, surf, part, n_around, b0, b1, ring_h, base_off, snap, theta0=0.0, overlap=0.05,
              ring_step=0.0025, sheet_step=0.0012, peels=None, skip=0.02, cut=None, lift=None, extra_w=0.035,
              seg=(0.03, 0.045), max_n=8):
    """Covers a tube with upright posters in overlapping rings, bottom to top. Each ring sits a
    little further out than the one below and each sheet a little further than its neighbour,
    so the layering is always clean. Alternate rings are offset like brickwork.
    peels: {(ring, sheet): peel dict} for sheets that come away from the body; an older poster
    is laid under each so the peel uncovers paper, not a hole."""
    peels = peels or {}
    span = b1 - b0
    rings = max(1, round((span - overlap) / (ring_h - overlap)))
    step = (span - overlap) / rings
    h = step + overlap
    for r in range(rings):
        bc = b0 + h / 2 + r * step
        circ = 2 * math.pi * surf.rmean(bc)
        for k in range(n_around):
            peel = peels.get((r, k))
            if not peel and rng.random() < skip:
                continue  # a sheet has fallen off; the pulp shows through
            th = theta0 + 2 * math.pi * (k + 0.5 * (r % 2)) / n_around + rng.gauss(0, 0.05)
            w = circ / n_around + extra_w + rng.uniform(0, 0.02)
            hh = h + rng.uniform(-0.01, 0.02)
            bs = bc + rng.uniform(-0.012, 0.012)
            pc, _ = surf.pos_theta(th, bs, 0.0)

            def place(a, b, th=th, bs=bs):
                return surf.pos_theta(th + a / surf.rmean(bs + b), bs + b, 0.0)

            off = base_off + r * ring_step + k * sheet_step
            if peel:
                add_sheet(mb, place, w * 0.92, hh * 0.92, off - 0.0006, poster_uv(pick_cell(pc.z), w, hh, (0.85, 1.0)),
                          part, snap=snap, seg=seg, max_n=max_n, cut=cut, lift=lift, missing_corner=0.0)
            add_sheet(mb, place, w, hh, off, poster_uv(pick_cell(pc.z), w, hh, (0.85, 1.0)), part,
                      psi=rng.gauss(0, 0.035), snap=snap, seg=seg, max_n=max_n, cut=cut, lift=lift, peel=peel)

