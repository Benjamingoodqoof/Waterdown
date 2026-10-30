#!/usr/bin/env python3
"""Builds the Receiver, the floor-4 monster: an 8 ft man made of thick, tangled, coiled black
phone cord, with a smoked black glass phone for a head (dirty water inside, the dial torn out
of its face), the dial set into his chest like a heart, and his own handset in his left hand.
Rigged for Roblox. Saves a .blend.

The cords are laid like muscle: ribs hooping round a barrel chest, cords fanning out of the
dial over the shoulders and down the arms, a narrow twisted waist, bundles that swell into
biceps, forearms, thighs and calves, bound at the joints, splaying into claws and spilling
across the floor round his feet.

Usage: python3 receiver_build.py OUT.blend
"""
import math
import os
import random
import sys

import bpy  # noqa: I001  (bpy must load before mathutils and bmesh)
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import receiver_common as C  # noqa: E402
from receiver_common import J, SIDES, V, in_region  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
rng = random.Random(11)
TAU = 2 * math.pi
CORD_R = 0.03  # the body's cords: thick
WRAP_R = 0.02  # cords bound round the joints
FINGER_R = 0.019


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
    def __init__(self, name, material):
        self.name, self.material = name, material
        self.co, self.w, self.faces, self.fuv = [], [], [], []

    def vert(self, co, weights):
        self.co.append(Vector(co))
        self.w.append(weights)
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

    def build(self):
        me = bpy.data.meshes.new(self.name)
        me.from_pydata([tuple(c) for c in self.co], [], self.faces)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, uvs in zip(me.polygons, self.fuv):
            for li, uv in zip(poly.loop_indices, uvs):
                uvl.data[li].uv = uv
        me.materials.append(MATS[self.material])
        me.shade_smooth()
        me.validate()
        ob = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


MESHES = {}


def mesh(name, material="cord"):
    if name not in MESHES:
        MESHES[name] = MB(name, material)
    return MESHES[name]


# ================================================================ curves
def catmull(points, per_seg=8):
    """A smooth curve through the control points (centripetal-ish Catmull-Rom)."""
    pts = [Vector(p) for p in points]
    if len(pts) < 2:
        return pts
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(per_seg):
            t = k / per_seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def resample(pts, step):
    """Points every `step` meters along a polyline (at least 2)."""
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    n = max(1, round(acc[-1] / step))
    out = []
    j = 1
    for k in range(n + 1):
        s = acc[-1] * k / n
        while j < len(acc) - 1 and acc[j] < s:
            j += 1
        f = (s - acc[j - 1]) / max(1e-9, acc[j] - acc[j - 1])
        out.append(pts[j - 1].lerp(pts[j], min(1.0, max(0.0, f))))
    return out


def frames(pts):
    """Tangents and rotation-minimising normals along a polyline (double reflection)."""
    n = len(pts)
    T = []
    for i in range(n):
        d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        T.append(d.normalized() if d.length > 1e-9 else V(0, 0, 1))
    ref = V(0, 0, 1) if abs(T[0].z) < 0.9 else V(1, 0, 0)
    N = [(ref - T[0] * ref.dot(T[0])).normalized()]
    for i in range(n - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = v1.dot(v1)
        if c1 < 1e-12:
            N.append(N[-1])
            continue
        rL = N[i] - v1 * (2 / c1 * v1.dot(N[i]))
        tL = T[i] - v1 * (2 / c1 * v1.dot(T[i]))
        v2 = T[i + 1] - tL
        c2 = v2.dot(v2)
        r = rL - v2 * (2 / c2 * v2.dot(rL)) if c2 > 1e-12 else rL
        N.append((r - T[i + 1] * r.dot(T[i + 1])).normalized())
    return T, N


# ================================================================ skinning
BONES = C.bones()
# how far round each bone its flesh reaches, for the envelope weights
REACH = {"LowerTorso": 0.13, "UpperTorso": 0.21, "Head": 0.12, "DialSpin": 0.0}
for _s, _ in SIDES:
    REACH.update({f"{_s}UpperArm": 0.07, f"{_s}LowerArm": 0.06, f"{_s}Hand": 0.05, f"{_s}UpperLeg": 0.1,
                  f"{_s}LowerLeg": 0.08, f"{_s}Foot": 0.06})
    for _f in C.FINGERS:
        REACH[f"{_s}{_f}1"] = REACH[f"{_s}{_f}2"] = 0.015


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-9, ab.dot(ab))))
    return (p - (a + ab * t)).length


def envelope(p, allowed):
    ws = {}
    for b in allowed:
        h, t, _ = BONES[b]
        d = max(0.0, seg_dist(p, h, t) - REACH[b])
        ws[b] = 1.0 / (d + 0.03) ** 4
    top = sorted(ws.items(), key=lambda kv: -kv[1])[:3]
    tot = sum(w for _, w in top)
    return {b: w / tot for b, w in top}


def chain(side, *parts):
    return [f"{side}{p}" for p in parts]


def smooth_weights(wl, k=3):
    out = []
    for i in range(len(wl)):
        acc = {}
        lo, hi = max(0, i - k), min(len(wl), i + k + 1)
        for j in range(lo, hi):
            for b, w in wl[j].items():
                acc[b] = acc.get(b, 0.0) + w
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(w for _, w in top)
        out.append({b: w / tot for b, w in top if w / tot > 0.01})
    return out


# ================================================================ cords
ENDS = []  # (kind, point, direction, radius, weights) for plugs, copper and claw tips


def cord(mesh_name, control, allowed, r=CORD_R, variant=0, sides=8, step=0.036, ends=("cap", "cap"),
         weights=None, smooth_curve=True):
    """A coiled cord along a smooth curve through the control points. allowed: bones it may follow
    (or weights=fixed dict). ends: 'cap' (rounded), 'tuck' (open, hidden in something), or
    'plug' / 'fray' / 'claw' (a cap, plus that detail added to the Details mesh)."""
    mb = mesh(mesh_name)
    pts = resample(catmull(control) if smooth_curve else [Vector(p) for p in control], step)
    T, N = frames(pts)
    wl = [weights] * len(pts) if weights else smooth_weights([envelope(p, allowed) for p in pts])
    u0 = 0.5 * variant
    s = 0.0
    rings = []
    for i, p in enumerate(pts):
        if i:
            s += (p - pts[i - 1]).length
        B = T[i].cross(N[i])
        ring = []
        for j in range(sides + 1):
            a = TAU * j / sides
            q = p + (N[i] * math.cos(a) + B * math.sin(a)) * r
            ring.append((mb.vert(q, wl[i]), (u0 + 0.5 * j / sides, s / C.CORD_TILE)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(sides):
            q = [rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]]
            ctr = (pts[i] + pts[i + 1]) / 2
            mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - ctr)
    for idx, sign, kind in ((0, -1, ends[0]), (len(pts) - 1, 1, ends[1])):
        if kind == "tuck":
            continue
        p, t = pts[idx], T[idx] * sign
        B = T[idx].cross(N[idx])
        prev = rings[idx]
        for k, (f_out, f_r) in enumerate(((0.45, 0.85), (0.8, 0.5))):  # a rounded end
            c = p + t * (r * f_out)
            ring = []
            for j in range(sides + 1):
                a = TAU * j / sides
                ring.append((mb.vert(c + (N[idx] * math.cos(a) + B * math.sin(a)) * r * f_r, wl[idx]),
                             (u0 + 0.5 * j / sides, (s if sign > 0 else 0.0) + sign * 0.01 * (k + 1))))
            for j in range(sides):
                q = [prev[j], prev[j + 1], ring[j + 1], ring[j]]
                mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - p)
            prev = ring
        tip = (mb.vert(p + t * r, wl[idx]), (u0 + 0.25, s))
        for j in range(sides):
            mb.face([prev[j], prev[j + 1], tip], t)
        if kind in ("plug", "fray", "claw"):
            ENDS.append((kind, p + t * r * 0.6, t, r, wl[idx]))
    return pts


