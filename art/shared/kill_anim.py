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
    moved by `move`."""
    joint = v.torso @ (K.LIMB_JOINT_POS[limb] + Vector(move))
    want = v.torso.to_3x3().inverted() @ (target - joint)
    rest = K.LIMB_END[limb] - K.LIMB_JOINT_POS[limb]
    if want.length < 1e-4:
        return Quaternion()
    return rest.rotation_difference(want)


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
                return qa.slerp(qb, t), ma.lerp(mb, t)
        return self._val(ks[-1][1], resolve)


def kick_keys(leg, t0, t1, beat=5, a0=1.0, a1=0.5, phase=0):
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
            out.append((f, ((sx * 0.08, -1, 0.35 * a), (0, 0.05, 0)), "o"))
    return out


def limb_pose(va, v, f, limb, q, move, lag=0):
    """Sets a limb from a torso-frame pose, dragging `lag` frames behind the torso's turning."""
    cur = v.torso.to_3x3().normalized()
    if lag:
        Rl = va.rot.get(f - lag, va.rot.get(max([k for k in va.rot if k <= f] or [f]), cur))
        R = cur.inverted() @ Rl @ q.to_matrix()
    else:
        R = q.to_matrix()
    v.rotate(limb, R.to_4x4())
    K.dislocate(v, limb, move)


