#!/usr/bin/env python3
"""The stack's Form and Scatter: litterlings crawling up onto each other to make the stack, and
the stack breaking back up into litterlings.

Form (120 frames): the creatures stand on the floor in a ring round it, facing in. The dark mass
that holds them together rises up out of the floor in the middle, and from the legs up they
scuttle in to its foot, turn up onto it and crawl up over the ones already in place to their own
spot, and settle there; the hands and feet come up with the mass. The head creatures go on last;
it rears up, arms flung wide, mouth open, and settles into the first frame of Idle.

Scatter (84 frames): from the first frame of Idle it shudders and tightens, then lets go: from
the top down the creatures crawl fast down it to the floor, turn the right way up and scuttle
outward, and stop in a ring round it, facing out, while the mass slumps and sinks into the floor.

Nothing hops and nothing floats: on the floor every creature rests on it, and on the way up or
down it keeps to the outside of the stack, belly to it. In the game: litterlings can run to the
creatures' places on Form's first frame and be swapped for the stack, and at the end of Scatter
the stack can be swapped for litterlings where its creatures stopped (each rides its Slot_ bone:
read its TransformedWorldCFrame). The mass is under the floor at both of those moments.

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

FORM_T, SCATTER_T = 120, 84
REST = 0.95  # a creature resting on the floor: its centre this many of its radii up
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
    # where each one stands on the floor: before Form, in two staggered rings round it facing
    # in; after Scatter, in a wider pair of rings facing out. Evenly round, in the same order as
    # their places on the body, so their paths in and out don't cross. Nothing on top of anything.
    rng = random.Random(9)
    order = sorted(MOVERS, key=lambda n: math.atan2(SLOTS[n][0].x, -SLOTS[n][0].y))
    a0 = math.atan2(SLOTS[order[0]][0].x, -SLOTS[order[0]][0].y)
    POSES["start"], POSES["ring"] = {}, {}
    for i, name in enumerate(order):
        size = SLOTS[name][1]
        a = a0 + math.pi * 2 * (i + 0.5) / len(order) + rng.uniform(-0.06, 0.06)
        out = Vector((math.sin(a), -math.cos(a), 0))
        r = (1.3 if i % 2 else 1.65) + rng.uniform(-0.05, 0.05)
        POSES["start"][name] = (out * r + UP * size * REST, out)
        a2 = a + rng.uniform(-0.06, 0.06)
        out2 = Vector((math.sin(a2), -math.cos(a2), 0))
        r2 = (1.45 if i % 2 else 1.85) + rng.uniform(-0.08, 0.08)
        POSES["ring"][name] = (out2 * r2 + UP * size * REST, out2)
    POSES["rank"] = {n: k for k, n in enumerate(sorted(MOVERS, key=lambda n: (n.startswith("Head"), SLOTS[n][0].z)))}


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


def attached(an):
    """Where every creature sits on the body now (its own frame, armature space)."""
    bpy.context.view_layer.update()
    return {n: an.pb[f"Slot_{n}"].matrix @ POSES["off"][n] for n in SLOTS}


def flat(v):
    return Vector((v.x, v.y, 0.0))


def axis_at(att, z):
    """The middle of the stack at height z (it leans and sways)."""
    pts = [F.translation for F in att.values() if abs(F.translation.z - z) < 0.3]
    if not pts:
        return Vector((0.0, 0.05, z))
    m = sum(pts, Vector()) / len(pts)
    return Vector((m.x, m.y, z))


def reach_out(att, z, axis, skip):
    """How far out from its middle the stack's creatures reach at height z."""
    r = 0.15
    for n, F in att.items():
        p = F.translation
        size = SLOTS[n][1]
        if n != skip and abs(p.z - z) < size + 0.06:
            r = max(r, (flat(p) - flat(axis)).length + size * 0.85)
    return r


def frame_at(p, front, up):
    return Matrix.Translation(p) @ C.frame(front, up).to_4x4()


