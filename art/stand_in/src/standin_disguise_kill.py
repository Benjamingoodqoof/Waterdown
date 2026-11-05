#!/usr/bin/env python3
"""CRT Man's kill while disguised as a teammate: R6 against R6.

The "teammate" stands still for a beat, staring, then walks over to the player like a normal
player would (an upright walk, four held poses a step), stops in front of them, reaches out and
grabs them by the throat, and lifts them off the floor one-handed. It holds them up while they
kick and claw at its arm, its head tipping over a little more every few beats. They go limp;
it opens its hand and they drop, land on their feet, buckle and fall onto their back. Its arm
comes down, and its head snaps upright: the moment for the game to glitch it back into the suit.

The disguise is stop motion, like its other disguise animations: distinct poses held for 4 to 6
frames that snap from one to the next, with no in-betweens. Limbs are moved as well as rotated
(an arm swinging forward crosses in front of the body, a lifted leg rises to fake a bent knee).
The player moves smoothly.

Writes export/StandIn_DisguisedKill.blend: a copy of the user's R6 kill file
(shared/r6/Blender_R6Kill.blend) with both InternalArmatures keyed: InternalArmature (the
disguised CRT Man, action StandIn_DisguisedKill_Killer) and InternalArmature.001 (the player,
action StandIn_DisguisedKill_Victim). Both start together, with the killer's HumanoidRootPart
DISTANCE studs in front of the player's, facing them; the killer's body starts WALK studs
behind its HumanoidRootPart and walks onto it. 206 frames at 30 fps.

Markers: Grab 104 (QTE starts), Death 158 (QTE ends), Drop 172, Reveal 196 (glitch him back
into the suit), End 206.

Usage: python3 standin_disguise_kill.py EXPORT_DIR PREVIEW_BLEND
"""
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import kill_anim as KA  # noqa: E402
import kill_core as K  # noqa: E402
from kill_anim import Track as T  # noqa: E402

DISTANCE = 1.9  # studs between the two HumanoidRootParts during the kill
WALK = 6.0  # how far behind its HumanoidRootPart the killer starts
LENGTH = 206
GRAB, DEATH, DROP, LAND, REVEAL = 104, 158, 172, 186, 196
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", REVEAL: "Reveal", LENGTH: "End"}
K2V = Matrix.Translation((0, 0, -DISTANCE)) @ K.rot("Y", 180)  # the killer's HRP space -> the player's
V2K = K2V.inverted()
NECK = Vector((0.0, 1.0, -0.3))  # the front of the throat, in the torso's frame
KILLER_COLORS = {"Torso": (0.12, 0.3, 0.16), "Head": (0.85, 0.7, 0.55), "Right Arm": (0.85, 0.7, 0.55),
                 "Left Arm": (0.85, 0.7, 0.55), "Right Leg": (0.12, 0.12, 0.14), "Left Leg": (0.12, 0.12, 0.14)}
V = Vector


# ---------------------------------------------------------------- the disguise: held key poses
def pose(hips, rot=(0, 0, 0), head=(0, 0, 0), look=True, legs=None, arms=None):
    return {"hips": V(hips), "rot": V(rot), "head": V(head), "look": look, "legs": legs or {}, "arms": arms or {}}


def arm_rot(fwd, out=0.0, move=(0, 0, 0), twist=0.0):
    """An arm swung forward (+) or back (-) and out to the side, then moved (torso axes)."""
    return ("rot", V((fwd, twist, out)), V(move))


