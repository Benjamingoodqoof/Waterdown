#!/usr/bin/env python3
"""The Receiver's kill, "Hang up": his phone head snaps round, he lunges and seizes the player
by the throat with his claw, lifts them and slams them down on their back. He crouches over
them, pinning them, the phone head hanging over their face with its dirty water sloshing, and
holds the handset to their ear while the dial in his chest dials, digit after digit. Then he
raises the handset high and slams it down on their face, like hanging up a phone.

Writes the Receiver's "Kill" action into the blend, and the player's half on the R6 rig
(export/Receiver_Kill_Victim.blend). Both are 4 s and start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Grab 12, Slammed 26 (they hit the floor), Handset 44 (play their voice line,
crackly), DialStart 48 (QTE starts), DialEnd 86 (QTE ends), HangUp 98 (the handset hits the
camera: dial tone, black), End 120.

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
GRAB, LIFT, SLAM, OVER, HANDSET, DIAL, DIAL_END, RAISE, HANG = 12, 18, 26, 38, 44, 48, 86, 92, 98
MARKERS = {0: "Notice", GRAB: "Grab", SLAM: "Slammed", HANDSET: "Handset", DIAL: "DialStart", DIAL_END: "DialEnd",
           HANG: "HangUp", LENGTH: "End"}
SOCKET = Vector((0.0, -0.43, 2.11))
SIDES = (("Left", 1.0), ("Right", -1.0))
HITS = (GRAB, SLAM, HANG)
LYING = Matrix.Translation((0.0, -2.5, -2.2)) @ K.rot("X", 90)  # on their back, head away from him


def dial(t):
    """His chest dial dialling fast: each digit pulled round in 5 frames and whirring back at
    20 degrees a frame."""
    for pull in (270, 120, 300, 90, 210, 180):
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
    snap = A.bump(f, 0, 3, 10)
    lunge = ss(4, GRAB, f) * (1 - ss(SLAM, OVER, f))
    lift = A.bump(f, GRAB, LIFT, SLAM)
    slam = ss(LIFT, SLAM, f)
    over = ss(SLAM, OVER, f)
    raise_ = A.bump(f, DIAL_END, RAISE, HANG)
    hang = A.bump(f, RAISE, HANG, HANG + 10)
    pose = {
        "LowerTorso": [("x", 6 + 20 * lunge - 6 * lift + 26 * slam * (1 - over) + 38 * over - 8 * raise_ + 10 * hang)],
        "UpperTorso": [("x", 6 + 16 * lunge - 10 * lift + 24 * slam * (1 - over) + 40 * over - 14 * raise_ + 16 * hang),
                       ("z", -10 * lift + 14 * slam * (1 - over) - 8 * raise_), ("y", 6 * over * math.sin(f / 11.0))],
        # the phone head hangs over their face; it rears back as the handset goes up
        "Head": [("x", -16 * snap - 10 * lunge + 34 * over - 18 * raise_ + 14 * hang + 4 * math.sin(f / 6.0) * over),
                 ("y", -18 * snap + 10 * window(f, DIAL, DIAL + 6, DIAL_END - 6, DIAL_END) * math.sin(f / 12.0)),
                 ("z", 8 * snap)],
        "DialSpin": [("ly", dial(f - DIAL) if f >= DIAL else 0.0)],
    }
    an.fk(pose, {"LowerTorso": (0.0, -0.3 * lunge - 0.3 * over, -0.1 * lunge + 0.08 * lift - 0.42 * over)})
    step = ss(4, 10, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        if side == "Right":
            off = Vector((0, -0.45 * step - 0.15 * over, 0.14 * math.sin(math.pi * step)))
        else:
            off = Vector((0.06, -0.08 * step - 0.4 * over, 0.12 * math.sin(math.pi * over)))
        an.leg(side, rest + off, 0.0, 0.16 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    socket = pl.point_to_victim(an.rest_delta("Head") @ SOCKET)
    if f <= GRAB:
        K.recoil(v, f, 1, 8, socket, (4, 10))
        ctx["grab_torso"] = v.torso.copy()
        K.jolt_head(v, f, HITS, 14)
        return v
    a = ctx["grab_torso"]
    up = Matrix.Translation(a.translation + Vector((0, 0.9, -0.4))) @ K.rot("X", -10)
    if f <= LIFT:
        v.torso = K.blend_cf(a, up, K.back_out((f - GRAB) / (LIFT - GRAB), 1.5))
    elif f <= SLAM:
        t = (f - LIFT) / (SLAM - LIFT)
        v.torso = K.blend_cf(up, LYING, t * t)
    else:
        v.torso = LYING.copy()
        v.torso.translation.y += 0.3 * math.sin(math.pi * min(1.0, (f - SLAM) / 5))
    kick = window(f, GRAB, GRAB + 2, DIAL_END, RAISE) * (0.5 if f > SLAM else 1.0)
    K.kick_legs(v, f, kick)
    if f > SLAM:  # flat on their back, legs kicking, then still
        for leg, sx in (("Right Leg", 1), ("Left Leg", -1)):
            v.rotate(leg, K.rot("X", -15 + 20 * math.sin(f / 2.5 + sx) * kick) @ K.rot("Z", 8 * sx))
    v.look(socket, limit=55 if f > SLAM else 70)
    K.jolt_head(v, f, HITS, 22 if f >= HANG else 14)
    return v


def claw_and_handset(an, ctx, f, v):
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    tb = pl.to_blender(v.torso)
    tu = tb.to_3x3().col[1].normalized()
    tf = -tb.to_3x3().col[2].normalized()  # the way their chest faces
    reach = ss(3, GRAB, f)
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    throat = pl.point_to_blender(v.torso @ Vector((0.0, 0.85, -0.6)))
    target = rest.lerp(throat, K.back_out(reach, 1.3))
    K.reach(an, "Right", target, T.to_3x3() @ Vector((-0.8, 0.4, -0.4)),
            (tu * 0.6 - tf * 0.2).normalized() if reach > 0.5 else None, -tf)
    # the handset: at his side, to their ear as they lie there, raised high, slammed down on their face
    head_b = pl.to_blender(v.head_world())
    hx = head_b.to_3x3().col[0].normalized()
    hu = head_b.to_3x3().col[1].normalized()
    hf = -head_b.to_3x3().col[2].normalized()
    ear = head_b.translation + hx * (0.62 * KM + 0.06) - hu * 0.04
    y = (hf * 0.8 - hu * 0.6).normalized()
    z = (hx - y * hx.dot(y)).normalized()
    M_ear = Matrix.Translation(ear) @ Matrix((y.cross(z), y, z)).transposed().to_4x4()
    face = head_b.translation + hf * (0.5 * KM + 0.05)
    yf, zf = hu.copy(), hf.copy()  # lying flat across their face, earpiece to their forehead
    M_face = Matrix.Translation(face) @ Matrix((yf.cross(zf), yf, zf)).transposed().to_4x4()
    M_high = Matrix.Translation(face + Vector((0, 0.15, 0.85))) @ Matrix((yf.cross(zf), yf, zf)).transposed().to_4x4()

    def hand_for(Mset):
        return Mset @ Matrix.Translation(-R.HANDSET_C) @ an.pb["LeftHand"].bone.matrix_local

    import bpy as _b
    _b.context.view_layer.update()
    an.fk({"LeftUpperArm": [("x", -0.1)], "LeftLowerArm": [("x", -1.9)]})
    _b.context.view_layer.update()
    M0 = an.pb["LeftHand"].matrix.copy()
    to_ear = ss(OVER - 4, HANDSET, f)
    up = ss(DIAL_END, RAISE, f)
    down = ss(RAISE + 2, HANG, f)
    M = K.blend_cf(M0, hand_for(M_ear), to_ear)
    if up:
        M = K.blend_cf(M, hand_for(M_high), K.back_out(up, 1.2))
    if down:
        M = K.blend_cf(M, hand_for(M_face), down * down)
    pole = Vector((0.5, 1.0, -0.2)).lerp(Vector((0.8, 0.3, 0.2)), max(to_ear, up))
    R.place_left_hand(an, M, pole)
    return reach


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    claw_and_handset(an, ctx, f, v)
    grip = ss(GRAB - 3, GRAB, f)
    pose = K.finger_curl(an, "Right", -6 + 44 * grip, spread=(1 - grip) * 6)
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRAB < f <= SLAM:  # their hands at the claw on their throat
        pl = ctx["pl"]
        K.clutch(v, pl, f, GRAB, {"Right Arm": an.pb["RightLowerArm"].tail, "Left Arm": an.pb["RightHand"].tail})
    elif f > SLAM:  # flat on the floor, arms thrown out to the sides, pushing at him
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            d = Vector((0.9 * sx, 0.25 + 0.15 * math.sin(f / 3.0 + sx), -0.45))
            v.point(arm, (v.torso.to_3x3() @ d).normalized())
        if f > RAISE:  # flung up to shield their face from the handset
            shield = ss(RAISE, HANG - 2, f)
            for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
                d = (v.torso.to_3x3() @ Vector((0.4 * sx, 0.3, -1.0))).normalized()
                cur = (v.parts()[arm].to_3x3() @ Vector((0, -1, 0))).normalized()
                v.point(arm, cur.lerp(d, shield).normalized())
    return v


NOTE = """Receiver kill, the player's half: InternalArmature carries the action
Receiver_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. The timeline markers are the beats:
Grab, Slammed, Handset, DialStart (QTE starts), DialEnd (QTE ends), HangUp, End.
The 'Monster (reference)' collection holds the Receiver playing his half, at your in-game size,
lined up where the game should put him: 4.5 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "Receiver_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Receiver_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "Receiver_Kill_Victim.blend"), ctx["parts"], "Receiver_Kill_Victim",
                     MARKERS, (blend, "Receiver_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
