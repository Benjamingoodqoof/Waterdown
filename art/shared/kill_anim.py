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
        self.limb_state = {}

    def orient(self, f, v, limb, O):
        """Sets a limb from its wanted orientation O (3x3, HRP axes: what its hanging direction
        maps to is where it points). A limb pointing (nearly) straight up has no clear twist, and
        working each frame out from scratch would flip it right round; so each frame carries on
        from the last one's orientation (turned by the smallest swing to the new direction), with
        the twist eased back toward the wanted one whenever the limb isn't pointing up."""
        d = (O @ HANG).normalized()
        st = self.limb_state.get(limb)
        if st is not None and st[0] == f - 1:
            Op, dp = st[1], st[2]
            R = dp.rotation_difference(d).to_matrix() @ Op
            up = v.torso.to_3x3() @ Vector((0, 1, 0))
            if d.angle(up) > math.radians(35):
                q = (O @ R.inverted()).to_quaternion()
                if q.w < 0:
                    q.negate()
                step = min(0.1, math.radians(5) / q.angle) if q.angle > 1e-6 else 0.0  # slow: unseen
                R = Quaternion().slerp(q, step).to_matrix() @ R
        else:
            R = O.copy()
        self.limb_state[limb] = (f, R.copy(), d.copy())
        v.rotate(limb, (v.torso.to_3x3().inverted() @ R).to_4x4())

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
            self.orient(f, v, limb, lagged(n) @ dir_q(d).to_matrix())
        for limb, d in (limbs_w or {}).items():
            self.orient(f, v, limb, cur @ dir_q(cur.inverted() @ Vector(d)).to_matrix())
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


def aim_bone(an, bone, point_rest, normal_rest, target, weight=1.0, max_deg=50.0):
    """Turns a bone (about its own head) so the face at point_rest, facing normal_rest (both at
    rest, armature space), looks at `target`, by `weight` of the way and by no more than
    max_deg. Keeps a monster's face on the player while its body twists and lunges.

    The direction is taken from the bone's pivot, not from the face: when the target comes close
    to the face (or passes it) a direction from the face flips round and spins the head."""
    import bpy
    if weight <= 0.0:
        return
    bpy.context.view_layer.update()
    pb = an.pb[bone]
    D = pb.matrix @ pb.bone.matrix_local.inverted()
    pivot = pb.matrix.translation.copy()
    n = (D.to_3x3() @ normal_rest).normalized()
    d = target - pivot
    if d.length < 1e-4:
        return
    q = n.rotation_difference(d.normalized())
    lim = math.radians(max_deg)
    if q.angle > lim:
        q = Quaternion().slerp(q, lim / q.angle)
    q = Quaternion().slerp(q, min(1.0, weight))
    M = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot) @ pb.matrix
    pb.matrix = M
    pb.location = (0, 0, 0)
    pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def follow(ctx, key, target, rate=0.35):
    """A target smoothed over frames (an aim that can't snap when what it follows jolts)."""
    prev = ctx.get(key)
    cur = target.copy() if prev is None else prev.lerp(target, rate)
    ctx[key] = cur
    return cur


# ---------------------------------------------------------------- R6 player poses, keyed
# Limb keys are (direction the limb points in the torso's frame, how far the limb is moved in
# the torso's frame). Moving as well as rotating is how R6 fakes elbows and knees: a knee
# pulled up is the leg rotated forward AND moved up toward the hip.
HANG = Vector((0, -1, 0))


def dir_q(d):
    """A limb pose from the direction it points (torso frame): the smallest swing from hanging."""
    return HANG.rotation_difference(Vector(d).normalized())


