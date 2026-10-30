#!/usr/bin/env python3
"""Poses the Receiver to test his skinning (lunge, reach, crouch, head cock, claw curl) and
renders a contact sheet.

Usage: python3 receiver_rig_check.py BLEND OUT.png [--samples 16]
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
    "lunge": {"LeftUpperLeg": [("x", -55)], "LeftLowerLeg": [("x", 70)], "RightUpperLeg": [("x", 30)],
              "RightLowerLeg": [("x", 35)], "UpperTorso": [("x", -15)], "RightUpperArm": [("x", -70)],
              "RightLowerArm": [("x", -30)], "LeftUpperArm": [("x", 40)]},
    "reach": {"RightUpperArm": [("y", 80), ("x", -40)], "RightLowerArm": [("x", -20)],
              "LeftUpperArm": [("y", -60)], "Head": [("z", 30)]},
    "crouch": {"LeftUpperLeg": [("x", -70)], "RightUpperLeg": [("x", -70)], "LeftLowerLeg": [("x", 110)],
               "RightLowerLeg": [("x", 110)], "LeftFoot": [("x", -40)], "RightFoot": [("x", -40)],
               "UpperTorso": [("x", -25)]},
    "head cock": {"Head": [("y", 35), ("x", 15)], "UpperTorso": [("z", 25)], "LeftLowerArm": [("x", -60)],
                  "DialSpin": [("y", 90)]},
    "claw": {f"Right{f}{k}": [("x", 35)] for f in ("Index", "Middle", "Ring", "Pinky") for k in (1, 2)}
    | {"RightLowerArm": [("x", -70)], "RightHand": [("x", -30)], "RightThumb1": [("z", -30)]},
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
    rig = bpy.data.objects["Receiver_Rig"]
    render.setup("studio", a.samples, (420, 560))
    render.VIEWS["rom"] = (None, (0.0, 0.0, 1.15), (-3.4, -4.4, 0.5), 42)
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
