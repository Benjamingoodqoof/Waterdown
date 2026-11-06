"""Shared tools for the REM CYCLE kill animations: a monster and an R6 player animated as a pair.

The monster's half is an ordinary action on its rig (exported as FBX like its other
animations). The player's half is written as a Roblox KeyframeSequence (.rbxmx) for the
standard R6 rig, so it loads straight into Studio.

Spaces:
- The monster's scene: Blender, meters, Z up, the monster facing -Y, its feet on z = 0.
- The victim: R6, in studs, in Roblox axes (Y up, facing -Z), relative to its own
  HumanoidRootPart, which stands `distance` studs in front of the monster's root, facing it.
  `k` is meters per in-game stud for this monster (its height in meters / its in-game height),
  so the victim is the right size next to it.
"""
import math
import os
from xml.sax.saxutils import escape

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30


def cf(x, y, z, *r):
    """A Roblox CFrame (position and the rotation's rows) as a 4x4 matrix."""
    m = Matrix(((r[0], r[1], r[2], x), (r[3], r[4], r[5], y), (r[6], r[7], r[8], z), (0, 0, 0, 1)))
    return m


# the standard R6 Motor6Ds: name -> (Part0, Part1, C0, C1)
JOINTS = {
    "RootJoint": ("HumanoidRootPart", "Torso", cf(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0), cf(0, 0, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)),
    "Neck": ("Torso", "Head", cf(0, 1, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0), cf(0, -0.5, 0, -1, 0, 0, 0, 0, 1, 0, 1, 0)),
    "Right Shoulder": ("Torso", "Right Arm", cf(1, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), cf(-0.5, 0.5, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0)),
    "Left Shoulder": ("Torso", "Left Arm", cf(-1, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), cf(0.5, 0.5, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0)),
    "Right Hip": ("Torso", "Right Leg", cf(1, -1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0), cf(0.5, 1, 0, 0, 0, 1, 0, 1, 0, -1, 0, 0)),
    "Left Hip": ("Torso", "Left Leg", cf(-1, -1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0), cf(-0.5, 1, 0, 0, 0, -1, 0, 1, 0, 1, 0, 0)),
}
LIMB_JOINT = {"Head": "Neck", "Right Arm": "Right Shoulder", "Left Arm": "Left Shoulder", "Right Leg": "Right Hip",
              "Left Leg": "Left Hip"}
SIZES = {"Torso": (2, 2, 1), "Head": (1.25, 1.25, 1.25), "Right Arm": (1, 2, 1), "Left Arm": (1, 2, 1),
         "Right Leg": (1, 2, 1), "Left Leg": (1, 2, 1)}
# Blender <- Roblox axes: x stays, Roblox Y (up) is Blender Z, Roblox Z (back) is Blender -Y
AXES = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))


def rot(axis, deg):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def rest_limb(torso, limb, T=None):
    """A limb's CFrame from the torso's through its joint: Part1 = Part0 * C0 * T * C1^-1."""
    _, _, c0, c1 = JOINTS[LIMB_JOINT[limb]]
    return torso @ c0 @ (T or Matrix.Identity(4)) @ c1.inverted()


