#!/usr/bin/env python3
"""The stack's kill, "Bite", keyed pose to pose.

It draws itself up to its full height, leaning back, arms flung wide and every creature in it
bristling, the head creature's mouth opening; a beat. Then it crashes forward and clamps both
hands on the player's shoulders, pinning their arms, and hoists them up to its head. The head
creature draws slowly back, mouth gaping, the whole stack coiling back with it, while they
strain away and kick; it holds there, trembling, then lunges and bites down on their head. It
thrashes them from side to side, swings them back across itself and throws them, tearing them
loose; they tumble and slam down on their back. The head creature chews; the creatures in the
pile turn to look at the body.

Writes the stack's "Kill" action into stack.blend, and the player's half on the R6 rig
(export/Stack_Kill_Victim.blend). Both start together, with the player's HumanoidRootPart
DISTANCE studs in front of the stack's, facing it. 110 frames at 30 fps.

Markers: Grab 18 (the save window opens: a teammate's light now makes it drop them), Bite 45
(the mouth closes over the camera: black, crunch, skittering; the window closes), Throw 70,
End 110.

Usage: python3 litter_kill.py LITTER_DIR PREVIEW_BLEND
"""
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
LENGTH = 110
RISE, GRAB, LIFTED, REAR, BITE, WINDT, THROW = 10, 18, 30, 42, 45, 66, 70
MARKERS = {GRAB: "Grab", BITE: "Bite", THROW: "Throw", LENGTH: "End"}
SIDES = (("Left", 1.0), ("Right", -1.0))
MOUTH = Vector((0.0, -0.05, -0.23))  # the head creature's mouth, in its slot bone's frame
HOLD = Vector((0.0, -0.78, 1.74))  # where it holds their torso, at rest (in front of its chest)
GRIP = Vector((1.25, 0.55, 0.0))  # its hands on their upper arms, in their torso's frame (x mirrored)
SHAKES = (49, 55, 61)  # the thrashes: left, right, left

# ---------------------------------------------------------------- its key poses
# world-axis degrees: x leans forward, y tips to its left, z turns its chest to its left
BODY = {
    "LowerTorso": T((0, (6, 0, 0)), (RISE, (-10, 0, 0), "io"), (RISE + 3, (-11, 0, 0)), (GRAB, (22, 0, 0), "o3"),
                    (LIFTED, (6, 0, 0), "io"), (36, (2, 0, 4)), (REAR, (-6, 0, -4), "i"), (BITE, (14, 0, 0), "o5"),
                    (49, (12, 0, 16), "o3"), (52, (12, 0, 12)), (55, (12, 0, -14), "o3"), (58, (12, 0, -10)),
                    (61, (12, 0, 12), "o3"), (WINDT, (8, 0, 16), "io"), (THROW, (18, 0, -20), "o3"), (78, (14, 0, -8)),
                    (90, (12, 0, -2)), (LENGTH, (12, 0, 0))),
    "UpperTorso": T((0, (10, 0, 0)), (RISE, (-16, 0, 0), "io"), (RISE + 3, (-17, 0, 0)), (GRAB, (20, 0, 0), "o3"),
                    (LIFTED, (6, 0, 0), "io"), (36, (2, 0, 6)), (REAR, (-12, 0, -6), "i"), (BITE, (16, 0, 0), "o5"),
                    (49, (14, 0, 20), "o3"), (52, (14, 0, 15)), (55, (14, 0, -18), "o3"), (58, (14, 0, -13)),
                    (61, (14, 0, 14), "o3"), (WINDT, (4, 0, 22), "io"), (THROW, (24, 0, -24), "o3"), (78, (24, 0, -10)),
                    (90, (20, 0, -2)), (LENGTH, (20, 0, 0))),
    "Head": T((0, (-12, 0, 0)), (RISE, (-26, 0, 0)), (GRAB, (-8, 0, 0), "o3"), (LIFTED, (4, 0, 0)), (REAR, (-28, 0, 0), "i"),
              (BITE, (24, 0, 0), "o5"), (64, (18, 0, 0)), (THROW, (-10, 0, 0), "o3"), (78, (16, 0, 0)), (LENGTH, (18, 0, 0))),
    # the open-mouthed head creature: draws slowly back, then lunges
    "Slot_Head1": T((0, (0, 0, 0)), (RISE, (-22, 0, 0)), (GRAB, (0, 0, 0), "o3"), (36, (-10, 0, 0)), (REAR, (-38, 0, 0), "i"),
                    (REAR + 1, (-40, 0, 0)), (BITE, (28, 0, 0), "o5"), (64, (20, 0, 0)), (THROW, (-14, 0, 0), "o3"),
                    (76, (6, 0, 0)), (LENGTH, (4, 0, 0))),
    "LeftUpperArm": T((0, (0, 0, 0)), (RISE, (-70, -60, 0), "io")),
    "RightUpperArm": T((0, (0, 0, 0)), (RISE, (-70, 60, 0), "io")),
    "LeftLowerArm": T((0, (0, 0, 0)), (RISE, (-36, 0, 0), "io")),
    "RightLowerArm": T((0, (0, 0, 0)), (RISE, (-36, 0, 0), "io")),
}
LAGS = {"UpperTorso": 1, "Head": 2, "Slot_Head1": 3}
PELVIS = T((0, (0, 0, 0)), (RISE, (0, 0.1, 0.08), "io"), (RISE + 3, (0, 0.11, 0.09)), (GRAB, (0, -0.24, -0.1), "o3"),
           (LIFTED, (0, -0.1, -0.02), "io"), (REAR, (0, -0.02, 0.0), "i"), (BITE, (0, -0.18, -0.07), "o5"),
           (64, (0, -0.14, -0.05)), (THROW, (0, -0.24, -0.1), "o3"), (LENGTH, (0, -0.16, -0.06)))
