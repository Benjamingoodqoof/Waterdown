#!/usr/bin/env python3
"""Exports the rigged poster monster for Roblox: a .glb and an .fbx in the rest pose, with
the 1024px textures Roblox accepts.

Roblox reads the file's numbers as studs, so the export is scaled to the target height in
studs, and moved so the origin is the pelvis (the Root bone), where Roblox puts the
HumanoidRootPart.

Usage: python3 export.py BLEND OUT_DIR [--height-studs 8]
"""
import argparse
import os

import bpy
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_RBX = os.path.normpath(os.path.join(HERE, "..", "textures", "roblox"))


def to_roblox_units(rig, height_studs):
    """Scales and shifts meshes and bones together. Returns (scale, pelvis height in studs)."""
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
    if rig.animation_data:
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

    bpy.ops.export_scene.gltf(
        filepath=os.path.join(a.out, "PosterMonster.glb"), export_format="GLB", export_skins=True,
        export_animations=False, export_yup=True, export_apply=False, export_materials="EXPORT",
    )
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(a.out, "PosterMonster.fbx"), object_types={"ARMATURE", "MESH"},
        use_mesh_modifiers=False, add_leaf_bones=False, bake_anim=False, axis_forward="-Z", axis_up="Y",
        apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE",
        use_armature_deform_only=False, primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
    )
    print(f"exported to {a.out}: {a.height_studs:.2f} studs tall (x{scale:.3f}), pelvis {pelvis:.2f} studs up")


if __name__ == "__main__":
    main()
