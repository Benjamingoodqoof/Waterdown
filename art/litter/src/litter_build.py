#!/usr/bin/env python3
"""Builds the Litter, a swarm monster: knee-high black creatures that pour out of the vents,
and the hunched monster 30 of them make when they climb onto each other.

A creature is a lumpy, sagging, tick-like body (a narrower head end, a bloated back), its
skin wrinkled and leathery under matted, greasy hair with vent dust caught in it, and a few
coarse bristles. Two wet black eyes sit in fleshy sockets, with a pale eyeshine that can glow
in the dark; under them, a lipless slit of a mouth with needle teeth. Eight thin, knobbly,
bristled legs end in hooked claws, their knees rising above the body.

- litterling.blend: one creature, rigged (Root, Body, two bones a leg). Its textures are baked
  here, on a fixed UV layout every creature shares.
- stack.blend: the stack, rigged like a humanoid with fingers plus a slot bone per creature.
  The creatures cling at every angle, legs hooked into each other; the hand creatures spread
  their legs as fingers, the foot creatures splay theirs as toes, and the head creature's mouth
  hangs open. It reuses the litterling's textures, so the whole swarm is one texture set.

Usage: python3 litter_build.py OUT_DIR [--only litterling|stack]
"""
import argparse
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "props", "src")))
import litter_common as C  # noqa: E402
import props_lib as L  # noqa: E402
from litter_common import SIDES, V  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
BAKED = os.path.join(TEX, "baked")
TAU = 2 * math.pi
GRID = (24, 13)  # the body's longitude x latitude: the same for every creature, so UVs match
# eyes: (direction from the body's centre, size): two big wet ones, and two small ones above them
EYES = [(V(sx * 0.3, -0.88, 0.3).normalized(), 1.0) for sx in (1, -1)] + [
    (V(sx * 0.44, -0.72, 0.52).normalized(), 0.55) for sx in (1, -1)] + [
    (V(sx * 0.12, -0.86, 0.5).normalized(), 0.42) for sx in (1, -1)]
# UV layout (shared): the body above v = 0.26, the legs in a strip below, small parts at the bottom
UV_BODY = (0.26, 1.0)
UV_LEG = (0.1, 0.24)
UV_EYE, UV_TOOTH, UV_BRISTLE, UV_MOUTH = (0.06, 0.04), (0.16, 0.04), (0.26, 0.04), (0.36, 0.04)


def spot(uv, n, e=0.012):
    """UVs for a face of a small one-colour part: a little square round its spot in the layout
    (a single point would bake to nothing)."""
    u, v = uv
    return [(u - e, v - e), (u + e, v - e), (u + e, v + e), (u - e, v + e)][:n]


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def blend(a, b, k):
    if k <= 0.0:
        return {a: 1.0}
    if k >= 1.0:
        return {b: 1.0}
    return {a: 1.0 - k, b: k}


