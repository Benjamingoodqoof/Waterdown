#!/usr/bin/env python3
"""Dewey's kill (the poster monster), "Neck snap", keyed pose to pose.

His head tilts slowly, curious. He sinks low, his neck jutting, his long arms swung back behind
him with the claws spread; a beat. Then he lunges, swings both rolled-poster claws round in a
wide arc and clamps them on the sides of the player's head, and rises up tall, yanking them off
their feet to his mask. He studies their face, the cracked mask tilting slowly from side to
side, while they claw at his arms and kick. Then the wind-up: elbows rising, his whole body
coils one way as he turns their head slowly the same way, and holds it, trembling, while they
kick wildly; then a violent snap the other way. The body jerks and goes slack in his hands. He
lifts it a little and lets go: it drops, folds and tips back, the head still turned the wrong
way. He keeps his hands up a beat, then straightens, watching it.

Writes Dewey's "Kill" action into the blend, and the player's half on the R6 rig
(export/PosterMonster_Kill_Victim.blend). Both start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him. 100 frames at 30 fps.

Markers: Grab 18 (QTE starts), Snap 51 (QTE ends: crack, cut to black, or fill the screen with
posters), Drop 60, End 100.

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
import kill_anim as KA  # noqa: E402
import kill_core as K  # noqa: E402
from kill_anim import Track as T  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.707, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.4
LENGTH = 100
COIL, GRAB, PULLED, TWIST, SNAP, DROP = 10, 18, 28, 44, 51, 60
MARKERS = {GRAB: "Grab", SNAP: "Snap", DROP: "Drop", LENGTH: "End"}
MASK = Vector((0.0, -0.2, 2.5))
MASK_N = Vector((-0.009, -0.976, 0.22))
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")

# ---------------------------------------------------------------- his key poses
# world-axis degrees: x leans forward, y tips to his left, z turns his chest to his left
BODY = {
    "LowerTorso": T((0, (0, 0, 0)), (4, (2, 0, 0)), (COIL, (-6, 0, 0), "io"), (COIL + 3, (-7, 0, 0)),
                    (GRAB, (26, 0, 0), "o3"), (PULLED, (8, 0, 0), "io"), (TWIST, (10, 0, 0)), (48, (18, 0, 8), "io"),
                    (SNAP, (22, 0, -6), "o5"), (54, (22, 0, -4)), (DROP, (20, 0, 0)), (DROP + 4, (24, 0, 0), "o"),
                    (80, (14, 0, 0), "io"), (LENGTH, (10, 0, 0))),
    "Spine": T((0, (0, 0, 0)), (COIL, (-8, 0, 0), "io"), (GRAB, (16, 0, 0), "o3"), (PULLED, (2, 0, 0), "io"), (TWIST, (4, 0, 0)),
               (48, (8, 0, 12), "io"), (SNAP, (10, 0, -14), "o5"), (54, (10, 0, -10)), (DROP, (10, 0, -4)),
               (80, (8, 0, 0)), (LENGTH, (6, 0, 0))),
    "UpperTorso": T((0, (0, 0, 0)), (COIL, (-10, 0, 0), "io"), (GRAB, (14, 0, 0), "o3"), (PULLED, (-4, 0, 0), "io"),
                    (36, (-2, 0, 0)), (TWIST, (0, 0, 0)), (48, (4, 0, 18), "io"), (SNAP, (8, 0, -22), "o5"),
                    (54, (8, 0, -16)), (DROP, (8, 0, -6)), (DROP + 4, (12, 0, 0), "o"), (80, (8, 0, 0)), (LENGTH, (6, 0, 0))),
    "Neck": T((0, (0, 0, 0)), (COIL, (14, 0, 0), "io"), (GRAB, (10, 0, 0), "o3"), (PULLED, (14, 0, 0)), (LENGTH, (10, 0, 0))),
    # the mask: tilts slowly, curious; held on the player (AIM) with slow side-to-side tilts
    "Head": T((0, (0, 0, 0)), (8, (0, 26, 0)), (COIL, (0, 30, 0)), (GRAB, (-6, 10, 0), "o3"), (PULLED, (-8, 18, 0)),
              (36, (-8, -20, 0), "io"), (TWIST, (-8, -10, 0)), (48, (-8, 14, 0), "io"), (SNAP, (-6, -16, 0), "o3"),
              (DROP, (-6, 24, 0)), (72, (0, 36, 0), "io"), (LENGTH, (0, 40, 0))),
}
LAGS = {"Spine": 1, "UpperTorso": 1, "Neck": 2, "Head": 3}
# aimed at the player until he has them; after that their head is placed in front of his mask
AIM = T((0, 0.6), (GRAB - 2, 1.0), (GRAB + 4, 0.0, "o"), (DROP + 2, 0.0), (DROP + 12, 0.8))
PELVIS = T((0, (0, 0, 0)), (4, (0, 0.02, 0)), (COIL, (0, 0.06, -0.12), "io"), (COIL + 3, (0, 0.07, -0.13)),
           (GRAB, (0, -0.08, -0.26), "o3"), (PULLED, (0, 0.04, -0.06), "io"), (SNAP, (0, 0.0, -0.16), "o5"),
           (DROP, (0, 0.0, -0.15)), (DROP + 4, (0, -0.02, -0.2), "o"), (80, (0, 0.0, -0.12)), (LENGTH, (0, 0.0, -0.06)))
LEFT_FOOT = T((0, (0, 0, 0)), (COIL + 3, (0, 0.02, 0)), (15, (0.02, -0.2, 0.12), "o"), (GRAB, (0.04, -0.36, 0), "i"), arc=True)
RIGHT_FOOT = T((0, (0, 0, 0)), (COIL, (0, 0.04, 0)), (GRAB, (-0.02, 0.06, 0), "o"))
FINGERS = T((0, 8), (COIL, -18), (GRAB - 1, -18), (GRAB, 40, "o3"), (47, 52), (SNAP, 46), (DROP - 1, 46),
            (DROP + 2, -10, "o3"), (80, 10))


def monster_body(an, f, ctx):
    peel = 10 * math.sin(math.pi * K.smoothstep(COIL, 26, f)) + 12 * A.bump(f, SNAP, SNAP + 3, SNAP + 14)
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS},
                    {f"{p}1": [("x", peel * math.sin(f / 3.0 + i) + 3 * math.sin(f / 9.0 + i))] for i, p in enumerate(PEELS)})
    if "vhead" in ctx:
        KA.aim_bone(an, "Head", MASK, MASK_N, KA.follow(ctx, "aim", ctx["vhead"], 0.4), AIM(f), max_deg=45)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (LEFT_FOOT if side == "Left" else RIGHT_FOOT)(f), 0.0, 0.2 * sx)


# ---------------------------------------------------------------- the player's key poses
FLINCH = KA.flinch_tracks(3, 14, "Right Leg", big=1.0)
# held by the head: the distance in front of his mask (m), the twist of their head on their neck
DIST = T((GRAB, 0.6), (PULLED, 0.46, "o"), (36, 0.42), (SNAP, 0.42), (SNAP + 2, 0.38, "o3"))
SNAPROT = T((GRAB, (0, 0, 0)), (TWIST, (0, 0, 0)), (48, (0, -35, -6), "io"), (49, (0, -38, -6)),
            (SNAP + 1, (14, 150, 24), "o"), (SNAP + 4, (8, 138, 20), "io"))
H_ROT = T((GRAB, FLINCH["rot"](GRAB)), (21, (-18, 0, -4), "o3"), (PULLED, (-6, 0, 2), "io"), (33, (-8, 4, -3)),
          (38, (-4, -4, 3)), (TWIST, (-6, 0, 0)), (48, (-6, -18, 4), "io"), (SNAP, (-10, -30, 10), "o3"),
          (53, (-4, 30, -6), "o"), (57, (2, 10, 0), "io"), (DROP, (0, 4, 0)))
OUT_R, OUT_L = ((0.9, 0.3, -0.35), (0, 0.15, 0)), ((-0.9, 0.3, -0.35), (0, 0.15, 0))
ARMS = {
    "Right Arm": KA.PoseKeys(
        (GRAB, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3))), (GRAB + 3, ("fore", (-0.2, 0.3, -0.4)), "o"),
        (26, ("fore", (-0.15, 0.1, -0.35))), (30, ("fore", (-0.2, 0.35, -0.4))), (34, ("fore", (-0.15, 0.05, -0.35))),
        (38, ("fore", (-0.2, 0.3, -0.4))), (TWIST, ("wrist", (-0.25, 0.3, -0.45)), "io"), (49, ("wrist", (-0.3, 0.35, -0.4))),
        (SNAP, OUT_R, "o3"), (53, ((0.6, -0.5, -0.5), (0, 0, 0)), "o"), (57, ((0.12, -1, 0.0), (0, 0, 0)), "i"),
        (DROP, ((0.1, -1, 0.05), (0, 0, 0)))),
    "Left Arm": KA.PoseKeys(
        (GRAB, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3))), (GRAB + 2, ("fore", (0.2, 0.3, -0.4)), "o"),
        (24, ("fore", (0.15, 0.35, -0.4))), (28, ("fore", (0.2, 0.1, -0.35))), (32, ("fore", (0.15, 0.35, -0.4))),
        (37, ("fore", (0.2, 0.05, -0.35))), (TWIST, ("wrist", (0.25, 0.35, -0.45)), "io"), (49, ("wrist", (0.3, 0.3, -0.4))),
        (SNAP, OUT_L, "o3"), (54, ((-0.5, -0.6, -0.4), (0, 0, 0)), "o"), (58, ((-0.1, -1, 0.05), (0, 0, 0)), "i"),
        (DROP, ((-0.1, -1, 0.05), (0, 0, 0)))),
}
LEGS = {
    leg: KA.PoseKeys(
        (GRAB, (((0.05, -0.95, 0.35) if leg == "Right Leg" else (-0.05, -0.95, -0.3)), (0, 0, 0))),
        (GRAB + 3, ((sx * 0.06, -1, 0.0), (0, 0, 0)), "o"),
        *KA.kick_keys(leg, 22, 42, beat=5, a0=1.0, a1=0.7, phase=0 if leg == "Right Leg" else 1),
        *KA.kick_keys(leg, TWIST, 48, beat=2, a0=0.9, a1=1.0, phase=1 if leg == "Right Leg" else 0),
        (SNAP, ((sx * 0.1, -0.55, -0.8), (0, 0.45, -0.12)), "o3"), (53, ((sx * 0.06, -1, 0.25), (0, 0, 0)), "o"),
        (57, ((sx * 0.05, -1, -0.05), (0, 0, 0)), "io"), (DROP, ((sx * 0.05, -1, 0.0), (0, 0, 0))))
    for leg, sx in (("Right Leg", 1), ("Left Leg", -1))
}


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    D = an.rest_delta("Head")
    mask = pl.point_to_victim(D @ MASK)
    if f <= GRAB:
        v = KA.apply_flinch(va, f, FLINCH, look_at=mask)
        ctx["grab_head"] = v.head_world().copy()
        return v
    if f < DROP:
        n = (D.to_3x3() @ MASK_N).normalized()
        front = pl.point_to_victim(D @ MASK + n * DIST(f))
        pull = KA.EASE["o"](min(1.0, (f - GRAB) / (PULLED - GRAB)))
        pos = ctx["grab_head"].translation.lerp(front, pull)
        head_cf = K.look_cf(pos, mask) @ KA.euler(SNAPROT(f))
        held = K.Victim()
        held.hang_from_head(head_cf, KA.euler(H_ROT(f)))
        v = va.build(f, held.torso, lag={"head": 0})
        v.T["Head"] = held.T["Head"]
        targets = {}
        for arm, side, t in (("Right Arm", "Left", 0.55), ("Left Arm", "Right", 0.45)):
            lo = an.pb[f"{side}LowerArm"]
            targets[arm] = {"fore": pl.point_to_victim(lo.head.lerp(lo.tail, t)) + Vector((0, -0.25, 0)),
                            "wrist": pl.point_to_victim(lo.tail) + Vector((0, -0.25, 0))}
        KA.pose_limbs(va, v, f, ARMS, LEGS, targets)
        ctx["drop_torso"], ctx["drop_rot"], ctx["drop_limbs"] = held.torso, H_ROT(f), KA.limb_dirs(v)
        ctx["neck_T"] = held.T["Head"].copy()
        return v
    # dropped: the legs fold, the body tips back and slams down, the head still turned the wrong way
    if "fall" not in ctx:
        ctx["fall"] = KA.fall_tracks(ctx["drop_torso"].translation.copy(), ctx["drop_rot"], DROP, "drop",
                                     land=(-0.6, 1.5), yaw=20, side=1.0)
    v = KA.apply_fall(va, f, ctx["fall"], ctx["drop_limbs"])
    v.T["Head"] = ctx["neck_T"]
    return KA.floor_clamp(v)


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
            back = r0 + Vector((sx * 0.12, 0.38, 0.12))  # swung back behind him, claws open
            mid = Vector((sx * 0.55, -0.5, 1.6))
            target = T((0, r0), (4, r0 + Vector((0, -0.04, 0))), (COIL, back, "io"), (COIL + 3, back + Vector((0, 0.03, 0.02))),
                       (16, mid, "i"), (GRAB, grip, "o"), arc=True)(f)
        elif f <= DROP:
            target = grip
        else:
            if "rel_" + side not in ctx:
                ctx["rel_" + side] = grip
            rel = ctx["rel_" + side]
            target = T((DROP, rel), (DROP + 3, rel + Vector((sx * 0.08, 0.02, 0.04)), "o3"), (70, rel + Vector((sx * 0.06, 0.04, 0.0))),
                       (90, r0 + Vector((0, -0.1, 0.12)), "io"), (LENGTH, r0 + Vector((0, -0.08, 0.08))))(f)
        hand_dir = (-hx * sx * 0.3 + Vector((0, 0, 1)) * 0.6 - hz * 0.2).normalized() if GRAB - 2 <= f <= DROP else None
        up = K.window(f, TWIST, 48, SNAP, SNAP + 4)  # elbows rise for the twist, whip through the snap
        pole = Tm.to_3x3() @ Vector((sx * 1.0, 0.2, -0.4)).lerp(Vector((sx * 0.8, 0.3, 0.5)), up)
        K.reach(an, side, target, pole, hand_dir, -hx * sx)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, FINGERS(f), spread=10 * K.window(f, 4, COIL, GRAB - 1, GRAB)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    ctx["vhead"] = pl.to_blender(v.head_world()).translation
    return v


NOTE = """Dewey (poster monster) kill, the player's half: InternalArmature carries the action
PosterMonster_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted
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
