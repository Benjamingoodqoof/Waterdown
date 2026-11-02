#!/usr/bin/env python3
"""Dewey's kill (the poster monster), "Snatch": he drops into a crouch, darts in low and
snatches the player by the ankle, whipping them off their feet and up into the air. He dangles
them upside down in front of his mask, turning them slowly, and tips his own head right over
to match theirs, grinning. Then he swings them up and slams them into the floor, and crouches
over them, claws pinning them, his mask sinking down over their face while the posters wrap.

Writes Dewey's "Kill" action into the blend, and the player's half on the R6 rig
(export/PosterMonster_Kill_Victim.blend). Both are 4 s and start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Snatch 12, Dangle 34 (QTE starts; the slowed jingle), Slam 76 (QTE ends), Wrap 84
(start slapping posters over the camera), Covered 104 (the last poster, "WELCOME!"), End 120.

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
DISTANCE = 4.6
LENGTH = 120
SNATCH, UP, DANGLE, WIND, SLAM, PIN = 12, 30, 34, 64, 76, 92
MARKERS = {0: "Notice", SNATCH: "Snatch", DANGLE: "Dangle", SLAM: "Slam", 84: "Wrap", 104: "Covered", LENGTH: "End"}
MASK = Vector((0.0, -0.2, 2.5))
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")
ANKLE = Vector((0, -0.7, 0))  # where he holds the left leg, in its own frame (just above the foot)
HITS = (SNATCH, SLAM)


def monster_body(an, f):
    crouch = ss(0, 6, f) * (1 - ss(SNATCH, UP, f))
    dart = ss(5, SNATCH, f) * (1 - ss(SNATCH + 4, UP, f))
    stand = ss(SNATCH + 2, UP, f) * (1 - ss(WIND, WIND + 6, f))
    bow = ss(UP, DANGLE + 6, f) * (1 - ss(WIND, WIND + 4, f))
    tip = ss(DANGLE, DANGLE + 20, f) * (1 - ss(WIND - 4, WIND + 2, f))
    wind = A.bump(f, WIND, WIND + 6, SLAM)
    slam = A.bump(f, WIND + 6, SLAM, SLAM + 10)
    pin = ss(SLAM, PIN, f)
    sink = ss(PIN, LENGTH, f)
    pose = {
        "LowerTorso": [("x", 14 * crouch + 22 * dart + 32 * bow - 18 * wind + 34 * slam * (1 - pin) + 40 * pin)],
        "Spine": [("x", 8 * crouch + 10 * dart + 18 * bow - 10 * wind + 16 * slam * (1 - pin) + 22 * pin), ("z", -12 * wind)],
        "UpperTorso": [("x", 6 * crouch + 8 * dart + 22 * bow - 12 * wind + 18 * slam * (1 - pin) + 30 * pin + 14 * sink),
                       ("z", 10 * dart - 16 * wind + 12 * slam * (1 - pin))],
        "Neck": [("x", 4 * bow + 8 * pin)],
        # the mask: on the player all along, tipped right over to match them as they hang
        "Head": [("x", -14 * crouch - 18 * dart - 66 * bow + 10 * wind - 50 * pin + 26 * sink),
                 ("y", 75 * tip + 22 * pin * math.sin(f / 9.0)), ("z", 6 * math.sin(f / 7.0) * (1 - tip))],
    }
    for p in PEELS:  # the loose sheets flap with every move
        pose[f"{p}1"] = [("x", 14 * math.sin(f / 3.0 + len(p)) * (dart + wind + slam + 0.2))]
    an.fk(pose, {"LowerTorso": (0.0, -0.3 * dart - 0.15 * stand - 0.8 * pin,
                                -0.32 * crouch - 0.2 * dart - 0.45 * bow - 0.5 * pin - 0.08 * sink)})
    step = ss(5, 11, f)
    over = ss(SLAM, PIN - 4, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        if side == "Left":
            off = Vector((0.1 * sx, -0.45 * step - 0.65 * over, 0.1 * math.sin(math.pi * step) + 0.14 * math.sin(math.pi * over)))
        else:
            off = Vector((-0.05, -0.12 * step - 0.85 * ss(SLAM + 4, PIN, f), 0.14 * math.sin(math.pi * ss(SLAM + 4, PIN, f))))
        an.leg(side, rest + off, 0.0, 0.22 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    mask_v = pl.point_to_victim(an.rest_delta("Head") @ MASK)
    if f <= SNATCH:
        K.recoil(v, f, 3, 10, mask_v, (6, 12))
        if f == SNATCH:
            ctx["snatch_torso"] = v.torso.copy()
        return v
    # upside down: rolled 180 degrees about their facing, spinning slowly while they hang
    spin = 40 * math.sin(math.pi * (f - DANGLE) / 40) * window(f, DANGLE, DANGLE + 6, WIND - 6, WIND)
    flip = K.rot("Y", spin) @ K.rot("Z", 180)
    if f <= WIND:
        # whipped off their feet (falling back as the leg goes) and up, to hang in front of his mask
        front = pl.point_to_victim(an.rest_delta("Head") @ (MASK + Vector((0, -0.44, -0.08))))
        hang = K.Victim()
        hang.T["Left Leg"] = Matrix.Identity(4)
        K.hang_from_limb(hang, "Left Leg", ANKLE, Vector((0, 0, 0)), flip)
        head_off = hang.head_world().translation - hang.torso.translation
        hang.torso = Matrix.Translation(front - head_off - hang.torso.translation) @ hang.torso
        t = K.back_out((f - SNATCH) / (UP - SNATCH), 1.4)
        mid = K.rot("X", 95)  # flat on their back, mid-whip
        a = ctx["snatch_torso"]
        b = Matrix.Translation(a.translation + Vector((0, 0.2, 0.3))) @ mid
        v.torso = K.blend_cf(a, b, min(1.0, t * 2)) if t < 0.5 else K.blend_cf(b, hang.torso, (t - 0.5) * 2)
        swing = math.sin((f - UP) / 5.0) * 6 * ss(UP, DANGLE, f) * (1 - ss(DANGLE + 10, WIND, f))
        v.torso = Matrix.Translation(v.torso.translation) @ K.rot("X", swing) @ v.torso.to_3x3().to_4x4()
        ctx["dangle_torso"] = v.torso.copy()
        # arms hanging down past their head, flailing; the free leg bent
        dangle = ss(UP - 6, UP, f)
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            flail = Vector((0.8 * sx, 0.3, 0.3 + 0.3 * math.sin(f / 2.2 + sx)))  # grabbing at the air as they go
            # hanging out to the sides and back, clear of their face (and the camera)
            hang_d = Vector((0.75 * sx, -1, 0.55 + 0.15 * math.sin(f / 3 + sx)))
            v.point(arm, flail.lerp(hang_d, dangle).normalized())
        v.rotate("Right Leg", K.rot("X", -30 - 15 * math.sin(f / 2.5)) @ K.rot("Z", 15))
        v.look(mask_v, limit=70)
        K.jolt_head(v, f, HITS, 14)
        return v
    # the slam: swung up and over, then down flat on their back
    lying = Matrix.Translation((0.2, -2.45, 0.6)) @ K.rot("Y", -10) @ K.rot("X", 90)
    raised = Matrix.Translation(ctx["dangle_torso"].translation + Vector((0, 1.2, 1.2))) @ K.rot("X", 140) @ K.rot("Z", 180)
    t = (f - WIND) / (SLAM - WIND)
    if t < 0.45:
        v.torso = K.blend_cf(ctx["dangle_torso"], raised, K.smoothstep(0, 1, t / 0.45))
    else:
        tt = min(1.0, (t - 0.45) / 0.55)
        v.torso = K.blend_cf(raised, lying, tt * tt)
    if f > SLAM:
        v.torso = lying.copy()
        v.torso.translation.y += 0.35 * math.sin(math.pi * min(1.0, (f - SLAM) / 6))
    limp = ss(SLAM, SLAM + 6, f)
    v.rotate("Right Arm", K.rot("Z", 80 * limp) @ K.rot("X", -10 * limp))
    v.rotate("Left Arm", K.rot("Z", -70 * limp) @ K.rot("X", 20 * limp))
    v.rotate("Right Leg", K.rot("X", -30 * limp))
    v.rotate("Left Leg", K.rot("X", -10 * limp) @ K.rot("Z", -12 * limp))
    v.look(mask_v, limit=60)
    K.jolt_head(v, f, HITS, 20)
    return v


def claws(an, ctx, f, v):
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    pin = ss(SLAM + 2, PIN, f)
    # the right claw: sweeps for the ankle, holds it, lets go at the slam
    leg_b = pl.to_blender(K.rest_limb(v.torso, "Left Leg", v.T["Left Leg"]))
    ankle = leg_b @ ANKLE
    reach = ss(4, SNATCH, f)
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    hold = 1.0 - ss(SLAM, SLAM + 3, f)
    chest = pl.point_to_blender(v.torso @ Vector((0, 0.4, -0.4)))
    targets = {"Right": rest.lerp(ankle, A.ease(reach)) if f <= SNATCH else ankle.lerp(chest + Vector((-0.12, 0, 0.05)), pin)}
    # the left claw: out for balance, then pinning their chest
    lrest = T @ an.pb["LeftLowerArm"].bone.tail_local
    targets["Left"] = lrest.lerp(chest + Vector((0.14, 0, 0.05)), pin) + Vector((0.1, -0.1, 0.15)) * window(f, SNATCH, UP, WIND, SLAM)
    for side, sx in SIDES:
        pole = T.to_3x3() @ Vector((sx * 0.9, 0.4, -0.3))
        down = Vector((0, 0, -1))
        K.reach(an, side, targets[side], pole, down if (side == "Right" and SNATCH <= f < SLAM) or pin > 0.5 else None,
                Vector((0, 1, 0)))
    return reach, hold, pin


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    reach, hold, pin = claws(an, ctx, f, v)
    pose = {}
    grip = ss(SNATCH - 3, SNATCH, f) * hold
    pose.update(K.finger_curl(an, "Right", 6 + 40 * max(grip, pin), spread=6 * (1 - grip)))
    pose.update(K.finger_curl(an, "Left", 6 + 30 * pin, spread=10 * (1 - pin)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """Dewey (poster monster) kill, the player's half: InternalArmature carries the action
PosterMonster_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted
so the keys drive it; export it with your R6 exporter as usual. The timeline markers are the
beats: Snatch, Dangle (QTE starts), Slam (QTE ends), Wrap, Covered, End.
The 'Monster (reference)' collection holds Dewey playing his half, at your in-game size, lined
up where the game should put him: 4.6 studs in front of the player, facing them.
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
