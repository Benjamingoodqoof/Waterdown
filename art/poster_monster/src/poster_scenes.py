#!/usr/bin/env python3
"""Renders original Frutiger Aero poster art in Blender (glass towers, grass, soap bubbles,
tropical fish, a glossy globe) and lays the slogans over it.

The textures script picks these up from textures/poster_art/ in place of its drawn posters.

Usage: python3 poster_scenes.py OUT_DIR [--only NAME] [--samples 64] [--percent 100]
"""
import argparse
import math
import os
import random

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Vector, noise
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONT_DIR = "/usr/share/fonts/opentype/inter/"
W, H = 808, 1120  # two times a poster cell of the atlas


# ---------------------------------------------------------------- scene helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    return sc


def node_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    return m, m.node_tree, next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_obj(name, verts, faces, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def uv_sphere(name, loc, r, mat, scale=(1, 1, 1), seg=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=rings)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def sky(sun_elev=38, sun_rot=200, strength=0.35):
    world = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    # a saturated Frutiger Aero sky: deep blue overhead fading to pale cyan at the horizon
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.55, 0.85, 1.0, 1)
    cr.elements[1].position, cr.elements[1].color = 0.55, (0.0, 0.12, 0.62, 1)
    e = cr.elements.new(0.18)
    e.color = (0.12, 0.5, 0.98, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 3.0
    sun.angle = math.radians(1.5)
    so = link(bpy.data.objects.new("Sun", sun))
    so.rotation_euler = (math.radians(90 - sun_elev), 0, math.radians(sun_rot + 90))


def camera(loc, target, lens=24):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    ob = link(bpy.data.objects.new("Cam", cd))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def cloud(loc, size, seed, facing):
    """A soft billboard cloud: a plane whose alpha is cut from noise."""
    m, nt, b = node_mat(f"Cloud{seed}")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["W"].default_value = seed
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 8
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.12
    ramp.color_ramp.elements[1].position = 0.32
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], grad.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], mul.inputs[0])
    nt.links.new(grad.outputs["Fac"], mul.inputs[1])
    nt.links.new(mul.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Alpha"])
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Roughness"].default_value = 1.0
    b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    b.inputs["Emission Strength"].default_value = 0.6
    ob = mesh_obj(f"Cloud{seed}", [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)], [(0, 1, 2, 3)], m)
    ob.location = loc
    ob.scale = (size, size, size * 0.55)
    ob.rotation_euler = (Vector(facing) - Vector(loc)).to_track_quat("-Y", "Z").to_euler()
    return ob


def glass_tower(name, x, y, w, d, h, tint, rot=0.0):
    """A glass skyscraper: reflective blue panes with pale mullions."""
    m, nt, b = node_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    grid = []
    for axis, period in (("X", 1.6), ("Y", 1.6), ("Z", 1.2)):
        mod = nt.nodes.new("ShaderNodeMath")
        mod.operation = "PINGPONG"
        mod.inputs[1].default_value = period / 2
        nt.links.new(sep.outputs[axis], mod.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = period * 0.018
        nt.links.new(mod.outputs["Value"], lt.inputs[0])
        grid.append(lt)
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(grid[0].outputs[0], mx.inputs[0])
    nt.links.new(grid[1].outputs[0], mx.inputs[1])
    mx2 = nt.nodes.new("ShaderNodeMath")
    mx2.operation = "MAXIMUM"
    nt.links.new(mx.outputs[0], mx2.inputs[0])
    nt.links.new(grid[2].outputs[0], mx2.inputs[1])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*tint, 1)
    mix.inputs["B"].default_value = (0.55, 0.62, 0.68, 1)
    nt.links.new(mx2.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rmix = nt.nodes.new("ShaderNodeMapRange")
    rmix.inputs["To Min"].default_value = 0.02
    rmix.inputs["To Max"].default_value = 0.35
    nt.links.new(mx2.outputs[0], rmix.inputs["Value"])
    nt.links.new(rmix.outputs["Result"], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = 0.55
    b.inputs["Coat Weight"].default_value = 0.8
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h / 2))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (w, d, h)
    ob.rotation_euler = (0, 0, rot)
    bpy.ops.object.transform_apply(scale=True)
    ob.data.materials.append(m)
    return ob


