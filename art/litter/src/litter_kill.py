#!/usr/bin/env python3
"""The stack's kill, "Pulled in": it rears up, its creatures squirming, and its right arm
shoots out, stretching as the creatures in it spread apart. The hand clamps on the player and
yanks them off their feet, face down on the floor. It drags them in across the floor, tug by
tug (the window for a teammate's light to save them), then hauls them up to its head creature's
open mouth and pulls them face first into its body, through the wall of small black bodies
and eyes, closing its other arm over them while the whole pile writhes.

Writes the stack's "Kill" action into stack.blend, and the player's half on the R6 rig
(export/Stack_Kill_Victim.blend). Both are 4 s and start together, with the player's
HumanoidRootPart DISTANCE studs in front of the stack's, facing it.

Markers: Grab 14 (the save window opens), Floor 22 (they hit the floor), Tug 32, 42 and 52,
Lift 58 (the window closes), Mouth 66, Black 74 (the camera is inside the stack), End 120.

Usage: python3 litter_kill.py LITTER_DIR PREVIEW_BLEND
"""
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
import kill_core as K  # noqa: E402
import litter_animate as LA  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.661, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 4.8
LENGTH = 120
GRAB, FLOOR, TUGS, LIFT, MOUTH, IN = 14, 22, (32, 42, 52), 58, 66, 74
MARKERS = {0: "Notice", GRAB: "Grab", FLOOR: "Floor", 32: "Tug", 42: "Tug", 52: "Tug", LIFT: "Lift", MOUTH: "Mouth",
           IN: "Black", LENGTH: "End"}
SIDES = (("Left", 1.0), ("Right", -1.0))
CHEST_IN = Vector((0.0, 0.0, 1.66))  # the middle of its body, at rest
MOUTH_FRONT = Vector((0.0, -0.72, 2.2))  # just in front of the head creature's mouth, at rest
LOC = ("LowerTorso", "RightLowerArm", "RightHand")
HITS = (GRAB, FLOOR) + TUGS


def prone(z):
    """Face down on the floor, head toward the stack, their torso's middle at z (studs)."""
    return Matrix.Translation((0.0, -2.2, z)) @ K.rot("X", -68)  # chest up off the floor, clawing


def drag_z(f):
    """How far in they've been dragged: three tugs, each a sharp pull, then a pause."""
    z = -1.0
    for t in TUGS:
        if f > t - 3:
            z -= 0.45 * K.back_out((f - (t - 3)) / 4, 1.2)
    return z


