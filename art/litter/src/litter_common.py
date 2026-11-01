"""Shared layout for the Litter: the small creatures and the stack they climb into.

Blender units are meters, Z is up, they face -Y, so their left side is +X.

- A litterling is knee-high: a lumpy, sagging, tick-like body about 0.36 m long, with a
  smaller head end and a bloated back, slung between eight thin jointed legs whose knees rise
  above it. Two wet black eyes with a pale eyeshine, and a lipless slit of a mouth with needle
  teeth under them.
- The stack is 30 of them climbed onto each other into one hunched monster about 9 ft tall:
  a barrel torso of ten, a head of two, arms and legs that are chains of them, hands whose
  creature spreads its legs out as long fingers, and feet whose creature splays its legs as
  toes. They cling at every angle, some upside down. Each sits on its own slot bone.
"""
import math
import random

import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Matrix, Quaternion, Vector


def V(*a):
    return Vector(a)


SIDES = (("Left", 1.0), ("Right", -1.0))
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")

# ---------------------------------------------------------------- the litterling (body frame:
# x to its left, y to its back, z up; the eyes look down -y)
BODY_C = V(0, 0.01, 0.26)
BODY_R = (0.15, 0.185, 0.125)  # half width, half length, half height
EYE_R = 0.021
LEGS = 4  # per side


def leg_layout(side, sx, k):
    """Litterling leg k (0 front .. 3 back) on one side: (hip under the body, knee, foot)."""
    a = math.radians((32, 72, 110, 148)[k])
    hd = V(sx * math.sin(a), -math.cos(a), 0)  # outward, round from the front
    hip = BODY_C + V(hd.x * 0.085, hd.y * 0.11, -0.07)
    knee = BODY_C + V(hd.x * 0.25, hd.y * 0.27, 0.15 - 0.02 * abs(k - 1.5))
    foot = V(hd.x * 0.4, hd.y * 0.42 + (-0.03, 0.0, 0.01, 0.04)[k], 0.0)
    return hip, knee, foot


def litterling_bones():
    b = {"Root": (V(0, 0, 0), V(0, 0, 0.1), None), "Body": (BODY_C, BODY_C + V(0, 0, 0.15), "Root")}
    for side, sx in SIDES:
        for k in range(LEGS):
            hip, knee, foot = leg_layout(side, sx, k)
            b[f"Leg{side[0]}{k + 1}A"] = (hip, knee, "Body")
            b[f"Leg{side[0]}{k + 1}B"] = (knee, foot, f"Leg{side[0]}{k + 1}A")
    return b


def frame(front, up):
    """A matrix from a creature's own frame (x left, y back, z up) to the world."""
    f = front.normalized()
    u = (up - f * up.dot(f)).normalized()
    x = u.cross(f).normalized()  # with -y forward and z up, x is its left
    return Matrix((x, -f, u)).transposed()


# ---------------------------------------------------------------- the stack
SJ = {
    "root": V(0, 0.05, 1.22),
    "waist": V(0, 0.04, 1.5),
    "neck": V(0, -0.12, 2.16),
    "head_top": V(0, -0.24, 2.7),
}
for _s, _x in SIDES:
    SJ[f"shoulder_{_s}"] = V(0.44 * _x, -0.07, 2.02)
    SJ[f"elbow_{_s}"] = V(0.58 * _x, 0.0, 1.54)
    SJ[f"wrist_{_s}"] = V(0.62 * _x, -0.16, 1.06)
    SJ[f"hip_{_s}"] = V(0.2 * _x, 0.05, 1.18)
    SJ[f"knee_{_s}"] = V(0.26 * _x, -0.06, 0.7)
    SJ[f"ankle_{_s}"] = V(0.27 * _x, 0.06, 0.2)
    SJ[f"toe_{_s}"] = V(0.3 * _x, -0.2, 0.03)


def slots():
    """The 30 creatures of the stack: name -> (centre, size, parent body bone, facing, up)."""
    rng = random.Random(30)
    out = {}

    def face(c, outward, bias=0.35):
        """Facing out of the pile, mostly forward; but some look sideways, up or down."""
        d = (outward.normalized() * (1 - bias) + V(0, -1, 0) * bias)
        d += V(rng.uniform(-0.6, 0.6), rng.uniform(-0.25, 0.25), rng.uniform(-0.55, 0.6))
        return d.normalized()

    def tumble(front):
        """Which way is up for a creature clinging in the pile: mostly up, some on their sides,
        a few upside down."""
        roll = rng.choice((0, 0, 25, -35, 60, -75, 110, 180, 160))
        return Quaternion(front, math.radians(roll + rng.uniform(-15, 15))) @ V(0, 0, 1)

    axis = lambda c: V(c.x, c.y - 0.03, 0)  # noqa: E731  (outward from the torso's middle)
    rows = (  # a hunched barrel: the higher rows lean forward, and the balls sit at different depths
        ("LowerTorso", 1.42, ((-0.21, 0.1), (0.0, -0.04), (0.2, 0.12))),
        ("UpperTorso", 1.7, ((-0.36, 0.06), (-0.12, -0.08), (0.13, 0.04), (0.35, -0.02))),
        ("UpperTorso", 1.96, ((-0.24, -0.07), (0.02, 0.06), (0.25, -0.1))),
    )
    k = 1
    for bone, z, cells in rows:
        for x, y in cells:
            c = V(x + rng.uniform(-0.05, 0.05), y + rng.uniform(-0.05, 0.05), z + rng.uniform(-0.06, 0.06))
            f = face(c, axis(c))
            out[f"Torso{k}"] = (c, rng.uniform(0.135, 0.195), bone, f, tumble(f))
            k += 1
    # the head: the open-mouthed face, and one more clinging on behind and above it, peering over
    out["Head1"] = (V(0, -0.2, 2.3), 0.21, "Head", V(0.05, -1, -0.08).normalized(), V(0, 0, 1))
    out["Head2"] = (V(-0.07, -0.04, 2.5), 0.17, "Head", V(-0.25, -0.75, 0.6).normalized(), V(0.1, 0.5, 1))
    for side, sx in SIDES:
        arm = ((f"{side}UpperArm", V(0.44 * sx, -0.07, 2.02), 0.17), (f"{side}UpperArm", V(0.52 * sx, -0.03, 1.78), 0.15),
               (f"{side}LowerArm", V(0.58 * sx, 0.0, 1.54), 0.15), (f"{side}LowerArm", V(0.6 * sx, -0.08, 1.3), 0.145),
               (f"{side}Hand", V(0.62 * sx, -0.17, 1.06), 0.15))
        for i, (bone, c, r) in enumerate(arm):
            f = face(c, V(sx, 0, 0), 0.45)
            out[f"{side}Arm{i + 1}"] = (c, r, bone, f, tumble(f) if i < 4 else V(0, 0, 1))
        leg = ((f"{side}UpperLeg", V(0.22 * sx, 0.03, 1.0), 0.165), (f"{side}LowerLeg", V(0.26 * sx, -0.05, 0.72), 0.16),
               (f"{side}LowerLeg", V(0.27 * sx, 0.0, 0.46), 0.15), (f"{side}Foot", V(0.27 * sx, 0.04, 0.2), 0.16))
        for i, (bone, c, r) in enumerate(leg):
            f = face(c, V(sx, -0.5, 0), 0.5)
            out[f"{side}Leg{i + 1}"] = (c, r, bone, f, tumble(f) if i < 3 else V(0, 0, 1))
    return out


