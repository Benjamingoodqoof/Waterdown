#!/usr/bin/env python3
"""The Stand-In's kill, "Broadcast": he grips the player's head the way he grips his own
monitor, lifts them off their feet and holds their face up to his screen (the game shows their
face on it, live, then NO SIGNAL), then drops them.

Writes the Stand-In's "Kill" action into the blend, and the player's half as an R6
KeyframeSequence (export/StandIn_Kill_Victim.rbxmx). Both are 4 s and start together, with the
player's HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers (KeyframeReached on the player's track): Notice 0, Grip 26 (QTE starts), Broadcast 58
(his screen shows the player's face), NoSignal 86 (screen and camcorder cut to NO SIGNAL; QTE
ends), Drop 98, End 120.

Usage: python3 standin_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
import kill_core as K  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0  # as tall in the game as the user scaled him
KM = HEIGHT_M / HEIGHT_STUDS  # meters per in-game stud
DISTANCE = 4.2  # studs between his HumanoidRootPart and the player's at the start
LENGTH = 120
MARKERS = {0: "Notice", 26: "Grip", 58: "Broadcast", 86: "NoSignal", 98: "Drop", 120: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))  # the middle of his screen, at rest
SIDES = (("Left", 1.0), ("Right", -1.0))
GRAB, LIFTED, DROP, LAND = 26, 52, 98, 110


def monster_body(an, f):
    """His body and legs: still and watching, a long stride in with a deep lean to grab, then
    straightening up with the player held to his screen."""
    lunge = ss(10, 24, f)
    straighten = ss(GRAB + 2, LIFTED, f)
    drop = ss(DROP, DROP + 10, f)
    lean = 30 * lunge * (1 - straighten) + 4 * straighten
    tilt = 12 * (1 - lunge) + 9 * window(f, 56, 66, 78, 88) * math.sin(math.pi * (f - 56) / 32)
    jolt = A.bump(f, 85, 88, 96)
    pose = {
        "LowerTorso": [("x", 4 + 0.6 * lean)],
        "UpperTorso": [("x", 6 + lean)],
        # the monitor tipped at the player, looking them over; it jolts when the signal cuts
        "Head": [("x", -6 * (1 - lunge) + (14 + 8 * jolt) * straighten + 18 * drop), ("y", tilt),
                 ("z", 5 * math.sin(2 * math.pi * f / 70) * straighten * (1 - drop))],
    }
    pose.update({f"Cable{i}": [("x", 6 * lunge * (1 - straighten) + 2 * math.sin(f / 7 + i))] for i in (1, 2, 3)})
    an.fk(pose, {"LowerTorso": (0.0, -0.38 * lunge + 0.12 * straighten, -0.07 * lunge + 0.04 * straighten)})
    step = ss(10, 22, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        if side == "Right":  # the long step in
            target = rest + Vector((0, -0.55 * step, 0.12 * math.sin(math.pi * step)))
        else:
            target = rest + Vector((0, -0.1 * step, 0))
        an.leg(side, target, 0.0, 0.06 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    screen = an.rest_delta("Head") @ SCREEN
    screen_v = pl.point_to_victim(screen)
    if f <= GRAB:
        # notices him and recoils, arms coming up to shield the face
        rec = ss(4, 20, f)
        lean = 9 * rec
        R = K.rot("X", lean)
        v.torso = Matrix.Translation((0, -0.05 * rec, 0.25 * rec)) @ K.rot("X", lean)
        for leg in ("Right Leg", "Left Leg"):
            v.rotate(leg, R.inverted())
        up = ss(12, 24, f)
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            v.point(arm, Vector((0.35 * sx * up, -1 + 1.6 * up, -0.9 * up)).normalized())
        v.look(screen_v, limit=60)
        ctx["grab_head"] = v.head_world().copy()
        return v
    # held by the head: from where he grabbed it up to his screen, then dropped
    hold_b = an.rest_delta("Head") @ (SCREEN + Vector((0, -0.34, -0.06)))  # in front of the screen
    hold = pl.point_to_victim(hold_b)
    lift = ss(GRAB, LIFTED, f)
    head_pos = ctx["grab_head"].translation.lerp(hold, lift)
    kick = window(f, GRAB, GRAB + 4, 84, 96)
    swing = Vector((math.sin(f / 4.3) * 5 * kick, 0, math.sin(f / 3.1) * 4 * kick))
    torso_rot = K.rot("X", swing.x) @ K.rot("Z", swing.z)
    head_cf = K.look_cf(head_pos, screen_v)
    held = K.Victim()
    held.hang_from_head(head_cf, torso_rot)
    if f >= DROP:
        # dropped: falls, crumples at his feet onto its back, and lies still
        t = min(1.0, (f - DROP) / (LAND - DROP))
        lying = K.Victim()
        lying.torso = Matrix.Translation((0.3, -2.45, -1.2)) @ K.rot("Y", 18) @ K.rot("X", 88)
        bounce = 0.25 * math.sin(math.pi * min(1.0, (f - LAND) / 6)) if f > LAND else 0.0
        a, b = held.torso, lying.torso
        m = K.blend_cf(a, b, t * t)
        m.translation.y += bounce
        v.torso = m
        limp = ss(DROP, LAND, f)
        v.rotate("Right Arm", K.rot("Z", 70 * limp) @ K.rot("X", -20 * limp))
        v.rotate("Left Arm", K.rot("Z", -55 * limp) @ K.rot("X", 30 * limp))
        v.rotate("Right Leg", K.rot("X", -25 * limp) @ K.rot("Z", 8 * limp))
        v.rotate("Left Leg", K.rot("X", -5 * limp) @ K.rot("Z", -10 * limp))
        v.look(screen_v, roll=-20 * limp, limit=50)
        return v
    v.torso, v.T["Head"] = held.torso, held.T["Head"]
    # legs kicking, slowing as he goes limp after the signal cuts
    for leg, ph in (("Right Leg", 0.0), ("Left Leg", math.pi)):
        a = math.sin(f / 2.6 + ph) * 32 * kick
        v.rotate(leg, K.rot("X", a - 8 * (1 - kick)) @ K.rot("Z", 4 * (1 if leg == "Right Leg" else -1)))
    ctx["head_cf"] = head_cf
    return v


def grip_arms(an, ctx, f, v):
    """His hands: hanging, then reaching for the player's head, then clamped on its sides (as on
    his own monitor), opening when he drops them."""
    pl = ctx["pl"]
    reach = ss(10, GRAB, f)
    release = ss(DROP, DROP + 8, f)
    T = an.rest_delta("UpperTorso")
    head_b = pl.to_blender(v.head_world())
    hc = head_b.translation
    side_x = head_b.to_3x3().col[0].normalized()  # the player's right, in his space
    up = head_b.to_3x3().col[1].normalized()
    fwd = -head_b.to_3x3().col[2].normalized()
    for side, sx in SIDES:
        rest = T @ an.pb[f"{side}LowerArm"].bone.tail_local
        grip = hc + side_x * sx * (0.62 * KM + 0.05) - up * 0.06 * 0 - fwd * 0.02
        target = rest.lerp(grip, A.ease(reach))
        target += (T.to_3x3() @ Vector((sx * 0.3, -1.0, 0.0))) * 0.18 * math.sin(math.pi * reach) * (1 - release)
        if release:
            target = target.lerp(rest + Vector((sx * 0.15, -0.35, 0.25)), release)
        pole = T.to_3x3() @ Vector((sx * 0.8, -0.65 * reach, -0.6))
        hand_dir = (up * 0.9 + fwd * 0.3).normalized() if reach > 0.5 else None
        palm = -side_x * sx
        K.reach(an, side, target, pole, hand_dir if release < 0.5 else None, palm)
    return reach, release


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    reach, release = grip_arms(an, ctx, f, v)
    grip = max(0.0, reach * 2 - 1) * (1 - release)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, 8 + 28 * grip, spread=-6 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    # the player's hands clutch at his wrists while held
    if GRAB < f < DROP:
        pl = ctx["pl"]
        clutch = ss(GRAB, GRAB + 8, f)
        for arm, side in (("Right Arm", "Left"), ("Left Arm", "Right")):
            wrist = pl.point_to_victim(an.pb[f"{side}LowerArm"].tail)
            sh = v.torso @ Vector((1.0 if arm == "Right Arm" else -1.0, 0.5, 0))
            d = (wrist - sh).normalized()
            hang = Vector((0, -1, 0))
            v.point(arm, hang.lerp(d, clutch).normalized())
    return v


def main(blend, export_dir, preview):
    K.run_kill(blend, "StandIn_Rig", LENGTH, KM, DISTANCE, kill, os.path.join(export_dir, "StandIn_Kill_Victim.rbxmx"),
               preview, "StandIn_Kill_Victim", MARKERS)
    print("kill: monster action 'Kill' and victim KeyframeSequence written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
