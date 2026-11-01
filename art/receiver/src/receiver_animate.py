#!/usr/bin/env python3
"""Keyframes the Receiver's Idle, Walk and Run (in place, 30 fps, looping), and a Call for his
fake calls.

- Idle: hunched and breathing heavily, the phone head tilting slowly as if listening, the
  claw flexing, the handset held still.
- Walk: "quick bursts": hunched strides that hurry and catch, so the steps come in spurts.
- Run: a low, lunging charge, the claw reaching ahead, the handset arm pumping.
- Call: he lifts the handset to the side of his head, the head cocks to it, and the dial in
  his chest spins.

Usage: python3 receiver_animate.py BLEND [OUT_BLEND]
"""
import math
import os
import sys

import bpy

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
    duty, stride = 0.38, 1.45
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 14 + 3 * cwave(phi, 2, -0.1)), ("y", -5 * wave(phi, 1, -0.18)), ("z", -10 * swing)],
        "UpperTorso": [("x", 16 + 3 * cwave(phi, 2, -0.15)), ("z", 12 * cwave(phi, 1, -0.04))],
        "Head": [("x", -22 + 3 * cwave(phi, 2, -0.2)), ("z", -10 * cwave(phi, 1, -0.08))],
    }
    a = cwave(phi, 1, -0.02)  # the claw reaches ahead as the left foot lands
    pose["RightUpperArm"] = mirror([("x", -30 - 40 * a), ("y", 8)], "Right")
    pose["RightLowerArm"] = [("x", -14 + 14 * cwave(phi, 1, -0.1))]
    pose["RightHand"] = [("x", -8 + 10 * cwave(phi, 1, -0.16))]
    b = cwave(phi, 1, -0.52)
    pose["LeftUpperArm"] = [("x", -10 - 30 * b), ("y", -4)]
    pose["LeftLowerArm"] = [("x", -16 - 14 * (0.5 + 0.5 * cwave(phi, 1, -0.62)))]
    pose.update(claw(-4 + 16 * (0.5 - 0.5 * cwave(phi, 1, -0.2)), 1.2))  # it opens wide as it reaches
    bob = -0.1 - 0.035 * cwave(phi, 2, -0.2)
    an.fk(pose, {"LowerTorso": (0.018 * wave(phi, 1, 0.06), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.32, 22, 0.12, 0.0)
    SPEEDS["Run"] = stride / (duty * RUN_T / A.FPS)


def call(an, phi, f):
    """The handset at his head, the dial spinning a full turn each loop."""
    br = wave(phi, 2)
    pose = {
        "LowerTorso": [("x", 3 + br)],
        "UpperTorso": [("x", 5 + 2 * br), ("z", 6)],
        "Head": [("x", -2), ("y", -16 + 3 * wave(phi, 1, 0.2)), ("z", 8)],
        "LeftUpperArm": [("x", -86), ("y", -28), ("z", 10)],
        "LeftLowerArm": [("x", -98 + 4 * wave(phi, 2, 0.1))],
        "LeftHand": [("x", 10), ("z", -30)],
        "RightUpperArm": mirror([("x", 2 * wave(phi, 1, 0.5)), ("y", 2)], "Right"),
        "RightLowerArm": [("x", -8)],
        "DialSpin": [("ly", -360 * phi)],
    }
    pose.update(claw(10 + 8 * wave(phi, 2, 0.3), 0.3))
    an.fk(pose, {"LowerTorso": (0.0, 0.0, -0.02 + 0.008 * br)})
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.12)


ACTIONS = (("Idle", 120, idle), ("Walk", WALK_T, walk), ("Run", RUN_T, run), ("Call", 90, call))


def main(blend, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    A.build_actions(bpy.data.objects["Receiver_Rig"], ACTIONS)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    for name, length, _ in ACTIONS:
        print(f"{name}: {length} frames ({length / A.FPS:.2f} s)"
              + (f", ground speed {SPEEDS[name]:.2f} m/s" if name in SPEEDS else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