def helix_wrap(mesh_name, center, axis, radius, length, turns, allowed, r=WRAP_R, phase=0.0, ends=("tuck", "fray")):
    """A cord bound round a joint: a few tight turns about the axis."""
    axis = axis.normalized()
    ref = V(1, 0, 0) if abs(axis.x) < 0.9 else V(0, 1, 0)
    U = (ref - axis * ref.dot(axis)).normalized()
    W = axis.cross(U)
    n = int(turns * 14)
    pts = []
    for k in range(n + 1):
        t = k / n
        a = phase + TAU * turns * t
        pts.append(center + axis * (length * (t - 0.5)) + (U * math.cos(a) + W * math.sin(a)) * radius)
    return cord(mesh_name, pts, allowed, r=r, ends=ends, step=0.02, smooth_curve=False)


# ---------------------------------------------------------------- the torso's surface
TORSO = [  # z, center y, half width, half depth
    (0.96, 0.06, 0.13, 0.105), (1.03, 0.05, 0.175, 0.125), (1.1, 0.05, 0.18, 0.125),
    (1.18, 0.055, 0.155, 0.112), (1.26, 0.065, 0.112, 0.086), (1.32, 0.07, 0.1, 0.08),
    (1.41, 0.06, 0.13, 0.1), (1.51, 0.035, 0.2, 0.14), (1.61, 0.0, 0.25, 0.172),
    (1.71, -0.02, 0.28, 0.186), (1.8, -0.02, 0.285, 0.19), (1.88, 0.0, 0.25, 0.165),
    (1.94, -0.04, 0.17, 0.12), (2.0, -0.1, 0.085, 0.075),
]


def torso_at(theta, z, inset=None):
    """A point on the torso's surface (a cord's centre, so inset by its radius). theta: degrees
    from +X (his left); -90 is the front."""
    cy, rx, ry = table(TORSO, z)
    inset = CORD_R if inset is None else inset
    a = math.radians(theta)
    return V((rx - inset) * math.cos(a), cy + (ry - inset) * math.sin(a), z)


def dial_frame():
    n = C.DIAL_NORMAL
    up = (V(0, 0, 1) - n * n.z).normalized()
    right = (V(1, 0, 0) - n * n.x - up * up.x).normalized()
    return J["dial"], n, up, right


def dial_at(clock, radius, depth=0.0):
    """A point on the dial: clock angle (degrees clockwise from the top, from the front)."""
    c, n, up, right = dial_frame()
    a = math.radians(clock)
    return c + (right * math.sin(a) + up * math.cos(a)) * radius + n * depth


def into_dial(clock):
    """The last two control points of a cord that dives in under the dial's chrome ring."""
    return [dial_at(clock, C.DIAL["ring"] + 0.035, -0.015), dial_at(clock, C.DIAL["ring"] - 0.015, -0.04)]


# ---------------------------------------------------------------- limbs
def limb_frame(a, b, sx):
    W = (b - a).normalized()
    out = (V(sx, 0, 0) - W * W.dot(V(sx, 0, 0))).normalized()
    fwd = W.cross(out)
    if fwd.y > 0:
        fwd = -fwd
    return W, out, fwd


def limb_at(a, b, sx, t, phi, radius):
    """A point round a limb from joint a to b: t along it, phi degrees round (0 out, 90 front)."""
    W, out, fwd = limb_frame(a, b, sx)
    p = math.radians(phi)
    return a.lerp(b, t) + (out * math.cos(p) + fwd * math.sin(p)) * radius


# muscle: the outside of each limb's bundle, by t along it and phi round it
def upper_arm_r(t, phi):
    p = math.radians(phi)
    return (table([(0, 0.085), (0.3, 0.085), (0.65, 0.08), (1.0, 0.066)], t)[0]
            + 0.024 * g((t - 0.5) / 0.22) * max(0.0, math.sin(p))  # biceps
            + 0.016 * g((t - 0.35) / 0.2) * max(0.0, -math.sin(p))  # triceps
            + 0.03 * g(t / 0.16) * max(0.0, math.cos(p) * 0.5 + 0.5))  # deltoid


def forearm_r(t, phi):
    p = math.radians(phi)
    return (table([(0, 0.07), (0.25, 0.08), (0.6, 0.066), (1.0, 0.05)], t)[0]
            + 0.016 * g((t - 0.25) / 0.2) * max(0.0, math.cos(p)))


def thigh_r(t, phi):
    p = math.radians(phi)
    return (table([(0, 0.12), (0.3, 0.135), (0.7, 0.112), (1.0, 0.086)], t)[0]
            + 0.02 * g((t - 0.45) / 0.25) * max(0.0, math.sin(p)))


def shin_r(t, phi):
    p = math.radians(phi)
    return (table([(0, 0.082), (0.3, 0.08), (0.65, 0.066), (1.0, 0.056)], t)[0]
            + 0.036 * g((t - 0.28) / 0.17) * max(0.0, -math.sin(p))  # calf
            + 0.012 * g((t - 0.3) / 0.2) * max(0.0, -math.cos(p)))


def arm_points(side, sx, phi0, phi1, stop="wrist", twist=(80, -50)):
    """Control points down the arm for a cord that enters the shoulder at angle phi0 and leaves
    the elbow at phi1 (degrees round the limb). stop: 'elbow', 'forearm' (dives into the middle
    of the forearm) or 'wrist'."""
    sh, el, wr = J[f"shoulder_{side}"], J[f"elbow_{side}"], J[f"wrist_{side}"]
    pts = []
    for t in (0.12, 0.35, 0.6, 0.85):
        phi = lerp(phi0, phi1, t) + twist[0] * t
        pts.append(limb_at(sh, el, sx, t, phi, upper_arm_r(t, phi) - CORD_R))
    phi_e = phi1 + twist[0]
    pts.append(limb_at(sh, el, sx, 1.0, phi_e, upper_arm_r(1.0, phi_e) - CORD_R + 0.006))
    if stop == "elbow":
        pts.append(limb_at(el, wr, sx, 0.08, phi_e, 0.02))
        return pts
    ts = (0.2, 0.45, 0.68) if stop == "forearm" else (0.2, 0.45, 0.7, 0.9)
    for t in ts:
        phi = phi_e + twist[1] * t
        pts.append(limb_at(el, wr, sx, t, phi, forearm_r(t, phi) - CORD_R))
    if stop == "forearm":
        pts.append(limb_at(el, wr, sx, 0.8, phi_e + twist[1], 0.01))
    else:
        pts.append(limb_at(el, wr, sx, 1.03, phi_e + twist[1], 0.01))
    return pts


