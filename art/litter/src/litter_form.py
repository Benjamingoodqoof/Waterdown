#!/usr/bin/env python3
"""The stack's Form and Scatter: litterlings piling up into the stack, and the stack bursting
back into litterlings.

Form (110 frames): the creatures lie heaped in a ring on the floor, facing in. The dark mass that
holds them together rises up out of the floor in the middle, and as each part of it comes up the
creatures leap onto it and cling in place, from the legs up (the hands and feet come up with the
mass), the body unfolding and standing as it fills. The head creatures go on last; it rears up,
arms flung wide, mouth open, and settles into the first frame of Idle.

Scatter (84 frames): from the first frame of Idle it shudders and tightens, then bursts: the
creatures leap off it from the top down and land in a wider ring around it, skitter outward and
stop, facing out, while the mass slumps into a heap and sinks back into the floor.

In the game: let litterlings run together to a spot, then swap them for the stack playing Form;
and at the end of Scatter swap the stack for litterlings standing where its creatures landed.
The mass is below the floor at the start of Form and the end of Scatter (the floor hides it).

Both are one-shots keyed on the stack's rig, every creature slot keyed in position as well as
rotation. Usage: python3 litter_form.py LITTER_DIR
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
import litter_animate as LA  # noqa: E402
import litter_common as C  # noqa: E402
from anim_core import mirror  # noqa: E402

FORM_T, SCATTER_T = 110, 84
SLOTS = C.slots()
MOVERS = [n for n in SLOTS if not n.endswith(("Arm5", "Leg4"))]  # the hands and feet stay on the mass
SINK = 1.9  # m: how far below the floor the mass goes when it's down
UP = Vector((0, 0, 1))
POSES = {}


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def ramp(f, a, b):
    return ease((f - a) / (b - a)) if b > a else float(f >= b)


def capture(an, fn):
    an.reset()
    fn()
    bpy.context.view_layer.update()
    return {pb.name: (pb.rotation_quaternion.copy(), pb.location.copy()) for pb in an.pb}


def collapsed(an):
    """The mass slumped into a heap: crouched right down, folded over, arms tucked in."""
    pose = {"LowerTorso": [("x", 38)], "UpperTorso": [("x", 58)], "Head": [("x", 28)]}
    for side in ("Left", "Right"):
        pose[f"{side}UpperArm"] = mirror([("x", -35), ("y", 30)], side)
        pose[f"{side}LowerArm"] = [("x", -105)]
        pose[f"{side}Hand"] = [("x", -20)]
        pose.update(LA.fingers(side, 50))
    an.fk(pose, {"LowerTorso": (0.0, -0.05, -0.78)})
    for side in ("Left", "Right"):
        an.leg(side, C.SJ[f"ankle_{side}"], 0.0, 0.3 if side == "Left" else -0.3)


def roar(an):
    """Reared up to its full height, arms flung wide, the head creature's mouth thrown open."""
    pose = {"LowerTorso": [("x", -10)], "UpperTorso": [("x", -16)], "Head": [("x", -26)],
            "LeftUpperArm": [("x", -70), ("y", -60)], "RightUpperArm": [("x", -70), ("y", 60)],
            "LeftLowerArm": [("x", -36)], "RightLowerArm": [("x", -36)], "Slot_Head1": [("x", -30)]}
    for side in ("Left", "Right"):
        pose.update(LA.fingers(side, -12, 1.0))
    an.fk(pose, {"LowerTorso": (0.0, 0.1, 0.08)})
    for side in ("Left", "Right"):
        an.leg(side, C.SJ[f"ankle_{side}"], 0.0, 0.15 if side == "Left" else -0.15)


