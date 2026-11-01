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

SHOTS = {  # blend, target, camera offset, lens[, bone the target follows]
    "stack_front": ("stack", (0.0, 0.0, 1.32), (0.0, -6.6, 0.1), 50),
    "stack_three": ("stack", (0.0, 0.0, 1.32), (-3.6, -5.2, 0.4), 50),
    "stack_back": ("stack", (0.0, 0.0, 1.32), (2.4, 5.8, 0.3), 50),
    "stack_side": ("stack", (0.0, 0.0, 1.32), (-6.6, -0.3, 0.1), 50),
    "stack_head": ("stack", (0.0, 0.0, 0.08), (-0.8, -1.6, 0.05), 55, "Slot_Head1"),
    "stack_hand": ("stack", (0.0, 0.0, -0.12), (0.75, -1.25, 0.2), 55, "Slot_LeftArm5"),
    "litterling_close": ("litterling", (0.0, -0.02, 0.24), (-0.55, -0.95, 0.12), 55),
    "litterling_face": ("litterling", (0.0, -0.17, 0.25), (-0.12, -0.42, 0.03), 60),
    "litterling_side": ("litterling", (0.0, 0.0, 0.22), (-1.25, -0.35, 0.3), 50),
    "swarm": ("stack", (-0.35, -0.6, 0.85), (1.15, -5.0, 0.15), 30),
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
    """A dark hallway: the stack lumbering out of the gloom further down, and litterlings
    spilling out of a vent low in the left wall and scuttling toward it, eyes glinting."""
    look(True)
    rig = bpy.data.objects["Stack_Rig"]
    rig.location = (0.35, 1.2, 0.0)
    rig.rotation_euler = (0, 0, math.radians(-12))
    if rig.animation_data and "Walk" in bpy.data.actions:
        rig.animation_data.action = bpy.data.actions["Walk"]
        bpy.context.scene.frame_set(7)
    carpet = render.mat("M_Carpet", (0.03, 0.026, 0.034), 0.95)
    render.add_mesh("Floor", [(-6, -9, 0), (6, -9, 0), (6, 9, 0), (-6, 9, 0)], [(0, 1, 2, 3)], carpet)
    wall = render.mat("M_Wall", (0.06, 0.065, 0.08), 0.75)
    render.add_mesh("WallL", [(-1.8, -9, 0), (-1.8, 9, 0), (-1.8, 9, 3.4), (-1.8, -9, 3.4)], [(0, 1, 2, 3)], wall)
    render.add_mesh("WallR", [(2.0, -9, 0), (2.0, 9, 0), (2.0, 9, 3.4), (2.0, -9, 3.4)], [(0, 1, 2, 3)], wall)
    render.add_mesh("Ceiling", [(-1.8, -9, 3.4), (2.0, -9, 3.4), (2.0, 9, 3.4), (-1.8, 9, 3.4)], [(0, 1, 2, 3)], wall)
    render.add_mesh("End", [(-1.8, 6.5, 0), (2.0, 6.5, 0), (2.0, 6.5, 3.4), (-1.8, 6.5, 3.4)], [(0, 1, 2, 3)], wall)
    vy0, vy1 = -2.9, -2.1  # the vent in the left wall, its grille knocked off onto the floor
    render.add_mesh("VentHole", [(-1.79, vy0, 0.12), (-1.79, vy1, 0.12), (-1.79, vy1, 0.6), (-1.79, vy0, 0.6)],
                    [(0, 1, 2, 3)], render.mat("M_Hole", (0.0, 0.0, 0.0), 1.0))
    grille = render.mat("M_Grille", (0.12, 0.12, 0.13), 0.45)
    g = render.add_mesh("Grille", [(0, 0, 0), (0.8, 0, 0), (0.8, 0, 0.48), (0, 0, 0.48)], [(0, 1, 2, 3)], grille)
    g.location = (-1.45, -3.3, 0.005)
    g.rotation_euler = (math.radians(-90), 0, math.radians(20))
    with bpy.data.libraries.load(os.path.join(litter_dir, "litterling.blend")) as (src, dst):
        dst.objects = list(src.objects)
    proto = [o for o in dst.objects if o is not None]
    rng = random.Random(9)
    start, end = Vector((-1.55, (vy0 + vy1) / 2, 0.0)), Vector((0.1, 0.4, 0.0))
    spots = []
    d = (end - start).normalized()
    side = Vector((-d.y, d.x, 0))
    for k in range(16):  # a loose stream from the vent to the stack's feet, spreading as it goes
        t = (k + rng.uniform(-0.4, 0.4)) / 15
        p = start.lerp(end, t) + side * rng.uniform(-0.75, 0.75) * (0.15 + t)
        z = 0.12 if k in (4, 9, 12) else 0.0  # a few scrambling over the others
        spots.append((p + Vector((0, 0, z)), math.degrees(math.atan2(d.x, -d.y)) + rng.uniform(-45, 45), z * 120))
    spots.append((Vector((-1.62, -2.35, 0.3)), 90, 0.0))  # one squeezing out of the vent
    for k, (p, yaw, roll) in enumerate(spots):
        root = bpy.data.objects.new(f"Swarm{k}", None)
        bpy.context.scene.collection.objects.link(root)
        root.location = p
        root.rotation_euler = Euler((math.radians(roll), 0, math.radians(yaw)))
        sc = rng.uniform(0.85, 1.05)
        root.scale = (sc, sc, sc)
        for o in proto:
            c = o.copy()
            if o.type == "MESH":
                c.modifiers["Armature"].object = None
            c.parent = root
            bpy.context.scene.collection.objects.link(c)
    # light: a cold rim from far down the hall behind the stack, a dim flickering ceiling panel
    # over the camera, and a faint glow from inside the vent
    render.add_light("AREA", (0.3, 5.5, 2.8), 700, (0.55, 0.65, 1.0), 1.5, (0.3, 1.2, 1.4))
    render.add_light("AREA", (-0.6, -3.2, 3.3), 14, (0.8, 0.85, 1.0), 0.8, (-0.8, -2.0, 0.0))
    render.add_light("SPOT", (1.4, -0.5, 3.3), 90, (0.7, 0.78, 1.0), 0.1, (0.2, 1.0, 1.4))
    render.add_light("POINT", (-1.9, -2.5, 0.35), 10, (0.95, 0.8, 0.6), 0.1)
    render.add_light("AREA", (0.1, 4.6, 3.2), 160, (0.6, 0.68, 0.9), 2.0, (0.1, 6.5, 0.8))  # the far wall, to stand out against
    render.add_light("SPOT", (1.3, -1.8, 3.3), 160, (0.75, 0.8, 1.0), 0.1, (0.35, 1.2, 1.6))  # a cold light catching the stack
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.data.type == "SPOT":
            ob.data.spot_size = math.radians(50)
            ob.data.spot_blend = 0.9
    eyes_glow(5.0)


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
        blend, tgt, off, lens, *bone = SHOTS[shot]
        bpy.ops.wm.open_mainfile(filepath=os.path.join(litter, f"{blend}.blend"))
        render.setup("studio", a.samples, (w, h))
        if shot == "swarm":
            swarm_scene(litter)
        else:
            look(False)
            bpy.data.objects.remove(bpy.data.objects["Puddle"])
            eyes_glow(0.15)  # in the studio the eyeshine is just a glint
        render.VIEWS["shot"] = (bone[0] if bone else None, tgt, off, lens)
        rig = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
        cam = render.camera("Cam", "shot", rig)
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