def blend_frames(A_, B_, t):
    qa, qb = A_.to_quaternion(), B_.to_quaternion()
    if qa.dot(qb) < 0:
        qb = -qb
    return Matrix.Translation(A_.translation.lerp(B_.translation, t)) @ qa.slerp(qb, t).to_matrix().to_4x4()


def scuttle(F, f, amount, seed):
    """A rigid little body scuttling: it waggles from side to side and bobs as its legs go."""
    if amount <= 0:
        return F
    ph = f * 2.4 + seed
    q = Quaternion(F.to_3x3() @ Vector((0, 0, 1)), math.radians(9 * amount * math.sin(ph)))
    side = F.to_3x3() @ Vector((1, 0, 0))
    M = Matrix.Translation(F.translation + side * 0.012 * amount * math.sin(ph) + UP * 0.006 * amount * abs(math.sin(ph)))
    return M @ (q.to_matrix() @ F.to_3x3()).to_4x4()


def wall(att, name, p, toward):
    """A creature on the side of the stack at p, belly to it, heading for `toward` (up or down)."""
    axis = axis_at(att, p.z)
    out = flat(p) - flat(axis)
    out = out.normalized() if out.length > 1e-4 else Vector((0, -1, 0))
    up = (out + UP * 0.25).normalized()
    head = toward - up * toward.dot(up)
    return out, axis, (head.normalized() if head.length > 1e-4 else UP), up


def on_body(att, name, P0, v, skip):
    """A point on the way from P0 (at the stack's foot) to the creature's place (v 0..1), kept to
    the outside of the creatures already on it."""
    PS = att[name].translation
    pl = P0.lerp(PS, v)
    axis = axis_at(att, pl.z)
    r_line = (flat(pl) - flat(axis)).length
    r_out = reach_out(att, pl.z, axis, skip) + SLOTS[name][1] * 0.9
    k = ramp(v, 0.7, 1.0)
    r = r_line * k + max(r_line, r_out) * (1 - k)
    d = flat(pl) - flat(axis)
    d = d.normalized() if d.length > 1e-4 else flat(PS - axis).normalized()
    return Vector((axis.x, axis.y, pl.z)) + d * r


def set_creature(an, name, F):
    pb = an.pb[f"Slot_{name}"]
    pb.matrix = F @ POSES["off"][name].inverted()
    pb.scale = (1, 1, 1)


STATE = {}


def form(an, phi, f):
    setup(an)
    if f == 0:
        STATE.clear()
    rise = ramp(f, 24, 84)
    rr = ramp(f, 86, 94) * (1 - ramp(f, 98, 112))
    sink = 1 - ramp(f, 6, 42)
    body(an, rise, rr, sink)
    if f >= 112:  # the last frames settle exactly onto Idle's first frame
        for n in SLOTS:
            an.pb[f"Slot_{n}"].rotation_quaternion = POSES["idle"][f"Slot_{n}"][0]
        return
    an.fk(LA.creatures(f / 37.0, 4 + 10 * ramp(f, 0, 10) * (1 - ramp(f, 88, 110)), look=10.0))
    att = attached(an)
    for name in MOVERS:
        size = SLOTS[name][1]
        rank = POSES["rank"][name]
        p0, out = POSES["start"][name]
        t_go = 4 + rank * 1.45
        t_foot = t_go + 14
        seed = rank * 1.7
        foot = Vector((0.0, 0.05, 0.0)) + out * (0.42 + size) + UP * size * REST
        floor_start = frame_at(p0, -out, UP)
        if f < t_go:  # waiting on the floor, breathing
            set_creature(an, name, scuttle(floor_start, f, 0.15, seed))
            continue
        if f < t_foot:  # scuttling in to the foot of the stack
            s_ = ease((f - t_go) / (t_foot - t_go))
            F = frame_at(p0.lerp(foot, s_), -out, UP)
            set_creature(an, name, scuttle(F, f, math.sin(math.pi * s_) + 0.3, seed))
            continue
        # up the stack, once its place on the body is up out of the floor
        st = STATE.setdefault(name, {})
        if "climb" not in st:
            if att[name].translation.z < size * 1.2:
                set_creature(an, name, scuttle(frame_at(foot, -out, UP), f, 0.4, seed))  # waiting at the foot
                continue
            st["climb"] = f
            st["dur"] = 8 + 9 * max(0.3, SLOTS[name][0].z)
        v = (f - st["climb"]) / st["dur"]
        if v >= 1.0:  # in its place, squirming as it settles
            k = f - st["climb"] - st["dur"]
            if k < 8:
                F = att[name]
                q = Quaternion(F.to_3x3() @ Vector((1, 0, 0)), math.radians(10 * math.exp(-0.4 * k) * math.sin(1.3 * k)))
                set_creature(an, name, Matrix.Translation(F.translation) @ (q.to_matrix() @ F.to_3x3()).to_4x4())
            continue
        ve = ease(v)
        p = on_body(att, name, foot, ve, name)
        _o, _a, front, up = wall(att, name, p, UP)
        F = frame_at(p, front, up)
        if v < 0.18:  # turning up off the floor onto the stack
            F = blend_frames(frame_at(foot, -out, UP), F, ease(v / 0.18))
        if v > 0.75:  # turning into its own place
            F = blend_frames(F, att[name], ease((v - 0.75) / 0.25))
        set_creature(an, name, scuttle(F, f, 1.0 - ramp(v, 0.8, 1.0), seed))