def walk_holds(ctx):
    """The walk: four held poses a step (5 frames each), like a stop-motion walk cycle. The
    planted foot stays put; the swinging foot lifts (the leg moved up to fake a bent knee) and
    reaches forward; the arms swing against the legs, the forward arm crossing in front."""
    holds = []
    feet = {"Right Leg": V((0.5, -3, WALK)), "Left Leg": V((-0.5, -3, WALK))}
    # standing still, staring; the head tips slightly
    stand = {leg: (feet[leg].copy(), V((0, 0, 0))) for leg in feet}
    arms0 = {"Right Arm": arm_rot(0, 3), "Left Arm": arm_rot(0, -3)}
    holds.append((0, pose((0, -1, WALK), (0, 0, 0), (0, 0, 6), True, stand, arms0)))
    holds.append((6, pose((0, -1, WALK), (0, 0, 0), (0, 0, 12), True, stand, arms0)))
    lands = {0: ("Right Leg", WALK - 2.1), 1: ("Left Leg", WALK - 3.6), 2: ("Right Leg", WALK - 5.1), 3: ("Left Leg", -0.35)}
    f = 12
    for step in range(4):
        leg, land = lands[step]
        other = "Left Leg" if leg == "Right Leg" else "Right Leg"
        sx = 1 if leg == "Right Leg" else -1
        start = feet[leg].copy()
        z0 = WALK - 1.5 * step
        for p, u in enumerate((0.25, 0.5, 0.75, 1.0)):
            hz = z0 - 1.5 * u
            bob = (-0.12, -0.04, 0.04, -0.1)[p]
            lift = (0.35, 0.55, 0.3, 0.0)[p]
            fz = start.z + (land - start.z) * (0.15, 0.5, 0.85, 1.0)[p]
            swing = (V((start.x, -3, fz)), V((0, lift * 0.8, -lift * 0.25)))
            planted = (feet[other].copy(), V((0, 0, 0)))
            a = (-22, -6, 12, 24)[p]  # the arm opposite the swinging leg swings forward
            fwd_arm = "Left Arm" if leg == "Right Leg" else "Right Arm"
            back_arm = "Right Arm" if leg == "Right Leg" else "Left Arm"
            fs = 1 if fwd_arm == "Right Arm" else -1
            arms = {fwd_arm: arm_rot(a, 2 * fs, (-fs * 0.12 * max(0, a) / 24, 0.04 * max(0, a) / 24, -0.18 * max(0, a) / 24)),
                    back_arm: arm_rot(-a, 3 * -fs, (0, 0, 0.08 * max(0, a) / 24))}
            rot = (-4, 7 * sx * (0.5 - u) * 2, 2 * sx * (p - 1.5) / 1.5)
            holds.append((f, pose((0, -1 + bob, hz), rot, (0, 0, 6), True, {leg: swing, other: planted}, arms)))
            f += 5
        feet[leg] = V((start.x, -3, land))
    # the closing half step, feet together, and stop
    for p, (zr, lift) in enumerate(((0.3, 0.35), (0.05, 0.0))):
        legs = {"Right Leg": (V((0.5, -3, zr)), V((0, lift * 0.8, -lift * 0.25))), "Left Leg": (feet["Left Leg"].copy(), V((0, 0, 0)))}
        holds.append((f, pose((0, -1 - 0.04 * (1 - p), 0.0), (-2, 0, 0), (0, 0, 4), True, legs,
                              {"Right Arm": arm_rot(10 - 10 * p, 3), "Left Arm": arm_rot(-8 + 8 * p, -3)})))
        f += 4
    return holds, f


