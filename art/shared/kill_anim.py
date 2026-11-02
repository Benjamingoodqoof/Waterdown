"""Pose-to-pose tools for the kill animations (on top of kill_core).

A kill is keyed like a hand-animated shot: key poses at chosen frames, eased between them, with
arcs on paths, and overlap/follow-through from lagging the chain (head and limbs sample their
parent's motion a few frames late).

- Track(keys): a value keyed at frames; each key says how the motion eases INTO it:
    "io"  slow in and out (the default)      "o"  fast start, settling (hits, snaps)
    "o3"  very fast start, long settle        "i"  slow start, accelerating (falls, wind-ups)
    "ob"  fast, overshoots and settles back   "lin" linear       "hold" steps at the key
  Vector tracks with arc=True follow a Catmull-Rom curve through the keys (arcs, not lines).
- R6 victim poses: torso keyed by its hip pivot (so the feet stay put when it leans) or by a
  grip point held by the monster; limbs keyed as directions; the head keyed as an offset from
  looking at a target. Limbs and head use the torso's orientation from a few frames earlier,
  so they drag behind when the body is jerked around (follow-through).
"""
import math

from mathutils import Matrix, Quaternion, Vector

import kill_core as K


def _back(t, s=1.9):
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


EASE = {
    "lin": lambda t: t,
    "io": lambda t: t * t * (3 - 2 * t),
    "i": lambda t: t * t,
    "i3": lambda t: t * t * t,
    "o": lambda t: 1 - (1 - t) ** 2,
    "o3": lambda t: 1 - (1 - t) ** 3,
    "o5": lambda t: 1 - (1 - t) ** 5,
    "ob": _back,
    "hold": lambda t: 1.0 if t >= 1 else 0.0,
}


def _vec(v):
    if isinstance(v, (int, float)):
        return float(v)
    return Vector(v)


class Track:
    def __init__(self, *keys, arc=False):
        self.keys = sorted([(k[0], _vec(k[1]), k[2] if len(k) > 2 else "io") for k in keys], key=lambda k: k[0])
        self.arc = arc

    def __call__(self, f):
        ks = self.keys
        if f <= ks[0][0]:
            return ks[0][1].copy() if isinstance(ks[0][1], Vector) else ks[0][1]
        if f >= ks[-1][0]:
            return ks[-1][1].copy() if isinstance(ks[-1][1], Vector) else ks[-1][1]
        for i in range(len(ks) - 1):
            f0, a, _ = ks[i]
            f1, b, ease = ks[i + 1]
            if f0 <= f <= f1:
                t = EASE[ease]((f - f0) / (f1 - f0)) if f1 > f0 else 1.0
                if self.arc and isinstance(a, Vector):
                    p0 = ks[i - 1][1] if i > 0 else a * 2 - b
                    p3 = ks[i + 2][1] if i + 2 < len(ks) else b * 2 - a
                    return catmull(p0, a, b, p3, t)
                return a + (b - a) * t
        return ks[-1][1]


def catmull(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)


def damped(f, hits, amp, freq=0.33, decay=0.18):
    """A damped spring set ringing at each (frame, strength) in hits: follow-through after a hit."""
    out = 0.0
    for h, s in hits:
        if f >= h:
            t = f - h
            out += s * amp * math.exp(-decay * t) * math.sin(2 * math.pi * freq * t)
    return out


# ---------------------------------------------------------------- the monster
def euler_rots(v):
    return [("x", v.x), ("y", v.y), ("z", v.z)]


def pose_monster(an, f, rot_tracks, lags=None, loc=None, extra=None):
    """Sets FK rotations (world-axis degrees, sampled f - lag frames for overlap) and bone
    location offsets. extra: more {bone: [(axis, deg)]} to add (secondary motion)."""
    pose = {}
    for bone, tr in rot_tracks.items():
        pose[bone] = euler_rots(tr(max(0, f - (lags or {}).get(bone, 0))))
    for bone, rots in (extra or {}).items():
        pose[bone] = pose.get(bone, []) + list(rots)
    an.fk(pose, {b: tuple(t(f)) for b, t in (loc or {}).items()})


