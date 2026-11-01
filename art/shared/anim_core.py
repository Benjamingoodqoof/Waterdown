"""Shared animation tools for the REM CYCLE monsters (Blender 5, `bpy`).

- Poses are written as rotations about world axes (as the bones sit at rest): +x tips a bone's
  tip backward when it hangs down and forward when it points up, y rolls it sideways, z turns
  it. Local axes (lx, ly, lz) are allowed too.
- Legs are solved with a two-bone IK every frame, aiming each bone with the smallest swing
  from where its parent leaves it, so no bone ever picks up a twist about its own length.
  The result is written out as plain rotation keys: ordinary FK animation any exporter reads.
- Cycles are in place, 30 fps, and loop: the last frame equals the first.
- export_actions writes one FBX per action plus a GLB and a .blend with every action, all in
  studs, after the monster's own export has scaled the scene.
"""
import math
import os
import subprocess

import bpy
from mathutils import Matrix, Quaternion, Vector

FPS = 30
AX = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
LOCAL = {"lx": Vector((1, 0, 0)), "ly": Vector((0, 1, 0)), "lz": Vector((0, 0, 1))}


# ---------------------------------------------------------------- timing helpers
def wave(phi, freq=1.0, off=0.0):
    return math.sin(2 * math.pi * (freq * phi + off))


def cwave(phi, freq=1.0, off=0.0):
    return math.cos(2 * math.pi * (freq * phi + off))


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def bump(f, a, b, c):
    """0 before frame a, rises to 1 by b, eases back to 0 by c."""
    if f <= a or f >= c:
        return 0.0
    return ease((f - a) / (b - a)) if f < b else 1.0 - ease((f - b) / (c - b))


def loop_noise(phi, seed, harmonics=3):
    """Smooth noise in -1..1 that loops over one cycle (a few whole-period waves)."""
    out = 0.0
    for k in range(1, harmonics + 1):
        out += math.sin(2 * math.pi * (k * phi + 0.137 * seed * k + 0.31 * seed)) / k
    return out / 1.83


def mirror(rots, side):
    """A left-side rotation list for the right side: Y and Z turns flip."""
    if side == "Left":
        return rots
    return [(a, -d if a in ("y", "z", "ly", "lz") else d) for a, d in rots]


def bone_quat(bone, rots):
    Rinv = bone.matrix_local.to_3x3().inverted()
    q = Quaternion()
    for axis, deg in rots:
        a = LOCAL[axis] if axis in LOCAL else Rinv @ AX[axis]
        q = Quaternion(a.normalized(), math.radians(deg)) @ q
    return q


# ---------------------------------------------------------------- gait
def foot_path(phi, duty, stride, lift, dangle, toe_first=True):
    """An in-place foot at cycle phase phi: (y offset, height, toe pitch in degrees, planted).
    During stance the foot slides back at ground speed; it lands toes first (if asked) and
    rolls off the toes."""
    if phi < duty:
        s = phi / duty
        y, z, pitch = -stride / 2 + stride * s, 0.0, 0.0
        if toe_first and s < 0.12:
            z, pitch = 0.03 * (1 - s / 0.12), 10 * (1 - s / 0.12)
        elif s > 0.8:
            t = (s - 0.8) / 0.2
            z, pitch = 0.06 * t, 24 * t
        return y, z, pitch, True
    s = (phi - duty) / (1 - duty)
    y = stride / 2 - stride * ease(s)
    z = 0.06 * (1 - s) + 0.03 * s + lift * math.sin(math.pi * s) ** 0.9
    pitch = 24 * (1 - s) ** 2 + dangle * math.sin(math.pi * s) + (10 * s * s if toe_first else 0.0)
    return y, z, pitch, False


def biped_legs(an, phi, duty, stride, lift, dangle=15, splay=0.1, stance_x=0.0, toe_first=True, drop=0.0):
    """Both legs of a humanoid rig through a gait cycle (the right half a cycle behind), feet
    planted during stance. drop lowers the feet's rest height (the pelvis is lowered by the
    caller), so the knees stay bent."""
    for side, sx in (("Left", 1.0), ("Right", -1.0)):
        ph = (phi + (0.0 if side == "Left" else 0.5)) % 1.0
        y, z, pitch, _ = foot_path(ph, duty, stride, lift, dangle, toe_first)
        rest = an.pb[f"{side}Foot"].bone.head_local
        an.leg(side, Vector((rest.x + sx * stance_x, rest.y + y, rest.z + z - drop)), pitch, splay * sx)


def impact(phi, hits, decay=6.0, freq=2.5, lag=0.0):
    """A damped wobble set off at each phase in `hits` (a looping cycle), delayed by `lag`."""
    out = 0.0
    for h in hits:
        dt = (phi - h - lag) % 1.0
        out += math.exp(-decay * dt) * math.sin(2 * math.pi * freq * dt)
    return out


