#!/usr/bin/env python3
"""The Stand-In's kill (CRT Man), keyed pose to pose.

He rears back for a beat, then lunges with one long step and seizes the player by the collar,
yanks them up off their feet and holds them out at arm's length, face to face with his screen
(the game shows their avatar on it, with static getting louder). The monitor cocks slowly from
side to side, studying them, while they kick and pull at his wrist. They convulse and go limp;
he holds them a beat, then opens his hand and they drop and crumple at his feet. He bends to
watch the body.

Writes the Stand-In's "Kill" action into the blend, and the player's half on the R6 rig
(export/StandIn_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of his, facing him. 110 frames at 30 fps.

Markers: Grab 14 (show the player's avatar on his screen, start the static; QTE starts),
Death 72 (static peaks; QTE ends), Drop 88, End 110.

Usage: python3 standin_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
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
import kill_anim as KA  # noqa: E402
import kill_core as K  # noqa: E402
from kill_anim import Track as T  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 110
GRAB, LIFTED, DEATH, LIMP, DROP, LAND = 14, 26, 72, 78, 88, 100
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", LENGTH: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))
COLLAR = Vector((0.0, 0.85, -0.55))  # the front of their collar, in their torso's frame
SIDES = (("Left", 1.0), ("Right", -1.0))

# ---------------------------------------------------------------- his key poses
BODY = {
    "LowerTorso": T((0, (3, 0, 0)), (7, (-2, 0, 0)), (14, (14, 0, -4), "o3"), (20, (11, 0, -2)), (30, (6, 0, 0)),
                    (88, (7, 0, 0)), (100, (12, 0, 0), "io"), (110, (10, 0, 0))),
    "UpperTorso": T((0, (6, 0, 0)), (7, (-6, 3, 4), "io"), (14, (26, -2, -8), "o3"), (20, (20, 0, -4)),
                    (30, (12, 0, 0)), (60, (15, 0, 0)), (88, (15, 0, 0)), (100, (24, 0, 0), "io"), (110, (20, 0, 0))),
    # the monitor: tips up as he rears, snaps down at the player, then cocks slowly from side to
    # side studying them, with a sharp twitch now and then
    "Head": T((0, (6, 0, 0)), (7, (-12, 0, 6)), (14, (22, 0, -6), "o3"), (22, (40, 6, 0), "o"), (30, (36, 10, 0)),
              (44, (38, -12, 2)), (52, (38, -12, 2)), (53, (40, -12, 10), "o"), (56, (38, -10, 2), "io"),
              (66, (40, 14, 0)), (72, (34, 14, 0)), (74, (44, 10, 0), "o"), (80, (40, 4, 0)), (88, (40, 4, 0)),
              (98, (56, 10, 0), "io"), (110, (52, 14, 0))),
    "LeftUpperArm": T((0, (-2, 3, 0)), (7, (-8, 3, 0)), (14, (16, 3, 0), "o3"), (24, (4, 3, 0)), (34, (0, 3, 0))),
    "LeftLowerArm": T((0, (-6, 0, 0)), (14, (-18, 0, 0), "o"), (30, (-8, 0, 0))),
}
LAGS = {"UpperTorso": 1, "Head": 2, "LeftUpperArm": 2, "LeftLowerArm": 4}
PELVIS = T((0, (0, 0, 0)), (7, (0, 0.04, 0.0)), (14, (0, -0.24, -0.08), "o3"), (22, (0, -0.2, -0.05)),
           (30, (0, -0.18, -0.03)), (88, (0, -0.18, -0.03)), (100, (0, -0.2, -0.07)), (110, (0, -0.2, -0.06)))
RIGHT_FOOT = T((0, (0, 0, 0)), (8, (0, 0, 0)), (11, (0, -0.25, 0.12), "o"), (14, (0, -0.48, 0), "i"), arc=True)
LEFT_FOOT = T((0, (0, 0, 0)), (14, (0, -0.04, 0), "o"))
FINGERS_R = T((0, 8), (7, -12), (13, -12), (14, 58, "o3"), (88, 58), (90, -8, "o"), (104, 10))
FINGERS_L = T((0, 8), (14, 0, "o"), (40, 18), (60, 6), (80, 16))


def monster_body(an, f):
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS},
                    {f"Cable{i}": [("x", 8 * math.sin(math.pi * K.smoothstep(7, 30, f)) + 2 * math.sin(f / 9 + i))]
                     for i in (1, 2, 3)})
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (RIGHT_FOOT if side == "Right" else LEFT_FOOT)(f), 0.0, 0.06 * sx)


# ---------------------------------------------------------------- the player's key poses (free)
V_HIPS = T((0, (0, -1, 0)), (4, (0, -1, 0)), (12, (0, -1, 0.4), "o"))
V_ROT = T((0, (0, 0, 0)), (4, (-4, 0, 0)), (12, (14, 0, -5), "o3"))
V_ARM_R = T((0, (0, -1, 0)), (5, (0.15, -1, 0.1)), (12, (0.25, 0.45, -0.9), "o3"))
V_ARM_L = T((0, (0, -1, 0)), (5, (-0.15, -1, 0.1)), (12, (-0.3, 0.6, -0.85), "o3"))
V_HEAD = T((0, (8, 0, 0)), (4, (14, 0, 0)), (12, (-6, 0, 4), "o"))  # looks up at him, then turtles
# held
H_ROT = T((GRAB, (14, 0, -5)), (17, (-14, 0, 5), "o3"), (22, (10, 0, -3)), (28, (4, 0, 2), "io"), (DEATH, (4, 0, 0)),
          (74, (-10, 0, 0), "o"), (76, (8, 0, 2), "o"), (LIMP, (4, 0, 0)), (DROP, (3, 0, 0)))
KICK = T((GRAB, 0.0), (18, 1.0, "o"), (40, 0.8), (64, 0.45), (DEATH, 0.3), (73, 1.3, "o"), (LIMP, 0.0, "o"))
CLUTCH = T((GRAB, 0.0), (20, 1.0, "o"), (DEATH, 1.0), (75, 0.0, "o"))
HEAD_H = T((GRAB, (-6, 0, 4)), (16, (-22, 0, -8), "o3"), (24, (6, 0, 0)), (DEATH, (0, 0, 0)), (75, (30, 0, 0), "o3"),
           (LIMP, (-25, 0, 0), "o"))


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    screen = pl.point_to_victim(an.rest_delta("Head") @ SCREEN)
    if f <= GRAB:
        hips, rot = V_HIPS(f), V_ROT(f)
        torso = va.torso_from_hips(hips, rot)
        feet = {"Right Leg": Vector((0.5, -3, 0.7 * K.smoothstep(4, 11, f))), "Left Leg": Vector((-0.5, -3, 0.0))}
        legs = {leg: foot - torso @ Vector((0.5 if leg == "Right Leg" else -0.5, -1, 0)) for leg, foot in feet.items()}
        v = va.build(f, torso, limbs={"Right Arm": V_ARM_R(f), "Left Arm": V_ARM_L(f)}, limbs_w=legs,
                     head=V_HEAD(f), look_at=screen)
        if f == GRAB:
            ctx["grab_rot"] = rot
        return v
    if f < DROP:
        grip = pl.point_to_victim(an.pb["RightHand"].matrix @ ctx["grip_local"])
        torso = va.torso_from_grip(grip, COLLAR, H_ROT(f) + Vector(
            (0, 0, 3 * math.sin(f / 7.0) * KICK(f))))
        k = KICK(f)
        legs = {"Right Leg": (0.05, -1, 0.55 * k * math.sin(f / 2.4)), "Left Leg": (-0.05, -1, -0.55 * k * math.sin(f / 2.4 + 0.6))}
        legs_w = {}
        if f >= LIMP - 2:
            legs, legs_w = {}, {"Right Leg": (0.05, -1, 0), "Left Leg": (-0.05, -1, 0)}
        wrist = pl.point_to_victim(an.pb["RightLowerArm"].tail)
        c = CLUTCH(f)
        arms = {}
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            sh = torso @ Vector((sx * 1.0, 0.5, 0))
            hang = torso.to_3x3().inverted() @ Vector((0, -1, 0))
            to_wrist = torso.to_3x3().inverted() @ (wrist + Vector((sx * 0.2, 0, 0)) - sh).normalized()
            arms[arm] = hang.lerp(to_wrist, c)
        limp = f >= LIMP
        head = HEAD_H(f)
        v = va.build(f, torso, limbs={**arms, **legs}, limbs_w=legs_w, head=head,
                     look_at=None if limp else screen, lag={"arms": 3, "legs": 3, "head": 2})
        ctx["drop_torso"] = torso
        ctx["drop_rot"] = H_ROT(f)
        return v
    # dropped: the legs hit, the body folds and tips back onto the floor, bounces once
    if "fall" not in ctx:
        p0 = ctx["drop_torso"].translation.copy()
        r0 = ctx["drop_rot"]
        ctx["fall"] = (T((DROP, p0), (94, (p0.x + 0.1, -0.7, p0.z + 0.2), "i"), (LAND, (p0.x + 0.2, -2.5, p0.z + 1.4), "i"),
                         (103, (p0.x + 0.2, -2.36, p0.z + 1.45), "o"), (107, (p0.x + 0.2, -2.5, p0.z + 1.5), "i")),
                       T((DROP, r0), (94, (22, 8, -10), "i"), (LAND, (88, 18, -14), "i"), (103, (82, 18, -14), "o"),
                         (107, (88, 18, -14), "i")))
    pos, rot = ctx["fall"][0](f), ctx["fall"][1](f)
    torso = Matrix.Translation(pos) @ KA.euler(rot)
    land = K.smoothstep(94, LAND, f)
    arms = {"Right Arm": Vector((0.3, 0.6, 0.2)).lerp(Vector((0.95, -0.25, 0.15)), land),
            "Left Arm": Vector((-0.3, 0.7, 0.1)).lerp(Vector((-0.95, -0.2, 0.2)), land)}
    legs = {"Right Leg": Vector((0.1, -0.75, -0.65)).lerp(Vector((0.18, -1, -0.15)), land),
            "Left Leg": Vector((-0.1, -0.8, -0.6)).lerp(Vector((-0.12, -1, -0.05)), land)}
    return va.build(f, torso, limbs={**arms, **legs}, head=Vector((-20 + 30 * land, 0, 25 * land)),
                    lag={"arms": 3, "legs": 2, "head": 3})


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f)
    Tm = an.rest_delta("UpperTorso")
    rest = Tm @ an.pb["RightLowerArm"].bone.tail_local
    if "hand_track" not in ctx:
        # where the collar will be at the grab, from the player's own (free) animation
        g = KA.VictimAnimator().torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
        collar = pl.point_to_blender(g @ COLLAR)
        rest0 = an.pb["RightLowerArm"].bone.tail_local.copy()
        lift = Vector((-0.04, -0.84, 1.66))
        ctx["hand_track"] = T((0, rest0), (7, rest0 + Vector((-0.06, 0.16, 0.08))),
                              (11, (rest0 + collar) / 2 + Vector((0, 0, 0.16)), "i"),
                              (GRAB, collar + Vector((0, 0.07, 0.02)), "o"),
                              (20, collar.lerp(lift, 0.6) + Vector((0, 0.1, 0.12)), "o3"), (LIFTED, lift, "io"),
                              (50, lift + Vector((0, 0.02, 0.03))), (DEATH, lift + Vector((0, 0.06, 0.05))),
                              (DROP, lift + Vector((0, 0.06, 0.05))), (93, lift + Vector((0.04, 0.0, -0.12)), "o"),
                              (LENGTH, rest0 + Vector((0, -0.12, 0.05))), arc=True)
    target = ctx["hand_track"](f)
    shake = Vector((0, 0, 0.004 * math.sin(f * 1.9))) * K.window(f, LIFTED, LIFTED + 6, DEATH, LIMP)
    hold = GRAB - 3 <= f <= DROP
    K.reach(an, "Right", target + shake, Tm.to_3x3() @ Vector((-0.8, 0.5, -0.6)),
            Vector((0.1, -0.85, -0.5)).normalized() if hold else None, Vector((0, -0.2, -1)))
    if f == GRAB:
        g = KA.VictimAnimator().torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
        collar = pl.point_to_blender(g @ COLLAR)
        ctx["grip_local"] = an.pb["RightHand"].matrix.inverted() @ collar
    pose = K.finger_curl(an, "Right", FINGERS_R(f))
    pose.update(K.finger_curl(an, "Left", FINGERS_L(f)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return victim(an, ctx, f)


NOTE = """CRT Man (Stand-In) kill, the player's half: InternalArmature carries the action
StandIn_Kill_Victim (30 fps, frames 0-110). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (show the
player's avatar on his screen, start the static), Death, Drop, End.
The 'Monster (reference)' collection holds the CRT Man playing his half, at your in-game size,
lined up where the game should put him: 3.6 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "StandIn_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "StandIn_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "StandIn_Kill_Victim.blend"), ctx["parts"], "StandIn_Kill_Victim",
                     MARKERS, (blend, "StandIn_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
