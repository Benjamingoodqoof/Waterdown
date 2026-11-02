#!/usr/bin/env python3
"""The stack's kill, "Pulled in": it rears up, then its right arm shoots out, stretching as
the creatures in it spread apart, and its hand closes on the player's chest. It drags them
in, tug by tug (the window for a teammate's light to save them), with its head creature's
open mouth turned on them, then yanks them face first into its body, through the wall of
small black bodies and eyes, and closes its other arm over them while the whole pile writhes.

Writes the stack's "Kill" action into stack.blend, and the player's half as an R6
KeyframeSequence (export/Stack_Kill_Victim.rbxmx). Both are 4 s and start together, with the
player's HumanoidRootPart DISTANCE studs in front of the stack's, facing it.

Markers (KeyframeReached on the player's track): Notice 0, Grab 26 (the save window opens),
Yank 58 (it closes), Black 70 (the camera is inside the stack), End 120.

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
import kill_core as K  # noqa: E402
import litter_animate as LA  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.661, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 4.8
LENGTH = 120
GRAB, YANK, IN = 26, 58, 70
MARKERS = {0: "Notice", GRAB: "Grab", YANK: "Yank", IN: "Black", LENGTH: "End"}
SIDES = (("Left", 1.0), ("Right", -1.0))
CHEST_IN = Vector((0.0, 0.0, 1.66))  # the middle of its body, at rest: where their head ends up  # inside the torso, at rest
LOC = ("LowerTorso", "RightLowerArm", "RightHand")


def tug(f):
    """The drag: three pulls, each a quick tug and a pause, then the yank."""
    out = 0.0
    for i, s0 in enumerate((30, 40, 50)):
        out += ss(s0, s0 + 4, f) / 3.0
    return out


def monster_body(an, f):
    rear = A.bump(f, 0, 8, 18)
    lunge = ss(10, 22, f)
    drag = ss(GRAB, YANK, f)
    yank = ss(YANK, IN, f)
    pulse = sum(A.bump(f, s0, s0 + 2, s0 + 8) for s0 in (30, 40, 50))
    writhe = ss(IN - 6, IN + 4, f)
    pose = {
        "LowerTorso": [("x", 6 + 10 * lunge - 6 * yank - 6 * rear), ("z", 6 * lunge * (1 - yank))],
        "UpperTorso": [("x", 10 - 14 * rear + 14 * lunge - 6 * drag + 3 * pulse + 16 * writhe + 3 * math.sin(f / 5) * writhe),
                       ("z", 10 * lunge * (1 - yank))],
        "Head": [("x", -18 * rear - 10 * lunge + 6 * writhe), ("z", -8 * lunge * (1 - writhe))],
        # the open-mouthed head creature turns on the player as it drags them in
        "Slot_Head1": [("x", -20 * drag * (1 - writhe)), ("y", 10 * math.sin(f / 6) * drag * (1 - writhe))],
        "LeftUpperArm": A.mirror([("x", -20 * rear), ("y", -40 * rear)], "Left"),
    }
    # every creature in the pile shifts and looks about, and writhes once the player is inside
    pose.update(LA.creatures(f / 40.0, 4.0 + 10 * writhe + 5 * yank, hits=(), look=10 + 30 * writhe))
    an.fk(pose, {"LowerTorso": (0.0, -0.3 * lunge + 0.12 * yank, -0.05 * lunge - 0.06 * writhe)})
    step = ss(10, 20, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.4 * step, 0.12 * math.sin(math.pi * step))) if side == "Right" else Vector((0, -0.06 * step, 0))
        an.leg(side, rest + off, 0.0, 0.14 * sx)


def victim_start(f, ctx):
    v = K.Victim()
    K.recoil(v, f, 4, 18, ctx.get("look"), (10, 22))
    return v


def kill(an, ctx, f):
    pl = ctx["pl"]
    monster_body(an, f)
    head_creature = an.pb["Slot_Head1"].matrix.translation.copy()
    ctx["look"] = pl.point_to_victim(head_creature)
    T = an.rest_delta("UpperTorso")
    if "grab_point" not in ctx:  # where its hand will close: the front of their chest, as they flinch
        g = victim_start(GRAB, ctx)
        ctx["grab_point"] = pl.point_to_blender(g.torso @ Vector((0, 0.3, -0.75)))
        ctx["grab_torso"] = g.torso.copy()
    G = ctx["grab_point"]
    reach = ss(10, GRAB, f)
    drag, yank = tug(f), ss(YANK, IN, f)
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    front = T @ Vector((-0.1, -0.9, 1.35))  # where the drag ends, low in front of it
    inside = T @ CHEST_IN
    pitch = 25 * drag + 35 * yank  # the player tipping toward it, then face first
    Rv = K.rot("X", -pitch) @ K.rot("Z", 6 * math.sin(f / 3.5) * (1 - yank))
    chest_off = Vector((0, 0.3, -0.75))
    if f <= GRAB:
        target = rest.lerp(G, A.ease(reach)) + Vector((0, 0, 0.25)) * math.sin(math.pi * reach)
    elif f <= YANK:
        target = G.lerp(front, drag)
    else:
        # yanked in until their head is in the middle of its body; the hand stays on their chest
        if "yank_head" not in ctx:
            vt = K.Victim()
            vt.torso = Matrix.Translation(pl.point_to_victim(front)) @ Rv @ Matrix.Translation(-chest_off)
            ctx["yank_head"] = vt.head_world().translation.copy()
        hv = ctx["yank_head"].lerp(pl.point_to_victim(inside), yank)
        vt = K.Victim()
        vt.torso = Matrix.Translation(hv) @ Rv @ Matrix.Translation(-Vector((0, 1.5, 0)))
        target = pl.point_to_blender(vt.torso @ chest_off)
    # the arm: IK as far as it reaches, then stretched the rest of the way
    K.reach(an, "Right", target, T.to_3x3() @ Vector((-0.6, 0.3, -0.7)))
    import bpy as _b
    _b.context.view_layer.update()
    gap = (target - an.pb["RightLowerArm"].tail).length
    stretch = min(0.9, gap) if f < IN else 0.0
    an.pb["RightLowerArm"].location = (0, stretch * 0.5, 0)
    an.pb["RightHand"].location = (0, stretch * 0.5, 0)
    _b.context.view_layer.update()
    hand = an.pb["Slot_RightArm5"].matrix.translation.copy()
    # the left arm: spread as it rears, then closing over them once they're inside
    close = ss(IN - 4, IN + 12, f)
    if close:
        lt = an.rest_delta("UpperTorso") @ Vector((0.05, -0.5, 1.5))
        K.reach(an, "Left", an.pb["LeftLowerArm"].tail.lerp(lt, close), T.to_3x3() @ Vector((0.8, 0.2, -0.3)))
    grip = ss(GRAB - 4, GRAB, f)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, (-10 + 50 * grip) if side == "Right" else (10 + 30 * close), spread=8 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    # the player
    if f <= GRAB:
        return victim_start(f, ctx)
    v = K.Victim()
    hv = pl.point_to_victim(hand)
    v.torso = Matrix.Translation(pl.point_to_victim(target) if f > YANK else hv) @ Rv @ Matrix.Translation(-chest_off)
    # feet dragging on the floor, then trailing
    kick = window(f, GRAB, GRAB + 4, IN, IN + 10)
    K.kick_legs(v, f, kick * 0.7)
    for leg in ("Right Leg", "Left Leg"):
        if f > YANK:
            v.rotate(leg, K.rot("X", 20 * yank))
    v.look(ctx["look"], limit=55)
    K.clutch(v, pl, f, GRAB, {"Right Arm": an.pb["RightLowerArm"].tail, "Left Arm": an.pb["RightLowerArm"].tail})
    return v


def main(litter_dir, preview):
    K.run_kill(os.path.join(litter_dir, "stack.blend"), "Stack_Rig", LENGTH, KM, DISTANCE, kill,
               os.path.join(litter_dir, "export", "Stack_Kill_Victim.rbxmx"), preview, "Stack_Kill_Victim", MARKERS,
               loc_bones=LOC)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
