"""Shared layout for the Receiver: joints, hands, the rig and the palette.

Blender units are meters, Z is up, he faces -Y, so his left side is +X. He's 2.44 m (8 ft)
to the top of the cradle prongs, standing hunched with his knees bent and his arms hanging
long. His left hand grips the handset; his right hand is an open claw.
"""
import math

import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Quaternion, Vector


def V(*a):
    return Vector(a)


HEIGHT = 2.44

PALETTE = {  # from the monster sheet
    "cord": (7, 9, 12), "ridge": (62, 65, 71), "smoke": (138, 143, 150), "glass": (42, 44, 49),
    "chrome": (201, 211, 218), "water": (11, 12, 14), "copper": (192, 122, 58), "alarm": (255, 42, 31),
}

SIDES = (("Left", 1.0), ("Right", -1.0))

# ---------------------------------------------------------------- joints
J = {
    "root": V(0, 0.06, 1.08),
    "waist": V(0, 0.07, 1.32),
    "neck": V(0, -0.13, 1.95),
    "head": V(0, -0.25, 2.05),  # underside of the phone
    "head_top": V(0, -0.25, 2.32),
    "dial": V(0, -0.205, 1.68),  # center of the dial in his chest
}
DIAL_NORMAL = V(0, -1, -0.2).normalized()
for _s, _x in SIDES:
    J[f"shoulder_{_s}"] = V(0.37 * _x, -0.07, 1.86)
    J[f"elbow_{_s}"] = V(0.47 * _x, 0.05, 1.42)
    J[f"wrist_{_s}"] = V(0.48 * _x, -0.14, 1.0)
    J[f"hip_{_s}"] = V(0.14 * _x, 0.05, 1.03)
    J[f"knee_{_s}"] = V(0.21 * _x, -0.15, 0.6)
    J[f"ankle_{_s}"] = V(0.18 * _x, 0.06, 0.12)
    J[f"toe_{_s}"] = V(0.21 * _x, -0.17, 0.03)

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def rot(v, axis, deg):
    return Quaternion(axis, math.radians(deg)) @ v


def hand_frame(side, sx):
    """(wrist, down the hand, palm normal facing his thigh, across toward the index finger)."""
    w = J[f"wrist_{side}"]
    d = (w - J[f"elbow_{side}"]).normalized()
    d = (d + V(0, -0.15, 0)).normalized()  # the hand carries on a little forward
    pn = V(-sx, 0, 0)
    pn = (pn - d * pn.dot(d)).normalized()
    a = d.cross(pn).normalized()
    if a.y > 0:
        a = -a
    return w, d, pn, a


def grip(side, sx):
    """Where the handset's handle sits in the left fist: (center, handle axis)."""
    w, d, pn, a = hand_frame(side, sx)
    return w + d * 0.19 + pn * 0.048, rot(a, pn, -35)


def hand_layout(side, sx):
    """Each finger as [knuckle, middle joint, tip], plus extra points the cord curls through.
    Returns {finger: (joints, path)}."""
    w, d, pn, a = hand_frame(side, sx)
    out = {}
    lengths = {"Index": 0.27, "Middle": 0.3, "Ring": 0.27, "Pinky": 0.22}
    for i, f in enumerate(("Index", "Middle", "Ring", "Pinky")):
        k = w + d * 0.15 + a * (0.06 - 0.04 * i) + pn * (0.008 if i in (1, 2) else 0.0)
        L1, L2 = lengths[f] * 0.55, lengths[f] * 0.45
        if side == "Left":  # wrapped around the handset handle
            g, _ = grip(side, sx)
            c = g + a * a.dot(k - g)
            r0 = (k - c).length
            u0 = (k - c).normalized()
            # curl under the handle first (toward his palm), then over the front and round the outside
            sign = 1 if rot(u0, a, 45).dot(-pn) > rot(u0, a, -45).dot(-pn) else -1
            path = [c + rot(u0, a, sign * 230 * t / 8) * (r0 + (0.047 - r0) * min(1.0, t / 3)) for t in range(9)]
            joints = [path[0], path[4], path[-1]]
        else:  # an open claw, fingers spread and hooked toward the palm
            d1 = (rot(d, pn, (1.5 - i) * 7) + pn * math.tan(math.radians(22))).normalized()
            m = k + d1 * L1
            d2 = (d1 + pn * math.tan(math.radians(50))).normalized()
            t = m + d2 * L2
            path = [k, k + d1 * L1 * 0.5, m, m + d2 * L2 * 0.5, t]
            joints = [k, m, t]
        out[f] = (joints, path)
    t0 = w + d * 0.06 + a * 0.065 + pn * 0.025
    if side == "Left":
        t1 = t0 + (d * 0.3 + a * 0.5 + pn * 0.8).normalized() * 0.1
        t2 = t1 + (d * 0.75 + pn * 0.2 - a * 0.3).normalized() * 0.09
    else:
        t1 = t0 + (d * 0.5 + a * 0.75 + pn * 0.45).normalized() * 0.1
        t2 = t1 + (d * 0.75 + a * 0.2 + pn * 0.6).normalized() * 0.09
    out["Thumb"] = ([t0, t1, t2], [t0, (t0 + t1) / 2, t1, (t1 + t2) / 2, t2])
    return out