class Victim:
    """An R6 pose: part CFrames relative to the HumanoidRootPart (studs, Roblox axes)."""

    def __init__(self):
        self.torso = Matrix.Identity(4)
        self.T = {limb: Matrix.Identity(4) for limb in LIMB_JOINT}

    def parts(self):
        out = {"Torso": self.torso}
        for limb in LIMB_JOINT:
            out[limb] = rest_limb(self.torso, limb, self.T[limb])
        return out

    def rotate(self, limb, R_torso_space):
        """Turns a limb about its joint by a rotation given in the torso's axes (x right, y up,
        z back): +x on an arm or leg swings it back, -x forward."""
        _, _, c0, _ = JOINTS[LIMB_JOINT[limb]]
        r = c0.to_3x3().inverted() @ R_torso_space.to_3x3() @ c0.to_3x3()
        self.T[limb] = r.to_4x4()

    def point(self, limb, direction, twist=0.0):
        """Points an arm or leg (its length, from the joint down) along `direction` (HRP space),
        by the smallest swing from where it hangs; twist turns it about its length."""
        t3 = self.torso.to_3x3()
        d_local = (t3.inverted() @ direction).normalized()
        q = Vector((0, -1, 0)).rotation_difference(d_local)
        R = q.to_matrix() @ Matrix.Rotation(math.radians(twist), 3, "Y")
        self.rotate(limb, R.to_4x4())

    def look(self, target, roll=0.0, limit=70.0):
        """Turns the head (by the neck) to face a point in HRP space, up to `limit` degrees off
        the torso's own facing."""
        t3 = self.torso.to_3x3()
        neck = (self.torso @ Vector((0, 1.5, 0)))
        d = (t3.inverted() @ (target - neck)).normalized()  # in torso space
        fwd = Vector((0, 0, -1))
        ang = fwd.angle(d)
        if ang > math.radians(limit):
            d = fwd.slerp(d, math.radians(limit) / ang) if hasattr(fwd, "slerp") else d
        q = fwd.rotation_difference(d)
        R = q.to_matrix() @ Matrix.Rotation(math.radians(roll), 3, "Z")
        self.rotate("Head", R.to_4x4())

    def head_world(self):
        return self.parts()["Head"]

    def T_torso_space(self, limb):
        """A limb's rotation at its joint, in the torso's axes (the inverse of rotate())."""
        _, _, c0, _ = JOINTS[LIMB_JOINT[limb]]
        return c0.to_3x3() @ self.T[limb].to_3x3() @ c0.to_3x3().inverted()

    def hang_from_head(self, head_cf, torso_rot):
        """Puts the head at head_cf (HRP space) with the torso turned to torso_rot below it, the
        neck taking up the difference."""
        _, _, c0, c1 = JOINTS["Neck"]
        r = (c0.to_3x3().inverted() @ torso_rot.to_3x3().inverted() @ head_cf.to_3x3() @ c1.to_3x3())
        self.T["Head"] = r.to_4x4()
        self.torso = head_cf @ c1 @ self.T["Head"].inverted() @ c0.inverted()

    def place_head(self, head_cf, neck_T=None):
        """Moves the torso so the head ends up at head_cf (HRP space), with the neck bent by
        neck_T (the torso hangs from the head)."""
        if neck_T is not None:
            self.T["Head"] = neck_T
        _, _, c0, c1 = JOINTS["Neck"]
        self.torso = head_cf @ (c0 @ self.T["Head"] @ c1.inverted()).inverted()

    def transforms(self):
        """Each Motor6D's Transform (what a Pose's CFrame holds)."""
        out = {}
        _, _, c0, c1 = JOINTS["RootJoint"]
        out["Torso"] = c0.inverted() @ self.torso @ c1
        for limb in LIMB_JOINT:
            out[limb] = self.T[limb]
        return out


class Placement:
    """Maps the victim's HRP space (studs, Roblox axes) into the monster's Blender scene."""

    def __init__(self, k, distance, monster_root):
        self.k = k
        self.origin = Vector((monster_root.x, monster_root.y - distance * k, 3.0 * k))
        self.P = Matrix.Translation(self.origin) @ Matrix.Scale(k, 4) @ AXES  # Roblox -Z (its facing) is +Y

    def to_blender(self, m):
        return self.P @ m

    def to_victim(self, m):
        return self.P.inverted() @ m

    def point_to_victim(self, p):
        return self.P.inverted() @ p

    def point_to_blender(self, p):
        return self.P @ p


def blend_cf(a, b, t):
    """Blends two CFrames (rigid)."""
    t = min(1.0, max(0.0, t))
    qa, qb = a.to_quaternion(), b.to_quaternion()
    m = qa.slerp(qb, t).to_matrix().to_4x4()
    m.translation = a.translation.lerp(b.translation, t)
    return m


def look_cf(pos, target, up=Vector((0, 1, 0))):
    """A CFrame at pos looking at target (-Z forward, Roblox axes)."""
    f = (target - pos).normalized()
    r = f.cross(up)
    if r.length < 1e-4:
        r = Vector((1, 0, 0))
    r.normalize()
    u = r.cross(f).normalized()
    m = Matrix((r, u, -f)).transposed().to_4x4()
    m.translation = pos
    return m


# ---------------------------------------------------------------- writing the KeyframeSequence
def _cframe_xml(m):
    vals = [m[0][3], m[1][3], m[2][3], m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2], m[2][0], m[2][1], m[2][2]]
    tags = ["X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22"]
    return "".join(f"<{t}>{v:.6f}</{t}>" for t, v in zip(tags, vals))


def write_keyframes(path, name, frames, priority=5, markers=None):
    """frames: [{part: Transform}] at 30 fps. Writes a one-shot R6 KeyframeSequence (.rbxmx).
    markers: {frame: name}; those keyframes take that name, so AnimationTrack.KeyframeReached
    fires with it."""
    ref = [0]

    def nid():
        ref[0] += 1
        return f"RBX{ref[0]:06d}"

    def pose(part, m, children="", weight=1.0):
        return (f'<Item class="Pose" referent="{nid()}"><Properties>'
                f'<CoordinateFrame name="CFrame">{_cframe_xml(m)}</CoordinateFrame>'
                f'<token name="EasingDirection">0</token><token name="EasingStyle">0</token>'
                f'<string name="Name">{escape(part)}</string><float name="Weight">{weight}</float>'
                f'</Properties>{children}</Item>')

    out = ['<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
           'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">',
           f'<Item class="KeyframeSequence" referent="{nid()}"><Properties>'
           f'<bool name="Loop">false</bool><string name="Name">{escape(name)}</string>'
           f'<token name="Priority">{priority}</token></Properties>']
    for i, tr in enumerate(frames):
        limbs = "".join(pose(p, tr[p]) for p in ("Head", "Right Arm", "Left Arm", "Right Leg", "Left Leg"))
        torso = pose("Torso", tr["Torso"], limbs)
        root = pose("HumanoidRootPart", Matrix.Identity(4), torso, 0.0)
        kname = escape((markers or {}).get(i, "Keyframe"))
        out.append(f'<Item class="Keyframe" referent="{nid()}"><Properties><string name="Name">{kname}</string>'
                   f'<float name="Time">{i / FPS:.6f}</float></Properties>{root}</Item>')
    out.append("</Item></roblox>")
    with open(path, "w") as fh:
        fh.write("".join(out))