def scatter(an, phi, f):
    setup(an)
    shudder = ramp(f, 0, 10) * (1 - ramp(f, 12, 14))
    rise = 1 - 0.12 * ramp(f, 0, 10) - 0.88 * ramp(f, 12, 46)  # crouches, and keeps going down as it lets go
    sink = ramp(f, 40, 76)
    body(an, rise, 0.0, sink)
    if f == 0:
        for n in SLOTS:
            an.pb[f"Slot_{n}"].rotation_quaternion = POSES["idle"][f"Slot_{n}"][0]
        return
    an.fk(LA.creatures(f / 37.0, 4 + 14 * shudder + 6 * ramp(f, 12, 20), look=10.0))
    tremble = 3.0 * shudder
    for n in SLOTS:
        pb = an.pb[f"Slot_{n}"]
        pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(Vector((1, 0, 0)), math.radians(tremble * math.sin(f * 2.3 + len(n))))
    att = attached(an)
    top = len(MOVERS) - 1
    for name in MOVERS:
        size = SLOTS[name][1]
        rank = top - POSES["rank"][name]  # the top ones let go first
        p_end, out = POSES["ring"][name]
        seed = rank * 1.3
        t_off = 12 + rank * 0.9
        down = 5 + 5 * max(0.3, SLOTS[name][0].z)
        t_floor = t_off + down
        t_end = t_floor + 16
        foot = Vector((0.0, 0.05, 0.0)) + out * (0.42 + size) + UP * size * REST
        if f < t_off:
            continue  # still holding on
        if f < t_floor:  # crawling fast down the stack, head first
            v = 1 - ((f - t_off) / down) ** 1.6  # speeding up as it goes
            p = on_body(att, name, foot, v, name)
            _o, _a, front, up = wall(att, name, p, -UP)
            F = frame_at(p, front, up)
            if v > 0.8:  # letting go of its place
                F = blend_frames(att[name], F, ease((1 - v) / 0.2))
            if v < 0.15:  # turning the right way up as it reaches the floor
                F = blend_frames(F, frame_at(foot, out, UP), ease((0.15 - v) / 0.15))
            set_creature(an, name, scuttle(F, f, 1.0, seed))
            continue
        s_ = ease((f - t_floor) / (t_end - t_floor))
        F = frame_at(foot.lerp(p_end, s_), out, UP)  # scuttling out, then still
        set_creature(an, name, scuttle(F, f, math.sin(math.pi * min(1.0, s_)) + (0.15 if s_ >= 1 else 0.3), seed))


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
