#!/usr/bin/env python3
"""Renders a rig's actions to looping mp4 previews (Cycles, the poster monster's studio), one
video per action, from a three-quarter view.

Usage: python3 anim_preview.py BLEND RIG OUT_DIR [--actions Idle,Walk,Run] [--target 0,0,1.2]
                               [--offset -4,-3.5,0.3] [--lens 45] [--res 480x600] [--samples 16]
                               [--idle-step 2] [--neutral]
"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "poster_monster", "src")))
import anim_core as A  # noqa: E402
import render  # noqa: E402


def vec(s):
    return tuple(float(x) for x in s.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("rig")
    ap.add_argument("out")
    ap.add_argument("--actions", default="Idle,Walk,Run")
    ap.add_argument("--target", default="0,0,1.2")
    ap.add_argument("--offset", default="-4,-3.5,0.3")
    ap.add_argument("--lens", type=float, default=45)
    ap.add_argument("--res", default="480x600")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--idle-step", type=int, default=2)
    ap.add_argument("--neutral", action="store_true", help="Khronos PBR Neutral, for saturated colours")
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects[a.rig]
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    if "Puddle" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Puddle"])
    sc = bpy.context.scene
    sc.cycles.max_bounces = 4
    if a.neutral:
        sc.view_settings.view_transform = "Khronos PBR Neutral"
        sc.view_settings.exposure = -0.9
    render.VIEWS["preview"] = (None, vec(a.target), vec(a.offset), a.lens)
    acts = a.actions.split(",")
    steps = {n: (a.idle_step if n == "Idle" else 1) for n in acts}
    A.preview(rig, a.out, {n: "preview" for n in acts}, acts, steps)


if __name__ == "__main__":
    main()