def leg_points(side, sx, phi0, stop="ankle", twist=(70, -55)):
    """Control points down the leg; stop: 'knee', 'shin' (dives into the calf) or 'ankle'."""
    hp, kn, an = J[f"hip_{side}"], J[f"knee_{side}"], J[f"ankle_{side}"]
    pts = []
    for t in (0.08, 0.3, 0.55, 0.8):
        phi = phi0 + twist[0] * t
        pts.append(limb_at(hp, kn, sx, t, phi, thigh_r(t, phi) - CORD_R))
    phi_k = phi0 + twist[0]
    pts.append(limb_at(hp, kn, sx, 1.0, phi_k, thigh_r(1.0, phi_k) - CORD_R + 0.004))
    if stop == "knee":
        pts.append(limb_at(kn, an, sx, 0.1, phi_k, 0.02))
        return pts
    ts = (0.15, 0.35, 0.55) if stop == "shin" else (0.15, 0.35, 0.6, 0.85)
    for t in ts:
        phi = phi_k + twist[1] * t
        pts.append(limb_at(kn, an, sx, t, phi, shin_r(t, phi) - CORD_R))
    if stop == "shin":
        pts.append(limb_at(kn, an, sx, 0.68, phi_k + twist[1], 0.01))
    else:
        pts.append(limb_at(kn, an, sx, 1.0, phi_k + twist[1], 0.012))
        pts.append(an + V(0, -0.005, -0.05))
    return pts


# ================================================================ the body
def build_torso():
    torso = ["LowerTorso", "UpperTorso"]
    # ribs: hoops from beside the spine, round the side, under the dial's ring
    for side, sx in SIDES:
        for k, (zb, clock) in enumerate(((1.9, 25), (1.82, 55), (1.74, 85), (1.65, 115), (1.56, 145))):
            ctl = []
            for th in (100, 70, 35, 0, -30, -50):
                th_s = th if sx > 0 else 180 - th
                frac = (100 - th) / 150
                ctl.append(torso_at(th_s, zb - 0.07 * frac ** 1.5))
            ctl += into_dial(clock * sx)
            cord("Chest", ctl, torso, variant=1 if k == 2 and sx > 0 else 0, ends=("cap", "tuck"))
    # the spine: a twisted rope from the pelvis, up the hump of his back and into the phone
    for k in range(4):
        a0 = 90 + (k - 1.5) * 28
        ctl = []
        for z in (0.98, 1.14, 1.32, 1.5, 1.7, 1.86):
            th = a0 + (z - 1.32) * 160
            ctl.append(torso_at(th, z, CORD_R + (0.04 if z > 1.45 else 0.0)))
        ctl += [V((k - 1.5) * 0.035, -0.06, 1.97), V((k - 1.5) * 0.045, -0.17, 2.02), V((k - 1.5) * 0.05, -0.22, 2.07)]
        cord("Waist", ctl, torso + ["Head"], r=0.032, ends=("cap", "tuck"))
    # abdomen: out from under the dial, down and twisting into the waist
    for k, clock in enumerate((150, 175, 200, 225)):
        th = -90 + (k - 1.5) * 26
        ctl = into_dial(clock)[::-1]
        for z in (1.48, 1.41, 1.34, 1.28):
            ctl.append(torso_at(th + (1.41 - z) * 140, z))
        ctl.append(torso_at(th + 30, 1.22, CORD_R + 0.03))
        cord("Waist", ctl, torso, variant=1 if k == 1 else 0, ends=("tuck", "tuck"))
    # one long cord slung diagonally across his back, hip to shoulder
    ctl = [torso_at(150, 1.08), torso_at(120, 1.3), torso_at(85, 1.52), torso_at(60, 1.72), torso_at(40, 1.86),
           J["shoulder_Left"] + V(-0.06, 0.11, 0.06)]
    cord("Waist", ctl, torso + ["LeftUpperArm"], ends=("cap", "tuck"))
    # a binding round the narrow waist
    helix_wrap("Waist", V(0, 0.06, 1.33), V(0, 0.0, 1), 0.112, 0.09, 2.6, torso, phase=0.3)
    # two cords crossing the dial's ring (clear of the finger holes), holding it in
    for a, b, start, end in ((292, 338, torso_at(-125, 1.84), torso_at(-92, 1.92)),
                             (122, 188, torso_at(-40, 1.5), torso_at(-150, 1.6))):
        mid = (a + b) / 2
        ctl = [start, dial_at(a, C.DIAL["ring"] + 0.012, 0.02), dial_at(mid, C.DIAL["ring"] + 0.002, 0.04),
               dial_at(b, C.DIAL["ring"] + 0.012, 0.02), end]
        cord("Chest", ctl, torso, ends=("tuck", "tuck"))
    # neck: from the tops of the shoulders and the back up into the bottom of the phone
    for side, sx in SIDES:
        for k in range(2):
            ctl = [torso_at(70 if sx > 0 else 110, 1.78 - 0.07 * k), J[f"shoulder_{side}"] + V(-0.13 * sx, 0.05 + 0.04 * k, 0.07),
                   V(0.07 * sx, -0.12 + 0.04 * k, 1.96), V(0.1 * sx - 0.03 * k * sx, -0.22 + 0.05 * k, 2.06)]
            cord("Chest", ctl, torso + ["Head"], ends=("cap", "tuck"))
    # loose cords hanging out from under the phone, one with a plug, one torn
    for sx, kind, length in ((1, "plug", 0.36), (-1, "fray", 0.28)):
        top = V(0.17 * sx, -0.37, 2.03)
        ctl = [top + V(0, 0.03, 0.02), top, top + V(0.02 * sx, -0.02, -length * 0.5), top + V(0.0, 0.01, -length)]
        cord("Chest", ctl, None, r=0.017, weights={"Head": 1.0}, ends=("tuck", kind))