def grab_holds(ctx):
    th = ctx["throat_k"]
    st = {"Right Leg": (V((0.55, -3, 0.35)), V((0, 0, 0))), "Left Leg": (V((-0.5, -3, -0.45)), V((0, 0, 0)))}
    hang_l = arm_rot(-6, -4, (0, -0.05, 0.05))
    holds = [
        # reaching out for the throat
        (100, pose((0, -1.05, 0.0), (-8, -6, 0), (0, 0, 4), True, st,
                   {"Right Arm": ("reach", th + V((0, 0.05, 0.35)), V((0, 0.05, -0.3))), "Left Arm": arm_rot(-12, -4)})),
        # clamped on it
        (GRAB, pose((0, -1.05, 0.0), (-10, -8, 0), (-4, 0, 6), True, st,
                    {"Right Arm": ("reach", th, V((0, 0.1, -0.4))), "Left Arm": hang_l})),
        # lifting, in two jolts, up onto its toes
        (110, pose((0, -0.88, 0.05), (-2, -4, 2), (6, 0, 8), True, st,
                   {"Right Arm": ("reach", V((0.6, 1.9, -2.45)), V((0.1, 0.25, -0.45))), "Left Arm": hang_l})),
        (116, pose((0, -0.62, 0.12), (5, 0, 3), (12, 0, 10), True, st,
                   {"Right Arm": ("reach", V((1.35, 2.8, -2.15)), V((0.22, 0.38, -0.6))), "Left Arm": arm_rot(-10, -6, (0, -0.05, 0.08))})),
        (122, pose((0, -0.66, 0.12), (4, 0, 3), (10, 0, 12), True, st,
                   {"Right Arm": ("reach", V((1.35, 2.7, -2.15)), V((0.22, 0.36, -0.6))), "Left Arm": hang_l})),
    ]
    # holding them up: a squeeze now and then, the head tipping over a little more each time
    for i, f in enumerate((130, 138, 146, 154, 162)):
        j = 0.06 * (1 if i % 2 else -1)
        holds.append((f, pose((0, -0.66 + j * 0.5, 0.12), (4, 0, 3 + 2 * (i % 2)), (8, 0, 18 + 10 * i), True, st,
                              {"Right Arm": ("reach", V((1.35 + j, 2.72 + j, -2.15)), V((0.22, 0.36 + j, -0.6))),
                               "Left Arm": arm_rot(-6 - 3 * (i % 2), -4, (0, -0.05, 0.05))})))
    # let go: the arm stays up a beat, comes down in two drops, the head snaps upright
    holds += [
        (DROP, pose((0, -0.7, 0.12), (6, 0, 3), (6, 0, 62), True, st,
                    {"Right Arm": ("reach", V((1.4, 2.75, -2.1)), V((0.24, 0.4, -0.62))), "Left Arm": hang_l})),
        (178, pose((0, -0.95, 0.08), (2, 0, 2), (-14, 0, 64), True, st,
                   {"Right Arm": ("reach", V((1.6, 0.9, -1.5)), V((0.12, 0.1, -0.3))), "Left Arm": hang_l})),
        (184, pose((0, -1.0, 0.05), (-2, 0, 0), (-22, 0, 68), True, st,
                   {"Right Arm": arm_rot(8, 4, (0.04, 0, -0.06)), "Left Arm": hang_l})),
        (REVEAL, pose((0, -1.0, 0.05), (0, 0, 0), (-4, 0, 0), True, st, {"Right Arm": arm_rot(0, 3), "Left Arm": arm_rot(0, -3)})),
    ]
    return holds


