#!/usr/bin/env python3
"""Builds the poster monster in Blender and saves a .blend.

A gaunt 9 ft figure: one merged papier-mache body covered in wet promo posters laid in
overlapping rows, a wadded-paper head behind a cracked droplet-mascot mask, rolled-poster
fingers, a few peeling sheets, packing tape and a torn-open chest with rolled-poster ribs.
Includes the rig and skin weights.

Usage: python3 build_model.py OUT.blend
"""
import math
import os
import sys

import bpy  # noqa: I001  (bpy must load before bmesh/mathutils)
from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import skeleton as SK  # noqa: E402
from geom import (MB, Blob, Snap, Tube, add_band, add_blob_core, add_grid_tube, add_path_tube,  # noqa: E402
                  add_ribbon, add_sheet, add_strip, basis, frame_to, lerp, pick_cell, poster_uv, region_uv, rng,
                  smooth, wrap_rows)
from layout import CAV, HEAD, HEAD_C, LIMBS, NECK, TORSO, cavity_e, head_weights, torso_part  # noqa: E402
from mask import add_cup, build_mask_object, mask_normal, mask_world  # noqa: E402
from skeleton import J, V  # noqa: E402

TEX = os.path.normpath(os.path.join(HERE, "..", "textures"))
CORE_TRIS = 5200


def palm_blob(side):
    along, across, palm = SK.hand_frame(side)
    center = J[f"wrist_{side}"] + (J[f"hand_{side}"] - J[f"wrist_{side}"]) * 0.55 + palm * 0.004
    return Blob(center, (0.03, 0.042, 0.058), basis(across.cross(-along), across, -along))


def foot_blob(side):
    fwd = J[f"toe_{side}"] - J[f"ankle_{side}"]
    fwd = V(fwd.x, fwd.y, 0).normalized()
    return Blob(J[f"ankle_{side}"] + fwd * 0.07 + V(0, 0, -0.035), (0.068, 0.14, 0.05),
                basis(fwd.cross(V(0, 0, 1)).normalized(), fwd, V(0, 0, 1)))


def on_blob(blob, d, twist=0.0):
    """Sheet placement centered where direction d (blob-local) meets the blob."""
    place = blob.placer(frame_to(d, twist))
    return lambda a, b: place(a, b, 0.0)