def build_arms():
    for side, sx in SIDES:
        torso = ["LowerTorso", "UpperTorso"]
        bones = ["UpperTorso"] + chain(side, "UpperArm", "LowerArm", "Hand")
        sh, el, wr = J[f"shoulder_{side}"], J[f"elbow_{side}"], J[f"wrist_{side}"]
        mesh_name = f"{side}Arm"
        # pectorals: out from under the dial, across the chest, over the front of the shoulder, down the arm
        for k, (clock, phi0, phi1, stop) in enumerate(((20, 70, 80, "wrist"), (45, 100, 110, "forearm"),
                                                      (75, 130, 140, "elbow"))):
            ctl = into_dial(clock * sx)[::-1]
            ctl += [torso_at(-55 + 28 * k if sx > 0 else -125 - 28 * k, 1.82 - 0.05 * k, CORD_R - 0.02),
                    sh + V(-0.02 * sx, -0.12 + 0.035 * k, 0.05 - 0.025 * k)]
            ctl += arm_points(side, sx, phi0, phi1, stop)
            cord(mesh_name, ctl, bones, variant=1 if k == 1 else 0, ends=("tuck", "tuck"))
        # from beside the spine, over the back of the shoulder and down the outside
        for k, (phi0, phi1, stop) in enumerate(((-20, 0, "wrist"), (-65, -45, "wrist"), (20, 35, "forearm"))):
            th = 75 - 18 * k if sx > 0 else 105 + 18 * k
            ctl = [torso_at(th, 1.62 + 0.08 * k), torso_at(th - 25 if sx > 0 else th + 25, 1.84, CORD_R - 0.015),
                   sh + V(0.02 * sx, 0.11 - 0.03 * k, 0.08 - 0.02 * k)]
            ctl += arm_points(side, sx, phi0, phi1, stop)
            cord(mesh_name, ctl, bones, ends=("cap", "tuck"))
        # the lat: from the waist up the side into the armpit and down the back of the arm
        th = 10 if sx > 0 else 170
        ctl = [torso_at(th + 25 * sx, 1.26, CORD_R + 0.025), torso_at(th, 1.36), torso_at(th - 8 * sx, 1.55),
               torso_at(th - 12 * sx, 1.72), sh + V(-0.07 * sx, 0.06, -0.13)]
        ctl += arm_points(side, sx, 200, 215, stop="elbow")
        cord(mesh_name, ctl, torso + chain(side, "UpperArm", "LowerArm"), ends=("tuck", "tuck"))
        # the deltoid: loops over the top of the shoulder, chest to back
        for k in range(2):
            ctl = [torso_at(-70 if sx > 0 else -110, 1.84 - 0.06 * k), sh + V(0.0, -0.1, 0.06 - 0.03 * k),
                   sh + V(0.05 * sx, 0.0, 0.1 - 0.025 * k), sh + V(0.0, 0.1, 0.06 - 0.03 * k),
                   torso_at(60 if sx > 0 else 120, 1.8 - 0.06 * k)]
            cord(mesh_name, ctl, bones, variant=0, ends=("tuck", "tuck"))
        # a cord wound diagonally round the upper arm, from the back of the shoulder to the elbow
        ctl = [torso_at(85 if sx > 0 else 95, 1.7), sh + V(0.03 * sx, 0.12, 0.02)]
        ctl += [limb_at(sh, el, sx, t, phi, upper_arm_r(t, phi) - 0.006) for t, phi in ((0.25, -40), (0.5, 50), (0.75, 140), (0.95, 220))]
        cord(mesh_name, ctl, bones, r=0.024, ends=("cap", "fray"))
        # the cores: a thick dark cord down the middle of each segment, filling the gaps
        cord(mesh_name, [sh + V(0, 0, 0.03), sh.lerp(el, 0.5), el], bones, r=0.05, ends=("tuck", "tuck"))
        cord(mesh_name, [el, el.lerp(wr, 0.5), wr], bones, r=0.04, ends=("tuck", "tuck"))
        # bindings at the elbow and wrist
        W1, W2 = (el - sh).normalized(), (wr - el).normalized()
        helix_wrap(mesh_name, el, (W1 + W2).normalized(), 0.078, 0.07, 2.2, bones, phase=1.0)
        helix_wrap(mesh_name, wr - W2 * 0.025, W2, 0.055, 0.06, 2.2, bones, phase=2.0)
        # the left forearm trails a loose cord with a plug on the end
        if sx > 0:
            p0 = limb_at(el, wr, sx, 0.4, 150, forearm_r(0.4, 150) - 0.01)
            ctl = [p0, p0 + V(0.01, 0.05, -0.12), p0 + V(0.04, 0.08, -0.3), p0 + V(0.03, 0.05, -0.45)]
            cord(mesh_name, ctl, None, r=0.017, weights={f"{side}LowerArm": 1.0}, ends=("tuck", "plug"))


def build_hands():
    for side, sx in SIDES:
        w, d, pn, a = C.hand_frame(side, sx)
        layout = C.hand_layout(side, sx)
        bones = chain(side, "LowerArm", "Hand")
        for i, (f, (joints, path)) in enumerate(layout.items()):
            fb = chain(side, f"{f}1", f"{f}2")
            off = {"Thumb": 0.02, "Index": 0.012, "Middle": 0.0, "Ring": -0.012, "Pinky": -0.024}[f]
            start = w - d * 0.035 + a * off
            mid = (start + joints[0]) / 2 - pn * 0.016
            cord(f"{side}Hand", [start, mid] + path, bones + fb, r=FINGER_R + (0.003 if f == "Thumb" else 0.0),
                 step=0.02, ends=("tuck", "claw"))
        # thicker cords on the palm side and the back give the hand some body
        for k, (off, depth) in enumerate(((-1, 0.014), (1, 0.014), (0, -0.016))):
            p0 = w + d * 0.01 + a * (0.024 * off) + pn * depth
            p1 = w + d * 0.14 + a * (0.04 * off) + pn * (depth + 0.008)
            cord(f"{side}Hand", [p0, (p0 + p1) / 2 + pn * 0.01, p1], bones, r=0.024, ends=("tuck", "cap"))


def build_legs():
    for side, sx in SIDES:
        bones = ["LowerTorso"] + chain(side, "UpperLeg", "LowerLeg", "Foot")
        hp, kn, an = J[f"hip_{side}"], J[f"knee_{side}"], J[f"ankle_{side}"]
        mesh_name = f"{side}Leg"
        # out of the waist binding, over the pelvis and down the leg
        starts = [(-75, 100, "ankle"), (-40, 62, "shin"), (-5, 25, "knee"), (35, -20, "ankle"),
                  (70, -62, "shin"), (110, -100, "knee"), (-100, 138, "ankle"), (95, -140, "shin")]
        for k, (th, phi, stop) in enumerate(starts):
            th_s = th if sx > 0 else 180 - th
            ctl = [torso_at(th_s, 1.33, CORD_R + 0.012), torso_at(th_s - 10 * sx, 1.23),
                   torso_at(th_s - 15 * sx, 1.11, CORD_R - 0.012)]
            ctl += leg_points(side, sx, phi, stop)
            cord(mesh_name, ctl, bones, variant=1 if k == 3 else 0, ends=("tuck", "tuck"))
        # two more from the hip bone, round the outside of the hip
        for k, (phi, stop) in enumerate(((170, "knee"), (215, "shin"))):
            th = 15 + 22 * k if sx > 0 else 165 - 22 * k
            ctl = [torso_at(th, 1.17 + 0.03 * k), torso_at(th - 5 * sx, 1.07, CORD_R - 0.01)]
            ctl += leg_points(side, sx, phi, stop)
            cord(mesh_name, ctl, bones, ends=("cap", "tuck"))
        # a cord wound diagonally round the thigh, from the front of the pelvis to behind the knee
        ctl = [torso_at(-100 if sx > 0 else -80, 1.16, CORD_R + 0.01)]
        ctl += [limb_at(hp, kn, sx, t, phi, thigh_r(t, phi) - 0.008) for t, phi in ((0.15, 130), (0.4, 40), (0.65, -50), (0.88, -140))]
        ctl.append(limb_at(kn, an, sx, 0.08, -170, 0.03))
        cord(mesh_name, ctl, bones, r=0.026, variant=1 if sx < 0 else 0, ends=("cap", "tuck"))
        cord(mesh_name, [hp + V(0, 0, 0.06), hp.lerp(kn, 0.5), kn], bones, r=0.075, ends=("tuck", "tuck"))
        cord(mesh_name, [kn, kn.lerp(an, 0.4) + V(0, 0.015, 0), an + V(0, 0, 0.02)], bones, r=0.05, ends=("tuck", "tuck"))
        W1, W2 = (kn - hp).normalized(), (an - kn).normalized()
        helix_wrap(mesh_name, kn, (W1 + W2).normalized(), 0.092, 0.08, 2.2, bones, phase=0.5)
        helix_wrap(mesh_name, an + W2 * -0.035, W2, 0.06, 0.06, 2.2, bones, phase=1.5)
        # the right hip trails a cord with a plug
        if sx < 0:
            p0 = torso_at(200, 1.1)
            ctl = [p0, p0 + V(-0.05, -0.03, -0.12), p0 + V(-0.08, -0.02, -0.3), p0 + V(-0.07, 0.0, -0.44)]
            cord(mesh_name, ctl, None, r=0.017, weights={"LowerTorso": 0.6, f"{side}UpperLeg": 0.4}, ends=("tuck", "plug"))