def setup(an):
    if POSES:
        return
    POSES["coll"] = capture(an, lambda: collapsed(an))
    POSES["idle"] = capture(an, lambda: LA.stack_idle(an, 0.0, 0))
    POSES["roar"] = capture(an, lambda: roar(an))
    # each creature's own frame on its slot bone (constant: the mesh is rigid on the bone)
    POSES["off"] = {}
    for name, (c, size, *_rest, front, up) in SLOTS.items():
        F0 = Matrix.Translation(c) @ C.frame(front, up).to_4x4()
        POSES["off"][name] = an.pb[f"Slot_{name}"].bone.matrix_local.inverted() @ F0
    # where each one lies on the floor: heaped in a ring facing in (before Form), or flung out
    # into a wider ring facing out (after Scatter), at the same bearing as its place on the body
    rng = random.Random(9)
    order = sorted(MOVERS, key=lambda n: math.atan2(SLOTS[n][0].x, -SLOTS[n][0].y))
    POSES["heap"], POSES["ring"] = {}, {}
    for i, name in enumerate(order):
        c, size = SLOTS[name][0], SLOTS[name][1]
        a = math.atan2(c.x, -c.y) + rng.uniform(-0.12, 0.12)
        out = Vector((math.sin(a), -math.cos(a), 0))
        top = i % 3 == 1  # every third one lies on top of the others
        r = (0.5 if top else 0.78) + rng.uniform(-0.06, 0.06)
        p = out * r + UP * (size * 0.8 + (0.24 if top else 0.0))
        face = (-out).lerp(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)), 0.3).normalized()
        POSES["heap"][name] = Matrix.Translation(p) @ C.frame(face, UP + out * (0.35 if top else 0.0)).to_4x4()
        # evenly round the circle (in the same order as their places on the body), near and far
        a2 = math.pi * 2 * (i + 0.5) / len(order) + math.atan2(SLOTS[order[0]][0].x, -SLOTS[order[0]][0].y)
        a2 += rng.uniform(-0.08, 0.08)
        r2 = (1.25 if i % 2 else 1.75) + rng.uniform(-0.1, 0.1)
        out2 = Vector((math.sin(a2), -math.cos(a2), 0))
        POSES["ring"][name] = (out2 * r2 + UP * size * 0.8, out2)


def body(an, rise, rr, sink):
    """The mass: from the heap (rise 0) to standing (1), rearing up by rr, sunk by sink."""
    P = POSES
    for pb in an.pb:
        n = pb.name
        if n.startswith("Slot_") or n not in P["idle"]:
            continue
        qc, lc = P["coll"][n]
        qi, li = P["idle"][n]
        qr, lr = P["roar"][n]
        if qc.dot(qi) < 0:
            qi = -qi
        q = qc.slerp(qi, rise)
        if q.dot(qr) < 0:
            qr = -qr
        pb.rotation_quaternion = q.slerp(qr, rr)
        pb.location = lc.lerp(li, rise).lerp(lr, rr)
    lt = an.pb["LowerTorso"]
    lt.location = lt.location + lt.bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, -SINK * sink))
    for side, sx in (("Left", 1), ("Right", -1)):
        foot = C.SJ[f"ankle_{side}"] + Vector((0.02 * sx, -0.04 if side == "Left" else 0.05, 0)) * rise
        an.leg(side, foot + Vector((0, 0, -SINK * sink)), 0.0, 0.15 * sx)


def place(an, f, name, w, start, hop, wobble=0.0):
    """Puts a creature between the floor (w 0: its frame `start`) and its slot on the body
    (w 1), on an arc `hop` m high; wobble: the jolt of landing (degrees about its own x)."""
    pb = an.pb[f"Slot_{name}"]
    O = POSES["off"][name]
    bpy.context.view_layer.update()
    att = pb.matrix @ O  # where it sits on the body now
    if w >= 1.0 and not wobble:
        return
    t = ease(w)
    p = start.translation.lerp(att.translation, t) + UP * hop * math.sin(math.pi * min(1.0, max(0.0, w)))
    q0, q1 = start.to_quaternion(), att.to_quaternion()
    if q0.dot(q1) < 0:
        q1 = -q1
    q = q0.slerp(q1, t)
    if wobble:
        q = q @ Quaternion(Vector((1, 0, 0)), math.radians(wobble))
    F = Matrix.Translation(p) @ q.to_matrix().to_4x4()
    pb.matrix = F @ O.inverted()
    pb.scale = (1, 1, 1)


def heights():
    zs = {n: SLOTS[n][0].z for n in MOVERS}
    return zs, min(zs.values()), max(zs.values())