def hills(seed=1, height=2.4, size=160, near=0.0, flat=18.0, n=90):
    """Stylized Frutiger Aero hills: smooth glossy rolling green, flat near the camera."""
    m, nt, b = node_mat(f"Hills{seed}")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.03, 0.28, 0.02, 1)
    cr.elements[1].position, cr.elements[1].color = 1.0, (0.55, 0.9, 0.08, 1)
    e = cr.elements.new(0.45)
    e.color = (0.12, 0.6, 0.03, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.2
    mr.inputs["From Max"].default_value = height
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.32
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.15
    verts, faces = [], []
    for j in range(n + 1):
        y = near + size * (j / n) ** 1.6
        rise = min(1.0, max(0.0, (y - near) / flat))
        for i in range(n + 1):
            x = -size / 2 + size * i / n
            z = height * rise * (0.55 + 0.45 * noise.noise(Vector((x * 0.035, y * 0.035, seed))))
            z += 0.25 * rise * noise.noise(Vector((x * 0.12, y * 0.12, seed + 5)))
            verts.append((x, y, z))
    for j in range(n):
        for i in range(n):
            k = j * (n + 1) + i
            faces.append((k, k + 1, k + n + 2, k + n + 1))
    ob = mesh_obj(f"Hills{seed}", verts, faces, m)
    ob.data.shade_smooth()
    return ob


def glossy(name, color, rough=0.08, coat=1.0, transmission=0.0, emit=None, strength=0.0):
    m, nt, b = node_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = 0.03
    b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def droplet_mesh(name, loc, height, mat, m=1.1, width=0.74):
    """A teardrop, point up, built by pinching a sphere."""
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
    ob = bpy.context.active_object
    ob.name = name
    ts = [i / 1000 * math.pi for i in range(1, 1000)]
    k = max(math.sin(t) * math.sin(t / 2) ** m for t in ts)
    for v in ob.data.vertices:
        t = math.acos(max(-1.0, min(1.0, v.co.z)))
        f = (abs(math.sin(t / 2)) ** m) / k * width
        v.co.x *= f
        v.co.y *= f
    ob.scale = (height / 2,) * 3
    ob.location = loc
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def mascot(loc, height, rot_z=0.0, eyes="empty"):
    """The company's droplet mascot in glossy blue plastic. Its eyes are black voids."""
    body = droplet_mesh("Mascot", loc, height, glossy("MascotBlue", (0.05, 0.35, 0.95), rough=0.12))
    black = glossy("MascotBlack", (0.005, 0.005, 0.008), rough=0.2, coat=0.5)
    s = height / 2
    face_z = loc[2] - 0.38 * s
    parts = []
    for side in (-1, 1):
        e = uv_sphere("Eye", (loc[0] + side * 0.24 * s, loc[1] - 0.69 * s, face_z + 0.12 * s), 0.11 * s, black,
                      scale=(1.0, 0.45, 1.5), seg=24, rings=12)
        parts.append(e)
    # the grin: a thick curved tube
    cd = bpy.data.curves.new("Smile", "CURVE")
    cd.dimensions = "3D"
    cd.bevel_depth = 0.035 * s
    sp = cd.splines.new("POLY")
    pts = []
    for i in range(13):
        u = -1 + 2 * i / 12
        x = u * 0.36 * s
        z = face_z - 0.16 * s - 0.13 * s * (1 - u * u)
        yy = loc[1] - 0.73 * s * (1 - 0.3 * u * u)
        pts.append((loc[0] + x, yy, z))
    sp.points.add(len(pts) - 1)
    for pt, co in zip(sp.points, pts):
        pt.co = (*co, 1)
    smile = link(bpy.data.objects.new("Smile", cd))
    smile.data.materials.append(glossy("Grin", (0.5, 0.02, 0.05), rough=0.25))
    parts.append(smile)
    for p in parts:
        p.parent = body
        p.matrix_parent_inverse = body.matrix_world.inverted()
    body.rotation_euler = (0, 0, rot_z)
    return body


def orb(loc, r, color):
    """A glossy Frutiger orb, half see-through."""
    return uv_sphere("Orb", loc, r, glossy(f"Orb{len(bpy.data.materials)}", color, rough=0.03, transmission=0.45),
                     seg=48, rings=24)


def leaf(loc, length, rot, color=(0.15, 0.62, 0.05)):
    verts, faces = [], []
    n = 12
    for i in range(n + 1):
        t = i / n
        w = math.sin(math.pi * t) * 0.32 * length
        bend = 0.18 * length * math.sin(math.pi * t)
        verts += [(t * length, -w, bend), (t * length, w, bend), (t * length, 0, bend + 0.03 * length)]
    for i in range(n):
        a, b = 3 * i, 3 * (i + 1)
        faces += [(a, b, b + 2, a + 2), (a + 2, b + 2, b + 1, a + 1)]
    ob = mesh_obj("Leaf", verts, faces, glossy(f"Leaf{len(bpy.data.materials)}", color, rough=0.2, coat=0.8))
    ob.data.shade_smooth()
    ob.location = loc
    ob.rotation_euler = rot
    sol = ob.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.01 * length
    return ob


def crt(loc, size, rot_z=0.0):
    """A glossy old computer monitor whose screen shows a bright sky."""
    shell = glossy("CRTShell", (0.85, 0.88, 0.9), rough=0.25, coat=0.6)
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    body = bpy.context.active_object
    body.scale = (size, size * 0.9, size * 0.82)
    body.data.materials.append(shell)
    bev = body.modifiers.new("bevel", "BEVEL")
    bev.width = size * 0.06
    bev.segments = 4
    m, nt, b = node_mat("Screen")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.6, 0.9, 1.0, 1)
    ramp.color_ramp.elements[1].color = (0.0, 0.25, 0.9, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 2.5
    b.inputs["Base Color"].default_value = (0.02, 0.05, 0.1, 1)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Coat Weight"].default_value = 1.0
    sx, sz = size * 0.38, size * 0.31
    screen = mesh_obj("Screen", [(-sx, 0, -sz), (sx, 0, -sz), (sx, 0, sz), (-sx, 0, sz)], [(0, 1, 2, 3)], m)
    screen.location = (loc[0], loc[1] - size * 0.455, loc[2] + size * 0.03)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] - size * 0.5))
    stand = bpy.context.active_object
    stand.scale = (size * 0.5, size * 0.5, size * 0.12)
    stand.data.materials.append(shell)
    for ob in (screen, stand):
        ob.parent = body
        ob.matrix_parent_inverse = body.matrix_world.inverted()
    body.rotation_euler = (0, 0, rot_z)


