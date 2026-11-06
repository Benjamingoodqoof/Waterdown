"""Hands that actually grip an R6 player: the palm flat on the part, the fingers wrapped round it.

A grip is described on the R6 part being grabbed (head, torso, an arm), in that part's own frame
in studs: a point on its surface, the surface's outward normal there, and the way the fingers
point along it. grip_hand() puts the monster's palm on that point, facing into the part, with
the fingers pointing that way; wrap_fingers() then curls each finger until it touches the part
(or as far as it goes), so fingers rest on the surface instead of poking through or floating.

The R6 parts are boxes (torso 2x2x1, arms and legs 1x2x1) and the head is a rounded cylinder,
1.2 studs across and 1.2 tall, as on the R6 rig.
"""
import math

import bpy
from mathutils import Vector

import anim_core as A
import kill_core as K

SIZES = {"Torso": Vector((2, 2, 1)), "Right Arm": Vector((1, 2, 1)), "Left Arm": Vector((1, 2, 1)),
         "Right Leg": Vector((1, 2, 1)), "Left Leg": Vector((1, 2, 1))}
HEAD_R, HEAD_HALF, HEAD_ROUND = 0.6, 0.6, 0.25
FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")
AXIS = {"x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "z": Vector((0, 0, 1)), "-z": Vector((0, 0, -1))}


def sdf_box(p, half):
    q = Vector((abs(p.x) - half.x, abs(p.y) - half.y, abs(p.z) - half.z))
    outside = Vector((max(q.x, 0), max(q.y, 0), max(q.z, 0))).length
    return outside + min(max(q.x, q.y, q.z), 0.0)


def sdf_head(p):
    """The R6 head: a cylinder about its up (y) axis with rounded rims."""
    r = math.hypot(p.x, p.z)
    dx, dy = r - HEAD_R + HEAD_ROUND, abs(p.y) - HEAD_HALF + HEAD_ROUND
    return min(max(dx, dy), 0.0) + math.hypot(max(dx, 0.0), max(dy, 0.0)) - HEAD_ROUND


def part_sdf(part, p):
    return sdf_head(p) if part == "Head" else sdf_box(p, SIZES[part] / 2)


class Body:
    """An R6 player's parts in the monster's armature space (meters), for distances and grips."""

    def __init__(self, pl, parts, k):
        self.k = k
        self.m = {name: pl.to_blender(cf) for name, cf in parts.items() if name in SIZES or name == "Head"}
        self.inv = {name: m.inverted() for name, m in self.m.items()}

    def distance(self, p, only=None):
        """Signed distance (meters) from p to the nearest part (negative inside)."""
        return min(part_sdf(n, self.inv[n] @ p) * self.k for n in (only or self.m))

    def surface(self, part, point, normal, along):
        """A grip spot on a part (its frame, studs) -> (point, outward normal, finger direction),
        armature space."""
        m = self.m[part]
        r = m.to_3x3().normalized()
        n = (r @ Vector(normal)).normalized()
        d = r @ Vector(along)
        d = (d - n * d.dot(n)).normalized()
        return m @ Vector(point), n, d


def palm(an, side, thick):
    """The hand's palm: (point on the palm's surface, finger direction, way the palm faces)."""
    bpy.context.view_layer.update()
    pb = an.pb[f"{side}Hand"]
    faces = (pb.matrix.to_3x3() @ AXIS[K.palm_axis(an, side)]).normalized()
    d = (pb.tail - pb.head).normalized()
    return pb.head + (pb.tail - pb.head) * 0.6 + faces * thick, d, faces


def grip_hand(an, side, point, normal, along, pole, thick, weight=1.0, free_wrist=None):
    """Puts the palm flat on `point` (normal: the surface's outward normal there), fingers along
    `along`, the elbow toward `pole`. weight < 1 blends from free_wrist (where the hand would
    otherwise be) onto the grip."""
    L = (an.pb[f"{side}Hand"].tail - an.pb[f"{side}Hand"].head).length
    wrist = point + normal * thick - along * 0.6 * L
    if free_wrist is not None and weight < 1:
        wrist = free_wrist.lerp(wrist, weight)
    hand_dir, faces = along, -normal
    for _ in range(3):
        K.reach(an, side, wrist, pole, hand_dir, faces)
        p, _, _ = palm(an, side, thick)
        miss = (point if weight >= 1 else (free_wrist + along * 0.6 * L).lerp(point, weight)) - p
        if miss.length < 0.003:
            break
        wrist = wrist + miss


def _chain(an, side, finger):
    return [an.pb[f"{side}{finger}{s}"] for s in (1, 2, 3) if f"{side}{finger}{s}" in an.pb]


def _fk_points(an, chain, quats):
    """Where a finger's joints and tip are with these rotations (armature space), worked out
    directly from the hand's pose (no scene update per try)."""
    pts = []
    parent = chain[0].parent
    M = parent.matrix.copy()
    Mp_rest = parent.bone.matrix_local
    for pb, q in zip(chain, quats):
        local = Mp_rest.inverted() @ pb.bone.matrix_local
        M = M @ local @ q.to_matrix().to_4x4()
        Mp_rest = pb.bone.matrix_local
        L = pb.bone.length
        pts += [M @ Vector((0, L * 0.5, 0)), M @ Vector((0, L, 0))]
    return pts


def wrap_fingers(an, side, body, open_curl=-5.0, max_curl=95.0, margin=0.006, spread=0.0, weight=1.0,
                 thumb_open=-45.0, thumb_max=60.0):
    """Wraps each finger of a hand round the player, joint by joint, as a hand closes on
    something: the first knuckle bends until the finger meets the body (or as far as it goes),
    then the next joint, then the next, so the whole finger lies along the surface and the tip
    rests on it. weight < 1 blends from the pose the fingers already have toward the wrap (the
    hand closing on, or letting go of, the body). Sets the finger bones and returns
    {finger: [curl per joint]}."""
    bpy.context.view_layer.update()
    hand = an.pb[f"{side}Hand"].bone
    pal = (hand.matrix_local.to_3x3() @ AXIS[K.palm_axis(an, side)]).normalized()
    out = {}
    for i, fname in enumerate(FINGERS):
        chain = _chain(an, side, fname)
        if not chain:
            continue
        lo0, hi = (thumb_open, thumb_max) if fname == "Thumb" else (open_curl, max_curl)
        axes = []
        for pb in chain:
            y = (pb.bone.matrix_local.to_3x3() @ Vector((0, 1, 0))).normalized()
            axes.append(y.cross(pal).normalized())
        fan = (spread * (i - 2.5) * (1 if side == "Left" else -1)) if fname != "Thumb" else 0.0

        def quats(curls):
            qs = []
            for j, (pb, ax, c) in enumerate(zip(chain, axes, curls)):
                rots = [(ax, c)] + ([(pal, fan)] if j == 0 and fan else [])
                qs.append(A.bone_quat(pb.bone, rots))
            return qs

        def clear(curls, j):
            pts = _fk_points(an, chain, quats(curls))[2 * j:]  # this joint's segment and the ones after
            return min(body.distance(p) for p in pts) >= margin

        curls = [lo0] * len(chain)
        for j in range(len(chain)):
            test = list(curls)
            test[j] = hi
            if clear(test, j):
                curls[j] = hi
                continue
            test[j] = lo0
            if not clear(test, j):
                # touching even open: take the most closed curl that clears, else the one that
                # goes least far in (never a finger left sticking out straight)
                best, best_d = lo0, -1e9
                for k in range(1, 11):
                    test[j] = lo0 + (hi - lo0) * k / 10
                    d = min(body.distance(p) for p in _fk_points(an, chain, quats(test))[2 * j:])
                    if d >= margin:
                        best, best_d = test[j], 1e9
                    elif best_d < 1e9 and d > best_d:
                        best, best_d = test[j], d
                curls[j] = best
                continue
            lo, top = lo0, hi
            for _ in range(8):
                mid = (lo + top) / 2
                test[j] = mid
                if clear(test, j):
                    lo = mid
                else:
                    top = mid
            curls[j] = lo
        for pb, q in zip(chain, quats(curls)):
            if weight < 1:
                q0 = pb.rotation_quaternion.copy()
                if q0.dot(q) < 0:
                    q = -q
                q = q0.slerp(q, weight)
            pb.rotation_quaternion = q
        out[fname] = curls
    bpy.context.view_layer.update()
    return out