def reach_q(v, limb, target, move=(0, 0, 0)):
    """A limb pose (torso frame) putting the limb's far end on `target` (HRP space), its joint
    moved by `move`. It's the same kind of pose as dir_q (a swing from hanging, no twist), so
    blending between a reach and a fixed pose doesn't spin the limb round."""
    joint = v.torso @ (K.LIMB_JOINT_POS[limb] + Vector(move))
    want = v.torso.to_3x3().inverted() @ (target - joint)
    if want.length < 1e-4:
        return Quaternion()
    rest = K.LIMB_END[limb] - K.LIMB_JOINT_POS[limb]  # the far end isn't on the limb's axis
    d = want.normalized()
    for _ in range(4):  # turn the pointing direction until the far end lines up with the target
        end = dir_q(d) @ rest
        d = (end.rotation_difference(want) @ d).normalized()
    return dir_q(d)


class PoseKeys:
    """Limb keys whose values can be worked out when sampled (a hand reaching for something that
    moves). A key's value is (direction or name, move): a direction (torso frame) is a fixed pose;
    a name is looked up through resolve(name, move) -> Quaternion. Eased like Track."""

    def __init__(self, *keys):
        self.keys = sorted([(k[0], k[1], k[2] if len(k) > 2 else "io") for k in keys], key=lambda k: k[0])

    def _val(self, key, resolve):
        what, move = key
        move = Vector(move)
        q = resolve(what, move) if isinstance(what, str) else dir_q(what)
        return q, move

    def __call__(self, f, resolve=None):
        ks = self.keys
        if f <= ks[0][0]:
            return self._val(ks[0][1], resolve)
        if f >= ks[-1][0]:
            return self._val(ks[-1][1], resolve)
        for i in range(len(ks) - 1):
            f0, a, _ = ks[i]
            f1, b, ease = ks[i + 1]
            if f0 <= f <= f1:
                t = EASE[ease]((f - f0) / (f1 - f0)) if f1 > f0 else 1.0
                qa, ma = self._val(a, resolve)
                qb, mb = self._val(b, resolve)
                if qa.dot(qb) < 0:  # the short way round
                    qb = -qb
                return qa.slerp(qb, t), ma.lerp(mb, t)
        return self._val(ks[-1][1], resolve)


def kick_keys(leg, t0, t1, beat=6, a0=1.0, a1=0.5, phase=0):
    """Keys for a held body's leg kicking: the knee driven up (the leg swung forward and moved
    up into the hip) then stamped straight down, every `beat` frames, strength a0 -> a1."""
    sx = 1 if leg == "Right Leg" else -1
    out = []
    n = max(1, (t1 - t0) // beat)
    for i in range(n + 1):
        f = t0 + i * beat
        a = a0 + (a1 - a0) * i / n
        if (i + phase) % 2 == 0:
            out.append((f, ((sx * 0.15, -0.6 + 0.1 * (1 - a), -0.8 * a), (0, 0.5 * a, -0.15 * a)), "io"))
        else:
            out.append((f, ((sx * 0.08, -1, 0.35 * a), (0, 0.05, 0)), "io"))
    return out


def limb_pose(va, v, f, limb, q, move, lag=0):
    """Sets a limb from a torso-frame pose, dragging `lag` frames behind the torso's turning."""
    cur = v.torso.to_3x3().normalized()
    Rl = va.rot.get(f - lag, va.rot.get(max([k for k in va.rot if k <= f] or [f]), cur)) if lag else cur
    va.orient(f, v, limb, Rl @ q.to_matrix())
    K.dislocate(v, limb, move)


def flinch_tracks(t0, t1, step="Right Leg", big=1.0):
    """A flinch from standing (t0) to braced (t1): a startled jerk back first (the head and
    shoulders), then a step back on one leg (the knee bent as it travels), the torso rocking back
    and turning from the threat, both hands coming up in front of the face with the elbows
    bent, the head ducking."""
    tj = t0 + 2  # the startle
    tm = (t0 + t1) // 2
    other = "Left Leg" if step == "Right Leg" else "Right Leg"
    sx = 1 if step == "Right Leg" else -1
    return {
        "hips": Track((t0, (0, -1, 0)), (tj, (0, -0.98, 0.04), "io"), (tm, (0, -1.05, 0.22 * big), "io"),
                      (t1, (0, -1.15, 0.5 * big), "io")),
        "rot": Track((t0, (0, 0, 0)), (tj, (6, 0, 0), "io"), (tm, (2, -4 * sx, 0), "io"),
                     (t1, (14 * big, -10 * sx, -5 * sx), "io")),
        "feet": {step: Track((t0, (sx * 0.5, -3, 0)), (tj, (sx * 0.5, -3, 0)), (tm, (sx * 0.55, -2.6, 0.5 * big), "io"),
                             (t1, (sx * 0.6, -3, 1.1 * big), "i")),
                 other: Track((t0, (-sx * 0.5, -3, 0)), (t1, (-sx * 0.45, -3, 0.1)))},
        "arms": {"Right Arm": PoseKeys((t0, ((0, -1, 0), (0, 0, 0))), (tj, ((0.25, -0.9, 0.1), (0, 0.05, 0)), "io"),
                                       (tm, ((0.2, -0.4, -0.75), (-0.05, 0.15, -0.15)), "io"),
                                       (t1, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3)), "io")),
                 "Left Arm": PoseKeys((t0, ((0, -1, 0), (0, 0, 0))), (tj, ((-0.25, -0.9, 0.1), (0, 0.05, 0)), "io"),
                                      (tm, ((-0.2, -0.35, -0.8), (0.05, 0.15, -0.15)), "io"),
                                      (t1, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3)), "io"))},
        "head": Track((t0, (6, 0, 0)), (tj, (18, 0, 0), "io"), (tm, (4, 6 * sx, 2 * sx), "io"), (t1, (-16, 12 * sx, 4 * sx), "io")),
    }