# ---------------------------------------------------------------- the R6 victim
def euler(v):
    """Torso-style rotation from (pitch about X, yaw about Y, roll about Z), degrees, Roblox axes:
    +pitch tips the top backward, +yaw turns toward its left, +roll tips toward its left."""
    return K.rot("Y", v.y) @ K.rot("X", v.x) @ K.rot("Z", v.z)


HIP = Vector((0.0, -1.0, 0.0))  # the middle of the hips, in the torso's frame


class VictimAnimator:
    """Builds R6 poses frame by frame, remembering the torso's orientation for follow-through."""

    def __init__(self):
        self.rot = {}

    def torso_from_hips(self, hips, rot_deg):
        """The torso CFrame pivoting on its hips at `hips` (HRP space)."""
        return Matrix.Translation(hips) @ euler(rot_deg) @ Matrix.Translation(-HIP)

    def torso_from_grip(self, grip, grip_local, rot_deg):
        """The torso CFrame with the point grip_local (its own frame) held at `grip`."""
        R = euler(rot_deg)
        return Matrix.Translation(grip - R.to_3x3() @ grip_local) @ R

    def build(self, f, torso, limbs=None, limbs_w=None, head=None, look_at=None, lag=None):
        """limbs: {limb: direction in the torso's frame}; limbs_w: {limb: direction in HRP space};
        head: (pitch, yaw, roll) degrees on top of looking at look_at (or of facing straight
        ahead). lag: {"arms": n, "legs": n, "head": n} frames of drag."""
        lag = {"arms": 2, "legs": 2, "head": 2, **(lag or {})}
        v = K.Victim()
        v.torso = torso
        cur = torso.to_3x3().normalized()
        self.rot[f] = cur.copy()

        def lagged(n):
            return self.rot.get(f - n, self.rot.get(max(k for k in self.rot if k <= f), cur)) if n else cur

        for limb, d in (limbs or {}).items():
            n = lag["arms"] if "Arm" in limb else lag["legs"]
            v.point(limb, (lagged(n) @ Vector(d)).normalized())
        for limb, d in (limbs_w or {}).items():
            v.point(limb, Vector(d).normalized())
        Rl = lagged(lag["head"])
        if look_at is not None:
            neck = torso @ Vector((0, 1.5, 0))
            d = (look_at - neck).normalized()
            base = Vector((0, 0, -1)).rotation_difference(Rl.inverted() @ d).to_matrix()
        else:
            base = Matrix.Identity(3)
        hv = head if head is not None else Vector((0, 0, 0))
        W = Rl @ base @ euler(Vector(hv)).to_3x3()
        v.rotate("Head", (cur.inverted() @ W).to_4x4())
        return v


def standing(an_v, f, hips, rot_deg, **kw):
    return an_v.build(f, an_v.torso_from_hips(hips, rot_deg), **kw)


def aim_bone(an, bone, point_rest, normal_rest, target, weight=1.0):
    """Turns a bone (about its own head) so the face at point_rest, facing normal_rest (both at
    rest, armature space), points at `target`, by `weight` of the way. Keeps a monster's face
    locked on the player while its body twists and lunges."""
    import bpy
    if weight <= 0.0:
        return
    bpy.context.view_layer.update()
    pb = an.pb[bone]
    D = pb.matrix @ pb.bone.matrix_local.inverted()
    p = D @ point_rest
    n = (D.to_3x3() @ normal_rest).normalized()
    d = (target - p)
    if d.length < 1e-4:
        return
    q = Quaternion().slerp(n.rotation_difference(d.normalized()), min(1.0, weight))
    pivot = pb.matrix.translation.copy()
    M = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ pb.matrix
    pb.matrix = M
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