def boil(i, scale=1.0):
    r = random.Random(i * 7919 + 13)
    return V((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * scale


def killer_pose(ka, i, frame, p, vhead_k):
    b = boil(i)
    torso = ka.torso_from_hips(p["hips"], p["rot"] + b * 0.6)
    k = ka.build(frame, torso, head=p["head"] + b * 1.2, look_at=vhead_k if p["look"] else None, lag={"head": 0})
    for leg, (target, move) in p["legs"].items():
        K.reach_r6_off(k, leg, target, move)
    for arm, spec in p["arms"].items():
        if spec[0] == "rot":
            e, move = spec[1], spec[2]
            k.rotate(arm, K.rot("X", e.x) @ K.rot("Y", e.y) @ K.rot("Z", e.z))
            K.dislocate(k, arm, move)
        else:
            K.reach_r6_off(k, arm, spec[1], spec[2])
    return k


# ---------------------------------------------------------------- the player (their own space, smooth)
V_HIPS = T((0, (0, -1, 0)), (60, (0, -1, 0)), (76, (0, -1, 0.35), "io"), (98, (0, -1, 0.4)), (103, (0, -1, 0.55), "o3"))
V_ROT = T((0, (0, 0, 0)), (40, (0, 0, 0)), (62, (4, 0, -3), "io"), (96, (6, 0, 2)), (103, (14, 0, 0), "o3"))
V_HEAD = T((0, (0, 0, 0)), (16, (0, 0, 0)), (28, (0, 0, 10), "io"), (50, (0, 0, 4)), (86, (6, 0, 0)), (103, (-6, 0, 0), "o"))
V_ARMS_UP = T((0, 0.0), (78, 0.0), (98, 0.6, "io"), (103, 1.0, "o3"))
H_ROT = T((GRAB, (14, 0, 0)), (108, (-10, 0, 4), "o3"), (114, (4, 0, -2)), (124, (8, 0, 0)), (DEATH, (6, 0, 0)),
          (160, (-6, 0, 0), "o"), (164, (8, 0, 3), "o"), (DROP, (5, 0, 0)))
KICK = T((GRAB, 0.0), (110, 1.2, "o"), (134, 1.0), (148, 0.6), (DEATH, 0.35), (160, 1.3, "o3"), (166, 0.0, "o"))
CLUTCH = T((GRAB, 0.0), (110, 1.0, "o"), (152, 0.9), (DEATH + 2, 0.0, "o"))
HEAD_H = T((GRAB, (-6, 0, 0)), (108, (-20, 0, 6), "o3"), (116, (16, 0, 0)), (DEATH, (20, 0, 0)), (160, (34, 0, 0), "o3"),
           (166, (-14, 0, 34), "o"), (DROP, (-16, 0, 38)))


def fall_tracks(p0, r0):
    """The fall, posed: lands on its feet, the knees buckle, tips back onto the floor with the arms
    flung out, bounces (the legs lift a little and slap down) and settles with the legs flat."""
    x, z = p0.x, p0.z
    torso_pos = T((DROP, p0), (177, (x, 0.0, z), "i"), (181, (x + 0.1, -1.0, z + 0.25), "io"),
                  (LAND, (x + 0.2, -2.5, z + 1.45), "i"), (189, (x + 0.2, -2.32, z + 1.48), "o"),
                  (194, (x + 0.2, -2.5, z + 1.5), "io"))
    torso_rot = T((DROP, r0), (177, (-10, 4, -3), "i"), (181, (26, 8, -6), "io"), (LAND, (90, 14, -10), "i"),
                  (189, (84, 14, -10), "o"), (194, (90, 16, -12), "io"))
    limbs = {
        "Right Arm": T((DROP, (0.1, -1, 0.05)), (177, (0.2, -1, -0.1)), (181, (0.75, 0.35, 0.2), "o"), (LAND, (1.0, -0.15, 0.1), "i"),
                       (189, (0.95, 0.1, 0.05), "o"), (194, (0.95, -0.25, 0.15), "io")),
        "Left Arm": T((DROP, (-0.1, -1, 0.05)), (177, (-0.15, -1, -0.15)), (181, (-0.6, 0.55, 0.1), "o"), (LAND, (-0.9, 0.2, 0.1), "i"),
                      (189, (-0.85, 0.35, 0.05), "o"), (194, (-0.35, -0.95, -0.05), "io")),  # comes to rest along the side
        "Right Leg": T((DROP, (0.05, -1, 0.0)), (177, (0.1, -1, -0.05)), (181, (0.25, -0.6, -0.75), "io"), (LAND, (0.12, -1, -0.05), "i"),
                       (189, (0.12, -0.95, -0.25), "o"), (194, (0.15, -1, 0.0), "io")),
        "Left Leg": T((DROP, (-0.05, -1, 0.0)), (177, (-0.1, -1, -0.05)), (181, (-0.25, -0.65, -0.7), "io"), (LAND, (-0.12, -0.95, -0.3), "i"),
                      (189, (-0.12, -1, -0.1), "o"), (194, (-0.35, -0.95, -0.02), "io")),  # flat, splayed out
    }
    moves = {  # the legs moved up toward the hips when they're bent (fake knees)
        "Right Leg": T((DROP, (0, 0, 0)), (177, (0, 0, 0)), (181, (0, 0.45, -0.1), "io"), (LAND, (0, 0, 0), "i")),
        "Left Leg": T((DROP, (0, 0, 0)), (177, (0, 0, 0)), (181, (0, 0.45, -0.1), "io"), (LAND, (0, 0, 0), "i")),
    }
    head = T((DROP, (-16, 0, 38)), (177, (-35, 0, 20), "i"), (181, (-10, 0, 10), "o"), (LAND, (20, 0, 0), "i"),
             (189, (-5, 0, 10), "o"), (194, (5, 0, 40), "io"))
    return torso_pos, torso_rot, limbs, moves, head


def victim_pose(va, f, kill_k, ctx):
    khead = (K2V @ kill_k.head_world()).translation
    if f <= GRAB:
        torso = va.torso_from_hips(V_HIPS(f), V_ROT(f))
        v = va.build(f, torso, head=V_HEAD(f), look_at=khead)
        feet = {"Right Leg": V((0.5, -3, 0.7 * K.smoothstep(60, 74, f))), "Left Leg": V((-0.5, -3, 0.35 * K.smoothstep(66, 80, f)))}
        for leg, foot in feet.items():
            K.reach_r6(v, leg, foot)
        up = V_ARMS_UP(f)
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            v.point(arm, (torso.to_3x3() @ V((0, -1, 0)).lerp(V((sx * 0.35, 0.15, -0.9)), up)).normalized())
        ctx["grip"] = None
        return v
    hand = (K2V @ kill_k.parts()["Right Arm"]) @ V((0, -0.85, 0))  # its fingers, in the player's space
    if f < DROP:
        # held by the throat: the body follows the jerking hand smoothly, a beat behind
        g = ctx.get("grip")
        g = hand if g is None else g + (hand - g) * 0.35
        ctx["grip"] = g
        k = KICK(f)
        rot = H_ROT(f) + V((0, 0, 4 * math.sin(f / 5.0) * k))
        R = KA.euler(rot)
        torso = Matrix.Translation(g - R.to_3x3() @ (NECK + V((0, 0, -0.25)))) @ R
        dead = f >= 162
        v = va.build(f, torso, head=HEAD_H(f), look_at=None if dead else khead, lag={"head": 2})
        for leg, sx, ph in (("Right Leg", 1, 0.0), ("Left Leg", -1, 1.4)):
            d = V((sx * 0.08, -1, 0.6 * k * math.sin(f / 2.6 + ph)))
            if dead:
                v.point(leg, V((sx * 0.05, -1, 0.03)).normalized())
            else:
                v.point(leg, (va.rot.get(f - 3, torso.to_3x3()) @ d).normalized())
        c = CLUTCH(f)
        ka_arm = K2V @ kill_k.parts()["Right Arm"]
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            on_arm = ka_arm @ V((0, -0.2 - 0.35 * (sx > 0), 0))  # both hands on its forearm
            if c > 0.02:
                K.reach_r6(v, arm, (torso @ V((sx * 1.5, -1.0, -0.6))).lerp(on_arm, c))
            else:
                v.point(arm, V((sx * 0.1, -1, 0.05)).normalized())
        ctx["drop_torso"], ctx["drop_rot"] = torso, rot
        return v
    if "fall" not in ctx:
        ctx["fall"] = fall_tracks(ctx["drop_torso"].translation.copy(), ctx["drop_rot"])
    tpos, trot, limbs, moves, head = ctx["fall"]
    torso = Matrix.Translation(tpos(f)) @ KA.euler(trot(f))
    v = va.build(f, torso, head=head(f), limbs={limb: tr(f) for limb, tr in limbs.items()},
                 lag={"arms": 2, "legs": 1, "head": 2})
    for leg, tr in moves.items():
        K.dislocate(v, leg, tr(f))
    return v


# ---------------------------------------------------------------- building it
def frames():
    va, ka, ctx = KA.VictimAnimator(), KA.VictimAnimator(), {}
    g = va.torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))  # where the throat will be at the grab
    ctx["throat_k"] = V2K @ (g @ NECK)
    holds, _ = walk_holds(ctx)
    holds += grab_holds(ctx)
    holds.sort(key=lambda h: h[0])
    vic, kil, cache = [], [], {}
    vhead_k = V2K @ V((0, 1.5, 0))
    for f in range(LENGTH + 1):
        i = max(j for j, (hf, _) in enumerate(holds) if hf <= f)
        if i not in cache:
            cache[i] = killer_pose(ka, i, holds[i][0], holds[i][1], vhead_k)
        k = cache[i]
        v = victim_pose(va, f, k, ctx)
        vhead_k = V2K @ v.head_world().translation
        vic.append(v.parts())
        kil.append(k.parts())
    return vic, kil


