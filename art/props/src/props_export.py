#!/usr/bin/env python3
"""Exports the props for Roblox: each as .fbx and .glb, scaled to studs at the same scale as
the monsters (8 studs for 9 ft, so 2.92 studs to the meter), facing Roblox's forward (-Z).

Also copies the textures Roblox needs into textures/roblox/ and prints the numbers the game's
scripts need: where the tape player's door hinge is and where a tape sits in its bay.

Usage: python3 props_export.py PROPS_DIR [--studs-per-meter 2.916]
"""
import argparse
import os
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import props_build as PB  # noqa: E402


def to_roblox(v):
    """Blender axes to Roblox's, as the exporter maps them (+Y forward to +Z, Z up to Y)."""
    return Vector((-v.x, v.z, v.y))


def center(ob):
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector()) / 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("props")
    ap.add_argument("--studs-per-meter", type=float, default=8.0 / (9 * 0.3048))
    a = ap.parse_args()
    root = os.path.abspath(a.props)
    out = os.path.join(root, "export")
    rbx = os.path.join(root, "textures", "roblox")
    os.makedirs(out, exist_ok=True)
    os.makedirs(rbx, exist_ok=True)
    s = a.studs_per_meter
    for key, name in PB.FILES.items():
        bpy.ops.wm.open_mainfile(filepath=os.path.join(root, f"{name}.blend"))
        S = Matrix.Scale(s, 4)
        for ob in bpy.context.scene.objects:
            ob.matrix_world = S @ ob.matrix_world
            ob.select_set(True)
        bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        title = "".join(w.capitalize() for w in name.split("_"))
        kw = dict(object_types={"MESH"}, use_mesh_modifiers=True, axis_forward="Z", axis_up="Y",
                  apply_scale_options="FBX_SCALE_UNITS", path_mode="COPY", embed_textures=True, mesh_smooth_type="FACE")
        bpy.ops.export_scene.fbx(filepath=os.path.join(out, f"{title}.fbx"), **kw)
        bpy.ops.export_scene.gltf(filepath=os.path.join(out, f"{title}.glb"), export_format="GLB", export_yup=True,
                                  export_materials="EXPORT")
        size = Vector((0, 0, 0))
        obs = list(bpy.context.scene.objects)
        lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in obs for c in o.bound_box) for i in range(3)])
        hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in obs for c in o.bound_box) for i in range(3)])
        size = to_roblox(hi - lo)
        print(f"{title}: {abs(size.x):.3f} x {abs(size.y):.3f} x {abs(size.z):.3f} studs")
        if key == "player":
            door, body = bpy.data.objects["Door"], bpy.data.objects["Body"]
            hinge = Vector(PB.PLAYER_HINGE) * s
            print("  hinge from the door's centre (Roblox axes, studs):", tuple(round(c, 4) for c in to_roblox(hinge - center(door))))
            print("  tape centre from the body's centre:", tuple(round(c, 4) for c in to_roblox(Vector((0.004, 0, 0)) * s - center(body))))
    for f in os.listdir(os.path.join(root, "textures", "baked")):
        shutil.copy(os.path.join(root, "textures", "baked", f), os.path.join(rbx, f))
    for f in ("label_stairwell.png", "label_blank.png", "screen_playback.png"):
        shutil.copy(os.path.join(root, "textures", f), os.path.join(rbx, f))
    print("exported to", out)


if __name__ == "__main__":
    main()
