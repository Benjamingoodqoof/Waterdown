#!/usr/bin/env python3
"""Keyframes the Stand-In's Idle, Walk and Run (in place, 30 fps, looping). He moves "slow,
stooped": a tall man with too-long limbs who doesn't quite know how to use them.

- Idle: stooped and still, swaying a little, the monitor drifting and tipping as if he's
  watching you, his long fingers slowly curling and uncurling.
- Walk: long, slow strides, stooped, the arms hanging and barely swinging.
- Run: a lanky lope, leaning forward, the arms loose and trailing behind, the monitor bobbing.

The cable down his back swings a beat behind his body in all three.

Usage: python3 standin_animate.py BLEND [OUT_BLEND]
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
from anim_core import bump, cwave, mirror, wave  # noqa: E402

SIDES = (("Left", 1.0), ("Right", -1.0))
FINGERS = ("Index", "Middle", "Ring", "Pinky")
SPEEDS = {}


def fingers(side, curl, phi=0.0, wiggle=0.0, phase=0.0):
    out = {}
    for i, f in enumerate(FINGERS):
        w = wiggle * wave(phi, 1, phase + i * 0.11)
        out[f"{side}{f}1"] = mirror([("x", -(curl + w))], side)
        out[f"{side}{f}2"] = mirror([("x", -(curl * 1.4 + w * 1.5))], side)
    out[f"{side}Thumb1"] = mirror([("x", -curl * 0.5)], side)
    return out


def cable(phi, sway, swing, lag=0.12):
    """The hanging cable: each bone follows the one above it a little later."""
    return {f"Cable{k}": [("y", sway * wave(phi, 1, -lag * k)), ("x", swing * cwave(phi, 2, -lag * k))]
            for k in (1, 2, 3)}


def idle(an, phi, f):
    br = wave(phi, 1)
    look = wave(phi, 1, 0.15)
    pose = {
        "LowerTorso": [("x", 2 + 0.6 * br), ("y", 1.2 * wave(phi, 1, 0.3))],
        "UpperTorso": [("x", 12 + 1.5 * br), ("y", 2 * wave(phi, 1, 0.45))],
        "Head": [("x", 6 + 3 * wave(phi, 1, 0.6)), ("y", 10 * look), ("z", 8 * wave(phi, 1, 0.35))],
    }
    for side, sx in SIDES:
        ph = 0.0 if side == "Left" else 0.4
        pose[f"{side}UpperArm"] = mirror([("x", -4 + 2 * wave(phi, 1, ph)), ("y", 1.5)], side)
        pose[f"{side}LowerArm"] = [("x", -5 + 2 * wave(phi, 1, ph + 0.1))]
        pose[f"{side}Hand"] = [("x", -4 + 3 * wave(phi, 1, ph + 0.2))]
    # the long fingers curl in slowly, one hand then the other
    pose.update(fingers("Left", 4 + 22 * bump(f, 20, 44, 70), phi, 4))
    pose.update(fingers("Right", 6 + 18 * bump(f, 60, 82, 112), phi, 4, 0.5))
    pose.update(cable(phi, 3, 1.5))
    an.fk(pose, {"LowerTorso": (0.006 * wave(phi, 1, 0.3), 0.0, -0.02 + 0.006 * br)})
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.06)


WALK_T, RUN_T = 48, 24


def walk(an, phi, f):
    duty, stride = 0.62, 1.15
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 4 + 1.5 * cwave(phi, 2)), ("y", -3 * wave(phi, 1, -0.05)), ("z", -6 * swing)],
        "UpperTorso": [("x", 14 + 2 * cwave(phi, 2, -0.1)), ("y", 2 * wave(phi, 1, 0.1)), ("z", 5 * swing)],
        "Head": [("x", 8 + 2 * cwave(phi, 2, -0.2)), ("y", 4 * wave(phi, 1, 0.2)), ("z", -4 * swing)],
    }
    for side, sx in SIDES:
        peak = 0.5 if side == "Left" else 0.0
        a = cwave(phi, 1, -(peak + 0.06))
        pose[f"{side}UpperArm"] = mirror([("x", -4 - 9 * a), ("y", 2)], side)
        pose[f"{side}LowerArm"] = [("x", -6 - 5 * (0.5 + 0.5 * cwave(phi, 1, -(peak + 0.18))))]
        pose[f"{side}Hand"] = [("x", -3 + 5 * wave(phi, 1, -(peak + 0.26)))]
        pose.update(fingers(side, 8 + 4 * a, phi, 3, peak))
    pose.update(cable(phi, 6, 4, 0.1))
    bob = -0.05 + 0.02 * (0.5 - 0.5 * cwave(phi, 2, -0.03))
    an.fk(pose, {"LowerTorso": (0.025 * wave(phi, 1, -0.05), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.16, 16, 0.06, 0.0)
    SPEEDS["Walk"] = stride / (duty * WALK_T / A.FPS)


def run(an, phi, f):
    duty, stride = 0.42, 1.7
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 12 + 2 * cwave(phi, 2, -0.1)), ("y", -4 * wave(phi, 1, -0.2)), ("z", -9 * swing)],
        "UpperTorso": [("x", 22 + 3 * cwave(phi, 2, -0.15)), ("z", 8 * cwave(phi, 1, -0.04))],
        "Head": [("x", -4 + 5 * cwave(phi, 2, -0.25)), ("y", 6 * wave(phi, 1, -0.1)), ("z", -8 * cwave(phi, 1, -0.1))],
    }
    for side, sx in SIDES:
        peak = 0.5 if side == "Left" else 0.0

        def arc(lag, peak=peak):
            return cwave(phi, 1, -(peak + lag))

        a = arc(0.0)
        # loose, too-long arms trailing and flapping, never quite in time
        pose[f"{side}UpperArm"] = mirror([("x", 8 - 34 * a), ("y", 8 + 4 * a)], side)
        pose[f"{side}LowerArm"] = [("x", -14 - 16 * (0.5 + 0.5 * arc(0.14)))]
        pose[f"{side}Hand"] = [("x", 4 + 10 * arc(0.24))]
        pose.update(fingers(side, 6 + 10 * (0.5 + 0.5 * arc(0.3)), phi, 0))
    pose.update(cable(phi, 8, 10, 0.08))
    pose["Cable1"].append(("x", 25))  # flung out behind him
    pose["Cable2"].append(("x", 10))
    bob = -0.09 - 0.04 * cwave(phi, 2, -0.18)
    an.fk(pose, {"LowerTorso": (0.02 * wave(phi, 1, 0.06), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.3, 20, 0.06, 0.0)
    SPEEDS["Run"] = stride / (duty * RUN_T / A.FPS)


ACTIONS = (("Idle", 120, idle), ("Walk", WALK_T, walk), ("Run", RUN_T, run))


def main(blend, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    A.build_actions(bpy.data.objects["StandIn_Rig"], ACTIONS)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    for name, length, _ in ACTIONS:
        print(f"{name}: {length} frames ({length / A.FPS:.2f} s)"
              + (f", ground speed {SPEEDS[name]:.2f} m/s" if name in SPEEDS else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
