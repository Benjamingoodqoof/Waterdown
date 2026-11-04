#!/usr/bin/env python3
"""CRT Man's kill while disguised as a teammate: R6 against R6.

The "teammate" stands too still, its head tipped over, staring. Then it walks slowly at the
player, one heavy stomping step after another, hunched and swaying, its arms hanging half out
of their sockets, its head tilted and locked on them. Its right arm snaps up to their throat
and it lifts them off the floor one-handed, in jolts, the arm pulled out of its socket by the
weight. They kick and claw at its arm while its head tips further and further over. They go
limp; it opens its hand and they drop and crumple. Its arm sinks back down in jerks, and its
head snaps upright: the moment for the game to glitch it back into the suit.

The disguise is animated in stop motion (poses held on fours, about 7 fps, with a little
boil between holds, like its other disguise animations); the player moves smoothly.

Writes export/StandIn_DisguisedKill.blend: a copy of the user's R6 kill file
(shared/r6/Blender_R6Kill.blend) with both InternalArmatures keyed: InternalArmature (the
disguised CRT Man, action StandIn_DisguisedKill_Killer) and InternalArmature.001 (the player,
action StandIn_DisguisedKill_Victim). Both start together, with the killer's HumanoidRootPart
DISTANCE studs in front of the player's, facing them; the killer's body starts WALK studs
behind its HumanoidRootPart and walks onto it. 198 frames at 30 fps.

Markers: Grab 96 (QTE starts), Death 150 (QTE ends), Drop 166, Reveal 190 (glitch him back into
the suit), End 198.

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
LENGTH = 198
STILL, STEP_T = 12, 20  # it stands still, then 4 steps of 20 frames
GRAB, LIFTED, DEATH, DROP, LAND, REVEAL = 96, 126, 150, 166, 182, 190
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", REVEAL: "Reveal", LENGTH: "End"}
K2V = Matrix.Translation((0, 0, -DISTANCE)) @ K.rot("Y", 180)  # the killer's HRP space -> the player's
V2K = K2V.inverted()
NECK = Vector((0.0, 1.0, -0.3))  # the front of the throat, in the torso's frame
KILLER_COLORS = {"Torso": (0.12, 0.3, 0.16), "Head": (0.85, 0.7, 0.55), "Right Arm": (0.85, 0.7, 0.55),
                 "Left Arm": (0.85, 0.7, 0.55), "Right Leg": (0.12, 0.12, 0.14), "Left Leg": (0.12, 0.12, 0.14)}


# ---------------------------------------------------------------- stop motion
def hold_of(f):
    """The frame whose pose the disguise is holding at frame f: on fours, on twos for the
    snap to the throat, on threes as it lets go."""
    if f < 92:
        return f - f % 4
    if f < 100:
        return 92 + (f - 92) // 2 * 2
    if f < DROP:
        return 100 + (f - 100) // 4 * 4
    return DROP + (f - DROP) // 3 * 3


def boil(hold, scale=1.0):
    """A small random wobble, fixed for each held pose (stop-motion boil)."""
    r = random.Random(hold * 7919 + 13)
    return Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * scale


# ---------------------------------------------------------------- the killer (its own space, facing -Z)
def walk_state(f):
    """Hip position, sway and the two feet's floor positions for the walk."""
    if f <= STILL:
        return WALK, 0, Vector((0.5, -3, WALK)), Vector((-0.5, -3, WALK)), 0.0, -1
    i = min(3, int((f - STILL) // STEP_T))
    u = min(1.0, (f - STILL - i * STEP_T) / STEP_T) if f < STILL + 4 * STEP_T else 1.0
    if f >= STILL + 4 * STEP_T:
        i, u = 3, 1.0
    hz0 = WALK - 1.5 * i
    hz = hz0 - 1.5 * KA.EASE["io"](u)
    lands = [WALK - 1.5 - 0.6, WALK - 3.0 - 0.6, WALK - 4.5 - 0.6, 0.0]  # where each step's foot comes down
    right = [WALK, lands[0], lands[0], lands[2], lands[2]]
    left = [WALK, WALK, lands[1], lands[1], lands[3]]
    swing = "R" if i % 2 == 0 else "L"
    rz = right[i] + (right[i + 1] - right[i]) * KA.EASE["io"](u)
    lz = left[i] + (left[i + 1] - left[i]) * KA.EASE["io"](u)
    lift = 0.9 * math.sin(math.pi * u) ** 0.8
    rf = Vector((0.5, -3 + (lift if swing == "R" else 0), rz))
    lf = Vector((-0.5, -3 + (lift if swing == "L" else 0), lz))
    return hz, (1 if swing == "R" else -1), rf, lf, u, i


K_TORSO_ROT = T((0, (-6, 0, 0)), (STILL, (-10, 0, 0)), (90, (-14, 0, 0)), (92, (-6, -16, 4)), (95, (-20, 10, -2)),
                (GRAB, (-18, 8, 0)), (112, (0, 4, 2)), (LIFTED, (5, 4, 4)), (DROP, (4, 4, 2)), (172, (-4, 0, 0)), (LENGTH, (-8, 0, 0)))
K_HEAD = T((0, (0, 0, 24)), (STILL, (0, 0, 28)), (90, (-4, 0, 26)), (GRAB, (-2, 0, 18)), (132, (0, 0, 32)),
           (140, (0, 0, 46)), (148, (0, 0, 60)), (156, (0, 0, 74)), (DROP, (0, 0, 80)), (REVEAL - 1, (-10, 0, 84)),
           (REVEAL, (0, 0, 0), "hold"), (LENGTH, (0, 4, -6)))
# the lifting arm's hand, in the killer's space: from the throat, up in jolts
LIFT_PATH = T((GRAB, (0, 1.0, -2.0)), (104, (0.6, 1.7, -2.4)), (112, (1.1, 2.3, -2.25)), (120, (1.4, 2.7, -2.1)),
              (LIFTED, (1.5, 2.85, -2.05)), (DROP, (1.5, 2.9, -2.05)), (174, (1.52, 2.9, -2.1)),
              (186, (1.5, -0.9, -0.4), "io"))
R_OFFSET = T((0, (0.1, -0.25, -0.2)), (90, (0.1, -0.3, -0.35)), (95, (0.05, 0.0, -0.6)), (GRAB, (0.0, 0.1, -0.55)),
             (LIFTED, (0.25, 0.35, -0.8)), (DROP, (0.25, 0.37, -0.82)), (186, (0.1, -0.3, -0.15)))
L_OFFSET = T((0, (-0.1, -0.35, -0.1)), (LENGTH, (-0.1, -0.4, -0.1)))


def killer_pose(ka, h, vhead_k, ctx):
    """The killer's pose for held frame h (its own space). vhead_k: the player's head."""
    hz, side, rf, lf, u, step = walk_state(h)
    b = boil(h)
    sway = 6 * side * math.sin(math.pi * u) if step >= 0 else 0.0
    bob = -0.12 - 0.12 * math.sin(math.pi * u) if step >= 0 else -0.08
    rise = 0.45 * K.smoothstep(GRAB, LIFTED, h) * (1 - K.smoothstep(DROP, 180, h))  # up on its toes to lift
    rot = K_TORSO_ROT(h) + Vector((0, 5 * side * math.sin(math.pi * u) if step >= 0 else 0, sway)) + b * 1.2
    torso = ka.torso_from_hips(Vector((0, -1 + bob + rise, hz)), rot)
    k = ka.build(h, torso, head=K_HEAD(h) + b * 2.5, look_at=vhead_k if h < REVEAL else None, lag={"head": 0})
    # legs: planted feet, the swinging one lifted high and stomped down
    K.reach_r6(k, "Right Leg", rf + Vector((0, 0, -0.05)))
    K.reach_r6(k, "Left Leg", lf + Vector((0, 0, -0.05)))
    # the left arm hangs out of its socket, swinging a little against the steps
    swing_l = -10 * side * math.sin(math.pi * u) if step >= 0 else 0.0
    k.rotate("Left Arm", (K.rot("X", 8 + swing_l) @ K.rot("Z", -4) @ K.rot("Y", 10)))
    K.dislocate(k, "Left Arm", L_OFFSET(h) + b * 0.03)
    # the right arm: half raised and reaching as it walks; snaps to the throat; lifts; sinks
    if h < 92:
        reach = K.smoothstep(STILL, 90, h)
        k.rotate("Right Arm", K.rot("X", 20 + 30 * reach - 8 * side * math.sin(math.pi * u)) @ K.rot("Z", 8))
        K.dislocate(k, "Right Arm", R_OFFSET(h) + b * 0.03)
    elif h < GRAB:
        if h < 95:  # drawn back
            k.rotate("Right Arm", K.rot("X", -25) @ K.rot("Z", 18))
            K.dislocate(k, "Right Arm", R_OFFSET(h))
        else:
            K.reach_r6_off(k, "Right Arm", ctx["throat_k"] + Vector((0, 0.1, 0.25)), R_OFFSET(h))
    else:
        target = LIFT_PATH(h) if h >= 104 else ctx["throat_k"].lerp(LIFT_PATH(104), (h - GRAB) / 8)
        if h <= DROP:
            target = target + (ctx["throat_k"] - LIFT_PATH(GRAB)) * (1 - K.smoothstep(GRAB, 112, h))
        K.reach_r6_off(k, "Right Arm", target + b * 0.04, R_OFFSET(h))
    return k


# ---------------------------------------------------------------- the player (their own space, smooth)
V_HIPS = T((0, (0, -1, 0)), (60, (0, -1, 0)), (75, (0, -1, 0.35), "io"), (92, (0, -1, 0.4)), (95, (0, -1, 0.55), "o3"))
V_ROT = T((0, (0, 0, 0)), (40, (0, 0, 0)), (60, (4, 0, -3), "io"), (88, (6, 0, 2)), (95, (14, 0, 0), "o3"))
V_HEAD = T((0, (0, 0, 0)), (16, (0, 0, 0)), (28, (0, 0, 10), "io"), (50, (0, 0, 4)), (80, (6, 0, 0)), (95, (-6, 0, 0), "o"))
V_ARMS_UP = T((0, 0.0), (70, 0.0), (90, 0.6, "io"), (95, 1.0, "o3"))
H_ROT = T((GRAB, (14, 0, 0)), (99, (-10, 0, 4), "o3"), (106, (4, 0, -2)), (LIFTED, (8, 0, 0)), (DEATH, (6, 0, 0)),
          (152, (-6, 0, 0), "o"), (156, (8, 0, 3), "o"), (DROP, (5, 0, 0)))
KICK = T((GRAB, 0.0), (102, 1.2, "o"), (128, 1.0), (140, 0.6), (DEATH, 0.35), (152, 1.3, "o3"), (158, 0.0, "o"))
CLUTCH = T((GRAB, 0.0), (102, 1.0, "o"), (144, 0.9), (DEATH + 2, 0.0, "o"))
HEAD_H = T((GRAB, (-6, 0, 0)), (99, (-20, 0, 6), "o3"), (108, (16, 0, 0)), (DEATH, (20, 0, 0)), (152, (34, 0, 0), "o3"),
           (158, (-14, 0, 34), "o"), (DROP, (-16, 0, 38)))


def victim_pose(va, f, kill_k, ctx):
    """kill_k: the killer's pose this frame (its own space)."""
    khead = (K2V @ kill_k.head_world()).translation
    if f <= GRAB:
        torso = va.torso_from_hips(V_HIPS(f), V_ROT(f))
        v = va.build(f, torso, head=V_HEAD(f), look_at=khead)
        feet = {"Right Leg": Vector((0.5, -3, 0.7 * K.smoothstep(60, 74, f))), "Left Leg": Vector((-0.5, -3, 0.35 * K.smoothstep(66, 80, f)))}
        for leg, foot in feet.items():
            K.reach_r6(v, leg, foot)
        up = V_ARMS_UP(f)
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            v.point(arm, (torso.to_3x3() @ Vector((0, -1, 0)).lerp(Vector((sx * 0.35, 0.15, -0.9)), up)).normalized())
        ctx["grip"] = None
        return v
    hand = (K2V @ kill_k.parts()["Right Arm"]) @ Vector((0, -0.85, 0))  # its fingers, in the player's space
    if f < DROP:
        # held by the throat: the body follows its jerking hand smoothly, a beat behind
        g = ctx.get("grip")
        g = hand if g is None else g + (hand - g) * 0.55
        ctx["grip"] = g
        k = KICK(f)
        rot = H_ROT(f) + Vector((0, 0, 4 * math.sin(f / 5.0) * k))
        R = KA.euler(rot)
        torso = Matrix.Translation(g - R.to_3x3() @ (NECK + Vector((0, 0, -0.25)))) @ R
        dead = f >= 154
        v = va.build(f, torso, head=HEAD_H(f), look_at=None if dead else khead, lag={"head": 2})
        for leg, sx, ph in (("Right Leg", 1, 0.0), ("Left Leg", -1, 1.4)):
            d = Vector((sx * 0.08, -1, 0.6 * k * math.sin(f / 2.6 + ph)))
            if dead:
                v.point(leg, Vector((sx * 0.05, -1, 0.03)).normalized())
            else:
                v.point(leg, (va.rot.get(f - 3, torso.to_3x3()) @ d).normalized())
        c = CLUTCH(f)
        for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
            ka_arm = K2V @ kill_k.parts()["Right Arm"]
            on_arm = ka_arm @ Vector((0, -0.2 - 0.35 * (sx > 0), 0))  # both hands on its forearm
            hang = Vector((sx * 0.1, -1, 0.05))
            if c > 0.02:
                K.reach_r6(v, arm, (torso @ Vector((sx * 1.5, -1.0, -0.6))).lerp(on_arm, c))
            else:
                v.point(arm, hang.normalized())
        ctx["drop_torso"], ctx["drop_rot"] = torso, rot
        return v
    # dropped: falls, the legs fold under, tips back onto the floor, a bounce
    if "fall" not in ctx:
        p0, r0 = ctx["drop_torso"].translation.copy(), ctx["drop_rot"]
        ctx["fall"] = (T((DROP, p0), (172, (p0.x, 0.1, p0.z + 0.1), "i"), (LAND, (p0.x + 0.3, -2.5, p0.z + 1.4), "i"),
                         (185, (p0.x + 0.3, -2.36, p0.z + 1.45), "o"), (189, (p0.x + 0.3, -2.5, p0.z + 1.5), "i")),
                       T((DROP, r0), (172, (18, 6, -6), "i"), (LAND, (88, 14, -12), "i"), (185, (82, 14, -12), "o"),
                         (189, (88, 14, -12), "i")))
    pos, rot = ctx["fall"][0](f), ctx["fall"][1](f)
    land = K.smoothstep(172, LAND, f)
    v = va.build(f, Matrix.Translation(pos) @ KA.euler(rot), head=Vector((-30 + 40 * land, 0, 30 * land)),
                 lag={"arms": 3, "legs": 2, "head": 3},
                 limbs={"Right Arm": Vector((0.2, 0.5, 0.1)).lerp(Vector((0.95, -0.25, 0.15)), land),
                        "Left Arm": Vector((-0.2, 0.6, 0.1)).lerp(Vector((-0.95, -0.2, 0.2)), land),
                        "Right Leg": Vector((0.1, -0.75, -0.65)).lerp(Vector((0.18, -1, -0.15)), land),
                        "Left Leg": Vector((-0.1, -0.8, -0.6)).lerp(Vector((-0.12, -1, -0.05)), land)})
    return v


# ---------------------------------------------------------------- building it
def frames():
    va, ka, ctx = KA.VictimAnimator(), KA.VictimAnimator(), {}
    # where the throat will be at the grab, from the player's own animation
    g = va.torso_from_hips(V_HIPS(GRAB), V_ROT(GRAB))
    ctx["throat_k"] = V2K @ (g @ NECK)
    vic, kil, cache = [], [], {}
    vhead_k = V2K @ Vector((0, 1.5, 0))
    for f in range(LENGTH + 1):
        h = hold_of(f)
        if h not in cache:
            cache[h] = killer_pose(ka, h, vhead_k, ctx)
        k = cache[h]
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
    pl = K.Placement(k, 0.0, Vector((0, 0, 0)))
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
frames 0-198. Their constraints to the control rigs (KillerRig.001, PlayerRig) are muted so
the keys drive them, and the control rigs are hidden; your own poses are still on the control
rigs if you unmute them. Export each InternalArmature's action with your R6 exporter.

In the game: the killer's HumanoidRootPart 1.9 studs in front of the player's, facing them.
Its body starts 6 studs further back and walks onto its HumanoidRootPart.
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
