#!/usr/bin/env python3
"""The Receiver's kill, keyed pose to pose.

His phone head snaps round to the player. He coils: chest back, hips turned, his left arm drawn
back with the fingers splayed. Then he lunges with one long step and seizes them by the neck,
straightens up and hoists them off their feet while they kick and pull at his wrist. He winds
the claw right back: his whole body twists away, the arm cocked high behind his shoulder, the
claw aimed at them. They see it and reach out at it. He holds it, trembling, then drives it
through their chest. Their body jolts back, the knees jerk up; they grab at the arm in them and
look down at it. He twists it. They go slack. He pushes it in once more, rips it out with a wide
sweep, swings them across and flings them aside, then flicks the claw clean and watches them.

Writes the Receiver's "Kill" action into the blend, and the player's half on the R6 rig
(export/Receiver_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of his, facing him. 120 frames at 30 fps.

Markers: Grab 16 (QTE starts), Stab 43 (blood on the player's screen; QTE ends), RipOut 68,
Drop 74, End 120.

Usage: python3 receiver_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
"""
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

HEIGHT_M, HEIGHT_STUDS = 2.2825, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.8
LENGTH = 120
COIL, GRAB, LIFTED, WIND, STAB, TWIST, RIP, DROP = 9, 16, 27, 40, 43, 54, 68, 74
MARKERS = {GRAB: "Grab", STAB: "Stab", RIP: "RipOut", DROP: "Drop", LENGTH: "End"}
SOCKET = Vector((0.0, -0.43, 2.11))
SOCKET_N = Vector((0.0, -0.965, 0.262))
NECK = Vector((0.0, 1.0, -0.45))  # the front of their neck, in their torso's frame
CHEST_IN = Vector((0.0, 0.2, -0.05))  # where his wrist ends up: in the middle of their chest
SIDES = (("Left", 1.0), ("Right", -1.0))

# ---------------------------------------------------------------- his key poses
# world-axis degrees: x leans forward, y tips to his left, z turns his chest to his left
BODY = {
    "LowerTorso": T((0, (2, 0, 0)), (COIL, (-6, 0, 8)), (COIL + 3, (-7, 0, 9)), (GRAB, (12, 0, -10), "o3"),
                    (LIFTED, (0, 0, -4)), (34, (-2, 0, -10)), (WIND, (-4, 2, -18), "i"), (STAB, (9, 0, 12), "o5"),
                    (46, (7, 0, 9)), (57, (0, 0, 9), "io"), (RIP - 2, (6, 0, 13)), (RIP, (4, 0, -12), "o3"), (DROP - 2, (2, 0, -15), "io"),
                    (DROP, (8, 0, 16), "o3"), (82, (8, 0, 10)), (96, (6, 0, 4)), (LENGTH, (5, 0, 2))),
    "UpperTorso": T((0, (4, 0, 0)), (COIL, (-14, -4, 18), "io"), (COIL + 3, (-15, -4, 20)), (GRAB, (18, 0, -22), "o3"),
                    (LIFTED, (-2, 6, -6), "io"), (34, (-4, 4, -22)), (WIND, (-10, 6, -42), "i"),
                    (STAB, (12, -4, 28), "o5"), (46, (8, -2, 22)), (TWIST, (4, 2, 24)), (57, (-2, 4, 22), "io"), (RIP - 2, (6, 0, 26)),
                    (RIP, (6, 0, -20), "o3"), (DROP - 2, (4, 0, -28), "io"), (DROP, (14, 0, 28), "o3"),
                    (82, (14, 0, 16)), (96, (12, 0, 4)), (LENGTH, (10, 0, 0))),
    # the phone head: keyed cocks on top of staying aimed at the player (AIM)
    "Head": T((0, (0, 0, 0)), (2, (-8, -16, 0), "o3"), (COIL, (-10, -10, 0)), (GRAB, (-12, 10, 0), "o3"),
              (LIFTED, (-6, 22, 0), "io"), (34, (-6, 12, 0)), (WIND, (-6, -16, 0)), (STAB, (-14, 0, 0), "o3"),
              (48, (-14, 24, 0), "io"), (TWIST, (-12, -18, 0), "o"), (62, (-12, 16, 0)), (RIP, (-6, 0, 0)),
              (DROP, (0, 0, 0)), (90, (0, 20, 0), "io"), (104, (0, 26, 0)), (LENGTH, (0, 30, 0))),
}
LAGS = {"UpperTorso": 1, "Head": 2}
AIM = T((0, 0.4), (3, 1.0, "o3"), (LENGTH, 1.0))
PELVIS = T((0, (0, 0, 0)), (COIL, (0, 0.08, -0.08)), (COIL + 3, (0, 0.09, -0.09)), (GRAB, (0, -0.26, -0.12), "o3"),
           (LIFTED, (0, -0.18, 0.0), "io"), (WIND, (0, -0.08, -0.05), "i"), (STAB, (0, -0.22, -0.10), "o5"),
           (RIP - 2, (0, -0.22, -0.09)), (RIP, (0, -0.22, -0.06), "o3"), (DROP, (0.04, -0.24, -0.07), "o3"),
           (100, (0, -0.22, -0.04)))
