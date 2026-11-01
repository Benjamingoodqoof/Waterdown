#!/usr/bin/env python3
"""Preview renders of the Stand-In (Cycles, CPU), using the poster monster's studio setup.

Looks: studio (neutral) or hall (a dark Orange Court corridor lit mostly by his screen).

Usage: python3 standin_render.py BLEND OUT_DIR [--look studio|hall]
                                 [--views front,three,back,side,head] [--samples 48] [--res 900x1200]
"""
import argparse
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import render  # noqa: E402

VIEWS = {
    "front": (None, (0.0, 0.0, 1.34), (0.0, -6.4, 0.1), 50),
    "three": (None, (0.0, 0.0, 1.34), (-3.5, -5.1, 0.35), 50),
    "back": (None, (0.0, 0.0, 1.34), (2.3, 5.7, 0.3), 50),
    "side": (None, (0.0, 0.0, 1.34), (-6.4, -0.3, 0.1), 50),
    "head": (None, (0.0, -0.05, 2.38), (-0.75, -1.45, 0.08), 55),
    "hand": (None, (-0.27, -0.05, 1.05), (-0.6, -1.0, 0.1), 55),
    "hallway": (None, (0.0, 0.0, 1.45), (-0.95, -4.6, 0.15), 40),  # inside the corridor
}


def hall():
    """A dark corridor: brown carpet, wood-panelled walls, and almost no light but his screen."""
    sc = bpy.context.scene
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.004, 0.003, 0.002, 1)
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT" or ob.name in ("Floor", "Puddle"):
            bpy.data.objects.remove(ob)
    carpet = render.mat("M_Carpet", (0.05, 0.022, 0.01), 0.95)
    render.add_mesh("Floor", [(-6, -8, 0), (6, -8, 0), (6, 8, 0), (-6, 8, 0)], [(0, 1, 2, 3)], carpet)
    wall = render.mat("M_Panels", (0.12, 0.05, 0.02), 0.6)
    for x in (-1.4, 1.4):
        render.add_mesh(f"Wall{x}", [(x, -8, 0), (x, 8, 0), (x, 8, 3.2), (x, -8, 3.2)], [(0, 1, 2, 3)], wall)
    render.add_mesh("End", [(-1.4, 4.0, 0), (1.4, 4.0, 0), (1.4, 4.0, 3.2), (-1.4, 4.0, 3.2)], [(0, 1, 2, 3)], wall)
    render.add_light("AREA", (0.0, -0.75, 2.5), 60, (1.0, 0.62, 0.38), 0.35, (0, -3, 1.6))  # his screen's glow
    render.add_light("AREA", (1.0, -3.2, 3.1), 70, (1.0, 0.75, 0.5), 1.0, (0, 0, 1.2))
    render.add_light("POINT", (-1.0, 2.5, 2.8), 90, (1.0, 0.6, 0.3), 0.1)
    render.add_light("AREA", (0.5, 2.0, 2.6), 70, (0.6, 0.65, 0.9), 0.8, (0, 0, 1.6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--look", default="studio")
    ap.add_argument("--views", default="front,three,back")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="900x1200")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["StandIn_Rig"]
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    bpy.data.objects.remove(bpy.data.objects["Puddle"])
    try:  # keeps the sheet's saturated orange, where AgX would wash it out to peach
        bpy.context.scene.view_settings.view_transform = "Khronos PBR Neutral"
        bpy.context.scene.view_settings.look = "None"
        bpy.context.scene.view_settings.exposure = -0.9  # the studio lights are set for darker monsters
    except TypeError:
        bpy.context.scene.view_settings.look = "AgX - Punchy"
    if a.look == "hall":
        hall()
    render.VIEWS.update(VIEWS)
    for view in a.views.split(","):
        bpy.context.scene.camera = render.camera(f"Cam_{view}", view, rig)
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{a.look}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", bpy.context.scene.render.filepath)
    if {"front", "three", "back"} <= set(a.views.split(",")):
        from PIL import Image
        tiles = [Image.open(os.path.join(a.out, f"{a.look}_{v}.png")).convert("RGB") for v in ("front", "three", "back")]
        sheet = Image.new("RGB", (tiles[0].width * 3, tiles[0].height))
        for i, t in enumerate(tiles):
            sheet.paste(t, (tiles[0].width * i, 0))
        sheet.save(os.path.join(a.out, f"{a.look}_turnaround.png"))


if __name__ == "__main__":
    main()
