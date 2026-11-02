#!/usr/bin/env python3
"""Keyframes the Receiver's Idle, Walk and Run (in place, 30 fps, looping), and a Call for his
fake calls.

- Idle: hunched and breathing heavily, the phone head tilting slowly as if listening, the
  claw flexing, the handset held still.
- Walk: "quick bursts": hunched strides that hurry and catch, so the steps come in spurts.
- Run: a low, loose, predatory run like a cord monster's: bent far over, rolling side to side,
  the long arms hanging wide and swinging loosely, elbows and claws whipping a beat behind,
  each footstep sending a springy wobble up through him.
- CallStart (one-shot): he looks down at the handset and lifts it to the side of his head,
  which tips over to meet it.
- CallLoop: listening with the handset to his head, the claw's fingers drumming, the dial in
  his chest dialling.

Usage: python3 receiver_animate.py BLEND [OUT_BLEND]
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
from anim_core import bump, cwave, mirror, wave  # noqa: E402

SIDES = (("Left", 1.0), ("Right", -1.0))
SPEEDS = {}
CLAW = ("Index", "Middle", "Ring", "Pinky")


def claw(curl, spread=0.0, phi=0.0, wiggle=0.0):
    """The right hand's open claw: + curls the fingers further in."""
    out = {}
    for i, f in enumerate(CLAW):
        w = wiggle * wave(phi, 2, i * 0.15)
        out[f"Right{f}1"] = mirror([("x", -(curl + w)), ("z", spread * (i - 1.5) * 5)], "Right")
        out[f"Right{f}2"] = mirror([("x", -(curl * 1.2 + w))], "Right")
    out["RightThumb1"] = mirror([("x", -curl * 0.6)], "Right")
    return out


def idle(an, phi, f):
    br = wave(phi, 2)  # two slow, heavy breaths
    listen = wave(phi, 1, 0.1)
    pose = {
        "LowerTorso": [("x", 2 + br)],
        "UpperTorso": [("x", 4 + 2.5 * br), ("y", 2 * wave(phi, 1, 0.3))],
        "Head": [("x", -3 - 1.5 * br), ("y", 9 * listen), ("z", 6 * wave(phi, 1, 0.35))],
        "LeftUpperArm": [("x", -2 + 2 * wave(phi, 1, 0.2))],
        "LeftLowerArm": [("x", -2 * wave(phi, 1, 0.3))],
        "RightUpperArm": mirror([("x", 3 * wave(phi, 1, 0.55)), ("y", 2)], "Right"),
        "RightLowerArm": [("x", -6 - 4 * wave(phi, 1, 0.65))],
        "RightHand": [("x", -6 * wave(phi, 1, 0.75))],
    }
    flex = bump(f, 36, 48, 70)  # the claw slowly closes and opens again
    pose.update(claw(-6 + 24 * flex, 1 - flex, phi, 3))
    an.fk(pose, {"LowerTorso": (0.006 * wave(phi, 1), 0.0, -0.02 + 0.01 * br)})
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.12)


WALK_T, RUN_T = 36, 20


def burst(phi, amt):
    """Warps time so the cycle hurries and catches twice: steps in spurts."""
    return phi + amt * math.sin(4 * math.pi * phi) / (4 * math.pi)


def walk(an, phi, f):
    duty, stride = 0.6, 1.0
    p = burst(phi, 0.35)
    swing = cwave(p)
    pose = {
        "LowerTorso": [("x", 6 + 2 * cwave(p, 2)), ("y", -4 * wave(p, 1, -0.05)), ("z", -7 * swing)],
        "UpperTorso": [("x", 10 + 3 * cwave(p, 2, -0.1)), ("z", 8 * swing)],
        "Head": [("x", -8 + 3 * cwave(p, 2, -0.2)), ("y", 6 * wave(p, 1, 0.2)), ("z", -6 * swing)],
    }
    # the claw arm swings against the legs; the handset arm swings less, holding on
    a = cwave(p, 1, -0.05)
    pose["RightUpperArm"] = mirror([("x", -4 - 22 * a), ("y", 4)], "Right")
    pose["RightLowerArm"] = [("x", -10 - 12 * (0.5 + 0.5 * cwave(p, 1, -0.2)))]
    pose["RightHand"] = [("x", -4 + 8 * wave(p, 1, -0.3))]
    b = cwave(p, 1, -0.55)
    pose["LeftUpperArm"] = [("x", -4 - 12 * b)]
    pose["LeftLowerArm"] = [("x", -6 - 6 * (0.5 + 0.5 * cwave(p, 1, -0.7)))]
    pose.update(claw(4 + 6 * a, 0.5, p, 2))
    bob = -0.07 + 0.022 * (0.5 - 0.5 * cwave(p, 2, -0.03))
    an.fk(pose, {"LowerTorso": (0.03 * wave(p, 1, -0.05), 0.0, bob)})
    A.biped_legs(an, p, duty, stride, 0.2, 18, 0.14, 0.0)
    SPEEDS["Walk"] = stride / (duty * WALK_T / A.FPS)


