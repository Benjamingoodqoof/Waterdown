"""Shared layout for the Stand-In: joints, hands, the rig and the palette.

Blender units are meters, Z is up, he faces -Y, so his left side is +X. He's 2.69 m (8.75 ft)
to the top of his monitor, very tall and thin, standing slightly stooped.
"""
import math

import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Quaternion, Vector


def V(*a):
    return Vector(a)


HEIGHT = 2.69
SIDES = (("Left", 1.0), ("Right", -1.0))

PALETTE = {  # from the monster sheet
    "suit": (242, 104, 16), "suit_shade": (201, 82, 31), "monitor": (255, 144, 85), "dead_screen": (27, 12, 6),
    "screen_glow": (255, 176, 122), "shirt": (255, 240, 226), "tie": (122, 45, 6), "hands": (244, 184, 140),
}

# ---------------------------------------------------------------- joints
J = {
    "root": V(0, 0.02, 1.36),
    "waist": V(0, 0.02, 1.6),
    "neck": V(0, -0.02, 2.24),  # where the cable comes up out of his collar
    "head_top": V(0, -0.05, 2.69),
}
for _s, _x in SIDES:
    J[f"shoulder_{_s}"] = V(0.205 * _x, 0.005, 2.165)
    J[f"elbow_{_s}"] = V(0.235 * _x, 0.04, 1.66)
    J[f"wrist_{_s}"] = V(0.25 * _x, 0.0, 1.2)
    J[f"hip_{_s}"] = V(0.095 * _x, 0.02, 1.32)
    J[f"knee_{_s}"] = V(0.105 * _x, -0.02, 0.72)
    J[f"ankle_{_s}"] = V(0.105 * _x, 0.03, 0.095)
    J[f"toe_{_s}"] = V(0.11 * _x, -0.14, 0.02)

# the monitor: its underside sits just above the collar, tipped forward a little (he's stooped)
MONITOR = {"w": 0.42, "h": 0.36, "bezel_d": 0.075, "depth": 0.42, "bottom": 2.33, "y": -0.04, "tilt": 6}
# the cable that hangs down his back, held by three bones so it can sway
CABLE = [V(0.06, 0.2, 2.36), V(0.07, 0.17, 2.1), V(0.06, 0.16, 1.7), V(0.03, 0.17, 1.3), V(0.0, 0.2, 0.92)]

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def rot(v, axis, deg):
    return Quaternion(axis, math.radians(deg)) @ v


def hand_frame(side, sx):
    """(wrist, down the hand, palm normal facing his thigh, across toward the index finger)."""
    w = J[f"wrist_{side}"]
    d = (w - J[f"elbow_{side}"]).normalized()
    pn = V(-sx, 0, 0)
    pn = (pn - d * pn.dot(d)).normalized()
    a = d.cross(pn).normalized()
    if a.y > 0:
        a = -a
    return w, d, pn, a


def hand_layout(side, sx):
    """Long thin fingers hanging relaxed, curled a little: {finger: [knuckle, middle, tip]}."""
    w, d, pn, a = hand_frame(side, sx)
    out = {}
    lengths = {"Index": 0.19, "Middle": 0.215, "Ring": 0.2, "Pinky": 0.165}
    for i, f in enumerate(("Index", "Middle", "Ring", "Pinky")):
        k = w + d * 0.115 + a * (0.027 - 0.018 * i)
        d1 = (rot(d, pn, (1.5 - i) * 3) + pn * math.tan(math.radians(10))).normalized()
        m = k + d1 * lengths[f] * 0.52
        d2 = (d1 + pn * math.tan(math.radians(22))).normalized()
        out[f] = [k, m, m + d2 * lengths[f] * 0.48]
    t0 = w + d * 0.035 + a * 0.032 + pn * 0.012
    t1 = t0 + (d * 0.6 + a * 0.55 + pn * 0.35).normalized() * 0.07
    out["Thumb"] = [t0, t1, t1 + (d * 0.85 + a * 0.15 + pn * 0.3).normalized() * 0.065]
    return out


def bones():
    """name -> (head, tail, parent). Bones run along the limbs."""
    up = V(0, 0, 0.2)
    b = {
        "Root": (J["root"], J["root"] + up, None),
        "HumanoidRootNode": (J["root"], J["root"] + up, "Root"),
        "LowerTorso": (J["root"], J["waist"], "HumanoidRootNode"),
        "UpperTorso": (J["waist"], J["neck"], "LowerTorso"),
        "Head": (J["neck"], J["head_top"], "UpperTorso"),
        "Cable1": (CABLE[1], CABLE[2], "UpperTorso"),
        "Cable2": (CABLE[2], CABLE[3], "Cable1"),
        "Cable3": (CABLE[3], CABLE[4], "Cable2"),
    }
    for s, sx in SIDES:
        w, d, pn, a = hand_frame(s, sx)
        b[f"{s}UpperArm"] = (J[f"shoulder_{s}"], J[f"elbow_{s}"], "UpperTorso")
        b[f"{s}LowerArm"] = (J[f"elbow_{s}"], J[f"wrist_{s}"], f"{s}UpperArm")
        b[f"{s}Hand"] = (J[f"wrist_{s}"], w + d * 0.115, f"{s}LowerArm")
        for f, (k, m, t) in hand_layout(s, sx).items():
            b[f"{s}{f}1"] = (k, m, f"{s}Hand")
            b[f"{s}{f}2"] = (m, t, f"{s}{f}1")
        b[f"{s}UpperLeg"] = (J[f"hip_{s}"], J[f"knee_{s}"], "LowerTorso")
        b[f"{s}LowerLeg"] = (J[f"knee_{s}"], J[f"ankle_{s}"], f"{s}UpperLeg")
        b[f"{s}Foot"] = (J[f"ankle_{s}"], J[f"toe_{s}"], f"{s}LowerLeg")
    return b
