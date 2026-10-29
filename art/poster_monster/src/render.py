#!/usr/bin/env python3
"""Preview renders of the poster monster (Cycles, CPU).

Usage: python3 render.py BLEND OUT_DIR [--look studio|atrium] [--pose idle|rest]
                         [--views front,three,head,back] [--samples 48] [--res 900x1200]
                         [--action NAME --frame N]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import posing  # noqa: E402

VIEWS = {
    # name: (bone to aim at or None, target offset, camera offset from the target, focal length mm)
    "front": (None, (0.0, 0.0, 1.36), (0.0, -6.0, 0.08), 50),
    "three": (None, (0.0, 0.0, 1.36), (-3.3, -4.7, 0.3), 50),
    "back": (None, (0.0, 0.0, 1.36), (2.2, 5.4, 0.25), 50),
    "head": ("Head", (0.0, -0.05, 0.0), (-0.7, -1.25, 0.06), 70),
    "low": (None, (0.0, 0.0, 1.75), (-1.2, -3.3, -1.2), 28),
    "hand": ("LeftHand", (0.0, -0.04, -0.12), (0.75, -1.05, 0.25), 60),
    "chest": ("Spine", (0.08, -0.12, 0.05), (0.55, -1.25, 0.12), 60),
}


def mat(name, color, rough, emit=None, strength=0.0, coat=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def tile_floor_material(look):
    m = bpy.data.materials.new("M_Floor")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if look == "studio":
        b.inputs["Base Color"].default_value = (0.16, 0.16, 0.17, 1)
        b.inputs["Roughness"].default_value = 0.55
        return m
    checker = nt.nodes.new("ShaderNodeTexChecker")
    checker.inputs["Scale"].default_value = 8.0
    c1, c2 = ((0.80, 0.86, 0.92, 1), (0.66, 0.76, 0.86, 1))
    checker.inputs["Color1"].default_value = c1
    checker.inputs["Color2"].default_value = c2
    nt.links.new(checker.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["Coat Weight"].default_value = 0.5
    return m


def add_mesh(name, verts, faces, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def add_light(kind, loc, energy, color=(1, 1, 1), size=1.0, target=(0, 0, 1.4)):
    ld = bpy.data.lights.new(f"L_{kind}_{len(bpy.data.lights)}", kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = size
    ob = bpy.data.objects.new(ld.name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def setup(look, samples, res):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast" if look != "atrium" else "AgX - Base Contrast"
    except TypeError:
        pass

    world = bpy.data.worlds.new("World")
    sc.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    sky = {"studio": ((0.05, 0.055, 0.06), 1.0), "atrium": ((0.40, 0.66, 1.0), 1.1)}[look]
    bg.inputs["Color"].default_value = (*sky[0], 1)
    bg.inputs["Strength"].default_value = sky[1]

    floor = add_mesh("Floor", [(-12, -12, 0), (12, -12, 0), (12, 12, 0), (-12, 12, 0)], [(0, 1, 2, 3)],
                     tile_floor_material(look))
    floor.data.uv_layers.new()
    # a wet puddle the monster is standing in
    import random
    rnd = random.Random(5)
    pts = []
    for i in range(48):
        a = 2 * math.pi * i / 48
        r = 0.75 + 0.18 * math.sin(a * 3 + 1) + 0.08 * math.sin(a * 7) + rnd.uniform(-0.03, 0.03)
        pts.append((math.cos(a) * r * 1.15, math.sin(a) * r * 0.9 - 0.05, 0.0015))
    add_mesh("Puddle", [(0, -0.05, 0.0015)] + pts, [(0, i + 1, (i + 1) % 48 + 1) for i in range(48)],
             mat("M_Puddle", (0.012, 0.014, 0.016), 0.03, coat=1.0))

    if look == "studio":
        add_light("AREA", (-3.0, -3.6, 4.0), 900, (1.0, 0.97, 0.92), 2.5)
        add_light("AREA", (3.5, -2.5, 2.0), 260, (0.75, 0.85, 1.0), 3.0)
        add_light("AREA", (1.5, 4.0, 3.8), 700, (0.9, 0.95, 1.0), 1.5)
    else:  # atrium
        sun = bpy.data.lights.new("Sun", "SUN")
        sun.energy = 3.6
        sun.angle = math.radians(2.0)
        so = bpy.data.objects.new("Sun", sun)
        sc.collection.objects.link(so)
        so.rotation_euler = (math.radians(38), 0, math.radians(-35))
        add_light("AREA", (0, -5, 3.5), 500, (0.9, 0.95, 1.0), 6.0)
        # glass wall behind
        add_mesh("Backdrop", [(-12, 6, 0), (12, 6, 0), (12, 6, 8), (-12, 6, 8)], [(0, 1, 2, 3)],
                 mat("M_Glass", (0.7, 0.85, 1.0), 0.05, emit=(0.55, 0.78, 1.0), strength=0.9))


def camera(name, view, rig):
    bone, toff, coff, lens = VIEWS[view]
    tgt = Vector(toff)
    if bone:
        bpy.context.view_layer.update()
        pb = rig.pose.bones[bone]
        tgt = rig.matrix_world @ ((pb.head + pb.tail) / 2) + Vector(toff)
    pos = tgt + Vector(coff)
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = pos
    ob.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
    return ob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--look", default="studio")
    ap.add_argument("--pose", default="idle")
    ap.add_argument("--views", default="front,three,head,back")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="900x1200")
    ap.add_argument("--action", default=None)
    ap.add_argument("--frame", type=int, default=1)
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["PosterMonster_Rig"]
    if a.action:
        rig.animation_data_create()
        rig.animation_data.action = bpy.data.actions[a.action]
        bpy.context.scene.frame_set(a.frame)
    elif a.pose == "idle":
        posing.apply_pose(rig, posing.IDLE)
    w, h = (int(x) for x in a.res.split("x"))
    setup(a.look, a.samples, (w, h))
    for view in a.views.split(","):
        cam = camera(f"Cam_{view}", view, rig)
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{a.prefix}{a.look}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", bpy.context.scene.render.filepath)


if __name__ == "__main__":
    main()
