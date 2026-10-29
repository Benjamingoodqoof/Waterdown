#!/usr/bin/env python3
"""Exports the rigged poster monster for Roblox: a .glb and an .fbx in the rest pose, with
the 1024px textures Roblox accepts.

Usage: python3 export.py BLEND OUT_DIR
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
TEX_RBX = os.path.normpath(os.path.join(HERE, "..", "textures", "roblox"))


def main(blend, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)

    # swap the 2048 authoring maps for the 1024 copies Roblox accepts
    for img in bpy.data.images:
        path = os.path.join(TEX_RBX, os.path.basename(img.filepath))
        if os.path.exists(path):
            if img.packed_file:
                img.unpack(method="REMOVE")
            img.filepath = path
            img.reload()

    bpy.ops.export_scene.gltf(
        filepath=os.path.join(out_dir, "PosterMonster.glb"), export_format="GLB", export_skins=True,
        export_animations=False, export_yup=True, export_apply=False, export_materials="EXPORT",
    )
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(out_dir, "PosterMonster.fbx"), object_types={"ARMATURE", "MESH"},
        use_mesh_modifiers=False, add_leaf_bones=False, bake_anim=False, axis_forward="-Z", axis_up="Y",
        apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE",
        use_armature_deform_only=False, primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
    )
    print("exported to", out_dir)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