LEFT_FOOT = T((0, (0, 0, 0)), (COIL + 2, (0, 0.02, 0)), (13, (0, -0.2, 0.14), "o"), (GRAB, (0, -0.44, 0), "i"), arc=True)
RIGHT_FOOT = T((0, (0, 0, 0)), (COIL, (0, 0.04, 0)), (GRAB, (0, -0.06, 0), "o"), (STAB, (0, -0.12, 0), "o"))
FINGERS_R = T((0, 6), (WIND - 8, 0), (WIND, -22, "i"), (STAB - 1, -12), (STAB, -6, "o"), (RIP + 2, -12),
              (72, 20, "o"), (86, 30), (89, -6, "o3"), (93, 26, "o"), (97, -4, "o3"), (LENGTH, 12))
FINGERS_L = T((0, 6), (COIL, -22), (GRAB - 1, -22), (GRAB, 50, "o3"), (DROP - 1, 50), (DROP + 1, -14, "o3"), (90, 8))
HOLD = Vector((0.14, -1.12, 1.46))  # where his left hand holds their neck once they're up


def dial(t):
    """The dial in his chest dialling after the stab: pulled round fast, whirring back."""
    out = 0.0
    for pull in (300, 180, 270):
        span = 5 + 1 + pull / 20.0 + 3
        if t < 0:
            return out
        if t < span:
            if t < 5:
                return -pull * A.ease(t / 5)
            return -pull + min(pull, max(0.0, t - 6) * 20.0)
        t -= span
    return 0.0


def monster_body(an, f, ctx):
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS}, {"DialSpin": [("ly", dial(f - STAB - 3))]})
    if "vhead" in ctx:  # the socket stays on the player's face (smoothed, so a jolt can't whip it)
        KA.aim_bone(an, "Head", SOCKET, SOCKET_N, KA.follow(ctx, "aim", ctx["vhead"], 0.4), AIM(f), max_deg=45)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (LEFT_FOOT if side == "Left" else RIGHT_FOOT)(f), 0.0, 0.14 * sx)


# ---------------------------------------------------------------- the player's key poses
FLINCH = KA.flinch_tracks(2, 12, "Right Leg")
# held by the neck (+pitch tips the top back, +yaw turns to their left)
H_ROT = T((GRAB, FLINCH["rot"](GRAB)), (19, (-14, -4, 6), "o3"), (23, (8, 2, -4), "o"), (LIFTED, (0, 0, 3)),
          (31, (-5, 4, -3)), (35, (3, 8, 3)), (WIND, (-2, 14, 0)), (STAB, (-24, 4, -2), "o5"), (47, (8, 2, 2), "io"),
          (51, (2, 0, 0)), (TWIST, (-12, -8, 6), "o3"), (58, (4, -2, -2), "io"), (64, (6, 0, -4)),
          (RIP - 2, (-6, 0, -2), "o"), (RIP, (16, 0, 2), "o3"), (71, (4, 0, 0), "io"), (DROP, (-6, 0, 4)))
HEAD_H = T((GRAB, FLINCH["head"](GRAB)), (19, (16, 0, -6), "o3"), (24, (8, -12, 4)), (28, (10, 12, -4)),
           (32, (6, 0, 0)), (WIND, (10, 0, 0)), (STAB, (8, 0, 0), "o5"), (47, (0, 0, 0)), (52, (-30, 8, 10)),
           (TWIST, (10, 0, -6), "o3"), (58, (-20, -8, 10)), (64, (-40, 6, 20)), (RIP, (-10, 0, 0), "o"),
           (DROP, (-30, 0, 10)))