def monster_body(an, f):
    rear = A.bump(f, 0, 6, 12)
    shoot = ss(6, GRAB, f)
    pulse = sum(A.bump(f, t - 3, t, t + 6) for t in TUGS)
    lift = ss(LIFT, MOUTH, f)
    yank = ss(MOUTH, IN, f)
    writhe = ss(IN - 4, IN + 6, f)
    lunge_mouth = window(f, LIFT, MOUTH, IN - 2, IN + 6)
    pose = {
        "LowerTorso": [("x", 6 + 14 * shoot * (1 - lift) - 6 * rear + 4 * pulse - 6 * yank), ("z", 8 * shoot * (1 - lift))],
        "UpperTorso": [("x", 10 - 16 * rear + 18 * shoot * (1 - lift) + 6 * pulse - 10 * lift + 18 * writhe
                        + 3 * math.sin(f / 4) * writhe), ("z", 14 * shoot * (1 - lift) - 6 * pulse)],
        "Head": [("x", -20 * rear - 14 * shoot * (1 - lift) + 18 * lift), ("z", -8 * shoot * (1 - writhe))],
        # the open-mouthed head creature lunges at them as they're hauled up
        "Slot_Head1": [("x", -24 * lunge_mouth + 8 * math.sin(f / 3.0) * lunge_mouth), ("y", 12 * math.sin(f / 5) * (1 - writhe))],
        "LeftUpperArm": A.mirror([("x", -24 * rear), ("y", -45 * rear)], "Left"),
    }
    pose.update(LA.creatures(f / 40.0, 4.0 + 4 * pulse + 14 * writhe + 6 * yank, hits=(), look=12 + 30 * writhe))
    an.fk(pose, {"LowerTorso": (0.0, -0.2 * shoot * (1 - lift) + 0.08 * yank, -0.06 * shoot - 0.08 * writhe)})
    step = ss(6, 12, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.3 * step, 0.12 * math.sin(math.pi * step))) if side == "Right" else Vector((0, -0.05 * step, 0))
        an.leg(side, rest + off, 0.0, 0.14 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    head_c = pl.point_to_victim(an.pb["Slot_Head1"].matrix.translation)
    if f <= GRAB:
        K.recoil(v, f, 1, 8, head_c, (4, 10))
        ctx["grab_torso"] = v.torso.copy()
        K.jolt_head(v, f, HITS, 12)
        return v
    if f <= FLOOR:  # yanked forward off their feet, face down
        t = (f - GRAB) / (FLOOR - GRAB)
        v.torso = K.blend_cf(ctx["grab_torso"], prone(-1.0), t * t)
        flail = 1.0
    elif f <= LIFT:  # dragged in across the floor
        v.torso = prone(drag_z(f))
        if f < FLOOR + 5:
            v.torso.translation.y += 0.2 * math.sin(math.pi * (f - FLOOR) / 5)
        flail = 0.6
    else:  # hauled up to its mouth, then pulled in, head first
        mouth = pl.point_to_victim(an.rest_delta("Slot_Head1") @ MOUTH_FRONT)
        inside = pl.point_to_victim(an.rest_delta("UpperTorso") @ CHEST_IN)
        lift = K.back_out((f - LIFT) / (MOUTH - LIFT), 1.3)
        yank = ss(MOUTH + 1, IN, f)
        ctx.setdefault("lift_from", prone(drag_z(LIFT)))
        pitch = 40 + 40 * yank
        R = K.rot("X", -pitch)
        hv = K.Victim()
        hv.hang_from_head(Matrix.Translation(mouth.lerp(inside, yank)) @ R, R)
        v.torso = K.blend_cf(ctx["lift_from"], hv.torso, lift) if lift < 1 else hv.torso
        flail = 0.8 * (1 - yank)
    # arms clawing out ahead of them (at the floor, at its arm); legs kicking
    for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
        reach = Vector((0.9 * sx, -0.5 + 0.4 * math.sin(f / 2.3 + sx), -0.6))  # out to the sides, clear of the view
        v.point(arm, (v.torso.to_3x3() @ reach).normalized().lerp(Vector((0, -1, 0)), 0.2 * (1 - flail)).normalized())
    K.kick_legs(v, f, flail * 0.8)
    # on the floor they look along it at the body coming at them; lifted, at the head creature
    body_c = pl.point_to_victim(an.pb["UpperTorso"].head)
    v.look(head_c if (f <= GRAB or f > LIFT) else body_c, limit=80)
    K.jolt_head(v, f, HITS, 14)
    return v


def kill(an, ctx, f):
    pl = ctx["pl"]
    monster_body(an, f)
    v = victim(an, ctx, f)
    T = an.rest_delta("UpperTorso")
    # the right hand: shoots out to their chest, then holds them by the back of the neck
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    if f <= GRAB:
        if "grab_point" not in ctx:
            g = K.recoil(K.Victim(), GRAB, 1, 8)
            ctx["grab_point"] = pl.point_to_blender(g.torso @ Vector((0, 0.3, -0.75)))
        s = ss(6, GRAB, f)
        target = rest.lerp(ctx["grab_point"], A.ease(s)) + Vector((0, 0, 0.2)) * math.sin(math.pi * s)
    else:
        target = pl.point_to_blender(v.torso @ Vector((0, 1.1, 0.4)))  # the back of their neck
    K.reach(an, "Right", target, T.to_3x3() @ Vector((-0.6, 0.3, -0.7)))
    import bpy as _b
    _b.context.view_layer.update()
    gap = (target - an.pb["RightLowerArm"].tail).length
    stretch = min(1.0, gap) if f < IN else 0.0
    an.pb["RightLowerArm"].location = (0, stretch * 0.5, 0)
    an.pb["RightHand"].location = (0, stretch * 0.5, 0)
    close = ss(IN - 4, IN + 12, f)
    if close:
        lt = T @ Vector((0.05, -0.5, 1.5))
        K.reach(an, "Left", an.pb["LeftLowerArm"].tail.lerp(lt, close), T.to_3x3() @ Vector((0.8, 0.2, -0.3)))
    grip = ss(GRAB - 3, GRAB, f)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, (-12 + 54 * grip) if side == "Right" else (10 + 30 * close), spread=10 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """The Litter (stack) kill, the player's half: InternalArmature carries the action
Stack_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. The timeline markers are the beats:
Grab (save window opens), Floor, Tug x3, Lift (window closes), Mouth, Black, End.
The 'Monster (reference)' collection holds the stack playing its half, at your in-game size,
lined up where the game should put it: 4.8 studs in front of the player, facing them.
"""


def main(litter_dir, preview):
    blend = os.path.join(litter_dir, "stack.blend")
    ctx = K.run_kill(blend, "Stack_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Stack_Kill_Victim", MARKERS,
                     loc_bones=LOC)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(litter_dir, "export", "Stack_Kill_Victim.blend"), ctx["parts"],
                     "Stack_Kill_Victim", MARKERS, (blend, "Stack_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