def dseg(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (a + ab * t - p).length


# ================================================================ merged body
def build_core():
    """One watertight papier-mache body. The pieces are unioned by a voxel remesh and smoothed,
    so the arms, legs, neck and head grow out of the torso. Returns the decimated body and a
    snapper onto the full-resolution surface (before the chest is carved) for laying posters."""
    src = MB("core_src")
    add_grid_tube(src, TORSO, 24, 26, -0.022, "x")
    add_grid_tube(src, NECK, 12, 10, -0.002, "x")
    add_blob_core(src, HEAD, 20, 14, -0.006, "x")
    for side, _ in SK.SIDES:
        L = LIMBS[side]
        for key, inset in (("uarm", -0.012), ("farm", -0.006), ("thigh", -0.012), ("shin", -0.006)):
            add_grid_tube(src, L[key], 12, 10, inset, "x")
        for j, r in (("shoulder", 0.06), ("elbow", 0.038), ("wrist", 0.03), ("hip", 0.072), ("knee", 0.046),
                     ("ankle", 0.036)):
            add_blob_core(src, Blob(J[f"{j}_{side}"], (r, r, r)), 12, 8, 0.0, "x")
        add_blob_core(src, palm_blob(side), 12, 8, 0.0, "x")
        add_blob_core(src, foot_blob(side), 14, 8, 0.0, "x")
    ob = src.build(None)
    rem = ob.modifiers.new("remesh", "REMESH")
    rem.mode = "VOXEL"
    rem.voxel_size = 0.008
    sm = ob.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = 6
    hi = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    src_mesh = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(src_mesh)
    snap = Snap(hi)

    # the torn chest: push the pulp inward behind the hole
    for v in hi.vertices:
        p = v.co
        if 1.45 < p.z < 1.85 and abs(p.x) < 0.2:
            e = cavity_e(p)
            if e < 1.0:
                v.co = p - v.normal * 0.045 * (1 - e) ** 0.7
    hi.update()
    tmp = bpy.data.objects.new("core_tmp", hi)
    bpy.context.scene.collection.objects.link(tmp)
    dec = tmp.modifiers.new("decimate", "DECIMATE")
    dec.ratio = CORE_TRIS / (2 * len(hi.polygons))
    lo = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(hi)

    mb = MB("Body_Core")
    ids = [mb.add_vert(v.co, *core_skin(v.co)) for v in lo.vertices]
    pulp, void = region_uv("pulp"), region_uv("void")
    for poly in lo.polygons:
        ax = max(range(3), key=lambda i: abs(poly.normal[i]))
        c = poly.center
        r = void if (1.45 < c.z < 1.85 and abs(c.x) < 0.2 and cavity_e(c) < 0.85) else pulp
        uvs = []
        for vi in poly.vertices:
            co = lo.vertices[vi].co
            a, b = [(co.y, co.z - 1.4), (co.x, co.z - 1.4), (co.x, co.y)][ax]
            uvs.append((r[0] + (r[2] - r[0]) * min(1.0, max(0.0, (a + 1.4) / 2.8)),
                        r[1] + (r[3] - r[1]) * min(1.0, max(0.0, (b + 1.4) / 2.8))))
        mb.add_face([ids[i] for i in poly.vertices], uvs)
    bpy.data.meshes.remove(lo)
    return mb, snap


def core_skin(p):
    """(part, fixed weights) for a body vertex: the nearest body part, kept to the vertex's side."""
    s = "Left" if p.x >= 0 else "Right"
    cands = (("torso", ("LowerTorso", "Spine", "UpperTorso")), ("neck", ("Neck",)), ("head", ("Head",)),
             (f"shoulder_{s}", (f"{s}Shoulder",)), (f"arm_{s}", (f"{s}UpperArm", f"{s}LowerArm")),
             (f"hand_{s}", (f"{s}Hand",)), (f"leg_{s}", (f"{s}UpperLeg", f"{s}LowerLeg")), (f"foot_{s}", (f"{s}Foot",)))
    _, part = min((dseg(p, SK.BONES[b][0], SK.BONES[b][1]) / SK.BONES[b][3], part) for part, bones in cands for b in bones)
    if part == "head":
        return None, head_weights(p)
    if part == "torso" and p.z < 1.36:
        part = "pelvis"
    return part, None


# ================================================================ posters and the rest
def build_wrap(snap):
    upper, lower, hands, glow = MB("Body_Upper"), MB("Body_Lower"), MB("Body_Hands"), MB("EyeGlow")

    def cut(p):  # the hole in the chest
        return cavity_e(p) < 0.9

    def lift(p):  # torn edges curl outward around the hole
        e = cavity_e(p)
        return 0.03 * min(0.4, 1.3 - e) if 0.9 <= e < 1.3 else 0.0

    # ---- torso: four rows of five posters, the wrap-around seam at the back
    wrap_rows(upper, TORSO, torso_part, 5, 1.26 - TORSO.z0, 2.0 - TORSO.z0, 0.24, 0.024, snap,
              theta0=math.pi / 2 + math.pi / 5, seg=(0.035, 0.045), cut=cut, lift=lift, peels={
                  (0, 3): dict(name="PeelHip", parent="LowerTorso", attach=0.1, amount=0.04),
                  (1, 4): dict(name="PeelBack", parent="Spine", attach=0.15, amount=0.05),
                  (2, 1): dict(name="PeelChest", parent="UpperTorso", attach=0.2, amount=0.07)})

    # ribs of rolled posters across the hole, hanging off a rolled-poster sternum; the far ends
    # slide under the posters on the side
    for zr in (1.57, 1.63, 1.69):
        pts, radii = [], []
        for k in range(15):
            t = k / 14
            th = CAV["th"] - 0.36 + 0.98 * t
            p, n = snap(TORSO.pos_theta(th, zr + 0.02 * (th - CAV["th"]) / 0.42 - TORSO.z0, 0.0)[0])
            pts.append(p + n * (0.016 - 0.014 * smooth(0.65, 1.0, t)))
            radii.append(0.0115 - 0.003 * t)
        add_path_tube(upper, pts, radii, 6, poster_uv(rng.choice(C.DRY_CELLS), 0.06, 0.3), "torso", saw=0.25)
    pts = []
    for k in range(9):
        p, n = snap(TORSO.pos_theta(CAV["th"] - 0.38, 1.53 + 0.26 * k / 8 - TORSO.z0, 0.0)[0])
        pts.append(p + n * 0.016)
    add_path_tube(upper, pts, [0.013] * 9, 6, poster_uv(rng.choice(C.DRY_CELLS), 0.06, 0.3), "torso", saw=0.2)

    # ---- shoulders: posters over the slope up to the neck, and one over the joint where the arm
    # meets the torso
    for side, sx in SK.SIDES:
        tb = Blob(V(0.1 * sx, 0.012, 2.0), (0.06, 0.06, 0.04))
        for d in (V(0.25 * sx, -0.6, 0.75), V(0.25 * sx, 0.6, 0.75)):
            add_sheet(upper, on_blob(tb, d), 0.16, 0.14, 0.038, poster_uv(pick_cell(2.0), 0.16, 0.14, (0.85, 1.0)),
                      "torso", snap=snap, seg=(0.03, 0.035))
        sb = Blob(J[f"shoulder_{side}"], (0.07, 0.065, 0.07))
        add_sheet(upper, on_blob(sb, V(0.8 * sx, 0.0, 0.6)), 0.17, 0.19, 0.03,
                  poster_uv(pick_cell(1.95), 0.17, 0.19, (0.85, 1.0)), f"shoulder_{side}", snap=snap, seg=(0.03, 0.035))

    # ---- neck: the dark pulp stalk with a few strips and tape
    for k in range(5):
        th, bc = k * 2 * math.pi / 5 + rng.uniform(0, 0.3), rng.uniform(0.08, 0.24)

        def neck_place(a, b, th=th, bc=bc):
            return NECK.pos_theta(th + a / NECK.rmean(bc + b), bc + b, 0.0)

        add_sheet(upper, neck_place, 0.055, 0.18, 0.004, poster_uv(pick_cell(2.1), 0.055, 0.18, (0.85, 1.0)), "neck",
                  psi=0.45, snap=snap, seg=(0.02, 0.04), edge_lift=0.0)
    add_band(upper, NECK, 0.10, 0.03, 0.008, "neck", segs=12, tilt=0.02, snap=snap)
    add_band(upper, NECK, 0.27, 0.026, 0.007, "neck", segs=12, tilt=0.015, snap=snap)

    # ---- limbs: rings of posters, upper rings over lower ones like shingles
    for side, sx in SK.SIDES:
        L = LIMBS[side]
        front = -math.pi / 2
        wrap_rows(upper, L["farm"], f"arm_{side}", 2, -0.03, L["farm"].L + 0.02, 0.2, 0.006, snap, theta0=front,
                  seg=(0.025, 0.045))
        wrap_rows(upper, L["uarm"], f"arm_{side}", 2, -0.02, L["uarm"].L + 0.03, 0.2, 0.014, snap, theta0=front,
                  seg=(0.025, 0.045), peels={(1, 0): dict(name="PeelArmL", parent="LeftUpperArm", attach=0.15,
                                                          amount=0.035)} if side == "Left" else None)
        wrap_rows(lower, L["shin"], f"leg_{side}", 2, -0.02, L["shin"].L + 0.02, 0.21, 0.006, snap, theta0=front,
                  seg=(0.025, 0.045), peels={(1, 0): dict(name="PeelShinL", parent="LeftLowerLeg", attach=0.15,
                                                          amount=0.035)} if side == "Left" else None)
        wrap_rows(lower, L["thigh"], f"leg_{side}", 3, -0.02, L["thigh"].L + 0.04, 0.21, 0.014, snap, theta0=front,
                  seg=(0.025, 0.045), peels={(1, 1): dict(name="PeelThighR", parent="RightUpperLeg", attach=0.15,
                                                          amount=0.045)} if side == "Right" else None)
        # tape where it was needed, not in neat pairs
        if side == "Left":
            add_band(upper, L["farm"], 0.05, 0.032, 0.016, f"arm_{side}", segs=12, tilt=0.015, snap=snap)
            add_band(upper, L["uarm"], 0.36, 0.034, 0.024, f"arm_{side}", segs=12, tilt=0.03, snap=snap)
            add_band(lower, L["thigh"], 0.30, 0.036, 0.026, f"leg_{side}", segs=14, tilt=0.03, snap=snap)
        else:
            add_band(upper, L["farm"], 0.33, 0.03, 0.016, f"arm_{side}", segs=12, tilt=0.025, snap=snap)
            add_band(lower, L["shin"], 0.5, 0.034, 0.016, f"leg_{side}", segs=12, tilt=0.03, snap=snap)

    # ---- hands: a wrapped wad with rolled-poster fingers
    pulp_mid = C.px_to_uv(*[(a + b) / 2 for a, b in zip(C.REGIONS["pulp"][:2], C.REGIONS["pulp"][2:])])
    for side, sx in SK.SIDES:
        along, across, palm = SK.hand_frame(side)
        pb = palm_blob(side)
        for d in (V(1, 0, 0.2), V(0.2, 1, 0), V(0.2, -1, 0), V(-0.9, 0, -0.2)):
            w, h = rng.uniform(0.08, 0.1), rng.uniform(0.09, 0.11)
            add_sheet(hands, on_blob(pb, d, rng.uniform(0, 6.28)), w, h, 0.003, poster_uv(pick_cell(0.9), w, h, (0.85, 1.0)),
                      f"hand_{side}", snap=snap, crumple=0.003, freq=40, seg=(0.025, 0.03), edge_lift=0.0)
        for fname, chain in SK.finger_chains(side).items():
            pts, radii = [], []
            r0 = 0.0155 if fname != "Thumb" else 0.017
            for k in range(3):
                for t in (0.0, 0.25, 0.5, 0.75):
                    pts.append(chain[k].lerp(chain[k + 1], t))
                    radii.append(lerp(r0, 0.0062, (k + t) / 3) * (1.08 if t == 0.0 and k else 1.0))
            pts.append(chain[3])
            radii.append(0.0055)
            tip = chain[3] + (chain[3] - chain[2]).normalized() * 0.014
            add_path_tube(hands, pts, radii, 8, poster_uv(pick_cell(0.6), 0.09, 0.4), f"f_{side}{fname}",
                          tip=tip, tip_uv=pulp_mid, saw=0.22)
            if rng.random() < 0.5:  # a twist of tape where the roll meets the hand
                ft = Tube(chain[0], chain[1], [(0, 0.0185, 0.0185), (1, 0.017, 0.017)], side=across)
                add_band(hands, ft, ft.L * 0.3, 0.018, 0.0, f"f_{side}{fname}", segs=8, tilt=0.003)

    # ---- feet: soggy wrapped clumps
    for side, sx in SK.SIDES:
        fb = foot_blob(side)
        for d in (V(0, 0.4, 1), V(0, 1, 0.3), V(1, 0.2, 0.3), V(-1, 0.2, 0.3)):
            w, h = rng.uniform(0.14, 0.18), rng.uniform(0.15, 0.2)
            add_sheet(lower, on_blob(fb, d, rng.uniform(0, 6.28)), w, h, 0.004,
                      poster_uv(rng.choice(C.WET_CELLS), w, h, (0.85, 1.0)), f"foot_{side}", snap=snap,
                      crumple=0.005, freq=30, seg=(0.03, 0.04), edge_lift=0.0)

    # ---- head: posters balled up behind the mask
    golden = math.pi * (3 - math.sqrt(5))
    n = 22
    for k in range(n):
        y = 1 - 2 * (k + 0.5) / n
        r = math.sqrt(1 - y * y)
        d = V(math.cos(golden * k) * r, math.sin(golden * k) * r, y)
        if d.dot(V(0, -1, 0)) > 0.35:  # hidden behind the mask, and keeps the eye sockets clear
            continue
        w, h = rng.uniform(0.18, 0.26), rng.uniform(0.18, 0.26)
        add_sheet(upper, on_blob(HEAD, d, rng.uniform(0, 6.28)), w, h, 0.004 + rng.uniform(0, 0.004),
                  poster_uv(pick_cell(2.4), w, h, (0.85, 1.0)), None, snap=snap, crumple=0.007, freq=12,
                  seg=(0.03, 0.03), torn=0.06, edge_lift=0.0, fixed=head_weights)
    for d, sz in ((V(0.45, -0.45, 0.75), 0.2), (V(-0.45, -0.45, 0.75), 0.2), (V(0.0, -0.4, 0.9), 0.2),
                  (V(0.72, -0.5, 0.45), 0.14), (V(-0.72, -0.5, 0.45), 0.14)):
        w, h = sz * rng.uniform(0.9, 1.1), sz * rng.uniform(0.9, 1.1)
        add_sheet(upper, on_blob(HEAD, d, rng.uniform(0, 6.28)), w, h, 0.01, poster_uv(pick_cell(2.4), w, h, (0.85, 1.0)),
                  None, snap=snap, crumple=0.006, freq=12, seg=(0.03, 0.03), torn=0.06, edge_lift=0.0,
                  fixed=head_weights)

    # ---- mask sockets, glints, the tape holding the mask on, and strings of wet paper like drool
    for k in range(2):
        (cx, cy), (rx, ry), _ = C.EYES[k]
        add_cup(upper, cx, cy, rx * 1.25, ry * 1.2, 0.05)
        g = mask_world(cx + 0.007, cy + 0.012, -0.004 - 0.042)
        add_blob_core(glow, Blob(g, (0.0042, 0.0042, 0.0042)), 8, 5, 0, None, {"Head": 1.0})
    add_cup(upper, 0.0, 0.0, C.SMILE_HW * 1.12, 0.016, 0.03, nphi=18, curve=C.smile_y)
    tape = region_uv("tape")
    for ex, ey in ((0.168, -0.06), (-0.17, -0.025), (0.085, 0.15), (-0.09, -0.175)):
        cx, cy = ex * 0.78, ey * 0.82 + 0.01
        pts, nrms = [], []
        for t in (0.0, 0.5, 1.0):
            x, y = lerp(cx, ex * 1.01, t), lerp(cy, ey * 1.01, t)
            pts.append(mask_world(x, y, 0.003))
            nrms.append(mask_normal(x, y))
        d0 = (pts[-1] - HEAD_C).normalized()
        # wrap backward around the head: sideways for side strips, over or under for the others
        axis = V(0, 0, 1) if abs(ey) < 0.1 else V(1, 0, 0) * (-1 if ey > 0 else 1)
        sgn = 1 if ex > 0 else -1
        for ang in (14, 30, 46, 60):
            d = Matrix.Rotation(math.radians(ang * sgn if abs(ey) < 0.1 else ang), 3, axis) @ d0
            p, nrm = snap(HEAD.at_dir(d, 0.0)[0])
            pts.append(p + nrm * 0.022)
            nrms.append(nrm)
        add_ribbon(upper, pts, nrms, 0.034, tape, None, {"Head": 1.0})
    for x, y, ln, wd in ((-0.065, -0.185, 0.2, 0.022), (0.015, -0.2, 0.13, 0.018), (0.075, -0.175, 0.24, 0.026)):
        add_strip(upper, mask_world(x, y, -0.008), ln, wd, mask_normal(x, y),
                  poster_uv(rng.choice(C.WET_CELLS), wd, ln), {"Head": 1.0}, curl=0.05)
    return upper, lower, hands, glow


# ================================================================ materials
def load_image(name, noncolor):
    img = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    return img


def make_material(name, prefix, coat=0.0, coat_rough=0.2):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    col = nt.nodes.new("ShaderNodeTexImage")
    col.image = load_image(f"{prefix}_color.png", False)
    col.location = (-700, 300)
    rough = nt.nodes.new("ShaderNodeTexImage")
    rough.image = load_image(f"{prefix}_roughness.png", True)
    rough.location = (-700, 0)
    nrm = nt.nodes.new("ShaderNodeTexImage")
    nrm.image = load_image(f"{prefix}_normal.png", True)
    nrm.location = (-1000, -300)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-700, -300)
    nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(rough.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Coat Roughness"].default_value = coat_rough
    return m


def make_glow_material():
    m = bpy.data.materials.new("M_EyeGlow")
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    bsdf.inputs["Roughness"].default_value = 0.1
    bsdf.inputs["Emission Color"].default_value = (0.75, 0.85, 1.0, 1)
    bsdf.inputs["Emission Strength"].default_value = 0.8
    return m


# ================================================================ rig + weights
def build_armature():
    arm = bpy.data.armatures.new("PosterMonster_Rig")
    ob = bpy.data.objects.new("PosterMonster_Rig", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for name, (h, t, parent, r, roll) in SK.BONES.items():
        eb = arm.edit_bones.new(name)
        eb.head, eb.tail = h, t
        eb.align_roll(roll)
        ebs[name] = eb
    for name, (h, t, parent, r, roll) in SK.BONES.items():
        if parent:
            ebs[name].parent = ebs[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    return ob


def part_bones():
    P = {
        "torso": [("LowerTorso", None), ("Spine", None), ("UpperTorso", None), ("LeftShoulder", None),
                  ("RightShoulder", None), ("Neck", 0.08)],
        "pelvis": [("LowerTorso", None), ("Spine", None), ("LeftUpperLeg", 0.05), ("RightUpperLeg", 0.05)],
        "neck": [("UpperTorso", 0.1), ("Neck", None), ("Head", 0.1)],
    }
    for s, _ in SK.SIDES:
        P[f"shoulder_{s}"] = [("UpperTorso", None), (f"{s}Shoulder", None), (f"{s}UpperArm", None)]
        P[f"arm_{s}"] = [(f"{s}Shoulder", 0.05), (f"{s}UpperArm", None), (f"{s}LowerArm", None), (f"{s}Hand", None)]
        P[f"hand_{s}"] = [(f"{s}LowerArm", None), (f"{s}Hand", None)]
        P[f"leg_{s}"] = [("LowerTorso", 0.1), (f"{s}UpperLeg", None), (f"{s}LowerLeg", None), (f"{s}Foot", None)]
        P[f"foot_{s}"] = [(f"{s}LowerLeg", None), (f"{s}Foot", None)]
        for f in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
            P[f"f_{s}{f}"] = [(f"{s}Hand", 0.02)] + [(f"{s}{f}{k}", None) for k in (1, 2, 3)]
    return P


def skin(ob, mb_parts, mb_fixed, co_list, rig):
    P = part_bones()
    groups = {}
    for name in SK.BONES:
        groups[name] = ob.vertex_groups.new(name=name)
    for vi, co in enumerate(co_list):
        ws = mb_fixed[vi]
        if not ws:
            ws = {}
            for bname, rad in P[mb_parts[vi]]:
                h, t, _, r0, _ = SK.BONES[bname]
                d = dseg(co, h, t) / (rad or r0)
                ws[bname] = 1.0 / (1e-4 + d ** 4)
        top = sorted(((b, w) for b, w in ws.items() if w > 0), key=lambda kv: -kv[1])[:4]
        tot = sum(w for _, w in top)
        top = [(b, w / tot) for b, w in top if w / tot > 0.02]
        tot = sum(w for _, w in top)
        for b, w in top:
            groups[b].add([vi], w / tot, "REPLACE")
    ob.parent = rig
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = rig


def main(out_path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    paper = make_material("M_PaperAtlas", "paper")
    mask_mat = make_material("M_Mask", "mask", coat=0.15, coat_rough=0.2)
    glow = make_glow_material()

    core_mb, snap = build_core()
    upper_mb, lower_mb, hands_mb, glow_mb = build_wrap(snap)
    rig = build_armature()
    stats = []
    for mb, material in ((core_mb, paper), (upper_mb, paper), (lower_mb, paper), (hands_mb, paper), (glow_mb, glow)):
        ob = mb.build(material)
        skin(ob, mb.part, mb.fixed, mb.co, rig)
        stats.append((mb.name, len(mb.co), mb.tris()))
    mask = build_mask_object(mask_mat)
    mask_co = [v.co.copy() for v in mask.data.vertices]
    skin(mask, [None] * len(mask_co), [{"Head": 1.0}] * len(mask_co), mask_co, rig)
    stats.append(("Mask", len(mask_co), sum(len(p.vertices) - 2 for p in mask.data.polygons)))

    for name, nv, nt in stats:
        print(f"{name:12s} verts {nv:6d}  tris {nt:6d}")
    print("total tris", sum(s[2] for s in stats), "bones", len(SK.BONES))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out_path))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "poster_monster.blend"))