def run(an, phi, f):
    """A low, loose, predatory run like a cord monster's (after the Ennard reference): bent far
    over with the phone head held up to look ahead, rolling from side to side over each foot;
    the long arms hang low and wide and swing loosely, the elbows and claws whipping a beat
    behind like coiled cord, and every footstep sends a springy wobble up through him."""
    duty, stride = 0.42, 1.4
    tw = cwave(phi)  # +1 when the left leg is forward
    hits = (0.02, 0.52)
    wob = A.impact(phi, hits, 5.0, 2.4)  # the coil's spring after each footstep
    wob2 = A.impact(phi, hits, 5.0, 2.4, 0.05)
    pose = {
        "LowerTorso": [("x", 18 + 3 * cwave(phi, 2, -0.25)), ("y", -8 * wave(phi)), ("z", -8 * tw)],
        "UpperTorso": [("x", 22 + 4 * wob), ("y", 4 * wave(phi, 1, -0.06)), ("z", 15 * tw)],
        "Head": [("x", -34 + 6 * wob2), ("y", 3 * wave(phi, 1, -0.1)), ("z", -8 * cwave(phi, 1, -0.08))],
    }
    for side, peak, amp in (("Left", 0.55, 0.8), ("Right", 0.05, 1.0)):  # the handset arm swings a little less
        # the arms hang down from the shoulders however far he leans, and swing loose and wide
        arm = A.arm_swing(side, phi, peak, fwd=32 * amp, back=30 * amp, elbow=10, elbow_amp=22 * amp, adduct=-24,
                          adduct_amp=12, twist=0, twist_amp=14, lag=(0.2, 0.36), hand=0, hand_amp=28 * amp, lean=40)
        arm[f"{side}UpperArm"] += mirror([("y", -6 * wob)], side)  # flung out at each step
        arm[f"{side}LowerArm"] += [("x", -12 * wob2)]
        pose.update(arm)
    flail = 0.5 + 0.5 * cwave(phi, 1, -0.45)
    pose.update(claw(2 + 18 * flail, 1.2 - flail, phi, 6))  # the claw's fingers trail and flick
    bob = -0.12 - 0.04 * cwave(phi, 2, -0.21)
    an.fk(pose, {"LowerTorso": (0.07 * wave(phi), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.3, 20, 0.16, 0.03, skew=0.75)
    SPEEDS["Run"] = stride / (duty * RUN_T / A.FPS)


# ---------------------------------------------------------------- the call
# The handset is rigid on LeftHand. For the call it lies against the left side of the phone
# head, earpiece up and back, mouthpiece (where the cord goes in) forward and down. Where the
# hand has to be for that is worked out from the handset's rest pose, in the head's space, so
# the handset stays against the head however the head moves.
HANDSET_C = Vector((0.436, -0.241, 0.847))  # the handset's centre at rest (its length runs along +y)
CALL_C = Vector((0.272, -0.25, 2.12))  # where it goes, against the side of the head (head at rest)
CALL_AXIS = Vector((0.0, -0.8, -0.6)).normalized()  # its mouthpiece end, forward and down
CALL_START_T, CALL_LOOP_T = 45, 120


def handset_hand(an):
    """LeftHand's armature-space matrix with the handset held to the side of the head."""
    y = CALL_AXIS
    z = Vector((1, 0, 0))
    z = (z - y * z.dot(y)).normalized()  # the handset's underside (its earcups) faces the head
    x = y.cross(z)
    R = Matrix((x, y, z)).transposed().to_4x4()
    M = Matrix.Translation(CALL_C) @ R @ Matrix.Translation(-HANDSET_C) @ an.pb["LeftHand"].bone.matrix_local
    return an.rest_delta("Head") @ M


def place_left_hand(an, M, pole):
    an.two_bone("LeftUpperArm", "LeftLowerArm", M.translation, pole)
    hand = an.pb["LeftHand"]
    m = M.copy()
    m.translation = an.pb["LeftLowerArm"].tail.copy()
    hand.matrix = m
    hand.location = (0, 0, 0)
    hand.scale = (1, 1, 1)


CALL_POLE = Vector((0.6, 0.25, -0.75))  # the elbow out, down and back


def dial(f):
    """The dial in his chest dialling three digits: each pulled round to the finger stop
    (quick), let go, and whirring back at a steady speed, as a rotary dial does."""
    angle, t = 0.0, 4
    for pull in (150, 60, 240):
        if f < t:
            break
        if f < t + 8:
            angle = -pull * A.ease((f - t) / 8)
            break
        if f < t + 10:
            angle = -pull
            break
        back = pull / 10.0  # 10 degrees a frame on the way back
        if f < t + 10 + back:
            angle = -pull + (f - t - 10) * 10.0
            break
        t += 10 + int(back) + 8
    return angle


def call_body(phi, f, w=1.0):
    """The listening pose (CallLoop's at phase phi), weighted by w for the lift."""
    br = wave(phi, 2)
    lean = wave(phi, 1, 0.15)
    pose = {
        "LowerTorso": [("x", (3 + br) * w)],
        "UpperTorso": [("x", (6 + 2 * br) * w), ("z", (8 + 2 * lean) * w), ("y", 2 * wave(phi, 1, 0.4) * w)],
        # the head leans into the handset, listening, and eases off again
        "Head": [("x", (-4 + 2 * wave(phi, 2, 0.3)) * w), ("y", (-18 - 4 * lean) * w), ("z", (10 + 3 * wave(phi, 1, 0.4)) * w)],
        "RightUpperArm": mirror([("x", 2 * wave(phi, 1, 0.5) * w), ("y", 2 * w)], "Right"),
        "RightLowerArm": [("x", -8 * w)],
    }
    return pose


def drum(f, length):
    """The claw's fingers drumming, one after another, twice a loop."""
    out = {}
    for i, fg in enumerate(CLAW):
        tap = max(bump(f, s0 + i * 4, s0 + i * 4 + 4, s0 + i * 4 + 12) for s0 in (20, 20 + length // 2))
        out[f"Right{fg}1"] = mirror([("x", -(10 + 18 * tap)), ("z", 0.3 * (i - 1.5) * 5)], "Right")
        out[f"Right{fg}2"] = mirror([("x", -(12 + 14 * tap))], "Right")
    out["RightThumb1"] = mirror([("x", -6)], "Right")
    return out


def call_loop(an, phi, f):
    pose = call_body(phi, f)
    pose.update(drum(f, CALL_LOOP_T))
    pose["DialSpin"] = [("ly", dial(f))]
    an.fk(pose, {"LowerTorso": (0.0, 0.0, -0.02 + 0.008 * wave(phi, 2))})
    place_left_hand(an, handset_hand(an), CALL_POLE)
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.12)


def call_start(an, phi, f):
    """He looks down at the handset (0-8), then lifts it: the elbow leads up and out, the
    forearm folds and the handset turns up to the side of his head, which tips over to meet
    it (8-34), settling with a slight overshoot onto CallLoop's first frame (34-45)."""
    look = bump(f, 0, 7, 26)
    lift = A.ease((f - 7) / 27)
    settle = math.sin(math.pi * min(1.0, max(0.0, (f - 30) / 15))) * (1 - A.ease((f - 30) / 15))
    w = A.ease((f - 10) / 30)
    pose = call_body(0.0, 0, w)
    # from the idle's first pose
    pose["LowerTorso"].append(("x", 2 * (1 - w)))
    pose["UpperTorso"].append(("x", 4 * (1 - w)))
    pose["Head"] = [("x", -3 * (1 - w) + 14 * look)] + pose["Head"] + [("z", 12 * look), ("y", 3 * settle)]
    pose.update(claw(-6 * (1 - w), 1 - w, 0.0, 0))  # the idle's open claw, easing into the drumming hand
    for k, v in drum(0, CALL_LOOP_T).items():
        pose[k] = [(ax, d * w) for ax, d in v] + pose.get(k, [])
    pose["DialSpin"] = [("ly", 0.0)]
    an.fk(pose, {"LowerTorso": (0.0, 0.0, -0.02)})
    # the hand: from where the idle holds it, up along an arc that swings the elbow out, to the head
    an.fk({"LeftUpperArm": [("x", -0.1)], "LeftLowerArm": [("x", -1.9)]})  # the idle's left arm
    bpy.context.view_layer.update()
    M0 = an.pb["LeftHand"].matrix.copy()
    M1 = handset_hand(an)
    t = lift
    p = M0.translation.lerp(M1.translation, t) + Vector((0.16, 0.06, 0.0)) * math.sin(math.pi * min(1.0, t))
    q = M0.to_quaternion().slerp(M1.to_quaternion(), A.ease(min(1.0, (t - 0.15) / 0.75)))
    M = q.to_matrix().to_4x4()
    M.translation = p
    rest_pole = Vector((0.5, 1.0, -0.2))
    place_left_hand(an, M, rest_pole.lerp(CALL_POLE, A.ease(t * 1.3)))
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.12)


ACTIONS = (("Idle", 120, idle), ("Walk", WALK_T, walk), ("Run", RUN_T, run),
           ("CallStart", CALL_START_T, call_start, {"loop": False}), ("CallLoop", CALL_LOOP_T, call_loop))


def main(blend, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    if "Call" in bpy.data.actions:  # replaced by CallStart and CallLoop
        bpy.data.actions.remove(bpy.data.actions["Call"])
    A.build_actions(bpy.data.objects["Receiver_Rig"], ACTIONS)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    for name, length, *_ in ACTIONS:
        print(f"{name}: {length} frames ({length / A.FPS:.2f} s)"
              + (f", ground speed {SPEEDS[name]:.2f} m/s" if name in SPEEDS else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
