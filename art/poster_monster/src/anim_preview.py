#!/usr/bin/env python3
"""Renders preview videos (and a contact sheet) of the monster's animations.

Usage: python3 anim_preview.py BLEND OUT_DIR [--actions Idle,Walk,Run] [--step 1] [--samples 12]
                               [--res 480x640] [--sheet]
"""
import argparse
import os
import subprocess
import sys

import bpy
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render  # noqa: E402

VIEW = {"Idle": (None, (0.0, 0.0, 1.35), (-2.4, -4.6, 0.35), 50),
        "Walk": (None, (0.0, 0.0, 1.25), (-4.4, -3.4, 0.25), 50),
        "Run": (None, (0.0, 0.0, 1.15), (-4.4, -3.6, 0.2), 50),
        "RunSide": (None, (0.0, 0.0, 1.15), (-5.6, 0.0, 0.2), 50)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--actions", default="Idle,Walk,Run")
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--res", default="480x640")
    ap.add_argument("--sheet", action="store_true")
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    sc = bpy.context.scene
    sc.cycles.max_bounces = 4
    os.makedirs(a.out, exist_ok=True)
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", 18)
    for name in a.actions.split(","):
        view = name
        if ":" in name:  # Action:View picks another camera
            name, view = name.split(":")
        act = bpy.data.actions[name]
        rig.animation_data.action = act
        render.VIEWS[f"anim_{name}"] = VIEW[view]
        sc.camera = render.camera(f"Cam_{name}", f"anim_{name}", rig)
        frames_dir = os.path.join(os.path.abspath(a.out), f"_{name}")
        os.makedirs(frames_dir, exist_ok=True)
        frames = list(range(int(act.frame_start), int(act.frame_end), a.step))
        paths = []
        for f in frames:
            sc.frame_set(f)
            p = os.path.join(frames_dir, f"f_{f:04d}.png")
            if not os.path.exists(p):  # frames from an earlier run are reused
                sc.render.filepath = p
                bpy.ops.render.render(write_still=True)
            paths.append(p)
        if a.sheet:
            ims = [Image.open(p) for p in paths]
            cols = min(6, len(ims))
            rows = (len(ims) + cols - 1) // cols
            sheet = Image.new("RGB", (w * cols, h * rows))
            for i, (f, im) in enumerate(zip(frames, ims)):
                sheet.paste(im, ((i % cols) * w, (i // cols) * h))
                ImageDraw.Draw(sheet).text(((i % cols) * w + 8, (i // cols) * h + 6), f"{name} {f}", font=font,
                                           fill=(240, 240, 240))
            sheet.save(os.path.join(a.out, f"{name}_sheet.png"))
        else:
            # loop it three times so the cycle reads in the preview
            listing = os.path.join(frames_dir, "list.txt")
            with open(listing, "w") as fh:
                for _ in range(3 if name != "Idle" else 1):
                    for p in paths:
                        fh.write(f"file '{p}'\nduration {a.step / 30:.5f}\n")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-vf",
                            "fps=30,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                            os.path.join(a.out, f"{name}.mp4")], check=True)
        print("done", name)


if __name__ == "__main__":
    main()
