#!/usr/bin/env python3
"""Exports the Stand-in for Roblox: an R15 model (15 body parts plus BadgePhoto) as .fbx and
.glb, and a Roblox-scaled .blend, with 1024px textures.

The scale matches the poster monster (8 studs for 9 ft), so she is about 7.4 studs tall, and
the origin is her pelvis (the Root bone), where Roblox puts the HumanoidRootPart.

Usage: python3 standin_export.py BLEND OUT_DIR [--height-studs 7.38]
"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
from export import to_roblox_units  # noqa: E402

TEX_RBX = os.path.normpath(os.path.join(HERE, "..", "textures", "roblox"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--height-studs", type=float, default=8.0 * 8.3 / 9.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["StandIn_Rig"]
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
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(a.out, "StandIn.fbx"), object_types={"ARMATURE", "MESH"}, use_mesh_modifiers=False,
        add_leaf_bones=False, bake_anim=False, axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_UNITS",
        path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE", use_armature_deform_only=False,
        primary_bone_axis="Y", secondary_bone_axis="X", armature_nodetype="NULL",
    )
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(a.out, "StandIn.glb"), export_format="GLB", export_skins=True,
        export_animations=False, export_yup=True, export_apply=False, export_materials="EXPORT",
    )
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.abspath(a.out), "StandIn_Roblox.blend"))
    print(f"exported to {a.out}: {a.height_studs:.2f} studs tall (x{scale:.3f}), pelvis {pelvis:.2f} studs up")


if __name__ == "__main__":
    main()
