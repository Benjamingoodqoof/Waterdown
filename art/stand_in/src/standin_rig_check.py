#!/usr/bin/env python3
"""Poses the Stand-in the way player animations would (run, sit, arms up, twist) and renders a
contact sheet, to check the R15 joints and the skirt.

Usage: python3 standin_rig_check.py BLEND OUT.png [--samples 16]
"""
import argparse
import os
import sys

import bpy
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import standin_render as SR  # noqa: E402

POSES = {
    "rest": {},
    "run": {"LeftUpperLeg": [("x", -45)], "LeftLowerLeg": [("x", 60)], "RightUpperLeg": [("x", 35)],
            "RightLowerLeg": [("x", 20)], "LeftUpperArm": [("x", 40)], "RightUpperArm": [("x", -45)],
            "RightLowerArm": [("x", -60)], "LeftLowerArm": [("x", -40)], "UpperTorso": [("x", 10)]},
    "sit": {"LeftUpperLeg": [("x", -90)], "RightUpperLeg": [("x", -90)], "LeftLowerLeg": [("x", 90)],
            "RightLowerLeg": [("x", 90)], "LeftUpperArm": [("x", -30)], "RightUpperArm": [("x", -30)]},
    "arms up": {"LeftUpperArm": [("y", -170)], "RightUpperArm": [("y", 170)], "Head": [("x", -20)]},
    "twist": {"UpperTorso": [("z", 35)], "Head": [("z", 40), ("y", 20)], "LeftUpperLeg": [("x", -30)],
              "RightUpperArm": [("x", -70)], "RightLowerArm": [("x", -50)]},
    "mimic": SR.MIMIC,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["StandIn_Rig"]
    SR.setup(a.samples, (420, 560))
    SR.render.VIEWS["rom"] = (None, (0.0, 0.0, 1.2), (-3.4, -4.4, 0.5), 42)
    bpy.context.scene.camera = SR.render.camera("Cam_rom", "rom", rig)
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_rom")
    os.makedirs(tmp, exist_ok=True)
    tiles = []
    for name, pose in POSES.items():
        SR.apply(rig, pose)
        p = os.path.join(tmp, name.replace(" ", "_") + ".png")
        bpy.context.scene.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append((name, p))
    ims = [Image.open(p) for _, p in tiles]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * 3, h * 2), (20, 20, 22))
    f = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 20)
    for i, ((name, _), im) in enumerate(zip(tiles, ims)):
        sheet.paste(im, ((i % 3) * w, (i // 3) * h))
        ImageDraw.Draw(sheet).text(((i % 3) * w + 12, (i // 3) * h + 10), name, font=f, fill=(235, 235, 235))
    sheet.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