def form(an, phi, f):
    setup(an)
    rise = ramp(f, 18, 74)
    rr = ramp(f, 76, 84) * (1 - ramp(f, 88, 104))
    sink = 1 - ramp(f, 4, 36)
    body(an, rise, rr, sink)
    bristle = 4 + 10 * ramp(f, 0, 10) * (1 - ramp(f, 80, 104))
    if f >= 104:  # the last frames settle exactly onto Idle's first frame
        for n in SLOTS:
            an.pb[f"Slot_{n}"].rotation_quaternion = POSES["idle"][f"Slot_{n}"][0]
    else:
        an.fk(LA.creatures(f / 37.0, bristle, look=10.0))
    zs, z0, z1 = heights()
    rng = random.Random(3)
    for name in sorted(MOVERS):
        t0 = 24 + (zs[name] - z0) / (z1 - z0) * 40 + rng.uniform(-2, 2)  # once the mass is out of the floor
        if name.startswith("Head"):
            t0 = 66 if name == "Head2" else 70
        start = POSES["heap"][name].copy()
        jit = math.sin(f * 1.7 + len(name)) * 0.012 * (1 - ramp(f, t0 - 3, t0))
        squash = 0.03 * math.sin(math.pi * min(1.0, max(0.0, (f - (t0 - 4)) / 4)))  # the crouch before it leaps
        start.translation = start.translation + UP * (jit - squash)
        w = (f - t0) / 9.0
        land = f - (t0 + 9)
        wob = 18 * math.exp(-0.45 * land) * math.cos(0.9 * land) if 0 <= land < 10 else 0.0
        place(an, f, name, min(1.0, w), start, 0.22 + 0.25 * max(0.0, zs[name] - 1.0), wob)


def scatter(an, phi, f):
    setup(an)
    shudder = ramp(f, 0, 10) * (1 - ramp(f, 12, 14))
    rise = 1 - 0.12 * shudder - 0.88 * ramp(f, 12, 42)
    sink = ramp(f, 36, 72)
    body(an, rise, 0.0, sink)
    if f == 0:
        for n in SLOTS:
            an.pb[f"Slot_{n}"].rotation_quaternion = POSES["idle"][f"Slot_{n}"][0]
    else:
        an.fk(LA.creatures(f / 37.0, 4 + 14 * shudder + 6 * ramp(f, 12, 20), look=10.0))
        tremble = 3.0 * shudder
        for n in SLOTS:
            pb = an.pb[f"Slot_{n}"]
            pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(Vector((1, 0, 0)), math.radians(tremble * math.sin(f * 2.3 + len(n))))
    zs, z0, z1 = heights()
    rng = random.Random(5)
    for name in sorted(MOVERS):
        t0 = 12 + (z1 - zs[name]) / (z1 - z0) * 18 + rng.uniform(-1.5, 1.5)
        if f < t0:
            continue
        p, out = POSES["ring"][name]
        slide = 0.28 * ramp(f, t0 + 10, t0 + 18)
        skitter = 0.02 * math.sin(f * 2.1 + len(name)) * (ramp(f, t0 + 10, t0 + 12) - ramp(f, t0 + 16, t0 + 20))
        end = Matrix.Translation(p + out * slide + out.cross(UP) * skitter) @ C.frame(out, UP).to_4x4()
        land = f - (t0 + 10)
        wob = 14 * math.exp(-0.5 * land) * math.cos(1.0 * land) if 0 <= land < 8 else 0.0
        w = 1 - (f - t0) / 10.0
        place(an, f, name, max(0.0, w), end, 0.35 + 0.15 * zs[name], wob)


def main(litter_dir):
    blend = os.path.join(os.path.abspath(litter_dir), "stack.blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    rig = bpy.data.objects["Stack_Rig"]
    loc = ("LowerTorso",) + tuple(f"Slot_{n}" for n in SLOTS)
    A.build_actions(rig, (("Form", FORM_T, form, {"loop": False}), ("Scatter", SCATTER_T, scatter, {"loop": False})), loc)
    if "Idle" in bpy.data.actions:
        rig.animation_data.action = bpy.data.actions["Idle"]
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("Form", FORM_T, "frames; Scatter", SCATTER_T, "frames")


if __name__ == "__main__":
    main(sys.argv[1])