LOOK = ((GRAB, "phone"), (31, "phone"), (35, "claw", "io"), (WIND, "claw"), (STAB, "wound", "o3"), (50, "wound"),
        (60, "ahead", "io"))
# hands: on his wrist, reaching at the cocked claw, flung out by the stab, grabbing the arm in
# them, slipping off ("wrist", "reach", "claw" are worked out each frame)
ARMS = {
    "Right Arm": KA.PoseKeys(
        (GRAB, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3))), (GRAB + 3, ("wrist", (-0.25, 0.25, -0.45)), "o"),
        (23, ("wrist", (-0.2, 0.05, -0.4))), (26, ("wrist", (-0.25, 0.3, -0.45))), (30, ("wrist", (-0.2, 0.05, -0.4))),
        (34, ("reach", (-0.1, 0.35, -0.3)), "o"), (WIND, ("reach", (-0.05, 0.45, -0.25))),
        (STAB, ((0.85, 0.3, -0.4), (0, 0.2, 0)), "o3"), (47, ("claw", (-0.2, 0.15, -0.45)), "o"),
        (TWIST, ("claw", (-0.15, 0.1, -0.4))), (56, ((0.5, -0.6, -0.5), (0, 0.1, 0)), "o"),
        (60, ("claw", (-0.1, 0.0, -0.3))), (65, ((0.12, -1, -0.15), (0, 0, 0)), "i"),
        (RIP, ((0.1, -0.8, -0.6), (0, 0, 0)), "o"), (DROP, ((0.2, -0.9, -0.3), (0, 0, 0)))),
    "Left Arm": KA.PoseKeys(
        (GRAB, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3))), (GRAB + 2, ("wrist", (0.25, 0.25, -0.45)), "o"),
        (22, ("wrist", (0.2, 0.35, -0.45))), (27, ("wrist", (0.25, 0.1, -0.4))), (31, ("wrist", (0.2, 0.3, -0.45))),
        (WIND, ("wrist", (0.2, 0.15, -0.4))), (STAB, ((-0.85, 0.35, -0.35), (0, 0.2, 0)), "o3"),
        (46, ((-0.7, 0.0, -0.5), (0, 0.1, 0))), (50, ("wrist", (0.2, 0.1, -0.4))),
        (TWIST, ((-0.6, 0.1, -0.6), (0, 0.1, 0)), "o"), (58, ("wrist", (0.15, 0.0, -0.3))),
        (63, ((-0.1, -1, -0.1), (0, 0, 0)), "i"), (RIP, ((-0.1, -0.8, -0.55), (0, 0, 0)), "o"),
        (DROP, ((-0.2, -0.9, -0.3), (0, 0, 0)))),
}
HANGL = {"Right Leg": ((0.06, -1, 0.1), (0, 0, 0)), "Left Leg": ((-0.06, -1, 0.1), (0, 0, 0))}
LEGS = {
    leg: KA.PoseKeys(
        (GRAB, (((0.05, -0.95, 0.35) if leg == "Right Leg" else (-0.05, -0.95, -0.3)), (0, 0, 0))),
        (GRAB + 3, ((sx * 0.06, -1, 0.0), (0, 0, 0)), "o"),
        *KA.kick_keys(leg, 19, 39, beat=4, a0=1.0, a1=0.85, phase=0 if leg == "Right Leg" else 1),
        (STAB, ((sx * 0.12, -0.5, -0.85), (0, 0.5, -0.15)), "o3"), (46, ((sx * 0.1, -0.6, -0.8), (0, 0.45, -0.12))),
        (51, HANGL[leg], "io"),
        (TWIST, (((0.12, -0.65, -0.7), (0, 0.35, -0.1)) if leg == "Right Leg" else ((-0.05, -1, -0.2), (0, 0, 0))), "o3"),
        (58, HANGL[leg], "io"), (64, ((sx * 0.05, -1, 0.05), (0, 0, 0))), (RIP, ((sx * 0.05, -0.95, 0.3), (0, 0, 0)), "o"),
        (DROP, ((sx * 0.05, -1, 0.0), (0, 0, 0))))
    for leg, sx in (("Right Leg", 1), ("Left Leg", -1))
}


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    socket = pl.point_to_victim(an.rest_delta("Head") @ SOCKET)
    if f <= GRAB:
        return KA.apply_flinch(va, f, FLINCH, look_at=socket)
    if f < DROP:
        grip = pl.point_to_victim(an.pb["LeftHand"].matrix @ ctx["grip_local"])
        torso = va.torso_from_grip(grip, NECK, H_ROT(f))
        wrist = pl.point_to_victim(an.pb["LeftLowerArm"].tail)
        elbow = pl.point_to_victim(an.pb["LeftLowerArm"].head)
        claw = ctx.get("claw_v", wrist)  # his claw arm, last frame (it's posed after them)
        points = {"phone": socket, "claw": ctx.get("claw_tip_v", socket),
                  "wound": torso @ Vector((0, 0.1, -1.7)), "ahead": torso @ Vector((0, 1.0, -6))}
        v = va.build(f, torso, head=HEAD_H(f), look_at=KA.look_blend(f, LOOK, points), lag={"head": 2})
        down = Vector((0, -0.25, 0))
        targets = {"Right Arm": {"wrist": wrist.lerp(elbow, 0.12) + down, "claw": claw + down,
                                 "reach": ctx.get("claw_tip_v", socket)},
                   "Left Arm": {"wrist": wrist.lerp(elbow, 0.45) + down, "claw": claw + down,
                                "reach": ctx.get("claw_tip_v", socket)}}
        KA.pose_limbs(va, v, f, ARMS, LEGS, targets)
        ctx["drop_torso"], ctx["drop_rot"] = torso, H_ROT(f)
        ctx["drop_limbs"] = KA.limb_dirs(v)
        return v
    # flung aside to his left (their right): tumbling, onto their back, a bounce and a slide
    if "fall" not in ctx:
        ctx["fall"] = KA.fall_tracks(ctx["drop_torso"].translation.copy(), ctx["drop_rot"], DROP, "thrown",
                                     land=(2.8, 0.9), yaw=70, side=1.0)
    return KA.apply_fall(va, f, ctx["fall"], ctx["drop_limbs"], look_at=socket)


