#!/usr/bin/env python3
"""Poses the Stand-In to test his skinning (a stooped step, a wave, a reach, a crouch, a head tilt with the cable swinging) and
renders a contact sheet.

Usage: python3 standin_rig_check.py BLEND OUT.png [--samples 16]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import render  # noqa: E402

# rotations in degrees about world axes, applied at each bone's head (x tips forward/back,
# y rolls sideways, z turns)
POSES = {
    "rest": {},
    "stooped step": {"LeftUpperLeg": [("x", -30)], "LeftLowerLeg": [("x", 25)], "RightUpperLeg": [("x", 18)],
                     "RightLowerLeg": [("x", 20)], "UpperTorso": [("x", -14)], "Head": [("x", -12)],
                     "LeftUpperArm": [("x", 20)], "RightUpperArm": [("x", -15)]},
    "wave": {"RightUpperArm": [("y", 70), ("x", -20)], "RightLowerArm": [("y", 80)], "Head": [("y", 18)],
             "RightIndex1": [("x", -10)], "RightMiddle1": [("x", -10)]},
    "reach": {"LeftUpperArm": [("x", -80)], "LeftLowerArm": [("x", -15)], "RightUpperArm": [("x", -70)],
              "UpperTorso": [("x", -20)], "Head": [("x", 10)]},
    "crouch": {"LeftUpperLeg": [("x", -80)], "RightUpperLeg": [("x", -80)], "LeftLowerLeg": [("x", 110)],
               "RightLowerLeg": [("x", 110)], "LeftFoot": [("x", -30)], "RightFoot": [("x", -30)],
               "UpperTorso": [("x", -30)]},
    "head tilt": {"Head": [("y", 30)], "UpperTorso": [("z", 20)], "Cable1": [("y", -25)], "Cable2": [("y", -20)],
                  "Cable3": [("y", -20)], "LeftHand": [("x", -40)]},
}


def apply(rig, pose):
    ax = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        q = Quaternion()
        rinv = pb.bone.matrix_local.to_3x3().inverted()
        for a, deg in pose.get(pb.name, []):
            q = Quaternion((rinv @ ax[a]).normalized(), math.radians(deg)) @ q
        pb.rotation_quaternion = q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["StandIn_Rig"]
    render.setup("studio", a.samples, (420, 560))
    try:  # the same color handling as the previews
        bpy.context.scene.view_settings.view_transform = "Khronos PBR Neutral"
        bpy.context.scene.view_settings.look = "None"
        bpy.context.scene.view_settings.exposure = -0.9
    except TypeError:
        pass
    render.VIEWS["rom"] = (None, (0.0, 0.0, 1.3), (-3.8, -4.9, 0.5), 42)
    bpy.context.scene.camera = render.camera("Cam_rom", "rom", rig)
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_rom")
    os.makedirs(tmp, exist_ok=True)
    tiles = []
    for name, pose in POSES.items():
        apply(rig, pose)
        p = os.path.join(tmp, name.replace(" ", "_") + ".png")
        bpy.context.scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append((name, p))
    w, h = 420, 560
    sheet = Image.new("RGB", (w * 3, h * 2), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 20)
    for i, (name, p) in enumerate(tiles):
        x, y = (i % 3) * w, (i // 3) * h
        sheet.paste(Image.open(p).convert("RGB"), (x, y))
        d.text((x + 12, y + 10), name, font=fnt, fill=(240, 240, 240))
    sheet.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