# ---------------------------------------------------------------- rig
def bones():
    """name -> (head, tail, parent). Bones run along the limbs."""
    up = V(0, 0, 0.2)
    b = {
        "Root": (J["root"], J["root"] + up, None),
        "HumanoidRootNode": (J["root"], J["root"] + up, "Root"),
        "LowerTorso": (J["root"], J["waist"], "HumanoidRootNode"),
        "UpperTorso": (J["waist"], J["neck"], "LowerTorso"),
        "Head": (J["neck"], J["head_top"], "UpperTorso"),
        "DialSpin": (J["dial"], J["dial"] + DIAL_NORMAL * 0.1, "UpperTorso"),
    }
    for s, sx in SIDES:
        w, d, pn, a = hand_frame(s, sx)
        b[f"{s}UpperArm"] = (J[f"shoulder_{s}"], J[f"elbow_{s}"], "UpperTorso")
        b[f"{s}LowerArm"] = (J[f"elbow_{s}"], J[f"wrist_{s}"], f"{s}UpperArm")
        b[f"{s}Hand"] = (J[f"wrist_{s}"], w + d * 0.15, f"{s}LowerArm")
        for f, (joints, _) in hand_layout(s, sx).items():
            b[f"{s}{f}1"] = (joints[0], joints[1], f"{s}Hand")
            b[f"{s}{f}2"] = (joints[1], joints[2], f"{s}{f}1")
        b[f"{s}UpperLeg"] = (J[f"hip_{s}"], J[f"knee_{s}"], "LowerTorso")
        b[f"{s}LowerLeg"] = (J[f"knee_{s}"], J[f"ankle_{s}"], f"{s}UpperLeg")
        b[f"{s}Foot"] = (J[f"ankle_{s}"], J[f"toe_{s}"], f"{s}LowerLeg")
    return b


# ---------------------------------------------------------------- props atlas (1024 px, x right, y down)
ATLAS = 1024
PROPS = {
    "plastic": (0, 0, 256, 256),
    "chrome": (256, 0, 384, 128),
    "rubber": (384, 0, 512, 128),
    "socket": (256, 128, 384, 256),
    "copper": (384, 128, 512, 256),
    "plate": (512, 0, 768, 256),
    "wheel": (768, 0, 1024, 256),
    "hub": (0, 256, 128, 384),
    "plug": (128, 256, 256, 384),
    "cap": (256, 256, 384, 384),
    "gold": (384, 256, 512, 384),
}


def region_uv(name, inset=3):
    x0, y0, x1, y1 = PROPS[name]
    return (x0 + inset) / ATLAS, 1 - (y1 - inset) / ATLAS, (x1 - inset) / ATLAS, 1 - (y0 + inset) / ATLAS


def in_region(name, u, v):
    """Map (u, v) in 0..1 into a props region's UV rect."""
    u0, v0, u1, v1 = region_uv(name)
    return u0 + (u1 - u0) * min(1.0, max(0.0, u)), v0 + (v1 - v0) * min(1.0, max(0.0, v))


# ---------------------------------------------------------------- the cord texture tiles along the cord
CORD_TILE = 0.064  # meters of cord per texture repeat (4 coils)
COILS_PER_TILE = 4
CORD_VARIANTS = ("black", "smoke")  # side by side in u, half the texture each

# ---------------------------------------------------------------- the phone head (local: origin at the
# middle of its underside, x right, y back, z up) and the dial in his chest
SHELL_H = 0.19
SOCKET = {"z": 0.085, "r": 0.065, "depth": 0.04}  # where the dial was torn out of the front face


def shell_uv(x, z):
    """The glass shell is mapped from the front."""
    return (x + 0.22) / 0.44, z / 0.24


DIAL = {"ring": 0.125, "plate": 0.106, "wheel": 0.1, "holes_at": 0.074, "hole": 0.0165, "hub": 0.034}
# clock angle (degrees clockwise from the top, seen from the front) -> digit, out of order
DIAL_DIGITS = [(200, "0"), (230, "9"), (260, "8"), (290, "3"), (320, "6"), (350, "5"), (20, "4"), (50, "7"),
               (80, "2"), (110, "1")]
FINGER_STOP = 155