def light_shaft(loc, length, width, tilt):
    m, nt, b = node_mat(f"Shaft{len(bpy.data.materials)}")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].color = (0.35, 0.35, 0.35, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Alpha"])
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Color"].default_value = (0.7, 0.95, 1.0, 1)
    b.inputs["Emission Strength"].default_value = 1.6
    ob = mesh_obj("Shaft", [(-width / 2, 0, 0), (width / 2, 0, 0), (width / 2, 0, length), (-width / 2, 0, length)],
                  [(0, 1, 2, 3)], m)
    ob.location = loc
    ob.rotation_euler = (0, tilt, 0)
    return ob


def sky_gradient(top, mid, bottom):
    """Override the sky colours (for underwater or sunset scenes)."""
    nt = bpy.context.scene.world.node_tree
    ramp = next(n for n in nt.nodes if n.type == "VALTORGB")
    cr = ramp.color_ramp
    cols = sorted(cr.elements, key=lambda e: e.position)
    cols[0].color, cols[1].color, cols[2].color = (*bottom, 1), (*mid, 1), (*top, 1)


def bubble(loc, r, thickness):
    m, nt, b = node_mat(f"Bubble{len(bpy.data.materials)}")
    b.inputs["Base Color"].default_value = (1, 1, 1, 1)
    b.inputs["Roughness"].default_value = 0.0
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.1
    b.inputs["Thin Film Thickness"].default_value = thickness
    b.inputs["Thin Film IOR"].default_value = 1.33
    return uv_sphere("Bubble", loc, r, m, seg=32, rings=16)


def fish(name, loc, length, heading, kind="clown"):
    """A stylized tropical fish: banded body, tail and fins, glossy wet skin."""
    m, nt, b = node_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    palettes = {
        # (position along the body from tail -1 to nose 1 mapped to 0..1, color)
        "clown": [(0.0, (0.02, 0.02, 0.02)), (0.04, (1.0, 0.28, 0.0)), (0.2, (0.02, 0.02, 0.02)), (0.215, (0.95, 0.95, 0.95)),
                  (0.3, (0.02, 0.02, 0.02)), (0.315, (1.0, 0.28, 0.0)), (0.47, (0.02, 0.02, 0.02)), (0.485, (0.95, 0.95, 0.95)),
                  (0.58, (0.02, 0.02, 0.02)), (0.595, (1.0, 0.3, 0.0)), (0.74, (0.02, 0.02, 0.02)), (0.755, (0.95, 0.95, 0.95)),
                  (0.83, (0.02, 0.02, 0.02)), (0.845, (1.0, 0.32, 0.0))],
        "tang": [(0.0, (1.0, 0.85, 0.0)), (0.25, (0.02, 0.12, 0.65)), (0.7, (0.01, 0.02, 0.08)), (0.8, (0.05, 0.25, 0.85))],
        "yellow": [(0.0, (1.0, 0.82, 0.02)), (0.9, (1.0, 0.74, 0.0))],
    }
    pal = palettes[kind]
    for el, (pos, col) in zip(cr.elements, pal[:2]):
        el.position, el.color = pos, (*col, 1)
    for pos, col in pal[2:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.6
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(sep.outputs["X"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.18
    b.inputs["Coat Weight"].default_value = 0.8
    b.inputs["Subsurface Weight"].default_value = 0.1
    # body: a sphere squashed into a fish shape, nose at +X
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=40, ring_count=20)
    body = bpy.context.active_object
    tall = 0.62 if kind != "tang" else 0.72
    for v in body.data.vertices:
        x, y, z = v.co
        taper = 1 - 0.55 * max(0.0, -x) ** 1.5
        v.co = Vector((x * 1.0, y * 0.28 * taper, z * tall * taper + 0.08 * (1 - x * x) * (z > 0)))
    # tail and fins as thin wedges
    tail = [(-0.9, 0, 0), (-1.55, 0, 0.55), (-1.4, 0, 0.0), (-1.55, 0, -0.55)]
    dors = [(-0.6, 0, 0.45), (0.3, 0, 0.62), (0.0, 0, 0.95 if kind == "tang" else 0.8), (-0.75, 0, 0.75)]
    belly = [(-0.5, 0, -0.42), (0.1, 0, -0.55), (-0.25, 0, -0.8)]
    fins = mesh_obj(name + "Fins", tail + dors + belly, [(0, 1, 2), (0, 2, 3), (4, 5, 6, 7), (8, 9, 10)])
    bpy.ops.object.select_all(action="DESELECT")
    for ob in (body, fins):
        ob.data.materials.append(m)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    bpy.ops.object.shade_smooth()
    body.name = name
    sol = body.modifiers.new("solid", "SOLIDIFY")
    sol.thickness = 0.03
    eye_m, _, eb = node_mat(name + "Eye")
    eb.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1)
    eb.inputs["Roughness"].default_value = 0.05
    eb.inputs["Coat Weight"].default_value = 1.0
    for s in (1, -1):
        e = uv_sphere(name + "Eye", (0.62, 0.22 * s, 0.12), 0.11, eye_m, seg=16, rings=8)
        e.parent = body
    body.scale = (length / 2.5,) * 3
    body.location = loc
    body.rotation_euler = (0, math.radians(heading[1]), math.radians(heading[0]))
    return body


def globe(loc, r):
    m, nt, b = node_mat("Globe")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.6
    noise.inputs["Detail"].default_value = 6
    noise.inputs["Roughness"].default_value = 0.6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.0, 0.12, 0.55, 1)
    cr.elements[1].position, cr.elements[1].color = 0.53, (0.02, 0.35, 0.85, 1)
    e = cr.elements.new(0.545)
    e.color = (0.25, 0.6, 0.12, 1)
    e = cr.elements.new(0.62)
    e.color = (0.12, 0.42, 0.06, 1)
    e = cr.elements.new(0.7)
    e.color = (0.55, 0.5, 0.25, 1)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.25
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.02
    g = uv_sphere("Globe", loc, r, m, seg=64, rings=32)
    # a thin glowing atmosphere
    am, _, ab = node_mat("Atmosphere")
    ab.inputs["Base Color"].default_value = (0.6, 0.85, 1.0, 1)
    ab.inputs["Transmission Weight"].default_value = 1.0
    ab.inputs["Roughness"].default_value = 0.0
    ab.inputs["IOR"].default_value = 1.0
    ab.inputs["Emission Color"].default_value = (0.5, 0.8, 1.0, 1)
    ab.inputs["Emission Strength"].default_value = 0.15
    uv_sphere("Atmosphere", loc, r * 1.04, am, seg=64, rings=32)
    return g


# ---------------------------------------------------------------- scenes
def base(samples, seed, sun_elev=40, clouds_n=10, cloud_y=60):
    sc = reset()
    sc.cycles.samples = samples
    rnd = random.Random(seed)
    sky(sun_elev=sun_elev, sun_rot=215)
    for i in range(clouds_n):
        cloud((rnd.uniform(-24, 24), cloud_y, rnd.uniform(8, 38)), rnd.uniform(6, 11), i + seed * 20, (0, 0, 1))
    return rnd


def bubbles(rnd, n, x, y, z, r=(0.06, 0.26)):
    for _ in range(n):
        bubble((rnd.uniform(*x), rnd.uniform(*y), rnd.uniform(*z)), rnd.uniform(*r), rnd.uniform(250, 750))


def scene_tomorrow(samples):
    """Glass towers from the hills, a globe in the sky, fish and bubbles in the air."""
    rnd = base(samples, 3)
    hills(seed=3, height=1.8, near=0.0, flat=10)
    towers = [(-3.5, 14, 2.2, 2.2, 26, (0.01, 0.07, 0.22)), (1.8, 18, 3.0, 2.5, 34, (0.01, 0.09, 0.26)),
              (6.5, 13, 2.4, 2.4, 22, (0.02, 0.08, 0.2)), (-8.0, 20, 3.2, 3.0, 30, (0.01, 0.06, 0.18)),
              (10.5, 22, 3.0, 3.0, 28, (0.01, 0.08, 0.24)), (-1.2, 26, 2.6, 2.6, 40, (0.01, 0.07, 0.2))]
    for i, (x, y, w, d, h, tint) in enumerate(towers):
        glass_tower(f"Tower{i}", x, y, w, d, h, tint, rot=math.radians(rnd.uniform(-12, 12)))
    globe((-2.6, 9.0, 7.6), 1.25)
    bubbles(rnd, 20, (-1.8, 2.2), (1.8, 5.5), (1.0, 4.2))
    fish("Clown", (0.9, 2.3, 1.6), 0.95, (-30, -8), "clown")
    fish("Clown2", (-0.55, 3.6, 2.9), 0.5, (25, 5), "clown")
    fish("Tang", (-1.25, 4.2, 3.6), 0.85, (15, 0), "tang")
    fish("Yellow", (1.5, 4.8, 3.6), 0.55, (160, 6), "yellow")
    camera((0.2, -0.6, 0.9), (0.3, 10, 7.0), lens=22)


def scene_pure(samples):
    """A giant glass water drop standing on the hills."""
    rnd = base(samples, 5)
    hills(seed=5, height=2.2, near=0.0, flat=14)
    water = glossy("Water", (0.75, 0.92, 1.0), rough=0.0, coat=0.0, transmission=1.0)
    nt = water.node_tree
    next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED").inputs["IOR"].default_value = 1.33
    droplet_mesh("Drop", (0.0, 7.0, 2.25), 4.2, water)
    bubbles(rnd, 14, (-1.0, 1.0), (6.4, 7.6), (0.8, 3.0), (0.04, 0.14))
    bubbles(rnd, 10, (-3.2, 3.2), (3.0, 6.0), (0.6, 4.5))
    camera((0.0, -1.5, 1.2), (0.0, 7.0, 2.6), lens=30)


def scene_tower(samples):
    """The building itself: a rounded glass tower above a koi pond."""
    rnd = base(samples, 7)
    hills(seed=7, height=2.0, near=0.0, flat=12)
    tower = glass_tower("Main", 0.0, 20.0, 6.0, 6.0, 34, (0.01, 0.1, 0.3))
    bev = tower.modifiers.new("round", "BEVEL")
    bev.width = 2.6
    bev.segments = 10
    for i, x in enumerate((-9.0, 9.5)):
        glass_tower(f"Wing{i}", x, 24.0, 5.0, 5.0, 18 + 4 * i, (0.01, 0.08, 0.24))
    pond = uv_sphere("Pond", (0.0, 7.0, 0.05), 3.2, glossy("PondWater", (0.0, 0.25, 0.6), rough=0.02),
                     scale=(1.4, 0.7, 0.01))
    for k in range(4):
        fish(f"Koi{k}", (rnd.uniform(-2.5, 2.5), rnd.uniform(6.0, 8.0), 0.12), 0.45, (rnd.uniform(0, 360), 0), "clown")
    bubbles(rnd, 12, (-4, 4), (4, 10), (1.0, 6.0), (0.1, 0.35))
    _ = pond
    camera((0.0, -3.0, 2.2), (0.0, 20.0, 14.0), lens=24)


def scene_flow(samples):
    """Underwater: light shafts, a school of fish and bubbles rising."""
    rnd = base(samples, 9, clouds_n=0)
    sky_gradient((0.55, 0.95, 1.0), (0.0, 0.45, 0.75), (0.0, 0.08, 0.22))
    for i in range(6):
        light_shaft((rnd.uniform(-6, 6), rnd.uniform(10, 18), -2), 24, rnd.uniform(0.8, 2.2), rnd.uniform(-0.35, 0.35))
    kinds = ("clown", "tang", "yellow")
    for k in range(14):
        fish(f"School{k}", (rnd.uniform(-3, 3), rnd.uniform(5, 12), rnd.uniform(-1.5, 3.5)), rnd.uniform(0.4, 0.9),
             (rnd.uniform(-40, 40) + (180 if k % 3 == 0 else 0), rnd.uniform(-10, 10)), kinds[k % 3])
    bubbles(rnd, 40, (-3, 3), (2, 9), (-2, 5), (0.04, 0.22))
    for k in range(5):
        orb((rnd.uniform(-2.5, 2.5), rnd.uniform(4, 8), rnd.uniform(-1, 4)), rnd.uniform(0.15, 0.35), (0.3, 0.85, 1.0))
    camera((0.0, -2.0, 1.0), (0.0, 10.0, 1.6), lens=26)


def scene_hydrated(samples):
    """A glass terrarium globe on the hills, a little tree growing inside."""
    rnd = base(samples, 11)
    hills(seed=11, height=2.0, near=0.0, flat=10)
    glass = glossy("Terrarium", (0.9, 0.97, 1.0), rough=0.0, coat=0.0, transmission=1.0)
    uv_sphere("Terrarium", (0.0, 4.2, 1.75), 1.75, glass, seg=64, rings=32)
    uv_sphere("Moss", (0.0, 4.2, 0.35), 1.45, glossy("Moss", (0.18, 0.62, 0.06), rough=0.3, coat=0.6),
              scale=(1.0, 1.0, 0.35))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=1.3, location=(0.0, 4.2, 1.15))
    bpy.context.active_object.data.materials.append(glossy("Trunk", (0.25, 0.13, 0.05), rough=0.4, coat=0.3))
    for dx, dz, r in ((0.0, 2.1, 0.62), (-0.42, 1.85, 0.45), (0.45, 1.9, 0.48)):
        uv_sphere("Canopy", (dx, 4.2, dz), r, glossy(f"Canopy{dx}", (0.2, 0.7, 0.08), rough=0.25, coat=0.7))
    bubbles(rnd, 20, (-3, 3), (1.6, 3.4), (0.4, 5.0), (0.06, 0.3))
    camera((0.0, -1.6, 1.6), (0.0, 4.2, 2.0), lens=32)


