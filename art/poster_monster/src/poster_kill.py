#!/usr/bin/env python3
"""Dewey's kill (the poster monster), "Poster wrap": he steps in, clamps his rolled-poster
claws on the player's shoulders and yanks them up against his chest, face first into the wet
posters, wrapping his long arms round them. His mask bends down over the back of their head.
He squeezes, tighter with each breath, while they struggle less and less, then lets them
slide down his front and crumple at his feet.

Writes Dewey's "Kill" action into the blend, and the player's half on the R6 rig
(export/PosterMonster_Kill_Victim.blend). Both are 100 frames (3.3 s) and start together, with
the player's HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Grab 10, Wrap 22 (their face hits his chest: start slapping posters over the camera),
Covered 66 (the last poster, "WELCOME!"), Drop 72, End 100.

Usage: python3 poster_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
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

HEIGHT_M, HEIGHT_STUDS = 2.707, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.8
LENGTH = 100
GRAB, WRAP, COVERED, DROP, DOWN = 10, 22, 66, 72, 88
MARKERS = {GRAB: "Grab", WRAP: "Wrap", COVERED: "Covered", DROP: "Drop", LENGTH: "End"}
MASK = Vector((0.0, -0.2, 2.5))
CHEST = Vector((0.0, -0.3, 1.8))  # the front of his chest, at rest
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")
SQUEEZES = (34, 46, 58)


def squeeze(f):
    return sum(A.bump(f, s0 - 3, s0, s0 + 8) for s0 in SQUEEZES)


def monster_body(an, f):
    step = ss(0, 9, f)
    hug = ss(GRAB, WRAP, f) * (1 - ss(DROP, DOWN, f))
    sq = squeeze(f)
    pose = {
        "LowerTorso": [("x", 4 + 6 * step - 4 * hug)],
        "Spine": [("x", 4 * step + 4 * hug + 3 * sq)],
        "UpperTorso": [("x", 6 * step + 10 * hug + 5 * sq)],
        "Neck": [("x", 10 * hug)],
        # the mask bends down over the back of their head, and tips as he squeezes
        "Head": [("x", -10 * step + 30 * hug + 6 * sq), ("y", 14 * hug + 4 * sq), ("z", 4 * math.sin(f / 9.0))],
    }
    for p in PEELS:
        pose[f"{p}1"] = [("x", 6 * math.sin(f / 4.0 + len(p)) * (0.4 + step * (1 - hug) + sq))]
    an.fk(pose, {"LowerTorso": (0.0, -0.22 * step + 0.06 * hug, -0.04 * step - 0.02 * sq)})
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.4 * step, 0.1 * math.sin(math.pi * step))) if side == "Left" else Vector((0, -0.05 * step, 0))
        an.leg(side, rest + off, 0.0, 0.16 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    mask = pl.point_to_victim(an.rest_delta("Head") @ MASK)
    if f <= GRAB:
        K.recoil(v, f, 1, 9, mask, (4, 10))
        ctx["grab_head"] = v.head_world().translation.copy()
        return v
    # yanked up against his chest, face first, feet off the floor
    chest = pl.point_to_victim(an.rest_delta("UpperTorso") @ (CHEST + Vector((0, -0.12, 0))))
    into = pl.point_to_victim(an.rest_delta("UpperTorso") @ (CHEST + Vector((0, 0.3, 0))))
    t = K.back_out((f - GRAB) / (WRAP - GRAB), 1.3)
    struggle = window(f, WRAP - 4, WRAP, COVERED - 14, COVERED) * (1 - 0.5 * squeeze(f))
    sway = K.rot("Z", 6 * math.sin(f / 3.4) * struggle) @ K.rot("X", 5 * math.sin(f / 4.4) * struggle)
    head_cf = K.look_cf(ctx["grab_head"].lerp(chest, t), into)
    held = K.Victim()
    held.hang_from_head(head_cf, sway @ K.rot("X", 6))
    if f >= DROP:
        ctx.setdefault("drop_torso", held.torso.copy())
        lying = Matrix.Translation((0.3, -2.5, 0.9)) @ K.rot("Y", 15) @ K.rot("X", 90)
        return K.crumple(v, f, DROP, DOWN, ctx["drop_torso"], lying, mask)
    v.torso, v.T["Head"] = held.torso, held.T["Head"]
    K.kick_legs(v, f, 0.9 * struggle, 2.6)
    K.jolt_head(v, f, (WRAP,) + SQUEEZES, 6)
    # arms pinned by his, pushing at his chest, going slack
    slack = ss(COVERED - 10, DROP, f)
    for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
        push = Vector((0.35 * sx, 0.1 + 0.15 * math.sin(f / 3 + sx) * struggle, -1.0))
        d = (v.torso.to_3x3() @ push).normalized()
        v.point(arm, d.lerp(Vector((0, -1, 0)), slack).normalized())
    return v


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    reach = ss(1, GRAB, f)
    hug = ss(GRAB + 2, WRAP + 4, f)
    release = ss(DROP, DROP + 6, f)
    torso = v.torso if f < DROP else ctx["drop_torso"]
    sq = squeeze(f)
    for side, sx in SIDES:
        rest = T @ an.pb[f"{side}LowerArm"].bone.tail_local
        # his left is their right: the claws on their shoulders, then wrapped round their back
        shoulder = pl.point_to_blender(torso @ Vector((sx * 1.0, 0.9, -0.2)))
        back = pl.point_to_blender(torso @ Vector((-sx * 0.4, 0.2 - 0.1 * sq, 0.75)))
        target = rest.lerp(shoulder, A.ease(reach)).lerp(back, hug)
        target = target.lerp(rest + Vector((sx * 0.1, -0.35, 0.1)), release)
        pole = T.to_3x3() @ Vector((sx * 1.0, -0.2 + 0.4 * hug, -0.3))
        hand_dir = (T.to_3x3() @ Vector((-sx, 0.2, -0.2))).normalized() if hug > 0.5 and release < 0.5 else None
        K.reach(an, side, target, pole, hand_dir, Vector((0, 1, 0)))
    grip = ss(GRAB - 3, GRAB, f) * (1 - release)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, 6 + 34 * grip + 10 * sq, spread=6 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """Dewey (poster monster) kill, the player's half: InternalArmature carries the action
PosterMonster_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted
so the keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab, Wrap
(start slapping posters over the camera), Covered, Drop, End.
The 'Monster (reference)' collection holds Dewey playing his half, at your in-game size, lined
up where the game should put him: 3.8 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "PosterMonster_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "PosterMonster_Kill_Victim",
                     MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "PosterMonster_Kill_Victim.blend"), ctx["parts"],
                     "PosterMonster_Kill_Victim", MARKERS, (blend, "PosterMonster_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
