"""Shared modeling, material and baking helpers for the props.

Units are meters at real size; each prop faces -Y (its lens points that way), Z is up, and its
own left side is +X.
"""
import math
import os

import bpy  # noqa: I001  (bpy must load before mathutils and bmesh)
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
TAU = 2 * math.pi


def V(*a):
    return Vector(a)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"


# ---------------------------------------------------------------- geometry
def from_bm(name, bm, mat):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def axis_matrix(axis):
    return {"X": Matrix.Rotation(math.pi / 2, 4, "Y"), "Y": Matrix.Rotation(math.pi / 2, 4, "X"),
            "Z": Matrix.Identity(4)}[axis]


def rbox(name, size, center, bevel, mat, segs=3, rot=None):
    """A box with rounded edges."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = V(v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segs, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    M = Matrix.Translation(V(*center)) @ (rot or Matrix.Identity(4))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return from_bm(name, bm, mat)


def cyl(name, r, h, center, mat, axis="Z", segs=32, bevel=0.0, r2=None, rot=None):
    """A cylinder (or cone, with r2) along an axis, its cap edges optionally rounded."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r if r2 is None else r2,
                          depth=h)
    if bevel > 0:
        caps = [e for e in bm.edges if any(len(f.verts) > 4 for f in e.link_faces)]
        bmesh.ops.bevel(bm, geom=caps, offset=bevel, segments=2, profile=0.5, affect="EDGES", clamp_overlap=True)
    M = Matrix.Translation(V(*center)) @ (rot or Matrix.Identity(4)) @ axis_matrix(axis)
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return from_bm(name, bm, mat)


def sphere(name, r, center, mat, segs=16, rings=8):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    bmesh.ops.translate(bm, vec=V(*center), verts=bm.verts)
    return from_bm(name, bm, mat)


def gear(name, r_out, r_in, teeth, h, center, mat, axis="Z"):
    """A toothed wheel."""
    bm = bmesh.new()
    vs = []
    for k in range(teeth * 2):
        a = TAU * k / (teeth * 2)
        r = r_out if k % 2 == 0 else r_in
        vs.append(bm.verts.new(V(math.cos(a) * r, math.sin(a) * r, -h / 2)))
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=V(0, 0, h), verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(V(*center)) @ axis_matrix(axis), verts=bm.verts)
    return from_bm(name, bm, mat)


def sweep(name, path, section, mat, cap=True):
    """A tube along `path` (points); section(t) -> list of (u, v) offsets across it, u along the
    path's side vector and v along its up vector (world Z made perpendicular)."""
    bm = bmesh.new()
    rings = []
    n = len(path)
    for i, p in enumerate(path):
        T = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        up = V(0, 0, 1) - T * T.z
        up = up.normalized() if up.length > 1e-6 else V(1, 0, 0)
        side = T.cross(up).normalized()
        rings.append([bm.verts.new(p + side * u + up * v) for u, v in section(i / (n - 1))])
    m = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for j in range(m):
            bm.faces.new([a[j], a[(j + 1) % m], b[(j + 1) % m], b[j]])
    if cap:
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return from_bm(name, bm, mat)


def superellipse(rx, ry, n=24, e=4.0):
    pts = []
    for k in range(n):
        a = TAU * k / n
        c, s = math.cos(a), math.sin(a)
        pts.append((rx * math.copysign(abs(c) ** (2 / e), c), ry * math.copysign(abs(s) ** (2 / e), s)))
    return pts


def plane(name, w, h, center, normal, up, mat):
    """A flat quad (UV 0..1), for labels, screens and printing."""
    n = V(*normal).normalized()
    u = V(*up).normalized()
    r = u.cross(n).normalized()
    c = V(*center)
    bm = bmesh.new()
    vs = [bm.verts.new(c + r * (x * w / 2) + u * (y * h / 2)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    f = bm.faces.new(vs)
    uvl = bm.loops.layers.uv.new("Decal")
    for loop, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
        loop[uvl].uv = uv
    return from_bm(name, bm, mat)


def activate(ob):
    for o in bpy.context.scene.objects:
        if o is not None:
            o.select_set(False)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def cut(target, cutter, op="DIFFERENCE"):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    activate(target)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)
    return target


def join(objs, name):
    objs = [o for o in objs if o]
    activate(objs[0])
    for o in objs[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return ob


def finish(ob, angle=32):
    """Smooth shading with hard edges past `angle`, origin at the middle of its bounds."""
    me = ob.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))
    activate(ob)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    return ob