# ---------------------------------------------------------------- preview geometry
VICTIM_COLORS = {"Torso": (0.05, 0.25, 0.7), "Head": (0.95, 0.8, 0.25), "Right Arm": (0.95, 0.8, 0.25),
                 "Left Arm": (0.95, 0.8, 0.25), "Right Leg": (0.25, 0.55, 0.2), "Left Leg": (0.25, 0.55, 0.2)}


def victim_boxes(k):
    """Blocky R6 parts (a Noob's colours) for previews, as objects named Victim_<part>."""
    obs = {}
    for part, size in SIZES.items():
        me = bpy.data.meshes.new(f"Victim_{part}")
        sx, sy, sz = (s * 0.5 for s in size)
        verts = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        me.from_pydata(verts, [], faces)
        mat = bpy.data.materials.new(f"M_Victim_{part}")
        try:
            mat.use_nodes = True
        except AttributeError:
            pass
        b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*VICTIM_COLORS[part], 1)
        b.inputs["Roughness"].default_value = 0.6
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"Victim_{part}", me)
        bpy.context.scene.collection.objects.link(ob)
        obs[part] = ob
    return obs


def key_victim(obs, placement, parts, frame):
    for part, ob in obs.items():
        ob.matrix_world = placement.to_blender(parts[part])
        ob.keyframe_insert("location", frame=frame)
        ob.keyframe_insert("rotation_euler", frame=frame)
        ob.keyframe_insert("scale", frame=frame)


def fp_camera(placement, head_cf, frame, cam):
    """Keys the first-person camera: at the victim's eyes, looking where the head looks."""
    m = placement.to_blender(head_cf @ Matrix.Translation((0, 0.15, -0.55)))
    loc, q, _ = m.decompose()
    cam.location = loc
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = q
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_quaternion", frame=frame)