def scene_green(samples):
    """A glossy globe resting in the hills among big leaves."""
    rnd = base(samples, 13)
    hills(seed=13, height=2.3, near=0.0, flat=12)
    globe((0.0, 6.0, 1.9), 1.7)
    for k in range(7):
        a = 2 * math.pi * k / 7
        leaf((math.cos(a) * 1.3, 6.0 + math.sin(a) * 0.9, 0.7), rnd.uniform(1.6, 2.4),
             (rnd.uniform(-0.4, 0.2), -0.6, a), (rnd.uniform(0.1, 0.25), rnd.uniform(0.55, 0.7), 0.05))
    bubbles(rnd, 18, (-3, 3), (3, 7), (0.6, 5.0))
    camera((0.0, -1.2, 1.6), (0.0, 6.0, 2.2), lens=30)


def scene_funday(samples):
    """Glossy orbs drifting over the hills."""
    rnd = base(samples, 15)
    hills(seed=15, height=2.6, near=0.0, flat=12)
    cols = [(0.0, 0.6, 1.0), (0.2, 0.9, 0.3), (1.0, 0.75, 0.1), (0.95, 0.3, 0.55), (0.55, 0.3, 1.0)]
    for k in range(11):
        orb((rnd.uniform(-3.5, 3.5), rnd.uniform(4, 11), rnd.uniform(1.0, 6.0)), rnd.uniform(0.3, 0.9), cols[k % 5])
    bubbles(rnd, 14, (-3, 3), (2, 6), (0.6, 5))
    camera((0.0, -1.0, 1.4), (0.0, 8.0, 3.4), lens=26)


