#!/usr/bin/env python3
"""Renders a contact sheet of a rig's actions (a row of evenly spaced frames per action), to
check animation quickly.

Usage: python3 anim_sheet.py BLEND RIG OUT.png [--actions Idle,Walk,Run] [--frames 6]
                             [--target 0,0,1.2] [--offset -4,-3.5,0.3] [--lens 45] [--res 320x400]
"""
import argparse
import os
import sys

import bpy
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "poster_monster", "src")))
import render  # noqa: E402


def vec(s):
    return tuple(float(x) for x in s.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("rig")
    ap.add_argument("out")
    ap.add_argument("--actions", default="Idle,Walk,Run")
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--target", default="0,0,1.2")
    ap.add_argument("--offset", default="-4,-3.5,0.3")
    ap.add_argument("--lens", type=float, default=45)
    ap.add_argument("--res", default="320x400")
    ap.add_argument("--samples", type=int, default=8)
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects[a.rig]
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    if "Puddle" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Puddle"])
    sc = bpy.context.scene
    sc.cycles.max_bounces = 3
    render.VIEWS["sheet"] = (None, vec(a.target), vec(a.offset), a.lens)
    sc.camera = render.camera("CamSheet", "sheet", rig)
    acts = a.actions.split(",")
    sheet = Image.new("RGB", (w * a.frames, h * len(acts)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 16)
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_sheet.png")
    for r, name in enumerate(acts):
        act = bpy.data.actions[name]
        rig.animation_data.action = act
        n = int(act.frame_end - act.frame_start)
        for c in range(a.frames):
            f = int(act.frame_start) + round(n * c / a.frames)
            sc.frame_set(f)
            sc.render.filepath = tmp
            bpy.ops.render.render(write_still=True)
            sheet.paste(Image.open(tmp).convert("RGB"), (c * w, r * h))
            d.text((c * w + 6, r * h + 4), f"{name} {f}", font=fnt, fill=(235, 235, 235))
    sheet.save(a.out)
    os.remove(tmp)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