def build_feet():
    for side, sx in SIDES:
        an, toe = J[f"ankle_{side}"], J[f"toe_{side}"]
        fwd = (V(toe.x - an.x, toe.y - an.y, 0)).normalized()
        out = V(sx, 0, 0)
        foot = {f"{side}Foot": 1.0}
        # toes: thick splayed cords that run forward onto the floor and end in claws
        for k, ang in enumerate((-30, -10, 10, 30)):
            dirn = (fwd * math.cos(math.radians(ang)) + out * math.sin(math.radians(ang))).normalized()
            reach = 0.32 - 0.04 * abs(k - 1.5)
            ctl = [an + V(0, 0, 0.04), an + dirn * 0.03 + V(0, 0, -0.03), an + dirn * 0.12 + V(0, 0, -0.07),
                   V(*(an + dirn * 0.22)[:2], 0.026), V(*(an + dirn * reach)[:2], 0.022)]
            cord(f"{side}Foot", ctl, None, r=0.024, weights=foot, ends=("tuck", "claw"))
        # the heel, and cords spilling out behind and beside him in loose loops
        back = (-fwd + out * 0.4).normalized()
        ctl = [an + V(0, 0, 0.03), an + back * 0.07 + V(0, 0, -0.08), V(*(an + back * 0.16)[:2], CORD_R)]
        c = an + back * 0.36
        for k in range(10):
            a = math.radians(-60 * sx + 40 * k * sx)
            rr = 0.16 + 0.03 * math.sin(k * 1.7)
            ctl.append(V(c.x + math.cos(a) * rr, c.y + math.sin(a) * rr * 0.8, CORD_R))
        cord(f"{side}Foot", ctl, None, weights=foot, ends=("tuck", "plug" if sx > 0 else "fray"))
        side_dir = (out + fwd * 0.3).normalized()
        ctl = [an + V(0, 0, 0.04), an + side_dir * 0.08 + V(0, 0, -0.07), V(*(an + side_dir * 0.18)[:2], CORD_R)]
        c = an + side_dir * 0.34 + fwd * 0.05
        for k in range(7):
            a = math.radians(180 + 50 * k) if sx > 0 else math.radians(-50 * k)
            rr = 0.13 + 0.025 * math.sin(k * 2.3)
            ctl.append(V(c.x + math.cos(a) * rr * sx, c.y + math.sin(a) * rr * 0.85, CORD_R))
        cord(f"{side}Foot", ctl, None, variant=1 if sx < 0 else 0, weights=foot, ends=("tuck", "cap"))


# ================================================================ the phone head
def head_matrix():
    return Matrix.Translation(J["head"]) @ Matrix.Rotation(math.radians(12), 4, "X")


def shell_ring(z, inset=0.0, n=56):
    """Cross-section of the phone body at height z (local), a rounded rectangle."""
    f = z / C.SHELL_H
    hw = lerp(0.205, 0.15, f) - inset
    yf = lerp(-0.175, -0.065, f) + inset
    yb = lerp(0.175, 0.125, f) - inset
    F = 0.04
    if z > C.SHELL_H - F:
        k = (z - (C.SHELL_H - F)) / F
        sh = F * (1 - math.sqrt(max(0.0, 1 - k * k)))
        hw, yf, yb = hw - sh, yf + sh, yb - sh
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    out = []
    for j in range(n):
        a = TAU * j / n
        c, s = math.cos(a), math.sin(a)
        e = 2 / 6
        out.append(V(hw * math.copysign(abs(c) ** e, c), yc + hd * math.copysign(abs(s) ** e, s), z))
    return out


def phone_solid(mb, inset, z_top, uv_fn, weights, n=56):
    """A closed body made of shell rings from the bottom to z_top (rounded at the shell's top)."""
    zs = [0.002 + (z_top - 0.002) * (k / 14) for k in range(15)]
    if z_top >= C.SHELL_H - 1e-6:
        zs = [0.002 + (C.SHELL_H - 0.045) * k / 10 for k in range(11)] + [C.SHELL_H - 0.04 + 0.04 * (k / 8) ** 0.7
                                                                          for k in range(1, 9)]
    rings = []
    for z in zs:
        ring = shell_ring(min(z, C.SHELL_H - 1e-4), inset, n)
        rings.append([(mb.vert(p, weights), uv_fn(p)) for p in ring])
    for i in range(len(rings) - 1):
        for j in range(n):
            q = [rings[i][j], rings[i][(j + 1) % n], rings[i + 1][(j + 1) % n], rings[i + 1][j]]
            ctr = sum((mb.co[x] for x, _ in q), Vector()) / 4
            mb.face(q, V(ctr.x, ctr.y - 0.0, 0) if i < len(rings) - 2 else V(ctr.x, ctr.y, 0.2))
    for ring, z, sign in ((rings[0], zs[0], -1), (rings[-1], zs[-1], 1)):
        c = sum((mb.co[x] for x, _ in ring), Vector()) / len(ring)
        tip = (mb.vert(c, weights), uv_fn(c))
        for j in range(n):
            mb.face([ring[j], ring[(j + 1) % n], tip], V(0, 0, sign))
    return mb


def socket_frame():
    z = C.SOCKET["z"]
    f = z / C.SHELL_H
    yf = lerp(-0.175, -0.065, f)
    slope = V(0, 0.11, C.SHELL_H).normalized()
    n = slope.cross(V(1, 0, 0)).normalized()
    if n.y > 0:
        n = -n
    return V(0, yf, z), n


def to_world(mb, M):
    for i, c in enumerate(mb.co):
        mb.co[i] = M @ c


def cutter(name, center, axis, radius, depth_out, depth_in, uv, n=40):
    """A cylinder object to carve the dial socket out of the shell and the water."""
    axis = axis.normalized()
    ref = V(1, 0, 0)
    U = (ref - axis * ref.dot(axis)).normalized()
    W = axis.cross(U)
    bm = bmesh.new()
    top, bot = [], []
    for j in range(n):
        a = TAU * j / n
        d = (U * math.cos(a) + W * math.sin(a)) * radius
        top.append(bm.verts.new(center + axis * depth_out + d))
        bot.append(bm.verts.new(center - axis * depth_in + d))
    for j in range(n):
        bm.faces.new([top[j], top[(j + 1) % n], bot[(j + 1) % n], bot[j]])
    bm.faces.new(top[::-1])
    bm.faces.new(bot)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    for loop in uvl.data:
        loop.uv = uv
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def carve(ob, cut):
    mod = ob.modifiers.new("Socket", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cut
    mod.solver = "EXACT"
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cut)


