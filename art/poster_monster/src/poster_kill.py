#!/usr/bin/env python3
"""Dewey's kill (the poster monster), "Neck snap", keyed pose to pose.

His head tilts slowly, curious; he sinks a little and his long arms swing back, then he lunges
and clamps both rolled-poster claws on the sides of the player's head and yanks them up off
their feet to his mask, bending down to meet them. He holds them there, his cracked mask tilting
slowly from side to side as he studies their face, while they claw at his arms. Then a small
twist one way, and a violent snap the other. The body goes slack in his hands; he lets go and it
drops in a heap, the head turned the wrong way. He keeps his hands up a beat, then straightens,
watching it.

Writes Dewey's "Kill" action into the blend, and the player's half on the R6 rig
(export/PosterMonster_Kill_Victim.blend). Both start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him. 90 frames at 30 fps.

Markers: Grab 16 (QTE starts), Snap 46 (QTE ends: crack, cut to black, or fill the screen with
posters), Drop 54, End 90.

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
import kill_anim as KA  # noqa: E402
import kill_core as K  # noqa: E402
from kill_anim import Track as T  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.707, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.4
LENGTH = 90
GRAB, PULLED, TWIST, SNAP, DROP, LAND = 16, 26, 42, 46, 54, 66
MARKERS = {GRAB: "Grab", SNAP: "Snap", DROP: "Drop", LENGTH: "End"}
MASK = Vector((0.0, -0.2, 2.5))
MASK_N = Vector((-0.009, -0.976, 0.22))
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")

BODY = {
    "LowerTorso": T((0, (0, 0, 0)), (9, (-4, 0, 0)), (GRAB, (24, 0, 0), "o3"), (PULLED, (22, 0, 0)),
                    (SNAP, (22, 0, 0)), (SNAP + 2, (26, 0, 0), "o3"), (DROP + 6, (18, 0, 0)), (LENGTH, (12, 0, 0))),
    "Spine": T((0, (0, 0, 0)), (9, (-4, 0, 0)), (GRAB, (16, 0, 0), "o3"), (PULLED, (16, 0, 0)), (TWIST, (16, 0, -6)),
               (SNAP, (16, 0, 10), "o5"), (DROP + 6, (12, 0, 0)), (LENGTH, (10, 0, 0))),
    "UpperTorso": T((0, (0, 0, 0)), (9, (-6, 0, 0)), (GRAB, (14, 0, 0), "o3"), (PULLED, (16, 0, 0)),
                    (TWIST, (16, 0, -10), "io"), (SNAP, (16, 0, 14), "o5"), (DROP, (16, 0, 6)), (LENGTH, (12, 0, 0))),
    "Neck": T((0, (0, 0, 0)), (GRAB, (10, 0, 0), "o3"), (PULLED, (14, 0, 0)), (LENGTH, (10, 0, 0))),
    # the mask: tilts slowly, curious; held on the player (AIM) with slow side-to-side tilts
    "Head": T((0, (0, 0, 0)), (8, (0, 26, 0)), (GRAB, (-6, 10, 0), "o3"), (PULLED, (-8, 18, 0)), (34, (-8, -20, 0), "io"),
              (TWIST, (-8, -8, 0)), (SNAP, (-6, 22, 0), "o3"), (DROP, (-6, 14, 0)), (70, (0, 30, 0), "io"), (LENGTH, (0, 34, 0))),
}
LAGS = {"Spine": 1, "UpperTorso": 1, "Neck": 2, "Head": 3}
# aimed at the player until he has them; after that their head is placed in front of his mask
AIM = T((0, 0.6), (GRAB - 2, 1.0), (GRAB + 4, 0.0, "o"), (DROP + 2, 0.0), (DROP + 10, 0.8))
PELVIS = T((0, (0, 0, 0)), (9, (0, 0.04, -0.06)), (GRAB, (0, -0.06, -0.3), "o3"), (PULLED, (0, 0.0, -0.26)),
           (SNAP, (0, 0.0, -0.26)), (SNAP + 2, (0, -0.02, -0.29), "o3"), (DROP + 8, (0, 0.0, -0.2)), (LENGTH, (0, 0.0, -0.08)))
LEFT_FOOT = T((0, (0, 0, 0)), (10, (0, 0, 0)), (13, (0.02, -0.2, 0.1), "o"), (GRAB, (0.04, -0.34, 0), "i"), arc=True)
RIGHT_FOOT = T((0, (0, 0, 0)), (GRAB, (-0.02, 0.06, 0), "o"))
FINGERS = T((0, 8), (10, -14), (GRAB - 1, -14), (GRAB, 40, "o3"), (SNAP, 46), (DROP, 46), (DROP + 3, -6, "o3"), (LENGTH, 10))


def monster_body(an, f, ctx):
    peel = 10 * math.sin(math.pi * K.smoothstep(9, 24, f)) + 12 * A.bump(f, SNAP, SNAP + 3, SNAP + 14)
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS},
                    {f"{p}1": [("x", peel * math.sin(f / 3.0 + i) + 3 * math.sin(f / 9.0 + i))] for i, p in enumerate(PEELS)})
    if "vhead" in ctx:
        KA.aim_bone(an, "Head", MASK, MASK_N, ctx["vhead"], AIM(f))
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (LEFT_FOOT if side == "Left" else RIGHT_FOOT)(f), 0.0, 0.2 * sx)


# ---------------------------------------------------------------- the player's key poses
V_HIPS = T((0, (0, -1, 0)), (4, (0, -1, 0)), (14, (0, -1, 0.4), "o"))
V_ROT = T((0, (0, 0, 0)), (4, (-3, 0, 0)), (14, (12, 0, 4), "o3"))
V_ARM_R = T((0, (0, -1, 0)), (6, (0.15, -1, 0.1)), (14, (0.3, 0.45, -0.85), "o3"))
V_ARM_L = T((0, (0, -1, 0)), (6, (-0.15, -1, 0.1)), (14, (-0.25, 0.55, -0.85), "o3"))
V_HEAD = T((0, (10, 0, 0)), (4, (18, 0, 0), "o"), (14, (-4, 0, -3), "o"))
# held by the head: the distance in front of his mask, the twist of their head on their neck
DIST = T((GRAB, 0.6), (PULLED, 0.46, "o"), (34, 0.42), (SNAP, 0.42), (SNAP + 2, 0.38, "o3"))
SNAPROT = T((GRAB, (0, 0, 0)), (TWIST, (0, 0, 0)), (44, (0, -28, -6), "io"), (SNAP, (14, 150, 24), "o5"),
            (SNAP + 3, (8, 138, 20), "io"))
H_ROT = T((GRAB, (12, 0, 4)), (19, (-18, 0, -4), "o3"), (PULLED, (-8, 0, 2)), (TWIST, (-6, 0, 0)), (SNAP, (-6, 0, 0)),
          (SNAP + 2, (-10, 0, 14), "o3"), (50, (2, 0, -6)), (DROP, (-2, 0, 2)))
KICK = T((GRAB, 0.0), (20, 1.0, "o"), (TWIST, 0.6), (SNAP, 0.6), (SNAP + 1, 0.0, "o3"))
CLAW = T((GRAB, 0.0), (22, 1.0, "o"), (SNAP, 1.0), (SNAP + 2, 0.0, "o3"))


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    D = an.rest_delta("Head")
    mask = pl.point_to_victim(D @ MASK)
    if f <= GRAB:
        torso = va.torso_from_hips(V_HIPS(f), V_ROT(f))
        feet = {"Right Leg": Vector((0.5, -3, 0.75 * K.smoothstep(4, 12, f))), "Left Leg": Vector((-0.5, -3, 0.0))}
        legs = {leg: foot - torso @ Vector((0.5 if leg == "Right Leg" else -0.5, -1, 0)) for leg, foot in feet.items()}
        v = va.build(f, torso, limbs={"Right Arm": V_ARM_R(f), "Left Arm": V_ARM_L(f)}, limbs_w=legs, head=V_HEAD(f),
                     look_at=mask)
        ctx["grab_head"] = v.head_world().copy()
        return v
    if f < DROP:
        n = (D.to_3x3() @ MASK_N).normalized()
        front = pl.point_to_victim(D @ MASK + n * DIST(f) * 1.0)
        pull = KA.EASE["o"](min(1.0, (f - GRAB) / (PULLED - GRAB)))
        pos = ctx["grab_head"].translation.lerp(front, pull)
        head_cf = K.look_cf(pos, mask) @ KA.euler(SNAPROT(f))
        k = KICK(f)
        held = K.Victim()
        held.hang_from_head(head_cf, KA.euler(H_ROT(f) + Vector((0, 0, 4 * math.sin(f / 3.5) * k))))
        dead = f > SNAP
        legs = {"Right Leg": (0.05, -1, 0.5 * k * math.sin(f / 2.4)), "Left Leg": (-0.05, -1, -0.5 * k * math.sin(f / 2.4 + 0.6))}
        legs_w = {}
        if dead:
            legs, legs_w = {}, {"Right Leg": (0.08, -1, 0.05), "Left Leg": (-0.05, -1, -0.05)}
        # their hands claw at his forearms, then drop dead
        arms = {}
        for arm, sx, side in (("Right Arm", 1, "Left"), ("Left Arm", -1, "Right")):
            sh = held.torso @ Vector((sx * 1.0, 0.5, 0))
            fa = pl.point_to_victim((an.pb[f"{side}LowerArm"].head + an.pb[f"{side}LowerArm"].tail) / 2)
            to = held.torso.to_3x3().inverted() @ (fa - sh).normalized()
            arms[arm] = Vector((0, -1, 0)).lerp(to, CLAW(f))
        arms_w = {}
        if dead:
            arms = {}
            arms_w = {"Right Arm": (0.15, -1, 0.1), "Left Arm": (-0.1, -1, -0.05)}
        v = va.build(f, held.torso, limbs={**arms, **legs}, limbs_w={**legs_w, **arms_w}, lag={"arms": 4, "legs": 3})
        v.T["Head"] = held.T["Head"]
        ctx["drop_torso"], ctx["drop_rot"], ctx["neck_T"] = held.torso, H_ROT(f), held.T["Head"].copy()
        return v
    # dropped: the legs fold, the body slumps onto its side, the head still turned the wrong way
    if "fall" not in ctx:
        p0 = ctx["drop_torso"].translation.copy()
        r0 = ctx["drop_rot"]
        ctx["fall"] = (T((DROP, p0), (59, (p0.x + 0.1, -0.9, p0.z + 0.2), "i"), (LAND, (p0.x + 0.9, -2.0, p0.z + 0.4), "i"),
                         (69, (p0.x + 0.95, -1.88, p0.z + 0.42), "o"), (73, (p0.x + 1.0, -2.0, p0.z + 0.45), "i")),
                       T((DROP, r0), (59, (-12, 10, -20), "i"), (LAND, (-6, 30, -88), "i"), (69, (-6, 30, -82), "o"),
                         (73, (-6, 30, -88), "i")))
    pos, rot = ctx["fall"][0](f), ctx["fall"][1](f)
    land = K.smoothstep(59, LAND, f)
    torso = Matrix.Translation(pos) @ KA.euler(rot)
    arms = {"Right Arm": Vector((0.3, -0.9, 0.3)).lerp(Vector((0.4, -0.6, -0.7)), land),
            "Left Arm": Vector((-0.2, -0.9, -0.2)).lerp(Vector((-0.2, -0.8, 0.55)), land)}
    legs = {"Right Leg": Vector((0.05, -0.7, -0.7)).lerp(Vector((0.15, -0.9, -0.4)), land),
            "Left Leg": Vector((-0.05, -0.75, -0.65)).lerp(Vector((-0.05, -0.85, -0.5)), land)}
    v = va.build(f, torso, limbs={**arms, **legs}, lag={"arms": 3, "legs": 2})
    v.T["Head"] = ctx["neck_T"]
    return v


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f, ctx)
    v = victim(an, ctx, f)
    Tm = an.rest_delta("UpperTorso")
    hb = pl.to_blender(v.head_world())
    hx = hb.to_3x3().col[0].normalized()
    hz = hb.to_3x3().col[2].normalized()  # the back of their head
    for side, sx in SIDES:
        r0 = an.pb[f"{side}LowerArm"].bone.tail_local.copy()
        # his left claw on their right side of the head (both at +x), a little behind the ear
        grip = hb.translation + hx * sx * (0.62 * KM + 0.05) + hz * 0.03
        if f <= GRAB:
            mid = Vector((sx * 0.5, -0.45, 1.25))
            target = T((0, r0), (9, r0 + Vector((sx * 0.1, 0.12, 0.05))), (13, mid, "i"), (GRAB, grip, "o"), arc=True)(f)
        elif f <= DROP:
            target = grip
        else:
            if "rel_" + side not in ctx:
                ctx["rel_" + side] = grip
            rel = ctx["rel_" + side]
            target = T((DROP, rel), (DROP + 3, rel + Vector((sx * 0.08, 0.02, 0.04)), "o3"), (62, rel + Vector((sx * 0.06, 0.04, 0.0))),
                       (LENGTH, r0 + Vector((0, -0.1, 0.12)), "io"))(f)
        hand_dir = (-hx * sx * 0.3 + Vector((0, 0, 1)) * 0.6 - hz * 0.2).normalized() if GRAB - 2 <= f <= DROP else None
        K.reach(an, side, target, Tm.to_3x3() @ Vector((sx * 1.0, 0.2, -0.4)), hand_dir, -hx * sx)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, FINGERS(f), spread=8 * K.window(f, 6, 10, GRAB - 1, GRAB)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    ctx["vhead"] = pl.to_blender(v.head_world()).translation
    return v


NOTE = """Dewey (poster monster) kill, the player's half: InternalArmature carries the action
PosterMonster_Kill_Victim (30 fps, frames 0-90). Its constraints to the control rig are muted
so the keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (QTE
starts), Snap (QTE ends), Drop, End.
The 'Monster (reference)' collection holds Dewey playing his half, at your in-game size, lined
up where the game should put him: 3.4 studs in front of the player, facing them.
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