def render_sheet(out_png, frames, cams, res=(300, 240), samples=10, label=""):
    """Renders a grid: a row per camera, a column per frame."""
    from PIL import Image, ImageDraw, ImageFont
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.cycles.samples = samples
    tmp = out_png + "_tmp.png"
    sheet = Image.new("RGB", (res[0] * len(frames), res[1] * len(cams)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 14)
    for r, cam in enumerate(cams):
        sc.camera = cam
        for o in bpy.data.objects:  # in first person, as in Roblox, you don't see your own body
            if o.name.startswith("Victim_"):
                o.hide_render = cam.name == "FP"
        for c, f in enumerate(frames):
            sc.frame_set(f)
            sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            sheet.paste(Image.open(tmp).convert("RGB"), (c * res[0], r * res[1]))
            d.text((c * res[0] + 5, r * res[1] + 3), f"{label} {cam.name} {f}", font=fnt, fill=(240, 240, 240))
    sheet.save(out_png)
    os.remove(tmp)


# ---------------------------------------------------------------- the monster's side
def palm_axis(an, side):
    """Which local axis of a hand bone faces its palm (toward the thigh at rest)."""
    m = an.pb[f"{side}Hand"].bone.matrix_local.to_3x3()
    inward = Vector((-1.0 if side == "Left" else 1.0, 0, 0))
    return max((("x", m.col[0]), ("-x", -m.col[0]), ("z", m.col[2]), ("-z", -m.col[2])),
               key=lambda kv: kv[1].dot(inward))[0]


PALM_AXES = {"x": Vector((1, 0, 0)), "-x": Vector((-1, 0, 0)), "z": Vector((0, 0, 1)), "-z": Vector((0, 0, -1))}


def finger_curl(an, side, amount, spread=0.0, skip=()):
    """Curls every finger bone on a side toward the palm by `amount` degrees per joint (the
    thumb less), and fans the fingers apart by `spread` degrees (in the plane of the palm).
    Each joint bends about the axis across its own bone and the palm's facing, so the fingers
    close onto the palm (a fist at ~90) whatever the rig's bone rolls."""
    hand = an.pb[f"{side}Hand"].bone
    palm = (hand.matrix_local.to_3x3() @ PALM_AXES[palm_axis(an, side)]).normalized()
    out = {}
    names = ("Thumb", "Index", "Middle", "Ring", "Pinky")
    for i, fname in enumerate(names):
        if fname in skip:
            continue
        for seg in (1, 2, 3):
            b = f"{side}{fname}{seg}"
            if b not in an.pb:
                continue
            y = (an.pb[b].bone.matrix_local.to_3x3() @ Vector((0, 1, 0))).normalized()
            axis = y.cross(palm)
            if axis.length < 1e-6:
                continue
            rots = [(axis.normalized(), amount * (0.6 if fname == "Thumb" else 1.0) * (1.25 if seg > 1 else 1.0))]
            if seg == 1 and spread and fname != "Thumb":
                fan = 1 if side == "Left" else -1
                rots.append((palm, spread * (i - 2.5) * fan))
            out[b] = rots
    return out


def reach(an, side, wrist, pole, hand_dir=None, palm_dir=None):
    """IKs an arm so the wrist reaches `wrist` (armature space), elbow toward `pole`; then turns
    the hand to point along hand_dir with its palm toward palm_dir."""
    an.two_bone(f"{side}UpperArm", f"{side}LowerArm", wrist, pole)
    if hand_dir is not None:
        an.orient(f"{side}Hand", hand_dir, palm_axis(an, side), palm_dir if palm_dir is not None else Vector((0, 0, -1)))


def smoothstep(a, b, f):
    if f <= a:
        return 0.0
    if f >= b:
        return 1.0
    t = (f - a) / (b - a)
    return t * t * (3 - 2 * t)


def window(f, a, b, c, d):
    """0 before a, eases to 1 by b, holds, eases back to 0 from c to d."""
    return smoothstep(a, b, f) * (1 - smoothstep(c, d, f))


def run_kill(blend, rig_name, length, k, distance, fn, out_rbxmx, preview_blend, victim_name, markers,
             loc_bones=("LowerTorso",), action="Kill", play=False):
    """Keys the monster's `action` and the victim's KeyframeSequence together. fn(an, ctx, f)
    poses the monster for frame f and returns the Victim's pose; ctx holds the Placement (pl) and
    anything fn wants to keep between frames. Saves the blend, writes the .rbxmx, and saves a
    preview blend with the victim as boxes and a first-person camera on its head.

    play=True: the monster's `action` is already animated (e.g. edited by hand in Blender): it's
    played rather than made, and fn works out the victim against it (ctx["play"] is True); fn may
    key a few of his bones into it (the copy in `action`; the original is kept as
    "<action>_source")."""
    import anim_core as A
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    rig = bpy.data.objects[rig_name]
    an = A.Animator(rig, loc_bones)
    root = rig.data.bones["Root"].head_local.copy()
    ctx = {"pl": Placement(k, distance, root), "k": k, "play": play}
    rig.animation_data_create()
    trs, parts = [], []
    if play:
        # the hand-made action is kept as it is in "<action>_source"; each run starts from a fresh
        # copy of it, so whatever fn keys into it (e.g. a hand fitted to the player) never piles up
        src = bpy.data.actions.get(action + "_source")
        if src is None:
            src = bpy.data.actions[action].copy()
            src.name = action + "_source"
            src.use_fake_user = True
        old = bpy.data.actions.get(action)
        if old:
            old.name = action + "_old"
        act = src.copy()
        act.name = action
        act.use_fake_user = True
        if old:
            bpy.data.actions.remove(old)
        rig.animation_data.action = act
        for f in range(length + 1):
            bpy.context.scene.frame_set(f)
            v = fn(an, ctx, f)
            trs.append(v.transforms())
            parts.append(v.parts())
        rig.animation_data.action = None
    else:
        old = bpy.data.actions.get(action)
        if old:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(action)
        act.use_fake_user = True
        rig.animation_data.action = act
        for f in range(length + 1):
            an.reset()
            v = fn(an, ctx, f)
            an.key(f)
            trs.append(v.transforms())
            parts.append(v.parts())
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, length
        act.use_cyclic = False
    an.reset()
    if "Idle" in bpy.data.actions:
        rig.animation_data.action = bpy.data.actions["Idle"]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
    if out_rbxmx:
        write_keyframes(out_rbxmx, victim_name, trs, markers=markers)
    ctx["parts"] = parts
    ctx["root"] = root
    if os.environ.get("KILL_DEBUG"):  # how far each limb swings (its pointing) and twists, per frame
        for limb in ("Right Arm", "Left Arm", "Right Leg", "Left Leg"):
            rows = []
            for f in range(1, len(parts)):
                a3, b3 = parts[f - 1][limb].to_3x3(), parts[f][limb].to_3x3()
                da, db = a3 @ Vector((0, -1, 0)), b3 @ Vector((0, -1, 0))
                swing = math.degrees(da.angle(db))
                xa = da.rotation_difference(db).to_matrix() @ (a3 @ Vector((1, 0, 0)))
                twist = math.degrees(xa.angle(b3 @ Vector((1, 0, 0))))
                if swing > 25 or twist > 25:
                    rows.append((f, round(swing), round(twist)))
            print("LIMB", limb, rows[:14])
    # the preview scene
    rig.animation_data.action = act
    obs = victim_boxes(k)
    cam = bpy.data.objects.new("FP", bpy.data.cameras.new("FP"))
    cam.data.lens = 18  # about Roblox's default 70 degree field of view
    cam.data.clip_start = 0.01
    bpy.context.scene.collection.objects.link(cam)
    for f, p in enumerate(parts):
        key_victim(obs, ctx["pl"], p, f)
        fp_camera(ctx["pl"], p["Head"], f, cam)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, length
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(preview_blend))
    return ctx


