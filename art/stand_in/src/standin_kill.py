#!/usr/bin/env python3
"""The Stand-In's kill (CRT Man), "Broadcast" into "Channel change": his monitor snaps round to
the player, he lunges and clamps both hands on their head the way he grips his own monitor,
and yanks them off their feet up to his screen. Their face goes up on it, live. He smacks the
side of their head, twice, like a broken TV, then turns their head like a channel knob, click
by click, so the first-person view rolls round. The signal cuts, and he hurls them to the
floor.

Writes the Stand-In's "Kill" action into the blend, and the player's half on the R6 rig
(export/StandIn_Kill_Victim.blend). Both are 4 s and start together, with the player's
HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Grip 14 (QTE starts), Broadcast 30 (his screen shows their face), Smack 50 and 60,
Channel 66 (QTE ends; the view starts glitching), NoSignal 88 (screen and camcorder cut to NO
SIGNAL), Thrown 100 (they hit the floor), End 120.

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
import kill_core as K  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 4.2
LENGTH = 120
GRIP, LIFTED, SMACKS, CLICKS, NOSIG, THROW, LAND = 14, 28, (50, 60), (68, 74, 80, 86), 88, 90, 100
MARKERS = {0: "Notice", GRIP: "Grip", 30: "Broadcast", 50: "Smack", 60: "Smack", 66: "Channel", NOSIG: "NoSignal",
           LAND: "Thrown", LENGTH: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))
SIDES = (("Left", 1.0), ("Right", -1.0))
HITS = (GRIP, SMACKS[0], SMACKS[1], NOSIG, LAND) + CLICKS


def smack(f, at):
    """A slap landing at frame `at`: -1 winding up, +1 at the hit, settling back."""
    wind = ss(at - 8, at - 2, f) * (1 - ss(at - 2, at, f))
    hit = A.bump(f, at - 2, at, at + 9)
    return wind, hit


def roll(f):
    """The channel-knob twist: 32 degrees a click, each snapped round in 2 frames."""
    return sum(-32 * ss(c - 2, c, f) for c in CLICKS)


def monster_body(an, f):
    snap = A.bump(f, 0, 3, 12)
    antic = A.bump(f, 3, 6, 10)
    lunge = ss(5, GRIP, f)
    up = ss(GRIP, LIFTED, f)
    throw = ss(THROW - 4, LAND, f)
    after = ss(LAND, LAND + 10, f)
    w1, h1 = smack(f, SMACKS[0])
    w2, h2 = smack(f, SMACKS[1])
    click = sum(A.bump(f, c - 2, c, c + 5) for c in CLICKS)
    lean = -6 * antic + 34 * lunge * (1 - up) + 4 * up + 26 * throw * (1 - after) + 14 * after
    twist = -14 * (w1 + 1.4 * w2) + 10 * (h1 + 1.4 * h2) + 30 * A.bump(f, THROW - 4, THROW + 2, LAND + 6)
    pose = {
        "LowerTorso": [("x", 3 + 0.5 * lean)],
        "UpperTorso": [("x", 4 + lean), ("z", twist)],
        # the monitor snaps to the player, leans in to look them over, jerks with each click
        "Head": [("x", -8 * snap + 12 * up + 6 * click + 10 * A.bump(f, NOSIG - 2, NOSIG, NOSIG + 8) + 22 * after),
                 ("y", 14 * snap - 10 * up * (1 - after) - 4 * click), ("z", 10 * snap + 6 * math.sin(f / 8.0) * up * (1 - throw))],
    }
    pose.update({f"Cable{i}": [("x", 12 * lunge * (1 - up) + 18 * throw * (1 - after) + 3 * math.sin(f / 5 + i))]
                 for i in (1, 2, 3)})
    an.fk(pose, {"LowerTorso": (0.0, 0.05 * antic - 0.4 * lunge + 0.14 * up - 0.12 * throw,
                                -0.08 * lunge + 0.05 * up - 0.08 * throw)})
    step = ss(5, 12, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        target = rest + (Vector((0, -0.6 * step, 0.14 * math.sin(math.pi * step))) if side == "Right" else
                         Vector((0, -0.1 * step, 0)))
        an.leg(side, target, 0.0, 0.06 * sx)


def held_head(an, ctx, f):
    """Where the player's head is while he holds it, and which way it faces."""
    pl = ctx["pl"]
    screen_v = pl.point_to_victim(an.rest_delta("Head") @ SCREEN)
    hold = pl.point_to_victim(an.rest_delta("Head") @ (SCREEN + Vector((0, -0.34, -0.06))))
    lift = K.back_out((f - GRIP) / (LIFTED - GRIP), 2.2)
    pos = ctx["grab_head"].translation.lerp(hold, lift)
    _, h1 = smack(f, SMACKS[0])
    _, h2 = smack(f, SMACKS[1])
    hit = h1 + 1.5 * h2
    pos += Vector((0.5 * hit, 0.1 * hit, 0))  # knocked toward their right
    cf = K.look_cf(pos, screen_v) @ K.rot("Y", -28 * hit) @ K.rot("Z", -10 * hit) @ K.rot("Z", roll(f))
    return cf, screen_v


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    screen_v = pl.point_to_victim(an.rest_delta("Head") @ SCREEN)
    if f <= GRIP:
        K.recoil(v, f, 1, 9, screen_v, (5, 12))
        ctx["grab_head"] = v.head_world().copy()
        K.jolt_head(v, f, (GRIP,))
        return v
    head_cf, _ = held_head(an, ctx, f)
    kick = window(f, GRIP, GRIP + 3, 70, 86)
    sw = K.rot("X", 6 * math.sin(f / 3.6) * kick) @ K.rot("Z", 5 * math.sin(f / 2.9) * kick + roll(f) * 0.3)
    held = K.Victim()
    held.hang_from_head(head_cf, sw)
    if f >= THROW:
        # hurled down and away to his right, tumbling, onto their back
        lying = Matrix.Translation((-1.8, -2.45, -0.4)) @ K.rot("Y", 60) @ K.rot("X", 90)
        ctx.setdefault("throw_from", held.torso.copy())
        K.fall(v, ctx["throw_from"], f, THROW, LAND, lying, screen_v)
        K.jolt_head(v, f, (LAND,), 18)
        return v
    v.torso, v.T["Head"] = held.torso, held.T["Head"]
    K.kick_legs(v, f, kick)
    K.jolt_head(v, f, HITS, 10)
    return v


