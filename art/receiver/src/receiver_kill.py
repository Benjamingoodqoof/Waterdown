#!/usr/bin/env python3
"""The Receiver's kill, "Hold the line" into "Dial": he lunges, grabs the player round the
chest with his claw and lifts them to his face. He presses his handset to their ear, turns
the empty dial socket in his phone head right up to their face, and the dial in his chest
dials and dials. Then his head drives into theirs and he drops them.

Writes the Receiver's "Kill" action into the blend, and the player's half as an R6
KeyframeSequence (export/Receiver_Kill_Victim.rbxmx). Both are 4 s and start together, with the
player's HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers (KeyframeReached on the player's track): Notice 0, Grab 24, Handset 46 (play the
player's voice line, crackly), DialStart 58 (QTE starts), DialEnd 98 (busy signal; QTE ends),
Black 104 (his head hits the camera), Drop 106, End 120.

Usage: python3 receiver_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
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
import receiver_animate as R  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.2825, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 4.5
LENGTH = 120
GRAB, LIFTED, HANDSET, DIAL, DIAL_END, HIT, DROP, LAND = 24, 44, 46, 58, 98, 104, 106, 116
MARKERS = {0: "Notice", GRAB: "Grab", HANDSET: "Handset", DIAL: "DialStart", DIAL_END: "DialEnd", HIT: "Black",
           DROP: "Drop", LENGTH: "End"}
SOCKET = Vector((0.0, -0.43, 2.11))  # the mouth of the dial socket in his phone head, at rest
SIDES = (("Left", 1.0), ("Right", -1.0))


def dial(t):
    """His chest dial dialling fast, digit after digit: each pulled round to the stop in 5
    frames and whirring back at 20 degrees a frame (every pull ends back at rest)."""
    for pull in (270, 120, 300, 90, 210):
        back = pull / 20.0
        span = 5 + 1 + back + 2
        if t < 0:
            return 0.0
        if t < span:
            if t < 5:
                return -pull * A.ease(t / 5)
            if t < 6:
                return -pull
            return -pull + min(pull, (t - 6) * 20.0)
        t -= span
    return 0.0


def monster_body(an, f):
    snap = A.bump(f, 0, 5, 14)  # the head snaps round to the player
    lunge = ss(8, 22, f)
    hold = ss(GRAB, LIFTED, f)
    hit = A.bump(f, 99, 103, 110)
    drop = ss(DROP, LAND, f)
    pose = {
        "LowerTorso": [("x", 6 + 14 * lunge - 8 * hold), ("y", 4 * snap)],
        "UpperTorso": [("x", 6 + 18 * lunge - 10 * hold + 14 * hit), ("z", -6 * hold)],
        # the head comes level with the player's face, the socket turned to them; it drives in
        "Head": [("x", -6 - 8 * lunge + 14 * hold + 16 * hit - 10 * drop), ("y", -14 * snap + 8 * window(f, 60, 70, 88, 98)),
                 ("z", 6 * snap)],
        "DialSpin": [("ly", dial(f - DIAL))],
    }
    an.fk(pose, {"LowerTorso": (0.0, -0.3 * lunge + 0.05 * hold - 0.16 * hit, -0.1 * lunge + 0.05 * hold)})
    step = ss(8, 20, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.42 * step, 0.12 * math.sin(math.pi * step))) if side == "Right" else Vector((0, -0.08 * step, 0))
        an.leg(side, rest + off, 0.0, 0.12 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    socket = pl.point_to_victim(an.rest_delta("Head") @ SOCKET)
    if f <= GRAB:
        K.recoil(v, f, 4, 18, socket, (10, 22))
        ctx["grab_head"] = v.head_world().copy()
        return v
    face = pl.point_to_victim(an.rest_delta("Head") @ (SOCKET + Vector((0, -0.24, -0.02))))
    lift = ss(GRAB, LIFTED, f)
    pos = ctx["grab_head"].translation.lerp(face, lift)
    kick = window(f, GRAB, GRAB + 4, DIAL_END - 6, DROP)
    sw = K.rot("X", 5 * math.sin(f / 4.0) * kick) @ K.rot("Z", 4 * math.sin(f / 3.3) * kick)
    head_cf = K.look_cf(pos, socket)
    held = K.Victim()
    held.hang_from_head(head_cf, sw)
    if f >= DROP:
        lying = Matrix.Translation((-0.2, -2.45, -1.6)) @ K.rot("Y", -15) @ K.rot("X", 88)
        ctx.setdefault("drop_torso", held.torso.copy())
        return K.fall(v, ctx["drop_torso"], f, DROP, LAND, lying, socket)
    v.torso, v.T["Head"] = held.torso, held.T["Head"]
    K.kick_legs(v, f, kick)
    return v


def claw_and_handset(an, ctx, f, v):
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    torso_b = pl.to_blender(v.torso)
    tc = torso_b.translation
    right_v = torso_b.to_3x3().col[0].normalized()
    up_v = torso_b.to_3x3().col[1].normalized()
    fwd_v = -torso_b.to_3x3().col[2].normalized()  # the player's facing (toward him)
    # the claw: reaches for the chest, clamps round it, opens to let go
    reach = ss(8, GRAB, f)
    release = ss(DROP, DROP + 6, f)
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    chest = tc + fwd_v * (0.5 * KM + 0.07) + up_v * 0.25 * KM
    target = rest.lerp(chest, A.ease(reach)) + (T.to_3x3() @ Vector((-0.3, -1, 0.2))) * 0.15 * math.sin(math.pi * reach)
    if release:
        target = target.lerp(rest + Vector((-0.1, -0.3, 0.2)), release)
    hand_dir = (up_v * 0.2 - right_v * 0.3 - fwd_v * 0.2).normalized()
    K.reach(an, "Right", target, T.to_3x3() @ Vector((-0.8, 0.4, -0.4)),
            hand_dir if 0.5 < reach and release < 0.5 else None, -fwd_v)
    # the handset: from his side up to the player's ear, earcups to it, mouthpiece to their mouth
    lift = ss(GRAB + 4, HANDSET, f) * (1 - ss(HIT - 2, DROP + 4, f))
    head_b = pl.to_blender(v.head_world())
    hx = head_b.to_3x3().col[0].normalized()
    hu = head_b.to_3x3().col[1].normalized()
    hf = -head_b.to_3x3().col[2].normalized()
    centre = head_b.translation + hx * (0.62 * KM + 0.06) + hf * 0.02 - hu * 0.06
    y = (hf * 0.8 - hu * 0.6).normalized()  # the mouthpiece end
    z = (hx - y * hx.dot(y)).normalized()  # earcups (its underside) to the ear
    x = y.cross(z)
    Mset = Matrix((x, y, z)).transposed().to_4x4()
    M1 = Matrix.Translation(centre) @ Mset @ Matrix.Translation(-R.HANDSET_C) @ an.pb["LeftHand"].bone.matrix_local
    import bpy as _b
    _b.context.view_layer.update()
    an.fk({"LeftUpperArm": [("x", -0.1)], "LeftLowerArm": [("x", -1.9)]})
    _b.context.view_layer.update()
    M0 = an.pb["LeftHand"].matrix.copy()
    p = M0.translation.lerp(M1.translation, lift) + Vector((0.15, 0.0, 0.05)) * math.sin(math.pi * lift)
    q = M0.to_quaternion().slerp(M1.to_quaternion(), A.ease(min(1.0, lift * 1.3)))
    M = q.to_matrix().to_4x4()
    M.translation = p
    R.place_left_hand(an, M, Vector((0.5, 1.0, -0.2)).lerp(Vector((0.7, 0.1, -0.7)), lift))
    return reach, release


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    reach, release = claw_and_handset(an, ctx, f, v)
    grip = max(0.0, reach * 2 - 1) * (1 - release)
    pose = K.finger_curl(an, "Right", -4 + 36 * grip, spread=(1 - grip) * 4)
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRAB < f < DROP:
        pl = ctx["pl"]
        K.clutch(v, pl, f, GRAB, {"Right Arm": an.pb["RightLowerArm"].tail, "Left Arm": an.pb["RightLowerArm"].head})
    return v


def main(blend, export_dir, preview):
    K.run_kill(blend, "Receiver_Rig", LENGTH, KM, DISTANCE, kill, os.path.join(export_dir, "Receiver_Kill_Victim.rbxmx"),
               preview, "Receiver_Kill_Victim", MARKERS)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
