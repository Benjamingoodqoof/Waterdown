#!/usr/bin/env python3
"""Preview renders of the Litter (Cycles, CPU), using the poster monster's studio setup.

Shots: the stack (front, three, back, side, head, hand), a litterling (close, top), and
"swarm": the stack in a dark hallway with litterlings pouring out of a vent, eyes glowing.

Usage: python3 litter_render.py LITTER_DIR OUT_DIR [--shots ...] [--samples 48] [--res 900x1200]
"""
import argparse
import math
import os
import random
import sys

import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import render  # noqa: E402

SHOTS = {  # blend, target, camera offset, lens
    "stack_front": ("stack", (0.0, 0.0, 1.32), (0.0, -6.6, 0.1), 50),
    "stack_three": ("stack", (0.0, 0.0, 1.32), (-3.6, -5.2, 0.4), 50),
    "stack_back": ("stack", (0.0, 0.0, 1.32), (2.4, 5.8, 0.3), 50),
    "stack_side": ("stack", (0.0, 0.0, 1.32), (-6.6, -0.3, 0.1), 50),
    "stack_head": ("stack", (0.0, -0.1, 2.25), (-0.8, -1.6, 0.1), 55),
    "stack_hand": ("stack", (0.6, -0.15, 1.0), (0.7, -1.2, 0.15), 55),
    "litterling_close": ("litterling", (0.0, -0.02, 0.24), (-0.55, -0.95, 0.12), 55),
    "litterling_face": ("litterling", (0.0, -0.17, 0.25), (-0.12, -0.42, 0.03), 60),
    "litterling_side": ("litterling", (0.0, 0.0, 0.22), (-1.25, -0.35, 0.3), 50),
    "swarm": ("stack", (0.2, 0.0, 1.0), (-1.9, -5.4, 0.25), 38),
}


def look(dark):
    sc = bpy.context.scene
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    if dark:
        bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
        bg.inputs["Color"].default_value = (0.004, 0.004, 0.005, 1)
        for ob in list(bpy.data.objects):
            if ob.type == "LIGHT" or ob.name in ("Floor", "Puddle"):
                bpy.data.objects.remove(ob)


def eyes_glow(strength):
    m = bpy.data.materials.get("M_Eyeshine")
    if m:
        b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Emission Strength"].default_value = strength


def swarm_scene(litter_dir):
    """A dark hotel hallway: a vent low in the wall, litterlings spilling out of it and
    scuttling toward the stack."""
    look(True)
    carpet = render.mat("M_Carpet", (0.035, 0.03, 0.04), 0.95)
    render.add_mesh("Floor", [(-6, -9, 0), (6, -9, 0), (6, 9, 0), (-6, 9, 0)], [(0, 1, 2, 3)], carpet)
    wall = render.mat("M_Wall", (0.16, 0.17, 0.2), 0.7)
    render.add_mesh("WallL", [(-1.8, -9, 0), (-1.8, 9, 0), (-1.8, 9, 3.4), (-1.8, -9, 3.4)], [(0, 1, 2, 3)], wall)
    render.add_mesh("WallR", [(2.0, -9, 0), (2.0, 9, 0), (2.0, 9, 3.4), (2.0, -9, 3.4)], [(0, 1, 2, 3)], wall)
    render.add_mesh("End", [(-1.8, 3.5, 0), (2.0, 3.5, 0), (2.0, 3.5, 3.4), (-1.8, 3.5, 3.4)], [(0, 1, 2, 3)], wall)
    grille = render.mat("M_Grille", (0.5, 0.5, 0.52), 0.35)
    render.add_mesh("VentHole", [(-1.79, -2.2, 0.15), (-1.79, -1.5, 0.15), (-1.79, -1.5, 0.6), (-1.79, -2.2, 0.6)],
                    [(0, 1, 2, 3)], render.mat("M_Hole", (0.0, 0.0, 0.0), 1.0))
    grille_ob = render.add_mesh("Grille", [(0, 0, 0), (0.7, 0, 0), (0.7, 0, 0.42), (0, 0, 0.42)], [(0, 1, 2, 3)], grille)
    grille_ob.location = (-1.5, -2.35, 0.005)
    grille_ob.rotation_euler = (math.radians(-90), 0, math.radians(15))  # knocked off, lying on the floor
    with bpy.data.libraries.load(os.path.join(litter_dir, "litterling.blend")) as (src, dst):
        dst.objects = list(src.objects)
    proto = [o for o in dst.objects if o is not None]
    rng = random.Random(9)
    spots = [(-1.6, -1.85, 0.0, 70), (-1.25, -1.6, 0.0, 40), (-1.3, -2.25, 0.0, 95), (-0.85, -1.4, 0.0, 20),
             (-0.55, -1.9, 0.0, 10), (-0.95, -2.5, 0.0, 60), (-0.25, -1.3, 0.0, -10), (-1.72, -1.95, 0.32, 85)]
    for k, (x, y, z, yaw) in enumerate(spots):
        root = bpy.data.objects.new(f"Swarm{k}", None)
        bpy.context.scene.collection.objects.link(root)
        root.location = (x, y, z)
        root.rotation_euler = Euler((0, 0, math.radians(yaw + rng.uniform(-15, 15))))
        s = rng.uniform(0.85, 1.05)
        root.scale = (s, s, s)
        for o in proto:
            c = o.copy()
            if o.type == "MESH":
                c.modifiers["Armature"].object = None
            c.parent = root
            bpy.context.scene.collection.objects.link(c)
    for o in proto:
        pass
    render.add_light("SPOT", (0.6, -3.6, 3.2), 260, (0.75, 0.8, 1.0), 0.15, (0.0, 0.0, 1.0))
    render.add_light("AREA", (1.2, 2.0, 3.0), 60, (0.6, 0.65, 0.9), 1.5, (0, 0, 1.2))
    render.add_light("POINT", (-1.5, -1.9, 0.5), 3, (0.9, 0.85, 1.0), 0.1)
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.data.type == "SPOT":
            ob.data.spot_size = math.radians(55)
            ob.data.spot_blend = 0.8
    eyes_glow(6.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("litter")
    ap.add_argument("out")
    ap.add_argument("--shots", default="stack_front,stack_three,stack_back")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="900x1200")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    w, h = (int(x) for x in a.res.split("x"))
    litter = os.path.abspath(a.litter)
    for shot in a.shots.split(","):
        blend, tgt, off, lens = SHOTS[shot]
        bpy.ops.wm.open_mainfile(filepath=os.path.join(litter, f"{blend}.blend"))
        render.setup("studio", a.samples, (w, h))
        if shot == "swarm":
            swarm_scene(litter)
        else:
            look(False)
            bpy.data.objects.remove(bpy.data.objects["Puddle"])
        render.VIEWS["shot"] = (None, tgt, off, lens)
        cam = render.camera("Cam", "shot", None)
        cam.data.clip_start = 0.01
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{shot}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", shot)
    shots = a.shots.split(",")
    if {"stack_front", "stack_three", "stack_back"} <= set(shots):
        from PIL import Image
        tiles = [Image.open(os.path.join(a.out, f"stack_{v}.png")).convert("RGB") for v in ("front", "three", "back")]
        sheet = Image.new("RGB", (tiles[0].width * 3, tiles[0].height))
        for i, t in enumerate(tiles):
            sheet.paste(t, (tiles[0].width * i, 0))
        sheet.save(os.path.join(a.out, "stack_turnaround.png"))


if __name__ == "__main__":
    main()