RIGHT_FOOT = T((0, (0, 0, 0)), (RISE + 3, (0, 0.02, 0)), (15, (0, -0.15, 0.1), "o"), (GRAB, (0, -0.34, 0), "i"), arc=True)
LEFT_FOOT = T((0, (0, 0, 0)), (GRAB, (0, -0.06, 0), "o"))
BRISTLE = T((0, 4.0), (RISE, 16.0, "o"), (RISE + 3, 16.0), (GRAB, 6.0), (REAR, 12.0), (BITE, 6.0), (BITE + 2, 18.0, "o3"),
            (64, 10.0), (80, 6.0), (LENGTH, 5.0))
FINGERS = T((0, 6), (RISE, -16, "o"), (GRAB - 1, -16), (GRAB, 46, "o3"), (THROW - 1, 46), (THROW + 1, -12, "o3"), (LENGTH, 10))


def monster_body(an, f):
    extra = LA.creatures(f / 37.0, BRISTLE(f), hits=(BITE / 37.0,), kick=1.5, look=10 + 30 * K.smoothstep(THROW, 88, f))
    # the head creature chews after the throw
    extra["Slot_Head1"] = [("x", 8 * A.bump(f, 74, 76, 79) + 8 * A.bump(f, 82, 84, 87) + 6 * A.bump(f, 92, 94, 97))]
    KA.pose_monster(an, f, BODY, LAGS, {"LowerTorso": PELVIS}, extra)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, rest + (RIGHT_FOOT if side == "Right" else LEFT_FOOT)(f), 0.0, 0.16 * sx)


def mouth_point(an):
    return an.pb["Slot_Head1"].matrix @ MOUTH


# ---------------------------------------------------------------- the player's key poses
FLINCH = KA.flinch_tracks(3, 14, "Right Leg", big=1.2)
# The whole body is keyed on the same frames (the key poses), so on the R6 rig Blender eases between
# whole poses:  18 grabbed by the shoulders  24 / 30 hoisted, kicking  36 / 42 straining away from the
#   mouth as it draws back  45 the bite (held)  48 the body jerks  52 / 58 / 64 thrashed left, right,
#   left (lagging the stack)  66 hanging  70 swung back across it and thrown
H_ROT = T((GRAB, FLINCH["rot"](GRAB)), (24, (-10, 0, 4), "io"), (LIFTED, (4, 0, -2), "io"), (36, (10, 0, 3), "io"),
          (REAR, (18, 8, 0), "io"), (BITE, (18, 8, 0)))
HEAD_H = T((GRAB, FLINCH["head"](GRAB)), (24, (10, 0, 0), "io"), (LIFTED, (0, 0, 0), "io"), (36, (6, -30, 6), "io"),
           (REAR, (14, -34, 6), "io"), (BITE, (14, -34, 6)))
# in its jaws: thrashed side to side (roll), the body jerking (pitch)
SWING = T((BITE, (-8, 0, 0)), (48, (10, 0, -10), "o"), (52, (-4, 0, 30), "io"), (58, (-4, 0, -32), "io"),
          (64, (-6, 0, 24), "io"), (WINDT, (-8, 0, -6), "io"), (THROW, (-10, 0, -14), "io"))
