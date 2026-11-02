#!/usr/bin/env python3
"""The stack's kill, "Swarmed": it lurches in and slams both hands onto the player's shoulders,
shoves them over onto their back, and collapses on top of them, the whole pile coming down over
their face. Pinned under it, they push at it while the creatures in it writhe and turn to look
at them, until they stop moving.

Writes the stack's "Kill" action into stack.blend, and the player's half on the R6 rig
(export/Stack_Kill_Victim.blend). Both are 100 frames (3.3 s) and start together, with the
player's HumanoidRootPart DISTANCE studs in front of the stack's, facing it.

Markers: Grab 10 (the save window opens: a teammate's light now makes it drop them), Floor 24
(they hit the floor), Swarm 34 (the pile lands on them, the camera goes dark; the window
closes), End 100.

Usage: python3 litter_kill.py LITTER_DIR PREVIEW_BLEND
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
import litter_animate as LA  # noqa: E402
from kill_core import smoothstep as ss, window  # noqa: E402

HEIGHT_M, HEIGHT_STUDS = 2.661, 10.0
KM = HEIGHT_M / HEIGHT_STUDS
DISTANCE = 3.6
LENGTH = 100
GRAB, FLOOR, SWARM, STILL = 10, 24, 34, 80
MARKERS = {GRAB: "Grab", FLOOR: "Floor", SWARM: "Swarm", LENGTH: "End"}
SIDES = (("Left", 1.0), ("Right", -1.0))
LYING = Matrix.Translation((0.0, -2.5, 0.6)) @ K.rot("X", 90)  # on their back, head away from it


def monster_body(an, f):
    lurch = ss(0, GRAB, f)
    shove = ss(GRAB, FLOOR, f)
    fall = ss(FLOOR - 4, SWARM, f)
    land = A.bump(f, SWARM - 2, SWARM, SWARM + 10)
    writhe = ss(SWARM, SWARM + 8, f) * (1 - 0.6 * ss(STILL - 10, STILL + 10, f))
    pose = {
        "LowerTorso": [("x", 6 + 8 * lurch + 16 * shove + 46 * fall), ("z", 4 * math.sin(f / 7.0) * writhe)],
        "UpperTorso": [("x", 6 + 10 * lurch + 10 * shove + 20 * fall - 6 * land + 4 * math.sin(f / 5.0) * writhe),
                       ("z", 5 * math.sin(f / 6.0 + 1) * writhe)],
        "Head": [("x", -16 * lurch - 10 * shove + 10 * fall)],
        # the open-mouthed head creature lunges down at their face
        "Slot_Head1": [("x", -20 * shove * (1 - fall) - 10 * fall + 8 * math.sin(f / 3.0) * writhe)],
    }
    # every creature squirms, wildly once the pile is on them
    pose.update(LA.creatures(f / 40.0, 4.0 + 4 * lurch + 16 * writhe, hits=(SWARM / 100.0,), kick=2.0 * fall,
                             look=10 + 40 * writhe))
    an.fk(pose, {"LowerTorso": (0.0, -0.15 * lurch - 0.2 * shove - 0.35 * fall, -0.06 * lurch - 0.72 * fall)})
    step = ss(0, 9, f)
    for side, sx in SIDES:
        rest = an.pb[f"{side}Foot"].bone.head_local
        off = Vector((0, -0.35 * step - 0.15 * shove, 0.12 * math.sin(math.pi * step))) if side == "Right" else \
            Vector((0, -0.05 * step, 0))
        an.leg(side, rest + off, 0.0, 0.2 * sx)


def victim(an, ctx, f):
    pl = ctx["pl"]
    v = K.Victim()
    head_c = pl.point_to_victim(an.pb["Slot_Head1"].matrix.translation)
    if f <= GRAB:
        K.recoil(v, f, 1, 9, head_c, (4, 10))
        ctx["grab_torso"] = v.torso.copy()
        return v
    # shoved over backwards onto the floor, then pinned under the pile
    K.fall(v, ctx["grab_torso"], f, GRAB, FLOOR, LYING)
    if f > FLOOR:
        v.torso.translation.y -= 0.15 * A.bump(f, SWARM - 2, SWARM, SWARM + 8)  # crushed when it lands
    fight = window(f, GRAB, GRAB + 3, STILL - 16, STILL)
    K.kick_legs(v, f, 0.8 * fight, 2.4)
    # arms up, shoving at the mass coming down on them, weakening
    for arm, sx in (("Right Arm", 1), ("Left Arm", -1)):
        up = Vector((0.45 * sx, 0.5 + 0.2 * math.sin(f / 2.6 + sx) * fight, -1.0))  # out in front of their chest
        cur = (v.torso.to_3x3() @ up).normalized()
        v.point(arm, cur.lerp((v.torso.to_3x3() @ Vector((0.9 * sx, -0.2, 0))).normalized(), 1 - fight).normalized())
    v.look(head_c, limit=70)
    K.jolt_head(v, f, (GRAB, FLOOR, SWARM), 14)
    return v


def kill(an, ctx, f):
    pl = ctx["pl"]
    monster_body(an, f)
    v = victim(an, ctx, f)
    T = an.rest_delta("UpperTorso")
    reach = ss(2, GRAB, f)
    for side, sx in SIDES:
        rest = T @ an.pb[f"{side}LowerArm"].bone.tail_local
        # its left hand on their right shoulder: slammed on, then pinning it to the floor
        shoulder = pl.point_to_blender(v.torso @ Vector((sx * 0.85, 0.9, -0.3)))
        target = rest.lerp(shoulder, K.back_out(reach, 1.2))
        K.reach(an, side, target, T.to_3x3() @ Vector((sx * 0.9, 0.3, -0.4)),
                Vector((0, 0, -1)) if reach > 0.6 else None, Vector((0, 1, 0)))
    grip = ss(GRAB - 3, GRAB, f)
    pose = {}
    for side, _ in SIDES:
        pose.update(K.finger_curl(an, side, -10 + 50 * grip + 6 * math.sin(f / 4.0) * grip, spread=10 * (1 - grip)))
    for name, rots in pose.items():
        an.pb[name].rotation_quaternion = A.bone_quat(an.pb[name].bone, rots)
    return v


NOTE = """The Litter (stack) kill, the player's half: InternalArmature carries the action
Stack_Kill_Victim (30 fps, frames 0-100). Its constraints to the control rig are muted so the
keys drive it; export it with your R6 exporter as usual. Timeline markers: Grab (save window
opens), Floor, Swarm (the pile lands; window closes), End.
The 'Monster (reference)' collection holds the stack playing its half, at your in-game size,
lined up where the game should put it: 3.6 studs in front of the player, facing them.
"""


def main(litter_dir, preview):
    blend = os.path.join(litter_dir, "stack.blend")
    ctx = K.run_kill(blend, "Stack_Rig", LENGTH, KM, DISTANCE, kill, None, preview, "Stack_Kill_Victim", MARKERS)
    template = os.path.normpath(os.path.join(HERE, "..", "..", "shared", "r6", "Blender_R6.blend"))
    K.write_r6_blend(template, os.path.join(litter_dir, "export", "Stack_Kill_Victim.blend"), ctx["parts"],
                     "Stack_Kill_Victim", MARKERS, (blend, "Stack_Rig", "Kill", KM, DISTANCE, ctx["root"]), NOTE)
    print("kill written")


if __name__ == "__main__":
    main(*sys.argv[1:3])
