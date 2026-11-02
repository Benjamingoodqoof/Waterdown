#!/usr/bin/env python3
"""The Receiver's kill: his phone head snaps round and he steps in, seizes the player by the
neck with his left hand (the handset pressed across their throat) and lifts them onto their
toes. He holds them there a moment, head cocked, drawing his claw back, then drives it through
their torso. They look down at it. He pulls it out and drops them, and they crumple at his feet.

Writes the Receiver's "Kill" action into the blend, and the player's half on the R6 rig
(export/Receiver_Kill_Victim.blend). Both are 100 frames (3.3 s) and start together, with the
player's HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Grab 12, Stab 44 (blood on the player's screen), Drop 74, End 100.

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
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.2825, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.8
LENGTH = 100
GRAB, LIFTED, WIND, STAB, OUT, DROP, DOWN = 12, 24, 30, 44, 68, 74, 86
MARKERS = {GRAB: "Grab", STAB: "Stab", DROP: "Drop", LENGTH: "End"}
SOCKET = Vector((0.0, -0.43, 2.11))
SIDES = (("Left", 1.0), ("Right", -1.0))
NECK = Vector((0.0, 1.05, -0.35))  # the front of their neck, in their torso's frame
CHEST = Vector((0.0, 0.2, -0.5))  # the middle of their chest, at the front
HOLD = Vector((0.1, -0.78, 1.55))  # where he holds their neck, at rest (in front of his chest, to his left)


def monster_body(an, f):
    snap = A.bump(f, 0, 3, 10)
    step = ss(0, 10, f)
    wind = A.bump(f, WIND - 4, WIND + 6, STAB)
    stab = A.bump(f, STAB - 3, STAB, STAB + 14)
    drop = ss(DROP, DOWN, f)
    pose = {
        "LowerTorso": [("x", 6 + 6 * step - 4 * wind + 8 * stab), ("z", 6 * wind - 10 * stab)],
        "UpperTorso": [("x", 8 + 6 * step - 6 * wind + 12 * stab + 6 * drop), ("z", 14 * wind - 18 * stab)],
        # the phone head cocked, watching their face, then watching them fall
        "Head": [("x", -14 * snap - 4 + 10 * stab + 16 * drop), ("y", -18 * snap + 14 * ss(GRAB, LIFTED, f) * (1 - drop)),
                 ("z", 8 * snap)],
        "DialSpin": [("ly", -40 * stab)],
    }
    an.fk(pose, {"LowerTorso": (0.0, -0.22 * step, -0.04 * step - 0.03 * stab)})
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.38 * step, 0.12 * math.sin(math.pi * step))) if side == "Right" else Vector((0, -0.05 * step, 0))
        an.leg(side, rest + off, 0.0, 0.14 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    socket = pl.point_to_victim(an.rest_delta("Head") @ SOCKET)
    if f <= GRAB:
        K.recoil(v, f, 2, 10, socket, (5, 11))
        ctx["grab_torso"] = v.torso.copy()
        return v
    # held up by the neck, onto their toes
    lift = ss(GRAB, LIFTED, f)
    hold = pl.point_to_victim(an.rest_delta("UpperTorso") @ HOLD)
    start_neck = ctx["grab_torso"] @ NECK
    struggle = window(f, GRAB, GRAB + 4, STAB, STAB + 4)
    hit = A.bump(f, STAB - 2, STAB, STAB + 12)
    fold = ss(STAB, STAB + 8, f)
    R = K.rot("X", -6 * lift - 14 * fold - 8 * hit) @ K.rot("Z", 4 * math.sin(f / 4.0) * struggle)
    neck = start_neck.lerp(hold, lift)
    torso = Matrix.Translation(neck) @ R @ Matrix.Translation(-NECK)
    if f >= DROP:
        ctx.setdefault("drop_torso", torso.copy())
        lying = Matrix.Translation((-0.3, -2.5, 0.9)) @ K.rot("Y", -15) @ K.rot("X", 90)
        return K.crumple(v, f, DROP, DOWN, ctx["drop_torso"], lying, socket, -1.0)
    v.torso = torso
    K.kick_legs(v, f, 0.5 * struggle + 0.6 * A.bump(f, STAB, STAB + 3, STAB + 16), 3.0)
    # they watch his head, then look down at the claw in their chest, then their head sags
    down = window(f, STAB + 3, STAB + 10, OUT - 4, OUT + 4)
    entry = torso @ (CHEST + Vector((0, -0.3, -0.4)))  # where the claw goes in
    v.look(socket.lerp(entry, down), limit=85)
    K.jolt_head(v, f, (GRAB, STAB), 14)
    sag = ss(OUT - 2, DROP, f)
    if sag:
        v.T["Head"] = v.T["Head"] @ K.rot("X", 22 * sag)
    return v


def arms(an, ctx, f, v):
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    tb = pl.to_blender(v.torso)
    tx = tb.to_3x3().col[0].normalized()
    tu = tb.to_3x3().col[1].normalized()
    tf = -tb.to_3x3().col[2].normalized()  # the way they face (at him)
    drop_w = ss(DROP, DROP + 5, f)
    # left hand: round their throat, the handset across it
    lrest = T @ an.pb["LeftLowerArm"].bone.tail_local
    neck = pl.point_to_blender(v.torso @ NECK) if f < DROP else pl.point_to_blender(ctx["drop_torso"] @ NECK)
    grab = ss(2, GRAB, f)
    lt = lrest.lerp(neck + tf * 0.07, A.ease(grab))
    if drop_w:
        lt = lt.lerp(lrest + Vector((0.05, -0.25, 0.1)), drop_w)
    K.reach(an, "Left", lt, T.to_3x3() @ Vector((0.8, 0.3, -0.5)),
            (tu * 0.6 - tx * 0.8).normalized() if grab > 0.6 and drop_w < 0.5 else None, -tf)
    # right claw: drawn back, driven through their chest, pulled out
    rrest = T @ an.pb["RightLowerArm"].bone.tail_local
    back = T @ Vector((-0.42, 0.25, 1.35))
    chest = pl.point_to_blender(v.torso @ CHEST) if f < DROP else pl.point_to_blender(ctx["drop_torso"] @ CHEST)
    through = chest - tf * 0.32  # out of their back
    wind = ss(WIND - 4, WIND + 6, f)
    drive = ss(STAB - 4, STAB, f)
    pull = ss(OUT, OUT + 6, f)
    rt = rrest.lerp(back, wind)
    rt = rt.lerp(through, drive * drive)
    rt = rt.lerp(chest + tf * 0.25, pull).lerp(rrest, ss(OUT + 6, DOWN, f))
    spear = (-tf).normalized()  # claw pointing through them
    K.reach(an, "Right", rt, T.to_3x3() @ Vector((-0.8, 0.5, -0.3)), spear if drive > 0.3 and pull < 0.7 else None, tu)
    return grab, drive


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    grab, drive = arms(an, ctx, f, v)
    pose = K.finger_curl(an, "Right", -8 + 10 * drive, spread=2 * (1 - drive))  # claw straight, like a blade
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRAB < f < DROP:  # their hands on his wrist at their throat, then grabbing at the claw
        pl = ctx["pl"]
        tgt = {"Right Arm": an.pb["LeftLowerArm"].tail, "Left Arm": an.pb["LeftLowerArm"].tail}
        if f > STAB:
            tgt["Left Arm"] = an.pb["RightLowerArm"].tail
        K.clutch(v, pl, f, GRAB, tgt)
        weak = ss(OUT - 6, DROP, f)
        if weak:
            for arm in ("Right Arm", "Left Arm"):
                cur = (v.parts()[arm].to_3x3() @ Vector((0, -1, 0))).normalized()
                v.point(arm, cur.lerp(Vector((0, -1, 0)), weak).normalized())
    return v


NOTE = """Receiver kill, the player's half: InternalArmature carries the action
Receiver_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab, Stab (blood on
the player's screen), Drop, End.
The 'Monster (reference)' collection holds the Receiver playing his half, at your in-game size,
lined up where the game should put him: 3.8 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "Receiver_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Receiver_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "Receiver_Kill_Victim.blend"), ctx["parts"], "Receiver_Kill_Victim",
                     MARKERS, (blend, "Receiver_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
