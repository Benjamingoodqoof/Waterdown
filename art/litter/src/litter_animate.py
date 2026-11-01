#!/usr/bin/env python3
"""Keyframes the Litter's Idle, Walk and Run (in place, 30 fps, looping):

- the stack: hunched and heaving. Every creature in it keeps shifting and looking about on its
  slot, and each footstep sends a wobble up through the creatures. The walk is a heavy
  lumber; the run is a scrambling charge, leaning in with the claws reaching.
- the litterling: an idle that taps the floor and rears up with its front legs raised, and a
  scuttling, spider-like alternating gait (L1 R2 L3 R4, then R1 L2 R3 L4) for the walk and run.

Usage: python3 litter_animate.py LITTER_DIR [--only stack|litterling]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
import litter_common as C  # noqa: E402
from anim_core import bump, cwave, impact, loop_noise, mirror, wave  # noqa: E402

SIDES = C.SIDES
SPEEDS = {}
SLOTS = list(C.slots())


# ================================================================ the stack
def fingers(side, curl, spread=0.0, phase=0.0, phi=0.0, wiggle=0.0):
    out = {}
    for i, f in enumerate(C.FINGERS):
        w = wiggle * wave(phi, 2, phase + i * 0.13)
        out[f"{side}{f}1"] = mirror([("x", -(curl + w)), ("z", spread * (i - 2) * 4)], side)
        out[f"{side}{f}2"] = mirror([("x", -(curl * 1.3 + w))], side)
    return out


def creatures(phi, amount, hits=(), kick=0.0, look=0.0):
    """Every creature fidgets on its slot; footsteps send a wobble up the body (higher ones
    later); a few turn right round to look."""
    out = {}
    for k, name in enumerate(SLOTS):
        c = C.slots()[name][0]
        lag = 0.03 + 0.05 * max(0.0, c.z - 0.3)  # the wobble climbs the stack
        hit = impact(phi, hits, 7.0, 2.2, lag) * kick if hits else 0.0
        if "Arm5" in name or "Leg4" in name:  # the hands and feet hold steady
            amt, hit = amount * 0.3, hit * 0.3
        else:
            amt = amount
        turn = look * loop_noise(phi, k * 7 + 3, 2) if k % 4 == 0 else 0.0
        out[f"Slot_{name}"] = [("x", amt * loop_noise(phi, k + 1) + hit * 6), ("y", amt * loop_noise(phi, k + 11)),
                               ("z", amt * 1.4 * loop_noise(phi, k + 23) + turn)]
    return out


def stack_idle(an, phi, f):
    br = wave(phi, 2)
    pose = {
        "LowerTorso": [("x", 4 + br)],
        "UpperTorso": [("x", 14 + 2.5 * br), ("y", 3 * wave(phi, 1, 0.2))],
        "Head": [("x", -12 - br), ("z", 16 * wave(phi, 1, 0.1)), ("y", 6 * wave(phi, 1, 0.35))],
    }
    for side, sx in SIDES:
        ph = 0.0 if side == "Left" else 0.37
        pose[f"{side}UpperArm"] = mirror([("x", -10 + 3 * wave(phi, 1, ph)), ("y", 4)], side)
        pose[f"{side}LowerArm"] = [("x", -14 + 3 * wave(phi, 1, ph + 0.1))]
        pose[f"{side}Hand"] = [("x", -6 + 4 * wave(phi, 1, ph + 0.2))]
        pose.update(fingers(side, 10 + 12 * (0.5 + 0.5 * wave(phi, 1, ph + 0.3)), 0.6, ph, phi, 6))
    pose.update(creatures(phi, 4.0, look=28.0))
    an.fk(pose, {"LowerTorso": (0.008 * wave(phi, 1), 0.0, -0.07 + 0.012 * br)})
    an.leg("Left", C.SJ["ankle_Left"] + Vector((0.02, -0.04, 0)), 0.0, 0.15)
    an.leg("Right", C.SJ["ankle_Right"] + Vector((-0.02, 0.05, 0)), 0.0, -0.15)


STACK_WALK_T, STACK_RUN_T = 40, 22


def stack_walk(an, phi, f):
    duty, stride = 0.62, 0.9
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 8 + 2 * cwave(phi, 2)), ("y", -5 * wave(phi, 1, -0.05)), ("z", -7 * swing)],
        "UpperTorso": [("x", 16 + 2 * cwave(phi, 2, -0.08)), ("y", 4 * wave(phi, 1, 0.1)), ("z", 9 * swing)],
        "Head": [("x", -14 + 3 * cwave(phi, 2, -0.15)), ("z", -6 * swing)],
    }
    for side, sx in SIDES:
        peak = 0.5 if side == "Left" else 0.0
        a = cwave(phi, 1, -(peak + 0.05))
        pose[f"{side}UpperArm"] = mirror([("x", -10 - 20 * a), ("y", 6)], side)
        pose[f"{side}LowerArm"] = [("x", -18 - 10 * (0.5 + 0.5 * cwave(phi, 1, -(peak + 0.15))))]
        pose[f"{side}Hand"] = [("x", -6 + 8 * wave(phi, 1, -(peak + 0.22)))]
        pose.update(fingers(side, 18 + 8 * a, 0.5, peak, phi, 4))
    pose.update(creatures(phi, 3.0, hits=(0.02, 0.52), kick=1.0, look=14.0))
    bob = -0.1 + 0.03 * (0.5 - 0.5 * cwave(phi, 2, -0.02))
    an.fk(pose, {"LowerTorso": (0.04 * wave(phi, 1, -0.05), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.2, 14, 0.14, 0.01, toe_first=False)
    SPEEDS["Stack Walk"] = stride / (duty * STACK_WALK_T / A.FPS)


def stack_run(an, phi, f):
    duty, stride = 0.4, 1.35
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 16 + 3 * cwave(phi, 2, -0.1)), ("y", -6 * wave(phi, 1, -0.2)), ("z", -10 * swing)],
        "UpperTorso": [("x", 20 + 3 * cwave(phi, 2, -0.15)), ("z", 14 * cwave(phi, 1, -0.04))],
        "Head": [("x", -30 + 4 * cwave(phi, 2, -0.2)), ("z", -10 * cwave(phi, 1, -0.08))],
    }
    for side, sx in SIDES:
        peak = 0.5 if side == "Left" else 0.0

        def arc(lag, peak=peak):
            return cwave(phi, 1, -(peak + lag))

        a = arc(0.0)
        pose[f"{side}UpperArm"] = mirror([("x", -35 - 45 * a), ("y", 12 + 6 * a)], side)  # reaching, clawing forward
        pose[f"{side}LowerArm"] = [("x", -30 + 18 * arc(0.1))]
        pose[f"{side}Hand"] = [("x", -10 + 10 * arc(0.16))]
        pose.update(fingers(side, 14 + 20 * (0.5 - 0.5 * arc(0.2)), 1.0, peak, phi, 0))  # claws open at the front
    pose.update(creatures(phi, 4.0, hits=(0.0, 0.5), kick=1.8, look=8.0))
    bob = -0.13 - 0.04 * cwave(phi, 2, -0.18)
    an.fk(pose, {"LowerTorso": (0.02 * wave(phi, 1, 0.06), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.34, 20, 0.12, 0.01, toe_first=False)
    SPEEDS["Stack Run"] = stride / (duty * STACK_RUN_T / A.FPS)


# ================================================================ the litterling
LEGS = [(side, sx, k) for side, sx in SIDES for k in range(C.LEGS)]
# an alternating tetrapod, like a spider's: L1 R2 L3 R4 step together, then R1 L2 R3 L4
GROUP = {(side, k): (k + (side == "Right")) % 2 for side, _ in SIDES for k in range(C.LEGS)}


def litter_legs(an, phi, duty, stride, lift, lift_legs=None):
    """All eight legs: feet planted during stance, sliding back at ground speed; lift_legs adds
    an offset to a few feet ({(side, k): Vector})."""
    for side, sx, k in LEGS:
        hip, knee, foot = C.leg_layout(side, sx, k)
        y, z = 0.0, 0.0
        if stride:
            ph = (phi + 0.5 * GROUP[(side, k)] + 0.04 * k) % 1.0  # the back legs a touch behind
            if ph < duty:
                y = -stride / 2 + stride * ph / duty
            else:
                s = (ph - duty) / (1 - duty)
                y = stride / 2 - stride * A.ease(s)
                z = lift * math.sin(math.pi * s)
        target = foot + Vector((0, y, z)) + (lift_legs or {}).get((side, k), Vector())
        pole = (knee - C.BODY_C)
        pole = Vector((pole.x, pole.y, 0)).normalized() * 0.3 + Vector((0, 0, 1))
        an.two_bone(f"Leg{side[0]}{k + 1}A", f"Leg{side[0]}{k + 1}B", target, pole)


def ling_idle(an, phi, f):
    """Still, breathing, the body turning to look about; a front leg taps the floor, then it
    rears up with its front legs raised, and settles."""
    br = wave(phi, 2)
    rear = bump(f, 52, 62, 80)
    an.fk({"Body": [("x", 3 * br - 18 * rear), ("z", 10 * wave(phi, 1, 0.2)), ("y", 4 * wave(phi, 1, 0.45))]},
          {"Body": (0.004 * wave(phi, 1, 0.1), 0.012 * rear, 0.008 * br - 0.01 + 0.035 * rear)})
    lifts = {}
    tap = max(bump(f, 18, 22, 30), bump(f, 32, 35, 42))  # a front leg taps the floor, twice
    if tap:
        lifts[("Left", 0)] = Vector((0, -0.01, 0.05 * tap))
    if rear:
        for side, sx in SIDES:  # the front legs raised and spread, feeling the air
            lifts[(side, 0)] = Vector((sx * 0.03, -0.06, 0.16)) * rear + Vector((0, 0, 0.012 * wave(phi, 6)))
            lifts[(side, 1)] = Vector((sx * 0.02, -0.02, 0.05)) * rear
    tap2 = bump(f, 96, 99, 106)
    if tap2:
        lifts[("Right", 1)] = Vector((0, 0, 0.04 * tap2))
    litter_legs(an, phi, 0, 0, 0, lifts)


LING_WALK_T, LING_RUN_T = 16, 8


def ling_walk(an, phi, f):
    duty, stride = 0.55, 0.17
    an.fk({"Body": [("x", 4 + 2 * cwave(phi, 2)), ("z", 4 * wave(phi, 1)), ("y", 3 * cwave(phi, 1))]},
          {"Body": (0.006 * wave(phi, 1), 0.0, -0.01 + 0.012 * (0.5 - 0.5 * cwave(phi, 2)))})
    litter_legs(an, phi, duty, stride, 0.06)
    SPEEDS["Litterling Walk"] = stride / (duty * LING_WALK_T / A.FPS)


def ling_run(an, phi, f):
    duty, stride = 0.4, 0.3
    an.fk({"Body": [("x", 10 + 3 * cwave(phi, 2)), ("z", 5 * wave(phi, 1)), ("y", 4 * cwave(phi, 1))]},
          {"Body": (0.008 * wave(phi, 1), -0.01, -0.045 + 0.02 * (0.5 - 0.5 * cwave(phi, 2)))})
    litter_legs(an, phi, duty, stride, 0.085)
    SPEEDS["Litterling Run"] = stride / (duty * LING_RUN_T / A.FPS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("litter")
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    root = os.path.abspath(a.litter)
    jobs = []
    if a.only in (None, "stack"):
        jobs.append(("stack.blend", "Stack_Rig", (("Idle", 120, stack_idle), ("Walk", STACK_WALK_T, stack_walk),
                                                  ("Run", STACK_RUN_T, stack_run)), ("LowerTorso",)))
    if a.only in (None, "litterling"):
        jobs.append(("litterling.blend", "Litterling_Rig", (("Idle", 120, ling_idle), ("Walk", LING_WALK_T, ling_walk),
                                                            ("Run", LING_RUN_T, ling_run)), ("Body",)))
    for blend, rig_name, actions, loc in jobs:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(root, blend))
        A.build_actions(bpy.data.objects[rig_name], actions, loc)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(root, blend))
        print(blend, ", ".join(f"{n} {t} frames" for n, t, _ in actions))
    for k, v in SPEEDS.items():
        print(f"{k}: {v:.2f} m/s")


if __name__ == "__main__":
    main()