# his claw: Tm-relative points (vectors) or worked-out ones (names), armature space
CLAW = KA.Live(
    (0, (-0.48, -0.14, 1.0)), (COIL, (-0.46, -0.24, 1.04)), (GRAB, (-0.5, 0.06, 1.02), "o"), (LIFTED, (-0.5, 0.0, 1.05)),
    (32, (-0.64, 0.18, 1.5), "i"), (37, (-0.5, 0.40, 2.02), "io"), (WIND, (-0.46, 0.47, 2.13), "i"),
    (WIND + 1.6, "strike", "i"), (STAB, "through", "o"), (STAB + 1, "deeper", "o"), (STAB + 3, "through", "io"),
    (RIP - 4, "through"), (RIP - 2, "deeper", "io"), (RIP, "out", "o3"), (72, (-0.78, 0.06, 1.45), "o"),
    (80, (-0.6, -0.1, 1.2), "io"), (86, (-0.58, -0.2, 1.4), "io"), (89, (-0.62, -0.12, 0.96), "o3"),
    (94, (-0.55, -0.15, 1.08), "io"), (LENGTH, (-0.52, -0.18, 1.04)), arc=True)


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f, ctx)
    Tm = an.rest_delta("UpperTorso")
    # the left hand: drawn back, lunges for the neck, hoists them, flings them away
    if "hand_track" not in ctx:
        neck = pl.point_to_blender(KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH) @ NECK)
        r0 = an.pb["LeftLowerArm"].bone.tail_local.copy()
        L = HOLD
        ctx["hand_track"] = T((0, r0), (COIL, Vector((0.6, 0.25, 1.24))), (COIL + 3, Vector((0.62, 0.28, 1.27))),
                              (14, (Vector((0.62, 0.28, 1.27)) + neck) / 2 + Vector((0.06, 0, 0.12)), "i"),
                              (GRAB, neck + Vector((0.02, 0.05, 0)), "o"), (20, neck.lerp(L, 0.6) + Vector((0, -0.04, 0.1)), "o3"),
                              (LIFTED, L, "io"), (31, L + Vector((0, 0.02, 0.02))), (WIND, L + Vector((0.02, 0.04, 0.03))),
                              (STAB, L + Vector((0, -0.16, 0.0)), "o3"), (48, L + Vector((0, -0.12, 0))),
                              (57, L + Vector((0, -0.1, 0.14)), "io"), (RIP - 2, L + Vector((0, -0.11, 0.12))), (RIP, L + Vector((0, -0.02, 0.1)), "o3"),
                              (DROP - 2, L + Vector((-0.12, 0.02, 0.06)), "io"), (DROP, L + Vector((0.4, -0.05, -0.1)), "o3"),
                              (80, L + Vector((0.55, 0.05, -0.35)), "o"), (92, r0 + Vector((0.12, -0.1, 0.05)), "io"),
                              (LENGTH, r0 + Vector((0.02, -0.04, 0.02))), arc=True)
    hold = GRAB - 2 <= f <= DROP
    K.reach(an, "Left", ctx["hand_track"](f), Tm.to_3x3() @ Vector((0.8, 0.3, -0.6)),
            Vector((-0.5, -0.75, 0.2)).normalized() if hold else None, Vector((0, -1, 0)))
    if f == GRAB:
        neck = pl.point_to_blender(KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH) @ NECK)
        ctx["grip_local"] = an.pb["LeftHand"].matrix.inverted() @ neck
    v = victim(an, ctx, f)
    # the claw: cocked far back, driven through their chest, held, twisted, ripped out, flicked
    if f < DROP:
        tb = pl.to_blender(v.torso)
        sdir = (tb.to_3x3() @ Vector((0, 0, 1))).normalized()  # through them, front to back
        through = tb @ CHEST_IN
        cocked = an.rest_delta("UpperTorso") @ Vector((-0.46, 0.47, 2.13))
        ctx["named"] = {"through": through, "deeper": through + sdir * 0.06, "out": tb @ Vector((0, 0.2, -2.6)),
                        "strike": (cocked + through) / 2 + Vector((0, 0, 0.18))}
        ctx["sdir"] = sdir
    named = ctx["named"]
    target = CLAW(f, lambda x: named[x] if isinstance(x, str) else Tm @ Vector(x))
    cock = K.window(f, 28, 34, WIND, STAB)
    pole = Tm.to_3x3() @ Vector((-0.8, 0.4, -0.4)).lerp(Vector((-0.6, 0.7, 0.4)), cock)
    hand_dir, palm = None, Vector((0, 0, -1))
    if 30 <= f < STAB:  # aimed at them
        aim = (pl.point_to_blender(v.torso @ CHEST_IN) - target).normalized()
        hand_dir = aim.lerp(Vector((0, 0, -1)), 1 - K.smoothstep(30, 36, f)).normalized()
    elif STAB <= f < RIP + 2:
        hand_dir = ctx["sdir"]
        twist = K.smoothstep(TWIST - 2, TWIST + 1, f)  # he turns the claw in them
        palm = Vector((0, 0, -1)).lerp(Vector((-1, 0, 0)), twist).normalized()
    K.reach(an, "Right", target, pole, hand_dir, palm)
    pose = K.finger_curl(an, "Right", FINGERS_R(f), spread=-8 * K.window(f, 30, 36, STAB - 1, STAB + 2))
    pose.update(K.finger_curl(an, "Left", FINGERS_L(f), spread=10 * K.window(f, 4, COIL, GRAB - 1, GRAB)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    import bpy as _b
    _b.context.view_layer.update()
    ctx["claw_v"] = pl.point_to_victim(an.pb["RightLowerArm"].head.lerp(an.pb["RightLowerArm"].tail, 0.7))
    ctx["claw_tip_v"] = pl.point_to_victim(an.pb["RightHand"].tail)
    ctx["vhead"] = pl.to_blender(v.head_world()).translation
    if os.environ.get("KILL_DEBUG"):
        D = an.pb["Head"].matrix @ an.pb["Head"].bone.matrix_local.inverted()
        d = (D @ SOCKET - ctx["vhead"]).length
        print(f"DBG {f} socket-head {d:.2f} m")
    return v


NOTE = """Receiver kill, the player's half: InternalArmature carries the action
Receiver_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab, Stab (blood on
the player's screen), RipOut, Drop, End.
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
