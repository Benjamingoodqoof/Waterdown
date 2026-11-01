#!/usr/bin/env python3
"""Exports the Receiver for Roblox with his animations: Receiver.fbx (rigged, rest pose),
Receiver_<Action>.fbx (one per animation, to import with the Animation Editor), Receiver.glb
(every animation) and Receiver_Roblox.blend.

The scale matches the poster monster (8 studs for 9 ft), so at 8 ft he's 7.1 studs tall, and
the origin is his pelvis (the Root bone), where Roblox puts the HumanoidRootPart. Every
texture is already 1024 px.

Usage: python3 receiver_export.py BLEND OUT_DIR [--height-studs 7.11]
"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
from export import to_roblox_units  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--height-studs", type=float, default=8.0 * 8.0 / 9.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["Receiver_Rig"]
    rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)
    scale, pelvis = to_roblox_units(rig, a.height_studs)
    acts = A.export_actions(rig, a.out, "Receiver", names=("Idle", "Walk", "Run", "Call"))
    print(f"exported to {a.out}: {a.height_studs:.2f} studs tall (x{scale:.3f}), pelvis {pelvis:.2f} studs up; "
          f"animations: {', '.join(acts)}")


if __name__ == "__main__":
    main()