# ---------------------------------------------------------------- shared victim beats
def recoil(v, f, a, b, look_at=None, arms_up=(12, 24)):
    """Standing, then flinching back from a to b, the arms coming up to shield the face."""
    rec = smoothstep(a, b, f)
    lean = 9 * rec
    R = rot("X", lean)
    v.torso = Matrix.Translation((0, -0.05 * rec, 0.25 * rec)) @ R
    for leg in ("Right Leg", "Left Leg"):
        v.rotate(leg, R.inverted())
    up = smoothstep(arms_up[0], arms_up[1], f)
    for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
        v.point(arm, Vector((0.35 * sx * up, -1 + 1.6 * up, -0.9 * up)).normalized())
    if look_at is not None:
        v.look(look_at, limit=60)
    return v


def kick_legs(v, f, amount, speed=2.6):
    for leg, ph in (("Right Leg", 0.0), ("Left Leg", math.pi)):
        a = math.sin(f / speed + ph) * 32 * amount
        v.rotate(leg, rot("X", a - 8 * (1 - amount)) @ rot("Z", 4 * (1 if leg == "Right Leg" else -1)))


def clutch(v, pl, f, start, targets):
    """The victim's hands grabbing at the monster: targets is {"Right Arm": blender point, ...}."""
    c = smoothstep(start, start + 8, f)
    for arm, tb in targets.items():
        t = pl.point_to_victim(tb)
        sh = v.torso @ Vector((1.0 if arm == "Right Arm" else -1.0, 0.5, 0))
        v.point(arm, Vector((0, -1, 0)).lerp((t - sh).normalized(), c).normalized())


def fall(v, held_torso, f, drop, land, lying, look_at=None):
    """Dropped from held_torso: falls (accelerating), lands at `lying`, bounces once, limp."""
    t = min(1.0, max(0.0, (f - drop) / (land - drop)))
    m = blend_cf(held_torso, lying, t * t)
    if f > land:
        m.translation.y += 0.25 * math.sin(math.pi * min(1.0, (f - land) / 6))
    v.torso = m
    limp = smoothstep(drop, land, f)
    v.rotate("Right Arm", rot("Z", 70 * limp) @ rot("X", -20 * limp))
    v.rotate("Left Arm", rot("Z", -55 * limp) @ rot("X", 30 * limp))
    v.rotate("Right Leg", rot("X", -25 * limp) @ rot("Z", 8 * limp))
    v.rotate("Left Leg", rot("X", -5 * limp) @ rot("Z", -10 * limp))
    if look_at is not None:
        v.look(look_at, roll=-20 * limp, limit=50)
    return v


