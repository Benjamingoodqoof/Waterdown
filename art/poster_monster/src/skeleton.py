"""Rest-pose skeleton of the poster monster.

Blender units are meters, Z is up and the monster faces -Y, so its left side is +X.
Bone names follow Roblox R15 where one exists (LowerTorso, UpperTorso, LeftUpperArm...).
"""
import math

import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Matrix, Vector


def V(*a):
    return Vector(a)


HEIGHT = 2.74  # 9 ft

J = {
    "root": V(0, 0, 0),
    "hips": V(0, 0.0, 1.30),
    "waist": V(0, 0.010, 1.50),
    "chest": V(0, 0.0, 1.68),
    "neck": V(0, 0.014, 2.02),
    "head": V(0, 0.0, 2.33),
    "head_top": V(0, 0.0, 2.68),
}

SIDES = (("Left", 1.0), ("Right", -1.0))

# finger name, spread angle (deg, + toward the back of the hand), length, offset across the palm
FINGERS = (
    ("Index", -11.0, 0.33, -0.027),
    ("Middle", -3.0, 0.37, -0.009),
    ("Ring", 5.0, 0.34, 0.009),
    ("Pinky", 12.0, 0.27, 0.026),
)
SEG_FRACS = (0.42, 0.33, 0.25)
CURL_DEG = (8.0, 11.0, 12.0)

for side, sx in SIDES:
    J[f"clav_{side}"] = V(0.04 * sx, 0.01, 1.965)
    J[f"shoulder_{side}"] = V(0.222 * sx, 0.014, 1.95)
    J[f"elbow_{side}"] = J[f"shoulder_{side}"] + V(0.25 * sx, -0.03, -0.968).normalized() * 0.62
    J[f"wrist_{side}"] = J[f"elbow_{side}"] + V(0.23 * sx, -0.07, -0.971).normalized() * 0.60
    J[f"hand_{side}"] = J[f"wrist_{side}"] + V(0.20 * sx, -0.06, -0.978).normalized() * 0.11
    J[f"hip_{side}"] = V(0.10 * sx, 0.0, 1.27)
    J[f"knee_{side}"] = V(0.118 * sx, -0.03, 0.69)
    J[f"ankle_{side}"] = V(0.132 * sx, 0.012, 0.10)
    J[f"toe_{side}"] = V(0.145 * sx, -0.20, 0.03)


def hand_frame(side):
    """(along, across, palm_normal): along points down the hand, across toward the back
    (index to pinky), palm_normal toward the body."""
    sx = 1.0 if side == "Left" else -1.0
    along = (J[f"hand_{side}"] - J[f"wrist_{side}"]).normalized()
    back = V(0, 1, 0)
    across = (back - along * back.dot(along)).normalized()
    palm = V(-sx, 0, 0)
    palm = (palm - along * palm.dot(along) - across * palm.dot(across)).normalized()
    return along, across, palm


def finger_chains(side):
    """{finger: [p0, p1, p2, tip]} rest joint positions, including the thumb."""
    along, across, palm = hand_frame(side)
    base_c = J[f"hand_{side}"]
    chains = {}
    for name, spread, length, off in FINGERS:
        p = base_c + across * off - along * (0.012 * abs(off) / 0.027)
        d = Matrix.Rotation(math.radians(spread), 3, palm) @ along
        bend_axis = d.cross(palm).normalized()
        pts = [p]
        for frac, curl in zip(SEG_FRACS, CURL_DEG):
            d = Matrix.Rotation(math.radians(curl), 3, bend_axis) @ d
            p = p + d * (length * frac)
            pts.append(p)
        chains[name] = pts
    # thumb: short, from the front of the palm, angled forward and in
    p = J[f"wrist_{side}"] + (J[f"hand_{side}"] - J[f"wrist_{side}"]) * 0.45 - across * 0.03 + palm * 0.018
    d = (along * 0.55 - across * 0.7 + palm * 0.45).normalized()
    pts = [p]
    for frac, curl in zip((0.4, 0.33, 0.27), (6.0, 9.0, 10.0)):
        bend_axis = d.cross(palm).normalized()
        d = Matrix.Rotation(math.radians(curl), 3, bend_axis) @ d
        p = p + d * (0.20 * frac)
        pts.append(p)
    chains["Thumb"] = pts
    return chains


# bone name -> (head, tail, parent, influence radius for skin weights, roll target)
BONES = {}


def _bone(name, head, tail, parent, radius, roll=V(0, -1, 0)):
    BONES[name] = (Vector(head), Vector(tail), parent, radius, roll)


# Roblox builds the HumanoidRootPart from the rig root, so the root sits at the pelvis
# (Root > HumanoidRootNode > LowerTorso, as in Roblox's own skinned character rigs).
_bone("Root", J["hips"], J["hips"] + V(0, 0, 0.12), None, 0.0)
_bone("HumanoidRootNode", J["hips"], J["hips"] + V(0, 0, 0.1), "Root", 0.0)
_bone("LowerTorso", J["hips"], J["waist"], "HumanoidRootNode", 0.14)
_bone("Spine", J["waist"], J["chest"], "LowerTorso", 0.13)
_bone("UpperTorso", J["chest"], J["neck"], "Spine", 0.16)
_bone("Neck", J["neck"], J["head"], "UpperTorso", 0.05)
_bone("Head", J["head"], J["head_top"], "Neck", 0.20)
for _side, _sx in SIDES:
    _bone(f"{_side}Shoulder", J[f"clav_{_side}"], J[f"shoulder_{_side}"], "UpperTorso", 0.06)
    _bone(f"{_side}UpperArm", J[f"shoulder_{_side}"], J[f"elbow_{_side}"], f"{_side}Shoulder", 0.065)
    _bone(f"{_side}LowerArm", J[f"elbow_{_side}"], J[f"wrist_{_side}"], f"{_side}UpperArm", 0.05)
    _bone(f"{_side}Hand", J[f"wrist_{_side}"], J[f"hand_{_side}"], f"{_side}LowerArm", 0.05)
    _palm = hand_frame(_side)[2]
    for _f, _pts in finger_chains(_side).items():
        for _k in range(3):
            _bone(f"{_side}{_f}{_k + 1}", _pts[_k], _pts[_k + 1],
                  f"{_side}Hand" if _k == 0 else f"{_side}{_f}{_k}", 0.016, _palm)
    _bone(f"{_side}UpperLeg", J[f"hip_{_side}"], J[f"knee_{_side}"], "LowerTorso", 0.085)
    _bone(f"{_side}LowerLeg", J[f"knee_{_side}"], J[f"ankle_{_side}"], f"{_side}UpperLeg", 0.06)
    _bone(f"{_side}Foot", J[f"ankle_{_side}"], J[f"toe_{_side}"], f"{_side}LowerLeg", 0.07, V(0, 0, 1))


def add_flap_bones(name, top, mid, bottom, parent, roll):
    _bone(f"{name}1", top, mid, parent, 0.05, roll)
    _bone(f"{name}2", mid, bottom, f"{name}1", 0.05, roll)
