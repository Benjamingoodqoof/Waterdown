#!/usr/bin/env python3
"""The Stand-In's kill (CRT Man), keyed pose to pose.

His monitor jerks round to the player. He draws himself up and back: chest back, the monitor
tipped back to look down at them, his right hand drawn back. A beat. Then one long lunge and he
seizes them by the collar, gathers them in and hoists them up to his screen at arm's length
(the game shows their avatar on it, with static getting louder). The monitor cocks slowly from
side to side, studying them, while they kick, pull at his wrist and shove at the screen. He
pulls them in close to it; the static peaks; they convulse and go limp. He holds the body up a
beat, tilting the monitor at it, lifts it a little and opens his hand. It drops, folds and
tips back at his feet; he steps back and bends to watch it.

Writes the Stand-In's "Kill" action into the blend, and the player's half on the R6 rig
(export/StandIn_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of his, facing him. 120 frames at 30 fps.

Markers: Grab 17 (show the player's avatar on his screen, start the static; QTE starts),
Death 72 (static peaks; QTE ends), Drop 90, End 120.

Usage: python3 standin_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
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

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 120
COIL, GRAB, LIFTED, PULL, DEATH, LIMP, DROP = 10, 17, 30, 66, 72, 78, 90
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", LENGTH: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))
COLLAR = Vector((0.0, 0.85, -0.55))  # the front of their collar, in their torso's frame
SIDES = (("Left", 1.0), ("Right", -1.0))

# ---------------------------------------------------------------- his key poses
# world-axis degrees: x leans forward, y tips to his left, z turns his chest to his left
BODY = {
    "LowerTorso": T((0, (3, 0, 0)), (3, (2, 0, 0)), (COIL, (-6, 0, -6), "io"), (COIL + 2, (-7, 0, -7)),
                    (GRAB, (14, 0, 8), "o3"), (20, (16, 0, 6)), (LIFTED, (2, 0, 2), "io"), (50, (3, 0, 0)),
                    (PULL, (6, 0, 2), "io"), (DEATH, (0, 0, -2), "o3"), (84, (2, 0, 0)), (88, (0, 0, 0), "io"),
                    (DROP, (5, 0, 0), "o"), (104, (16, 0, 0), "io"), (LENGTH, (14, 0, 0))),
    "UpperTorso": T((0, (6, 0, 0)), (3, (4, 0, 0)), (COIL, (-12, 4, -14), "io"), (COIL + 2, (-13, 4, -15)),
                    (GRAB, (30, -2, 16), "o3"), (20, (32, 0, 12)), (LIFTED, (2, -4, 4), "io"), (44, (4, -2, 2)),
                    (56, (8, 0, 4)), (PULL, (14, 0, 6), "io"), (DEATH, (2, 0, 0), "o3"), (LIMP, (6, 0, 0)),
                    (88, (2, 0, 0), "io"), (DROP, (10, 0, 0), "o"), (104, (34, 0, 0), "io"), (LENGTH, (30, 0, 0))),
    # the monitor: jerks round, tips back, snaps down at them, then cocks slowly from side to
    # side studying them, with a sharp twitch now and then
    "Head": T((0, (6, 0, 0)), (3, (2, 12, 0), "o3"), (COIL, (-16, 4, 0)), (COIL + 2, (-18, 4, 0)), (GRAB, (22, 0, 0), "o3"),
              (24, (34, 8, 0), "o"), (LIFTED, (38, 12, 0)), (38, (38, -12, 2), "io"), (44, (38, -12, 2)),
              (45, (40, -12, 10), "o"), (48, (38, -10, 2), "io"), (56, (40, 14, 0), "io"), (PULL, (34, 4, 0)),
              (DEATH, (28, 0, 0), "o3"), (74, (40, 10, 0), "o"), (80, (40, 18, 0), "io"), (88, (40, 18, 0)),
              (DROP, (46, 8, 0)), (104, (56, 14, 0), "io"), (LENGTH, (52, 18, 0))),
    "LeftUpperArm": T((0, (-2, 3, 0)), (COIL, (16, 3, 0), "io"), (GRAB, (-24, 8, 0), "o3"), (LIFTED, (-6, 14, 0), "io"),
                      (PULL, (-4, 10, 0)), (DEATH, (-10, 18, 0), "o3"), (DROP, (0, 6, 0)), (104, (14, 3, 0), "io")),
    "LeftLowerArm": T((0, (-6, 0, 0)), (COIL, (-20, 0, 0)), (GRAB, (-10, 0, 0), "o"), (LIFTED, (-24, 0, 0)),
                      (DEATH, (-30, 0, 0), "o3"), (DROP, (-10, 0, 0)), (LENGTH, (-12, 0, 0))),
}
LAGS = {"UpperTorso": 1, "Head": 2, "LeftUpperArm": 2, "LeftLowerArm": 4}
PELVIS = T((0, (0, 0, 0)), (COIL, (0, 0.06, -0.03), "io"), (COIL + 2, (0, 0.07, -0.04)), (GRAB, (0, -0.26, -0.1), "o3"),
           (20, (0, -0.24, -0.12)), (LIFTED, (0, -0.18, -0.03), "io"), (PULL, (0, -0.16, -0.04)),
           (DROP, (0, -0.18, -0.03)), (100, (0, -0.1, -0.06), "io"), (LENGTH, (0, -0.1, -0.05)))
RIGHT_FOOT = T((0, (0, 0, 0)), (COIL + 1, (0, 0.02, 0)), (14, (0, -0.25, 0.12), "o"), (GRAB, (0, -0.48, 0), "i"),
               (DROP + 3, (0, -0.48, 0)), (DROP + 6, (0, -0.34, 0.08), "o"), (DROP + 9, (0, -0.2, 0), "i"), arc=True)
LEFT_FOOT = T((0, (0, 0, 0)), (COIL, (0, 0.04, 0)), (GRAB, (0, -0.04, 0), "o"))
FINGERS_R = T((0, 8), (COIL, -14), (15, -14), (GRAB, 58, "o3"), (DROP - 1, 58), (DROP + 1, -10, "o3"), (104, 10))
FINGERS_L = T((0, 8), (GRAB, 0, "o"), (LIFTED, 24), (50, 40), (PULL, 60), (DEATH, -10, "o3"), (80, 20), (104, 8))
LIFT = Vector((-0.04, -0.84, 1.66))  # his right hand, holding them up to his screen


def monster_body(an, f):
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS},
                    {f"Cable{i}": [("x", 8 * math.sin(math.pi * K.smoothstep(COIL, 30, f)) + 2 * math.sin(f / 9 + i))]
                     for i in (1, 2, 3)})
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (RIGHT_FOOT if side == "Right" else LEFT_FOOT)(f), 0.0, 0.06 * sx)


# ---------------------------------------------------------------- the player's key poses
FLINCH = KA.flinch_tracks(3, 13, "Left Leg", big=1.1)
H_ROT = T((GRAB, FLINCH["rot"](GRAB)), (20, (-16, 0, 6), "o3"), (24, (10, 0, -4), "o"), (LIFTED, (2, 0, 2)),
          (35, (-4, 3, -2)), (40, (3, -3, 2)), (45, (-3, 2, -2)), (50, (2, 0, 0)), (56, (0, 0, 0)),
          (PULL, (-6, 0, 0), "io"), (DEATH, (12, 0, 0), "o3"), (74, (4, 0, 0), "o"), (75, (10, 0, 0), "o"),
          (LIMP, (-4, 0, 2), "io"), (84, (2, 0, -2)), (DROP, (0, 0, 0)))
HEAD_H = T((GRAB, FLINCH["head"](GRAB)), (20, (20, 0, -6), "o3"), (24, (0, -12, 0)), (28, (0, 12, 0)),
           (LIFTED, (-6, 0, 0)), (40, (-4, -12, 4), "io"), (48, (-6, -14, 6)), (56, (-4, 12, -4), "io"),
           (64, (0, 4, 0), "io"), (DEATH, (30, 0, 0), "o3"), (74, (16, 0, 0)), (75, (28, 0, 0)),
           (LIMP, (-45, 10, 14), "o"), (DROP, (-40, 10, 14)))
LOOK = ((GRAB, "screen"), (LIMP - 3, "screen"), (LIMP, "ahead", "o"))
OUT_R, OUT_L = ((0.95, 0.15, -0.25), (0, 0.15, 0)), ((-0.95, 0.15, -0.25), (0, 0.15, 0))
ARMS = {
    "Right Arm": KA.PoseKeys(
        (GRAB, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3))), (GRAB + 3, ("wrist", (-0.25, 0.25, -0.45)), "o"),
        (26, ("wrist", (-0.2, 0.05, -0.4))), (30, ("wrist", (-0.25, 0.3, -0.45))), (34, ("wrist", (-0.2, 0.05, -0.4))),
        (38, ("screen", (-0.1, 0.4, -0.3))), (44, ("screen", (-0.05, 0.3, -0.35))), (50, ("screen", (-0.1, 0.45, -0.3))),
        (56, ("wrist", (-0.25, 0.2, -0.45))), (PULL, ("wrist", (-0.2, 0.1, -0.4))), (DEATH, OUT_R, "o3"),
        (74, ((0.8, -0.2, -0.3), (0, 0.1, 0)), "o"), (75, OUT_R, "o"), (LIMP, ((0.1, -1, -0.1), (0, 0, 0)), "i"),
        (DROP, ((0.12, -1, 0.05), (0, 0, 0)))),
    "Left Arm": KA.PoseKeys(
        (GRAB, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3))), (GRAB + 2, ("wrist", (0.25, 0.25, -0.45)), "o"),
        (25, ("wrist", (0.2, 0.35, -0.45))), (29, ("wrist", (0.25, 0.1, -0.4))), (33, ("wrist", (0.2, 0.3, -0.45))),
        (44, ("wrist", (0.25, 0.15, -0.4))), (52, ("screen", (0.1, 0.4, -0.3))), (60, ("screen", (0.05, 0.3, -0.35))),
        (PULL, ("wrist", (0.2, 0.2, -0.4))), (DEATH, OUT_L, "o3"), (74, ((-0.8, -0.2, -0.3), (0, 0.1, 0)), "o"),
        (75, OUT_L, "o"), (LIMP, ((-0.1, -1, -0.1), (0, 0, 0)), "i"), (DROP, ((-0.12, -1, 0.05), (0, 0, 0)))),
}
LEGS = {
    leg: KA.PoseKeys(
        (GRAB, (((-0.05, -0.95, 0.35) if leg == "Left Leg" else (0.05, -0.95, -0.3)), (0, 0, 0))),
        (GRAB + 3, ((sx * 0.06, -1, 0.0), (0, 0, 0)), "o"),
        *KA.kick_keys(leg, 22, 62, beat=5, a0=1.0, a1=0.45, phase=0 if leg == "Right Leg" else 1),
        (PULL, ((sx * 0.06, -1, 0.1), (0, 0, 0)), "io"), (DEATH, ((sx * 0.05, -1, 0.15), (0, 0, 0)), "o3"),
        (74, ((sx * 0.12, -0.9, -0.35), (0, 0.2, -0.05)), "o"), (75, ((sx * 0.05, -1, 0.15), (0, 0, 0)), "o"),
        (LIMP, ((sx * 0.06, -1, 0.05), (0, 0, 0)), "io"), (DROP, ((sx * 0.06, -1, 0.05), (0, 0, 0))))
    for leg, sx in (("Right Leg", 1), ("Left Leg", -1))
}


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    D = an.rest_delta("Head")
    screen = pl.point_to_victim(D @ SCREEN)
    if f <= GRAB:
        return KA.apply_flinch(va, f, FLINCH, look_at=screen)
    if f < DROP:
        grip = pl.point_to_victim(an.pb["RightHand"].matrix @ ctx["grip_local"])
        torso = va.torso_from_grip(grip, COLLAR, H_ROT(f))
        points = {"screen": screen, "ahead": torso @ Vector((0, 1.0, -6))}
        v = va.build(f, torso, head=HEAD_H(f), look_at=KA.look_blend(f, LOOK, points), lag={"head": 2})
        wrist = pl.point_to_victim(an.pb["RightLowerArm"].tail)
        elbow = pl.point_to_victim(an.pb["RightLowerArm"].head)
        down = Vector((0, -0.25, 0))
        side = D.to_3x3() @ Vector((0.12, 0, -0.08))  # toward the screen's corners (their right is +x)
        targets = {"Right Arm": {"wrist": wrist.lerp(elbow, 0.12) + down, "screen": pl.point_to_victim(D @ SCREEN + side)},
                   "Left Arm": {"wrist": wrist.lerp(elbow, 0.45) + down,
                                "screen": pl.point_to_victim(D @ SCREEN + Vector((-side.x, side.y, side.z)))}}
        KA.pose_limbs(va, v, f, ARMS, LEGS, targets)
        ctx["drop_torso"], ctx["drop_rot"], ctx["drop_limbs"] = torso, H_ROT(f), KA.limb_dirs(v)
        return v
    # dropped: the feet hit, the knees buckle, they tip back and slam down at his feet
    if "fall" not in ctx:
        ctx["fall"] = KA.fall_tracks(ctx["drop_torso"].translation.copy(), ctx["drop_rot"], DROP, "drop",
                                     land=(0.35, 1.7), yaw=-15, side=-1.0)
    return KA.apply_fall(va, f, ctx["fall"], ctx["drop_limbs"], look_at=screen)


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f)
    Tm = an.rest_delta("UpperTorso")
    if "hand_track" not in ctx:
        # where the collar will be at the grab, from the player's own (free) animation
        collar = pl.point_to_blender(KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH) @ COLLAR)
        r0 = an.pb["RightLowerArm"].bone.tail_local.copy()
        back = r0 + Vector((-0.08, 0.22, 0.12))
        ctx["hand_track"] = T((0, r0), (COIL, back), (COIL + 2, back + Vector((0, 0.02, 0.02))),
                              (15, (back + collar) / 2 + Vector((0, 0, 0.18)), "i"),
                              (GRAB, collar + Vector((0, 0.06, 0.02)), "o"), (20, collar + Vector((0, 0.1, -0.08)), "io"),
                              (24, collar.lerp(LIFT, 0.6) + Vector((0, 0.04, 0.12)), "o3"), (LIFTED, LIFT, "io"),
                              (50, LIFT + Vector((0, 0.02, 0.03))), (56, LIFT + Vector((0, 0.04, 0.03))),
                              (PULL, LIFT + Vector((0, 0.16, 0.04)), "io"), (DEATH, LIFT + Vector((0, 0.0, 0.06)), "o3"),
                              (LIMP, LIFT + Vector((0, 0.04, 0.04))), (86, LIFT + Vector((0, 0.04, 0.10)), "io"),
                              (DROP, LIFT + Vector((0.04, 0.02, 0.08))), (94, LIFT + Vector((0.04, -0.02, -0.06)), "o"),
                              (104, r0 + Vector((0, -0.2, 0.15)), "io"), (LENGTH, r0 + Vector((0, -0.15, 0.08))), arc=True)
    target = ctx["hand_track"](f)
    shake = Vector((0, 0, 0.004 * math.sin(f * 1.9))) * K.window(f, LIFTED, LIFTED + 6, DEATH, LIMP)
    hold = GRAB - 3 <= f <= DROP
    K.reach(an, "Right", target + shake, Tm.to_3x3() @ Vector((-0.8, 0.5, -0.6)),
            Vector((0.1, -0.85, -0.5)).normalized() if hold else None, Vector((0, -0.2, -1)))
    if f == GRAB:
        collar = pl.point_to_blender(KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH) @ COLLAR)
        ctx["grip_local"] = an.pb["RightHand"].matrix.inverted() @ collar
    pose = K.finger_curl(an, "Right", FINGERS_R(f), spread=8 * K.window(f, 4, COIL, GRAB - 1, GRAB))
    pose.update(K.finger_curl(an, "Left", FINGERS_L(f), spread=10 * K.window(f, DEATH - 1, DEATH, DEATH + 4, LIMP + 2)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    v = victim(an, ctx, f)
    if os.environ.get("KILL_DEBUG"):
        D = an.rest_delta("Head")
        print(f"DBG {f} screen-head {(D @ SCREEN - pl.to_blender(v.head_world()).translation).length:.2f} m")
    return v


NOTE = """CRT Man (Stand-In) kill, the player's half: InternalArmature carries the action
StandIn_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted so the
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