def flinch_torso(va, f, tr):
    return va.torso_from_hips(tr["hips"](f), tr["rot"](f))


def apply_flinch(va, f, tr, look_at=None, arms=None):
    """The flinch at frame f. arms: PoseKeys to use instead of the flinch's own (a later beat)."""
    torso = flinch_torso(va, f, tr)
    v = va.build(f, torso, head=tr["head"](f), look_at=look_at)
    for leg, ft in tr["feet"].items():
        p = ft(f)
        lift = max(0.0, p.y + 3.0)
        mv = Vector((0, lift * 1.2, -lift * 0.5))
        limb_pose(va, v, f, leg, reach_q(v, leg, Vector((p.x, -3.0 + lift * 0.4, p.z)), mv), mv)
    for arm, keys in (arms or tr["arms"]).items():
        q, mv = keys(f)
        limb_pose(va, v, f, arm, q, mv, lag=2)
    return v


def fall_tracks(p0, r0, s, kind="drop", land=(0.2, 1.45), yaw=0.0, side=1.0, look_at=None, start_limbs=None):
    """A posed fall onto the back, from the torso at p0 turned r0 (degrees) at frame s.

    kind "drop": let go: falls onto its feet, the knees give, buckle, and the body tips back
    and slams down (pivoting on its feet: a dz of about 3 studs keeps them where they landed). kind "thrown": flung through the air, turning, and slams down on its back.
    The impact is a hard stop: the torso hits flat, the arms and legs (still in the air,
    dragging behind) slap down a moment later, the body bounces once and comes to rest. The
    pose it lands in is the pose it stays in (dead bodies don't rearrange themselves): one arm
    thrown out past the head, the other out from the side, the legs flat and apart, the head
    rolled toward look_at (the killer) if given. `land` is (dx, dz) to where it lies, `yaw`
    turns the lying body, `side` mirrors the pose. Returns tracks for apply_fall, with "impact"
    frames for keying."""
    x, z = p0.x, p0.z
    dx, dz = land
    sd = side
    lying = Vector((x + dx, -2.5, z + dz))
    flat = (90, yaw, 0)
    up, down = ("Right Arm", "Left Arm") if sd > 0 else ("Left Arm", "Right Arm")
    ux, dwx = (1 if up == "Right Arm" else -1), (1 if down == "Right Arm" else -1)
    rest = {up: (ux * 0.55, 0.83, 0.0), down: (dwx * 0.6, -0.8, 0.0),
            "Right Leg": (0.3 if sd > 0 else 0.12, -0.96, 0.0), "Left Leg": (-0.12 if sd > 0 else -0.3, -0.96, 0.0)}
    air = {k: (v[0], v[1], -0.45 if "Arm" in k else -0.35) for k, v in rest.items()}  # dragging behind
    if kind == "drop":
        F, B, L = s + 6, s + 12, s + 21
        pos = [(s, p0), (F, (x, min(p0.y, -0.15), z), "i"), (B, (x + 0.2 * dx, -1.3, z + 0.3 * dz), "io"), (L, lying, "i")]
        rot = [(s, r0), (F, (-6, yaw * 0.2, -3 * sd), "i"), (B, (28, yaw * 0.5, -6 * sd), "io"), (L, flat, "i")]
        limbs = {"Right Arm": [(F, (0.2, -0.95, -0.2), "io"), (B, (0.55, -0.3, -0.75), "io")],
                 "Left Arm": [(F, (-0.2, -0.95, -0.25), "io"), (B, (-0.5, -0.2, -0.8), "io")],
                 "Right Leg": [(F, (0.08, -1, -0.05)), (B, (0.2, -0.55, -0.8), "io")],
                 "Left Leg": [(F, (-0.08, -1, -0.05)), (B, (-0.2, -0.6, -0.78), "io")]}
        # the knees give as the feet land, then buckle (the legs moved up into the hips)
        moves = {"Right Leg": [(F, (0, 0.25, -0.05), "o"), (B, (0, 0.5, -0.15), "io"), (L - 2, (0, 0.1, 0))],
                 "Left Leg": [(F, (0, 0.25, -0.05), "o"), (B, (0, 0.5, -0.15), "io"), (L - 2, (0, 0.1, 0))]}
        head = [(s, (-10, 0, 0)), (F, (-24, 0, 8 * sd), "i"), (B, (12, 0, 4 * sd), "io")]
    else:
        A_, L = s + 6, s + 13
        mid = p0 + Vector((0.5 * dx, 0.4, 0.5 * dz))
        pos = [(s, p0), (A_, mid, "o"), (L, lying, "i")]
        rot = [(s, r0), (A_, (45, yaw * 0.6, 20 * sd), "io"), (L, flat, "i")]
        limbs = {"Right Arm": [(A_, (0.75, 0.55, 0.3), "io")], "Left Arm": [(A_, (-0.7, 0.6, -0.3), "io")],
                 "Right Leg": [(A_, (0.3, -0.7, -0.6), "io")], "Left Leg": [(A_, (-0.2, -0.8, 0.5), "io")]}
        moves = {"Right Leg": [(A_, (0, 0.3, -0.1), "io"), (L - 2, (0, 0, 0))], "Left Leg": [(A_, (0, 0.1, 0), "io"), (L - 2, (0, 0, 0))]}
        head = [(s, (-25, 0, 10 * sd)), (A_, (-30, 15 * sd, 15 * sd), "io")]
    # the head comes to rest rolled toward the killer (or to one side), chin a little down
    hy = 45 * sd
    if look_at is not None:
        T = Matrix.Translation(lying) @ euler(Vector(flat))
        d = T.to_3x3().inverted() @ (look_at - T @ Vector((0, 1.5, 0)))
        hy = max(-75.0, min(75.0, math.degrees(math.atan2(-d.x, -d.z))))
    head_rest = (-12, hy, 0)
    bounce = 0.35 if kind == "drop" else 0.45
    slide = Vector((0.1 * dx, 0, 0.1 * dz)) if kind == "thrown" else Vector((0, 0, 0))
    # L: the torso hits; L+2 the limbs slap down and it bounces; L+5 down again; L+9 at rest
    pos += [(L + 2, lying + slide * 0.5 + Vector((0, bounce, 0)), "o"), (L + 5, lying + slide * 0.9, "i"),
            (L + 9, lying + slide, "io")]
    rot += [(L + 2, (84, yaw, 0), "o"), (L + 5, flat, "i")]
    for k in limbs:  # still in the air as the torso hits, then slapped down (carried by its bounce)
        limbs[k] += [(L, air[k], "i"), (L + 2, rest[k], "i")]
    for k in ("Right Leg", "Left Leg"):
        moves.setdefault(k, [])
        moves[k] += [(L, (0, 0, 0))]
    head += [(L, (22, 0, 0), "i"), (L + 2, (-4, hy * 0.6, 0), "o"), (L + 5, (-14, hy, 0), "io"), (L + 9, head_rest, "io")]
    return {
        "start": s, "end": L + 9, "land": L, "impact": (L, L + 5),
        "pos": Track(*pos), "rot": Track(*rot), "head": Track(*head),
        "limbs": {k: Track(*([(s, Vector((start_limbs or {}).get(k, HANG)))] + v)) for k, v in limbs.items()},
        "moves": {k: Track(*([(s, (0, 0, 0))] + [m for m in v if m[0] > s])) for k, v in moves.items()},
    }


