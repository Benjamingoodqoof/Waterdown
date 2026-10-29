#!/usr/bin/env python3
"""Keyframes the poster monster's Idle, Walk and Run into the .blend (in place, 30 fps,
looping, last frame equal to the first).

The legs are solved with a two-bone IK every frame so planted feet don't slide; the solve
is written out as plain rotation keys, so the actions are ordinary FK animation that any
exporter can read. Steps are deliberately light: toe-first landings, little bounce, and a
float in the run, because the monster is made of paper.

Usage: python3 animate.py BLEND [OUT_BLEND]
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from posing import bone_quat, hand, mirror  # noqa: E402

FPS = 30
SIDES = (("Left", 1.0), ("Right", -1.0))
PEELS = ("PeelHip", "PeelBack", "PeelChest", "PeelArmL", "PeelShinL", "PeelThighR")

# ground speed each cycle is made for, so feet don't skate (meters per second)
SPEEDS = {}


def wave(phi, freq=1.0, off=0.0):
    return math.sin(2 * math.pi * (freq * phi + off))


def cwave(phi, freq=1.0, off=0.0):
    return math.cos(2 * math.pi * (freq * phi + off))


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def bump(f, a, b, c):
    """0 before frame a, snaps up to 1 by b, eases back to 0 by c."""
    if f <= a or f >= c:
        return 0.0
    return ease((f - a) / (b - a)) if f < b else 1.0 - ease((f - b) / (c - b))


def bone_frame(head, tail, fwd):
    """Armature-space matrix for a bone from head to tail with its Z axis toward fwd."""
    y = (tail - head).normalized()
    z = (fwd - y * fwd.dot(y)).normalized()
    m = Matrix((y.cross(z), y, z)).transposed().to_4x4()
    m.translation = head
    return m


class Animator:
    def __init__(self, rig):
        self.rig = rig
        self.pb = rig.pose.bones
        self.prev = {}

    def reset(self):
        for pb in self.pb:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)

    def fk(self, pose, loc=None):
        for name, rots in pose.items():
            if name in self.pb:
                self.pb[name].rotation_quaternion = bone_quat(self.pb[name].bone, rots)
        for name, off in (loc or {}).items():
            pb = self.pb[name]
            pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)

    def leg(self, side, ankle, pitch_deg, splay):
        """Two-bone IK: thigh and shin reach `ankle` (armature space) with the knee bending
        forward; the foot is pitched about X from its rest angle (+ points the toes down)."""
        bpy.context.view_layer.update()
        th, sh, ft = (self.pb[f"{side}{b}"] for b in ("UpperLeg", "LowerLeg", "Foot"))
        hip = th.head.copy()
        l1, l2 = th.bone.length, sh.bone.length
        d = ankle - hip
        dist = min(d.length, (l1 + l2) * 0.999)
        u = d.normalized()
        fwd = Vector((splay, -1.0, 0.0)).normalized()
        w = (fwd - u * fwd.dot(u)).normalized()
        a = math.acos(max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))))
        knee = hip + (u * math.cos(a) + w * math.sin(a)) * l1
        reach = hip + u * dist
        for pb, h, t in ((th, hip, knee), (sh, knee, reach)):
            pb.matrix = bone_frame(h, t, fwd)
            pb.location = (0, 0, 0)
            bpy.context.view_layer.update()
        rot = Matrix.Rotation(math.radians(pitch_deg), 4, "X") @ ft.bone.matrix_local.to_3x3().to_4x4()
        rot.translation = reach
        ft.matrix = rot
        ft.location = (0, 0, 0)

    def key(self, frame):
        bpy.context.view_layer.update()
        for pb in self.pb:
            q = pb.rotation_quaternion.copy()
            prev = self.prev.get(pb.name)
            if prev is not None and prev.dot(q) < 0:
                q.negate()
                pb.rotation_quaternion = q
            self.prev[pb.name] = q.copy()
            pb.keyframe_insert("rotation_quaternion", frame=frame, group=pb.name)
            if pb.name == "LowerTorso":
                pb.keyframe_insert("location", frame=frame, group=pb.name)


# ---------------------------------------------------------------- gait helpers
def foot_path(phi, duty, stride, lift, dangle):
    """In-place foot: (y offset, height, toe pitch in degrees) at cycle phase phi.
    Stance slides the foot back at ground speed; it lands toes first and rolls off the toes."""
    if phi < duty:
        s = phi / duty
        y, z, pitch = -stride / 2 + stride * s, 0.0, 0.0
        if s < 0.12:  # toes touched first; the heel settles
            z, pitch = 0.04 * (1 - s / 0.12), 12 * (1 - s / 0.12)
        elif s > 0.8:  # heel peels off the floor
            t = (s - 0.8) / 0.2
            z, pitch = 0.07 * t, 26 * t
        return y, z, pitch
    s = (phi - duty) / (1 - duty)
    y = stride / 2 - stride * ease(s)
    z = 0.07 * (1 - s) + 0.04 * s + lift * math.sin(math.pi * s) ** 0.9
    pitch = 26 * (1 - s) ** 2 + dangle * math.sin(math.pi * s) + 12 * s * s
    return y, z, pitch


def legs(an, phi, duty, stride, lift, dangle, splay, stance_x=0.015):
    for side, sx in SIDES:
        ph = (phi + (0.0 if side == "Left" else 0.5)) % 1.0
        y, z, pitch = foot_path(ph, duty, stride, lift, dangle)
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, Vector((rest.x + sx * stance_x, rest.y + y, rest.z + z)), pitch, splay * sx)


def flaps(phi, freq, base1, amp1, base2, amp2):
    out = {}
    for k, name in enumerate(PEELS):
        out[f"{name}1"] = [("lx", base1 + amp1 * wave(phi, freq, k * 0.17))]
        out[f"{name}2"] = [("lx", base2 + amp2 * wave(phi, freq, k * 0.17 - 0.15))]
    return out


# ---------------------------------------------------------------- the three actions
def idle(an, phi, f):
    """Hunched and still, a slow sway; the head drifts, then snaps to a new angle."""
    br = wave(phi)
    tw = bump(f, 64, 67, 104)  # the head twitch
    shrug = bump(f, 40, 52, 84)
    flick = bump(f, 28, 30, 40) + bump(f, 92, 94, 101)
    pose = {
        "LowerTorso": [("x", 4 + br)],
        "Spine": [("x", 10 + 1.5 * br), ("y", -3)],
        "UpperTorso": [("x", 16 + 2 * br), ("y", 5)],
        "Neck": [("x", 24 - br)],
        "Head": [("x", -16 + 3 * br - 6 * tw), ("y", 21 + 6 * wave(phi, 1, 0.2) - 16 * tw), ("z", -10 + 24 * tw)],
        "LeftShoulder": [("x", 8), ("y", -7 * shrug)],
        "RightShoulder": mirror([("x", 8)], "Right"),
    }
    for side, sx in SIDES:
        pose[f"{side}UpperArm"] = mirror([("y", 6), ("x", -6 + 2 * wave(phi, 1, -0.15))], side)
        pose[f"{side}LowerArm"] = [("x", -16 + 3 * wave(phi, 1, -0.25))]
        pose[f"{side}Hand"] = [("x", -8 + 4 * wave(phi, 1, -0.35))]
    pose.update(hand("Left", (10 + 4 * wave(phi, 2), 14, 12), 6))
    pose.update(hand("Right", (14, 18, 16), 4, jitter={"Index": 38 * flick, "Middle": 22 * flick}))
    pose.update(flaps(phi, 2, 3, 4, 5, 6))
    an.fk(pose, {"LowerTorso": (0.006 * wave(phi, 1, 0.1), 0.0, -0.07 + 0.008 * br)})
    an.leg("Left", Vector((0.147, -0.07, 0.10)), 0.0, 0.15)
    an.leg("Right", Vector((-0.135, 0.06, 0.10)), 0.0, -0.15)


def walk(an, phi, f):
    """A slow crouched stalk: light toe-first steps, arms dragging, the head steady and tilted."""
    duty, stride = 0.6, 0.86
    tw = bump(f, 20, 22, 29)  # a small twitch every cycle
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 10 + 1.5 * cwave(phi, 2)), ("y", -3 * wave(phi, 1, -0.05)), ("z", -5 * swing)],
        "Spine": [("x", 8), ("z", 2 * swing)],
        "UpperTorso": [("x", 14), ("y", 3), ("z", 6 * swing)],
        "Neck": [("x", 22 + 2 * wave(phi, 2, -0.1))],
        "Head": [("x", -14 - 4 * tw), ("y", 18 + 4 * wave(phi, 1, 0.3) - 9 * tw), ("z", -6 * swing + 14 * tw)],
        "LeftShoulder": [("x", 8)],
        "RightShoulder": mirror([("x", 6), ("y", 4)], "Right"),  # one shoulder hangs lower
    }
    for side, sx in SIDES:
        fwd_phase = 0.5 if side == "Left" else 0.0  # each arm swings with the opposite leg
        amp = 14 if side == "Left" else 10
        a = cwave(phi, 1, -(fwd_phase + 0.06))
        pose[f"{side}UpperArm"] = mirror([("y", 4), ("x", -6 - amp * a)], side)
        pose[f"{side}LowerArm"] = [("x", -12 - 10 * (0.5 + 0.5 * cwave(phi, 1, -(fwd_phase + 0.18))))]
        pose[f"{side}Hand"] = [("x", -6 + 8 * wave(phi, 1, -(fwd_phase + 0.26)))]
    pose.update(hand("Left", (12 + 4 * wave(phi, 1), 16, 14), 6))
    pose.update(hand("Right", (16, 20 + 5 * wave(phi, 1, 0.4), 18), 4))
    pose.update(flaps(phi, 2, 4, 6, 6, 9))
    sway = 0.03 * wave(phi, 1, -0.05)
    bob = -0.12 + 0.016 * (0.5 - 0.5 * cwave(phi, 2))
    an.fk(pose, {"LowerTorso": (sway, 0.0, bob)})
    legs(an, phi, duty, stride, 0.16, 18, 0.12)
    SPEEDS["Walk"] = stride / (duty * WALK_T / FPS)


def run(an, phi, f):
    """A lunging run: deep lean, arms clawing forward in turn, head locked on; light,
    floating steps with a moment in the air."""
    duty, stride = 0.36, 1.05
    swing = cwave(phi)
    pose = {
        "LowerTorso": [("x", 30 + 3 * cwave(phi, 2, -0.1)), ("y", -4 * wave(phi, 1, -0.18)), ("z", -9 * swing)],
        "Spine": [("x", 16), ("z", 3 * swing)],
        "UpperTorso": [("x", 14), ("y", 3 * wave(phi, 1, 0.1)), ("z", 10 * swing)],
        "Neck": [("x", -16 + 4 * wave(phi, 2))],
        "Head": [("x", -44 + 3 * wave(phi, 2, 0.15)), ("y", 14 + 5 * wave(phi, 1, 0.1) + 2 * wave(phi, 3)),
                 ("z", -7 * swing + 3 * wave(phi, 3, 0.3))],
    }
    for side, sx in SIDES:
        fwd_phase = 0.5 if side == "Left" else 0.0
        reach = 0.5 - 0.5 * cwave(phi, 1, -(fwd_phase + 0.05))  # 1 = arm thrown forward
        pose[f"{side}Shoulder"] = mirror([("x", 6 - 10 * reach)], side)
        pose[f"{side}UpperArm"] = mirror([("y", 8 - 16 * reach), ("x", 40 - 150 * reach)], side)
        pose[f"{side}LowerArm"] = [("x", -8 - 42 * (1 - reach))]
        pose[f"{side}Hand"] = [("x", -12 + 24 * reach)]
        curl = 55 - 60 * reach  # curled while swinging back, claws splayed at the reach
        pose.update(hand(side, (curl, curl * 0.9, curl * 0.8), 22 * reach, thumb=(curl * 0.5,) * 3))
    pose.update(flaps(phi, 4, 10, 12, 15, 18))
    bob = -0.16 - 0.035 * cwave(phi, 2, -0.18)
    an.fk(pose, {"LowerTorso": (0.02 * wave(phi, 1, 0.07), 0.0, bob)})
    legs(an, phi, duty, stride, 0.3, 25, 0.12)
    SPEEDS["Run"] = stride / (duty * RUN_T / FPS)


IDLE_T, WALK_T, RUN_T = 120, 34, 20
ACTIONS = (("Idle", IDLE_T, idle), ("Walk", WALK_T, walk), ("Run", RUN_T, run))


def build(rig):
    an = Animator(rig)
    rig.animation_data_create()
    made = {}
    for name, length, fn in ACTIONS:
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        rig.animation_data.action = act
        an.prev = {}
        for f in range(length + 1):
            an.reset()
            fn(an, f / length, f)
            an.key(f)
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, length
        act.use_cyclic = True
        made[name] = act
    rig.animation_data.action = made["Idle"]
    bpy.context.scene.render.fps = FPS
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, IDLE_T
    return made


def main(blend, out):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    build(rig)
    for name, length, _ in ACTIONS:
        print(f"{name}: {length} frames ({length / FPS:.2f} s)"
              + (f", ground speed {SPEEDS[name]:.2f} m/s" if name in SPEEDS else ""))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1])
