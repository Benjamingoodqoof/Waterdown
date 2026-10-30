#!/usr/bin/env python3
"""Preview renders of the Receiver (Cycles, CPU), using the poster monster's studio setup.

Looks: studio (neutral, with the wet puddle he leaves) or closet (dark, standing in a closet
doorway, lit by a weak bulb; --alarm turns the floor-4 alarm on: red light, his finger holes
and the pinprick in his socket glowing red).

Usage: python3 receiver_render.py BLEND OUT_DIR [--look studio|closet] [--alarm]
                                  [--views front,three,back,head,dial,low] [--samples 48] [--res 900x1200]
"""
import argparse
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import render  # noqa: E402

VIEWS = {
    "front": (None, (0.0, 0.0, 1.22), (0.0, -5.8, 0.1), 50),
    "three": (None, (0.0, 0.0, 1.22), (-3.2, -4.6, 0.35), 50),
    "back": (None, (0.0, 0.0, 1.22), (2.1, 5.2, 0.3), 50),
    "side": (None, (0.0, 0.0, 1.22), (-5.8, -0.4, 0.1), 50),
    "head": (None, (0.0, -0.3, 2.12), (-0.55, -1.2, 0.1), 60),
    "dial": (None, (0.0, -0.2, 1.68), (-0.35, -1.0, 0.0), 60),
    "low": (None, (0.0, 0.0, 1.5), (-1.3, -3.0, -1.1), 28),
    "hand": (None, (0.4, -0.08, 0.9), (0.5, -1.1, 0.15), 55),
}


def closet(alarm):
    """A dark closet: back wall and side walls close round him, a doorway, one weak bulb."""
    sc = bpy.context.scene
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.004, 0.004, 0.005, 1)
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT":
            bpy.data.objects.remove(ob)
    wall = render.mat("M_Wall", (0.05, 0.048, 0.045), 0.8)
    render.add_mesh("Back", [(-1.3, 0.75, 0), (1.3, 0.75, 0), (1.3, 0.75, 3.2), (-1.3, 0.75, 3.2)], [(0, 1, 2, 3)], wall)
    for x in (-1.0, 1.0):  # shallow side walls, so the camera sees in
        render.add_mesh(f"Side{x}", [(x, 0.75, 0), (x, 0.1, 0), (x, 0.1, 3.2), (x, 0.75, 3.2)], [(0, 1, 2, 3)], wall)
    render.add_mesh("Rail", [(-1.0, 0.5, 2.55), (1.0, 0.5, 2.55), (1.0, 0.52, 2.57), (-1.0, 0.52, 2.57)], [(0, 1, 2, 3)],
                    render.mat("M_Rail", (0.5, 0.5, 0.52), 0.3))
    if alarm:
        render.add_light("SPOT", (0.0, -2.6, 3.0), 260, (1.0, 0.12, 0.07), 0.3, (0, 0, 1.5))
        render.add_light("POINT", (0.3, 0.2, 2.8), 12, (1.0, 0.2, 0.1), 0.1)
        render.add_light("AREA", (-2.4, -1.0, 1.2), 30, (0.5, 0.6, 0.9), 1.0, (0, 0, 1.3))
    else:
        render.add_light("POINT", (0.2, -0.3, 2.95), 45, (1.0, 0.82, 0.6), 0.08)
        render.add_light("AREA", (-2.2, -3.0, 2.2), 70, (0.55, 0.65, 0.9), 2.0, (0, 0, 1.4))
        render.add_light("AREA", (0.0, 0.6, 2.8), 25, (0.6, 0.7, 0.9), 1.0, (0, 0, 1.6))


def set_alarm():
    """The floor-4 alarm: his shell glows red, and his finger holes and the pinprick in his socket burn."""
    glass = bpy.data.materials.get("M_Glass")
    if glass:
        b = next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Emission Color"].default_value = (1.0, 0.02, 0.01, 1)
        b.inputs["Emission Strength"].default_value = 0.25
    for name in ("M_DialGlow", "M_SocketLight"):
        m = bpy.data.materials.get(name)
        if not m:
            continue
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (1.0, 0.05, 0.03, 1)
        b.inputs["Emission Color"].default_value = (1.0, 0.05, 0.03, 1)
        b.inputs["Emission Strength"].default_value = 12.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--look", default="studio")
    ap.add_argument("--alarm", action="store_true")
    ap.add_argument("--views", default="front,three,back")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="900x1200")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["Receiver_Rig"]
    w, h = (int(x) for x in a.res.split("x"))
    render.setup("studio", a.samples, (w, h))
    bpy.context.scene.cycles.max_bounces = 10
    bpy.context.scene.cycles.transmission_bounces = 8
    if a.look == "closet":
        closet(a.alarm)
    if a.alarm:
        set_alarm()
    render.VIEWS.update(VIEWS)
    name = f"{a.prefix}{a.look}{'_alarm' if a.alarm else ''}"
    for view in a.views.split(","):
        bpy.context.scene.camera = render.camera(f"Cam_{view}", view, rig)
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{name}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", bpy.context.scene.render.filepath)
    if {"front", "three", "back"} <= set(a.views.split(",")):
        from PIL import Image
        tiles = [Image.open(os.path.join(a.out, f"{name}_{v}.png")).convert("RGB") for v in ("front", "three", "back")]
        sheet = Image.new("RGB", (tiles[0].width * 3, tiles[0].height))
        for i, t in enumerate(tiles):
            sheet.paste(t, (tiles[0].width * i, 0))
        sheet.save(os.path.join(a.out, f"{name}_turnaround.png"))


if __name__ == "__main__":
    main()