def rot(v, axis, deg):
    return Quaternion(axis, math.radians(deg)) @ v


def hand_frame(side, sx):
    """For the hand creature: (centre, down the hand, palm normal facing in, across to the index)."""
    c, r, _, _, _ = slots()[f"{side}Arm5"]
    d = (SJ[f"wrist_{side}"] - SJ[f"elbow_{side}"]).normalized()
    pn = V(-sx, 0, 0)
    pn = (pn - d * pn.dot(d)).normalized()
    a = d.cross(pn).normalized()
    if a.y > 0:
        a = -a
    return c, r, d, pn, a


def finger_layout(side, sx):
    """The hand creature's legs, spread as five long fingers: {finger: [base, knuckle, tip]}."""
    c, r, d, pn, a = hand_frame(side, sx)
    out = {}
    lengths = {"Index": 0.3, "Middle": 0.33, "Ring": 0.3, "Pinky": 0.25}
    for i, f in enumerate(("Index", "Middle", "Ring", "Pinky")):
        across = 0.6 - 0.4 * i
        base_dir = (d * 0.7 + a * across * 0.75 + pn * 0.1).normalized()
        base = c + base_dir * r * 0.95
        d1 = (rot(d, pn, (1.5 - i) * 16) + pn * math.tan(math.radians(12))).normalized()
        k = base + d1 * lengths[f] * 0.5
        d2 = (d1 + pn * math.tan(math.radians(32))).normalized()
        out[f] = [base, k, k + d2 * lengths[f] * 0.5]
    base = c + (d * 0.3 + a * 0.85 + pn * 0.4).normalized() * r * 0.95
    k = base + (d * 0.5 + a * 0.6 + pn * 0.6).normalized() * 0.12
    out["Thumb"] = [base, k, k + (d * 0.85 + pn * 0.45).normalized() * 0.12]
    return out


def stack_bones():
    """name -> (head, tail, parent, roll_z_toward or None). Limb bones run along the limbs; each
    slot bone sits at its creature's centre, pointing up its body, with -Z where its eyes look."""
    up = V(0, 0, 0.2)
    b = {
        "Root": (SJ["root"], SJ["root"] + up, None, None),
        "HumanoidRootNode": (SJ["root"], SJ["root"] + up, "Root", None),
        "LowerTorso": (SJ["root"], SJ["waist"], "HumanoidRootNode", None),
        "UpperTorso": (SJ["waist"], SJ["neck"], "LowerTorso", None),
        "Head": (SJ["neck"], SJ["head_top"], "UpperTorso", None),
    }
    for s, sx in SIDES:
        c, r, d, pn, a = hand_frame(s, sx)
        b[f"{s}UpperArm"] = (SJ[f"shoulder_{s}"], SJ[f"elbow_{s}"], "UpperTorso", None)
        b[f"{s}LowerArm"] = (SJ[f"elbow_{s}"], SJ[f"wrist_{s}"], f"{s}UpperArm", None)
        b[f"{s}Hand"] = (SJ[f"wrist_{s}"], c + d * r, f"{s}LowerArm", None)
        for f, (base, k, t) in finger_layout(s, sx).items():
            b[f"{s}{f}1"] = (base, k, f"{s}Hand", None)
            b[f"{s}{f}2"] = (k, t, f"{s}{f}1", None)
        b[f"{s}UpperLeg"] = (SJ[f"hip_{s}"], SJ[f"knee_{s}"], "LowerTorso", None)
        b[f"{s}LowerLeg"] = (SJ[f"knee_{s}"], SJ[f"ankle_{s}"], f"{s}UpperLeg", None)
        b[f"{s}Foot"] = (SJ[f"ankle_{s}"], SJ[f"toe_{s}"], f"{s}LowerLeg", None)
    for name, (c, r, parent, front, upv) in slots().items():
        upv = (upv - front * upv.dot(front)).normalized()
        b[f"Slot_{name}"] = (c, c + upv * 0.12, parent, -front)
    return b