# ---------------------------------------------------------------- timing and impacts
def back_out(t, s=1.70158):
    """Ease out with an overshoot past 1 and back (a snap that settles)."""
    t = min(1.0, max(0.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def shake(f, hits, amp=1.0, decay=0.22, freq=0.9):
    """A jolt after each impact frame in hits: (pitch, yaw, roll) noise that dies away."""
    out = Vector((0, 0, 0))
    for h in hits:
        if f >= h:
            t = f - h
            e = amp * math.exp(-decay * t)
            out += Vector((math.sin(freq * t * 2.1 + 0.3), math.sin(freq * t * 1.7 + 1.9), math.sin(freq * t * 2.6 + 4.1))) * e
    return out


def jolt_head(v, f, hits, deg=12.0):
    """Shakes the victim's head (and so a camera locked to it) after each impact."""
    s = shake(f, hits) * deg
    if s.length > 1e-4:
        v.T["Head"] = v.T["Head"] @ (rot("X", s.x) @ rot("Y", s.y) @ rot("Z", s.z))


def hang_from_limb(v, limb, point_local, at, torso_rot, limb_T=None):
    """Places the victim so a point on `limb` (in the limb's own frame) is at `at` (HRP space),
    the torso turned to torso_rot and the limb bent by limb_T at its joint."""
    if limb_T is not None:
        v.T[limb] = limb_T
    v.torso = torso_rot.to_3x3().to_4x4()
    p = rest_limb(v.torso, limb, v.T[limb]) @ point_local
    v.torso = Matrix.Translation(at - p) @ v.torso
    return v


# ---------------------------------------------------------------- the victim on the user's R6 rig
R6_REST = {"Torso": (0, 3, 0), "Head": (0, 4.5, 0), "Right Arm": (1.5, 3, 0), "Left Arm": (-1.5, 3, 0),
           "Right Leg": (0.5, 1, 0), "Left Leg": (-0.5, 1, 0)}
R6_ORDER = ("Torso", "Head", "Right Arm", "Left Arm", "Right Leg", "Left Leg")


def write_r6_blend(template, out_blend, parts_frames, action_name, markers, monster=None, note="", ref=None,
                   keys=(), sharp=(), refine=("Torso",)):
    """Keys the victim onto the R6 rig in `template` (a copy of the user's Blender_R6.blend: its
    InternalArmature has a bone per R6 part, in studs, facing +Y) and saves it as out_blend at
    30 fps. The InternalArmature's constraints to the control rig are muted, so the keys drive
    it directly. monster: (blend, rig name, action, k, distance, root) appends the monster,
    scaled to studs and playing its kill, as a reference in its own collection. keys/sharp: the
    key poses and impact frames (see key_r6_rig)."""
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(template))
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, len(parts_frames) - 1
    arm = bpy.data.objects["InternalArmature"]
    ctrl = bpy.data.objects.get("__PrimaryArmature")
    if ctrl:
        ctrl.hide_set(True)
    act = key_r6_rig(arm, parts_frames, action_name, forced=keys, sharp=sharp, refine=refine)
    for f, name in (markers or {}).items():
        m = sc.timeline_markers.new(name, frame=f)
        m.select = False
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, len(parts_frames) - 1
    if monster:
        mblend, rig_name, maction, k, distance, root = monster
        with bpy.data.libraries.load(os.path.abspath(mblend), link=False) as (src, dst):
            dst.objects = list(src.objects)
            dst.actions = [a for a in src.actions if a == maction]
        col = bpy.data.collections.new("Monster (reference)")
        sc.collection.children.link(col)
        rig = None
        for o in dst.objects:
            if o is None:
                continue
            col.objects.link(o)
            if o.type == "ARMATURE" and o.name.startswith(rig_name):
                rig = o
        rig.animation_data_create()
        rig.animation_data.action = dst.actions[0]
        rig.matrix_world = Matrix.Scale(1.0 / k, 4) @ Matrix.Translation(-Vector((root.x, root.y - distance * k, 0.0)))
    if ref:  # another R6 player, as plain blocks keyed per frame (in this rig's HRP space)
        ref_frames, ref_name, ref_colors = ref
        col = bpy.data.collections.new(f"{ref_name} (reference)")
        sc.collection.children.link(col)
        boxes = r6_boxes(ref_name.replace(" ", ""), ref_colors, 1.0, col)
        for f, parts in enumerate(ref_frames):
            for part, ob in boxes.items():
                ob.matrix_world = AXES @ Matrix.Translation((0, 3, 0)) @ parts[part]
                for path in ("location", "rotation_euler", "scale"):
                    ob.keyframe_insert(path, frame=f)
    txt = bpy.data.texts.new("KILL_README")
    txt.write(note)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_blend))


def crumple(v, f, start, end, from_torso, lying, look_at=None, side=1.0):
    """Goes limp and collapses: the knees give (the body drops and folds), then it tips over
    onto its back (or side) on the floor. Weighty, not a ragdoll fling."""
    t = min(1.0, max(0.0, (f - start) / (end - start)))
    knees = Matrix.Translation(from_torso.translation + Vector((0.2 * side, -1.3, -0.3))) @ rot("Z", 8 * side) @ rot("X", -18)
    if t < 0.45:
        m = blend_cf(from_torso, knees, smoothstep(0, 1, t / 0.45))
        sit = smoothstep(0, 1, t / 0.45)
    else:
        u = (t - 0.45) / 0.55
        m = blend_cf(knees, lying, u * u)
        sit = 1.0 - 0.7 * u
    if f > end:
        m = lying.copy()
        m.translation.y += 0.12 * math.sin(math.pi * min(1.0, (f - end) / 5))
    v.torso = m
    limp = smoothstep(start, end, f)
    v.rotate("Right Leg", rot("X", -70 * sit - 10 * limp) @ rot("Z", 6))
    v.rotate("Left Leg", rot("X", -55 * sit - 5 * limp) @ rot("Z", -8))
    v.rotate("Right Arm", rot("Z", 25 * limp) @ rot("X", -15 * limp))
    v.rotate("Left Arm", rot("Z", -30 * limp) @ rot("X", 10 * limp))
    if look_at is not None:
        v.look(look_at, roll=-15 * limp * side, limit=40 + 20 * (1 - limp))
    return v


