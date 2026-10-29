#!/usr/bin/env python3
"""Range-of-motion test for the rig: poses the monster in extreme poses and renders a
contact sheet, to catch skinning problems before animating.

Usage: python3 rig_check.py BLEND OUT.png [--samples 16]
"""
import argparse
import os
import sys

import bpy
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import posing  # noqa: E402
import render  # noqa: E402
from posing import hand, sided  # noqa: E402


def poses():
    P = {}
    P["rest"] = {}
    reach = sided({
        "Spine": [("x", 15)], "UpperTorso": [("x", 15)], "Neck": [("x", 10)], "Head": [("x", -25)],
        "{s}Shoulder": [("x", -10)], "{s}UpperArm": [("x", -85), ("y", 10)], "{s}LowerArm": [("x", -25)],
        "{s}UpperLeg": [("x", -10)], "{s}LowerLeg": [("x", 15)],
    })
    reach.update(hand("Left", (5, 5, 5), 18))
    reach.update(hand("Right", (5, 5, 5), 18))
    P["reach"] = reach
    P["arms out"] = sided({
        "{s}UpperArm": [("y", -70)], "{s}LowerArm": [("x", -40)], "Head": [("y", -30)],
    })
    crouch = sided({
        "LowerTorso": [("x", 30)], "Spine": [("x", 20)], "UpperTorso": [("x", 15)], "Neck": [("x", -10)],
        "Head": [("x", -35)], "{s}UpperLeg": [("x", -95), ("y", -10)], "{s}LowerLeg": [("x", 115)],
        "{s}Foot": [("x", -20)], "{s}UpperArm": [("x", -30)], "{s}LowerArm": [("x", -30)],
    })
    P["crouch"] = crouch
    twist = sided({
        "Spine": [("z", 20)], "UpperTorso": [("z", 25), ("y", 10)], "Neck": [("z", 25)],
        "Head": [("z", 45), ("y", -35)], "LeftUpperArm": [("x", -40)], "RightUpperArm": [("x", 30)],
        "LeftUpperLeg": [("x", -35)], "LeftLowerLeg": [("x", 50)], "RightUpperLeg": [("x", 20)],
    })
    P["twist"] = twist
    fist = sided({"{s}LowerArm": [("x", -95)], "{s}UpperArm": [("x", -20)], "{s}Hand": [("x", 30)]})
    fist.update(hand("Left", (70, 75, 60), 0, thumb=(30, 40, 40)))
    fist.update(hand("Right", (70, 75, 60), 0, thumb=(30, 40, 40)))
    P["fists"] = fist
    lunge = sided({
        "LowerTorso": [("x", 20)], "Spine": [("x", 25)], "UpperTorso": [("x", 20)], "Neck": [("x", -20)],
        "Head": [("x", -30), ("y", 25)], "LeftUpperArm": [("x", -110), ("y", 25)], "LeftLowerArm": [("x", -10)],
        "RightUpperArm": [("x", -60), ("y", -30)], "RightLowerArm": [("x", -50)],
        "LeftUpperLeg": [("x", -60)], "LeftLowerLeg": [("x", 70)], "RightUpperLeg": [("x", 25)],
        "RightLowerLeg": [("x", 30)], "RightFoot": [("x", 20)],
    })
    lunge.update(hand("Left", (-10, 10, 20), 25))
    lunge.update(hand("Right", (40, 50, 50), 10))
    P["lunge"] = lunge
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    render.setup("studio", a.samples, (420, 560))
    render.VIEWS["rom"] = (None, (0.0, 0.0, 1.2), (-3.6, -4.6, 0.6), 42)
    cam = render.camera("Cam_rom", "rom", rig)
    bpy.context.scene.camera = cam
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_rom")
    os.makedirs(tmp, exist_ok=True)
    tiles = []
    for name, pose in poses().items():
        posing.apply_pose(rig, pose)
        path = os.path.join(tmp, name.replace(" ", "_") + ".png")
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append((name, path))
    ims = [Image.open(p) for _, p in tiles]
    cols = 4
    rows = (len(ims) + cols - 1) // cols
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * cols, h * rows), (20, 20, 22))
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 20)
    for i, ((name, _), im) in enumerate(zip(tiles, ims)):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        ImageDraw.Draw(sheet).text(((i % cols) * w + 12, (i // cols) * h + 10), name, font=font, fill=(235, 235, 235))
    sheet.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