PIN_R, PIN_L = ((0.15, -1, -0.15), (0, 0.1, 0)), ((-0.15, -1, -0.15), (0, 0.1, 0))
FLAIL_R, FLAIL_L = ((0.3, -0.7, -0.65), (0, 0.05, 0)), ((-0.3, -0.7, -0.6), (0, 0.05, 0))
ARMS = {
    "Right Arm": KA.PoseKeys(
        (GRAB, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3))), (24, PIN_R, "io"), (LIFTED, FLAIL_R, "io"), (36, PIN_R, "io"),
        (REAR, FLAIL_R, "io"), (BITE, FLAIL_R), (48, ((0.55, -0.5, -0.65), (0, 0.1, 0)), "o"),
        (52, ((0.3, -0.9, 0.2), (0, 0.05, 0)), "io"), (58, ((0.7, -0.3, -0.5), (0, 0.1, 0)), "io"),
        (64, ((0.5, -0.6, -0.5), (0, 0.05, 0)), "io"), (WINDT, ((0.12, -1, 0.05), (0, 0, 0)), "io"),
        (THROW, ((0.15, -1, 0.0), (0, 0, 0)), "io")),
    "Left Arm": KA.PoseKeys(
        (GRAB, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3))), (24, PIN_L, "io"), (LIFTED, PIN_L, "io"), (36, FLAIL_L, "io"),
        (REAR, FLAIL_L, "io"), (BITE, FLAIL_L), (48, ((-0.55, -0.5, -0.65), (0, 0.1, 0)), "o"),
        (52, ((-0.6, -0.5, -0.6), (0, 0.1, 0)), "io"), (58, ((-0.2, -1, 0.1), (0, 0, 0)), "io"),
        (64, ((-0.2, -0.95, 0.1), (0, 0, 0)), "io"), (WINDT, ((-0.12, -1, 0.05), (0, 0, 0)), "io"),
        (THROW, ((-0.15, -1, 0.0), (0, 0, 0)), "io")),
}
LEGS = {
    leg: KA.PoseKeys(
        (GRAB, (((0.05, -0.95, 0.35) if leg == "Right Leg" else (-0.05, -0.95, -0.3)), (0, 0, 0))),
        (24, ((sx * 0.06, -1, 0.0), (0, 0, 0)), "io"),
        *KA.kick_keys(leg, LIFTED, REAR, beat=6, a0=1.0, a1=1.0, phase=0 if leg == "Right Leg" else 1),
        (BITE, ((sx * 0.08, -0.9, 0.2), (0, 0.05, 0)), "io"), (48, ((sx * 0.12, -0.5, -0.85), (0, 0.5, -0.15)), "o"),
        (52, ((0.45 + sx * 0.05, -0.9, 0.1), (0, 0, 0)), "io"), (58, ((-0.45 + sx * 0.05, -0.9, 0.1), (0, 0, 0)), "io"),
        (64, ((0.35 + sx * 0.05, -0.9, 0.1), (0, 0, 0)), "io"), (WINDT, ((sx * 0.05, -1, 0.05), (0, 0, 0)), "io"),
        (THROW, ((-0.3 + sx * 0.05, -0.95, 0.1), (0, 0, 0)), "io"))
    for leg, sx in (("Right Leg", 1), ("Left Leg", -1))
}
# the key poses on the R6 rig (Blender eases between them) and the hits (hard stops)
R6_KEYS = (3, 5, 8, 14, GRAB, 24, LIFTED, 36, REAR, BITE, 48, 52, 58, 64, WINDT, THROW)
R6_SHARP = (BITE,)


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
        v = KA.apply_flinch(va, f, FLINCH, look_at=mouth)
        ctx["grab_torso"] = v.torso.copy()
        return v
    if f < BITE:
        held = held_torso(an, ctx, f)
        lift = KA.EASE["o3"](min(1.0, (f - GRAB) / (LIFTED - GRAB)))
        torso = K.blend_cf(ctx["grab_torso"], held, lift)
        v = va.build(f, torso, look_at=mouth, head=HEAD_H(f), lag={"head": 2})
        KA.pose_limbs(va, v, f, ARMS, LEGS)
        ctx["bite_from"] = torso
        return v
    if f < THROW:
        # clamped in its jaws by the head: hanging from the mouth, thrashed side to side
        mt = pl.to_victim(an.pb["Slot_Head1"].matrix)  # the head creature's frame, in their space
        clamp = mt @ Vector((0, -0.1, -0.2))  # their head, in its mouth (slot frame, meters)
        hold = KA.EASE["o5"](min(1.0, (f - BITE + 2) / 3))
        b = K.Victim()
        b.torso = ctx["bite_from"]
        head_pos = b.head_world().translation.lerp(clamp, hold)
        head_cf = K.look_cf(head_pos, pl.point_to_victim(an.pb["Slot_Head1"].matrix.translation))
        hv = K.Victim()
        hv.hang_from_head(head_cf, KA.euler(SWING(f)))
        v = va.build(f, hv.torso, lag={"head": 0})
        v.T["Head"] = hv.T["Head"]
        KA.pose_limbs(va, v, f, ARMS, LEGS)
        ctx["throw_from"], ctx["throw_rot"], ctx["throw_limbs"] = hv.torso, SWING(f), KA.limb_dirs(v)
        return v
    # torn loose and thrown down to its right (their left): tumbling, onto their back, a slide
    if "fall" not in ctx:
        ctx["fall"] = KA.fall_tracks(ctx["throw_from"].translation.copy(), ctx["throw_rot"], THROW, "thrown",
                                     land=(-3.4, 1.7), yaw=-55, side=-1.0, look_at=mouth, start_limbs=ctx["throw_limbs"])
    return KA.apply_fall(va, f, ctx["fall"])