def scene_visitor(samples):
    """An old computer on the hills, fish swimming out of its sky-blue screen."""
    rnd = base(samples, 17)
    hills(seed=17, height=2.0, near=0.0, flat=8)
    crt((0.5, 4.0, 1.25), 1.9, rot_z=math.radians(-22))
    for k, kind in enumerate(("clown", "tang", "yellow", "clown")):
        fish(f"Out{k}", (-0.1 - 0.5 * k, 3.0 - 0.25 * k, 1.2 + 0.25 * k), 0.45 + 0.08 * k, (165 + 8 * k, 6), kind)
    bubbles(rnd, 18, (-2.5, 1.5), (2.0, 4.5), (0.8, 2.6))
    camera((0.0, -1.6, 1.5), (-0.2, 4.0, 1.9), lens=28)


def scene_smile(samples):
    """A rainbow arcing over the hills, bubbles drifting up into it."""
    rnd = base(samples, 19, sun_elev=55)
    hills(seed=19, height=2.4, near=0.0, flat=10)
    cols = [(1.0, 0.1, 0.1), (1.0, 0.5, 0.0), (1.0, 0.95, 0.1), (0.1, 0.9, 0.2), (0.1, 0.5, 1.0), (0.5, 0.2, 1.0)]
    for k, col in enumerate(cols):
        m, nt, b = node_mat(f"Bow{k}")
        b.inputs["Base Color"].default_value = (0, 0, 0, 1)
        b.inputs["Emission Color"].default_value = (*col, 1)
        b.inputs["Emission Strength"].default_value = 1.4
        b.inputs["Alpha"].default_value = 0.55
        bpy.ops.mesh.primitive_torus_add(major_radius=11.0 - 0.32 * k, minor_radius=0.16, major_segments=96,
                                         minor_segments=8, location=(0.0, 30.0, -2.0), rotation=(math.pi / 2, 0, 0))
        bpy.context.active_object.data.materials.append(m)
    bubbles(rnd, 26, (-3.5, 3.5), (4, 9), (1, 7), (0.08, 0.35))
    camera((0.0, -1.0, 1.3), (0.0, 20.0, 5.0), lens=26)