# ---------------------------------------------------------------- materials
def _mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    return m, m.node_tree, next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def plastic(name, color, rough=0.35, metal=0.0, scuff=0.12, grain=0.02, texture=None, tex_scale=300.0, tex_strength=0.3):
    """Plastic or metal with scuffs and fine grain. texture: 'knurl' (rubber grip), 'weave'
    (fabric strap), 'grille' (microphone holes) or 'ridges' (a knurled dial)."""
    m, nt, b = _mat(name)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.62
    ramp.color_ramp.elements[1].position = 0.75
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*color, 1)
    lighter = tuple(min(1.0, c * 1.6 + 0.04) for c in color)
    mix.inputs["B"].default_value = (*lighter, 1)
    nt.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    mix.inputs["Factor"].default_value = 0
    sc = nt.nodes.new("ShaderNodeMath")
    sc.operation = "MULTIPLY"
    sc.inputs[1].default_value = scuff
    nt.links.new(ramp.outputs["Color"], sc.inputs[0])
    nt.links.new(sc.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    rr = nt.nodes.new("ShaderNodeMath")
    rr.operation = "MULTIPLY_ADD"
    rr.inputs[1].default_value = 0.25
    rr.inputs[2].default_value = rough
    nt.links.new(ramp.outputs["Color"], rr.inputs[0])
    nt.links.new(rr.outputs[0], b.inputs["Roughness"])
    b.inputs["Metallic"].default_value = metal
    # fine grain, plus the surface pattern
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 900.0
    nt.links.new(coord.outputs["Object"], fine.inputs["Vector"])
    height = fine.outputs["Fac"]
    strength = grain
    if texture:
        if texture == "knurl":
            t = nt.nodes.new("ShaderNodeTexVoronoi")
            t.inputs["Scale"].default_value = tex_scale
            out = t.outputs["Distance"]
        elif texture == "grille":
            t = nt.nodes.new("ShaderNodeTexVoronoi")
            t.inputs["Scale"].default_value = tex_scale
            t.inputs["Randomness"].default_value = 0.0
            lt = nt.nodes.new("ShaderNodeMath")
            lt.operation = "LESS_THAN"
            lt.inputs[1].default_value = 0.28
            nt.links.new(t.outputs["Distance"], lt.inputs[0])
            out = lt.outputs[0]
            dark = nt.nodes.new("ShaderNodeMix")
            dark.data_type = "RGBA"
            nt.links.new(mix.outputs["Result"], dark.inputs["A"])
            dark.inputs["B"].default_value = (0.0, 0.0, 0.0, 1)
            nt.links.new(lt.outputs[0], dark.inputs["Factor"])
            nt.links.new(dark.outputs["Result"], b.inputs["Base Color"])
        else:  # weave / ridges: crossing or single waves
            t = nt.nodes.new("ShaderNodeTexWave")
            t.inputs["Scale"].default_value = tex_scale
            t.wave_profile = "SIN"
            if texture == "weave":
                t2 = nt.nodes.new("ShaderNodeTexWave")
                t2.inputs["Scale"].default_value = tex_scale
                t2.bands_direction = "Y"
                nt.links.new(coord.outputs["Object"], t2.inputs["Vector"])
                add = nt.nodes.new("ShaderNodeMath")
                nt.links.new(t.outputs["Fac"], add.inputs[0])
                nt.links.new(t2.outputs["Fac"], add.inputs[1])
                out = add.outputs[0]
            else:
                t.bands_direction = "Z"
                out = t.outputs["Fac"]
        nt.links.new(coord.outputs["Object"], t.inputs["Vector"])
        height = out
        strength = tex_strength
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def printed(name, base, image, rough=0.35, metal=0.0):
    """Base plastic with printing from an RGBA image laid over it (on a UV 0..1 quad)."""
    m, nt, b = _mat(name)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(TEX, image), check_existing=True)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "Decal"  # the quad's own 0..1 layout, kept apart from the bake's unwrap
    nt.links.new(uv.outputs["UV"], img.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*base, 1)
    nt.links.new(img.outputs["Color"], mix.inputs["B"])
    nt.links.new(img.outputs["Alpha"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def textured(name, image, rough=0.4, emit=0.0):
    """A part that shows an image as it is (labels, the screen)."""
    m, nt, b = _mat(name)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(TEX, image), check_existing=True)
    nt.links.new(img.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    if emit:
        nt.links.new(img.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emit
    return m


def glass(name, tint=(0.6, 0.65, 0.7), rough=0.03):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.5
    return m


def light(name, color, strength=4.0):
    m, nt, b = _mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m


# ---------------------------------------------------------------- baking to Roblox textures
def bake(ob, size, prefix, out_dir):
    """Unwraps a part and bakes its materials into color, roughness, normal and metalness
    maps, then gives it a single material using them (what SurfaceAppearance takes)."""
    sc = bpy.context.scene
    sc.cycles.samples = 8
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    me.uv_layers.active = me.uv_layers["UVMap"]
    me.uv_layers["UVMap"].active_render = True
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.006)
    bpy.ops.uv.pack_islands(margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")
    maps = {}
    for kind in ("color", "roughness", "normal", "metalness"):
        img = bpy.data.images.new(f"{prefix}_{kind}", size, size, alpha=False)
        if kind != "color":
            img.colorspace_settings.name = "Non-Color"
        maps[kind] = img
    mats = [s.material for s in ob.material_slots]

    def target(img):
        for m in mats:
            nt = m.node_tree
            n = nt.nodes.get("_bake") or nt.nodes.new("ShaderNodeTexImage")
            n.name = "_bake"
            n.image = img
            nt.nodes.active = n

    def emit_from(kind):
        saved = []
        for m in mats:
            nt = m.node_tree
            b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            ec, es = b.inputs["Emission Color"], b.inputs["Emission Strength"]
            links = [lk for lk in nt.links if lk.to_socket == ec]
            saved.append((nt, b, tuple(ec.default_value), es.default_value, [lk.from_socket for lk in links]))
            for lk in links:
                nt.links.remove(lk)
            src = b.inputs["Base Color"] if kind == "color" else b.inputs["Metallic"]
            if src.is_linked:
                nt.links.new(src.links[0].from_socket, ec)
            elif kind == "color":
                ec.default_value = tuple(src.default_value)
            else:
                ec.default_value = (src.default_value,) * 3 + (1,)
            es.default_value = 1.0
        return saved

    def restore(saved):
        for nt, b, col, strength, froms in saved:
            ec = b.inputs["Emission Color"]
            for lk in [lk for lk in nt.links if lk.to_socket == ec]:
                nt.links.remove(lk)
            ec.default_value = col
            b.inputs["Emission Strength"].default_value = strength
            for f in froms:
                nt.links.new(f, ec)

    for kind in ("color", "metalness"):
        target(maps[kind])
        saved = emit_from(kind)
        bpy.ops.object.bake(type="EMIT", margin=6, use_clear=True)
        restore(saved)
    target(maps["roughness"])
    bpy.ops.object.bake(type="ROUGHNESS", margin=6, use_clear=True)
    target(maps["normal"])
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=6, use_clear=True)
    os.makedirs(out_dir, exist_ok=True)
    for kind, img in maps.items():
        img.filepath_raw = os.path.join(out_dir, f"{prefix}_{kind}.png")
        img.file_format = "PNG"
        img.save()
    # one baked material in place of the procedural ones
    m, nt, b = _mat(f"M_{prefix}")

    def tex(kind):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = maps[kind]
        return n

    nt.links.new(tex("color").outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex("roughness").outputs["Color"], b.inputs["Roughness"])
    nt.links.new(tex("metalness").outputs["Color"], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex("normal").outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    if "Decal" in me.uv_layers:
        me.uv_layers.remove(me.uv_layers["Decal"])
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)