def build_head():
    """The head: smoked glass shell (Shell), the water in it (Water), and the opaque parts (Head)."""
    M = head_matrix()
    hw = {"Head": 1.0}
    shell = MB("Shell", "glass")
    phone_solid(shell, 0.0, C.SHELL_H, lambda p: C.shell_uv(p.x, p.z), hw)
    water = MB("Water", "water")
    z_w = C.SHELL_H * 0.71
    phone_solid(water, 0.008, z_w, lambda p: C.shell_uv(p.x, p.z), hw, 40)
    # bubbles stuck to the inside of the glass and a scrap of leaf at the surface
    for k in range(14):
        z = rng.uniform(0.02, z_w - 0.015)
        ring = shell_ring(z, 0.016, 56)
        p = ring[rng.randrange(56)]
        r = rng.uniform(0.003, 0.009)
        sphere(water, p, (r, r, r), lambda u, v: (0.97, 0.03), hw, 8, 5)
    leaf_c = V(0.07, 0.05, z_w + 0.001)
    leaf = [(mb_v, uv) for mb_v, uv in []]
    pts = [leaf_c + V(math.cos(a) * 0.03 * (1 if k % 2 == 0 else 0.6), math.sin(a) * 0.014, 0)
           for k, a in enumerate(TAU * i / 10 for i in range(10))]
    ids = [(water.vert(p, hw), (0.9, 0.03)) for p in pts]
    tip = (water.vert(leaf_c, hw), (0.9, 0.03))
    for j in range(10):
        water.face([ids[j], ids[(j + 1) % 10], tip], V(0, 0, 1))
    del leaf
    to_world(shell, M)
    to_world(water, M)
    s_ob, w_ob = shell.build(), water.build()
    c, n = socket_frame()
    cw, nw = M @ c, (M.to_3x3() @ n).normalized()
    carve(s_ob, cutter("CutShell", cw, nw, C.SOCKET["r"], 0.05, C.SOCKET["depth"], (0.02, 0.98)))
    carve(w_ob, cutter("CutWater", cw, nw, C.SOCKET["r"] + 0.008, 0.05, C.SOCKET["depth"] + 0.008, (0.5, 0.2)))

    # the opaque parts: the base plate, the empty cradle, the socket's black hole and torn ring
    head = mesh("Head", "props")
    base = []
    for z, inset in ((-0.024, 0.0), (-0.006, -0.012), (0.004, -0.012), (0.004, 0.004)):
        ring = [p - V(0, 0, p.z - z) for p in shell_ring(0.0, inset, 56)]
        base.append([(head.vert(M @ p, hw), in_region("plastic", 0.5 + p.x, 0.5 + p.y)) for p in ring])
    for i in range(len(base) - 1):
        for j in range(56):
            q = [base[i][j], base[i][(j + 1) % 56], base[i + 1][(j + 1) % 56], base[i + 1][j]]
            ctr = sum((head.co[x] for x, _ in q), Vector()) / 4
            head.face(q, ctr - M @ V(0, 0, -0.01))
    bot = sum((head.co[x] for x, _ in base[0]), Vector()) / 56
    tip = (head.vert(bot, hw), in_region("plastic", 0.5, 0.5))
    for j in range(56):
        head.face([base[0][j], base[0][(j + 1) % 56], tip], -(M.to_3x3() @ V(0, 0, 1)))
    for sx in (1, -1):  # the cradle prongs, with nothing on them
        p0 = M @ V(0.1 * sx, 0.035, C.SHELL_H - 0.03)
        up = (M.to_3x3() @ V(0, 0, 1)).normalized()
        tube(head, p0, p0 + up * 0.07, lambda t: 0.042 if t < 0.55 else 0.042 * math.sqrt(max(0.0, 1 - ((t - 0.55) / 0.45) ** 2)),
             "plastic", hw, 18, 10)
    # the socket: a black cup where the dial was, a ragged ring of what's left of it, and a pinprick of light
    up = (M.to_3x3() @ V(0, 0, 1)).normalized()
    tube(head, cw - nw * (C.SOCKET["depth"] - 0.002), cw + nw * 0.003, lambda t: C.SOCKET["r"] - 0.002, "socket", hw, 32, 2,
         cap0=True)
    U = (up - nw * up.dot(nw)).normalized()
    Wv = nw.cross(U)
    ring_out, ring_in = [], []
    n = 48
    for j in range(n + 1):
        a = TAU * j / n
        if a > math.radians(285):
            break
        jag = 0.012 * (0.4 + 0.6 * rng.random()) * (1 if j % 2 else 0.4)
        d = U * math.cos(a) + Wv * math.sin(a)
        ring_out.append((head.vert(cw + d * (C.SOCKET["r"] - 0.001) + nw * 0.004, hw), in_region("chrome", j / n, 0)))
        ring_in.append((head.vert(cw + d * (C.SOCKET["r"] - 0.006 - jag) + nw * 0.004, hw), in_region("chrome", j / n, 1)))
    for j in range(len(ring_out) - 1):
        head.face([ring_out[j], ring_out[j + 1], ring_in[j + 1], ring_in[j]], nw)
    light = mesh("SocketLight", "light")
    sphere(light, cw - nw * (C.SOCKET["depth"] - 0.008) + U * 0.012, (0.006, 0.006, 0.006), lambda u, v: (0.5, 0.5), hw, 10, 6)
    # where the handset's cord comes out of the back
    return M @ V(0.17, 0.12, 0.012)


def tube(mb, a, b, radius_fn, region, weights, n=16, rows=8, cap0=False, cap1=False):
    """A straight tube of varying radius from a to b, in a props region."""
    axis = (b - a)
    W = axis.normalized()
    ref = V(1, 0, 0) if abs(W.x) < 0.9 else V(0, 1, 0)
    U = (ref - W * ref.dot(W)).normalized()
    Vv = W.cross(U)
    rings = []
    for k in range(rows + 1):
        t = k / rows
        r = radius_fn(t)
        c = a + axis * t
        rings.append([(mb.vert(c + (U * math.cos(TAU * j / n) + Vv * math.sin(TAU * j / n)) * r, weights),
                       in_region(region, j / n, t)) for j in range(n + 1)])
    for k in range(rows):
        c = a + axis * ((k + 0.5) / rows)
        for j in range(n):
            q = [rings[k][j], rings[k][j + 1], rings[k + 1][j + 1], rings[k + 1][j]]
            mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - c)
    for ring, p, want, on in ((rings[0], a, -W, cap0), (rings[-1], b, W, cap1)):
        if on:
            tip = (mb.vert(p, weights), in_region(region, 0.5, 0.5))
            for j in range(n):
                mb.face([ring[j], ring[j + 1], tip], want)
    return rings


def sphere(mb, c, radii, uv_fn, weights, n_lon=12, n_lat=8, rot=None):
    R = rot or Matrix.Identity(3)
    rows = []
    for i in range(n_lat + 1):
        lam = -math.pi / 2 + math.pi * i / n_lat
        row = []
        for j in range(n_lon + 1):
            phi = TAU * j / n_lon
            d = V(math.cos(lam) * math.cos(phi), math.cos(lam) * math.sin(phi), math.sin(lam))
            p = c + R @ V(d.x * radii[0], d.y * radii[1], d.z * radii[2])
            row.append((mb.vert(p, weights), uv_fn(j / n_lon, i / n_lat)))
        rows.append(row)
    for i in range(n_lat):
        for j in range(n_lon):
            q = [rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]]
            mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - c)
    return rows