def r6_boxes(prefix, colors, scale=1.0, collection=None):
    """Blocky R6 parts named <prefix>_<part>, their mesh in the part's own Roblox axes."""
    obs = {}
    for part, size in SIZES.items():
        me = bpy.data.meshes.new(f"{prefix}_{part}")
        sx, sy, sz = (x * 0.5 for x in size)
        verts = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
        me.from_pydata(verts, [], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
        me.validate()
        mat = bpy.data.materials.new(f"M_{prefix}_{part}")
        try:
            mat.use_nodes = True
        except AttributeError:
            pass
        b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (*colors[part], 1)
        b.inputs["Roughness"].default_value = 0.6
        me.materials.append(mat)
        ob = bpy.data.objects.new(f"{prefix}_{part}", me)
        (collection or bpy.context.scene.collection).objects.link(ob)
        obs[part] = ob
    return obs


# where each R6 limb joins the torso, and the point at its far end (a hand's grip, a foot's
# sole), both in the torso's frame with the limb at rest
LIMB_JOINT_POS = {"Right Arm": Vector((1, 0.5, 0)), "Left Arm": Vector((-1, 0.5, 0)),
                  "Right Leg": Vector((1, -1, 0)), "Left Leg": Vector((-1, -1, 0))}
LIMB_END = {"Right Arm": Vector((1.5, -0.9, 0)), "Left Arm": Vector((-1.5, -0.9, 0)),
            "Right Leg": Vector((0.5, -3, 0)), "Left Leg": Vector((-0.5, -3, 0))}


def reach_r6(v, limb, target, twist=0.0):
    """Turns an R6 arm or leg about its joint so its far end points at `target` (HRP space),
    as near as its length allows (R6 limbs don't bend)."""
    t3 = v.torso.to_3x3()
    joint = v.torso @ LIMB_JOINT_POS[limb]
    want = t3.inverted() @ (target - joint)
    rest = LIMB_END[limb] - LIMB_JOINT_POS[limb]
    if want.length < 1e-4:
        return
    q = rest.rotation_difference(want)
    R = q.to_matrix() @ Matrix.Rotation(math.radians(twist), 3, rest.normalized())
    v.rotate(limb, R.to_4x4())


def limb_end(v, limb):
    return v.torso @ (LIMB_JOINT_POS[limb] + (v.T_torso_space(limb) @ (LIMB_END[limb] - LIMB_JOINT_POS[limb])))


def dislocate(v, limb, offset):
    """Pulls a limb out of its socket by `offset` (studs, in the torso's axes), on top of its
    rotation: Roblox Motor6D transforms can translate as well as rotate."""
    _, _, c0, _ = JOINTS[LIMB_JOINT[limb]]
    r = c0.to_3x3().to_4x4()
    v.T[limb] = r.inverted() @ Matrix.Translation(Vector(offset)) @ r @ v.T[limb]


def reach_r6_off(v, limb, target, offset):
    """reach_r6 for a dislocated limb: aims from the moved joint, then moves it."""
    t3 = v.torso.to_3x3()
    joint = v.torso @ (LIMB_JOINT_POS[limb] + Vector(offset))
    want = t3.inverted() @ (target - joint)
    rest = LIMB_END[limb] - LIMB_JOINT_POS[limb]
    if want.length > 1e-4:
        v.rotate(limb, rest.rotation_difference(want).to_matrix().to_4x4())
    dislocate(v, limb, offset)


def _r6_values(arm, parts_frames):
    """Each R6 bone's local rotation and location at every frame (quaternions kept continuous)."""
    vals = {pb.name: [] for pb in arm.pose.bones}
    prev = {}
    for parts in parts_frames:
        arm.pose.bones["HumanoidRootPart"].matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for name in R6_ORDER:
            pb = arm.pose.bones[name]
            cur = Matrix.Translation((0, 3, 0)) @ parts[name]
            D = AXES @ cur @ Matrix.Translation(R6_REST[name]).inverted() @ AXES.inverted()
            pb.matrix = D @ pb.bone.matrix_local
            pb.scale = (1, 1, 1)
            bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            q = pb.rotation_quaternion.copy()
            if pb.name in prev and prev[pb.name].dot(q) < 0:
                q.negate()
            prev[pb.name] = q.copy()
            vals[pb.name].append((q, pb.location.copy()))
    return vals


def _channelbag(act):
    for layer in act.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                return bag
    return None


def key_r6_rig(arm, parts_frames, action_name, forced=(), sharp=(), constant=False, tol_deg=6.0, tol_loc=0.2,
               refine=("Torso",)):
    """Keys an R6 InternalArmature (bones in studs, facing +Y, constraints muted) from part
    CFrames in its own HRP space, as key poses rather than a key on every frame.

    Smooth (the default): keys at `forced` (the key poses) and the first and last frame, with
    every bone keyed on the same frames, like posing the whole body; Blender's Bezier does the
    in-betweens. Only where the body itself (the `refine` bones: the torso, which is what's held
    by the monster) would drift from where it has to be by more than tol_deg / tol_loc studs is
    a breakdown key added. Keys ease in and out (auto-clamped handles), except the `sharp` ones (impacts), whose
    vector handles give a hard stop. constant=True (stop motion): a key wherever the pose
    changes, held until the next one."""
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.mute = True
        pb.rotation_mode = "QUATERNION"
    arm.animation_data_create()
    old = bpy.data.actions.get(action_name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(action_name)
    act.use_fake_user = True
    arm.animation_data.action = act
    vals = _r6_values(arm, parts_frames)
    last = len(parts_frames) - 1
    if os.environ.get("KILL_DEBUG"):
        for b in vals:
            jumps = [(f, round(math.degrees(vals[b][f - 1][0].rotation_difference(vals[b][f][0]).angle)))
                     for f in range(1, last + 1)]
            big = [j for j in jumps if j[1] > 30]
            print("R6 jumps", b, "max", max(j[1] for j in jumps), big[:12])
    if os.environ.get("KILL_TOL"):
        tol_deg, tol_loc = (float(x) for x in os.environ["KILL_TOL"].split(","))
    bones = list(vals)

    def differs(i, j, eps_deg=0.05, eps_loc=1e-3):
        for b in bones:
            (qa, la), (qb, lb) = vals[b][i], vals[b][j]
            if math.degrees(qa.rotation_difference(qb).angle) > eps_deg or (la - lb).length > eps_loc:
                return True
        return False

    def put(frames):
        for f in frames:
            for b in bones:
                pb = arm.pose.bones[b]
                pb.rotation_quaternion, pb.location = vals[b][f]
                pb.keyframe_insert("rotation_quaternion", frame=f, group=b)
                pb.keyframe_insert("location", frame=f, group=b)

    def shape(bag):
        for fc in bag.fcurves:
            for kp in fc.keyframe_points:
                f = round(kp.co[0])
                if constant:
                    kp.interpolation = "CONSTANT"
                    continue
                kp.interpolation = "BEZIER"
                kind = "VECTOR" if f in sharp else "AUTO_CLAMPED"
                kp.handle_left_type = kp.handle_right_type = kind
            fc.update()

    if constant:
        keys = [0] + [f for f in range(1, last + 1) if differs(f, f - 1)]
        put(sorted(set(keys) | {last}))
        shape(_channelbag(act))
    else:
        keys = sorted({0, last} | {int(f) for f in forced if 0 <= f <= last} | {int(f) for f in sharp if 0 <= f <= last})
        put(keys)
        bag = _channelbag(act)
        shape(bag)
        curves = {}
        for fc in bag.fcurves:
            b = fc.data_path.split('"')[1]
            curves.setdefault(b, {})[(fc.data_path.rsplit(".", 1)[1], fc.array_index)] = fc
        for _ in range(40):
            worst = {}
            for f in range(last + 1):
                err, who = 0.0, ""
                for b in refine:
                    c = curves[b]
                    q = Quaternion([c[("rotation_quaternion", i)].evaluate(f) for i in range(4)]).normalized()
                    loc = Vector([c[("location", i)].evaluate(f) for i in range(3)])
                    qv, lv = vals[b][f]
                    e1 = math.degrees(q.rotation_difference(qv).angle) / tol_deg
                    e2 = (loc - lv).length / tol_loc
                    if max(e1, e2) > err:
                        err, who = max(e1, e2), b + ("/rot" if e1 > e2 else "/loc")
                if err > 1.0:
                    seg = max(k for k in keys if k <= f)
                    if err > worst.get(seg, (0, 0))[0]:
                        worst[seg] = (err, f, who)
            if os.environ.get("KILL_DEBUG"):
                print("R6 pass", sorted((f, round(e, 1), w) for e, f, w in worst.values()))
            new = sorted({f for _, f, _ in worst.values()} - set(keys))
            if not new:
                break
            put(new)
            keys = sorted(set(keys) | set(new))
            shape(bag)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 0, last
    n = len(_channelbag(act).fcurves[0].keyframe_points)
    print(f"{action_name}: {n} key poses over {last + 1} frames")
    return act


def key_frames(*things):
    """Every frame keyed in some Tracks / PoseKeys / Live tracks (or dicts and lists of them):
    the poses an animation was built from."""
    out = set()
    for t in things:
        if isinstance(t, dict):
            out |= key_frames(*t.values())
        elif isinstance(t, (list, tuple)):
            out |= key_frames(*t)
        elif hasattr(t, "keys") and isinstance(getattr(t, "keys"), (list, tuple)):
            for k in t.keys:
                if isinstance(k[0], (int, float)):
                    out.add(int(round(k[0])))
    return out