def corners(cfm, size):
    hx, hy, hz = (c / 2 for c in size)
    return [cfm @ Vector((sx * hx, sy * hy, sz * hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def floor_clamp(v, floor=-3.0):
    """Keeps a pose out of the floor: lifts the body if the torso sinks into it, then lifts any
    limb that still does by moving it (a fraction of a stud). The head is round, not a box, so
    it's left alone (it rests on the floor where the box's corners would poke through)."""
    parts = v.parts()
    low = min(c.y for c in corners(parts["Torso"], K.SIZES["Torso"]))
    if low < floor:
        v.torso = Matrix.Translation((0, floor - low, 0)) @ v.torso
        parts = v.parts()
    inv = v.torso.to_3x3().inverted()
    for limb in ("Right Arm", "Left Arm", "Right Leg", "Left Leg"):
        low = min(c.y for c in corners(parts[limb], K.SIZES[limb]))
        if low < floor:
            K.dislocate(v, limb, inv @ Vector((0, floor - low, 0)))
    return v


def apply_fall(va, f, fall):
    """The posed fall at frame f (its limbs start from where they were when it began)."""
    torso = Matrix.Translation(fall["pos"](f)) @ euler(fall["rot"](f))
    limbs = {k: tr(f) for k, tr in fall["limbs"].items()}
    # the limbs drag behind the body's turning (it has stopped turning by the time it's at rest)
    v = va.build(f, torso, head=fall["head"](f), limbs=limbs, lag={"arms": 2, "legs": 1, "head": 2})
    for k, tr in fall["moves"].items():
        K.dislocate(v, k, tr(f))
    return floor_clamp(v)


class Live:
    """A Track whose keys are worked out when sampled: resolve(value) -> Vector turns each key's
    value (a name, or a vector in some moving frame) into a point at that frame."""

    def __init__(self, *keys, arc=False):
        self.keys = keys
        self.arc = arc

    def __call__(self, f, resolve):
        return Track(*[(k[0], resolve(k[1])) + tuple(k[2:]) for k in self.keys], arc=self.arc)(f)


def look_blend(f, keys, points):
    """Where the head looks: keys [(frame, name, ease)] blend between named points (HRP space)."""
    return Live(*keys)(f, lambda name: points[name])


LIMBS = ("Right Arm", "Left Arm", "Right Leg", "Left Leg")


def pose_limbs(va, v, f, arms, legs, targets=None):
    """Poses the arms and legs of a held body from PoseKeys; targets: {arm: {name: point}}."""
    for arm, keys in arms.items():
        q, mv = keys(f, lambda name, move, arm=arm: reach_q(v, arm, targets[arm][name], move))
        limb_pose(va, v, f, arm, q, mv, lag=1)
    for leg, keys in legs.items():
        q, mv = keys(f)
        limb_pose(va, v, f, leg, q, mv, lag=2)


def limb_dirs(v):
    """Where each limb points now (torso frame): what a fall starts from."""
    t = v.torso.to_3x3().inverted()
    parts = v.parts()
    return {k: (t @ (parts[k].to_3x3() @ Vector((0, -1, 0)))).normalized() for k in LIMBS}
