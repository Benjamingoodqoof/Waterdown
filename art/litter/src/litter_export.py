#!/usr/bin/env python3
"""Exports the Litter for Roblox with its animations, for the stack and the litterling:
<Name>.fbx (rigged, rest pose), <Name>_<Action>.fbx (one per animation, to import with the
Animation Editor), <Name>.glb (every animation) and <Name>_Roblox.blend, with Name = Stack or
Litterling. Also copies the baked maps into textures/roblox/.

The scale matches the other monsters (8 studs for 9 ft, 2.92 studs a meter), for both, so a
litterling stays knee-high next to the stack. Each model's origin is its Root bone: the stack's
pelvis, and the litterling's body height between its legs.

Usage: python3 litter_export.py LITTER_DIR OUT_DIR
"""
import argparse
import os
import shutil
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
from export import to_roblox_units  # noqa: E402

STUDS_PER_M = 8.0 / (9 * 0.3048)


def export(blend, rig_name, base, out):
    bpy.ops.wm.open_mainfile(filepath=blend)
    rig = bpy.data.objects[rig_name]
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    zs = [v.co.z for o in bpy.data.objects if o.type == "MESH" for v in o.data.vertices]
    height = (max(zs) - min(zs)) * STUDS_PER_M
    scale, pelvis = to_roblox_units(rig, height)
    acts = A.export_actions(rig, out, base)
    print(f"{base}: {height:.2f} studs tall, root {pelvis:.2f} studs up; animations: {', '.join(acts)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("litter")
    ap.add_argument("out")
    a = ap.parse_args()
    root, out = os.path.abspath(a.litter), os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    export(os.path.join(root, "stack.blend"), "Stack_Rig", "Stack", out)
    export(os.path.join(root, "litterling.blend"), "Litterling_Rig", "Litterling", out)
    tex = os.path.join(root, "textures")
    rbx = os.path.join(tex, "roblox")
    os.makedirs(rbx, exist_ok=True)
    for f in os.listdir(os.path.join(tex, "baked")):
        shutil.copy(os.path.join(tex, "baked", f), os.path.join(rbx, f))


if __name__ == "__main__":
    main()
