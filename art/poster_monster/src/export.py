#!/usr/bin/env python3
"""Exports the rigged poster monster for Roblox, with the 1024px textures Roblox accepts:
- PosterMonster.fbx: the rigged model in the rest pose, for the 3D Importer
- PosterMonster_<Action>.fbx: one per animation (Idle, Walk, Run)
- PosterMonster.glb: model plus all animations
- PosterMonster_Roblox.blend: the same scene with the actions, for exporting animations
  with a Roblox animation plugin

Roblox reads the file's numbers as studs, so everything is scaled to the target height in
studs (animation translations too), and moved so the origin is the pelvis (the Root bone),
where Roblox puts the HumanoidRootPart.

Usage: python3 export.py BLEND OUT_DIR [--height-studs 8]
"""
import argparse
import os

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_RBX = os.path.normpath(os.path.join(HERE, "..", "textures", "roblox"))


def action_fcurves(action):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                yield from bag.fcurves


def to_roblox_units(rig, height_studs):
    """Scales and shifts meshes, bones and animation translations together.
    Returns (scale, pelvis height in studs)."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    zs = [v.co.z for o in meshes for v in o.data.vertices]
    root = rig.data.bones["Root"].head_local.copy()
    scale = height_studs / (max(zs) - min(zs))
    m = Matrix.Scale(scale, 4) @ Matrix.Translation(-root)
    for o in meshes:  # parented to the rig with identity transforms
        o.data.transform(m)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for eb in rig.data.edit_bones:
        roll = eb.roll
        eb.head, eb.tail = m @ eb.head, m @ eb.tail
        eb.roll = roll
    bpy.ops.object.mode_set(mode="OBJECT")
    for action in bpy.data.actions:  # bone translations are in bone space, so they scale too
        for fc in action_fcurves(action):
            if fc.data_path.endswith(".location"):
                for kp in fc.keyframe_points:
                    kp.co.y *= scale
                    kp.handle_left.y *= scale
                    kp.handle_right.y *= scale
    return scale, (root.z - min(zs)) * scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--height-studs", type=float, default=8.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    scale, pelvis = to_roblox_units(rig, a.height_studs)

    # swap the 2048 authoring maps for the 1024 copies Roblox accepts
    for img in bpy.data.images:
        path = os.path.join(TEX_RBX, os.path.basename(img.filepath))
        if os.path.exists(path):
            if img.packed_file:
                img.unpack(method="REMOVE")
            img.filepath = path
            img.reload()

    fbx = dict(object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=False, add_leaf_bones=False, axis_forward="-Z",
               axis_up="Y", apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY", embed_textures=True,
               mesh_smooth_type="FACE", use_armature_deform_only=False, primary_bone_axis="Y",
               secondary_bone_axis="X", armature_nodetype="NULL")
    bpy.ops.export_scene.fbx(filepath=os.path.join(a.out, "PosterMonster.fbx"), bake_anim=False, **fbx)
    actions = [act for act in bpy.data.actions if act.name in ("Idle", "Walk", "Run")]
    sc = bpy.context.scene
    for act in actions:
        rig.animation_data.action = act
        sc.frame_start, sc.frame_end = int(act.frame_start), int(act.frame_end)
        bpy.ops.export_scene.fbx(filepath=os.path.join(a.out, f"PosterMonster_{act.name}.fbx"), bake_anim=True,
                                 bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                                 bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0, **fbx)
    if actions:
        rig.animation_data.action = next(act for act in actions if act.name == "Idle")
        sc.frame_start, sc.frame_end = 0, int(rig.animation_data.action.frame_end)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(a.out, "PosterMonster.glb"), export_format="GLB", export_skins=True,
        export_animations=bool(actions), export_animation_mode="ACTIONS", export_yup=True, export_apply=False,
        export_materials="EXPORT",
    )
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), "PosterMonster_Roblox.blend"))
    print(f"exported to {a.out}: {a.height_studs:.2f} studs tall (x{scale:.3f}), pelvis {pelvis:.2f} studs up, "
          f"animations: {', '.join(act.name for act in actions) or 'none'}")


if __name__ == "__main__":
    main()