def hands(an, ctx, f, v):
    """Both hands on the sides of the player's head; the right one swings away and slaps back
    in for each smack; both let go to throw them."""
    pl = ctx["pl"]
    reach = ss(4, GRIP, f)
    release = ss(THROW, THROW + 4, f)
    T = an.rest_delta("UpperTorso")
    head_b = pl.to_blender(v.head_world())
    hc = head_b.translation
    hx = head_b.to_3x3().col[0].normalized()
    hu = head_b.to_3x3().col[1].normalized()
    hf = -head_b.to_3x3().col[2].normalized()
    for side, sx in SIDES:
        rest = T @ an.pb[f"{side}LowerArm"].bone.tail_local
        grip = hc + hx * sx * (0.62 * KM + 0.05) - hf * 0.02
        target = rest.lerp(grip, K.back_out(reach, 1.2))
        target += (T.to_3x3() @ Vector((sx * 0.3, -1.0, 0.2))) * 0.15 * math.sin(math.pi * reach)
        if side == "Right":
            for at in SMACKS:
                w, h = smack(f, at)
                target = target + hx * sx * 0.45 * w + (T.to_3x3() @ Vector((0, 0, 0.12))) * w
        if release:
            follow = rest + (T.to_3x3() @ Vector((sx * 0.2, -0.45, -0.15)))
            target = target.lerp(follow, release)
        pole = T.to_3x3() @ Vector((sx * 0.8, -0.65 * reach, -0.6))
        hand_dir = (hu * 0.9 + hf * 0.3).normalized() if reach > 0.5 and release < 0.5 else None
        K.reach(an, side, target, pole, hand_dir, -hx * sx)
    return reach, release


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    reach, release = hands(an, ctx, f, v)
    grip = max(0.0, reach * 2 - 1) * (1 - release)
    pose = {}
    for side, _ in SIDES:
        open_ = max(smack(f, a)[0] for a in SMACKS) if side == "Right" else 0.0
        pose.update(K.finger_curl(an, side, (8 + 30 * grip) * (1 - open_) - 8 * open_, spread=-6 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRIP < f < THROW:  # their hands clawing at his wrists, flung out by the smacks
        pl = ctx["pl"]
        K.clutch(v, pl, f, GRIP, {"Right Arm": an.pb["LeftLowerArm"].tail, "Left Arm": an.pb["RightLowerArm"].tail})
        fling = sum(smack(f, a)[1] for a in SMACKS)
        if fling > 0.01:
            v.point("Left Arm", Vector((-0.9, 0.2 + fling, 0.3)).normalized())
    return v


NOTE = """CRT Man (Stand-In) kill, the player's half: InternalArmature carries the action
StandIn_Kill_Victim (30 fps, frames 0-120). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. The timeline markers are the beats:
Grip (QTE starts), Broadcast, Smack, Smack, Channel (QTE ends), NoSignal, Thrown, End.
The 'Monster (reference)' collection holds the CRT Man playing his half, at your in-game size,
lined up where the game should put him: 4.2 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "StandIn_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "StandIn_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "StandIn_Kill_Victim.blend"), ctx["parts"], "StandIn_Kill_Victim",
                     MARKERS, (blend, "StandIn_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
