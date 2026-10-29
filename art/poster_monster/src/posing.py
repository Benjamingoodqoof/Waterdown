"""Pose helpers. Rotations are given about armature-space axes measured in the bone's rest
frame, so a child keeps its meaning when its parent moves. Axes "lx", "ly", "lz" are the
bone's own local axes instead.

Axis conventions (the monster faces -Y, its left is +X):
  +X on an upright bone bends it forward; -X on a hanging limb swings it forward.
  +Y tilts an upright bone toward the monster's left.
  +Z turns an upright bone toward the monster's left.
  Finger bones have local Z toward the palm, so +lx curls a finger in.
"""
import math

import bpy  # noqa: F401  (loads mathutils when running as a module)
from mathutils import Quaternion, Vector

import skeleton as SK

AX = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
LOCAL = {"lx": Vector((1, 0, 0)), "ly": Vector((0, 1, 0)), "lz": Vector((0, 0, 1))}
FINGERS = ("Index", "Middle", "Ring", "Pinky")


def bone_quat(bone, rots):
    """rots: [(axis, degrees), ...] applied in order."""
    Rinv = bone.matrix_local.to_3x3().inverted()
    q = Quaternion()
    for axis, deg in rots:
        if isinstance(axis, str) and axis in LOCAL:
            a = LOCAL[axis]
        else:
            a = Rinv @ (AX[axis] if isinstance(axis, str) else Vector(axis))
        q = Quaternion(a.normalized(), math.radians(deg)) @ q
    return q


def mirror(rots, side):
    """Mirror a left-side rotation list for the right side (flip Y and Z turns)."""
    if side == "Left":
        return rots
    out = []
    for a, d in rots:
        if isinstance(a, str):
            out.append((a, -d if a in ("y", "z") else d))
        else:
            out.append(((-a[0], a[1], a[2]), -d))
    return out


def sided(pose_left, sides=("Left", "Right")):
    """Expand '{s}' bone-name templates for both sides, mirroring the right."""
    out = {}
    for name, rots in pose_left.items():
        if "{s}" in name:
            for s in sides:
                out[name.format(s=s)] = mirror(rots, s)
        else:
            out[name] = rots
    return out


def hand(side, curl, spread=0.0, thumb=None, jitter=None):
    """Finger rotations: curl degrees per joint (tuple of 3 or a number), fan spread in degrees."""
    along, across, palm = SK.hand_frame(side)
    fan_axis = tuple(along.cross(across).normalized())
    c = curl if isinstance(curl, (tuple, list)) else (curl, curl, curl)
    out = {}
    for i, f in enumerate(FINGERS):
        j = (jitter or {}).get(f, 0.0)
        for k in (1, 2, 3):
            rots = [("lx", c[k - 1] + j)]
            if k == 1 and spread:
                rots.append((fan_axis, (i - 1.5) * spread))
            out[f"{side}{f}{k}"] = rots
    t = thumb if thumb is not None else tuple(x * 0.6 for x in c)
    for k in (1, 2, 3):
        out[f"{side}Thumb{k}"] = [("lx", t[k - 1])]
    return out


def apply_pose(rig, pose, loc=None, frame=None):
    """pose: {bone: [(axis, deg), ...]}; bones not listed return to rest.
    loc: {bone: (x, y, z)} armature-space offsets. Inserts keys when frame is given."""
    loc = loc or {}
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = bone_quat(pb.bone, pose.get(pb.name, []))
        off = loc.get(pb.name)
        pb.location = (pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)) if off else Vector()
        if frame is not None:
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            pb.keyframe_insert("location", frame=frame)


IDLE = sided({
    "LowerTorso": [("x", 4)],
    "Spine": [("x", 10), ("y", -3)],
    "UpperTorso": [("x", 16), ("y", 5)],
    "Neck": [("x", 24)],
    "Head": [("x", -16), ("y", 21), ("z", -10)],
    "{s}Shoulder": [("x", 8)],
    "{s}UpperArm": [("y", 6), ("x", -6)],
    "{s}LowerArm": [("x", -16)],
    "{s}Hand": [("x", -8)],
    "{s}UpperLeg": [("x", -8)],
    "{s}LowerLeg": [("x", 16)],
    "{s}Foot": [("x", -8)],
})
IDLE.update(hand("Left", (10, 14, 12), 6))
IDLE.update(hand("Right", (14, 18, 16), 4))