def flinch_tracks(t0, t1, step="Right Leg", big=1.0):
    """A flinch from standing (t0) to braced (t1): a quick step back on one leg (the knee bent as
    it travels), the torso rocking back and turning from the threat, both hands thrown up in
    front of the face with the elbows bent, the head ducking."""
    tm = (t0 + t1) // 2
    other = "Left Leg" if step == "Right Leg" else "Right Leg"
    sx = 1 if step == "Right Leg" else -1
    return {
        "hips": Track((t0, (0, -1, 0)), (tm, (0, -1.05, 0.2 * big), "o"), (t1, (0, -1.15, 0.5 * big), "o3")),
        "rot": Track((t0, (0, 0, 0)), (tm, (-5, 0, 0), "o"), (t1, (14 * big, -10 * sx, -5 * sx), "o3")),
        "feet": {step: Track((t0, (sx * 0.5, -3, 0)), (tm, (sx * 0.55, -2.6, 0.5 * big), "o"), (t1, (sx * 0.6, -3, 1.1 * big), "i")),
                 other: Track((t0, (-sx * 0.5, -3, 0)), (t1, (-sx * 0.45, -3, 0.1)))},
        "arms": {"Right Arm": PoseKeys((t0, ((0, -1, 0), (0, 0, 0))), (tm, ((0.3, -0.6, -0.6), (0, 0.1, -0.1)), "o"),
                                       (t1, ((-0.15, 0.5, -0.85), (-0.2, 0.3, -0.3)), "o3")),
                 "Left Arm": PoseKeys((t0, ((0, -1, 0), (0, 0, 0))), (tm, ((-0.3, -0.5, -0.65), (0, 0.1, -0.1)), "o"),
                                      (t1, ((0.2, 0.6, -0.8), (0.2, 0.35, -0.3)), "o3"))},
        "head": Track((t0, (6, 0, 0)), (tm, (12, 0, 0)), (t1, (-16, 12 * sx, 4 * sx), "o")),
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


def fall_tracks(p0, r0, s, kind="drop", land=(0.2, 1.45), yaw=0.0, side=1.0):
    """A posed fall onto the back, from the torso at p0 turned r0 (degrees) at frame s.

    kind "drop": let go: the feet hit, the knees buckle, the body tips back and slams down.
    kind "thrown": flung: tumbling through the air, the back hits, a bounce and a slide.
    Both end the same way, posed rather than lerped: arms flung out at the impact, a bounce
    (the legs lift off the floor a little and slap back down), then a settle with one arm
    thrown up past the head, the other along the side, the legs flat and splayed, the head
    rolled to one side. `land` is (dx, dz) to where the body
    lies, `yaw` the way the lying body turns (0: head away from where it fell from), `side`
    mirrors the pose. Returns tracks for apply_fall."""
    x, z = p0.x, p0.z
    dx, dz = land
    sd = side
    lying = Vector((x + dx, -2.5, z + dz))
    if kind == "drop":
        F, B, L = s + 4, s + 8, s + 13
        pos = [(s, p0), (F, (x, min(p0.y, 0.0), z), "i"), (B, (x + 0.2 * dx, -1.2, z + 0.25 * dz), "io"), (L, lying, "i")]
        rot = [(s, r0), (F, (-8, yaw * 0.2, -4 * sd), "i"), (B, (24, yaw * 0.5, -8 * sd), "io"), (L, (90, yaw, -10 * sd), "i")]
        limbs = {"Right Arm": [(F, (0.25, -0.9, -0.3)), (B, (0.6, -0.2, -0.75), "o"), (L, (1.0, 0.25, -0.1), "o")],
                 "Left Arm": [(F, (-0.25, -0.9, -0.35)), (B, (-0.55, -0.1, -0.8), "o"), (L, (-1.0, 0.15, -0.1), "o")],
                 "Right Leg": [(F, (0.1, -1, 0.0)), (B, (0.25, -0.5, -0.85), "io"), (L, (0.15, -1, -0.1), "i")],
                 "Left Leg": [(F, (-0.1, -1, 0.0)), (B, (-0.25, -0.55, -0.8), "io"), (L, (-0.12, -0.95, -0.3), "i")]}
        moves = {"Right Leg": [(F, (0, 0, 0)), (B, (0, 0.5, -0.15), "io"), (L, (0, 0, 0), "i")],
                 "Left Leg": [(F, (0, 0, 0)), (B, (0, 0.5, -0.15), "io"), (L, (0, 0, 0), "i")]}
        head = [(s, (-10, 0, 0)), (F, (-30, 0, 10 * sd), "i"), (B, (10, 0, 6 * sd), "o"), (L, (30, 0, 0), "i")]
    else:
        A_, L = s + 4, s + 9
        mid = p0 + Vector((0.5 * dx, 0.35, 0.5 * dz))
        pos = [(s, p0), (A_, mid, "o"), (L, lying, "i")]
        rot = [(s, r0), (A_, (45, yaw * 0.6, 28 * sd), "io"), (L, (90, yaw, -12 * sd), "i")]
        limbs = {"Right Arm": [(A_, (0.75, 0.6, 0.25), "o"), (L, (1.0, 0.3, -0.1), "o")],
                 "Left Arm": [(A_, (-0.7, 0.65, -0.3), "o"), (L, (-1.0, 0.1, -0.15), "o")],
                 "Right Leg": [(A_, (0.3, -0.7, -0.6), "o"), (L, (0.2, -1, -0.15), "i")],
                 "Left Leg": [(A_, (-0.2, -0.8, 0.5), "o"), (L, (-0.12, -0.95, -0.3), "i")]}
        moves = {"Right Leg": [(A_, (0, 0.35, -0.1), "o"), (L, (0, 0, 0), "i")],
                 "Left Leg": [(A_, (0, 0.1, 0.0), "o"), (L, (0, 0, 0), "i")]}
        head = [(s, (-25, 0, 10 * sd)), (A_, (-35, 15 * sd, 20 * sd), "io"), (L, (35, 0, 0), "i")]
    slide = Vector((0.12 * dx, 0, 0.12 * dz)) if kind == "thrown" else Vector((0, 0, 0))
    pos += [(L + 3, lying + slide * 0.6 + Vector((0, 0.3 if kind == "thrown" else 0.2, 0)), "o"),
            (L + 7, lying + slide, "i"), (L + 9, lying + slide + Vector((0, 0.05, 0)), "o"), (L + 14, lying + slide, "io")]
    rot += [(L + 3, (82, yaw, -10 * sd), "o"), (L + 7, (90, yaw, -12 * sd), "i"), (L + 14, (90, yaw + 4 * sd, -16 * sd), "io")]
    head += [(L + 3, (-10, 0, 6 * sd), "o"), (L + 7, (10, 15 * sd, 0), "i"), (L + 14, (0, 55 * sd, 10 * sd), "io")]
    # settle: one arm up past the head, the other along the side; the legs flat, one splayed out
    up, down = ("Right Arm", "Left Arm") if sd > 0 else ("Left Arm", "Right Arm")
    bent, straight = ("Left Leg", "Right Leg") if sd > 0 else ("Right Leg", "Left Leg")
    ux, dx_ = (1 if up == "Right Arm" else -1), (1 if down == "Right Arm" else -1)
    bx, sx = (1 if bent == "Right Leg" else -1), (1 if straight == "Right Leg" else -1)
    limbs[up] += [(L + 3, (ux * 0.9, 0.45, -0.3), "o"), (L + 7, (ux * 0.95, 0.3, -0.05), "i"), (L + 14, (ux * 0.6, 0.8, -0.05), "io")]
    limbs[down] += [(L + 3, (dx_ * 0.85, 0.3, -0.4), "o"), (L + 7, (dx_ * 0.9, 0.05, -0.05), "i"), (L + 14, (dx_ * 0.3, -0.95, -0.05), "io")]
    limbs[bent] += [(L + 3, (bx * 0.15, -0.9, -0.35), "o"), (L + 7, (bx * 0.2, -1, -0.08), "i"), (L + 14, (bx * 0.35, -0.95, -0.02), "io")]
    limbs[straight] += [(L + 3, (sx * 0.15, -0.92, -0.3), "o"), (L + 7, (sx * 0.15, -1, -0.05), "i"), (L + 14, (sx * 0.25, -1, -0.02), "io")]
    moves.setdefault(bent, [(s, (0, 0, 0))])
    moves[bent] += [(L + 7, (0, 0, 0), "i")]
    moves.setdefault(straight, [(s, (0, 0, 0))])
    moves[straight] += [(L + 7, (0, 0, 0), "i")]
    return {
        "start": s, "end": L + 14, "land": L,
        "pos": Track(*pos), "rot": Track(*rot), "head": Track(*head),
        "limbs": {k: Track(*([(s, HANG)] + v)) for k, v in limbs.items()},
        "moves": {k: Track(*([(s, (0, 0, 0))] + [m for m in v if m[0] > s])) for k, v in moves.items()},
    }


def corners(cfm, size):
    hx, hy, hz = (c / 2 for c in size)
    return [cfm @ Vector((sx * hx, sy * hy, sz * hz)) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


def floor_clamp(v, floor=-3.0, body=True):
    """Keeps a pose out of the floor: lifts the whole body if the torso or head sink into it,
    then lifts any limb that still does, by moving it (a fraction of a stud, unseen)."""
    parts = v.parts()
    if body:
        low = min(c.y for p in ("Torso", "Head") for c in corners(parts[p], K.SIZES[p]))
        if low < floor:
            v.torso = Matrix.Translation((0, floor - low, 0)) @ v.torso
            parts = v.parts()
    inv = v.torso.to_3x3().inverted()
    for limb in ("Right Arm", "Left Arm", "Right Leg", "Left Leg"):
        low = min(c.y for c in corners(parts[limb], K.SIZES[limb]))
        if low < floor:
            K.dislocate(v, limb, inv @ Vector((0, floor - low, 0)))
    return v


def apply_fall(va, f, fall, start_limbs=None, look_at=None):
    """The posed fall at frame f. start_limbs: {limb: direction} the limbs had when it began,
    blended out over the first few frames so nothing pops. look_at: a point (HRP space) the
    head rolls round to face once the body has settled (the killer: the last thing they see)."""
    torso = Matrix.Translation(fall["pos"](f)) @ euler(fall["rot"](f))
    limbs = {}
    w = min(1.0, (f - fall["start"]) / 4.0)
    for k, tr in fall["limbs"].items():
        d = tr(f)
        if start_limbs and k in start_limbs and w < 1:
            d = Vector(start_limbs[k]).lerp(d, w)
        limbs[k] = d
    head, look = fall["head"](f), None
    if look_at is not None:
        lw = K.smoothstep(fall["land"] + 5, fall["end"] + 2, f)
        if lw > 0:
            ahead = torso @ Vector((0, 1.5, -6))
            look = ahead.lerp(look_at, lw)
            head = head * (1 - lw) + Vector((8, 0, 6)) * lw
    v = va.build(f, torso, head=head, look_at=look, limbs=limbs, lag={"arms": 2, "legs": 1, "head": 2})
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