def kill(an, ctx, f):
    pl = ctx["pl"]
    ctx.setdefault("va", KA.VictimAnimator())
    monster_body(an, f)
    v = victim(an, ctx, f)
    Tm = an.rest_delta("UpperTorso")
    if GRAB - 6 <= f <= THROW:
        tb = pl.to_blender(v.torso)
        for side, sx in SIDES:
            # its left hand on their right arm (both at +x)
            grip = tb @ Vector((GRIP.x * sx, GRIP.y, GRIP.z))
            if f < GRAB:
                g = KA.flinch_torso(KA.VictimAnimator(), GRAB, FLINCH)
                grip_at = pl.point_to_blender(g @ Vector((GRIP.x * sx, GRIP.y, GRIP.z)))
                wide = Tm @ an.pb[f"{side}LowerArm"].bone.tail_local
                t = KA.EASE["i"]((f - (GRAB - 6)) / 6)
                target = KA.catmull(wide, wide, grip_at + Vector((sx * 0.25, 0, 0.2)), grip_at, t).lerp(grip_at, t)
            else:
                target = grip
            K.reach(an, side, target, Tm.to_3x3() @ Vector((sx * 0.9, 0.3, -0.3)),
                    (Vector((0, 0, -1)) - tb.to_3x3().col[0] * sx * 0.3).normalized() if f >= GRAB - 1 else None,
                    -tb.to_3x3().col[0] * sx)
            ctx["rel_" + side] = target
    elif f > THROW:
        for side, sx in SIDES:  # its arms swing through after the throw, open, and settle
            r0 = Tm @ an.pb[f"{side}LowerArm"].bone.tail_local
            rel = ctx["rel_" + side]
            follow = KA.Track((THROW, rel), (THROW + 4, rel.lerp(r0, 0.4) + Vector((-0.35, -0.2, -0.1)), "o3"),
                                       (90, r0 + Vector((-0.05, -0.1, 0.0)), "io"), (LENGTH, r0))
            K.reach(an, side, follow(f), Tm.to_3x3() @ Vector((sx * 0.9, 0.3, -0.3)))
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, FINGERS(f), spread=10 * K.window(f, 4, RISE, GRAB - 1, GRAB)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """The Litter (stack) kill, the player's half: InternalArmature carries the action
Stack_Kill_Victim (30 fps, frames 0-110). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (save window
opens), Bite (window closes), Throw, End.
The 'Monster (reference)' collection holds the stack playing its half, at your in-game size,
lined up where the game should put it: 3.6 studs in front of the player, facing them.
"""


def main(litter_dir, preview):
    blend = os.path.join(litter_dir, "stack.blend")
    ctx = K.run_kill(blend, "Stack_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Stack_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    fall = ctx["fall"]
    K.write_r6_blend(template, os.path.join(litter_dir, "export", "Stack_Kill_Victim.blend"), ctx["parts"],
                     "Stack_Kill_Victim", MARKERS, (blend, "Stack_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE,
                     keys=set(R6_KEYS) | K.key_frames(fall), sharp=set(R6_SHARP) | set(fall["impact"]),
                     refine=("Torso", "Head"))  # the head is in its jaws: it has to stay there
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
