#!/usr/bin/env python3
"""The Stand-In's kill (CRT Man): he takes one long step in and grabs the player by the collar,
hauls them up onto their toes and pulls them in under his screen, his monitor bending down over
their face. The game puts the player's avatar on his screen, with static that keeps getting
louder. He holds them there, still, for two seconds while they struggle; then they go limp, he
lets go and they crumple to the floor at his feet.

Writes the Stand-In's "Kill" action into the blend, and the player's half on the R6 rig
(export/StandIn_Kill_Victim.blend). Both are 100 frames (3.3 s) and start together, with the
player's HumanoidRootPart DISTANCE studs in front of his, facing him.

Markers: Grab 12 (show their avatar on his screen, start the static), Death 74 (the static
peaks), Drop 80, End 100.

Usage: python3 standin_kill.py BLEND EXPORT_DIR PREVIEW_BLEND
"""
import math
import os
import sys

import bpy  # noqa: F401
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.normpath(os.path.join(HERE, "..", "..", "shared")))
import anim_core as A  # noqa: E402
import kill_core as K  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.6958, 11.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 100
GRAB, PULLED, DEATH, DROP, DOWN = 12, 26, 74, 80, 92
MARKERS = {GRAB: "Grab", DEATH: "Death", DROP: "Drop", LENGTH: "End"}
SCREEN = Vector((0.0, -0.3, 2.49))
SIDES = (("Left", 1.0), ("Right", -1.0))
COLLAR = Vector((0.0, 0.9, -0.55))  # the front of their collar, in their torso's frame


def monster_body(an, f):
    step = ss(0, 10, f)
    bend = ss(GRAB, PULLED, f) * (1 - ss(DROP + 4, LENGTH, f))
    lean_in = ss(PULLED, DEATH, f)  # the monitor creeping closer while the static builds
    up = ss(DROP + 2, LENGTH, f)
    pose = {
        "LowerTorso": [("x", 4 + 6 * step + 10 * bend)],
        "UpperTorso": [("x", 6 + 8 * step + 18 * bend + 4 * lean_in - 8 * up)],
        # the monitor bends down to look the player in the face, and doesn't look away
        "Head": [("x", 8 * step + 26 * bend + 8 * lean_in + 10 * up), ("y", 8 * math.sin(math.pi * lean_in) * (1 - up)),
                 ("z", -4 * step)],
    }
    pose.update({f"Cable{i}": [("x", 6 * bend + 2 * math.sin(f / 9 + i))] for i in (1, 2, 3)})
    an.fk(pose, {"LowerTorso": (0.0, -0.2 * step, -0.05 * step - 0.06 * bend)})
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        if side == "Right":
            target = rest + Vector((0, -0.42 * step, 0.12 * math.sin(math.pi * step)))
        else:
            target = rest + Vector((0, -0.04 * step, 0))
        an.leg(side, target, 0.0, 0.06 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    screen = pl.point_to_victim(an.rest_delta("Head") @ SCREEN)
    if f <= GRAB:
        K.recoil(v, f, 2, 12, screen, (6, 12))
        ctx["grab_torso"] = v.torso.copy()
        ctx["grab_head"] = v.head_world().translation.copy()
        return v
    # hauled up by the collar onto their toes and in under his screen
    pull = ss(GRAB, PULLED, f)
    # their face held a forearm's length out from his screen, wherever it is
    face = pl.point_to_victim(an.rest_delta("Head") @ (SCREEN + Vector((0.0, -0.5, -0.12))))
    struggle = window(f, GRAB, GRAB + 4, DEATH - 10, DEATH)
    sway = K.rot("Z", 4 * math.sin(f / 4.0) * struggle) @ K.rot("X", 3 * math.sin(f / 5.3) * struggle)
    hv = K.Victim()
    hv.hang_from_head(K.look_cf(ctx["grab_head"].lerp(face, pull), screen), sway @ K.rot("X", -8 * pull))
    torso = hv.torso
    spasm = A.bump(f, DEATH - 2, DEATH, DEATH + 6)
    if f >= DROP:
        ctx.setdefault("drop_torso", torso.copy())
        lying = Matrix.Translation((0.4, -2.5, 1.2)) @ K.rot("Y", 20) @ K.rot("X", 90)
        return K.crumple(v, f, DROP, DOWN, ctx["drop_torso"], lying, screen)
    v.torso = torso
    K.kick_legs(v, f, 0.35 * struggle, 3.2)
    v.look(screen, limit=80)
    # dying: a jolt, then the head drops
    limp = ss(DEATH, DROP, f)
    if spasm or limp:
        v.T["Head"] = v.T["Head"] @ K.rot("X", -12 * spasm + 25 * limp)
    return v


def kill(an, ctx, f):
    monster_body(an, f)
    v = victim(an, ctx, f)
    pl = ctx["pl"]
    T = an.rest_delta("UpperTorso")
    # his right hand: reaches, fists the collar, lets go
    reach = ss(2, GRAB, f)
    release = ss(DROP, DROP + 5, f)
    rest = T @ an.pb["RightLowerArm"].bone.tail_local
    collar = pl.point_to_blender(v.torso @ COLLAR) + Vector((0, 0.02, 0.06))
    if f >= DROP:
        collar = pl.point_to_blender(ctx["drop_torso"] @ COLLAR)
    target = rest.lerp(collar, A.ease(reach))
    if release:
        target = target.lerp(rest + Vector((0.05, -0.3, 0.1)), release)
    tremble = Vector((0, 0, 0.004 * math.sin(f * 1.7))) * window(f, PULLED, PULLED + 6, DEATH, DROP)
    K.reach(an, "Right", target + tremble, T.to_3x3() @ Vector((-0.6, 0.4, -0.6)),
            Vector((0, 0, -1)) if 0.6 < reach and release < 0.5 else None, Vector((0, 1, 0)))
    # his left hand hangs, fingers twitching slowly
    pose = K.finger_curl(an, "Right", (6 + 50 * ss(GRAB - 3, GRAB, f)) * (1 - release))
    pose.update(K.finger_curl(an, "Left", 10 + 8 * math.sin(f / 7.0)))
    pose["LeftUpperArm"] = [("x", -4 - 6 * ss(GRAB, PULLED, f)), ("y", 4)]
    pose["LeftLowerArm"] = [("x", -10)]
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    if GRAB < f < DROP:  # their hands pulling at his wrist, weakening, then falling away
        hold_w = 1 - ss(DEATH - 4, DEATH + 4, f)
        wrist = an.pb["RightLowerArm"].tail
        if hold_w > 0.02:
            K.clutch(v, pl, f, GRAB, {"Right Arm": wrist, "Left Arm": wrist})
        if hold_w < 1:
            for arm in ("Right Arm", "Left Arm"):
                cur = (v.parts()[arm].to_3x3() @ Vector((0, -1, 0))).normalized()
                v.point(arm, cur.lerp(Vector((0, -1, 0)), 1 - hold_w).normalized())
    return v


NOTE = """CRT Man (Stand-In) kill, the player's half: InternalArmature carries the action
StandIn_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (show the
player's avatar on his screen, start the static), Death, Drop, End.
The 'Monster (reference)' collection holds the CRT Man playing his half, at your in-game size,
lined up where the game should put him: 3.6 studs in front of the player, facing them.
"""


def main(blend, export_dir, preview):
    ctx = K.run_kill(blend, "StandIn_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "StandIn_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(export_dir, "StandIn_Kill_Victim.blend"), ctx["parts"], "StandIn_Kill_Victim",
                     MARKERS, (blend, "StandIn_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:4])