# ================================================================ mesh builder with weights and UVs
class MB:
    def __init__(self, name):
        self.name = name
        self.co, self.w, self.faces, self.fuv, self.mats, self.slots = [], [], [], [], [], []

    def vert(self, co, weights):
        self.co.append(Vector(co))
        self.w.append(weights)
        return len(self.co) - 1

    def face(self, ids, uvs, want, mat):
        a, b, c = (self.co[i] for i in ids[:3])
        if want is not None and (b - a).cross(c - a).dot(want) < 0:
            ids, uvs = ids[::-1], uvs[::-1]
        if mat not in self.slots:
            self.slots.append(mat)
        self.faces.append(ids)
        self.fuv.append(uvs)
        self.mats.append(self.slots.index(mat))

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(c) for c in self.co], [], self.faces)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, uvs in zip(me.polygons, self.fuv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
        for m in self.slots:
            me.materials.append(m)
        for poly, mi in zip(me.polygons, self.mats):
            poly.material_index = mi
        me.validate()
        me.shade_smooth()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


# ================================================================ materials
M = {}


def skin_material():
    """Leathery black skin under matted, greasy hair, wet in places, with dust on the upper
    surfaces and creases between the wrinkles."""
    m = bpy.data.materials.new("Skin")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    N = nt.nodes.new
    coord = N("ShaderNodeTexCoord")
    geo = N("ShaderNodeNewGeometry")

    def tex(kind, scale, stretch=None, **inputs):
        t = N(kind)
        t.inputs["Scale"].default_value = scale
        for k, v in inputs.items():
            t.inputs[k].default_value = v
        if stretch:
            mp = N("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = stretch
            nt.links.new(coord.outputs["Object"], mp.inputs["Vector"])
            nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        else:
            nt.links.new(coord.outputs["Object"], t.inputs["Vector"])
        return t

    def ramp(src, p0, p1, c0=(0, 0, 0, 1), c1=(1, 1, 1, 1)):
        r = N("ShaderNodeValToRGB")
        r.color_ramp.elements[0].position, r.color_ramp.elements[1].position = p0, p1
        r.color_ramp.elements[0].color, r.color_ramp.elements[1].color = c0, c1
        nt.links.new(src, r.inputs["Fac"])
        return r.outputs["Color"]

    def mix(a, bb, fac):
        n = N("ShaderNodeMix")
        n.data_type = "RGBA"
        for sock, val in (("A", a), ("B", bb), ("Factor", fac)):
            if isinstance(val, tuple):
                n.inputs[sock].default_value = val
            else:
                nt.links.new(val, n.inputs[sock])
        return n.outputs["Result"]

    def math_node(op, a, bb):
        n = N("ShaderNodeMath")
        n.operation = op
        for i, val in enumerate((a, bb)):
            if isinstance(val, (float, int)):
                n.inputs[i].default_value = val
            else:
                nt.links.new(val, n.inputs[i])
        return n.outputs[0]

    tone = tex("ShaderNodeTexNoise", 4.0, Detail=6.0)
    base = ramp(tone.outputs["Fac"], 0.35, 0.72, (0.003, 0.0026, 0.0024, 1), (0.026, 0.021, 0.018, 1))
    # coarse hair in matted streaks running back along the body (noise stretched along y)
    hair_n = tex("ShaderNodeTexNoise", 160.0, (1.0, 0.1, 1.0), Detail=3.0, Distortion=0.6)
    hair = ramp(hair_n.outputs["Fac"], 0.45, 0.62)
    patch = tex("ShaderNodeTexNoise", 6.0, Detail=3.0)
    hairy = ramp(patch.outputs["Fac"], 0.42, 0.58)  # hair in clumps, bare leathery skin between
    creases = tex("ShaderNodeTexVoronoi", 120.0, (1.0, 0.45, 1.0))
    creases.feature = "DISTANCE_TO_EDGE"
    crease = ramp(creases.outputs["Distance"], 0.0, 0.035, (1, 1, 1, 1), (0, 0, 0, 1))
    bare = math_node("SUBTRACT", 1.0, hairy)
    crease = math_node("MULTIPLY", crease, bare)  # wrinkles only show on the bare skin
    sep = N("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sep.inputs["Vector"])
    dmask = tex("ShaderNodeTexNoise", 16.0, Detail=4.0)
    dust = math_node("MULTIPLY", ramp(sep.outputs["Z"], 0.55, 0.98), ramp(dmask.outputs["Fac"], 0.52, 0.7))
    col = mix(base, (0.001, 0.001, 0.001, 1), math_node("MULTIPLY", crease, 0.7))
    col = mix(col, (0.03, 0.025, 0.021, 1), math_node("MULTIPLY", math_node("MULTIPLY", hair, hairy), 0.6))
    col = mix(col, (0.11, 0.1, 0.09, 1), math_node("MULTIPLY", dust, 0.6))  # vent dust and lint
    nt.links.new(col, b.inputs["Base Color"])
    wet = tex("ShaderNodeTexNoise", 6.5, Detail=4.0)
    wetness = ramp(wet.outputs["Fac"], 0.6, 0.72)  # small greasy, wet patches
    rough = math_node("SUBTRACT", 0.78, math_node("MULTIPLY", wetness, 0.5))
    rough = math_node("ADD", rough, math_node("MULTIPLY", dust, 0.1))
    nt.links.new(rough, b.inputs["Roughness"])
    fine = tex("ShaderNodeTexNoise", 380.0)
    h = math_node("ADD", math_node("MULTIPLY", crease, -0.22), math_node("MULTIPLY", hair, hairy))
    h = math_node("ADD", h, math_node("MULTIPLY", fine.outputs["Fac"], 0.25))
    bump = N("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.85
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Coat Weight"].default_value = 0.0
    return m


def materials():
    M["skin"] = skin_material()
    M["leg"] = L.plastic("Leg", (0.009, 0.0075, 0.007), 0.5, scuff=0.2, grain=0.12)
    M["eye"] = L.plastic("EyeBlack", (0.003, 0.0025, 0.0025), 0.06, scuff=0.0, grain=0.0)
    M["mouth"] = L.plastic("Mouth", (0.06, 0.007, 0.006), 0.08, scuff=0.02, grain=0.03)
    M["tooth"] = L.plastic("Tooth", (0.3, 0.25, 0.15), 0.4, scuff=0.2)
    M["shine"] = L.light("M_Eyeshine", (0.95, 0.85, 0.6), 0.5)


def baked_material():
    """The litterling's baked maps as one material, for the stack."""
    m = bpy.data.materials.new("M_Litter")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(kind, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(BAKED, f"litterling_body_{kind}.png"), check_existing=True)
        if noncolor:
            n.image.colorspace_settings.name = "Non-Color"
        return n

    nt.links.new(tex("color", False).outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex("roughness", True).outputs["Color"], b.inputs["Roughness"])
    nt.links.new(tex("metalness", True).outputs["Color"], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex("normal", True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    return m


# ================================================================ the creature
def mouth_factor(d, opening):
    """How deep in the mouth's slit a direction from the body's centre is (0..1)."""
    if d.y > -0.35:
        return 0.0
    u = d.x / 0.42
    if abs(u) >= 1:
        return 0.0
    zc = -0.36 + 0.05 * (1 - u * u)
    w = 0.03 + 0.07 * opening * (1 - u * u)
    return math.exp(-((d.z - zc) / w) ** 2) * (1 - u ** 6)


def body_point(d, s, off, opening):
    rx, ry, rz = (r * s for r in C.BODY_R)
    front = smooth(0.3, 0.95, -d.y)
    back = smooth(0.0, 0.8, d.y)
    pinch = 1 - 0.15 * math.exp(-((d.y + 0.42) / 0.13) ** 2)  # a waist between head and abdomen
    taper = (1 - 0.2 * front) * pinch  # the narrower head end
    x = d.x * rx * taper * (1 + 0.08 * back)
    z = d.z * rz * taper * (1 + 0.06 * back) * (0.82 if d.z < 0 else 1.0)  # a sagging belly
    p = V(x, d.y * ry, z)
    n = p.normalized()
    lump = noise.fractal(d * 2.2 + off, 1.0, 2.0, 3) * 0.055 + noise.noise(d * 13.0 + off) * 0.012
    disp = lump * 0.3 * s
    for e, es in EYES:  # sockets, with a fleshy rim round each
        a = d.angle(e)
        disp += es * (-0.016 * math.exp(-(a / (0.12 * es)) ** 2)
                      + 0.006 * math.exp(-((a - 0.2 * es) / (0.06 * es)) ** 2)) * s
    if d.z > -0.35:  # soft folds across the bloated back, like a tick's or a grub's
        for yk in (0.05, 0.3, 0.55, 0.78):
            disp -= 0.009 * s * math.exp(-((d.y - yk) / 0.045) ** 2) * smooth(-0.35, 0.0, d.z)
    disp -= mouth_factor(d, opening) * (0.035 + 0.05 * opening) * s
    return p + n * disp


def sphere_dirs():
    nl, nb = GRID
    rows = []
    for i in range(nb + 1):
        lam = -math.pi / 2 + math.pi * i / nb
        cnt = 1 if i in (0, nb) else nl
        rows.append([(V(math.cos(lam) * math.cos(math.pi / 2 + TAU * j / nl),
                        math.cos(lam) * math.sin(math.pi / 2 + TAU * j / nl), math.sin(lam)), j) for j in range(cnt)])
    return rows


SPHERE = sphere_dirs()


def creature(body, shine, c, R, s, seed, weights, opening=0.0, tufts=16, teeth=True, tiny_eyes=True):
    """One creature's body, eyes, mouth, teeth and hair tufts. R turns its own frame (x left, y
    back, z up) into the world; c is where its body's centre goes; s scales it."""
    rng = random.Random(seed)
    off = V(seed * 3.17, seed * 1.31, seed * 2.03)
    nl, nb = GRID

    def world(p):
        return c + R @ p

    ids = []
    for i, row in enumerate(SPHERE):
        ids.append([body.vert(world(body_point(d, s, off, opening)), weights) for d, _ in row])
    v0, v1 = UV_BODY
    for i in range(nb):
        a, b = ids[i], ids[i + 1]
        for j in range(nl):
            if len(a) == 1:
                q, uv = [a[0], b[(j + 1) % nl], b[j]], [((j + 0.5) / nl, v0), ((j + 1) / nl, lerp(v0, v1, (i + 1) / nb)),
                                                         (j / nl, lerp(v0, v1, (i + 1) / nb))]
            elif len(b) == 1:
                q, uv = [a[j], a[(j + 1) % nl], b[0]], [(j / nl, lerp(v0, v1, i / nb)), ((j + 1) / nl, lerp(v0, v1, i / nb)),
                                                         ((j + 0.5) / nl, v1)]
            else:
                q = [a[j], a[(j + 1) % nl], b[(j + 1) % nl], b[j]]
                uv = [(j / nl, lerp(v0, v1, i / nb)), ((j + 1) / nl, lerp(v0, v1, i / nb)),
                      ((j + 1) / nl, lerp(v0, v1, (i + 1) / nb)), (j / nl, lerp(v0, v1, (i + 1) / nb))]
            ctr = sum((body.co[x] for x in q), Vector()) / len(q)
            body.face(q, uv, ctr - c, M["skin"])
    # the mouth: a dark, wet slit lining the groove (a wide gash when it hangs open)
    def on_skin(d, lift=0.0015):
        p = body_point(d, s, off, opening)
        return world(p + p.normalized() * lift * s)

    rows = []
    for k in range(13):
        u = lerp(-0.86, 0.86, k / 12)
        zc = -0.36 + 0.05 * (1 - u * u)
        w = (0.03 + 0.07 * opening * (1 - u * u)) * (1 - abs(u) ** 4)
        rows.append([body.vert(on_skin(V(u * 0.42, -0.9, zc + sgn * w).normalized()), weights) for sgn in (1, 0, -1)])
    for k in range(12):
        for j in range(2):
            q = [rows[k][j], rows[k + 1][j], rows[k + 1][j + 1], rows[k][j + 1]]
            body.face(q, spot(UV_MOUTH, 4), R @ V(0, -1, 0), M["mouth"])

    # eyes: wet black balls in the sockets, each with a pale eyeshine glint
    for e, es in EYES:
        if es < 0.5 and not tiny_eyes:
            continue
        ec = world(body_point(e, s, off, opening) - e * 0.009 * s * es)  # sunk deep in the socket
        er = C.EYE_R * s * es
        big = es > 0.7
        small_sphere(body, ec, er, weights, M["eye"], UV_EYE, 8 if big else 6, 5 if big else 4)
        # eyeshine: a pale glint deep in the eye, which glows in the dark like an animal's
        gd = (R @ (e + V(0, 0, 0.2))).normalized()
        small_sphere(shine, ec + gd * er * 0.74, er * 0.3, weights, M["shine"], (0.5, 0.5), 6 if big else 4, 4 if big else 3)
    # needle teeth along the slit (top row always, the bottom row when the mouth is open)
    if teeth:
        rows = [(1, 11), (-1, 10)]
        for sgn, n in rows:
            for k in range(n):
                u = lerp(-0.76, 0.76, k / (n - 1)) + rng.uniform(-0.03, 0.03)
                zc = -0.36 + 0.05 * (1 - u * u)
                w = 0.03 + 0.07 * opening * (1 - u * u)
                d = V(u * 0.42, -0.9, zc + sgn * (w + 0.01)).normalized()
                base = on_skin(d, -0.004)
                length = rng.uniform(0.008, 0.02) * (1.6 if k in (1, n - 2) else 1.0)  # longer fangs near the corners
                tip = base + R @ V(rng.uniform(-0.2, 0.2), -0.35, -sgn).normalized() * length * s
                cone(body, base, tip, 0.0017 * s, weights, M["tooth"], UV_TOOTH)
    # tufts of coarse, matted hair: clumps of bristles combed back along the body
    placed = 0
    while placed < tufts:
        d = V(rng.uniform(-1, 1), rng.uniform(-0.75, 1), rng.uniform(-0.35, 1)).normalized()
        if (d.y < -0.55 and d.z < 0.5) or d.z < -0.3:
            continue  # not over the face, nor the belly
        placed += 1
        p = body_point(d, s, off, opening)
        nrm = p.normalized()
        comb = V(0, 1, 0.1) - nrm * V(0, 1, 0.1).dot(nrm)  # back along the body
        comb = comb.normalized() if comb.length > 1e-3 else nrm.orthogonal().normalized()
        for h in range(rng.choice((4, 5, 5, 6))):
            jitter = V(rng.uniform(-0.6, 0.6), rng.uniform(-0.3, 0.3), rng.uniform(-0.6, 0.6))
            base = p * 0.985 + jitter * 0.012 * s
            out = (nrm * rng.uniform(0.2, 0.5) + comb + jitter * 0.5).normalized()
            cone(body, world(base), world(base + out * rng.uniform(0.018, 0.045) * s), 0.0015 * s, weights, M["leg"],
                 UV_BRISTLE)


def small_sphere(mb, c, r, weights, mat, uv, nl=8, nb=5):
    rows = []
    for i in range(nb + 1):
        lam = -math.pi / 2 + math.pi * i / nb
        rows.append([mb.vert(c + V(math.cos(lam) * math.cos(TAU * j / nl), math.cos(lam) * math.sin(TAU * j / nl),
                                   math.sin(lam)) * r, weights) for j in range(nl)])
    for a, b in zip(rows, rows[1:]):
        for j in range(nl):
            q = [a[j], a[(j + 1) % nl], b[(j + 1) % nl], b[j]]
            mb.face(q, spot(uv, 4), sum((mb.co[x] for x in q), Vector()) / 4 - c, mat)


def cone(mb, base, tip, r, weights, mat, uv, n=3):
    T = (tip - base).normalized()
    U = T.orthogonal().normalized()
    W = T.cross(U)
    ring = [mb.vert(base + (U * math.cos(TAU * k / n) + W * math.sin(TAU * k / n)) * r, weights) for k in range(n)]
    t = mb.vert(tip, weights)
    for k in range(n):
        mb.face([ring[k], ring[(k + 1) % n], t], spot(uv, 3), (mb.co[ring[k]] + mb.co[ring[(k + 1) % n]]) / 2 - base, mat)


def spline(points, per=8):
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


def leg(mb, control, r0, r1, weights_at, n=6, per=6, joints=(), hairs=0, seed=0):
    """A thin, knobbly, tapering leg along a curve through the control points, ending in a
    claw; joints: fractions along it that bulge; hairs: bristles along it."""
    rng = random.Random(seed)
    pts = spline(control, per)
    m = len(pts) - 1
    rings, U = [], None
    l0, l1 = UV_LEG
    for i, p in enumerate(pts):
        t = i / m
        T = (pts[min(i + 1, m)] - pts[max(i - 1, 0)]).normalized()
        U = (T.orthogonal() if U is None else U - T * U.dot(T)).normalized()
        W = T.cross(U)
        r = lerp(r0, r1, t ** 0.8) * (1 + sum(0.55 * math.exp(-((t - j) / 0.03) ** 2) for j in joints))
        wt = weights_at(t)
        rings.append([(mb.vert(p + (U * math.cos(TAU * k / n) + W * math.sin(TAU * k / n)) * r, wt),
                       (t, lerp(l0, l1, k / n))) for k in range(n)])
    for i in range(m):
        for k in range(n):
            k2 = (k + 1) % n
            q = [rings[i][k][0], rings[i][k2][0], rings[i + 1][k2][0], rings[i + 1][k][0]]
            v_k2 = l1 if k2 == 0 else rings[i][k2][1][1]
            uv = [rings[i][k][1], (i / m, v_k2), ((i + 1) / m, v_k2), ((i + 1) / m, rings[i][k][1][1])]
            ctr = (pts[i] + pts[i + 1]) / 2
            mb.face(q, uv, sum((mb.co[x] for x in q), Vector()) / 4 - ctr, M["leg"])
    tip_d = (pts[-1] - pts[-2]).normalized()
    t = mb.vert(pts[-1] + tip_d * r1 * 3.0, weights_at(1.0))
    for k in range(n):
        mb.face([rings[-1][k][0], rings[-1][(k + 1) % n][0], t], spot(UV_BRISTLE, 3), tip_d, M["leg"])
    for h in range(hairs):
        i = rng.randrange(1, max(2, int(m * 0.85)))
        p, T = pts[i], (pts[i + 1] - pts[i]).normalized()
        d = (T.orthogonal() * rng.uniform(-1, 1) + T.cross(T.orthogonal()) * rng.uniform(-1, 1)).normalized()
        cone(mb, p, p + (d + T * 0.5).normalized() * rng.uniform(0.015, 0.03), 0.0018, weights_at(i / m), M["leg"],
             UV_BRISTLE)


# ================================================================ the litterling
def build_litterling():
    body, shine = MB("Body"), MB("Eyeshine")
    creature(body, shine, C.BODY_C, Matrix.Identity(3), 1.0, 1, {"Body": 1.0}, 0.0, tufts=46)
    for side, sx in SIDES:
        for k in range(C.LEGS):
            hip, knee, foot = C.leg_layout(side, sx, k)
            a, b = f"Leg{side[0]}{k + 1}A", f"Leg{side[0]}{k + 1}B"
            out = V(knee.x - C.BODY_C.x, knee.y - C.BODY_C.y, 0).normalized()
            ctl = [hip, hip + out * 0.1 + V(0, 0, 0.012), hip + out * 0.155 + V(0, 0, 0.1), knee,
                   knee.lerp(foot, 0.4) + out * 0.03, foot + V(0, 0, 0.055) + out * 0.008, foot + V(0, 0, 0.012),
                   foot - out * 0.012 + V(0, 0, 0.003)]

            def wts(t, a=a, b=b):
                if t < 0.06:
                    return blend("Body", a, t / 0.06)
                return blend(a, b, smooth(0.38, 0.48, t))

            leg(body, ctl, 0.0115, 0.0026, wts, n=5, per=4, joints=(0.2, 0.43, 0.62, 0.8), hairs=14, seed=k + 10 * (sx > 0))
    return body, shine


# ================================================================ the stack
def stack_mesh_name(slot):
    if slot.startswith("Torso"):
        return "StackTorso1" if int(slot[5:]) <= 5 else "StackTorso2"
    if slot.startswith("Head"):
        return "StackHead"
    side = "L" if slot.startswith("Left") else "R"
    return f"StackArm{side}" if "Arm" in slot else f"StackLeg{side}"


def build_stack():
    rng = random.Random(4)
    sl = C.slots()
    names = list(sl)
    meshes = {n: MB(n) for n in ("StackTorso1", "StackTorso2", "StackHead", "StackArmL", "StackArmR", "StackLegL",
                                 "StackLegR")}
    shine = MB("StackEyeshine")
    frames = {}
    for k, name in enumerate(names):
        c, size, _, front, up = sl[name]
        s = size / 0.16
        R = C.frame(front, up)
        frames[name] = (c, R, s)
        creature(meshes[stack_mesh_name(name)], shine, c, R, s, k + 3, {f"Slot_{name}": 1.0},
                 opening=1.0 if name == "Head1" else 0.0, tufts=9, tiny_eyes=name.startswith("Head"))

    def hips_of(name):
        c, R, s = frames[name]
        return [(c + R @ ((hip - C.BODY_C) * s), side, k) for side, sx in SIDES for k in range(C.LEGS)
                for hip in [C.leg_layout(side, sx, k)[0]]]

    # each creature hooks two or three legs into the ones it touches, and some leave one free
    for i, ni in enumerate(names):
        ci, Ri, si = frames[ni]
        near = [nj for nj in names if nj != ni and (frames[nj][0] - ci).length < (sl[nj][1] + sl[ni][1]) * 1.4]
        rng.shuffle(near)
        count = 1 if ("Arm5" in ni or "Leg4" in ni) else rng.choice((2, 3, 3))
        hips = hips_of(ni)
        for nj in near[:count]:
            cj, Rj, sj = frames[nj]
            u = (cj - ci).normalized()
            hip = max(hips, key=lambda h: (h[0] - ci).normalized().dot(u))[0]
            mid = (ci + cj) / 2
            outward = mid - V(0.0 if abs(mid.x) < 0.38 else math.copysign(0.5, mid.x), 0.03, mid.z)
            v = outward - u * outward.dot(u)
            v = v.normalized() if v.length > 1e-4 else u.orthogonal().normalized()
            grip = cj + ((ci - cj).normalized() + v * 0.9).normalized() * sl[nj][1] * 0.95
            knee = hip.lerp(grip, 0.45) + v * rng.uniform(0.07, 0.11)
            hook = grip + (cj - grip).normalized() * 0.02
            ctl = [hip, hip.lerp(knee, 0.5) + v * 0.02, knee, knee.lerp(grip, 0.55) + v * 0.015, grip, hook]
            leg(meshes[stack_mesh_name(ni)], ctl, 0.011 * si, 0.003 * si,
                lambda t, a=ni, b=nj: blend(f"Slot_{a}", f"Slot_{b}", smooth(0.35, 0.8, t)),
                n=5, per=3, joints=(0.4,), hairs=1, seed=i)
        if not ni.endswith(("Arm5", "Leg4", "Head1")) and rng.random() < 0.8:  # a free leg, hanging out of the pile
            out = V(ci.x, ci.y + 0.05, 0).normalized() if abs(ci.x) > 0.05 else V(0, -1, 0)
            hip = max(hips, key=lambda h: (h[0] - ci).normalized().dot(out))[0]
            knee = hip + out * 0.16 + V(0, 0, 0.06)
            tip = knee + out * 0.08 + V(0, 0, -0.2)
            leg(meshes[stack_mesh_name(ni)], [hip, knee, tip, tip + out * -0.015 + V(0, 0, -0.01)], 0.011 * si,
                0.003 * si, lambda t, a=ni: {f"Slot_{a}": 1.0}, n=5, per=4, joints=(0.4,), hairs=2, seed=i + 50)
    # the hands: the hand creatures' legs, spread as long, clawed fingers
    for side, sx in SIDES:
        c, r, d, pn, a = C.hand_frame(side, sx)
        for f, (base, kn, tip) in C.finger_layout(side, sx).items():
            b1, b2 = f"{side}{f}1", f"{side}{f}2"
            claw = tip + ((tip - kn).normalized() + pn * 0.9).normalized() * 0.03
            ctl = [base - (kn - base).normalized() * 0.02, base.lerp(kn, 0.5), kn, kn.lerp(tip, 0.55), tip, claw]
            leg(meshes[f"StackArm{side[0]}"], ctl, 0.013, 0.0035,
                lambda t, b1=b1, b2=b2, side=side: (blend(f"Slot_{side}Arm5", b1, t / 0.1) if t < 0.1
                                                    else blend(b1, b2, smooth(0.42, 0.52, t))),
                n=6, per=5, joints=(0.42, 0.75), hairs=3, seed=hash(f) % 97)
        # the feet: the foot creatures' legs, splayed on the floor as toes
        c, size, _, _, _ = sl[f"{side}Leg4"]
        for k, ang in enumerate((-60, -25, 10, 45, 150)):
            aa = math.radians(ang)
            dd = V(math.sin(aa) * sx * 0.9, -math.cos(aa), 0).normalized()
            base = c + (dd * 0.7 + V(0, 0, -0.55)).normalized() * size * 0.8
            reach = 0.32 if k < 4 else 0.22
            kn = c + dd * (size + 0.08) + V(0, 0, -0.03)
            tip = V(c.x, c.y, 0) + dd * reach + V(0, 0, 0.012)
            ctl = [base, kn, kn.lerp(tip, 0.5) + V(0, 0, 0.025), tip, tip + dd * 0.02 + V(0, 0, -0.008)]
            leg(meshes[f"StackLeg{side[0]}"], ctl, 0.013, 0.004, lambda t, side=side: {f"Slot_{side}Leg4": 1.0},
                n=6, per=4, joints=(0.3,), hairs=2, seed=k + 40)
    return meshes, shine


def build_mass(rig):
    """The crush of bodies inside the pile: one lumpy mass along the skeleton, which the
    creatures sink half into and cling to, so the stack reads as one monster's body rather than
    a heap of separate balls. Metaballs, lumped with noise and decimated."""
    J = C.SJ
    meta = bpy.data.metaballs.new("MassMeta")
    meta.resolution = meta.render_resolution = 0.03
    meta.threshold = 0.6

    def chain(a, b, r0, r1, n):  # r: the surface radius wanted (a ball's own radius is ~1.75x)
        for i in range(n + 1):
            e = meta.elements.new(type="BALL")
            e.co = a.lerp(b, i / n)
            e.radius = lerp(r0, r1, i / n) * 1.75

    for x in (-0.12, 0.0, 0.12):  # a hunched, flattened barrel, thinner than the creatures on it
        chain(J["root"] + V(x * 0.7, 0.02, 0.08), J["neck"] + V(x * 1.1, 0.06, -0.16), 0.1, 0.11, 8)
    chain(J["neck"] + V(0, 0.04, -0.14), C.slots()["Head1"][0] + V(0, 0.06, 0), 0.08, 0.07, 3)
    chain(J["neck"] + V(0, 0.06, -0.1), C.slots()["Head2"][0] + V(0, 0.03, -0.04), 0.08, 0.06, 3)
    for side, sx in SIDES:
        chain(J["neck"] + V(0.18 * sx, 0.03, -0.14), J[f"shoulder_{side}"], 0.08, 0.065, 3)
        chain(J[f"shoulder_{side}"], J[f"elbow_{side}"], 0.065, 0.055, 4)
        chain(J[f"elbow_{side}"], J[f"wrist_{side}"], 0.055, 0.05, 4)
        chain(J["root"] + V(0.08 * sx, 0.03, 0.02), J[f"hip_{side}"], 0.1, 0.085, 2)
        chain(J[f"hip_{side}"], J[f"knee_{side}"], 0.08, 0.06, 4)
        chain(J[f"knee_{side}"], J[f"ankle_{side}"], 0.06, 0.05, 4)
    tmp = bpy.data.objects.new("MassMeta", meta)
    bpy.context.scene.collection.objects.link(tmp)
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    me.name = "StackMass"
    for v in me.vertices:  # lumps: the bodies packed in under the skin
        q = v.co * 1.0
        v.co += v.normal * (noise.fractal(q * 6.0, 1.0, 2.0, 3) * 0.035 + noise.noise(q * 22.0) * 0.008)
    ob = bpy.data.objects.new("StackMass", me)
    bpy.context.scene.collection.objects.link(ob)
    dec = ob.modifiers.new("Decimate", "DECIMATE")
    dec.ratio = min(1.0, 3600 / max(1, len(me.polygons) * 2))
    L.activate(ob)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    me = ob.data
    me.shade_smooth()
    me.materials.append(M["skin"])
    weights = limb_weights(rig)
    groups = {}
    for v in me.vertices:
        for n, w in weights(v.co).items():
            if n not in groups:
                groups[n] = ob.vertex_groups.new(name=n)
            groups[n].add([v.index], w, "REPLACE")
    return ob


def limb_weights(rig):
    """p -> weights to the nearest (up to three) limb bones."""
    bones = [(b.name, b.head_local.copy(), b.tail_local.copy()) for b in rig.data.bones
             if not b.name.startswith(("Slot_", "Root", "Humanoid")) and not any(f in b.name for f in C.FINGERS)]

    def weights(p):
        ds = []
        for name, h, t in bones:
            seg = t - h
            k = max(0.0, min(1.0, (p - h).dot(seg) / seg.length_squared))
            ds.append(((p - (h + seg * k)).length, name))
        ds.sort()
        near = [(1.0 / (d ** 4 + 1e-6), n) for d, n in ds[:3]]
        tot = sum(w for w, _ in near)
        return {n: w / tot for w, n in near if w / tot > 0.02}
    return weights


def build_crush(mass, rig, shine):
    """What shows of the creatures packed inside, between the ones clinging on: legs jutting out
    of the mass and pairs of eyes peering out of it."""
    rng = random.Random(77)
    crush = MB("StackCrush")
    weights = limb_weights(rig)
    sl = C.slots()
    clear = [(c, size) for c, size, *_ in sl.values()]
    used = []
    verts = [(v.co.copy(), v.normal.copy()) for v in mass.data.vertices]
    rng.shuffle(verts)
    legs = eyes = 0
    for p, n in verts:
        if legs >= 26 and eyes >= 18:
            break
        if n.z < -0.4 or p.z < 0.3 or any((p - c).length < size * 1.05 for c, size in clear):
            continue  # not under the creatures clinging on, nor facing the floor
        if any((p - q).length < 0.09 for q in used):
            continue
        used.append(p)
        t = n.cross(V(0, 0, 1))
        t = t.normalized() if t.length > 1e-3 else V(1, 0, 0)
        w = weights(p)
        if eyes < 18 and (legs >= 26 or rng.random() < 0.45):
            eyes += 1
            er = C.EYE_R * rng.uniform(0.7, 0.95)
            for side in (-1, 1):
                ec = p + t * side * er * 1.6 - n * er * 0.35
                small_sphere(crush, ec, er, w, M["eye"], UV_EYE, 6, 4)
                g = (n + V(0, 0, 0.25)).normalized()
                small_sphere(shine, ec + g * er * 0.74, er * 0.3, w, M["shine"], (0.5, 0.5), 4, 3)
        else:
            legs += 1
            side = t * rng.uniform(-0.6, 0.6)
            knee = p + n * rng.uniform(0.07, 0.11) + V(0, 0, rng.uniform(0.0, 0.05)) + side * 0.03
            tip = knee + (n * 0.4 + V(0, 0, -1) + side).normalized() * rng.uniform(0.09, 0.15)
            ctl = [p - n * 0.02, p + n * 0.035, knee, knee.lerp(tip, 0.55) + n * 0.01, tip, tip + n * -0.012]
            leg(crush, ctl, 0.009, 0.0025, lambda u, w=w: w, n=5, per=3, joints=(0.45,), hairs=2, seed=legs + 300)
    return crush


# ================================================================ rigs


# ================================================================ rigs
def armature(name, bones):
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    L.activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for bname, spec in bones.items():
        h, t, parent = spec[:3]
        eb = arm.edit_bones.new(bname)
        eb.head, eb.tail = h, t
        if len(spec) > 3 and spec[3] is not None:
            eb.align_roll(spec[3])
        ebs[bname] = eb
    for bname, spec in bones.items():
        if spec[2]:
            ebs[bname].parent = ebs[spec[2]]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    if a.only in (None, "litterling"):
        L.reset()
        materials()
        body, shine = build_litterling()
        rig = armature("Litterling_Rig", C.litterling_bones())
        ob_b, ob_s = body.build(), shine.build()
        L.bake(ob_b, 1024, "litterling_body", BAKED, unwrap=False)
        skin(ob_b, body.w, rig)
        skin(ob_s, shine.w, rig)
        print("litterling: Body", L.tris(ob_b), "Eyeshine", L.tris(ob_s))
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "litterling.blend"))
    if a.only in (None, "stack"):
        L.reset()
        materials()
        meshes, shine = build_stack()
        rig = armature("Stack_Rig", C.stack_bones())
        litter = baked_material()
        mass = build_mass(rig)
        crush = build_crush(mass, rig, shine)
        L.bake(mass, 1024, "stack_mass", BAKED)
        mass.parent = rig
        mass.modifiers.new("Armature", "ARMATURE").object = rig
        total = L.tris(mass)
        print(f"  {'StackMass':14s} tris {total:6d}")
        for mb in list(meshes.values()) + [crush, shine]:
            ob = mb.build()
            if mb is not shine:
                ob.data.materials.clear()
                ob.data.materials.append(litter)
            skin(ob, mb.w, rig)
            total += L.tris(ob)
            print(f"  {mb.name:14s} tris {L.tris(ob):6d}")
        print("stack total tris", total)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "stack.blend"))


if __name__ == "__main__":
    main()
