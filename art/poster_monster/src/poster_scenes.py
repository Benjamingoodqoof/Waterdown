#!/usr/bin/env python3
"""Renders original Frutiger Aero poster art in Blender (glass towers, grass, soap bubbles,
tropical fish, a glossy globe) and lays the slogans over it.

Usage: python3 poster_scenes.py OUT_DIR [--only NAME] [--samples 64]
"""
import argparse
import math
import os
import random

import bpy  # noqa: I001  (bpy must load before mathutils)
from mathutils import Vector
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
    ob = mesh_obj(f"Cloud{seed}", [(-1, 0, -0.55), (1, 0, -0.55), (1, 0, 0.55), (-1, 0, 0.55)], [(0, 1, 2, 3)], m)
    ob.location = loc
    ob.scale = (size, size, size)
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


def grass_field(x0, x1, y0, y1, count=90000, length=0.32):
    """Hair grass on a patch in front of the camera, over a lawn that runs to the horizon."""
    m, nt, b = node_mat("Grass")
    b.inputs["Base Color"].default_value = (0.2, 0.62, 0.03, 1)
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Subsurface Weight"].default_value = 0.2
    try:
        b.inputs["Subsurface Radius"].default_value = (0.1, 0.4, 0.05)
    except (KeyError, TypeError):
        pass
    lawn, lt, lb = node_mat("Lawn")
    nz = lt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 60
    ramp = lt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.06, 0.3, 0.02, 1)
    ramp.color_ramp.elements[1].color = (0.25, 0.6, 0.05, 1)
    lt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    lt.links.new(ramp.outputs["Color"], lb.inputs["Base Color"])
    lb.inputs["Roughness"].default_value = 0.6
    mesh_obj("Lawn", [(-200, y0, 0), (200, y0, 0), (200, 300, 0), (-200, 300, 0)], [(0, 1, 2, 3)], lawn)
    ground = mesh_obj("Ground", [(x0, y0, 0.001), (x1, y0, 0.001), (x1, y1, 0.001), (x0, y1, 0.001)], [(0, 1, 2, 3)], lawn)
    ground.data.materials.append(m)
    ground.modifiers.new("grass", "PARTICLE_SYSTEM")
    st = ground.particle_systems[0].settings
    st.type = "HAIR"
    st.count = count
    st.hair_length = length
    st.material = 2
    st.use_advanced_hair = True
    st.normal_factor = length  # with advanced hair the emit velocity sets the blade length
    st.factor_random = length * 0.25
    st.brownian_factor = 0.0
    st.child_type = "INTERPOLATED"
    st.child_percent = 4
    st.rendered_child_count = 3
    st.roughness_endpoint = 0.06
    st.roughness_2 = 0.08
    st.child_length = 0.9
    st.child_length_threshold = 0.3
    st.root_radius = 1.0
    st.tip_radius = 0.0
    st.radius_scale = 0.0016
    st.display_step = 3
    st.render_step = 4
    return ground


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
def scene_promised(samples):
    """Low angle from the grass up at glass towers, a globe in the sky, fish and bubbles."""
    sc = reset()
    sc.cycles.samples = samples
    rnd = random.Random(3)
    sky(sun_elev=42, sun_rot=215)
    grass_field(-4.0, 4.0, 0.2, 6.0, count=120000, length=0.22)
    towers = [(-3.5, 14, 2.2, 2.2, 26, (0.01, 0.07, 0.22)), (1.8, 18, 3.0, 2.5, 34, (0.01, 0.09, 0.26)),
              (6.5, 13, 2.4, 2.4, 22, (0.02, 0.08, 0.2)), (-8.0, 20, 3.2, 3.0, 30, (0.01, 0.06, 0.18)),
              (10.5, 22, 3.0, 3.0, 28, (0.01, 0.08, 0.24)), (-1.2, 26, 2.6, 2.6, 40, (0.01, 0.07, 0.2))]
    for i, (x, y, w, d, h, tint) in enumerate(towers):
        glass_tower(f"Tower{i}", x, y, w, d, h, tint, rot=math.radians(rnd.uniform(-12, 12)))
    globe((-2.6, 9.0, 7.6), 1.25)
    for i in range(10):
        cloud((rnd.uniform(-22, 22), 60, rnd.uniform(10, 40)), rnd.uniform(6, 11), i, (0, 0, 1))
    for i in range(22):
        bubble((rnd.uniform(-1.6, 2.0), rnd.uniform(1.6, 5.5), rnd.uniform(0.7, 3.6)), rnd.uniform(0.06, 0.26),
               rnd.uniform(250, 750))
    fish("Clown", (0.9, 2.3, 1.15), 0.95, (-30, -8), "clown")
    fish("Clown2", (-0.55, 3.6, 2.5), 0.5, (25, 5), "clown")
    fish("Tang", (-1.25, 4.2, 3.4), 0.85, (15, 0), "tang")
    fish("Yellow", (1.5, 4.8, 3.3), 0.55, (160, 6), "yellow")
    fish("Yellow2", (-1.6, 3.0, 1.6), 0.4, (-20, 0), "yellow")
    camera((0.2, -0.6, 0.38), (0.3, 10, 7.0), lens=22)


SCENES = {
    "promised": (scene_promised, "Meet\nyour\npromised\nfuture", "Your future has been reserved."),
}


# ---------------------------------------------------------------- slogan overlay
def overlay(path, title, small):
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
    y0 = h - len(lines) * size * 0.98 - h * 0.045
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
    ImageDraw.Draw(img).text((w * 0.045, h * 0.03), small, font=small_font, fill=(255, 255, 255, 235))
    return img.convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--only", default=None)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--percent", type=int, default=100)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, (build, title, small) in SCENES.items():
        if a.only and name != a.only:
            continue
        build(a.samples)
        bpy.context.scene.render.resolution_percentage = a.percent
        raw = os.path.join(a.out, f"{name}_raw.png")
        bpy.context.scene.render.filepath = raw
        bpy.ops.render.render(write_still=True)
        overlay(raw, title, small).save(os.path.join(a.out, f"{name}.png"))
        print("poster", name)


if __name__ == "__main__":
    main()