class Animator:
    def __init__(self, rig, loc_bones=("LowerTorso",)):
        self.rig = rig
        self.pb = rig.pose.bones
        self.loc_bones = loc_bones
        self.prev = {}

    def reset(self):
        for pb in self.pb:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)

    def fk(self, pose, loc=None):
        """pose: {bone: [(axis, degrees), ...]}; loc: {bone: world-space offset}."""
        for name, rots in pose.items():
            if name in self.pb:
                self.pb[name].rotation_quaternion = bone_quat(self.pb[name].bone, rots)
        for name, off in (loc or {}).items():
            pb = self.pb[name]
            pb.location = pb.bone.matrix_local.to_3x3().inverted() @ Vector(off)

    def aim(self, pb, direction):
        """Turn a bone (from where its parent leaves it) so it points along `direction`
        (armature space), with the smallest swing."""
        pb.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        M = pb.matrix.copy()
        y = M.to_3x3().col[1].normalized()
        R = y.rotation_difference(direction.normalized()).to_matrix() @ M.to_3x3()
        out = R.to_4x4()
        out.translation = M.translation
        pb.matrix = out
        pb.location = (0, 0, 0)
        bpy.context.view_layer.update()

    def two_bone(self, upper, lower, target, pole):
        """Two-bone IK: `upper` and `lower` reach `target` (armature space), the middle joint
        bending toward `pole` (a direction)."""
        bpy.context.view_layer.update()
        a, b = self.pb[upper], self.pb[lower]
        a.rotation_quaternion = (1, 0, 0, 0)
        bpy.context.view_layer.update()
        root = a.head.copy()
        l1, l2 = a.bone.length, b.bone.length
        d = target - root
        dist = max(abs(l1 - l2) + 1e-4, min(d.length, (l1 + l2) * 0.9995))
        u = d.normalized()
        w = (pole - u * pole.dot(u)).normalized()
        ang = math.acos(max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))))
        mid = root + (u * math.cos(ang) + w * math.sin(ang)) * l1
        self.aim(a, mid - root)
        self.aim(b, root + u * dist - mid)

    def leg(self, side, ankle, pitch_deg=0.0, splay=0.0):
        """A humanoid leg ({side}UpperLeg, LowerLeg, Foot): the ankle reaches `ankle` with the
        knee forward, and the foot keeps its rest angle to the floor, pitched about X (+ toes
        down)."""
        self.two_bone(f"{side}UpperLeg", f"{side}LowerLeg", ankle, Vector((splay, -1.0, 0.0)))
        ft = self.pb[f"{side}Foot"]
        rot = Matrix.Rotation(math.radians(pitch_deg), 4, "X") @ ft.bone.matrix_local.to_3x3().to_4x4()
        rot.translation = self.pb[f"{side}LowerLeg"].tail.copy()
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
            if pb.name in self.loc_bones:
                pb.keyframe_insert("location", frame=frame, group=pb.name)


def build_actions(rig, actions, loc_bones=("LowerTorso",)):
    """actions: [(name, frames, fn(an, phi, frame))]. Keys every frame; the last equals the first."""
    an = Animator(rig, loc_bones)
    rig.animation_data_create()
    made = {}
    for name, length, fn in actions:
        old = bpy.data.actions.get(name)
        if old:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        rig.animation_data.action = act
        an.prev = {}
        for f in range(length + 1):
            an.reset()
            fn(an, (f % length) / length, f % length)
            an.key(f)
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, length
        act.use_cyclic = True
        made[name] = act
    an.reset()
    rig.animation_data.action = made[actions[0][0]]
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, actions[0][1]
    return made


# ---------------------------------------------------------------- export and previews
def action_fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


FBX_KW = dict(object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=False, add_leaf_bones=False, axis_forward="-Z",
              axis_up="Y", apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY", embed_textures=True,
              mesh_smooth_type="FACE", use_armature_deform_only=False, primary_bone_axis="Y", secondary_bone_axis="X",
              armature_nodetype="NULL")


def export_actions(rig, out_dir, base, names=("Idle", "Walk", "Run"), fbx_kw=None):
    """After the scene is scaled to studs: base.fbx (rest pose), base_<Action>.fbx for each
    action, base.glb with every action, and base_Roblox.blend."""
    kw = dict(FBX_KW, **(fbx_kw or {}))
    sc = bpy.context.scene
    acts = [bpy.data.actions[n] for n in names if n in bpy.data.actions]
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, f"{base}.fbx"), bake_anim=False, **kw)
    for act in acts:
        rig.animation_data.action = act
        sc.frame_start, sc.frame_end = int(act.frame_start), int(act.frame_end)
        bpy.ops.export_scene.fbx(filepath=os.path.join(out_dir, f"{base}_{act.name}.fbx"), bake_anim=True,
                                 bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                                 bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, **kw)
    if acts:
        rig.animation_data.action = acts[0]
        sc.frame_start, sc.frame_end = 0, int(acts[0].frame_end)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out_dir, f"{base}.glb"), export_format="GLB", export_skins=True,
                              export_animations=bool(acts), export_animation_mode="ACTIONS", export_yup=True,
                              export_apply=False, export_materials="EXPORT")
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(out_dir), f"{base}_Roblox.blend"))
    return [a.name for a in acts]


def preview(rig, out_dir, views, actions=("Idle", "Walk", "Run"), step=1, loops=3):
    """Renders each action from its camera in `views` ({action: view name in render.VIEWS})
    to an mp4 (looped `loops` times; the idle once). The scene, lights and cameras are the
    caller's."""
    import render  # the poster monster's studio helpers, on the caller's path
    sc = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    for name in actions:
        act = bpy.data.actions[name]
        rig.animation_data.action = act
        sc.camera = render.camera(f"Cam_{name}", views[name], rig)
        frames_dir = os.path.join(os.path.abspath(out_dir), f"_{name}")
        os.makedirs(frames_dir, exist_ok=True)
        paths = []
        for f in range(int(act.frame_start), int(act.frame_end), step):
            sc.frame_set(f)
            p = os.path.join(frames_dir, f"f_{f:04d}.png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            paths.append(p)
        listing = os.path.join(frames_dir, "list.txt")
        with open(listing, "w") as fh:
            for _ in range(1 if name == "Idle" else loops):
                for p in paths:
                    fh.write(f"file '{p}'\nduration {step / FPS:.5f}\n")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-vf",
                        "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20", os.path.join(out_dir, f"{name}.mp4")],
                       check=True)
        print("preview", name)
