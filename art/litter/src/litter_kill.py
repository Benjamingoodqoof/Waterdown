#!/usr/bin/env python3
"""The stack's kill, "Bite", keyed pose to pose.

It rears up to its full height, arms flung wide and every creature in it bristling, then crashes
forward and clamps both hands on the player's shoulders, pinning their arms. It hoists them up
off the floor to its head. The head creature draws back, its needle-toothed mouth gaping, and
bites down on the player's head; the whole stack thrashes them from side to side, then tears
them loose and flings them down. The head creature chews; the creatures in the pile turn to look
at the body.

Writes the stack's "Kill" action into stack.blend, and the player's half on the R6 rig
(export/Stack_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of the stack's, facing it. 100 frames at 30 fps.

Markers: Grab 14 (the save window opens: a teammate's light now makes it drop them), Bite 36
(the mouth closes over the camera: black, crunch, skittering; the window closes), Throw 62,
End 100.

Usage: python3 litter_kill.py LITTER_DIR PREVIEW_BLEND
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
import litter_animate as LA  # noqa: E402
from kill_anim import Track as T  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.661, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 100
GRAB, LIFTED, REAR, BITE, SHAKE_END, THROW, LAND = 14, 26, 33, 36, 56, 62, 74
MARKERS = {GRAB: "Grab", BITE: "Bite", THROW: "Throw", LENGTH: "End"}
SIDES = (("Left", 1.0), ("Right", -1.0))
MOUTH = Vector((0.0, -0.05, -0.23))  # the head creature's mouth, in its slot bone's frame
HOLD = Vector((0.0, -0.78, 1.74))  # where it holds their torso, at rest (in front of its chest)
GRIP = Vector((1.25, 0.55, 0.0))  # its hands on their upper arms, in their torso's frame (x mirrored)

BODY = {
    "LowerTorso": T((0, (6, 0, 0)), (8, (-10, 0, 0), "io"), (GRAB, (22, 0, 0), "o3"), (LIFTED, (8, 0, 0)),
                    (REAR, (4, 0, 0)), (BITE, (12, 0, 0), "o5"), (40, (10, 0, 16), "o3"), (45, (10, 0, -14), "io"),
                    (50, (10, 0, 10), "io"), (SHAKE_END, (10, 0, 0), "io"), (THROW - 2, (6, 0, 10)),
                    (THROW, (16, 0, -18), "o3"), (72, (14, 0, -8)), (LENGTH, (12, 0, 0))),
    "UpperTorso": T((0, (10, 0, 0)), (8, (-16, 0, 0), "io"), (GRAB, (20, 0, 0), "o3"), (LIFTED, (6, 0, 0)),
                    (REAR, (-6, 0, 0)), (BITE, (14, 0, 0), "o5"), (40, (12, 0, 18), "o3"), (45, (12, 0, -16), "io"),
                    (50, (12, 0, 10), "io"), (SHAKE_END, (12, 0, 0), "io"), (THROW - 2, (2, 0, 12)),
                    (THROW, (22, 0, -20), "o3"), (72, (24, 0, -8)), (LENGTH, (20, 0, 0))),
    "Head": T((0, (-12, 0, 0)), (8, (-24, 0, 0)), (GRAB, (-8, 0, 0), "o3"), (LIFTED, (4, 0, 0)), (REAR, (-24, 0, 0), "io"),
              (BITE, (22, 0, 0), "o5"), (SHAKE_END, (18, 0, 0)), (THROW, (-10, 0, 0), "o3"), (72, (16, 0, 0)), (LENGTH, (18, 0, 0))),
    # the open-mouthed head creature: rears right back, then lunges
    "Slot_Head1": T((0, (0, 0, 0)), (8, (-20, 0, 0)), (GRAB, (0, 0, 0), "o3"), (REAR, (-34, 0, 0), "io"),
                    (BITE, (26, 0, 0), "o5"), (SHAKE_END, (20, 0, 0)), (THROW, (-14, 0, 0), "o3"), (70, (6, 0, 0)), (LENGTH, (4, 0, 0))),
    "LeftUpperArm": T((0, (0, 0, 0)), (8, (-60, -50, 0), "io")),
    "RightUpperArm": T((0, (0, 0, 0)), (8, (-60, 50, 0), "io")),
    "LeftLowerArm": T((0, (0, 0, 0)), (8, (-30, 0, 0), "io")),
    "RightLowerArm": T((0, (0, 0, 0)), (8, (-30, 0, 0), "io")),
}
LAGS = {"UpperTorso": 1, "Head": 2, "Slot_Head1": 3}
PELVIS = T((0, (0, 0, 0)), (8, (0, 0.08, 0.06), "io"), (GRAB, (0, -0.24, -0.1), "o3"), (LIFTED, (0, -0.12, -0.04)),
           (BITE, (0, -0.16, -0.06), "o5"), (SHAKE_END, (0, -0.14, -0.05)), (THROW, (0, -0.24, -0.1), "o3"),
           (LENGTH, (0, -0.16, -0.06)))
RIGHT_FOOT = T((0, (0, 0, 0)), (9, (0, 0, 0)), (11, (0, -0.15, 0.1), "o"), (GRAB, (0, -0.34, 0), "i"), arc=True)
LEFT_FOOT = T((0, (0, 0, 0)), (GRAB, (0, -0.06, 0), "o"))
BRISTLE = T((0, 4.0), (8, 14.0, "o"), (GRAB, 6.0), (BITE, 6.0), (BITE + 2, 18.0, "o3"), (SHAKE_END, 10.0), (70, 6.0),
            (LENGTH, 5.0))
FINGERS = T((0, 6), (8, -16, "o"), (GRAB - 1, -16), (GRAB, 46, "o3"), (THROW - 1, 46), (THROW + 1, -12, "o3"), (LENGTH, 10))


def monster_body(an, f):
    extra = LA.creatures(f / 37.0, BRISTLE(f), hits=(BITE / 37.0,), kick=1.5, look=10 + 30 * K.smoothstep(THROW, 80, f))
    # the head creature chews after the throw
    extra["Slot_Head1"] = [("x", 8 * A.bump(f, 66, 68, 71) + 8 * A.bump(f, 74, 76, 79) + 6 * A.bump(f, 84, 86, 89))]
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS}, extra)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (RIGHT_FOOT if side == "Right" else LEFT_FOOT)(f), 0.0, 0.16 * sx)


def mouth_point(an):
    return an.pb["Slot_Head1"].matrix @ MOUTH


# ---------------------------------------------------------------- the player's key poses
V_HIPS = T((0, (0, -1, 0)), (4, (0, -1, 0)), (12, (0, -1, 0.35), "o"))
V_ROT = T((0, (0, 0, 0)), (4, (-3, 0, 0)), (12, (12, 0, -4), "o3"))
V_ARM_R = T((0, (0, -1, 0)), (6, (0.2, -1, 0.1)), (12, (0.35, -0.2, -0.9), "o3"))
V_ARM_L = T((0, (0, -1, 0)), (6, (-0.2, -1, 0.1)), (12, (-0.35, -0.1, -0.9), "o3"))
V_HEAD = T((0, (16, 0, 0)), (4, (28, 0, 0), "o"), (12, (8, 0, 3), "o"))
H_ROT = T((GRAB, (12, 0, -4)), (17, (-8, 0, 4), "o3"), (LIFTED, (4, 0, -2)), (REAR, (6, 0, 2)),
          (BITE, (-14, 0, 0), "o5"), (BITE + 3, (-8, 0, 0)))
KICK = T((GRAB, 0.0), (18, 1.0, "o"), (BITE, 0.8), (BITE + 2, 1.5, "o3"), (46, 0.6), (SHAKE_END, 0.1), (THROW, 0.0))


def held_torso(an, ctx, f):
    """Their torso held out in front of its chest (moving and twisting with its upper body)."""
    pl = ctx["pl"]
    Tm = an.rest_delta("UpperTorso")
    pos = pl.point_to_victim(Tm @ HOLD)
    Q = (pl.P.inverted() @ Tm.to_3x3().normalized().to_4x4() @ pl.P).to_3x3().normalized()
    return Matrix.Translation(pos) @ Q.to_4x4() @ KA.euler(H_ROT(f))


def victim(an, ctx, f):
    va, pl = ctx["va"], ctx["pl"]
    mouth = pl.point_to_victim(mouth_point(an))
    if f <= GRAB:
        torso = va.torso_from_hips(V_HIPS(f), V_ROT(f))
        feet = {"Right Leg": Vector((0.5, -3, 0.65 * K.smoothstep(4, 11, f))), "Left Leg": Vector((-0.5, -3, 0.0))}
        legs = {leg: foot - torso @ Vector((0.5 if leg == "Right Leg" else -0.5, -1, 0)) for leg, foot in feet.items()}
        v = va.build(f, torso, limbs={"Right Arm": V_ARM_R(f), "Left Arm": V_ARM_L(f)}, limbs_w=legs, head=V_HEAD(f),
                     look_at=mouth)
        ctx["grab_torso"] = torso
        return v
    k = KICK(f)
    legs = {"Right Leg": (0.05, -1, 0.5 * k * math.sin(f / 2.4)), "Left Leg": (-0.05, -1, -0.5 * k * math.sin(f / 2.4 + 0.6))}
    # arms pinned at their sides by its hands, the forearms (whole R6 arm) twitching forward
    arms = {"Right Arm": (0.12, -1, -0.25 * k * (0.5 + 0.5 * math.sin(f / 3.1))),
            "Left Arm": (-0.12, -1, -0.25 * k * (0.5 + 0.5 * math.sin(f / 2.7 + 1)))}
    if f < BITE:
        held = held_torso(an, ctx, f)
        lift = KA.EASE["o3"](min(1.0, (f - GRAB) / (LIFTED - GRAB)))
        torso = K.blend_cf(ctx["grab_torso"], held, lift)
        v = va.build(f, torso, limbs={**arms, **legs}, look_at=mouth, head=Vector((-6, 0, 0)),
                     lag={"arms": 2, "legs": 3, "head": 2})
        ctx["bite_from"] = torso
        return v
    if f < SHAKE_END + 3:
        # clamped in its jaws by the head: hanging from the mouth, thrashed side to side
        mt = pl.to_victim(an.pb["Slot_Head1"].matrix)  # the head creature's frame, in their space
        clamp = mt @ Vector((0, -0.1, -0.2))  # their head, in its mouth (slot frame, meters)
        hold = KA.EASE["o5"](min(1.0, (f - BITE + 2) / 3))
        b = K.Victim()
        b.torso = ctx["bite_from"]
        start = b.head_world().translation
        head_pos = start.lerp(clamp, hold)
        face_to = pl.point_to_victim(an.pb["Slot_Head1"].matrix.translation)
        head_cf = K.look_cf(head_pos, face_to)
        swing = KA.damped(f, [(40, 1.0), (45, -1.0), (50, 0.8)], 22, 0.12, 0.12)
        hv = K.Victim()
        hv.hang_from_head(head_cf, KA.euler(Vector((-8, 0, swing))))
        v = va.build(f, hv.torso, limbs={**arms, **legs}, lag={"arms": 3, "legs": 4})
        v.T["Head"] = hv.T["Head"]
        ctx["throw_from"], ctx["throw_rot"] = hv.torso, Vector((-8, 0, swing))
        return v
    # torn loose and flung down to its right: a short arc onto their back, a bounce
    if "fall" not in ctx:
        p0 = ctx["throw_from"].translation.copy()
        r0 = ctx["throw_rot"]
        ctx["fall"] = (T((SHAKE_END + 3, p0), (THROW, p0 + Vector((-0.4, 0.5, 0.0)), "o"), (67, p0 + Vector((-1.6, -0.6, -0.2)), "i"),
                         (LAND, (p0.x - 2.6, -2.5, p0.z + 0.6), "i"), (77, (p0.x - 2.7, -2.36, p0.z + 0.62), "o"),
                         (82, (p0.x - 2.75, -2.5, p0.z + 0.65), "i"), arc=True),
                       T((SHAKE_END + 3, r0), (THROW, (-20, 0, 20)), (67, (30, 0, 70), "i"), (LAND, (88, 0, 40), "i"),
                         (77, (82, 0, 40), "o"), (82, (88, 0, 40), "i")))
    pos, rot = ctx["fall"][0](f), ctx["fall"][1](f)
    land = K.smoothstep(67, LAND, f)
    arms = {"Right Arm": Vector((0.5, 0.6, 0.2)).lerp(Vector((0.95, -0.2, 0.1)), land),
            "Left Arm": Vector((-0.5, 0.5, 0.2)).lerp(Vector((-0.9, -0.3, 0.2)), land)}
    legs = {"Right Leg": Vector((0.2, -0.9, 0.3)).lerp(Vector((0.15, -1, -0.1)), land),
            "Left Leg": Vector((-0.15, -0.9, -0.4)).lerp(Vector((-0.1, -1, 0.0)), land)}
    return va.build(f, Matrix.Translation(pos) @ KA.euler(rot), limbs={**arms, **legs},
                    head=Vector((-10 + 20 * land, 0, -25 * land)), lag={"arms": 3, "legs": 2, "head": 3})


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f)
    v = victim(an, ctx, f)
    Tm = an.rest_delta("UpperTorso")
    if f >= GRAB - 6 and f <= THROW:
        tb = pl.to_blender(v.torso)
        for side, sx in SIDES:
            # its left hand on their right arm (both at +x)
            grip = tb @ Vector((GRIP.x * sx, GRIP.y, GRIP.z))
            if f < GRAB:
                g = KA.VictimAnimator().torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
                grip_at = pl.point_to_blender(g @ Vector((GRIP.x * sx, GRIP.y, GRIP.z)))
                wide = Tm @ an.pb[f"{side}LowerArm"].bone.tail_local
                target = KA.catmull(wide, wide, grip_at + Vector((sx * 0.25, 0, 0.2)), grip_at,
                                    KA.EASE["i"]((f - (GRAB - 6)) / 6))
                target = target.lerp(grip_at, KA.EASE["i"]((f - (GRAB - 6)) / 6))
            else:
                target = grip
            K.reach(an, side, target, Tm.to_3x3() @ Vector((sx * 0.9, 0.3, -0.3)),
                    (Vector((0, 0, -1)) - tb.to_3x3().col[0] * sx * 0.3).normalized() if f >= GRAB - 1 else None,
                    -tb.to_3x3().col[0] * sx)
    elif f > THROW:
        for side, sx in SIDES:  # arms swing through after the throw and settle
            r0 = Tm @ an.pb[f"{side}LowerArm"].bone.tail_local
            follow = Vector((sx * 0.1 - 0.3, -0.5, -0.1)) * (1 - K.smoothstep(THROW, 90, f))
            K.reach(an, side, r0 + follow, Tm.to_3x3() @ Vector((sx * 0.9, 0.3, -0.3)))
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, FINGERS(f), spread=10 * K.window(f, 6, 9, GRAB - 1, GRAB)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """The Litter (stack) kill, the player's half: InternalArmature carries the action
Stack_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (save window
opens), Bite (window closes), Throw, End.
The 'Monster (reference)' collection holds the stack playing its half, at your in-game size,
lined up where the game should put it: 3.6 studs in front of the player, facing them.
"""


def main(litter_dir, preview):
    blend = os.path.join(litter_dir, "stack.blend")
    ctx = K.run_kill(blend, "Stack_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Stack_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(litter_dir, "export", "Stack_Kill_Victim.blend"), ctx["parts"],
                     "Stack_Kill_Victim", MARKERS, (blend, "Stack_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