def preview(vic, kil, path, k=0.28):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 30
    sc.frame_start, sc.frame_end = 0, LENGTH
    pl = K.Placement(k, 0.0, V((0, 0, 0)))
    vb = K.r6_boxes("Victim", K.VICTIM_COLORS)
    kb = K.r6_boxes("Killer", KILLER_COLORS)
    cam = bpy.data.objects.new("FP", bpy.data.cameras.new("FP"))
    cam.data.lens = 18
    cam.data.clip_start = 0.01
    sc.collection.objects.link(cam)
    for f, (vp, kp) in enumerate(zip(vic, kil)):
        for boxes, parts in ((vb, vp), (kb, {p: K2V @ m for p, m in kp.items()})):
            for part, ob in boxes.items():
                ob.matrix_world = pl.to_blender(parts[part])
                for p in ("location", "rotation_euler", "scale"):
                    ob.keyframe_insert(p, frame=f)
        K.fp_camera(pl, vp["Head"], f, cam)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))


NOTE = """CRT Man's disguised kill (R6 against R6).

InternalArmature is the disguised CRT Man (action StandIn_DisguisedKill_Killer, stop motion);
InternalArmature.001 is the player (action StandIn_DisguisedKill_Victim, smooth). 30 fps,
frames 0-206. Their constraints to the control rigs (KillerRig.001, PlayerRig) are muted so
the keys drive them, and the control rigs are hidden; your own poses are still on the control
rigs if you unmute them. Export each InternalArmature's action with your R6 exporter.

In the game: the killer's HumanoidRootPart 1.9 studs in front of the player's, facing them.
Its body starts 6 studs further back and walks onto it.
Timeline markers: Grab (QTE starts), Death (QTE ends), Drop, Reveal (glitch him back into the
suit), End.
"""