# atlas slot: (scene, title, where the title goes, small line)
SCENES = {
    "tomorrow": (scene_tomorrow, "Meet\nyour\npromised\nfuture", "bottom", "Your future has been reserved."),
    "pure": (scene_pure, "Pure.\nClean.\nPromised.", "top", "Every drop, for every tomorrow."),
    "tower": (scene_tower, "The future\nis clear", "top", "Now open. Come inside."),
    "flow": (scene_flow, "Dive into\ntomorrow", "bottom", "The future is fluid."),
    "hydrated": (scene_hydrated, "Stay happy.\nStay hydrated.", "bottom", "We are always here for you."),
    "green": (scene_green, "The whole\nworld,\npromised.", "top", "Growing greener together."),
    "funday": (scene_funday, "Your future\nstarts today", "bottom", "Family fun day. Everyone welcome."),
    "visitor": (scene_visitor, "Welcome to\nthe promised\nfuture", "top", "Please stay in the bright areas."),
    "smile": (scene_smile, "Smile.\nTomorrow\nis watching.", "bottom", "Thank you for staying."),
}


# ---------------------------------------------------------------- slogan overlay
def overlay(path, title, small, where="bottom"):
    img = ImageEnhance.Contrast(ImageEnhance.Color(Image.open(path).convert("RGB")).enhance(1.35)).enhance(1.08)
    img = img.convert("RGBA")
    w, h = img.size
    # sun glare in the corner, the Frutiger Aero signature
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    for r, a in ((0.55, 40), (0.32, 70), (0.14, 150)):
        d.ellipse([w * 0.85 - w * r, -w * r * 0.6, w * 0.85 + w * r, w * r * 1.4], fill=(255, 255, 240, a))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(w * 0.06)))
    lines = title.split("\n")
    size = int(h * 0.105)
    font = ImageFont.truetype(f"{FONT_DIR}InterDisplay-Bold.otf", size)
    widest = max(font.getlength(line) for line in lines)
    if widest > w * 0.9:  # long lines shrink to fit the sheet
        size = int(size * w * 0.9 / widest)
        font = ImageFont.truetype(f"{FONT_DIR}InterDisplay-Bold.otf", size)
    y0 = h - len(lines) * size * 0.98 - h * 0.045 if where == "bottom" else h * 0.075
    text = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(text)
    for i, line in enumerate(lines):
        td.text((w * 0.045, y0 + i * size * 0.98), line, font=font, fill=(255, 255, 255, 255))
    halo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    halo.putalpha(text.split()[3].filter(ImageFilter.GaussianBlur(size * 0.18)))
    halo = Image.merge("RGBA", (*Image.new("RGB", img.size, (60, 170, 255)).split(), halo.split()[3]))
    img.alpha_composite(halo)
    img.alpha_composite(halo)
    img.alpha_composite(text)
    small_font = ImageFont.truetype(f"{FONT_DIR}Inter-Medium.otf", int(h * 0.022))
    small_y = h * 0.03 if where == "bottom" else h * 0.95
    ImageDraw.Draw(img).text((w * 0.045, small_y), small, font=small_font, fill=(255, 255, 255, 235))
    return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only", default=None)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--percent", type=int, default=100)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, (build, title, where, small) in SCENES.items():
        if a.only and name != a.only:
            continue
        build(a.samples)
        bpy.context.scene.render.resolution_percentage = a.percent
        raw = os.path.join(a.out, f"{name}_raw.png")
        bpy.context.scene.render.filepath = raw
        bpy.ops.render.render(write_still=True)
        overlay(raw, title, small, where).save(os.path.join(a.out, f"{name}.png"))
        os.remove(raw)
        print("poster", name)


if __name__ == "__main__":
    main()
