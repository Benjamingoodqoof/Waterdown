#!/usr/bin/env python3
"""Keyframes the Stand-In's Idle, Walk and Run (in place, 30 fps, looping). He moves "slow,
stooped": a tall man with too-long limbs who doesn't quite know how to use them.

- Idle: stooped and still, swaying a little, the monitor drifting and tipping as if he's
  watching you, his long fingers slowly curling and uncurling.
- Walk: long, slow strides, stooped, the arms hanging and barely swinging.
- Run: a long-legged sprint, leaning in: the arms pump with bent elbows, crossing in toward
  the chest and swinging out past the hip, the shoulders twisting against the hips, the wrists
  and fingers flopping a beat behind.
- Transform (one-shot): he grabs both sides of his monitor and wrenches at it; the game plays
  its glitch effects over it, then swaps him for the copied player.
- TransformLoop: the wrenching, shaking hold, to loop for as long as the glitch lasts.

The cable down his back swings a beat behind his body in all three.

Usage: python3 standin_animate.py BLEND [OUT_BLEND]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

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


WALK_T, RUN_T = 48, 22


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
    """A long-legged sprint, after the run reference: leaning in, the knees driving high and the
    heels kicking up behind; the arms pump with the elbows bent, crossing in toward the chest as
    they come forward and swinging out past the hip as they go back, the shoulders twisting
    against the hips. The wrists and long fingers flop a beat behind, a little too loose."""
    duty, stride = 0.42, 1.6
    tw = cwave(phi)  # +1 when the left leg is forward
    pose = {
        "LowerTorso": [("x", 9 + 2 * cwave(phi, 2, -0.25)), ("y", -3 * wave(phi, 1, -0.1)), ("z", -9 * tw)],
        "UpperTorso": [("x", 13 + 3 * cwave(phi, 2, -0.3)), ("y", 2 * wave(phi, 1, -0.05)), ("z", 20 * tw)],
        # the monitor stays on target, turning against the shoulders and nodding a beat late
        "Head": [("x", -9 + 3 * cwave(phi, 2, -0.4)), ("z", -10 * cwave(phi, 1, -0.06))],
    }
    for side, peak in (("Left", 0.53), ("Right", 0.03)):
        pose.update(A.arm_swing(side, phi, peak, fwd=40, back=58, elbow=70, elbow_amp=20, adduct=6, adduct_amp=8,
                                twist=10, twist_amp=18, lag=(0.05, 0.15), hand=2, hand_amp=12, lean=22))
        pose.update(fingers(side, 9 + 7 * (0.5 + 0.5 * cwave(phi, 1, -(peak + 0.22))), phi, 0))
    pose.update(cable(phi, 8, 10, 0.08))
    pose["Cable1"].append(("x", 28))  # flung out behind him
    pose["Cable2"].append(("x", 12))
    bob = -0.07 - 0.045 * cwave(phi, 2, -0.21)  # lowest mid-stance, highest in the air
    an.fk(pose, {"LowerTorso": (0.012 * wave(phi, 1, 0.06), 0.0, bob)})
    A.biped_legs(an, phi, duty, stride, 0.36, 24, 0.06, 0.0, skew=0.7)
    SPEEDS["Run"] = stride / (duty * RUN_T / A.FPS)


# ---------------------------------------------------------------- the transformation
# He grabs both sides of his monitor and wrenches at it while the game glitches him into a
# copy of a player. Transform is the grab (a one-shot); TransformLoop holds it, straining,
# for as long as the glitch lasts.
GRIP = {"Left": Vector((0.24, -0.21, 2.37)), "Right": Vector((-0.24, -0.21, 2.37))}  # wrists, on the bezel's sides
TRANSFORM_T, TRANSFORM_LOOP_T = 60, 60


def palm_axis(an, side):
    """Which local axis of the hand faces the palm (toward his thigh at rest)."""
    m = an.pb[f"{side}Hand"].bone.matrix_local.to_3x3()
    inward = Vector((-1.0 if side == "Left" else 1.0, 0, 0))
    best = max((("x", m.col[0]), ("-x", -m.col[0]), ("z", m.col[2]), ("-z", -m.col[2])),
               key=lambda kv: kv[1].dot(inward))
    return best[0]


def grip_arms(an, blend, flare=0.0):
    """IKs both hands onto the monitor's sides (blend 0: hanging as at rest, 1: gripping),
    reaching up in front of him."""
    D = an.rest_delta("Head")
    T = an.rest_delta("UpperTorso")
    for side, sx in SIDES:
        rest = an.pb[f"{side}LowerArm"].bone.tail_local
        start = T @ rest
        end = D @ GRIP[side]
        t = A.ease(blend)
        out = T.to_3x3() @ Vector((sx * 0.35, -1.0, 0.0))  # up in front of him, not past his hips
        target = start.lerp(end, t) + out * 0.24 * math.sin(math.pi * t)
        # the elbows come forward and out under the monitor, as when holding a box up to the face
        pole = (T.to_3x3() @ Vector((sx * 0.8, 0.3 - 0.95 * t, -0.6 - 0.3 * (1 - t)))) + Vector((sx * flare, 0, 0))
        an.two_bone(f"{side}UpperArm", f"{side}LowerArm", target, pole)
        if t > 0.0:
            fingers_up = D.to_3x3() @ Vector((0, -0.25, 1.0))
            hang = an.pb[f"{side}LowerArm"].matrix.to_3x3().col[1]
            ydir = hang.lerp(fingers_up, A.ease((t - 0.3) / 0.7)).normalized()
            palm = (D.to_3x3() @ Vector((-sx, 0, 0))).lerp(Vector((-sx, 0, 0)), 1 - t)
            an.orient(f"{side}Hand", ydir, palm_axis(an, side), palm)


def strain(phi):
    """The wrenching hold (TransformLoop's pose at phase phi): offsets for the body and monitor,
    plus a tremble that loops."""
    heave = wave(phi, 1)

    def tremble(seed, amp):
        return amp * sum(math.sin(2 * math.pi * (k * phi + 0.17 * seed * k)) for k in (7, 11, 13)) / 2.2

    return {
        "LowerTorso": [("x", 6 + 1.5 * heave + tremble(1, 0.4))],
        "UpperTorso": [("x", 17 + 3 * wave(phi, 1, 0.1) + tremble(2, 0.8)), ("z", -4 * wave(phi, 1, 0.05)),
                       ("y", 2 * wave(phi, 2, 0.3))],
        # the monitor wrenched side to side and pulled down, shaking in his hands
        "Head": [("x", 12 + 3 * wave(phi, 2, 0.15) + tremble(3, 1.6)), ("z", 8 * heave + tremble(4, 1.4)),
                 ("y", 5 * wave(phi, 1, 0.3) + tremble(5, 1.2))],
    }, -0.05 + 0.012 * wave(phi, 2, 0.1)


def transform_loop(an, phi, f):
    pose, drop = strain(phi)
    for side, _ in SIDES:
        pose.update(fingers(side, 22 + 6 * (0.5 + 0.5 * wave(phi, 3, 0.1 if side == "Left" else 0.4)), phi, 3))
    pose.update(cable(phi, 6, 4, 0.1))
    an.fk(pose, {"LowerTorso": (0.0, 0.0, drop)})
    grip_arms(an, 1.0)
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.1, drop=0.0)


def transform(an, phi, f):
    """0-10: he stiffens and straightens, fingers spreading; 8-24: both hands fly up and clamp
    onto the monitor; 22-30: it jolts down in his grip and he hunches over it; then the
    wrenching hold builds, arriving at TransformLoop's first frame."""
    stiff = A.ease(f / 10)
    reach = (f - 8) / 16
    jolt = bump(f, 22, 26, 34)
    build = A.ease((f - 26) / 14)
    lp = ((f - TRANSFORM_T) / TRANSFORM_LOOP_T) % 1.0  # the loop's phase, reaching 0 on the last frame
    hold, drop = strain(lp)
    idle_stoop = {"LowerTorso": 2, "UpperTorso": 12, "Head": 6}
    pose = {}
    for bone in ("LowerTorso", "UpperTorso", "Head"):
        base = idle_stoop[bone] * (1 - stiff) + (-4 if bone == "UpperTorso" else 0) * stiff * (1 - build)
        rots = [(ax, d * build) for ax, d in hold[bone]]
        rots.append(("x", base + {"UpperTorso": 6, "Head": 10}.get(bone, 0) * jolt))
        pose[bone] = rots
    for side, _ in SIDES:
        spread = -6 * stiff * (1 - A.ease(reach))
        clench = 22 * A.ease((f - 20) / 8) + 6 * build * (0.5 + 0.5 * wave(lp, 3, 0.1 if side == "Left" else 0.4))
        pose.update(fingers(side, 4 * (1 - build) + spread + clench, lp, 3 * build))
    pose.update(cable(lp, 3 + 3 * build, 1.5 + 2.5 * build, 0.1))
    an.fk(pose, {"LowerTorso": (0.0, 0.0, -0.02 * (1 - build) + drop * build - 0.02 * jolt)})
    grip_arms(an, max(0.0, min(1.0, reach)), 0.15 * jolt)
    A.biped_legs(an, 0.0, 1.0, 0.0, 0.0, splay=0.06 + 0.04 * build)


ACTIONS = (("Idle", 120, idle), ("Walk", WALK_T, walk), ("Run", RUN_T, run),
           ("Transform", TRANSFORM_T, transform, {"loop": False}), ("TransformLoop", TRANSFORM_LOOP_T, transform_loop))


def main(blend, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    A.build_actions(bpy.data.objects["StandIn_Rig"], ACTIONS)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    for name, length, *_ in ACTIONS:
        print(f"{name}: {length} frames ({length / A.FPS:.2f} s)"
              + (f", ground speed {SPEEDS[name]:.2f} m/s" if name in SPEEDS else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