def write_blend(src, out, vic, kil):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(src))
    sc = bpy.context.scene
    sc.render.fps = 30
    sc.frame_start, sc.frame_end = 0, LENGTH
    for m in list(sc.timeline_markers):
        sc.timeline_markers.remove(m)
    for f, name in MARKERS.items():
        sc.timeline_markers.new(name, frame=f)
    player_y = -2.86
    killer = bpy.data.objects["InternalArmature"]
    player = bpy.data.objects["InternalArmature.001"]
    K.key_r6_rig(killer, kil, "StandIn_DisguisedKill_Killer")
    K.key_r6_rig(player, vic, "StandIn_DisguisedKill_Victim")
    player.location = (0, player_y, 0)
    player.rotation_euler = (0, 0, 0)
    killer.location = (0, player_y + DISTANCE, 0)  # the player faces +Y, the killer faces it
    killer.rotation_euler = (0, 0, math.pi)
    for name in ("KillerRig.001", "PlayerRig"):
        ob = bpy.data.objects.get(name)
        if ob:
            ob.hide_set(True)
            ob.hide_render = True
    txt = bpy.data.texts.get("KILL_README") or bpy.data.texts.new("KILL_README")
    txt.clear()
    txt.write(NOTE)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))


def main(export_dir, preview_path):
    vic, kil = frames()
    preview(vic, kil, preview_path)
    src = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6Kill.blend"))
    write_blend(src, os.path.join(export_dir, "StandIn_DisguisedKill.blend"), vic, kil)
    print("disguised kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
