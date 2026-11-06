#!/usr/bin/env python3
"""The Stand-In's kill (CRT Man), keyed pose to pose.

His monitor jerks round to the player. He draws himself up and back: chest back, the monitor
tipped back to look down at them, his right hand drawn back. A beat. Then one long lunge and he
seizes them by the collar, gathers them in and hoists them up to his screen at arm's length
(the game shows their avatar on it, with static getting louder). The monitor cocks slowly from
side to side, studying them, while they kick, pull at his wrist and shove at the screen. He
pulls them in close to it; the static peaks; they convulse and go limp. He holds the body up a
beat, tilting the monitor at it, lifts it a little and opens his hand. It drops, folds and
tips back at his feet; he steps back and looks down at it.

Writes the Stand-In's "Kill" action into the blend, and the player's half on the R6 rig
(export/StandIn_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of his, facing him. 130 frames at 30 fps.

Markers: Grab 17 (show the player's avatar on his screen, start the static; QTE starts),
Death 72 (static peaks; QTE ends), Drop 90, End 130.

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
import grip as G  # noqa: E402
import kill_core as K  # noqa: E402
from kill_anim import Track as T  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 130
COIL, GRAB, LIFTED, PULL, DEATH, LIMP, DROP = 10, 17, 30, 66, 72, 78, 90
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", LENGTH: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))
COLLAR = Vector((0.0, 0.85, -0.55))  # the front of their collar, in their torso's frame
# his grip on their collar: the palm flat on the top of their chest, the fingers up over the
# collar (the top edge of the torso) and hooked over it, beside the neck on their left, where his
# right hand lands (their torso's frame, studs)
GRIP_AT, GRIP_N, GRIP_ALONG = Vector((-0.62, 0.74, -0.5)), Vector((0, 0, -1)), Vector((0, 1, 0))
PALM = 0.022  # half the thickness of his hand (m)
SIDES = (("Left", 1.0), ("Right", -1.0))

# ---------------------------------------------------------------- his key poses
# world-axis degrees: x leans forward, y tips to his left, z turns his chest to his left
BODY = {
    "LowerTorso": T((0, (3, 0, 0)), (3, (2, 0, 0)), (COIL, (-6, 0, -6), "io"), (COIL + 2, (-7, 0, -7)),
                    (GRAB, (14, 0, 8), "o3"), (20, (16, 0, 6)), (LIFTED, (2, 0, 2), "io"), (50, (3, 0, 0)),
                    (PULL, (6, 0, 2), "io"), (DEATH, (0, 0, -2), "o3"), (84, (2, 0, 0)), (88, (0, 0, 0), "io"),
                    (DROP, (4, 0, 0), "o"), (104, (5, 0, 0), "io"), (LENGTH, (4, 0, 0))),
    "UpperTorso": T((0, (6, 0, 0)), (3, (4, 0, 0)), (COIL, (-12, 4, -14), "io"), (COIL + 2, (-13, 4, -15)),
                    (GRAB, (30, -2, 16), "o3"), (20, (32, 0, 12)), (LIFTED, (2, -4, 4), "io"), (44, (4, -2, 2)),
                    (56, (8, 0, 4)), (PULL, (14, 0, 6), "io"), (DEATH, (2, 0, 0), "o3"), (LIMP, (6, 0, 0)),
                    (88, (2, 0, 0), "io"), (DROP, (8, 0, 0), "o"), (104, (10, 0, -6), "io"), (LENGTH, (8, 0, -6))),
    # the monitor: jerks round, tips back, snaps down at them, then cocks slowly from side to
    # side studying them, with a sharp twitch now and then
    "Head": T((0, (6, 0, 0)), (3, (2, 12, 0), "o3"), (COIL, (-16, 4, 0)), (COIL + 2, (-18, 4, 0)), (GRAB, (22, 0, 0), "o3"),
              (24, (34, 8, 0), "o"), (LIFTED, (38, 12, 0)), (38, (38, -12, 2), "io"), (44, (38, -12, 2)),
              (45, (40, -12, 10), "o"), (48, (38, -10, 2), "io"), (56, (40, 14, 0), "io"), (PULL, (34, 4, 0)),
              (DEATH, (28, 0, 0), "o3"), (74, (40, 10, 0), "o"), (80, (40, 18, 0), "io"), (88, (40, 18, 0)),
              (DROP, (40, 8, 0)), (104, (8, 14, 0), "io"), (118, (6, 22, 0), "io"), (LENGTH, (6, 18, 0))),
    "LeftUpperArm": T((0, (-2, 3, 0)), (COIL, (16, 3, 0), "io"), (GRAB, (-24, 8, 0), "o3"), (LIFTED, (-6, 14, 0), "io"),
                      (PULL, (-4, 10, 0)), (DEATH, (-10, 18, 0), "o3"), (DROP, (0, 6, 0)), (104, (2, 3, 0), "io")),
    "LeftLowerArm": T((0, (-6, 0, 0)), (COIL, (-20, 0, 0)), (GRAB, (-10, 0, 0), "o"), (LIFTED, (-24, 0, 0)),
                      (DEATH, (-30, 0, 0), "o3"), (DROP, (-10, 0, 0)), (LENGTH, (-12, 0, 0))),
}
LAGS = {"UpperTorso": 1, "Head": 2, "LeftUpperArm": 2, "LeftLowerArm": 4}
PELVIS = T((0, (0, 0, 0)), (COIL, (0, 0.06, -0.03), "io"), (COIL + 2, (0, 0.07, -0.04)), (GRAB, (0, -0.26, -0.1), "o3"),
           (20, (0, -0.24, -0.12)), (LIFTED, (0, -0.18, -0.03), "io"), (PULL, (0, -0.16, -0.04)),
           (DROP, (0, -0.18, -0.03)), (100, (0, -0.1, -0.01), "io"), (LENGTH, (0, -0.1, 0.0)))
RIGHT_FOOT = T((0, (0, 0, 0)), (COIL + 1, (0, 0.02, 0)), (14, (0, -0.25, 0.12), "o"), (GRAB, (0, -0.48, 0), "i"),
               (DROP + 3, (0, -0.48, 0)), (DROP + 6, (0, -0.34, 0.08), "o"), (DROP + 9, (0, -0.2, 0), "i"), arc=True)
LEFT_FOOT = T((0, (0, 0, 0)), (COIL, (0, 0.04, 0)), (GRAB, (0, -0.04, 0), "o"))
FINGERS_R = T((0, 8), (COIL, -14), (15, -14), (GRAB, 58, "o3"), (DROP - 1, 58), (DROP + 1, -10, "o3"), (104, 10))
FINGERS_L = T((0, 8), (GRAB, 0, "o"), (LIFTED, 24), (50, 40), (PULL, 60), (DEATH, -10, "o3"), (80, 20), (104, 8))
LIFT = Vector((-0.04, -0.84, 1.66))  # his right hand, holding them up to his screen


SCREEN_N = Vector((0.0, -1.0, 0.0))
AIM = T((0, 0.0), (DROP, 0.0), (DROP + 12, 1.0, "io"), (LENGTH, 1.0))  # the screen on the body, once it's down


def monster_body(an, f, ctx):
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS},
                    {f"Cable{i}": [("x", 8 * math.sin(math.pi * K.smoothstep(COIL, 30, f)) + 2 * math.sin(f / 9 + i))]
                     for i in (1, 2, 3)})
    if "vhead" in ctx and AIM(f) > 0:
        KA.aim_bone(an, "Head", SCREEN, SCREEN_N, KA.follow(ctx, "aim", ctx["vhead"], 0.3), AIM(f), max_deg=70)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (RIGHT_FOOT if side == "Right" else LEFT_FOOT)(f), 0.0, 0.06 * sx)


# ---------------------------------------------------------------- the player's key poses
FLINCH = KA.flinch_tracks(3, 13, "Left Leg", big=1.1)
# The whole body is keyed on the same frames (the key poses), so on the R6 rig Blender eases between
# whole poses:  17 grabbed  23 hoisted, hands on his wrist  30-60 kicking; pushing at his screen
#   66 pulled in to it  72 the static peaks (held)  75 the death spasm  78 limp  84 hanging  90 dropped
H_ROT = T((GRAB, FLINCH["rot"](GRAB)), (23, (-12, 0, 5), "io"), (LIFTED, (4, 0, -2), "io"), (36, (-4, 3, -2), "io"),
          (42, (3, -3, 2), "io"), (48, (-3, 2, -2), "io"), (54, (2, 0, 0), "io"), (60, (0, 0, 0), "io"),
          (PULL, (-6, 0, 0), "io"), (DEATH, (-6, 0, 0)), (75, (12, 0, 0), "o"), (LIMP, (-4, 0, 2), "io"),
          (84, (2, 0, -2), "io"), (DROP, (0, 0, 0), "io"))
HEAD_H = T((GRAB, FLINCH["head"](GRAB)), (23, (18, 0, -6), "io"), (LIFTED, (-6, 0, 0), "io"), (36, (-4, -12, 4), "io"),
           (42, (-6, -14, 6), "io"), (48, (-4, 12, -4), "io"), (54, (-2, 8, 0), "io"), (60, (0, 4, 0), "io"),
           (PULL, (0, 4, 0)), (DEATH, (0, 4, 0)), (75, (30, 0, 0), "o"), (LIMP, (-45, 10, 14), "io"),
           (84, (-42, 10, 14), "io"), (DROP, (-40, 10, 14), "io"))
LOOK = ((GRAB, "screen"), (75, "screen"), (LIMP, "ahead", "io"))
OUT_R, OUT_L = ((0.95, 0.15, -0.25), (0, 0.15, 0)), ((-0.95, 0.15, -0.25), (0, 0.15, 0))
HANG_R, HANG_L = ((0.1, -1, -0.05), (0, 0, 0)), ((-0.1, -1, -0.05), (0, 0, 0))
ARMS = {
    "Right Arm": KA.PoseKeys(
        (GRAB, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3))), (23, ("wrist", (-0.25, 0.25, -0.45)), "io"),
        (LIFTED, ("wrist", (-0.2, 0.05, -0.4)), "io"), (36, ("screen", (-0.1, 0.4, -0.3)), "io"),
        (42, ("screen", (-0.05, 0.3, -0.35)), "io"), (48, ("screen", (-0.1, 0.45, -0.3)), "io"),
        (54, ("wrist", (-0.25, 0.2, -0.45)), "io"), (60, ("wrist", (-0.2, 0.1, -0.4)), "io"),
        (PULL, ("wrist", (-0.2, 0.1, -0.4)), "io"), (DEATH, ("wrist", (-0.2, 0.1, -0.4))), (75, OUT_R, "o"),
        (LIMP, HANG_R, "io"), (84, HANG_R), (DROP, HANG_R)),
    "Left Arm": KA.PoseKeys(
        (GRAB, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3))), (23, ("wrist", (0.25, 0.25, -0.45)), "io"),
        (LIFTED, ("wrist", (0.2, 0.35, -0.45)), "io"), (36, ("wrist", (0.25, 0.1, -0.4)), "io"),
        (42, ("wrist", (0.2, 0.3, -0.45)), "io"), (48, ("screen", (0.1, 0.4, -0.3)), "io"),
        (54, ("screen", (0.05, 0.3, -0.35)), "io"), (60, ("screen", (0.1, 0.4, -0.3)), "io"),
        (PULL, ("wrist", (0.2, 0.2, -0.4)), "io"), (DEATH, ("wrist", (0.2, 0.2, -0.4))), (75, OUT_L, "o"),
        (LIMP, HANG_L, "io"), (84, HANG_L), (DROP, HANG_L)),
}
LEGS = {
    leg: KA.PoseKeys(
        (GRAB, (((-0.05, -0.95, 0.35) if leg == "Left Leg" else (0.05, -0.95, -0.3)), (0, 0, 0))),
        (23, ((sx * 0.06, -1, 0.0), (0, 0, 0)), "io"),
        *KA.kick_keys(leg, LIFTED, 60, beat=6, a0=1.0, a1=0.45, phase=0 if leg == "Right Leg" else 1),
        (PULL, ((sx * 0.06, -1, 0.1), (0, 0, 0)), "io"), (DEATH, ((sx * 0.06, -1, 0.1), (0, 0, 0))),
        (75, ((sx * 0.05, -1, 0.2), (0, 0, 0)), "o"), (LIMP, ((sx * 0.06, -1, 0.05), (0, 0, 0)), "io"),
        (84, ((sx * 0.06, -1, 0.05), (0, 0, 0))), (DROP, ((sx * 0.06, -1, 0.05), (0, 0, 0))))
    for leg, sx in (("Right Leg", 1), ("Left Leg", -1))
}
# the key poses on the R6 rig (Blender eases between them) and the hits (hard stops)
R6_KEYS = (3, 5, 8, 13, GRAB, 23, LIFTED, 36, 42, 48, 54, 60, PULL, DEATH, 75, LIMP, 84, DROP)
R6_SHARP = (DEATH,)


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    D = an.rest_delta("Head")
    screen = pl.point_to_victim(D @ SCREEN)
    if f <= GRAB:
        return KA.apply_flinch(va, f, FLINCH, look_at=screen)
    if f < DROP:
        # hanging from his grip: the spot on their chest under his palm
        R = KA.euler(H_ROT(f))
        torso = Matrix.Translation(ctx["palm_v"] - R.to_3x3() @ GRIP_AT) @ R
        if f < GRAB + 4:  # yanked into his hand from where they stood
            t0 = KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH).translation
            torso.translation = t0.lerp(torso.translation, K.smoothstep(GRAB, GRAB + 4, f))
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
                                     land=(0.35, 2.8), yaw=-15, side=-1.0, look_at=screen,
                                     start_limbs=ctx["drop_limbs"])
    return KA.apply_fall(va, f, ctx["fall"])


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f, ctx)
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
                              (104, r0 + Vector((0, -0.06, 0.06)), "io"), (LENGTH, r0 + Vector((0, -0.04, 0.03))), arc=True)
    target = ctx["hand_track"](f)
    shake = Vector((0, 0, 0.004 * math.sin(f * 1.9))) * K.window(f, LIFTED, LIFTED + 6, DEATH, LIMP)
    hold = K.smoothstep(GRAB - 3, GRAB, f) * (1 - K.smoothstep(DROP, DROP + 3, f))
    pole = Tm.to_3x3() @ Vector((-0.8, 0.5, -0.6))
    if hold > 0:
        # the hand turned to their chest: palm on it, fingers pointing up over the collar
        r3 = pl.to_blender(KA.euler(H_ROT(max(f, GRAB)))).to_3x3().normalized()
        n, along = r3 @ GRIP_N, r3 @ GRIP_ALONG
        K.reach(an, "Right", target + shake, pole, Vector((0, -0.2, -1)).lerp(along, hold).normalized(),
                Vector((0, -1, 0)).lerp(-n, hold).normalized())
        ctx["palm_v"] = pl.point_to_victim(G.palm(an, "Right", PALM)[0])
    else:
        K.reach(an, "Right", target + shake, pole)
    pose = K.finger_curl(an, "Right", FINGERS_R(f), spread=8 * K.window(f, 4, COIL, GRAB - 1, GRAB))
    pose.update(K.finger_curl(an, "Left", FINGERS_L(f), spread=10 * K.window(f, DEATH - 1, DEATH, DEATH + 4, LIMP + 2)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    v = victim(an, ctx, f)
    if hold > 0:  # his fingers close round the collar until they touch
        body = G.Body(pl, v.parts(), KM)
        curls = G.wrap_fingers(an, "Right", body, spread=3.0, weight=hold, open_curl=-15, margin=0.004)
        if os.environ.get("KILL_DEBUG") and f in (30, 60):
            pp, d, faces = G.palm(an, "Right", PALM)
            print("GRIP", f, "palm to chest", round(body.distance(pp, ["Torso"]) / KM, 2), "studs; palm local",
                  tuple(round(x, 2) for x in body.inv["Torso"] @ pp), "curls", {k: [round(x) for x in c] for k, c in curls.items()},
                  "tips", {fn: round(body.distance(G._chain(an, "Right", fn)[-1].tail) / KM, 2) for fn in G.FINGERS})
    ctx["vhead"] = pl.to_blender(v.head_world()).translation
    if os.environ.get("KILL_DEBUG"):
        D = an.rest_delta("Head")
        print(f"DBG {f} screen-head {(D @ SCREEN - pl.to_blender(v.head_world()).translation).length:.2f} m")
    return v


NOTE = """CRT Man (Stand-In) kill, the player's half: InternalArmature carries the action
StandIn_Kill_Victim (30 fps, frames 0-130). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (show the
player's avatar on his screen, start the static), Death, Drop, End.
The 'Monster (reference)' collection holds the CRT Man playing his half, at your in-game size,
lined up where the game should put him: 3.6 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "StandIn_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "StandIn_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    fall = ctx["fall"]
    K.write_r6_blend(template, os.path.join(export_dir, "StandIn_Kill_Victim.blend"), ctx["parts"], "StandIn_Kill_Victim",
                     MARKERS, (blend, "StandIn_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE,
                     keys=set(R6_KEYS) | K.key_frames(fall), sharp=set(R6_SHARP) | set(fall["impact"]))
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