# ================================================================ the dial heart
def build_dial():
    c, n, up, right = dial_frame()
    w = {"DialSpin": 1.0}
    dm = mesh("Dial", "props")
    R = C.DIAL

    def disk_point(x, y, depth):
        return c + right * x + up * y + n * depth

    def plate_uv(x, y):
        return in_region("plate", 0.5 + x / (2 * R["plate"]), 0.5 + y / (2 * R["plate"]))

    # number plate (behind), the chrome bezel ring, the hub
    rows = []
    for k, rr in enumerate((0.0, 0.03, 0.06, 0.09, R["plate"])):
        row = []
        for j in range(65):
            a = TAU * j / 64
            x, y = math.sin(a) * rr, math.cos(a) * rr
            row.append((dm.vert(disk_point(x, y, 0.0), w), plate_uv(x, y)))
        rows.append(row)
    for k in range(len(rows) - 1):
        for j in range(64):
            dm.face([rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]], n)
    prof = [(R["plate"] - 0.002, -0.01), (R["plate"], 0.012), (R["plate"] + 0.006, 0.022), (R["ring"] - 0.006, 0.026),
            (R["ring"], 0.018), (R["ring"] + 0.002, 0.0), (R["ring"] - 0.004, -0.02)]
    bez = []
    for k, (rr, dz) in enumerate(prof):
        bez.append([(dm.vert(disk_point(math.sin(TAU * j / 64) * rr, math.cos(TAU * j / 64) * rr, dz), w),
                     in_region("chrome", j / 64, k / (len(prof) - 1))) for j in range(65)])
    for k in range(len(bez) - 1):
        for j in range(64):
            q = [bez[k][j], bez[k][j + 1], bez[k + 1][j + 1], bez[k + 1][j]]
            mid = sum((dm.co[x] for x, _ in q), Vector()) / 4
            dm.face(q, (mid - c) - n * (mid - c).dot(n) * 0.3 + n * 0.3)
    # the finger wheel: a smoked glass disk in front of the plate, with ten holes
    wheel = MB("Wheel", "props")
    wz0, wz1 = 0.008, 0.016
    for depth, want in ((wz1, n), (wz0, -n)):
        rows = []
        for k in range(7):
            rr = R["wheel"] * k / 6
            row = []
            for j in range(65):
                a = TAU * j / 64
                x, y = math.sin(a) * rr, math.cos(a) * rr
                row.append((wheel.vert(disk_point(x, y, depth), w), in_region("wheel", 0.5 + x / (2 * R["wheel"]),
                                                                                 0.5 + y / (2 * R["wheel"]))))
            rows.append(row)
        for k in range(6):
            for j in range(64):
                wheel.face([rows[k][j], rows[k][j + 1], rows[k + 1][j + 1], rows[k + 1][j]], want)
    rim = [[(wheel.vert(disk_point(math.sin(TAU * j / 64) * R["wheel"], math.cos(TAU * j / 64) * R["wheel"], dz), w),
             in_region("wheel", j / 64, 0.98)) for j in range(65)] for dz in (wz0, wz1)]
    for j in range(64):
        q = [rim[0][j], rim[0][j + 1], rim[1][j + 1], rim[1][j]]
        mid = sum((wheel.co[x] for x, _ in q), Vector()) / 4
        wheel.face(q, mid - c - n * (mid - c).dot(n))
    to_add = wheel.build()
    for k, (clock, _) in enumerate(C.DIAL_DIGITS):
        a = math.radians(clock)
        hc = c + (right * math.sin(a) + up * math.cos(a)) * R["holes_at"]
        carve(to_add, cutter(f"Hole{k}", hc + n * 0.012, n, R["hole"], 0.02, 0.02, in_region("wheel", 0.5, 0.95), 16))
    # merge the wheel into the dial mesh
    me = to_add.data
    uvl = me.uv_layers[0]
    base = len(dm.co)
    for v in me.vertices:
        dm.vert(to_add.matrix_world @ v.co, w)
    for poly in me.polygons:
        dm.faces.append([base + i for i in poly.vertices])
        dm.fuv.append([tuple(uvl.data[li].uv) for li in poly.loop_indices])
    bpy.data.objects.remove(to_add)
    # the glow rings lining the finger holes (they light up red in the alarm)
    glow = mesh("DialGlow", "glow")
    for clock, _ in C.DIAL_DIGITS:
        a = math.radians(clock)
        hc = c + (right * math.sin(a) + up * math.cos(a)) * R["holes_at"]
        tube(glow, hc + n * (wz0 - 0.002), hc + n * (wz1 + 0.001), lambda t: R["hole"] - 0.0012, "socket", w, 16, 1)
    # the hub, cracked, and the chrome finger stop
    hub = []
    for k, (rr, dz) in enumerate(((R["hub"], wz1), (R["hub"] - 0.002, wz1 + 0.01), (R["hub"] * 0.6, wz1 + 0.016),
                                  (0.0, wz1 + 0.018))):
        hub.append([(dm.vert(disk_point(math.sin(TAU * j / 40) * rr, math.cos(TAU * j / 40) * rr, dz), w),
                     in_region("hub", 0.5 + math.sin(TAU * j / 40) * rr / (2 * R["hub"]),
                               0.5 + math.cos(TAU * j / 40) * rr / (2 * R["hub"]))) for j in range(41)])
    for k in range(len(hub) - 1):
        for j in range(40):
            dm.face([hub[k][j], hub[k][j + 1], hub[k + 1][j + 1], hub[k + 1][j]], n)
    a = math.radians(C.FINGER_STOP)
    s0 = c + (right * math.sin(a) + up * math.cos(a)) * (R["holes_at"] + 0.004) + n * wz1
    tube(dm, s0, s0 + n * 0.022 + (right * math.sin(a) + up * math.cos(a)) * 0.012, lambda t: 0.006, "chrome", w, 10, 3,
         cap1=True)


# ================================================================ the handset and its cord
def handset_frame():
    g, axis = C.grip("Left", 1.0)
    w, d, pn, a = C.hand_frame("Left", 1.0)
    side = (axis.cross(pn)).normalized()  # the cups face this way
    if side.x < 0:
        side = -side
    return g, axis.normalized(), side


def build_handset():
    g, axis, side = handset_frame()
    hw = {"LeftHand": 1.0}
    hs = mesh("Handset", "props")
    L = 0.21  # half length, centre of the grip to each cup

    def bar(t):  # along the handset, -1 (earpiece) .. 1 (mouthpiece); bowed away from the cups
        return g + axis * (L * t) - side * (0.036 * (1 - t * t))

    pts = [bar(-1 + 2 * k / 24) for k in range(25)]
    T, N = frames(pts)
    rings = []
    for k, p in enumerate(pts):
        t = -1 + 2 * k / 24
        r = 0.026 + 0.012 * smooth(0.55, 0.95, abs(t))
        B = T[k].cross(N[k])
        rings.append([(hs.vert(p + (N[k] * math.cos(TAU * j / 14) * r * 1.15 + B * math.sin(TAU * j / 14) * r), hw),
                       in_region("plastic", j / 14, k / 24)) for j in range(15)])
    for k in range(24):
        for j in range(14):
            q = [rings[k][j], rings[k][j + 1], rings[k + 1][j + 1], rings[k + 1][j]]
            hs.face(q, sum((hs.co[x] for x, _ in q), Vector()) / 4 - (pts[k] + pts[k + 1]) / 2)
    for k, sgn in ((0, -1), (24, 1)):
        tip = (hs.vert(pts[k] + axis * sgn * 0.012, hw), in_region("plastic", 0.5, 0.5))
        for j in range(14):
            hs.face([rings[k][j], rings[k][j + 1], tip], axis * sgn)
    for t in (-0.92, 0.92):  # the cups
        p = bar(t)
        cup = []
        for k, (rr, h) in enumerate(((0.03, -0.01), (0.05, 0.016), (0.058, 0.038), (0.055, 0.052))):
            cup.append([(hs.vert(p + side * h + (axis * math.cos(TAU * j / 24) + side.cross(axis) * math.sin(TAU * j / 24)) * rr, hw),
                         in_region("plastic", j / 24, k / 3)) for j in range(25)])
        for k in range(3):
            for j in range(24):
                q = [cup[k][j], cup[k][j + 1], cup[k + 1][j + 1], cup[k + 1][j]]
                hs.face(q, sum((hs.co[x] for x, _ in q), Vector()) / 4 - (p + side * 0.015))
        cap_c = p + side * 0.055
        tip = (hs.vert(cap_c, hw), in_region("cap", 0.5, 0.5))
        for j in range(24):
            a0, a1 = TAU * j / 24, TAU * (j + 1) / 24
            hs.face([(cup[3][j][0], in_region("cap", 0.5 + 0.48 * math.cos(a0), 0.5 + 0.48 * math.sin(a0))),
                     (cup[3][j + 1][0], in_region("cap", 0.5 + 0.48 * math.cos(a1), 0.5 + 0.48 * math.sin(a1))), tip], side)
    return bar(1.0) + axis * 0.01  # the mouthpiece end, where the coiled cord goes in


