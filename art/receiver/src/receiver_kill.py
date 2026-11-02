#!/usr/bin/env python3
"""The Receiver's kill, keyed pose to pose.

His phone head snaps round to the player and he coils, then lunges and seizes them by the neck
with his left hand, hoisting them onto their toes. He winds his claw far back, twisting his
whole body away, and drives it through their torso. They fold over it and look down at it. He
leans his phone head in close, the dial in his chest spinning, then rips the claw out and flings
them aside, and flicks the claw clean.

Writes the Receiver's "Kill" action into the blend, and the player's half on the R6 rig
(export/Receiver_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of his, facing him. 100 frames at 30 fps.

Markers: Grab 12 (QTE starts), Stab 35 (blood on the player's screen; QTE ends), RipOut 62,
Drop 66, End 100.

Usage: python3 receiver_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
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

HEIGHT_M, HEIGHT_STUDS = 2.2825, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.8
LENGTH = 100
GRAB, LIFTED, WIND, STAB, RIP, DROP, LAND = 12, 22, 32, 35, 62, 66, 78
MARKERS = {GRAB: "Grab", STAB: "Stab", RIP: "RipOut", DROP: "Drop", LENGTH: "End"}
SOCKET = Vector((0.0, -0.43, 2.11))
NECK = Vector((0.0, 1.0, -0.4))  # the front of their neck, in their torso's frame
CHEST_IN = Vector((0.0, 0.2, -0.05))  # where his wrist ends up: in the middle of their chest
SIDES = (("Left", 1.0), ("Right", -1.0))

BODY = {
    "LowerTorso": T((0, (2, 0, 0)), (6, (8, 0, 6)), (GRAB, (14, 0, -6), "o3"), (LIFTED, (4, 0, -4)),
                    (WIND, (6, 0, -10), "i"), (STAB, (12, 0, 8), "o5"), (44, (10, 0, 5)), (RIP - 2, (12, 0, 7)),
                    (RIP + 2, (4, 0, -8), "o3"), (DROP + 2, (6, 0, 10), "o3"), (84, (6, 0, 0)), (LENGTH, (5, 0, 0))),
    "UpperTorso": T((0, (4, 0, 0)), (6, (14, 0, 12), "io"), (GRAB, (18, 0, -14), "o3"), (LIFTED, (6, 0, -8)),
                    (WIND, (8, 0, -26), "i"), (STAB, (16, 0, 18), "o5"), (44, (14, 0, 12)), (RIP - 2, (17, 0, 15)),
                    (RIP + 2, (6, 0, -16), "o3"), (DROP + 2, (10, 0, 12), "o3"), (84, (12, 0, 0)), (LENGTH, (10, 0, 0))),
    # the phone head: snaps round, cocks watching, leans right in after the stab, watches them fall
    # the phone head: keyed cocks and leans on top of staying aimed at the player (AIM)
    "Head": T((0, (-3, 0, 0)), (3, (-6, -12, 6), "o3"), (6, (0, -8, 2)), (GRAB, (0, 8, 0), "o3"),
              (LIFTED, (0, 14, 0)), (WIND, (0, 20, -4)), (STAB, (6, 4, 0), "o3"), (40, (0, -14, 0), "io"),
              (54, (0, 16, 0)), (RIP, (0, 10, 0)), (DROP, (0, 0, 0)), (78, (6, 4, 10), "io"), (LENGTH, (6, 6, 12))),
}
LAGS = {"UpperTorso": 1, "Head": 2}
AIM = T((0, 0.0), (3, 1.0, "o3"), (DROP, 1.0), (LENGTH, 0.8))
SOCKET_N = Vector((0.0, -0.965, 0.262))
PELVIS = T((0, (0, 0, 0)), (6, (0, 0.04, -0.06)), (GRAB, (0, -0.24, -0.08), "o3"), (LIFTED, (0, -0.2, -0.03)),
           (WIND, (0, -0.16, -0.05), "i"), (STAB, (0, -0.22, -0.07), "o5"), (RIP, (0, -0.2, -0.06)),
           (RIP + 2, (0, -0.2, -0.04), "o3"), (84, (0, -0.2, -0.04)))
LEFT_FOOT = T((0, (0, 0, 0)), (6, (0, 0, 0)), (9, (0, -0.2, 0.12), "o"), (GRAB, (0, -0.38, 0), "i"), arc=True)
RIGHT_FOOT = T((0, (0, 0, 0)), (GRAB, (0, -0.06, 0), "o"), (STAB, (0, -0.12, 0), "o"))
FINGERS_R = T((0, 6), (WIND, 14), (STAB - 2, -12, "o"), (RIP + 2, -12), (70, 20, "o"), (82, 30), (84, -6, "o3"),
              (87, 26, "o"), (90, -4, "o3"), (LENGTH, 12))
FINGERS_L = T((0, 6), (8, -10), (GRAB, 50, "o3"), (DROP, 50), (DROP + 2, -10, "o3"), (LENGTH, 8))


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
    if "vhead" in ctx:  # the socket stays on the player's face (a little in front of it)
        KA.aim_bone(an, "Head", SOCKET, SOCKET_N, ctx["vhead"], AIM(f))
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (LEFT_FOOT if side == "Left" else RIGHT_FOOT)(f), 0.0, 0.14 * sx)


# ---------------------------------------------------------------- the player's key poses
V_HIPS = T((0, (0, -1, 0)), (3, (0, -1, 0)), (10, (0, -1, 0.35), "o"))
V_ROT = T((0, (0, 0, 0)), (3, (-3, 0, 0)), (10, (12, 0, -4), "o3"))
V_ARM_R = T((0, (0, -1, 0)), (4, (0.15, -1, 0.1)), (10, (0.25, 0.4, -0.9), "o3"))
V_ARM_L = T((0, (0, -1, 0)), (4, (-0.15, -1, 0.1)), (10, (-0.3, 0.55, -0.85), "o3"))
V_HEAD = T((0, (6, 0, 0)), (3, (14, 0, 0), "o"), (10, (-6, 0, 3), "o"))
H_ROT = T((GRAB, (12, 0, -4)), (15, (-10, 0, 5), "o3"), (LIFTED, (8, 0, -2)), (WIND, (6, 0, 2)),
          (STAB, (-6, 0, 0), "lin"), (STAB + 2, (-22, 0, 4), "o3"), (40, (-22, 0, 2)), (RIP - 2, (-18, 0, 0)),
          (RIP + 1, (-24, 0, -4), "o3"), (DROP, (-24, 0, 0)))
KICK = T((GRAB, 0.0), (16, 1.0, "o"), (WIND, 0.7), (STAB, 0.6), (STAB + 2, 1.6, "o3"), (42, 0.3), (50, 0.0),
         (RIP, 0.0), (RIP + 1, 0.8, "o3"), (DROP, 0.0))
HEAD_H = T((GRAB, (-6, 0, 3)), (14, (-24, 0, -6), "o3"), (LIFTED, (4, 0, 0)), (STAB, (0, 0, 0)),
           (STAB + 2, (-30, 0, 0), "o3"), (40, (-48, 6, 0), "io"), (50, (-46, 6, 0)), (58, (0, -4, 8), "io"),
           (RIP + 1, (-30, 0, 0), "o3"), (DROP, (-40, 0, 10)))


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    socket = pl.point_to_victim(an.rest_delta("Head") @ SOCKET)
    if f <= GRAB:
        torso = va.torso_from_hips(V_HIPS(f), V_ROT(f))
        feet = {"Right Leg": Vector((0.5, -3, 0.65 * K.smoothstep(3, 9, f))), "Left Leg": Vector((-0.5, -3, 0.0))}
        legs = {leg: foot - torso @ Vector((0.5 if leg == "Right Leg" else -0.5, -1, 0)) for leg, foot in feet.items()}
        return va.build(f, torso, limbs={"Right Arm": V_ARM_R(f), "Left Arm": V_ARM_L(f)}, limbs_w=legs, head=V_HEAD(f),
                        look_at=socket)
    if f < DROP:
        grip = pl.point_to_victim(an.pb["LeftHand"].matrix @ ctx["grip_local"])
        k = KICK(f)
        torso = va.torso_from_grip(grip, NECK, H_ROT(f) + Vector((0, 0, 3 * math.sin(f / 6.0) * k)))
        legs = {"Right Leg": (0.05, -1, -0.15 + 0.55 * k * math.sin(f / 2.3)),
                "Left Leg": (-0.05, -1, -0.15 - 0.55 * k * math.sin(f / 2.3 + 0.7))}
        # hands: at his wrist on their throat, then one grabbing at the claw in them, then slack
        lw = pl.point_to_victim(an.pb["LeftLowerArm"].tail)
        arms = {}
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            sh = torso @ Vector((sx * 1.0, 0.5, 0))
            tgt = lw if (f < STAB or arm == "Left Arm") else torso @ Vector((0, 0.1, -1.1))  # the claw at the wound
            hang = torso.to_3x3().inverted() @ Vector((0, -1, 0))
            to = torso.to_3x3().inverted() @ (tgt + Vector((sx * 0.25, 0, 0)) - sh).normalized()
            c = K.smoothstep(GRAB, GRAB + 6, f) * (1 - K.smoothstep(46 if arm == "Left Arm" else 54, 60, f))
            arms[arm] = hang.lerp(to, c)
        wound = torso @ Vector((0, 0.2, -1.2))
        look = socket if not (STAB < f < 56) else socket.lerp(wound, K.window(f, STAB, 40, 50, 56))
        v = va.build(f, torso, limbs={**arms, **legs}, head=HEAD_H(f), look_at=look if f < RIP else None,
                     lag={"arms": 3, "legs": 3, "head": 2})
        ctx["drop_torso"], ctx["drop_rot"] = torso, H_ROT(f)
        return v
    # flung aside to his left: a short arc, lands on their back, bounces once
    if "fall" not in ctx:
        p0 = ctx["drop_torso"].translation.copy()
        r0 = ctx["drop_rot"]
        ctx["fall"] = (T((DROP, p0), (71, p0 + Vector((1.2, 0.3, 0.3)), "o"), (LAND, (p0.x + 2.6, -2.5, p0.z + 0.8), "i"),
                         (81, (p0.x + 2.75, -2.34, p0.z + 0.85), "o"), (86, (p0.x + 2.85, -2.5, p0.z + 0.9), "i"), arc=True),
                       T((DROP, r0), (71, (20, -10, -40), "o"), (LAND, (88, -30, -20), "i"), (81, (82, -30, -18), "o"),
                         (86, (88, -30, -20), "i")))
    pos, rot = ctx["fall"][0](f), ctx["fall"][1](f)
    land = K.smoothstep(71, LAND, f)
    arms = {"Right Arm": Vector((0.6, 0.5, 0.1)).lerp(Vector((0.95, -0.2, 0.2)), land),
            "Left Arm": Vector((-0.5, 0.6, 0.1)).lerp(Vector((-0.9, -0.3, 0.1)), land)}
    legs = {"Right Leg": Vector((0.2, -0.9, -0.4)).lerp(Vector((0.15, -1, -0.1)), land),
            "Left Leg": Vector((-0.15, -0.9, 0.3)).lerp(Vector((-0.12, -1, 0.05)), land)}
    return va.build(f, Matrix.Translation(pos) @ KA.euler(rot), limbs={**arms, **legs},
                    head=Vector((-25 + 35 * land, 0, 30 * land)), lag={"arms": 3, "legs": 2, "head": 3})


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f, ctx)
    Tm = an.rest_delta("UpperTorso")
    # the left hand: cocks back, lunges for the neck, hoists them, flings them away
    if "hand_track" not in ctx:
        g = KA.VictimAnimator().torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
        neck = pl.point_to_blender(g @ NECK)
        r0 = an.pb["LeftLowerArm"].bone.tail_local.copy()
        L = Vector((0.12, -0.98, 1.46))
        ctx["hand_track"] = T((0, r0), (6, r0 + Vector((0.06, 0.14, 0.08))), (9, (r0 + neck) / 2 + Vector((0.04, 0, 0.12)), "i"),
                              (GRAB, neck + Vector((0.02, 0.07, 0)), "o"), (16, neck.lerp(L, 0.7) + Vector((0, 0.04, 0.1)), "o3"),
                              (LIFTED, L, "io"), (WIND, L + Vector((0, 0.03, 0.02))), (STAB, L), (STAB + 2, L + Vector((0, 0.04, 0.05)), "o3"),
                              (RIP, L + Vector((0, 0.02, 0.02))), (RIP + 1, L + Vector((0, -0.03, 0.03)), "o3"),
                              (DROP, L + Vector((0.32, 0.02, -0.18)), "o3"), (74, r0 + Vector((0.2, -0.2, 0.05)), "o"),
                              (LENGTH, r0), arc=True)
    hold = GRAB - 2 <= f <= DROP
    K.reach(an, "Left", ctx["hand_track"](f), Tm.to_3x3() @ Vector((0.8, 0.3, -0.6)),
            Vector((-0.5, -0.75, 0.2)).normalized() if hold else None, Vector((0, -1, 0)))
    if f == GRAB:
        g = KA.VictimAnimator().torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
        ctx["grip_local"] = an.pb["LeftHand"].matrix.inverted() @ pl.point_to_blender(g @ NECK)
    v = victim(an, ctx, f)
    # the claw: drawn far back, driven through their chest, held, ripped out, flicked
    r0 = Tm @ an.pb["RightLowerArm"].bone.tail_local
    wind = Tm @ Vector((-0.6, 0.38, 1.25))
    tb = pl.to_blender(v.torso) if f < DROP else None
    if f < DROP:
        through = tb @ CHEST_IN
        out = tb @ Vector((0, 0.2, -2.2))
        ctx["claw_last"] = through
    else:
        through = out = ctx["claw_last"]
    if f <= WIND:
        target = r0.lerp(wind, KA.EASE["io"](K.smoothstep(LIFTED - 6, WIND, f)))
    elif f <= STAB:
        target = wind.lerp(through, KA.EASE["o3"]((f - WIND) / (STAB - WIND)))
    elif f <= RIP - 2:
        target = through
    elif f <= RIP + 2:
        target = through.lerp(out, KA.EASE["o3"]((f - (RIP - 2)) / 4))
    else:
        target = out.lerp(r0 + Vector((0, -0.1, 0.05)), K.smoothstep(RIP + 2, 80, f))
        target += Vector((0.06, 0, 0.04)) * (A.bump(f, 82, 84, 87) - A.bump(f, 87, 89, 92))  # the flick
    stab_dir = None
    if WIND < f < RIP + 2 and tb is not None:
        stab_dir = (tb.to_3x3() @ Vector((0, 0, 1))).normalized()  # pointing through them
    K.reach(an, "Right", target, Tm.to_3x3() @ Vector((-0.8, 0.4, -0.4)), stab_dir, Vector((0, 0, -1)))
    pose = K.finger_curl(an, "Right", FINGERS_R(f), spread=-4 * K.window(f, WIND, STAB, RIP, RIP + 4))
    pose.update(K.finger_curl(an, "Left", FINGERS_L(f)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    ctx["vhead"] = pl.to_blender(v.head_world()).translation
    return v


NOTE = """Receiver kill, the player's half: InternalArmature carries the action
Receiver_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted so the
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
