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
        head = bpy.data.objects.get("Victim_Head")
        if head:  # in first person, as in Roblox, you don't see your own head
            head.hide_render = cam.name == "FP"
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


def finger_curl(an, side, amount, spread=0.0, skip=()):
    """Curls every finger bone on a side (left-side degrees; mirrored for the right)."""
    out = {}
    names = ("Thumb", "Index", "Middle", "Ring", "Pinky")
    for i, fname in enumerate(names):
        for seg in (1, 2, 3):
            b = f"{side}{fname}{seg}"
            if b in an.pb and fname not in skip:
                rots = [("x", -amount * (0.6 if fname == "Thumb" else 1.0) * (1.25 if seg > 1 else 1.0))]
                if seg == 1 and spread:
                    rots.append(("z", spread * (i - 2) * (1 if side == "Left" else -1)))
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
             loc_bones=("LowerTorso",), action="Kill"):
    """Keys the monster's `action` and the victim's KeyframeSequence together. fn(an, ctx, f)
    poses the monster for frame f and returns the Victim's pose; ctx holds the Placement (pl) and
    anything fn wants to keep between frames. Saves the blend, writes the .rbxmx, and saves a
    preview blend with the victim as boxes and a first-person camera on its head."""
    import anim_core as A
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    rig = bpy.data.objects[rig_name]
    an = A.Animator(rig, loc_bones)
    root = rig.data.bones["Root"].head_local.copy()
    ctx = {"pl": Placement(k, distance, root), "k": k}
    rig.animation_data_create()
    old = bpy.data.actions.get(action)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(action)
    act.use_fake_user = True
    rig.animation_data.action = act
    trs, parts = [], []
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


def write_r6_blend(template, out_blend, parts_frames, action_name, markers, monster=None, note=""):
    """Keys the victim onto the R6 rig in `template` (a copy of the user's Blender_R6.blend: its
    InternalArmature has a bone per R6 part, in studs, facing +Y) and saves it as out_blend at
    30 fps. The InternalArmature's constraints to the control rig are muted, so the keys drive
    it directly. monster: (blend, rig name, action, k, distance, root) appends the monster,
    scaled to studs and playing its kill, as a reference in its own collection."""
    import anim_core as A
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(template))
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, len(parts_frames) - 1
    arm = bpy.data.objects["InternalArmature"]
    for pb in arm.pose.bones:
        for c in pb.constraints:
            c.mute = True
        pb.rotation_mode = "QUATERNION"
    ctrl = bpy.data.objects.get("__PrimaryArmature")
    if ctrl:
        ctrl.hide_set(True)
    arm.animation_data_create()
    old = bpy.data.actions.get(action_name)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(action_name)
    act.use_fake_user = True
    arm.animation_data.action = act
    prev = {}
    for f, parts in enumerate(parts_frames):
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
                pb.rotation_quaternion = q
            prev[pb.name] = q.copy()
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
            pb.keyframe_insert("location", frame=f, group=pb.name)
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
    txt = bpy.data.texts.new("KILL_README")
    txt.write(note)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_blend))