def build_coil(start, end):
    """The handset's coiled cord: a real helix of wire round a hanging path, head to hand."""
    mid = (start + end) / 2
    ctl = [start, start + V(0.1, 0.06, -0.08), V(mid.x + 0.32, mid.y + 0.1, mid.z - 0.12),
           V(end.x + 0.16, end.y + 0.05, end.z - 0.1), end + V(0.03, 0.0, -0.04), end]
    path = resample(catmull(ctl), 0.004)
    T, N = frames(path)
    L = 0.004 * (len(path) - 1)
    pitch, coil_r, wire_r = 0.02, 0.017, 0.0055
    helix = []
    for i, p in enumerate(path):
        s = 0.004 * i
        a = TAU * s / pitch
        B = T[i].cross(N[i])
        k = smooth(0.0, 0.06, s) * smooth(L, L - 0.06, s)  # straight where it plugs in at each end
        helix.append(p + (N[i] * math.cos(a) + B * math.sin(a)) * coil_r * k)
    helix = helix[::max(1, len(helix) // 1200)]
    mb = mesh("HandsetCord", "props")
    T, N = frames(helix)
    n = 5
    rings = []
    for i, p in enumerate(helix):
        f = i / (len(helix) - 1)
        k = smooth(0.15, 0.85, f)
        wts = {"Head": 1 - k, "LeftHand": k} if 0 < k < 1 else ({"Head": 1.0} if k == 0 else {"LeftHand": 1.0})
        B = T[i].cross(N[i])
        rings.append([(mb.vert(p + (N[i] * math.cos(TAU * j / n) + B * math.sin(TAU * j / n)) * wire_r, wts),
                       in_region("plastic", j / n, f)) for j in range(n + 1)])
    for i in range(len(rings) - 1):
        for j in range(n):
            q = [rings[i][j], rings[i][j + 1], rings[i + 1][j + 1], rings[i + 1][j]]
            mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - (helix[i] + helix[i + 1]) / 2)


# ================================================================ plugs, claws and copper
def build_details():
    mb = mesh("Details", "props")
    for kind, p, t, r, w in ENDS:
        t = t.normalized()
        ref = V(0, 0, 1) if abs(t.z) < 0.9 else V(1, 0, 0)
        U = (ref - t * ref.dot(t)).normalized()
        W = t.cross(U)
        if kind == "plug":  # a modular phone plug: clear plastic block with gold contacts and a latch
            hw_, hh, ln = 0.017, 0.012, 0.045
            corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
            rings = []
            for k, (s, sc) in enumerate(((0.0, 0.7), (0.008, 1.0), (ln, 1.0))):
                rings.append([(mb.vert(p + t * s + U * (cx * hw_ * sc) + W * (cy * hh * sc), w), in_region("plug", i / 4, k / 2))
                              for i, (cx, cy) in enumerate(corners)])
            for k in range(2):
                for i in range(4):
                    q = [rings[k][i], rings[k][(i + 1) % 4], rings[k + 1][(i + 1) % 4], rings[k + 1][i]]
                    mb.face(q, sum((mb.co[x] for x, _ in q), Vector()) / 4 - (p + t * (ln / 2)))
            front = [(x, in_region("plug", 0.2 + 0.6 * (i in (1, 2)), 0.05 + 0.25 * (i in (2, 3)))) for i, (x, _) in enumerate(rings[2])]
            mb.face(front, t)
            tube(mb, p + t * 0.012 + W * hh, p + t * 0.04 + W * (hh + 0.008), lambda s: 0.003, "plug", w, 6, 2)
        elif kind == "claw":  # a chrome ferrule drawn out to a point
            tube(mb, p - t * r * 0.8, p + t * (r * 2.4), lambda s: r * 1.08 * (1 - s ** 1.6) + 0.0008, "chrome", w, 10, 5)
        elif kind == "fray":  # torn end: copper strands splaying out
            for k in range(6):
                a = TAU * k / 6 + rng.uniform(-0.3, 0.3)
                dirn = (t + (U * math.cos(a) + W * math.sin(a)) * rng.uniform(0.3, 0.8)).normalized()
                base = p + (U * math.cos(a) + W * math.sin(a)) * r * 0.4
                tube(mb, base, base + dirn * rng.uniform(0.02, 0.045), lambda s: 0.0028 * (1 - 0.7 * s), "copper", w, 5, 2)


# ================================================================ rig, materials
def build_armature():
    arm = bpy.data.armatures.new("Receiver_Rig")
    ob = bpy.data.objects.new("Receiver_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, (h, t, parent) in BONES.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = h, t
        ebs[name] = eb
    for name, (h, t, parent) in BONES.items():
        if parent:
            ebs[name].parent = ebs[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def image(fname, noncolor=False):
    img = bpy.data.images.load(os.path.join(TEX, fname), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    return img


def textured(name, prefix, metal=False, alpha=False, transmission=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def tex(fname, noncolor):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = image(fname, noncolor)
        return n

    col = tex(f"{prefix}_color.png", False)
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex(f"{prefix}_roughness.png", True).outputs["Color"], b.inputs["Roughness"])
    if os.path.exists(os.path.join(TEX, f"{prefix}_normal.png")):
        nrm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex(f"{prefix}_normal.png", True).outputs["Color"], nrm.inputs["Color"])
        nt.links.new(nrm.outputs["Normal"], b.inputs["Normal"])
    if metal:
        nt.links.new(tex(f"{prefix}_metalness.png", True).outputs["Color"], b.inputs["Metallic"])
    if alpha:
        nt.links.new(col.outputs["Alpha"], b.inputs["Alpha"])
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.45
    return m


def plain(name, color, emit=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.3
    if emit:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


MATS = {}


def skin(ob, mb, rig):
    groups = {}
    for vi, ws in enumerate(mb.w):
        for b, wt in ws.items():
            if b not in groups:
                groups[b] = ob.vertex_groups.new(name=b)
            groups[b].add([vi], wt, "REPLACE")
    ob.parent = rig
    ob.modifiers.new("Armature", "ARMATURE").object = rig


def main(out):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.update({
        "cord": textured("M_Cord", "cord"),
        "props": textured("M_Phone", "props", metal=True),
        "glass": textured("M_Glass", "glass", alpha=True, transmission=0.85),
        "water": textured("M_Water", "water"),
        "glow": plain("M_DialGlow", (0.02, 0.02, 0.025)),
        "light": plain("M_SocketLight", (1.0, 0.97, 0.9), emit=6.0),
    })
    build_torso()
    build_arms()
    build_hands()
    build_legs()
    build_feet()
    build_dial()
    cord_start = build_head()
    plug_in = build_handset()
    build_coil(cord_start, plug_in)
    build_details()
    rig = build_armature()
    total = 0
    for name, mb in MESHES.items():
        ob = mb.build()
        skin(ob, mb, rig)
        total += mb.tris()
        print(f"{name:12s} tris {mb.tris():6d}")
    for ob in bpy.data.objects:  # Shell and Water were built and carved separately
        if ob.name in ("Shell", "Water"):
            ob.vertex_groups.new(name="Head").add(list(range(len(ob.data.vertices))), 1.0, "REPLACE")
            ob.parent = rig
            ob.modifiers.new("Armature", "ARMATURE").object = rig
            n = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            total += n
            print(f"{ob.name:12s} tris {n:6d}")
    print("total tris", total)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "receiver.blend"))
