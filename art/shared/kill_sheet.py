#!/usr/bin/env python3
"""Renders a kill animation's preview blend (from kill_core.run_kill) as a contact sheet: a
third-person row and a first-person row (the victim's eyes).

Usage: python3 kill_sheet.py PREVIEW_BLEND OUT.png [--frames 0,10,20] [--target 0,-0.6,1.2]
                             [--offset -3.5,-3.2,0.4] [--lens 35] [--res 300x240] [--samples 10]
"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "poster_monster", "src")))
import kill_core as K  # noqa: E402
import render  # noqa: E402


def vec(s):
    return tuple(float(x) for x in s.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--frames", default="0,15,30,45,60,75,90,105,120")
    ap.add_argument("--target", default="0,-0.6,1.2")
    ap.add_argument("--offset", default="-3.5,-3.2,0.4")
    ap.add_argument("--lens", type=float, default=35)
    ap.add_argument("--res", default="300x240")
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--fp-only", action="store_true")
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    if "Puddle" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Puddle"])
    bpy.context.scene.cycles.max_bounces = 3
    render.VIEWS["kill"] = (None, vec(a.target), vec(a.offset), a.lens)
    tp = render.camera("TP", "kill", None)
    cams = [bpy.data.objects["FP"]] if a.fp_only else [tp, bpy.data.objects["FP"]]
    K.render_sheet(os.path.abspath(a.out), [int(x) for x in a.frames.split(",")], cams, (w, h), a.samples)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
