#!/usr/bin/env python3
"""Dewey's kill (the poster monster), "Close-up" into "Poster wrap": he lunges and clamps his
rolled-poster claws on the player's shoulders, then bends all the way down until his cracked
mask is a hand's width from their face and the empty eye holes stare into the lens, his head
tipping slowly over. Then he straightens and pulls them into his chest, wrapping his arms
round them, so the wet posters cover the camera.

Writes Dewey's "Kill" action into the blend, and the player's half as an R6 KeyframeSequence
(export/PosterMonster_Kill_Victim.rbxmx). Both are 4 s and start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers (KeyframeReached on the player's track): Notice 0, Grab 20, LeanIn 34 (the mask fills
the view; QTE starts), Wrap 62 (QTE ends; start slapping posters over the camera), Covered 100
(the last poster, "WELCOME!"), End 120.

Usage: python3 poster_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
"""
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Vector

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
GRAB, LEANED, WRAP, HUGGED = 20, 40, 62, 80
MARKERS = {0: "Notice", GRAB: "Grab", 34: "LeanIn", WRAP: "Wrap", 100: "Covered", LENGTH: "End"}
MASK = Vector((0.0, -0.2, 2.5))  # between the eye holes, at rest
CHEST = Vector((0.0, -0.24, 1.86))  # the front of his chest, at rest
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")


def monster_body(an, f):
    lunge = ss(6, 20, f)
    bow = ss(GRAB, LEANED, f) * (1 - ss(WRAP, HUGGED, f))
    hug = ss(WRAP, HUGGED, f)
    tip = ss(LEANED, WRAP, f)  # the slow tip of his head while he stares
    rock = math.sin(2 * math.pi * (f - HUGGED) / 40) * ss(HUGGED, HUGGED + 6, f)
    pose = {
        "LowerTorso": [("x", 8 * lunge + 26 * bow + 4 * hug)],
        "Spine": [("x", 6 * lunge + 18 * bow + 4 * hug)],
        "UpperTorso": [("x", 8 * lunge + 24 * bow - 4 * hug + 2 * rock)],
        # the long neck cranes forward and up so the mask stays on their face as he bends
        "Neck": [("x", 10 * lunge + 6 * bow + 10 * hug)],
        "Head": [("x", -8 * lunge - 66 * bow + 10 * hug), ("y", 26 * tip * (1 - hug)), ("z", 4 * math.sin(f / 9.0) * (1 - hug))],
    }
    for p in PEELS:  # the loose sheets flap when he moves
        pose[f"{p}1"] = [("x", 8 * math.sin(f / 4.0 + len(p)) * (lunge * (1 - bow) + hug))]
    an.fk(pose, {"LowerTorso": (0.0, -0.34 * lunge + 0.12 * hug, -0.05 * lunge - 0.36 * bow - 0.1 * hug)})
    step = ss(6, 18, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0.08 * sx * bow, -0.48 * step, 0.1 * math.sin(math.pi * step))) if side == "Left" else \
            Vector((-0.1 * bow, -0.12 * step, 0))
        an.leg(side, rest + off, 0.0, 0.18 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    mask = pl.point_to_victim(an.rest_delta("Head") @ MASK)
    if f <= GRAB:
        K.recoil(v, f, 3, 16, mask, (8, 18))
        ctx["grab_head"] = v.head_world().copy()
        return v
    D = an.rest_delta("Head")
    close = pl.point_to_victim(D @ (MASK + Vector((0, -0.24, -0.02))))  # a hand's width from the mask
    chest = pl.point_to_victim(an.rest_delta("UpperTorso") @ (CHEST + Vector((0, -0.16, 0.0))))
    lean = ss(GRAB, LEANED, f)
    hug = ss(WRAP, HUGGED, f)
    pos = ctx["grab_head"].translation.lerp(close, lean).lerp(chest, hug)
    pos += Vector((0, -0.6, 1.2)) * math.sin(math.pi * hug)  # swung out and down, clear of his mask, then in
    look = mask.lerp(pl.point_to_victim(an.rest_delta("UpperTorso") @ CHEST), hug)
    kick = window(f, GRAB, GRAB + 6, 88, 104)
    sw = K.rot("X", 4 * math.sin(f / 4.2) * kick) @ K.rot("Z", 3 * math.sin(f / 3.4) * kick)
    head_cf = K.look_cf(pos, look)
    v.hang_from_head(head_cf, sw)
    K.kick_legs(v, f, kick * (0.4 + 0.6 * hug))
    return v


def claws(an, ctx, f, v):
    """His claws: reaching, clamped on the player's shoulders, then wrapped round their back."""
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    tb = pl.to_blender(v.torso)
    tx, tu = tb.to_3x3().col[0].normalized(), tb.to_3x3().col[1].normalized()
    tf = -tb.to_3x3().col[2].normalized()  # toward him
    reach = ss(6, GRAB, f)
    hug = ss(WRAP, HUGGED, f)
    for side, sx in SIDES:
        rest = T @ an.pb[f"{side}LowerArm"].bone.tail_local
        shoulder = pl.point_to_blender(v.torso @ Vector((sx * 0.75, 1.0, -0.1)))  # his left is their right
        shoulder = shoulder + tu * 0.1 + tf * 0.04
        back = pl.point_to_blender(v.torso @ Vector((sx * 1.2, 0.2, 0.9)))
        target = rest.lerp(shoulder, A.ease(reach))
        target = target.lerp(back, hug)
        target += (T.to_3x3() @ Vector((sx * 0.4, -1, 0.3))) * 0.2 * math.sin(math.pi * reach)
        pole = T.to_3x3() @ Vector((sx * 1.0, 0.1 + 0.3 * hug, -0.5 + 0.4 * hug))
        if reach < 0.5:
            hand_dir, palm = None, None
        elif hug < 0.5:
            hand_dir, palm = (tf * 0.6 - tu * 0.8).normalized(), -tu  # claws hooked down over the shoulders
        else:
            hand_dir, palm = (-tx * sx * 0.7 + tf * 0.3).normalized(), tf  # round their back
        K.reach(an, side, target, pole, hand_dir, palm)
    return reach, hug


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    reach, hug = claws(an, ctx, f, v)
    grip = max(0.0, reach * 2 - 1)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, 6 + 30 * grip + 10 * hug, spread=4 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRAB < f:
        pl = ctx["pl"]
        clutch_w = 1 - ss(WRAP + 6, HUGGED + 6, f)
        if clutch_w > 0.02:
            K.clutch(v, pl, f, GRAB, {"Right Arm": an.pb["LeftLowerArm"].tail, "Left Arm": an.pb["RightLowerArm"].tail})
        if clutch_w < 1:  # pinned in his arms, hands pressed to his chest
            for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
                v.point(arm, Vector((0.2 * sx, -0.4, -1)).normalized().lerp(Vector((0, -1, 0)), clutch_w).normalized())
    return v


def main(blend, export_dir, preview):
    K.run_kill(blend, "PosterMonster_Rig", LENGTH, KM, DISTANCE, kill,
               os.path.join(export_dir, "PosterMonster_Kill_Victim.rbxmx"), preview, "PosterMonster_Kill_Victim", MARKERS)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
