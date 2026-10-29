#!/usr/bin/env python3
"""Preview renders of the Stand-in (Cycles, CPU), using the poster monster's studio setup.

Looks: studio (neutral) or dorfic (a dim, warm Orange Court room).
Poses: rest (as rigged) or mimic (head cocked, waving like a friendly player).

Usage: python3 standin_render.py BLEND OUT_DIR [--look studio|dorfic] [--pose rest|mimic]
                                 [--views front,three,back,head,badge] [--samples 48] [--res 900x1200]
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "poster_monster", "src")))
import render  # noqa: E402

VIEWS = {
    "front": (None, (0.0, 0.0, 1.27), (0.0, -5.6, 0.08), 50),
    "three": (None, (0.0, 0.0, 1.27), (-3.1, -4.4, 0.3), 50),
    "back": (None, (0.0, 0.0, 1.27), (2.1, 5.0, 0.25), 50),
    "head": (None, (0.0, 0.0, 2.3), (-0.55, -1.15, 0.05), 60),
    "badge": (None, (0.05, -0.12, 2.0), (-0.14, -0.5, 0.04), 60),
}

# mimic: what she does when she pretends to be your friend (rotations in degrees, armature axes)
MIMIC = {
    "Head": [("y", 26), ("x", 8)],
    "UpperTorso": [("y", -3)],
    "RightUpperArm": [("y", 95), ("x", -12)],
    "RightLowerArm": [("y", 70), ("x", -10)],
    "RightHand": [("y", 12)],
    "LeftUpperArm": [("y", -4)],
    "LeftUpperLeg": [("x", 4)],
    "RightUpperLeg": [("x", -6)],
}


def apply(rig, pose):
    ax = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        q = Quaternion()
        rinv = pb.bone.matrix_local.to_3x3().inverted()
        for a, deg in pose.get(pb.name, []):
            q = Quaternion((rinv @ ax[a]).normalized(), math.radians(deg)) @ q
        pb.rotation_quaternion = q


def setup(samples, res):
    """The poster monster's studio, with punchier color and without its puddle."""
    render.setup("studio", samples, res)
    bpy.context.scene.view_settings.look = "AgX - Punchy"
    if "Puddle" in bpy.data.objects:  # the poster monster drips; she doesn't
        bpy.data.objects.remove(bpy.data.objects["Puddle"])


def dorfic_room():
    """A dim, warm room: brown tile floor, wood-panel wall with the Orange Court sign."""
    sc = bpy.context.scene
    world = sc.world
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.03, 0.012, 0.004, 1)
    bg.inputs["Strength"].default_value = 1.0
    for ob in list(bpy.data.objects):
        if ob.type == "LIGHT" or ob.name == "Floor":
            bpy.data.objects.remove(ob)
    floor_m = render.mat("M_Tiles", (0.16, 0.07, 0.03), 0.25, coat=0.4)
    nt = floor_m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    ch = nt.nodes.new("ShaderNodeTexChecker")
    ch.inputs["Scale"].default_value = 12
    ch.inputs["Color1"].default_value = (0.09, 0.04, 0.018, 1)
    ch.inputs["Color2"].default_value = (0.045, 0.02, 0.01, 1)
    nt.links.new(ch.outputs["Color"], b.inputs["Base Color"])
    floor = render.add_mesh("Floor", [(-8, -8, 0), (8, -8, 0), (8, 8, 0), (-8, 8, 0)], [(0, 1, 2, 3)], floor_m)
    floor.data.uv_layers.new()
    wall_m = render.mat("M_Panels", (0.25, 0.1, 0.04), 0.5)
    nt = wall_m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3.5
    wave.inputs["Distortion"].default_value = 2.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.05, 0.02, 0.008, 1)
    ramp.color_ramp.elements[1].color = (0.14, 0.06, 0.025, 1)
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    render.add_mesh("Wall", [(-8, 2.4, 0), (8, 2.4, 0), (8, 2.4, 6), (-8, 2.4, 6)], [(0, 1, 2, 3)], wall_m)
    sign_m = render.mat("M_Sign", (0.9, 0.45, 0.15), 0.3)
    nt = sign_m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(HERE, "..", "textures", "orange_court_logo.png"))
    nt.links.new(img.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(img.outputs["Alpha"], b.inputs["Alpha"])
    b.inputs["Emission Strength"].default_value = 1.6
    sign = render.add_mesh("Sign", [(-0.7, 2.39, 2.3), (0.7, 2.39, 2.3), (0.7, 2.39, 3.7), (-0.7, 2.39, 3.7)],
                           [(0, 1, 2, 3)], sign_m)
    sign.data.uv_layers.new()
    uv = sign.data.uv_layers[0].data
    for li, c in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv[li].uv = c
    sign.location.x = 1.1
    render.add_light("SPOT", (-1.2, -2.2, 3.6), 600, (1.0, 0.72, 0.45), 0.2, (0, 0, 1.6))
    render.add_light("AREA", (2.4, -0.6, 1.4), 40, (1.0, 0.45, 0.2), 2.0, (0, 0, 1.2))
    render.add_light("POINT", (1.1, 2.0, 3.0), 60, (1.0, 0.5, 0.15), 0.4, (0, 0, 1.0))
    render.add_light("AREA", (0.4, 2.2, 3.4), 140, (0.95, 0.75, 0.6), 1.2, (0, 0, 1.6))
    for ob in bpy.data.objects:
        if ob.type == "LIGHT" and ob.data.type == "SPOT":
            ob.data.spot_size = math.radians(38)
            ob.data.spot_blend = 0.6


def turnaround(out, name):
    """Puts the front, three-quarter and back renders side by side."""
    from PIL import Image
    tiles = [Image.open(os.path.join(out, f"{name}_{v}.png")) for v in ("front", "three", "back")]
    w, h = tiles[0].size
    sheet = Image.new("RGB", (w * 3, h))
    for i, t in enumerate(tiles):
        sheet.paste(t.convert("RGB"), (w * i, 0))
    sheet.save(os.path.join(out, f"{name}_turnaround.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend")
    ap.add_argument("out")
    ap.add_argument("--look", default="studio")
    ap.add_argument("--pose", default="rest")
    ap.add_argument("--views", default="front,three,back")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--res", default="900x1200")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(a.blend))
    rig = bpy.data.objects["StandIn_Rig"]
    if a.pose == "mimic":
        apply(rig, MIMIC)
    w, h = (int(x) for x in a.res.split("x"))
    setup(a.samples, (w, h))
    if a.look == "dorfic":
        dorfic_room()
    render.VIEWS.update(VIEWS)
    for view in a.views.split(","):
        bpy.context.scene.camera = render.camera(f"Cam_{view}", view, rig)
        bpy.context.scene.render.filepath = os.path.join(a.out, f"{a.prefix}{a.look}_{view}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", bpy.context.scene.render.filepath)
    if {"front", "three", "back"} <= set(a.views.split(",")):
        turnaround(a.out, f"{a.prefix}{a.look}")


if __name__ == "__main__":
    main()
